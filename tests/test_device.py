"""Test Tesla BLE device."""
from datetime import datetime, timezone
import sys
import time
from types import ModuleType, SimpleNamespace
from typing import Generic, TypeVar
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from bleak_retry_connector import BleakError


def _ensure_homeassistant_stubs() -> None:
    for mod_name in list(sys.modules):
        if mod_name.startswith("homeassistant"):
            sys.modules.pop(mod_name)

    ha_module = ModuleType("homeassistant")
    sys.modules["homeassistant"] = ha_module

    components_module = ModuleType("homeassistant.components")
    components_module.__path__ = []  # treat as package for submodule imports
    components_module.__package__ = "homeassistant"
    import importlib.machinery
    components_module.__spec__ = importlib.machinery.ModuleSpec(
        "homeassistant.components", loader=None, is_package=True
    )
    bluetooth_module = ModuleType("homeassistant.components.bluetooth")
    bluetooth_module.async_ble_device_from_address = lambda *args, **kwargs: None
    bluetooth_module.async_track_unavailable = lambda *args, **kwargs: None
    bluetooth_module.BluetoothChange = object
    bluetooth_module.BluetoothServiceInfoBleak = object
    bluetooth_module.BluetoothScanningMode = SimpleNamespace(ACTIVE="active", PASSIVE="passive")

    sys.modules["homeassistant.components"] = components_module
    sys.modules["homeassistant.components.bluetooth"] = bluetooth_module
    components_module.bluetooth = bluetooth_module

    core_module = ModuleType("homeassistant.core")
    core_module.HomeAssistant = object
    def _callback(func):
        return func
    core_module.callback = _callback
    sys.modules["homeassistant.core"] = core_module

    helpers_module = ModuleType("homeassistant.helpers")
    storage_module = ModuleType("homeassistant.helpers.storage")

    class _Store:
        def __init__(self, *args, **kwargs):
            self.data = None

        async def async_load(self):
            return self.data

        async def async_save(self, data):
            self.data = data

    storage_module.Store = _Store
    sys.modules["homeassistant.helpers"] = helpers_module
    sys.modules["homeassistant.helpers.storage"] = storage_module
    helpers_module.storage = storage_module

    config_entries_module = ModuleType("homeassistant.config_entries")
    config_entries_module.ConfigEntry = object
    sys.modules["homeassistant.config_entries"] = config_entries_module

    const_module = ModuleType("homeassistant.const")
    const_module.Platform = SimpleNamespace(
        BINARY_SENSOR="binary_sensor",
        BUTTON="button",
        COVER="cover",
        LOCK="lock",
        NUMBER="number",
        SENSOR="sensor",
        SWITCH="switch",
    )
    const_module.ATTR_CONNECTIONS = "connections"
    sys.modules["homeassistant.const"] = const_module

    device_registry_module = ModuleType("homeassistant.helpers.device_registry")
    device_registry_module.DeviceInfo = dict
    device_registry_module.CONNECTION_BLUETOOTH = "bluetooth"
    device_registry_module.CONNECTION_NETWORK_MAC = "network_mac"
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module

    sensor_module = ModuleType("homeassistant.components.sensor")

    class _SensorEntity:
        def __init__(self, *args, **kwargs):
            self._attr_native_value = None

        @property
        def native_value(self):
            return self._attr_native_value

        @native_value.setter
        def native_value(self, value):
            self._attr_native_value = value

        def __getattr__(self, item):  # pragma: no cover - minimal stub
            raise AttributeError(item)

    sensor_module.SensorEntity = _SensorEntity
    sensor_module.SensorEntityDescription = object
    sensor_module.SensorDeviceClass = SimpleNamespace(
        BATTERY="battery",
        DISTANCE="distance",
        ENUM="enum",
        CURRENT="current",
        VOLTAGE="voltage",
        POWER="power",
        ENERGY="energy",
        DURATION="duration",
        TEMPERATURE="temperature",
        SPEED="speed",
        SIGNAL_STRENGTH="signal_strength",
        TIMESTAMP="timestamp",
    )
    sensor_module.SensorStateClass = SimpleNamespace(MEASUREMENT="measurement", TOTAL_INCREASING="total_increasing")
    sensor_module.__package__ = "homeassistant.components"
    sensor_module.__file__ = __file__
    sensor_module.__spec__ = importlib.machinery.ModuleSpec(
        "homeassistant.components.sensor", loader=None, is_package=False
    )

    sys.modules["homeassistant.components.sensor"] = sensor_module
    components_module.sensor = sensor_module

    passive_module = ModuleType(
        "homeassistant.components.bluetooth.passive_update_coordinator"
    )
    passive_module.__package__ = "homeassistant.components.bluetooth"
    import importlib.machinery
    passive_module.__spec__ = importlib.machinery.ModuleSpec(
        "homeassistant.components.bluetooth.passive_update_coordinator",
        loader=None,
        is_package=False,
    )

    _T = TypeVar("_T")

    class _PassiveEntity(Generic[_T]):
        def __init__(self, coordinator):
            self.coordinator = coordinator
            self._attr_unique_id = None

        @classmethod
        def __class_getitem__(cls, _item):  # pragma: no cover
            return cls

        @property
        def unique_id(self):  # pragma: no cover
            return self._attr_unique_id

    passive_module.PassiveBluetoothCoordinatorEntity = _PassiveEntity
    sys.modules[
        "homeassistant.components.bluetooth.passive_update_coordinator"
    ] = passive_module

    exceptions_module = ModuleType("homeassistant.exceptions")
    class _HomeAssistantError(Exception):
        pass
    exceptions_module.HomeAssistantError = _HomeAssistantError
    sys.modules["homeassistant.exceptions"] = exceptions_module

    ha_module.components = components_module
    ha_module.core = core_module
    ha_module.helpers = helpers_module
    ha_module.config_entries = config_entries_module
    ha_module.const = const_module

    util_module = ModuleType("homeassistant.util")
    util_module.slugify = lambda value: str(value).lower().replace(" ", "_").replace("'", "")
    sys.modules["homeassistant.util"] = util_module
    ha_module.util = util_module


