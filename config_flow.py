"""Config flow for Tesla BLE integration."""

from __future__ import annotations

import logging
from typing import Any, Mapping

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant, callback

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
    SERVICE_UUID,
)
from .device import TeslaBleDevice

_LOGGER = logging.getLogger(__name__)


POLLING_FIELD_DEFS: tuple[tuple[str, int, vol.Range], ...] = (
    (
        CONF_UPDATE_INTERVAL,
        DEFAULT_UPDATE_INTERVAL,
        vol.Range(min=5, max=300),
    ),
    (
        CONF_POST_WAKE_POLL_TIME,
        DEFAULT_POST_WAKE_POLL_TIME,
        vol.Range(min=60, max=1800),
    ),
    (
        CONF_POLL_DATA_PERIOD,
        DEFAULT_POLL_DATA_PERIOD,
        vol.Range(min=10, max=600),
    ),
    (
        CONF_POLL_ASLEEP_PERIOD,
        DEFAULT_POLL_ASLEEP_PERIOD,
        vol.Range(min=30, max=600),
    ),
    (
        CONF_POLL_CHARGING_PERIOD,
        DEFAULT_POLL_CHARGING_PERIOD,
        vol.Range(min=5, max=120),
    ),
    (
        CONF_BLE_DISCONNECTED_MIN_TIME,
        DEFAULT_BLE_DISCONNECTED_MIN_TIME,
        vol.Range(min=60, max=1800),
    ),
    (
        CONF_FAST_POLL_IF_UNLOCKED,
        DEFAULT_FAST_POLL_IF_UNLOCKED,
        vol.Range(min=0, max=1),
    ),
    (
        CONF_WAKE_ON_BOOT,
        DEFAULT_WAKE_ON_BOOT,
        vol.Range(min=0, max=1),
    ),
)


def _build_polling_schema(current: Mapping[str, Any]) -> vol.Schema:
    """Build voluptuous schema for polling configuration."""
    schema: dict[Any, Any] = {}
    for key, default, validator in POLLING_FIELD_DEFS:
        schema[vol.Optional(key, default=current.get(key, default))] = vol.All(
            vol.Coerce(int),
            validator,
        )
    return vol.Schema(schema)


def _sanitize_polling_options(data: Mapping[str, Any]) -> dict[str, int]:
    """Normalize polling option values to ints."""
    sanitized: dict[str, int] = {}
    for key, default, _validator in POLLING_FIELD_DEFS:
        sanitized[key] = int(data.get(key, default))
    return sanitized


async def async_validate_tesla_or_error(
    address: str, vin: str, private_key: str, public_key: str, hass: HomeAssistant
) -> dict[str, str]:
    """Validate the Tesla pairing and return errors if any (YaleXS pattern)."""
    device = hass.data.get("tesla_ble_validation_device")
    if device is None or getattr(device, "address", None) != address:
        try:
            device = TeslaBleDevice(
                address=address,
                vin=vin,
                private_key=bytes.fromhex(private_key),
                public_key=bytes.fromhex(public_key),
                hass=hass,
            )
            hass.data["tesla_ble_validation_device"] = device
        except Exception as ex:
            _LOGGER.exception("Tesla device creation error: %s", ex)
            return {"base": "cannot_connect"}

    try:
        success = await device.pair()
        if not success:
            reason = device.pairing_failure_reason or "pairing_failed"
            return {"base": reason}
    except Exception as ex:
        _LOGGER.exception("Tesla validation error: %s", ex)
        return {"base": "cannot_connect"}

    return {}


def get_vin_advertisement_name(vin: str) -> str:
    """Calculate Tesla BLE advertisement name from VIN (ESPHome pattern)."""
    import hashlib

    # BLE advertisement local name: `S + <ID> + C`, where `<ID>` is the
    # lower-case hex-encoding of the first eight bytes of the SHA1 digest of the VIN
    vin_sha1 = hashlib.sha1(vin.encode()).digest()
    hex_id = vin_sha1[:8].hex().lower()
    return f"S{hex_id}C"


class TeslaBleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesla BLE."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> TeslaBleOptionsFlow:
        """Create the options flow."""
        return TeslaBleOptionsFlow(config_entry)

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: BluetoothServiceInfoBleak | None = None
        self._pending_entry_data: dict[str, Any] | None = None
        self._pending_entry_title: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self._discovered_device = discovery_info

        # Extract Tesla identifier from device name if available
        device_name = discovery_info.name or discovery_info.device.name or ""
        if device_name.startswith("S"):
            # Tesla vehicles have names starting with 'S' followed by identifier
            context = {"title_placeholders": {"name": device_name}}
        else:
            context = {"title_placeholders": {"name": discovery_info.address}}

        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            vin = user_input[CONF_VIN].upper()
            name = user_input.get(CONF_NAME) or f"Tesla {vin[-4:]}"

            # Validate VIN format (17 characters, alphanumeric)
            if len(vin) != 17 or not vin.isalnum():
                errors[CONF_VIN] = "invalid_vin"
            else:
                # Store data for pairing flow
                self.context["vin"] = vin
                self.context["name"] = name

                # Generate keys for pairing
                from .crypto import _import_crypto_modules, TeslaCrypto
                _import_crypto_modules()  # Import crypto modules first
                crypto = TeslaCrypto()
                crypto.generate_private_key()

                self.context["private_key"] = crypto.get_private_key_bytes().hex()
                self.context["public_key"] = crypto.get_public_key_bytes().hex()

                # Move to device discovery step
                return await self.async_step_device_discovery()

        # Show form
        schema = vol.Schema({
            vol.Required(CONF_VIN): str,
            vol.Optional(CONF_NAME): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "name": (
                    self._discovered_device.name
                    if self._discovered_device
                    else "Tesla Vehicle"
                )
            },
        )

    async def _async_scan_for_tesla_devices(
        self, vin: str
    ) -> list[BluetoothServiceInfoBleak]:
        """Scan for Tesla BLE devices matching the VIN (ESPHome pattern)."""
        discovered_devices = []
        expected_name = get_vin_advertisement_name(vin)

        _LOGGER.debug("Looking for Tesla with advertisement name: %s", expected_name)

        # Get all discovered devices
        for service_info in async_discovered_service_info(self.hass):
            if self._is_tesla_device(service_info, expected_name):
                discovered_devices.append(service_info)

        return discovered_devices

    def _is_tesla_device(self, service_info: BluetoothServiceInfoBleak, expected_name: str) -> bool:
        """Check if the device matches the expected Tesla VIN advertisement name (ESPHome pattern)."""
        device_name = service_info.name or service_info.device.name or ""
        return device_name == expected_name

    async def _async_step_device_selection(
        self,
        devices: list[BluetoothServiceInfoBleak],
        vin: str,
        name: str,
    ) -> ConfigFlowResult:
        """Handle device selection when multiple devices are found."""
        device_options = {}
        for device in devices:
            device_name = device.name or device.device.name or device.address
            device_options[device.address] = f"{device_name} ({device.address})"

        schema = vol.Schema({
            vol.Required("device"): vol.In(device_options),
        })

        return self.async_show_form(
            step_id="device_selection",
            data_schema=schema,
            description_placeholders={
                "vin": vin,
                "name": name,
            },
        )

    async def async_step_device_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device selection."""
        if user_input is not None:
            address = user_input["device"]

            # Get stored VIN and name from context
            vin = self.context.get("vin", "")
            name = self.context.get("name", f"Tesla {vin[-4:]}")

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            # Generate keys for the device
            from .crypto import _import_crypto_modules, TeslaCrypto
            _import_crypto_modules()  # Import crypto modules first
            crypto = TeslaCrypto()
            crypto.generate_private_key()

            private_key_hex = crypto.get_private_key_bytes().hex()
            public_key_hex = crypto.get_public_key_bytes().hex()

            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                    CONF_VIN: vin,
                    CONF_NAME: name,
                    CONF_PRIVATE_KEY: private_key_hex,
                    CONF_PUBLIC_KEY: public_key_hex,
                },
            )

        return self.async_abort(reason="unknown")

    async def async_step_device_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device discovery step."""
        if user_input is not None:
            # User confirmed to proceed with discovery
            return await self.async_step_find_device()

        return self.async_show_form(
            step_id="device_discovery",
            description_placeholders={
                "vin": self.context["vin"],
            },
        )

    async def async_step_find_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Find Tesla device by scanning for BLE devices."""
        # Use discovered device if available
        if self._discovered_device:
            address = self._discovered_device.address
            self.context["address"] = address
            return await self.async_step_pairing_instructions()

        # Scan for Tesla devices
        discovered_devices = await self._async_scan_for_tesla_devices(self.context["vin"])

        if not discovered_devices:
            return self.async_show_form(
                step_id="device_discovery",
                errors={"base": "no_devices_found"},
                description_placeholders={
                    "vin": self.context["vin"],
                },
            )
        elif len(discovered_devices) == 1:
            # Single device found
            device = discovered_devices[0]
            self.context["address"] = device.address
            return await self.async_step_pairing_instructions()
        else:
            # Multiple devices - let user choose
            self.context["discovered_devices"] = discovered_devices
            return await self.async_step_select_device()

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let user select from multiple discovered devices."""
        if user_input is not None:
            address = user_input["device"]
            self.context["address"] = address
            return await self.async_step_pairing_instructions()

        # Create device selection options
        device_options = {}
        for device in self.context["discovered_devices"]:
            device_name = device.name or device.device.name or device.address
            device_options[device.address] = f"{device_name} ({device.address})"

        schema = vol.Schema({
            vol.Required("device"): vol.In(device_options),
        })

        return self.async_show_form(
            step_id="select_device",
            data_schema=schema,
            description_placeholders={
                "vin": self.context["vin"],
            },
        )

    async def async_step_pairing_instructions(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show pairing instructions to user."""
        if user_input is not None:
            # User confirmed they're ready to pair
            return await self.async_step_pair_device()

        return self.async_show_form(
            step_id="pairing_instructions",
            description_placeholders={
                "vin": self.context["vin"],
                "address": self.context["address"],
            },
        )

    async def async_step_pair_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Execute the actual pairing process (YaleXS pattern)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = self.context["address"]
            private_key = self.context["private_key"]
            public_key = self.context["public_key"]
            vin = self.context["vin"]
            name = self.context["name"]

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            # Perform Tesla key exchange validation (YaleXS pattern)
            if not (
                errors := await async_validate_tesla_or_error(
                    address, vin, private_key, public_key, self.hass
                )
            ):
                # Key exchange successful - capture data and request polling settings
                self._pending_entry_title = name
                self._pending_entry_data = {
                    CONF_ADDRESS: address,
                    CONF_VIN: vin,
                    CONF_NAME: name,
                    CONF_PRIVATE_KEY: private_key,
                    CONF_PUBLIC_KEY: public_key,
                }
                return await self.async_step_polling()

        # Show pairing form initially or with errors after failed validation
        return self.async_show_form(
            step_id="pair_device",
            errors=errors,
            description_placeholders={
                "vin": self.context["vin"],
                "address": self.context["address"],
            },
        )

    async def async_step_polling(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect polling preferences before creating the entry."""
        if self._pending_entry_data is None or self._pending_entry_title is None:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            options = _sanitize_polling_options(user_input)
            return self.async_create_entry(
                title=self._pending_entry_title,
                data=self._pending_entry_data,
                options=options,
            )

        schema = _build_polling_schema({})
        return self.async_show_form(
            step_id="polling",
            data_schema=schema,
            description_placeholders={
                "name": self._pending_entry_title,
            },
        )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    address = data[CONF_ADDRESS]
    vin = data[CONF_VIN]

    # Check if BLE device is available
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address.upper(), connectable=True
    )

    if not ble_device:
        raise ValueError("Cannot connect to device")

    return {"title": f"Tesla {vin[-4:]}"}


class TeslaBleOptionsFlow(OptionsFlow):
    """Handle Tesla BLE options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            options = _sanitize_polling_options(user_input)
            return self.async_create_entry(title="", data=options)

        current = self.config_entry.options or {}
        schema = _build_polling_schema(current)

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "name": self.config_entry.title,
            },
        )
