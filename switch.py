"""Tesla BLE switches."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TeslaBleDataUpdateCoordinator
from .entity import TeslaBleEntity, exception_handler
from .protocol import BLECarServerVehicleAction


@dataclass(frozen=True, kw_only=True)
class TeslaSwitchEntityDescription(SwitchEntityDescription):
    """Tesla BLE switch entity description."""

    is_on_fn: Callable[[dict[str, Any]], bool | None] = lambda data: None
    turn_on_action: BLECarServerVehicleAction | None = None
    turn_off_action: BLECarServerVehicleAction | None = None


SWITCHES: tuple[TeslaSwitchEntityDescription, ...] = (
    TeslaSwitchEntityDescription(
        key="charging",
        translation_key="charging",
        is_on_fn=lambda data: data.get("charging_state") == "Charging",
        turn_on_action=BLECarServerVehicleAction.SET_CHARGING_SWITCH,
        turn_off_action=BLECarServerVehicleAction.SET_CHARGING_SWITCH,
    ),
    TeslaSwitchEntityDescription(
        key="climate",
        translation_key="climate",
        is_on_fn=lambda data: data.get("is_climate_on"),
        turn_on_action=BLECarServerVehicleAction.SET_HVAC_SWITCH,
        turn_off_action=BLECarServerVehicleAction.SET_HVAC_SWITCH,
    ),
    TeslaSwitchEntityDescription(
        key="defrost",
        translation_key="defrost",
        is_on_fn=lambda data: data.get("defrost_active"),
        turn_on_action=BLECarServerVehicleAction.DEFROST_CAR,
        turn_off_action=BLECarServerVehicleAction.DEFROST_CAR,
    ),
    TeslaSwitchEntityDescription(
        key="steering_wheel_heater",
        translation_key="steering_wheel_heater",
        is_on_fn=lambda data: data.get("steering_wheel_heater"),
        turn_on_action=BLECarServerVehicleAction.SET_HVAC_STEERING_HEATER_SWITCH,
        turn_off_action=BLECarServerVehicleAction.SET_HVAC_STEERING_HEATER_SWITCH,
    ),
    TeslaSwitchEntityDescription(
        key="sentry_mode",
        translation_key="sentry_mode",
        is_on_fn=lambda data: data.get("sentry_mode"),
        turn_on_action=BLECarServerVehicleAction.SET_SENTRY_SWITCH,
        turn_off_action=BLECarServerVehicleAction.SET_SENTRY_SWITCH,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla BLE switch entities."""
    coordinator: TeslaBleDataUpdateCoordinator = entry.runtime_data

    entities = [
        TeslaBleSwitch(coordinator, description)
        for description in SWITCHES
    ]

    async_add_entities(entities)


class TeslaBleSwitch(TeslaBleEntity, SwitchEntity):
    """Tesla BLE switch entity."""

    entity_description: TeslaSwitchEntityDescription

    def __init__(
        self,
        coordinator: TeslaBleDataUpdateCoordinator,
        description: TeslaSwitchEntityDescription,
    ) -> None:
        """Initialize Tesla BLE switch."""
        super().__init__(
            coordinator,
            description.key,
            translation_key=description.translation_key,
            name=description.name,
            entity_category=description.entity_category,
        )
        self.entity_description = description

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._attr_is_on = self.entity_description.is_on_fn(self.device_data)
        super()._handle_coordinator_update()

    @exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.device.send_vehicle_action(
            self.entity_description.turn_on_action,
            parameter_bool=True,
        )
        self.async_write_ha_state()

    @exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.device.send_vehicle_action(
            self.entity_description.turn_off_action,
            parameter_bool=False,
        )
        self.async_write_ha_state()
