"""Minimal Home Assistant stubs so the integration imports under plain pytest.

Why this lives at the repo root and not under ``tests/``: this is a HACS
``content_in_root`` repository, so the repo directory *is* the ``tesla_ble``
package. Anything inside it can only be imported by first executing
``__init__.py``, which imports ``homeassistant`` at module scope — the very
thing we are stubbing. A root-level module loaded as an early pytest plugin
(``-p ha_stubs``, wired up in ``pytest.ini``) is imported *before* any package
import, which is the only ordering that works.

Keeping the stubs here rather than pulling in the real ``homeassistant``
package keeps the unit suite dependency-light and fast.
"""

from __future__ import annotations

import importlib.machinery
import sys
from types import ModuleType, SimpleNamespace
from typing import Generic, TypeVar

_T = TypeVar("_T")


def _module(name: str, *, is_package: bool = False) -> ModuleType:
    """Create a module registered in sys.modules with a usable spec."""
    mod = ModuleType(name)
    mod.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=is_package)
    if is_package:
        mod.__path__ = []
    if "." in name:
        mod.__package__ = name.rsplit(".", 1)[0]
    sys.modules[name] = mod
    return mod


class _Store:
    """Stand-in for homeassistant.helpers.storage.Store."""

    def __init__(self, *args, **kwargs) -> None:
        self.data = None

    async def async_load(self):
        return self.data

    async def async_save(self, data) -> None:
        self.data = data


class _SensorEntity:
    def __init__(self, *args, **kwargs) -> None:
        self._attr_native_value = None

    @property
    def native_value(self):
        return self._attr_native_value

    @native_value.setter
    def native_value(self, value) -> None:
        self._attr_native_value = value

    def __getattr__(self, item):  # pragma: no cover - minimal stub
        raise AttributeError(item)


class _PassiveEntity(Generic[_T]):
    def __init__(self, coordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = None

    @classmethod
    def __class_getitem__(cls, _item):  # pragma: no cover
        return cls

    @property
    def unique_id(self):  # pragma: no cover
        return self._attr_unique_id


class _ActiveCoordinator(Generic[_T]):
    """Stand-in for ActiveBluetoothDataUpdateCoordinator (subscriptable base)."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    @classmethod
    def __class_getitem__(cls, _item):  # pragma: no cover
        return cls


class _HomeAssistantError(Exception):
    """Stand-in for homeassistant.exceptions.HomeAssistantError."""


class _ConfigEntryNotReady(_HomeAssistantError):
    """Stand-in for homeassistant.exceptions.ConfigEntryNotReady."""


_INSTALLED = False


def install_homeassistant_stubs(force: bool = False) -> None:
    """Register stub ``homeassistant`` modules in ``sys.modules``.

    Idempotent *by identity*: repeat calls are a no-op unless ``force`` is set.
    This matters because integration modules bind the stub module objects at
    import time (``from homeassistant.components import bluetooth``). Rebuilding
    the stubs after that point would leave those modules holding references to
    orphaned objects — which is exactly how the previous duplicated stub
    installers made tests fail with spurious ``AttributeError``.
    """
    global _INSTALLED
    if _INSTALLED and not force:
        return
    _INSTALLED = True

    for mod_name in [m for m in sys.modules if m.startswith("homeassistant")]:
        sys.modules.pop(mod_name)

    ha = _module("homeassistant", is_package=True)

    components = _module("homeassistant.components", is_package=True)

    bluetooth = _module("homeassistant.components.bluetooth", is_package=True)
    bluetooth.async_ble_device_from_address = lambda *args, **kwargs: None
    bluetooth.async_track_unavailable = lambda *args, **kwargs: None
    bluetooth.async_last_service_info = lambda *args, **kwargs: None
    bluetooth.async_address_present = lambda *args, **kwargs: True
    bluetooth.async_register_callback = lambda *args, **kwargs: (lambda: None)
    bluetooth.BluetoothChange = object
    bluetooth.BluetoothServiceInfoBleak = object
    bluetooth.BluetoothScanningMode = SimpleNamespace(ACTIVE="active", PASSIVE="passive")
    components.bluetooth = bluetooth

    passive = _module("homeassistant.components.bluetooth.passive_update_coordinator")
    passive.PassiveBluetoothCoordinatorEntity = _PassiveEntity

    active = _module("homeassistant.components.bluetooth.active_update_coordinator")

    active.ActiveBluetoothDataUpdateCoordinator = _ActiveCoordinator

    core = _module("homeassistant.core")
    core.HomeAssistant = object
    core.CoreState = SimpleNamespace(running="running", starting="starting")
    core.callback = lambda func: func
    ha.core = core

    helpers = _module("homeassistant.helpers", is_package=True)
    storage = _module("homeassistant.helpers.storage")
    storage.Store = _Store
    helpers.storage = storage

    device_registry = _module("homeassistant.helpers.device_registry")
    device_registry.DeviceInfo = dict
    device_registry.CONNECTION_BLUETOOTH = "bluetooth"
    device_registry.CONNECTION_NETWORK_MAC = "network_mac"
    helpers.device_registry = device_registry

    entity_platform = _module("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = object

    event = _module("homeassistant.helpers.event")
    event.async_track_time_interval = lambda *args, **kwargs: (lambda: None)
    ha.helpers = helpers

    config_entries = _module("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    config_entries.ConfigFlow = object
    config_entries.ConfigFlowResult = dict
    config_entries.OptionsFlow = object
    ha.config_entries = config_entries

    const = _module("homeassistant.const")
    const.Platform = SimpleNamespace(
        BINARY_SENSOR="binary_sensor",
        BUTTON="button",
        COVER="cover",
        LOCK="lock",
        NUMBER="number",
        SENSOR="sensor",
        SWITCH="switch",
    )
    const.ATTR_CONNECTIONS = "connections"
    const.CONF_ADDRESS = "address"
    const.CONF_NAME = "name"
    const.PERCENTAGE = "%"
    const.EntityCategory = SimpleNamespace(CONFIG="config", DIAGNOSTIC="diagnostic")
    const.UnitOfElectricCurrent = SimpleNamespace(AMPERE="A")
    ha.const = const

    sensor = _module("homeassistant.components.sensor")
    sensor.SensorEntity = _SensorEntity
    sensor.SensorEntityDescription = object
    sensor.SensorDeviceClass = SimpleNamespace(
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
    sensor.SensorStateClass = SimpleNamespace(
        MEASUREMENT="measurement", TOTAL_INCREASING="total_increasing"
    )
    components.sensor = sensor

    exceptions = _module("homeassistant.exceptions")
    exceptions.HomeAssistantError = _HomeAssistantError
    exceptions.ConfigEntryNotReady = _ConfigEntryNotReady

    util = _module("homeassistant.util")
    util.slugify = lambda value: str(value).lower().replace(" ", "_").replace("'", "")
    ha.util = util

    ha.components = components


# Importing this module as a pytest plugin (``-p ha_stubs``) must install the
# stubs immediately — collection imports the package right after plugin load.
install_homeassistant_stubs()
