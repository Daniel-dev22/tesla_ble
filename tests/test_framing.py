"""Regression tests for BLE framing, buffer lifecycle and write atomicity.

Each test here locks down one root cause of the decode-failure storm that
produced ~29,000 `Failed to decode UniversalMessage` errors over 19 days.
Against the pre-fix code the first two tests hang or fail outright.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ha_stubs import install_homeassistant_stubs

install_homeassistant_stubs()

from ..device import (
    DECODE_RECOVERY_COOLDOWN,
    MAX_RX_BUFFER,
    BLE_DEFAULT_CHUNK_SIZE,
    TeslaBleDevice,
)
from ..messages import MAX_MESSAGE_LENGTH, FramingError, TeslaMessageDecoder
from .fake_vehicle import FakeTeslaVehicle, build_message, frame


TEST_VIN = "TEST123456789ABCD"


@pytest.fixture
def device():
    """A device wired to a fake vehicle, with crypto and routing stubbed out."""
    dev = TeslaBleDevice(
        ble_device=MagicMock(address="AA:BB:CC:DD:EE:FF"),
        vin=TEST_VIN,
    )
    dev.hass = None
    dev.key_manager = MagicMock()
    dev.protocol_client = MagicMock()
    # Framing is what's under test; routing/decryption of the decoded message is not.
    dev._handle_universal_message = AsyncMock()
    return dev


async def _drain_tasks(turns: int = 3) -> None:
    """Let tasks spawned via _spawn_task actually run."""
    import asyncio

    for _ in range(turns):
        await asyncio.sleep(0)


async def _attach(device, vehicle):
    device._client = vehicle
    device.is_connected = True
    device._notifications_started = True
    await vehicle.start_notify(None, device._handle_notification)


# --------------------------------------------------------------------------
# Root cause A: the receive buffer could never resynchronise
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_garbage_prefix_resynchronises_and_delivers_frame(device):
    """Garbage ahead of a valid frame must not swallow the frame stream forever.

    The old code deleted ONE byte per failed decode and returned, while each
    notification appended up to 20 — a guaranteed livelock. This is the
    regression lock for that bug.
    """
    vehicle = FakeTeslaVehicle()
    await _attach(device, vehicle)

    await vehicle.notify_garbage(8)
    # The garbage alone must not be left festering in the buffer.
    assert len(device._response_buffer) < 8

    await vehicle.notify_message(build_message(request_uuid=b"abc"))

    assert device._handle_universal_message.await_count == 1
    delivered = device._handle_universal_message.await_args[0][0]
    assert delivered.request_uuid == b"abc"
    assert len(device._response_buffer) == 0


@pytest.mark.asyncio
async def test_sustained_garbage_does_not_grow_the_buffer(device):
    """Continuous garbage must not accumulate — the old code grew ~19 bytes/packet."""
    vehicle = FakeTeslaVehicle()
    await _attach(device, vehicle)

    for _ in range(50):
        await vehicle.notify_garbage(20)

    assert len(device._response_buffer) <= MAX_RX_BUFFER
    # And a real frame still gets through afterwards.
    await vehicle.notify_message(build_message(request_uuid=b"after"))
    assert device._handle_universal_message.await_count == 1


@pytest.mark.asyncio
async def test_buffer_is_capped(device):
    """A stream of plausible-but-never-complete frames cannot grow without bound."""
    vehicle = FakeTeslaVehicle()
    await _attach(device, vehicle)

    # Promises MAX_MESSAGE_LENGTH bytes, then dribbles; never completes.
    header = MAX_MESSAGE_LENGTH.to_bytes(2, "big")
    await vehicle.notify_raw(header + b"\x00" * 100)
    for _ in range(200):
        await vehicle.notify_raw(b"\x00" * 100)

    assert len(device._response_buffer) <= MAX_RX_BUFFER


# --------------------------------------------------------------------------
# Root cause C: unbounded length prefix stalled the buffer silently
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prefix",
    [b"\xff\xff", b"\x00\x00", (MAX_MESSAGE_LENGTH + 1).to_bytes(2, "big")],
    ids=["max-uint16", "zero-length", "one-over-cap"],
)
def test_implausible_length_prefix_raises_framing_error(prefix):
    """An implausible prefix must resync, not wait for bytes that never come."""
    decoder = TeslaMessageDecoder()
    with pytest.raises(FramingError):
        decoder.decode_universal_message(prefix + b"\x00" * 10)


def test_incomplete_frame_still_waits():
    """A plausible, merely-incomplete frame must NOT be treated as a desync."""
    from ..messages import IncompleteMessageError

    decoder = TeslaMessageDecoder()
    payload = build_message().SerializeToString()
    with pytest.raises(IncompleteMessageError):
        decoder.decode_universal_message(frame(payload)[:-1])


def test_malformed_payload_raises_framing_error():
    """A well-sized frame whose body is not a RoutableMessage must resync."""
    decoder = TeslaMessageDecoder()
    # Field 1 declared as length-delimited with a length that overruns the payload.
    with pytest.raises(FramingError):
        decoder.decode_universal_message(frame(b"\x0a\x7f\x01"))


@pytest.mark.asyncio
async def test_split_frame_across_notifications_is_reassembled(device):
    """The happy path: one frame arriving in several notifications still decodes."""
    vehicle = FakeTeslaVehicle(mtu_size=23)
    await _attach(device, vehicle)

    message = build_message(request_uuid=b"split-me")
    await vehicle.notify_message(message)

    assert device._handle_universal_message.await_count == 1
    assert device._handle_universal_message.await_args[0][0].request_uuid == b"split-me"
    assert len(device._response_buffer) == 0


@pytest.mark.asyncio
async def test_two_frames_in_one_notification(device):
    """Back-to-back frames in a single notification must both be delivered."""
    vehicle = FakeTeslaVehicle(mtu_size=512)
    await _attach(device, vehicle)

    a = frame(build_message(request_uuid=b"one").SerializeToString())
    b = frame(build_message(request_uuid=b"two").SerializeToString())
    await vehicle.notify_raw(a + b)

    assert device._handle_universal_message.await_count == 2
    assert len(device._response_buffer) == 0


# --------------------------------------------------------------------------
# Root cause B: the buffer outlived the connection it belonged to
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_truncated_frame_is_discarded_on_reconnect(device):
    """A partial frame must not be prepended to the next connection's stream."""
    vehicle = FakeTeslaVehicle()
    await _attach(device, vehicle)

    # Vehicle starts a frame and the link dies before it finishes.
    await vehicle.notify_message(build_message(), truncate=4)
    assert len(device._response_buffer) > 0  # held, waiting for the rest

    device._handle_disconnect(vehicle)
    assert len(device._response_buffer) == 0

    # A fresh link delivers a clean frame, which must decode.
    vehicle2 = FakeTeslaVehicle()
    await _attach(device, vehicle2)
    await vehicle2.notify_message(build_message(request_uuid=b"fresh"))

    assert device._handle_universal_message.await_count == 1
    assert device._handle_universal_message.await_args[0][0].request_uuid == b"fresh"


