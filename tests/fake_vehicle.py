"""An in-process fake Tesla BLE peripheral, with fault injection.

Stands in for ``BleakClientWithServiceCache`` so the integration's transport can be
driven end-to-end without a car: it accepts GATT writes, reassembles the
length-prefixed stream exactly as the vehicle does, parses real
``RoutableMessage`` protobufs, and pushes real protobuf frames back through the
notify callback.

The point is the fault injection. Every framing defect this harness exists to
catch came from a *partial* or *corrupted* byte stream, which mocks that return
canned objects can never reproduce:

* :attr:`fail_write_at_chunk` — abort a write partway through a multi-chunk
  message, leaving the vehicle holding a fragment (what a real mid-message
  proxy drop does).
* :meth:`notify_garbage` — deliver bytes that cannot start a frame.
* ``truncate=`` on :meth:`notify_message` — deliver a frame the sender promised
  but never finished.
* :meth:`drop_link` — yank the connection.

Intentionally scoped to transport/framing: replies are well-formed frames but not
cryptographically signed, since the framing layer runs below authentication. The
natural next step is a session-aware mode that answers SessionInfo and signs
responses, which would let command-level flows be driven here too.
"""

from __future__ import annotations

from google.protobuf.message import DecodeError

from ..proto import universal_message_pb2


class FakeLinkDown(Exception):
    """Raised by the fake peripheral when a write hits a downed link."""


def frame(payload: bytes) -> bytes:
    """Wrap a protobuf payload in the 2-byte big-endian length prefix."""
    return len(payload).to_bytes(2, "big") + payload


def build_message(domain: int = 2, request_uuid: bytes = b"") -> universal_message_pb2.RoutableMessage:
    """Build a minimal but structurally valid RoutableMessage."""
    message = universal_message_pb2.RoutableMessage()
    message.from_destination.domain = domain
    message.to_destination.routing_address = b"\x01" * 16
    if request_uuid:
        message.request_uuid = request_uuid
    return message


class FakeTeslaVehicle:
    """Minimal GATT peripheral that speaks the Tesla BLE framing protocol."""

    def __init__(self, mtu_size: int = 23) -> None:
        self.is_connected = True
        self.mtu_size = mtu_size

        self._notify_cb = None
        self._rx = bytearray()  # bytes the "vehicle" has received but not yet framed

        # Observations
        self.received_messages: list[universal_message_pb2.RoutableMessage] = []
        self.written_chunks: list[bytes] = []
        self.undecodable_writes = 0

        # Fault injection
        self.fail_write_at_chunk: int | None = None
        self._chunk_counter = 0

    # ----- BleakClient surface -------------------------------------------------

    async def start_notify(self, _uuid, callback) -> None:
        self._notify_cb = callback

    async def stop_notify(self, _uuid) -> None:
        self._notify_cb = None

    async def disconnect(self) -> None:
        self.is_connected = False

    async def write_gatt_char(self, _uuid, data: bytes, response: bool = True) -> None:
        if not self.is_connected:
            raise FakeLinkDown("write on a closed link")

        index = self._chunk_counter
        self._chunk_counter += 1
        if self.fail_write_at_chunk is not None and index == self.fail_write_at_chunk:
            raise FakeLinkDown(f"simulated write failure at chunk {index}")

        self.written_chunks.append(bytes(data))
        self._rx.extend(data)
        self._reassemble()

    # ----- Vehicle-side reassembly --------------------------------------------

    def _reassemble(self) -> None:
        """Frame whatever complete messages have arrived, as the car would."""
        while len(self._rx) >= 2:
            length = int.from_bytes(self._rx[:2], "big")
            if len(self._rx) < 2 + length:
                return
            payload = bytes(self._rx[2:2 + length])
            del self._rx[:2 + length]
            message = universal_message_pb2.RoutableMessage()
            try:
                message.ParseFromString(payload)
            except DecodeError:
                # A desynchronised sender makes the vehicle read nonsense too.
                self.undecodable_writes += 1
                continue
            self.received_messages.append(message)

    @property
    def pending_rx_bytes(self) -> int:
        """Bytes the vehicle is holding as an incomplete frame."""
        return len(self._rx)

    # ----- Pushing data back to the integration --------------------------------

    async def _notify(self, data: bytes) -> None:
        """Deliver bytes to the client in MTU-sized notifications."""
        if self._notify_cb is None:
            raise RuntimeError("notifications not started")
        chunk = max(1, self.mtu_size - 3)
        for i in range(0, len(data), chunk):
            await self._notify_cb(0, data[i:i + chunk])

    async def notify_message(
        self,
        message: universal_message_pb2.RoutableMessage | None = None,
        *,
        prefix: bytes = b"",
        truncate: int = 0,
    ) -> bytes:
        """Send one framed message, optionally corrupted.

        ``prefix`` prepends raw bytes before the frame (stream desync);
        ``truncate`` drops that many trailing bytes (an unfinished frame).
        """
        if message is None:
            message = build_message()
        data = prefix + frame(message.SerializeToString())
        if truncate:
            data = data[:-truncate]
        await self._notify(data)
        return data

    async def notify_garbage(self, count: int = 8) -> bytes:
        """Send bytes that cannot begin a valid frame.

        0xFF bytes decode to a length prefix of 65535 — far beyond the protocol
        maximum — which is exactly the case that used to stall the buffer forever.
        """
        data = b"\xff" * count
        await self._notify(data)
        return data

    async def notify_raw(self, data: bytes) -> None:
        """Send arbitrary bytes."""
        await self._notify(data)

    def drop_link(self) -> None:
        """Simulate the peripheral going away without a clean disconnect."""
        self.is_connected = False
