"""Tests for Tesla BLE integration."""

from __future__ import annotations

import sys
import types

# Provide minimal Home Assistant stubs so the integration imports succeed during unit tests
if "homeassistant" not in sys.modules:
    ha_module = types.ModuleType("homeassistant")
    sys.modules["homeassistant"] = ha_module
else:
    ha_module = sys.modules["homeassistant"]

components_module = types.ModuleType("homeassistant.components")
bluetooth_module = types.ModuleType("homeassistant.components.bluetooth")
bluetooth_module.async_ble_device_from_address = lambda *args, **kwargs: None
bluetooth_module.async_track_unavailable = lambda *args, **kwargs: None
bluetooth_module.BluetoothChange = object
bluetooth_module.BluetoothServiceInfoBleak = object
bluetooth_module.BluetoothScanningMode = types.SimpleNamespace(ACTIVE="active", PASSIVE="passive")

sys.modules["homeassistant.components"] = components_module
sys.modules["homeassistant.components.bluetooth"] = bluetooth_module
components_module.bluetooth = bluetooth_module

core_module = types.ModuleType("homeassistant.core")
core_module.HomeAssistant = object
core_module.callback = lambda func: func
sys.modules["homeassistant.core"] = core_module

helpers_module = types.ModuleType("homeassistant.helpers")
storage_module = types.ModuleType("homeassistant.helpers.storage")

class _FakeStore:
    def __init__(self, *args, **kwargs):
        self.data = None

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.data = data

storage_module.Store = _FakeStore

sys.modules["homeassistant.helpers"] = helpers_module
sys.modules["homeassistant.helpers.storage"] = storage_module
helpers_module.storage = storage_module

config_entries_module = types.ModuleType("homeassistant.config_entries")
config_entries_module.ConfigEntry = object
sys.modules["homeassistant.config_entries"] = config_entries_module

const_module = types.ModuleType("homeassistant.const")
const_module.Platform = types.SimpleNamespace(
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

helpers_device_registry = types.ModuleType("homeassistant.helpers.device_registry")
helpers_device_registry.DeviceInfo = dict
helpers_device_registry.CONNECTION_BLUETOOTH = "bluetooth"
helpers_device_registry.CONNECTION_NETWORK_MAC = "network_mac"
sys.modules["homeassistant.helpers.device_registry"] = helpers_device_registry

passive_module = types.ModuleType(
    "homeassistant.components.bluetooth.passive_update_coordinator"
)

class _FakePassiveCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

passive_module.PassiveBluetoothCoordinatorEntity = _FakePassiveCoordinatorEntity
sys.modules[
    "homeassistant.components.bluetooth.passive_update_coordinator"
] = passive_module

# ensure submodules are discoverable via attribute lookup
ha_module.components = components_module
ha_module.core = core_module
ha_module.helpers = helpers_module
ha_module.config_entries = config_entries_module
ha_module.const = const_module
