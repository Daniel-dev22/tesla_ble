"""Tesla BLE lock."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TeslaBleDataUpdateCoordinator
from .entity import TeslaBleEntity, exception_handler


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla BLE lock entity."""
    coordinator: TeslaBleDataUpdateCoordinator = entry.runtime_data

    entities = [TeslaBleLock(coordinator)]
    async_add_entities(entities)


class TeslaBleLock(TeslaBleEntity, LockEntity):
    """Tesla BLE lock entity."""

    def __init__(self, coordinator: TeslaBleDataUpdateCoordinator) -> None:
        """Initialize Tesla BLE lock."""
        super().__init__(
            coordinator,
            "doors",
            translation_key="doors",
            name="Doors",
        )

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        return self.device_data.get("doors_locked")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._attr_is_locked = self.is_locked
        super()._handle_coordinator_update()

    @exception_handler
    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the vehicle."""
        await self.coordinator.device.lock_unlock_vehicle(lock=True)
        self.async_write_ha_state()

    @exception_handler
    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the vehicle."""
        await self.coordinator.device.lock_unlock_vehicle(lock=False)
        self.async_write_ha_state()