@pytest.mark.asyncio
async def test_disconnect_clears_buffer(device):
    """_disconnect must also drop partial frames."""
    vehicle = FakeTeslaVehicle()
    await _attach(device, vehicle)
    await vehicle.notify_message(build_message(), truncate=4)
    assert device._response_buffer

    await device._disconnect()
    assert len(device._response_buffer) == 0


@pytest.mark.asyncio
async def test_connect_clears_stale_buffer(device, monkeypatch):
    """Establishing a link starts from an empty buffer."""
    device._response_buffer.extend(b"\xde\xad\xbe\xef")

    vehicle = FakeTeslaVehicle()
    monkeypatch.setattr("tesla_ble.device.close_stale_connections_by_address", AsyncMock())
    monkeypatch.setattr("tesla_ble.device.establish_connection", AsyncMock(return_value=vehicle))
    monkeypatch.setattr(device, "_initialize_crypto", AsyncMock())

    await device._connect()

    assert len(device._response_buffer) == 0


# --------------------------------------------------------------------------
# Root causes D + E: recovery ran per packet and reset user config
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decode_failure_does_not_reset_polling_config(device):
    """Transport recovery must not touch configured polling or poll timers."""
    device.load_polling_parameters(
        update_interval=42,
        poll_data_period=99,
        poll_charging_period=7,
        fast_poll_if_unlocked=1,
    )
    device._last_poll_time = 12345.0
    device._last_wake_time = 999.0
    device._is_charging = True
    device._send_session_info_request = AsyncMock()
    device._process_domain_queue = AsyncMock()

    await device._recover_from_decode_failure()

    assert device.update_interval == 42
    assert device.poll_data_period == 99
    assert device.poll_charging_period == 7
    assert device.fast_poll_if_unlocked is True
    # Zeroing _last_poll_time forced an extra poll per decode failure.
    assert device._last_poll_time == 12345.0
    assert device._last_wake_time == 999.0
    assert device._is_charging is True


