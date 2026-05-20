"""Tesla BLE number entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TeslaBleDataUpdateCoordinator
from .entity import TeslaBleEntity, exception_handler
from .protocol import BLECarServerVehicleAction


@dataclass(frozen=True, kw_only=True)
class TeslaNumberEntityDescription(NumberEntityDescription):
    """Tesla BLE number entity description."""

    value_fn: Callable[[dict[str, Any]], float | None] = lambda data: None
    action: BLECarServerVehicleAction | None = None


NUMBERS: tuple[TeslaNumberEntityDescription, ...] = (
    TeslaNumberEntityDescription(
        key="charge_limit",
        translation_key="charge_limit",
        native_min_value=50,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: data.get("charge_limit"),
        action=BLECarServerVehicleAction.SET_CHARGING_LIMIT,
    ),
    TeslaNumberEntityDescription(
        key="charging_amps",
        translation_key="charging_amps",
        native_min_value=1,
        native_max_value=48,
        native_step=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda data: data.get("charging_amps"),
        action=BLECarServerVehicleAction.SET_CHARGING_AMPS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla BLE number entities."""
    coordinator: TeslaBleDataUpdateCoordinator = entry.runtime_data

    entities = [
        TeslaBleNumber(coordinator, description)
        for description in NUMBERS
    ]

    async_add_entities(entities)


class TeslaBleNumber(TeslaBleEntity, NumberEntity):
    """Tesla BLE number entity."""

    entity_description: TeslaNumberEntityDescription

    def __init__(
        self,
        coordinator: TeslaBleDataUpdateCoordinator,
        description: TeslaNumberEntityDescription,
    ) -> None:
        """Initialize Tesla BLE number."""
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
        self._attr_native_value = self.entity_description.value_fn(self.device_data)
        super()._handle_coordinator_update()

    @exception_handler
    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.device.send_vehicle_action(
            self.entity_description.action,
            parameter=int(value),
        )
        self.async_write_ha_state()
