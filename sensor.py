"""Tesla BLE sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TeslaBleDataUpdateCoordinator
from .entity import TeslaBleEntity


@dataclass(frozen=True, kw_only=True)
class TeslaBleEntityDescription(SensorEntityDescription):
    """Tesla BLE sensor entity description."""

    value_fn: Callable[[dict[str, Any]], Any] = lambda data: None


SENSORS: tuple[TeslaBleEntityDescription, ...] = (
    TeslaBleEntityDescription(
        key="charge_level",
        translation_key="charge_level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("charge_level"),
    ),
    TeslaBleEntityDescription(
        key="charge_limit",
        translation_key="charge_limit",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("charge_limit"),
    ),
    TeslaBleEntityDescription(
        key="battery_range",
        translation_key="battery_range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("battery_range"),
    ),
    TeslaBleEntityDescription(
        key="charging_state",
        translation_key="charging_state",
        device_class=SensorDeviceClass.ENUM,
        options=["Disconnected", "Stopped", "Charging", "Complete"],
        value_fn=lambda data: data.get("charging_state"),
    ),
    TeslaBleEntityDescription(
        key="charge_current",
        translation_key="charge_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("charge_current"),
    ),
    TeslaBleEntityDescription(
        key="charge_voltage",
        translation_key="charge_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("charge_voltage"),
    ),
    TeslaBleEntityDescription(
        key="charge_power",
        translation_key="charge_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("charge_power"),
    ),
    TeslaBleEntityDescription(
        key="charge_energy_added",
        translation_key="charge_energy_added",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get("charge_energy_added"),
    ),
    TeslaBleEntityDescription(
        key="charge_miles_added",
        translation_key="charge_miles_added",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("charge_miles_added"),
    ),
    TeslaBleEntityDescription(
        key="minutes_to_limit",
        translation_key="minutes_to_limit",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("minutes_to_limit"),
    ),
    TeslaBleEntityDescription(
        key="charge_current_request",
        translation_key="charge_current_request",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("charge_current_request"),
    ),
    TeslaBleEntityDescription(
        key="internal_temp",
        translation_key="internal_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("internal_temp"),
    ),
    TeslaBleEntityDescription(
        key="external_temp",
        translation_key="external_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("external_temp"),
    ),
    TeslaBleEntityDescription(
        key="odometer",
        translation_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get("odometer"),
    ),
    TeslaBleEntityDescription(
        key="vehicle_power",
        translation_key="vehicle_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("vehicle_power"),
    ),
    TeslaBleEntityDescription(
        key="shift_state",
        translation_key="shift_state",
        device_class=SensorDeviceClass.ENUM,
        options=["Invalid", "P", "R", "N", "D"],
        value_fn=lambda data: data.get("shift_state"),
    ),
    TeslaBleEntityDescription(
        key="defrost_mode",
        translation_key="defrost_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["Off", "Normal", "Max"],
        value_fn=lambda data: data.get("defrost_mode"),
    ),
    TeslaBleEntityDescription(
        key="sentry_mode_state",
        translation_key="sentry_mode_state",
        device_class=SensorDeviceClass.ENUM,
        options=["Off", "Idle", "Armed", "Aware", "Panic", "Quiet"],
        value_fn=lambda data: data.get("sentry_mode_state"),
    ),
    # Tire Pressure Sensors
    TeslaBleEntityDescription(
        key="tire_pressure_front_left",
        translation_key="tire_pressure_front_left",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PSI,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("tire_pressure_fl"),
    ),
    TeslaBleEntityDescription(
        key="tire_pressure_front_right",
        translation_key="tire_pressure_front_right",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PSI,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("tire_pressure_fr"),
    ),
    TeslaBleEntityDescription(
        key="tire_pressure_rear_left",
        translation_key="tire_pressure_rear_left",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PSI,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("tire_pressure_rl"),
    ),
    TeslaBleEntityDescription(
        key="tire_pressure_rear_right",
        translation_key="tire_pressure_rear_right",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PSI,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("tire_pressure_rr"),
    ),
    TeslaBleEntityDescription(
        key="tire_pressure_recommended_front",
        translation_key="tire_pressure_recommended_front",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PSI,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("tire_pressure_rcp_front"),
    ),
    TeslaBleEntityDescription(
        key="tire_pressure_recommended_rear",
        translation_key="tire_pressure_recommended_rear",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PSI,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("tire_pressure_rcp_rear"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla BLE sensor entities."""
    coordinator: TeslaBleDataUpdateCoordinator = entry.runtime_data

    entities = [
        TeslaBleeSensor(coordinator, description)
        for description in SENSORS
    ]

    # Add specialized RSSI sensor that queries the connected proxy
    entities.append(TeslaBleRSSISensor(coordinator))

    async_add_entities(entities)


class TeslaBleeSensor(TeslaBleEntity, SensorEntity):
    """Tesla BLE sensor entity."""

    entity_description: TeslaBleEntityDescription

    def __init__(
        self,
        coordinator: TeslaBleDataUpdateCoordinator,
        description: TeslaBleEntityDescription,
    ) -> None:
        """Initialize Tesla BLE sensor."""
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


class TeslaBleRSSISensor(TeslaBleEntity, SensorEntity):
    """Tesla BLE RSSI sensor that queries the connected proxy."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: TeslaBleDataUpdateCoordinator,
    ) -> None:
        """Initialize Tesla BLE RSSI sensor."""
        super().__init__(
            coordinator,
            "ble_rssi",
            translation_key="ble_rssi",
        )
        self._address = coordinator.ble_device.address

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        # Query RSSI from the connected proxy, not from advertisements
        # This is important because once connected, advertisement events stop
        # following the pattern used by Switchbot integration
        if service_info := async_last_service_info(
            self.hass, self._address, connectable=True
        ):
            self._attr_native_value = service_info.rssi
        else:
            self._attr_native_value = None
        super()._handle_coordinator_update()
