from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor
ROLE_CHARGING_MANAGER: Role
ROLE_DRIVER: Role
ROLE_FM: Role
ROLE_NONE: Role
ROLE_OWNER: Role
ROLE_SERVICE: Role
ROLE_VEHICLE_MONITOR: Role

class Role(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
