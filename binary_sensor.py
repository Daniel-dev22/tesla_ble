"""Tesla BLE binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TeslaBleDataUpdateCoordinator
from .entity import TeslaBleEntity


@dataclass(frozen=True, kw_only=True)
class TeslaBinaryEntityDescription(BinarySensorEntityDescription):
    """Tesla BLE binary sensor entity description."""

    value_fn: Callable[[dict[str, Any]], bool | None] = lambda data: None


BINARY_SENSORS: tuple[TeslaBinaryEntityDescription, ...] = (
    TeslaBinaryEntityDescription(
        key="is_asleep",
        translation_key="is_asleep",
        value_fn=lambda data: data.get("is_asleep"),
    ),
    TeslaBinaryEntityDescription(
        key="is_user_present",
        translation_key="is_user_present",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda data: data.get("is_user_present"),
    ),
    TeslaBinaryEntityDescription(
        key="doors_locked",
        translation_key="doors_locked",
        device_class=BinarySensorDeviceClass.LOCK,
        # LOCK device_class: on=unlocked, off=locked
        # So invert: when doors_locked=True (locked), set is_on=False (shows "locked")
        value_fn=lambda data: not data.get("doors_locked") if data.get("doors_locked") is not None else None,
    ),
    TeslaBinaryEntityDescription(
        key="is_charge_flap_open",
        translation_key="is_charge_flap_open",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda data: data.get("is_charge_flap_open"),
    ),
    TeslaBinaryEntityDescription(
        key="driver_front_door_open",
        translation_key="driver_front_door_open",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda data: data.get("driver_front_door_open"),
    ),
    TeslaBinaryEntityDescription(
        key="driver_rear_door_open",
        translation_key="driver_rear_door_open",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda data: data.get("driver_rear_door_open"),
    ),
    TeslaBinaryEntityDescription(
        key="passenger_front_door_open",
        translation_key="passenger_front_door_open",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda data: data.get("passenger_front_door_open"),
    ),
    TeslaBinaryEntityDescription(
        key="passenger_rear_door_open",
        translation_key="passenger_rear_door_open",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda data: data.get("passenger_rear_door_open"),
    ),
    TeslaBinaryEntityDescription(
        key="is_frunk_open",
        translation_key="is_frunk_open",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda data: data.get("is_frunk_open"),
    ),
    TeslaBinaryEntityDescription(
        key="is_trunk_open",
        translation_key="is_trunk_open",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda data: data.get("is_trunk_open"),
    ),
    TeslaBinaryEntityDescription(
        key="windows_open",
        translation_key="windows_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=lambda data: data.get("windows_open"),
    ),
    TeslaBinaryEntityDescription(
        key="is_climate_on",
        translation_key="is_climate_on",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.get("is_climate_on"),
    ),
    TeslaBinaryEntityDescription(
        key="defrost_active",
        translation_key="defrost_active",
        value_fn=lambda data: data.get("defrost_active"),
    ),
    TeslaBinaryEntityDescription(
        key="sentry_mode",
        translation_key="sentry_mode",
        device_class=BinarySensorDeviceClass.SAFETY,
        value_fn=lambda data: data.get("sentry_mode"),
    ),
    TeslaBinaryEntityDescription(
        key="is_preconditioning",
        translation_key="is_preconditioning",
        value_fn=lambda data: data.get("is_preconditioning"),
    ),
    TeslaBinaryEntityDescription(
        key="steering_wheel_heater",
        translation_key="steering_wheel_heater",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda data: data.get("steering_wheel_heater"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla BLE binary sensor entities."""
    coordinator: TeslaBleDataUpdateCoordinator = entry.runtime_data

    entities = [
        TeslaBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    ]

    async_add_entities(entities)


class TeslaBinarySensor(TeslaBleEntity, BinarySensorEntity):
    """Tesla BLE binary sensor entity."""

    entity_description: TeslaBinaryEntityDescription

    def __init__(
        self,
        coordinator: TeslaBleDataUpdateCoordinator,
        description: TeslaBinaryEntityDescription,
    ) -> None:
        """Initialize Tesla BLE binary sensor."""
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
        self._attr_is_on = self.entity_description.value_fn(self.device_data)
        if self.entity_description.key == "doors_locked":
            import logging
            _LOGGER = logging.getLogger(__name__)
            _LOGGER.debug("Binary sensor doors_locked update: device_data=%s, is_on=%s",
                         self.device_data.get("doors_locked"), self._attr_is_on)
        super()._handle_coordinator_update()
