"""Protobuf helpers for Tesla BLE."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

_REQUIRED_MODULES = [
    'keys_pb2',
    'errors_pb2',
    'common_pb2',
    'managed_charging_pb2',
    'signatures_pb2',
    'vcsec_pb2',
    'universal_message_pb2',
    'vehicle_pb2',
    'car_server_pb2',
]

_definitions: dict[str, ModuleType] | None = None

try:
    fleet_proto = import_module('tesla_fleet_api.tesla.vehicle.proto')
except ModuleNotFoundError:  # tesla_fleet_api not installed
    fleet_proto = None
else:
    if all(hasattr(fleet_proto, name) for name in _REQUIRED_MODULES):
        _definitions = {name: getattr(fleet_proto, name) for name in _REQUIRED_MODULES}

if _definitions is None:
    # Import our local protobuf modules in dependency order to avoid duplicate registration
    from . import keys_pb2 as _keys_pb2
    from . import errors_pb2 as _errors_pb2
    from . import common_pb2 as _common_pb2
    from . import managed_charging_pb2 as _managed_charging_pb2
    from . import signatures_pb2 as _signatures_pb2
    from . import vcsec_pb2 as _vcsec_pb2
    from . import universal_message_pb2 as _universal_message_pb2
    from . import vehicle_pb2 as _vehicle_pb2
    from . import car_server_pb2 as _car_server_pb2

    _definitions = {
        'keys_pb2': _keys_pb2,
        'errors_pb2': _errors_pb2,
        'common_pb2': _common_pb2,
        'managed_charging_pb2': _managed_charging_pb2,
        'signatures_pb2': _signatures_pb2,
        'vcsec_pb2': _vcsec_pb2,
        'universal_message_pb2': _universal_message_pb2,
        'vehicle_pb2': _vehicle_pb2,
        'car_server_pb2': _car_server_pb2,
    }

globals().update(_definitions)
__all__ = list(_definitions)
