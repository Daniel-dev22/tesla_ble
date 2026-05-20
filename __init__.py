"""Support for Tesla BLE devices."""

from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_BLE_DISCONNECTED_MIN_TIME,
    CONF_FAST_POLL_IF_UNLOCKED,
    CONF_POLL_ASLEEP_PERIOD,
    CONF_POLL_CHARGING_PERIOD,
    CONF_POLL_DATA_PERIOD,
    CONF_POST_WAKE_POLL_TIME,
    CONF_PRIVATE_KEY,
    CONF_PUBLIC_KEY,
    CONF_UPDATE_INTERVAL,
    CONF_VIN,
    CONF_WAKE_ON_BOOT,
    DEFAULT_BLE_DISCONNECTED_MIN_TIME,
    DEFAULT_FAST_POLL_IF_UNLOCKED,
    DEFAULT_POLL_ASLEEP_PERIOD,
    DEFAULT_POLL_CHARGING_PERIOD,
    DEFAULT_POLL_DATA_PERIOD,
    DEFAULT_POST_WAKE_POLL_TIME,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_WAKE_ON_BOOT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import TeslaBleConfigEntry, TeslaBleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: TeslaBleConfigEntry) -> bool:
    """Set up Tesla BLE from a config entry."""
    assert entry.unique_id is not None

    address: str = entry.data[CONF_ADDRESS]
    vin: str = entry.data[CONF_VIN]

    # Get BLE device
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address.upper(), connectable=True
    )
    if not ble_device:
        raise ConfigEntryNotReady(
            f"Could not find Tesla BLE device with address {address}"
        )

    # Lazy import to avoid blocking HA startup
    from .device import TeslaBleDevice

    # Create Tesla device
    device = TeslaBleDevice(
        ble_device=ble_device,
        vin=vin,
        private_key=entry.data.get(CONF_PRIVATE_KEY),
        public_key=entry.data.get(CONF_PUBLIC_KEY),
        hass=hass,
        entry=entry,
    )

    # Load polling parameters from options
    options = entry.options or {}
    device.load_polling_parameters(
        update_interval=options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        post_wake_poll_time=options.get(CONF_POST_WAKE_POLL_TIME, DEFAULT_POST_WAKE_POLL_TIME),
        poll_data_period=options.get(CONF_POLL_DATA_PERIOD, DEFAULT_POLL_DATA_PERIOD),
        poll_asleep_period=options.get(CONF_POLL_ASLEEP_PERIOD, DEFAULT_POLL_ASLEEP_PERIOD),
        poll_charging_period=options.get(CONF_POLL_CHARGING_PERIOD, DEFAULT_POLL_CHARGING_PERIOD),
        ble_disconnected_min_time=options.get(CONF_BLE_DISCONNECTED_MIN_TIME, DEFAULT_BLE_DISCONNECTED_MIN_TIME),
        fast_poll_if_unlocked=options.get(CONF_FAST_POLL_IF_UNLOCKED, DEFAULT_FAST_POLL_IF_UNLOCKED),
        wake_on_boot=options.get(CONF_WAKE_ON_BOOT, DEFAULT_WAKE_ON_BOOT),
    )

    # Create coordinator
    coordinator = entry.runtime_data = TeslaBleDataUpdateCoordinator(
        hass=hass,
        logger=_LOGGER,
        entry_id=entry.entry_id,
        ble_device=ble_device,
        device=device,
        base_unique_id=entry.unique_id,
        device_name=entry.title or f"Tesla {vin[-4:]}",
    )

    # Start coordinator
    entry.async_on_unload(coordinator.async_start())

    # Wait for device to be ready
    if not await coordinator.async_wait_ready():
        raise ConfigEntryNotReady(
            f"Tesla device {address} failed to start"
        )

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is not None:
        coordinator.device.cancel_background_tasks()
        await coordinator.async_shutdown()
    return unloaded