@pytest.mark.asyncio
async def test_recovery_is_debounced_across_many_failures(device, monkeypatch):
    """Many decode failures in a burst must trigger recovery once, not once each."""
    vehicle = FakeTeslaVehicle()
    await _attach(device, vehicle)

    recoveries = 0

    async def _count():
        nonlocal recoveries
        recoveries += 1

    monkeypatch.setattr(device, "_recover_from_decode_failure", _count)

    for _ in range(25):
        await vehicle.notify_garbage(20)

    await _drain_tasks()
    assert recoveries == 1, f"expected a single debounced recovery, got {recoveries}"


@pytest.mark.asyncio
async def test_recovery_rearms_after_cooldown(device, monkeypatch):
    """The debounce must not wedge recovery off permanently."""
    vehicle = FakeTeslaVehicle()
    await _attach(device, vehicle)

    recoveries = 0

    async def _count():
        nonlocal recoveries
        recoveries += 1

    monkeypatch.setattr(device, "_recover_from_decode_failure", _count)

    await vehicle.notify_garbage(20)
    await _drain_tasks()
    assert recoveries == 1

    device._last_decode_recovery -= DECODE_RECOVERY_COOLDOWN + 1
    device._decode_recovery_task = None
    await vehicle.notify_garbage(20)
    await _drain_tasks()
    assert recoveries == 2


@pytest.mark.asyncio
async def test_repeat_decode_failures_log_once(device, caplog):
    """Only the first failure of an episode is ERROR; a summary closes it out."""
    vehicle = FakeTeslaVehicle()
    await _attach(device, vehicle)
    device._handle_decode_failure = MagicMock()

    with caplog.at_level("DEBUG", logger="tesla_ble.device"):
        for _ in range(10):
            await vehicle.notify_garbage(20)

    errors = [r for r in caplog.records
              if r.levelname == "ERROR" and "Failed to decode" in r.getMessage()]
    assert len(errors) == 1, f"expected one ERROR per episode, got {len(errors)}"
    # The vehicle identity is present so multi-car installs are distinguishable.
    assert TEST_VIN[-6:] in errors[0].getMessage()


# --------------------------------------------------------------------------
# Root cause F: multi-chunk writes were not atomic
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_uses_negotiated_mtu(device):
    """Chunk size follows the MTU instead of the hardcoded 20 bytes."""
    vehicle = FakeTeslaVehicle(mtu_size=247)
    await _attach(device, vehicle)

    await device._write_ble_data(frame(build_message().SerializeToString()))

    assert vehicle.written_chunks, "nothing was written"
    assert max(len(c) for c in vehicle.written_chunks) > BLE_DEFAULT_CHUNK_SIZE


@pytest.mark.asyncio
async def test_small_mtu_falls_back_to_default_chunk(device):
    """A minimal/absent MTU still yields the safe 20-byte chunk."""
    vehicle = FakeTeslaVehicle(mtu_size=23)
    await _attach(device, vehicle)

    assert device._chunk_size() == BLE_DEFAULT_CHUNK_SIZE

    vehicle.mtu_size = None  # some backends never report one
    assert device._chunk_size() == BLE_DEFAULT_CHUNK_SIZE


