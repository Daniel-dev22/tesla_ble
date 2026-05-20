"""Tesla BLE entity base class."""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Mapping
import logging
from typing import Any, Concatenate

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import slugify as hass_slugify

from .const import DOMAIN, MANUFACTURER
from .coordinator import TeslaBleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class TeslaBleEntity(PassiveBluetoothCoordinatorEntity[TeslaBleDataUpdateCoordinator]):
    """Base Tesla BLE entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TeslaBleDataUpdateCoordinator,
        key: str,
        *,
        translation_key: str | None = None,
        name: str | None = None,
        entity_category: Any | None = None,
    ) -> None:
        """Initialize Tesla BLE entity."""
        super().__init__(coordinator)

        base_uid = coordinator.entry_id.replace("-", "")
        suffix_source = key or translation_key or "entity"
        unique_suffix = hass_slugify(str(suffix_source)) or "entity"

        self._key = key
        self._attr_unique_id = f"{base_uid}_{unique_suffix}"

        if translation_key:
            self._attr_translation_key = translation_key
        self._attr_translation_domain = DOMAIN

        if entity_category is not None:
            self._attr_entity_category = entity_category

        self._address = getattr(coordinator.ble_device, "address", None)

        connections: set[tuple[str, str]] = set()
        identifiers = {(DOMAIN, base_uid)}

        if self._address:
            connections.add((dr.CONNECTION_BLUETOOTH, self._address))
            if ":" in self._address:
                connections.add((dr.CONNECTION_NETWORK_MAC, self._address))

        self._attr_device_info = DeviceInfo(
            connections=connections if connections else None,
            identifiers=identifiers,
            manufacturer=MANUFACTURER,
            model="Tesla Vehicle",
            name=coordinator.device_name,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.device.is_available()

    @property
    def device_data(self) -> dict[str, Any]:
        """Return device data."""
        return self.coordinator.device.data

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        _LOGGER.debug("Entity %s coordinator update, doors_locked=%s",
                     self._key, self.device_data.get("doors_locked"))
        self.async_write_ha_state()


def exception_handler[_EntityT: TeslaBleEntity, **_P](
    func: Callable[Concatenate[_EntityT, _P], Coroutine[Any, Any, Any]],
) -> Callable[Concatenate[_EntityT, _P], Coroutine[Any, Any, None]]:
    """Decorate Tesla BLE calls to handle exceptions."""

    async def handler(self: _EntityT, *args: _P.args, **kwargs: _P.kwargs) -> None:
        try:
            await func(self, *args, **kwargs)
        except Exception as error:
            raise HomeAssistantError(
                f"Tesla BLE operation failed: {error}"
            ) from error

    return handler
