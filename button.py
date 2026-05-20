"""Tesla BLE buttons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TeslaBleDataUpdateCoordinator
from .entity import TeslaBleEntity, exception_handler
from .protocol import BLECarServerVehicleAction


@dataclass(frozen=True, kw_only=True)
class TeslaButtonEntityDescription(ButtonEntityDescription):
    """Tesla BLE button entity description."""

    action: BLECarServerVehicleAction | None = None
    is_special_command: bool = False


BUTTONS: tuple[TeslaButtonEntityDescription, ...] = (
    TeslaButtonEntityDescription(
        key="pair_key",
        translation_key="pair_key",
        is_special_command=True,
    ),
    TeslaButtonEntityDescription(
        key="honk_horn",
        translation_key="honk_horn",
        action=BLECarServerVehicleAction.SOUND_HORN,
    ),
    TeslaButtonEntityDescription(
        key="flash_lights",
        translation_key="flash_lights",
        action=BLECarServerVehicleAction.FLASH_LIGHT,
    ),
    TeslaButtonEntityDescription(
        key="wake_vehicle",
        translation_key="wake_vehicle",
        is_special_command=True,
    ),
    TeslaButtonEntityDescription(
        key="open_frunk",
        translation_key="open_frunk",
        is_special_command=True,
    ),
    TeslaButtonEntityDescription(
        key="unlock_charge_port",
        translation_key="unlock_charge_port",
        is_special_command=True,
    ),
    TeslaButtonEntityDescription(
        key="unlatch_driver_door",
        translation_key="unlatch_driver_door",
        is_special_command=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla BLE button entities."""
    coordinator: TeslaBleDataUpdateCoordinator = entry.runtime_data

    entities = [
        TeslaBleButton(coordinator, description)
        for description in BUTTONS
    ]

    async_add_entities(entities)


class TeslaBleButton(TeslaBleEntity, ButtonEntity):
    """Tesla BLE button entity."""

    entity_description: TeslaButtonEntityDescription

    def __init__(
        self,
        coordinator: TeslaBleDataUpdateCoordinator,
        description: TeslaButtonEntityDescription,
    ) -> None:
        """Initialize Tesla BLE button."""
        super().__init__(
            coordinator,
            description.key,
            translation_key=description.translation_key,
            name=description.name,
            entity_category=description.entity_category,
        )
        self.entity_description = description

    @exception_handler
    async def async_press(self) -> None:
        """Press the button."""
        if self.entity_description.is_special_command:
            if self.entity_description.key == "pair_key":
                await self.coordinator.device.pair_async()
            elif self.entity_description.key == "wake_vehicle":
                await self.coordinator.device.wake_vehicle()
            elif self.entity_description.key == "open_frunk":
                await self.coordinator.device.send_vcsec_closure_move("frontTrunk", "OPEN")
            elif self.entity_description.key == "unlock_charge_port":
                await self.coordinator.device.send_vcsec_closure_move("chargePort", "OPEN")
            elif self.entity_description.key == "unlatch_driver_door":
                await self.coordinator.device.send_vcsec_closure_move("frontDriverDoor", "OPEN")
        elif self.entity_description.action:
            await self.coordinator.device.send_vehicle_action(
                self.entity_description.action
            )