_ensure_homeassistant_stubs()

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
    await tesla_device._queue_command(
        "test_command",
        BLECarServerVehicleAction.GET_CHARGE_STATE,
        UniversalMessageDomain.DOMAIN_INFOTAINMENT
    )

    assert len(tesla_device._command_queue) == 1
    command = tesla_device._command_queue[0]
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

    monkeypatch.setattr("tesla_ble.device.time.time", lambda: 208.0)
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
    # Initially only one command should be queued (the SET_HVAC_SWITCH)
    assert len(tesla_device._command_queue) == 1
    assert tesla_device._command_queue[0].action == BLECarServerVehicleAction.SET_HVAC_SWITCH
    tesla_device._command_queue.clear()


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
            self.is_connected = False

        async def connect(self, timeout=None, **_kwargs):
            self.is_connected = True

        async def start_notify(self, uuid, callback):
            return None

        async def disconnect(self):
            self.is_connected = False

    monkeypatch.setattr("tesla_ble.device.BleakClient", FakeClient)

    await tesla_device._connect()

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
    tesla_device._command_queue.clear()


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
    tesla_device._command_queue.append(
        BLECommand(
            execute_name="vehicle_action_SET_HVAC_SWITCH",
            action=BLECarServerVehicleAction.SET_HVAC_SWITCH,
            domain=UniversalMessageDomain.DOMAIN_INFOTAINMENT,
            state=BLECommandState.WAITING_FOR_RESPONSE,
        )
    )

    await tesla_device._handle_infotainment_response(parsed)

    assert tesla_device.data["charging_state"] == CHARGING_STATE_CHARGING
    assert tesla_device.data["charge_energy_added"] == 5.4
    assert tesla_device.data["charge_miles_added"] == 18.0
    assert tesla_device.data["minutes_to_limit"] == 30
    assert tesla_device.data["steering_wheel_heater"] is True
    assert tesla_device.data["defrost_active"] is True
    assert tesla_device.data["is_boot_open"] is True
    assert tesla_device.data["windows_open"] is True
    assert tesla_device.data["sentry_mode"] is True
    assert tesla_device.data["is_preconditioning"] is True
    assert tesla_device.data["driver_front_door_open"] is True
    assert tesla_device.data["driver_rear_door_open"] is False
    assert tesla_device.data["passenger_front_door_open"] is True
    assert tesla_device.data["passenger_rear_door_open"] is False
    assert tesla_device.data["vehicle_speed"] == 35.5
    assert tesla_device.data["latitude"] == 51.5
    assert tesla_device.data["longitude"] == -0.13
    assert tesla_device.data["heading"] == 180
    assert tesla_device.data["gps_as_of"] == datetime.fromtimestamp(1690000000, timezone.utc)
    assert tesla_device.data["defrost_mode"] == "Normal"
    assert tesla_device.data["sentry_mode_state"] == "Armed"
    assert tesla_device._command_queue[0].state == BLECommandState.WAITING_FOR_GET_POST_SET
    tesla_device._complete_domain_command.assert_not_called()
    tesla_device._command_queue.clear()


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
            self.device_name = "Daniel's Model Y"
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

    assert entity.unique_id.startswith("daniels_model_y_")
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
    """Write failures should fall back to write-without-response after retry."""

    chunk = b"\x01\x02"

    client1 = MagicMock()
    client1.is_connected = True
    client1.write_gatt_char = AsyncMock(side_effect=BleakError("Characteristic does not support write-with-response"))
    client1.disconnect = AsyncMock()

    client2 = MagicMock()
    client2.is_connected = True
    client2.write_gatt_char = AsyncMock(return_value=None)
    client2.disconnect = AsyncMock()

    async def set_client2():
        tesla_device._client = client2

    tesla_device._client = client1
    tesla_device._connect = AsyncMock(side_effect=set_client2)

    await tesla_device._write_ble_chunk(chunk)

    assert client1.write_gatt_char.await_args_list == [
        call(WRITE_UUID, chunk, response=True),
        call(WRITE_UUID, chunk, response=False),
    ]
    client1.disconnect.assert_awaited_once()
    tesla_device._connect.assert_awaited_once()
    assert tesla_device._write_with_response is False
    assert tesla_device._client is client2


@pytest.mark.asyncio
async def test_write_ble_chunk_raises_after_max_attempts(tesla_device):
    """Write chunk should raise after exhausting retries."""

    attempts: list[MagicMock] = []

    async def connect_side_effect():
        client = MagicMock()
        client.is_connected = True
        client.write_gatt_char = AsyncMock(side_effect=BleakError("boom"))
        client.disconnect = AsyncMock()
        attempts.append(client)
        tesla_device._client = client

    tesla_device._client = None
    tesla_device._connect = AsyncMock(side_effect=connect_side_effect)

    with pytest.raises(RuntimeError):
        await tesla_device._write_ble_chunk(b"\x01\x02")

    assert tesla_device._connect.await_count == BLE_WRITE_MAX_ATTEMPTS
    for client in attempts:
        client.write_gatt_char.assert_awaited_once_with(WRITE_UUID, b"\x01\x02", response=True)
        client.disconnect.assert_awaited_once()
    assert tesla_device._write_with_response is True
    assert tesla_device._client is None


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