@pytest.mark.asyncio
async def test_write_never_reconnects_mid_message(device, monkeypatch):
    """A failure partway through a message must abort it, not reconnect and continue."""
    vehicle = FakeTeslaVehicle(mtu_size=23)
    await _attach(device, vehicle)

    connect = AsyncMock()
    monkeypatch.setattr(device, "_connect", connect)

    # Long enough to need several chunks; fail on the third.
    payload = frame(build_message(request_uuid=b"x" * 64).SerializeToString())
    assert len(payload) > 2 * BLE_DEFAULT_CHUNK_SIZE
    vehicle.fail_write_at_chunk = 2

    with pytest.raises(Exception):
        await device._write_ble_data(payload)

    connect.assert_not_awaited()
    # The link is dropped so the car does not reassemble the next message onto
    # the fragment it is still holding.
    assert device._client is None
    assert vehicle.pending_rx_bytes >= 0


@pytest.mark.asyncio
async def test_partial_write_drops_the_link(device):
    """After a torn write both ends must resynchronise, not carry the fragment."""
    vehicle = FakeTeslaVehicle(mtu_size=23)
    await _attach(device, vehicle)

    payload = frame(build_message(request_uuid=b"y" * 64).SerializeToString())
    vehicle.fail_write_at_chunk = 1

    with pytest.raises(Exception):
        await device._write_ble_data(payload)

    assert device.is_connected is False
    assert device._client is None
    assert len(device._response_buffer) == 0


@pytest.mark.asyncio
async def test_complete_message_arrives_intact(device):
    """The happy path: the vehicle reassembles exactly what we sent."""
    vehicle = FakeTeslaVehicle(mtu_size=23)
    await _attach(device, vehicle)

    message = build_message(request_uuid=b"z" * 40)
    await device._write_ble_data(frame(message.SerializeToString()))

    assert len(vehicle.received_messages) == 1
    assert vehicle.received_messages[0].request_uuid == b"z" * 40
    assert vehicle.pending_rx_bytes == 0
    assert vehicle.undecodable_writes == 0


@pytest.mark.asyncio
async def test_concurrent_writes_do_not_interleave(device):
    """Two messages sent concurrently must not interleave their chunks."""
    import asyncio

    vehicle = FakeTeslaVehicle(mtu_size=23)
    await _attach(device, vehicle)

    first = frame(build_message(request_uuid=b"a" * 60).SerializeToString())
    second = frame(build_message(request_uuid=b"b" * 60).SerializeToString())

    await asyncio.gather(
        device._write_ble_data(first),
        device._write_ble_data(second),
    )

    # Both decoded cleanly on the vehicle side — interleaving would have produced
    # garbage frames instead.
    assert vehicle.undecodable_writes == 0
    assert len(vehicle.received_messages) == 2
    assert {bytes(m.request_uuid) for m in vehicle.received_messages} == {b"a" * 60, b"b" * 60}
    assert vehicle.pending_rx_bytes == 0


# --------------------------------------------------------------------------
# Property-style chaos: whatever the vehicle sends, the buffer must stay
# bounded and a clean frame must still get through afterwards.
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("seed", [1, 7, 13, 42, 99])
async def test_random_stream_always_recovers(device, seed):
    """Fuzz the receive path: bounded buffer, and never permanently wedged."""
    import random

    rng = random.Random(seed)
    vehicle = FakeTeslaVehicle(mtu_size=rng.choice([23, 64, 247]))
    await _attach(device, vehicle)

    for _ in range(60):
        roll = rng.random()
        if roll < 0.4:
            await vehicle.notify_raw(bytes(rng.randrange(256) for _ in range(rng.randint(1, 40))))
        elif roll < 0.6:
            await vehicle.notify_message(build_message(), truncate=rng.randint(1, 5))
        elif roll < 0.8:
            await vehicle.notify_garbage(rng.randint(1, 30))
        else:
            await vehicle.notify_message(build_message(request_uuid=b"ok"))
        assert len(device._response_buffer) <= MAX_RX_BUFFER

    # However mangled the stream was, a clean frame on a fresh link must decode.
    device._handle_disconnect(vehicle)
    vehicle2 = FakeTeslaVehicle()
    await _attach(device, vehicle2)
    before = device._handle_universal_message.await_count
    await vehicle2.notify_message(build_message(request_uuid=b"final"))

    assert device._handle_universal_message.await_count == before + 1
    assert device._handle_universal_message.await_args[0][0].request_uuid == b"final"
    assert len(device._response_buffer) == 0
