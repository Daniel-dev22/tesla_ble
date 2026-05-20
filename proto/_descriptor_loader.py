"""Helper to load protobuf descriptors into the default pool safely."""

from __future__ import annotations

from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf import descriptor_pool as _descriptor_pool


def load_descriptor(serialized: bytes):
    """Load a FileDescriptorProto, tolerating duplicates from other packages."""
    pool = _descriptor_pool.Default()
    try:
        return pool.AddSerializedFile(serialized)
    except TypeError as err:  # pragma: no cover - depends on runtime environment
        message = str(err)
        if "duplicate file name" not in message:
            raise
        descriptor_proto = _descriptor_pb2.FileDescriptorProto()
        descriptor_proto.ParseFromString(serialized)
        existing = pool.FindFileByName(descriptor_proto.name)
        if existing.serialized_pb != serialized:
            raise RuntimeError(
                f"Conflicting protobuf definition already loaded for {descriptor_proto.name}. "
                "Please remove the other Tesla protobuf package so Tesla BLE can load its schema."
            ) from err
        return existing
