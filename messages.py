"""Tesla BLE protobuf helpers."""

from __future__ import annotations

import logging
from typing import Tuple

from google.protobuf.message import DecodeError

from .proto import car_server_pb2, signatures_pb2, universal_message_pb2, vcsec_pb2

_LOGGER = logging.getLogger(__name__)

# Largest length-prefixed frame we will wait for. Without any bound, a garbage
# prefix (up to 65535) makes the decoder wait forever for bytes that never
# arrive, silently stalling every real message queued behind it.
#
# Deliberately generous rather than tight. The failure modes are asymmetric: a
# cap set below a legitimate frame would reject that frame forever (permanently
# breaking whichever command produces it), whereas a loose cap only means a
# desynchronised buffer takes a little longer to reset — and it still resets,
# because a frame that fills up still has to parse as a RoutableMessage, and
# because a stalled buffer is cleared by the command-timeout -> disconnect path
# regardless. Real frames observed are in the low hundreds of bytes.
MAX_MESSAGE_LENGTH = 4096


class IncompleteMessageError(Exception):
    """Raised when a BLE buffer does not yet contain a full message.

    Recoverable by waiting: more notification data will complete the frame.
    """


class FramingError(Exception):
    """Raised when the buffer cannot be a valid frame at its current offset.

    Not recoverable by waiting — the stream is desynchronised and the caller
    must resynchronise rather than accumulate more bytes.
    """


class TeslaMessageDecoder:
    """Decode Tesla BLE protobuf messages."""

    def decode_universal_message(
        self, data: bytes
    ) -> Tuple[universal_message_pb2.RoutableMessage, int]:
        """Decode a length-prefixed UniversalMessage.

        Returns the message and the number of bytes consumed. Raises
        :class:`IncompleteMessageError` when the caller should wait for more
        data, and :class:`FramingError` when the caller must resynchronise.
        """
        if len(data) < 2:
            raise IncompleteMessageError("Incomplete length prefix")

        message_length = int.from_bytes(data[0:2], byteorder="big")

        # Check plausibility BEFORE waiting for the payload, so an implausible
        # prefix resynchronises immediately instead of stalling the buffer.
        if message_length == 0:
            raise FramingError("Zero-length frame")
        if message_length > MAX_MESSAGE_LENGTH:
            raise FramingError(
                f"Implausible frame length {message_length} (max {MAX_MESSAGE_LENGTH})"
            )

        if len(data) < 2 + message_length:
            raise IncompleteMessageError("Incomplete message payload")

        payload = data[2:2 + message_length]
        message = universal_message_pb2.RoutableMessage()
        try:
            message.ParseFromString(payload)
        except DecodeError as ex:
            raise FramingError(f"Malformed RoutableMessage: {ex}") from ex
        return message, 2 + message_length

    @staticmethod
    def decode_vcsec_message(payload: bytes) -> vcsec_pb2.FromVCSECMessage:
        """Decode VCSEC FromVCSECMessage payload."""
        message = vcsec_pb2.FromVCSECMessage()
        message.ParseFromString(payload)
        return message

    @staticmethod
    def decode_carserver_response(payload: bytes) -> car_server_pb2.Response:
        """Decode CarServer Response payload."""
        response = car_server_pb2.Response()
        response.ParseFromString(payload)
        return response

    @staticmethod
    def decode_session_info(payload: bytes) -> signatures_pb2.SessionInfo:
        """Decode Signatures SessionInfo payload."""
        info = signatures_pb2.SessionInfo()
        info.ParseFromString(payload)
        return info
