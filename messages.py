"""Tesla BLE protobuf helpers."""

from __future__ import annotations

import logging
from typing import Tuple

from .proto import car_server_pb2, signatures_pb2, universal_message_pb2, vcsec_pb2

_LOGGER = logging.getLogger(__name__)


class IncompleteMessageError(Exception):
    """Raised when a BLE buffer does not contain a full message."""


class TeslaMessageDecoder:
    """Decode Tesla BLE protobuf messages."""

    def decode_universal_message(
        self, data: bytes
    ) -> Tuple[universal_message_pb2.RoutableMessage, int]:
        """Decode a length-prefixed UniversalMessage."""
        if len(data) < 2:
            raise IncompleteMessageError("Incomplete length prefix")

        message_length = int.from_bytes(data[0:2], byteorder="big")
        if len(data) < 2 + message_length:
            raise IncompleteMessageError("Incomplete message payload")

        payload = data[2:2 + message_length]
        message = universal_message_pb2.RoutableMessage()
        message.ParseFromString(payload)
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
