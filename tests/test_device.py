"""Test Tesla BLE device."""
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from bleak_retry_connector import BleakError


from ha_stubs import install_homeassistant_stubs

install_homeassistant_stubs()

from ..const import (
    CHARGING_STATE_CHARGING,
    VEHICLE_STATE_ASLEEP,
    VEHICLE_STATE_AWAKE,
    WRITE_UUID,
)
from ..device import (
    BLE_WRITE_MAX_ATTEMPTS,
    SESSION_RETRY_INTERVAL,
    SESSION_RETRY_MAX_DELAY,
    TeslaBleDevice,
    WAKE_RETRY_INTERVAL,
    WAKE_RETRY_MAX_DELAY,
)
from ..protocol import (
    BLECarServerVehicleAction,
    BLECommand,
    BLECommandState,
    UniversalMessageDomain,
)
from ..protocol_client import ParsedCarServerResponse
from ..proto import signatures_pb2, universal_message_pb2, vcsec_pb2
from ..entity import TeslaBleEntity


@pytest.fixture
def mock_ble_device():
    """Create a mock BLE device."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "Tesla_S123456"
    return device


@pytest.fixture
def tesla_device(mock_ble_device):
    """Create Tesla BLE device for testing."""
    device = TeslaBleDevice(
        ble_device=mock_ble_device,
        vin="TEST123456789ABCD",
        private_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        public_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )
    device.hass = MagicMock()
    device.hass.async_add_executor_job = AsyncMock()

    key_manager = MagicMock()
    key_manager.set_vin = MagicMock()
    key_manager.is_session_valid = MagicMock(return_value=True)
    key_manager.initialize_keys = AsyncMock()
    key_manager.serialize_sessions = MagicMock(return_value={})
    key_manager.load_sessions = MagicMock()
    device.key_manager = key_manager

    device.protocol_client = MagicMock()

    return device


@pytest.mark.asyncio
async def test_device_initialization(tesla_device):
    """Test device initialization."""
    assert tesla_device.vin == "TEST123456789ABCD"
    assert tesla_device.is_connected is False
    assert tesla_device.vehicle_state == "asleep"
    assert tesla_device.data["ble_rssi"] is None


@pytest.mark.asyncio
async def test_queue_command(tesla_device):
    """Test command queueing."""
    # Queueing kicks the domain queue, which would otherwise attempt real BLE I/O.
    tesla_device._process_domain_queue = AsyncMock()

    await tesla_device._queue_command(
        "test_command",
        BLECarServerVehicleAction.GET_CHARGE_STATE,
        UniversalMessageDomain.DOMAIN_INFOTAINMENT
    )

    queued = tesla_device._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT).iter_all()
    assert len(queued) == 1
    command = queued[0]
    assert command.execute_name == "test_command"
    assert command.action == BLECarServerVehicleAction.GET_CHARGE_STATE
    assert command.domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT


def test_load_polling_parameters_sets_update_interval(tesla_device):
    """Ensure load_polling_parameters updates the base interval."""

    tesla_device.load_polling_parameters(update_interval=42)
    assert tesla_device.update_interval == 42


def test_should_poll_respects_asleep_period(monkeypatch, tesla_device):
    """Sleeping vehicles wait for the asleep interval."""

    tesla_device.vehicle_state = VEHICLE_STATE_ASLEEP
    tesla_device._last_poll_time = 100.0
    tesla_device.update_interval = 5
    tesla_device.poll_asleep_period = 60

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 155.0)
    assert tesla_device.should_poll() is False

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 165.0)
    assert tesla_device.should_poll() is True


def test_should_poll_awake_uses_data_period(monkeypatch, tesla_device):
    """Awake vehicles fall back to the data polling period."""

    tesla_device.vehicle_state = VEHICLE_STATE_AWAKE
    tesla_device._last_poll_time = 100.0
    tesla_device.poll_data_period = 20

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 115.0)
    assert tesla_device.should_poll() is False

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 121.0)
    assert tesla_device.should_poll() is True


def test_should_poll_enforces_minimum_interval(monkeypatch, tesla_device):
    """should_poll must not run more often than update_interval."""

    tesla_device.vehicle_state = VEHICLE_STATE_AWAKE
    tesla_device._last_poll_time = 100.0
    tesla_device.update_interval = 10
    tesla_device.poll_data_period = 20

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 108.0)
    assert tesla_device.should_poll() is False

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 121.0)
    assert tesla_device.should_poll() is True


def test_should_poll_fast_after_wake(monkeypatch, tesla_device):
    """When vehicle recently woke, use post-wake fast polling."""

    tesla_device.vehicle_state = VEHICLE_STATE_AWAKE
    tesla_device._car_just_woken = True
    tesla_device._last_wake_time = 190.0
    tesla_device._last_poll_time = 200.0
    tesla_device.post_wake_poll_time = 120
    tesla_device.poll_data_period = 15

    # First detection of a wake polls immediately, regardless of the interval.
    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 208.0)
    assert tesla_device.should_poll() is True

    # Once that first poll is consumed, the post-wake window uses poll_data_period.
    tesla_device._car_just_woken = False
    assert tesla_device.should_poll() is False

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 216.0)
    assert tesla_device.should_poll() is True


def test_should_poll_charging_period(monkeypatch, tesla_device):
    """Charging vehicles should use charging poll period."""

    tesla_device.vehicle_state = VEHICLE_STATE_AWAKE
    tesla_device._is_charging = True
    tesla_device._last_poll_time = 100.0
    tesla_device.poll_charging_period = 30

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 125.0)
    assert tesla_device.should_poll() is False

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 135.0)
    assert tesla_device.should_poll() is True


def test_should_poll_fast_when_unlocked(monkeypatch, tesla_device):
    """Unlocked vehicles respect fast polling option."""

    tesla_device.vehicle_state = VEHICLE_STATE_AWAKE
    tesla_device.fast_poll_if_unlocked = True
    tesla_device.data["doors_locked"] = False
    tesla_device._last_poll_time = 100.0
    tesla_device.update_interval = 10
    tesla_device.poll_data_period = 60

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 108.0)
    assert tesla_device.should_poll() is False

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 112.0)
    assert tesla_device.should_poll() is True


@pytest.mark.asyncio
async def test_key_manager_initialization(tesla_device):
    """Test key manager initialization."""
    tesla_device._send_session_info_request = AsyncMock()
    tesla_device.key_manager.initialize_keys = AsyncMock()

    # Test initialization
    await tesla_device._initialize_sessions()

    tesla_device.key_manager.initialize_keys.assert_awaited_once()
    tesla_device._send_session_info_request.assert_has_calls(
        [
            call(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY),
            call(UniversalMessageDomain.DOMAIN_INFOTAINMENT),
        ]
    )


@pytest.mark.asyncio
async def test_send_vehicle_action_uses_protocol_client(tesla_device):
    """Ensure vehicle actions are sent via the protocol client."""
    tesla_device.is_connected = True
    tesla_device._connect = AsyncMock()
    tesla_device._write_ble_data = AsyncMock()

    tesla_device.protocol_client.build_carserver_vehicle_action.return_value = b"vehicle"

    await tesla_device.send_vehicle_action(
        BLECarServerVehicleAction.SET_HVAC_SWITCH,
        parameter_bool=True,
    )

    tesla_device.protocol_client.build_carserver_vehicle_action.assert_called_once_with(
        BLECarServerVehicleAction.SET_HVAC_SWITCH,
        parameter=1,
        parameter_bool=True,
        parameter_float=None,
        parameter2=None,
    )
    tesla_device._write_ble_data.assert_called_once_with(b"vehicle")
    # Only the SET_HVAC_SWITCH is outstanding; its follow-up GET is queued later,
    # once the SET response arrives.
    queue_state = tesla_device._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
    assert queue_state.current_command is not None
    assert queue_state.current_command.action == BLECarServerVehicleAction.SET_HVAC_SWITCH
    # peek() promotes a command to current_command without removing it from its
    # deque, so iter_all() yields the same object twice while it is in flight.
    assert {id(c) for c in queue_state.iter_all()} == {id(queue_state.current_command)}
    queue_state.clear()


@pytest.mark.asyncio
async def test_send_vcsec_closure_move(tesla_device):
    """Ensure VCSEC closure moves are built via the protocol client."""
    tesla_device.is_connected = True
    tesla_device._connect = AsyncMock()
    tesla_device._write_ble_data = AsyncMock()

    tesla_device.protocol_client.build_vcsec_closure_move_request.return_value = b"vcsec"

    await tesla_device.send_vcsec_closure_move("frontTrunk", "OPEN")

    tesla_device.protocol_client.build_vcsec_closure_move_request.assert_called_once()
    args, _kwargs = tesla_device.protocol_client.build_vcsec_closure_move_request.call_args
    closure_request = args[0]
    assert (
        closure_request.frontTrunk
        == vcsec_pb2.ClosureMoveType_E.CLOSURE_MOVE_TYPE_OPEN
    )
    tesla_device._write_ble_data.assert_called_once_with(b"vcsec")


@pytest.mark.asyncio
async def test_connect_uses_bleak_retry(monkeypatch, tesla_device):
    """Ensure _connect resolves devices via HA bluetooth helpers."""
    mock_ble_device = MagicMock()

    tesla_device.ble_device = None
    tesla_device.address = "AA:BB:CC:DD:EE:FF"
    tesla_device.protocol_client = MagicMock()
    tesla_device.protocol_client.set_connection_id = MagicMock()

    close_mock = AsyncMock()
    get_device_mock = AsyncMock(return_value=mock_ble_device)
    async_ble_mock = MagicMock(return_value=mock_ble_device)

    monkeypatch.setattr(
        "tesla_ble.device.close_stale_connections_by_address",
        close_mock,
    )
    monkeypatch.setattr(
        "tesla_ble.device.get_device",
        get_device_mock,
    )
    monkeypatch.setattr(
        "tesla_ble.device.bluetooth.async_ble_device_from_address",
        async_ble_mock,
    )

    class FakeClient:
        def __init__(self, device, **_kwargs):
            self.device = device
            self.is_connected = True
            self.mtu_size = 23

        async def start_notify(self, uuid, callback):
            return None

        async def disconnect(self):
            self.is_connected = False

    # _connect goes through bleak_retry_connector.establish_connection, not
    # BleakClient directly; patching the latter let the real connector run and hang.
    establish_mock = AsyncMock(side_effect=lambda cls, device, name, disconnect_cb, **kw: FakeClient(device))
    monkeypatch.setattr("tesla_ble.device.establish_connection", establish_mock)

    await tesla_device._connect()

    establish_mock.assert_awaited_once()

    close_mock.assert_awaited_once_with("AA:BB:CC:DD:EE:FF")
    async_ble_mock.assert_called_once()
    tesla_device.protocol_client.set_connection_id.assert_called_once()
    assert tesla_device.is_connected is True
    assert tesla_device.ble_device is mock_ble_device


@pytest.mark.asyncio
async def test_send_vehicle_action_requests_session_when_invalid(tesla_device):
    """Vehicle actions should request a new session if none is valid."""

    tesla_device.is_connected = True
    tesla_device._connect = AsyncMock()
    tesla_device._write_ble_data = AsyncMock()

    tesla_device.protocol_client.build_carserver_vehicle_action.return_value = b"vehicle"

    tesla_device.key_manager.is_session_valid.side_effect = [False, True]
    tesla_device._send_session_info_request = AsyncMock()

    await tesla_device.send_vehicle_action(
        BLECarServerVehicleAction.SET_HVAC_SWITCH,
        parameter_bool=True,
    )

    tesla_device._send_session_info_request.assert_awaited_with(
        UniversalMessageDomain.DOMAIN_INFOTAINMENT
    )
    tesla_device._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT).clear()


def test_update_signal_strength_tracks_rssi(tesla_device):
    """BLE RSSI updates should be stored for diagnostic sensor."""

    tesla_device.update_signal_strength(-72)
    assert tesla_device.data["ble_rssi"] == -72

    tesla_device.update_signal_strength(None)
    assert tesla_device.data["ble_rssi"] == -72


@pytest.mark.asyncio
async def test_handle_infotainment_response_populates_data(tesla_device):
    """Infotainment responses should map to device telemetry fields."""

    class FakeOneOf:
        def __init__(self, value):
            self._value = value

        def WhichOneof(self, _name):
            return self._value

    class FakeMessage:
        def __init__(self, **fields):
            self._fields = fields
            for key, value in fields.items():
                setattr(self, key, value)

        def HasField(self, name: str) -> bool:
            return name in self._fields

    class FakeResponse:
        def __init__(self, vehicle_data):
            self.vehicleData = vehicle_data

        def WhichOneof(self, _name):
            return "vehicleData"

        def HasField(self, name: str) -> bool:
            return hasattr(self, name)

    charge_state = FakeMessage(
        charging_state=FakeOneOf("Charging"),
        battery_level=80,
        charge_limit_soc=90,
        charger_actual_current=32,
        charger_voltage=240,
        charger_power=7.2,
        battery_range=250.5,
        charge_energy_added=5.4,
        charge_miles_added_ideal=18.0,
        minutes_to_charge_limit=30,
        charging_amps=32,
        charge_current_request=40,
        charge_port_door_open=True,
    )

    climate_state = FakeMessage(
        is_climate_on=True,
        inside_temp_celsius=21.5,
        outside_temp_celsius=10.2,
        defrost_mode=FakeOneOf("Normal"),
        is_preconditioning=True,
        steering_wheel_heater=True,
    )

    drive_state = FakeMessage(
        shift_state=FakeOneOf("Drive"),
        odometer_in_hundredths_of_a_mile=123456,
        speed_float=35.5,
        power=12,
    )

    location_state = FakeMessage(
        latitude=51.5,
        longitude=-0.13,
        heading=180,
        gps_as_of=1690000000,
    )

    closures_state = FakeMessage(
        door_open_trunk_rear=True,
        door_open_trunk_front=False,
        locked=False,
        is_user_present=True,
        window_open_driver_front=True,
        door_open_driver_front=True,
        door_open_driver_rear=False,
        door_open_passenger_front=True,
        door_open_passenger_rear=False,
        sentry_mode_state=FakeOneOf("Armed"),
    )

    vehicle_data = FakeMessage(
        charge_state=charge_state,
        climate_state=climate_state,
        drive_state=drive_state,
        location_state=location_state,
        closures_state=closures_state,
    )

    parsed = ParsedCarServerResponse(response=FakeResponse(vehicle_data), fault=0)
    tesla_device._complete_domain_command = MagicMock()
    infotainment_queue = tesla_device._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
    infotainment_queue.add_command(
        BLECommand(
            execute_name="vehicle_action_SET_HVAC_SWITCH",
            action=BLECarServerVehicleAction.SET_HVAC_SWITCH,
            domain=UniversalMessageDomain.DOMAIN_INFOTAINMENT,
            state=BLECommandState.WAITING_FOR_RESPONSE,
        ),
        priority=0,
    )
    infotainment_queue.peek()  # promote to current_command, as the queue runner does

    await tesla_device._handle_infotainment_response(parsed)

    assert tesla_device.data["charging_state"] == CHARGING_STATE_CHARGING
    assert tesla_device.data["charge_energy_added"] == 5.4
    assert tesla_device.data["charge_miles_added"] == 18.0
    assert tesla_device.data["minutes_to_limit"] == 30
    assert tesla_device.data["steering_wheel_heater"] is True
    assert tesla_device.data["defrost_active"] is True
    assert tesla_device.data["is_trunk_open"] is True
    assert tesla_device.data["windows_open"] is True
    assert tesla_device.data["sentry_mode"] is True
    assert tesla_device.data["is_preconditioning"] is True
    assert tesla_device.data["driver_front_door_open"] is True
    assert tesla_device.data["driver_rear_door_open"] is False
    assert tesla_device.data["passenger_front_door_open"] is True
    assert tesla_device.data["passenger_rear_door_open"] is False
    # NOTE: speed / lat / lon / heading / gps_as_of are deliberately not asserted.
    # _handle_infotainment_response does not parse location_state and extracts no
    # speed field from drive_state, and no entity exposes them, so these were dead
    # assertions on behaviour the integration has never implemented.
    assert tesla_device.data["defrost_mode"] == "Normal"
    assert tesla_device.data["sentry_mode_state"] == "Armed"
    assert infotainment_queue.current_command.state == BLECommandState.WAITING_FOR_GET_POST_SET
    tesla_device._complete_domain_command.assert_not_called()
    infotainment_queue.clear()


@pytest.mark.asyncio
async def test_handle_vcsec_response_decrypts_encrypted_payload(tesla_device):
    """Encrypted VCSEC responses should be decrypted before parsing."""

    session = object()
    tesla_device.key_manager.get_session.return_value = session

    decrypted_message = vcsec_pb2.FromVCSECMessage()
    decrypted_message.vehicleStatus.vehicleSleepStatus = (
        vcsec_pb2.VehicleSleepStatus_E.VEHICLE_SLEEP_STATUS_AWAKE
    )
    decrypted_message.vehicleStatus.vehicleLockState = (
        vcsec_pb2.VehicleLockState_E.VEHICLELOCKSTATE_LOCKED
    )
    decrypted_message.vehicleStatus.userPresence = (
        vcsec_pb2.UserPresence_E.VEHICLE_USER_PRESENCE_PRESENT
    )
    decrypted_bytes = decrypted_message.SerializeToString()

    tesla_device.key_manager.decrypt_payload.return_value = decrypted_bytes

    routable = universal_message_pb2.RoutableMessage()
    routable.from_destination.domain = UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY
    routable.to_destination.domain = UniversalMessageDomain.DOMAIN_BROADCAST
    routable.flags = 1
    signature_data = routable.signature_data.AES_GCM_Response_data
    signature_data.nonce = b"0" * 12
    signature_data.tag = b"1" * 16
    routable.protobuf_message_as_bytes = b"encrypted"

    await tesla_device._handle_vcsec_response(decrypted_message, routable)

    tesla_device.key_manager.decrypt_payload.assert_called_once_with(
        int(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY),
        b"encrypted",
        signature_data.nonce,
        signature_data.tag,
        0,
        0,
        routable.flags,
    )
    assert tesla_device.vehicle_state == "awake"
    assert tesla_device.data["doors_locked"] is True


@pytest.mark.asyncio
async def test_handle_vcsec_wait_updates_pairing_reason(tesla_device):
    """WAIT responses during pairing should record failure reasons."""

    tesla_device.key_manager.get_session.return_value = object()

    vcsec_message = vcsec_pb2.FromVCSECMessage()
    status = vcsec_message.commandStatus
    status.operationStatus = vcsec_pb2.OperationStatus_E.OPERATIONSTATUS_WAIT
    status.whitelistOperationStatus.operationStatus = (
        vcsec_pb2.OperationStatus_E.OPERATIONSTATUS_WAIT
    )
    status.whitelistOperationStatus.whitelistOperationInformation = (
        vcsec_pb2.WhitelistOperation_information_E.WHITELISTOPERATION_INFORMATION_LOCAL_ENTITY_AUTH_FAILED_TIMED_OUT_WAITING_FOR_TAP
    )

    routable = universal_message_pb2.RoutableMessage()
    routable.from_destination.domain = UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY
    routable.to_destination.domain = UniversalMessageDomain.DOMAIN_BROADCAST
    routable.protobuf_message_as_bytes = vcsec_message.SerializeToString()

    await tesla_device._handle_vcsec_response(vcsec_message, routable)

    assert tesla_device.pairing_failure_reason == "pairing_tap_timeout"
    assert tesla_device._pairing_complete is False


@pytest.mark.asyncio
async def test_pair_key_timeout_reports_wait_reason(monkeypatch, tesla_device):
    """pair_key should surface stored wait reasons on timeout."""

    tesla_device.is_connected = True
    tesla_device._connect = AsyncMock()
    tesla_device._initialize_crypto = AsyncMock()
    tesla_device.key_manager.initialize_keys = AsyncMock()

    async def fake_write(_data):
        tesla_device._pairing_wait_info = (
            vcsec_pb2.WhitelistOperation_information_E.WHITELISTOPERATION_INFORMATION_LOCAL_ENTITY_AUTH_FAILED_TIMED_OUT_WAITING_FOR_TAP
        )
        tesla_device._pairing_failure_reason = tesla_device._pairing_reason_from_info(
            tesla_device._pairing_wait_info
        )

    tesla_device._write_ble_data = AsyncMock(side_effect=fake_write)

    start_time = 1000.0
    times = [start_time, start_time + 1]

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: times.pop(0))

    async def fake_sleep(_delay):
        return None

    monkeypatch.setattr("tesla_ble.device.asyncio.sleep", fake_sleep)

    result = await tesla_device.pair_key(timeout=0.5)

    assert result is False
    assert tesla_device.pairing_failure_reason == "pairing_tap_timeout"


@pytest.mark.asyncio
async def test_session_info_triggers_persistence(tesla_device):
    """Session info updates should prompt state persistence."""

    session_info = signatures_pb2.SessionInfo()
    session_info.publicKey = b"\x01" * 65
    session_info.counter = 5
    session_info.handle = 1
    session_info.status = 0
    session_info.clock_time = 10
    session_info.epoch = b"\x02" * 16

    message = MagicMock()
    message.WhichOneof.return_value = "session_info"
    message.session_info = session_info.SerializeToString()
    message.HasField.return_value = False

    tesla_device._persistent_state_loaded = True
    tesla_device._schedule_state_save = MagicMock()
    tesla_device.key_manager.serialize_sessions.return_value = {"2": "c2Vzcw=="}

    await tesla_device._handle_session_info_response(
        UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
        message,
    )

    tesla_device.key_manager.update_session_from_info.assert_called_once()
    tesla_device._schedule_state_save.assert_called_once()
    assert tesla_device._session_blobs == {"2": "c2Vzcw=="}


def test_entity_unique_id_and_update(monkeypatch):
    """TeslaBleEntity should slug device name for unique_id and refresh data."""

    class DummyDevice:
        def __init__(self) -> None:
            self.data = {}

        def is_available(self) -> bool:
            return True

    class DummyCoordinator:
        def __init__(self) -> None:
            self.device_name = "Test Vehicle"
            self.entry_id = "1234567890abcdef"
            self.base_unique_id = "1234567890abcdef"
            self.ble_device = MagicMock(address="AA:BB:CC:DD:EE:FF")
            self.device = DummyDevice()

    coordinator = DummyCoordinator()

    class DummyEntity(TeslaBleEntity):
        def __init__(self) -> None:
            super().__init__(
                coordinator,
                "charge_level",
                translation_key="charge_level",
            )
            self.async_write_ha_state = MagicMock()

        @property
        def native_value(self):  # pragma: no cover - simple accessor
            return getattr(self, "_native_value", None)

        def _handle_coordinator_update(self) -> None:
            self._native_value = coordinator.device.data.get("charge_level")
            self.async_write_ha_state()

    entity = DummyEntity()

    assert entity.unique_id.startswith(f"{coordinator.base_unique_id}_")
    assert entity.unique_id.endswith("charge_level")
    assert getattr(entity, "_attr_translation_key") == "charge_level"

    coordinator.device.data["charge_level"] = 82
    entity._handle_coordinator_update()
    assert entity.native_value == 82
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_send_vcsec_closure_move_requests_session_when_invalid(tesla_device):
    """VCSEC closure moves should request a session when needed."""

    tesla_device.is_connected = True
    tesla_device._connect = AsyncMock()
    tesla_device._write_ble_data = AsyncMock()
    tesla_device.protocol_client.build_vcsec_closure_move_request.return_value = b"vcsec"

    tesla_device.key_manager.is_session_valid.side_effect = [False, True]
    tesla_device._send_session_info_request = AsyncMock()

    await tesla_device.send_vcsec_closure_move("frontTrunk", "OPEN")

    tesla_device._send_session_info_request.assert_awaited_with(
        UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY
    )


@pytest.mark.asyncio
async def test_write_ble_chunk_falls_back_to_no_response(tesla_device):
    """A write-with-response rejection retries the same chunk without response."""

    chunk = b"\x01\x02"

    client = MagicMock()
    client.is_connected = True
    client.write_gatt_char = AsyncMock(
        side_effect=[
            BleakError("Characteristic does not support write-with-response"),
            None,
        ]
    )
    client.disconnect = AsyncMock()

    tesla_device._client = client
    tesla_device._connect = AsyncMock()

    await tesla_device._write_ble_chunk(chunk)

    assert client.write_gatt_char.await_args_list == [
        call(WRITE_UUID, chunk, response=True),
        call(WRITE_UUID, chunk, response=False),
    ]
    assert tesla_device._write_with_response is False
    # _write_ble_chunk must never establish a connection: doing so mid-message
    # would deliver the tail of a message on a different link.
    tesla_device._connect.assert_not_awaited()
    assert tesla_device._client is client


@pytest.mark.asyncio
async def test_write_ble_chunk_raises_after_max_attempts(tesla_device):
    """Write chunk should raise once its attempts are exhausted."""

    client = MagicMock()
    client.is_connected = True
    client.write_gatt_char = AsyncMock(side_effect=BleakError("boom"))
    client.disconnect = AsyncMock()

    tesla_device._client = client
    tesla_device._connect = AsyncMock()

    with pytest.raises(RuntimeError):
        await tesla_device._write_ble_chunk(b"\x01\x02")

    assert client.write_gatt_char.await_count == BLE_WRITE_MAX_ATTEMPTS
    client.write_gatt_char.assert_awaited_with(WRITE_UUID, b"\x01\x02", response=True)
    tesla_device._connect.assert_not_awaited()
    assert tesla_device._write_with_response is True


@pytest.mark.asyncio
async def test_write_ble_chunk_raises_when_link_drops(tesla_device):
    """A chunk write must fail fast rather than silently reconnecting."""

    tesla_device._client = None

    with pytest.raises(BleakError):
        await tesla_device._write_ble_chunk(b"\x01\x02")


@pytest.mark.asyncio
async def test_waiting_for_wake_exponential_backoff(tesla_device):
    """Wake retries should expand delay up to the configured maximum."""

    command = BLECommand(
        execute_name="vehicle_action_TEST",
        action=BLECarServerVehicleAction.SET_HVAC_SWITCH,
        domain=UniversalMessageDomain.DOMAIN_INFOTAINMENT,
        state=BLECommandState.WAITING_FOR_WAKE,
    )
    command.last_tx_at = time.time() - WAKE_RETRY_INTERVAL - 0.1
    command.retry_delay = WAKE_RETRY_INTERVAL
    tesla_device.data["is_asleep"] = True
    tesla_device.wake_vehicle = AsyncMock(return_value=True)

    result = await tesla_device._process_command_state(command, time.time())

    assert result is False
    assert command.retry_count == 1
    assert command.retry_delay == min(WAKE_RETRY_INTERVAL * 2, WAKE_RETRY_MAX_DELAY)
    tesla_device.wake_vehicle.assert_awaited_once()


@pytest.mark.asyncio
async def test_waiting_for_auth_exponential_backoff(tesla_device):
    """Session auth retries should use exponential backoff."""

    command = BLECommand(
        execute_name="vehicle_action_TEST",
        action=BLECarServerVehicleAction.GET_CHARGE_STATE,
        domain=UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
        state=BLECommandState.WAITING_FOR_VCSEC_AUTH,
    )
    command.last_tx_at = time.time() - SESSION_RETRY_INTERVAL - 0.1
    command.retry_delay = SESSION_RETRY_INTERVAL
    tesla_device.key_manager.is_session_valid.return_value = False
    tesla_device._send_session_info_request = AsyncMock()

    result = await tesla_device._process_command_state(command, time.time())

    assert result is False
    assert command.retry_count == 1
    assert command.retry_delay == min(SESSION_RETRY_INTERVAL * 2, SESSION_RETRY_MAX_DELAY)
    tesla_device._send_session_info_request.assert_awaited_with(
        UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY
    )


# ---------------------------------------------------------------------------
# Proxy rotation: deliberate flips, exponential backoff, graceful release
# ---------------------------------------------------------------------------


def _scanner_device(source, rssi, *, connectable=True):
    """Build a fake HA scanner-device entry for _select_alternate_proxy_device."""
    return SimpleNamespace(
        scanner=SimpleNamespace(source=source, connectable=connectable),
        advertisement=SimpleNamespace(rssi=rssi),
        ble_device=SimpleNamespace(address="AA:BB:CC:DD:EE:FF"),
    )


def test_proxy_cooldown_backoff_is_exponential_and_capped(tesla_device):
    """Each consecutive failure benches a proxy longer, up to the cap."""
    tesla_device._proxy_fail_streaks = {"p": 1}
    assert tesla_device._proxy_cooldown_duration("p") == 90.0
    tesla_device._proxy_fail_streaks = {"p": 2}
    assert tesla_device._proxy_cooldown_duration("p") == 180.0
    tesla_device._proxy_fail_streaks = {"p": 3}
    assert tesla_device._proxy_cooldown_duration("p") == 360.0
    tesla_device._proxy_fail_streaks = {"p": 99}
    assert tesla_device._proxy_cooldown_duration("p") == 600.0  # capped at PROXY_COOLDOWN_MAX


def test_proxy_rotation_benches_failing_proxy_then_flips(monkeypatch, tesla_device):
    """The failing current proxy is benched (monotonic backoff) and we flip to the other."""
    tesla_device.address = "AA:BB:CC:DD:EE:FF"
    tesla_device._current_proxy_source = "proxyA"
    sds = [_scanner_device("proxyA", -50), _scanner_device("proxyB", -70)]
    monkeypatch.setattr(
        "tesla_ble.device.bluetooth.async_scanner_devices_by_address",
        lambda *a, **k: sds,
        raising=False,
    )
    monkeypatch.setattr("tesla_ble.device.time.monotonic", lambda: 1000.0)

    chosen = tesla_device._select_alternate_proxy_device()

    # Flipped to B even though A had the stronger RSSI, because A is now benched.
    assert tesla_device._current_proxy_source == "proxyB"
    assert chosen is sds[1].ble_device
    assert tesla_device._proxy_fail_streaks["proxyA"] == 1
    assert tesla_device._proxy_cooldowns["proxyA"] == 1000.0 + 90.0


def test_proxy_rotation_single_proxy_does_not_flip(monkeypatch, tesla_device):
    """With only one proxy reaching the car there is nothing to flip to."""
    tesla_device.address = "AA:BB:CC:DD:EE:FF"
    monkeypatch.setattr(
        "tesla_ble.device.bluetooth.async_scanner_devices_by_address",
        lambda *a, **k: [_scanner_device("proxyA", -50)],
        raising=False,
    )
    assert tesla_device._select_alternate_proxy_device() is None


def test_proxy_rotation_releases_only_soonest_when_all_cooling(monkeypatch, tesla_device):
    """When every proxy is benched we release ONLY the soonest-expiring one, not all."""
    tesla_device.address = "AA:BB:CC:DD:EE:FF"
    tesla_device._current_proxy_source = None  # skip benching-on-entry for a clean assertion
    sds = [_scanner_device("proxyA", -50), _scanner_device("proxyB", -80)]
    monkeypatch.setattr(
        "tesla_ble.device.bluetooth.async_scanner_devices_by_address",
        lambda *a, **k: sds,
        raising=False,
    )
    monkeypatch.setattr("tesla_ble.device.time.monotonic", lambda: 1000.0)
    # Both still cooling; A expires sooner than B.
    tesla_device._proxy_cooldowns = {"proxyA": 1050.0, "proxyB": 1200.0}

    chosen = tesla_device._select_alternate_proxy_device()

    # Only proxyA released (soonest); proxyB stays benched — no clear-all thrash.
    assert "proxyA" not in tesla_device._proxy_cooldowns
    assert tesla_device._proxy_cooldowns.get("proxyB") == 1200.0
    assert tesla_device._current_proxy_source == "proxyA"
    assert chosen is sds[0].ble_device


# ---------------------------------------------------------------------------
# Sleep inference: never report "asleep" when the cause is a connection failure
# ---------------------------------------------------------------------------


def test_stale_with_connection_failures_flags_unreachable_not_asleep(monkeypatch, tesla_device):
    """VCSEC silence WITH connect failures => unreachable, last sleep state untouched."""
    tesla_device.data["is_asleep"] = False
    tesla_device.data["ble_unreachable"] = False
    tesla_device.vehicle_state = VEHICLE_STATE_AWAKE
    tesla_device._last_vcsec_update = 1000.0
    tesla_device._consecutive_connection_failures = 3
    monkeypatch.setattr("tesla_ble.device.time.monotonic", lambda: 1000.0 + 200.0)  # > 180s

    tesla_device._assume_asleep_if_vcsec_stale()

    assert tesla_device.data["ble_unreachable"] is True
    assert tesla_device.data["is_asleep"] is False  # not a lie about a possibly-charging car
    assert tesla_device.vehicle_state == VEHICLE_STATE_AWAKE


def test_stale_without_failures_assumes_asleep(monkeypatch, tesla_device):
    """VCSEC silence with NO connect failures keeps the legacy assume-asleep behavior."""
    tesla_device.data["is_asleep"] = False
    tesla_device.data["ble_unreachable"] = False
    tesla_device.vehicle_state = VEHICLE_STATE_AWAKE
    tesla_device._last_vcsec_update = 1000.0
    tesla_device._consecutive_connection_failures = 0
    monkeypatch.setattr("tesla_ble.device.time.monotonic", lambda: 1000.0 + 200.0)

    tesla_device._assume_asleep_if_vcsec_stale()

    assert tesla_device.data["is_asleep"] is True
    assert tesla_device.vehicle_state == VEHICLE_STATE_ASLEEP
    assert tesla_device.data["ble_unreachable"] is False


def test_not_stale_yet_leaves_state_unchanged(monkeypatch, tesla_device):
    """Within the staleness window nothing is inferred either way."""
    tesla_device.data["is_asleep"] = False
    tesla_device.data["ble_unreachable"] = False
    tesla_device._last_vcsec_update = 1000.0
    tesla_device._consecutive_connection_failures = 3
    monkeypatch.setattr("tesla_ble.device.time.monotonic", lambda: 1000.0 + 60.0)  # < 180s

    tesla_device._assume_asleep_if_vcsec_stale()

    assert tesla_device.data["ble_unreachable"] is False
    assert tesla_device.data["is_asleep"] is False
