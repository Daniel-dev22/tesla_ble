"""Tesla BLE cover entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TeslaBleDataUpdateCoordinator
from .entity import TeslaBleEntity, exception_handler
from .protocol import BLECarServerVehicleAction


@dataclass(frozen=True, kw_only=True)
class TeslaCoverEntityDescription(CoverEntityDescription):
    """Tesla BLE cover entity description."""

    is_closed_fn: Callable[[dict[str, Any]], bool | None] = lambda data: None
    open_action: BLECarServerVehicleAction | None = None
    close_action: BLECarServerVehicleAction | None = None
    features: CoverEntityFeature = CoverEntityFeature(0)
    open_vcsec: tuple[str, str] | None = None
    close_vcsec: tuple[str, str] | None = None


COVERS: tuple[TeslaCoverEntityDescription, ...] = (
    TeslaCoverEntityDescription(
        key="charge_port",
        translation_key="charge_port",
        device_class=CoverDeviceClass.DOOR,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        is_closed_fn=lambda data: not data.get("is_charge_flap_open", False),
        open_action=BLECarServerVehicleAction.SET_OPEN_CHARGE_PORT_DOOR,
        close_action=BLECarServerVehicleAction.SET_CLOSE_CHARGE_PORT_DOOR,
    ),
    TeslaCoverEntityDescription(
        key="windows",
        translation_key="windows",
        device_class=CoverDeviceClass.WINDOW,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        is_closed_fn=lambda data: not data.get("windows_open", False),
        open_action=BLECarServerVehicleAction.SET_WINDOWS_SWITCH,
        close_action=BLECarServerVehicleAction.SET_WINDOWS_SWITCH,
    ),
    TeslaCoverEntityDescription(
        key="trunk",
        translation_key="trunk",
        device_class=CoverDeviceClass.DOOR,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        is_closed_fn=lambda data: not data.get("is_trunk_open", False),
        open_vcsec=("rearTrunk", "OPEN"),
        close_vcsec=("rearTrunk", "CLOSE"),
    ),
    TeslaCoverEntityDescription(
        key="frunk",
        translation_key="frunk",
        device_class=CoverDeviceClass.DOOR,
        features=CoverEntityFeature.OPEN,
        is_closed_fn=lambda data: not data.get("is_frunk_open", False),
        open_vcsec=("frontTrunk", "OPEN"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla BLE cover entities."""
    coordinator: TeslaBleDataUpdateCoordinator = entry.runtime_data

    entities = [
        TeslaBleCover(coordinator, description)
        for description in COVERS
    ]

    async_add_entities(entities)


class TeslaBleCover(TeslaBleEntity, CoverEntity):
    """Tesla BLE cover entity."""

    entity_description: TeslaCoverEntityDescription

    def __init__(
        self,
        coordinator: TeslaBleDataUpdateCoordinator,
        description: TeslaCoverEntityDescription,
    ) -> None:
        """Initialize Tesla BLE cover."""
        super().__init__(
            coordinator,
            description.key,
            translation_key=description.translation_key,
            name=description.name,
            entity_category=description.entity_category,
        )
        self.entity_description = description
        self._attr_supported_features = description.features
        initial_state = description.is_closed_fn(self.device_data)
        self._attr_is_closed = initial_state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._attr_is_closed = self.entity_description.is_closed_fn(self.device_data)
        super()._handle_coordinator_update()

    @exception_handler
    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self.entity_description.open_action is not None:
            action_kwargs: dict[str, Any] = {}
            if (
                self.entity_description.open_action
                == BLECarServerVehicleAction.SET_WINDOWS_SWITCH
            ):
                action_kwargs = {"parameter": 1, "parameter_bool": True}
            await self.coordinator.device.send_vehicle_action(
                self.entity_description.open_action,
                **action_kwargs,
            )
        elif self.entity_description.open_vcsec is not None:
            closure_type, move_type = self.entity_description.open_vcsec
            await self.coordinator.device.send_vcsec_closure_move(closure_type, move_type)
        self.async_write_ha_state()

    @exception_handler
    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if self.entity_description.close_action is not None:
            action_kwargs: dict[str, Any] = {}
            if (
                self.entity_description.close_action
                == BLECarServerVehicleAction.SET_WINDOWS_SWITCH
            ):
                action_kwargs = {"parameter": 0, "parameter_bool": False}
            await self.coordinator.device.send_vehicle_action(
                self.entity_description.close_action,
                **action_kwargs,
            )
        elif self.entity_description.close_vcsec is not None:
            closure_type, move_type = self.entity_description.close_vcsec
            await self.coordinator.device.send_vcsec_closure_move(closure_type, move_type)
        self.async_write_ha_state()
