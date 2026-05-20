"""Tesla BLE Data Update Coordinator."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from .device import TeslaBleDevice

_LOGGER = logging.getLogger(__name__)

DEVICE_STARTUP_TIMEOUT = 30

type TeslaBleConfigEntry = ConfigEntry[TeslaBleDataUpdateCoordinator]


class TeslaBleDataUpdateCoordinator(ActiveBluetoothDataUpdateCoordinator[None]):
    """Class to manage fetching Tesla BLE data."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        entry_id: str,
        ble_device: BLEDevice,
        device: TeslaBleDevice,
        base_unique_id: str,
        device_name: str,
    ) -> None:
        """Initialize Tesla BLE data updater."""
        super().__init__(
            hass=hass,
            logger=logger,
            address=ble_device.address,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_update,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            connectable=True,
        )
        self.ble_device = ble_device
        self.device = device
        self.device_name = device_name
        self.entry_id = entry_id
        self.base_unique_id = base_unique_id or entry_id
        self._ready_event = asyncio.Event()
        self._was_unavailable = True
        self._last_update_time = 0
        self._pending_service_info: bluetooth.BluetoothServiceInfoBleak | None = None
        self._periodic_poll_cancel = None

        # Register callback so device can trigger coordinator updates when data changes
        self.device.set_data_update_callback(self._handle_data_update)

        # Schedule check for pending poll once HA is running
        hass.bus.async_listen_once(
            "homeassistant_started",
            self._async_process_pending_poll
        )

        # Start periodic polling timer
        self._start_periodic_poll()

    def _start_periodic_poll(self) -> None:
        """Start periodic polling to maintain connection and get updates."""
        @callback
        def _periodic_poll_timer(_now=None) -> None:
            """Trigger periodic poll."""
            # Create a fake service_info to trigger poll
            if self.ble_device and self.hass.state == CoreState.running:
                _LOGGER.debug("Periodic poll timer triggered, scheduling update")
                # Directly call device.update() to poll VCSEC
                self.hass.async_create_task(self.device.update())

        # Start timer - poll at the device's update interval
        self._periodic_poll_cancel = async_track_time_interval(
            self.hass,
            _periodic_poll_timer,
            timedelta(seconds=self.device.update_interval)
        )
        _LOGGER.debug("Started periodic polling every %s seconds", self.device.update_interval)

    @callback
    def _needs_poll(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        seconds_since_last_poll: float | None,
    ) -> bool:
        """Determine if we need to poll the device."""
        # Allow polling during startup or when running, but not if not_running or stopped
        hass_ready = self.hass.state in (CoreState.starting, CoreState.running)
        connectable = bool(
            bluetooth.async_ble_device_from_address(
                self.hass, service_info.device.address, connectable=True
            )
        )
        time_check = (
            seconds_since_last_poll is None
            or seconds_since_last_poll >= self.device.update_interval
        )

        # If HA not ready yet but we should poll, buffer the request
        if not hass_ready and connectable and time_check:
            _LOGGER.debug(
                "_needs_poll: HA not ready (state=%s), buffering poll request",
                self.hass.state
            )
            self._pending_service_info = service_info
            return False

        result = hass_ready and connectable and time_check

        _LOGGER.debug(
            "_needs_poll: hass_ready=%s (state=%s), connectable=%s, time_check=%s (%.1fs since last), result=%s",
            hass_ready, self.hass.state, connectable, time_check, seconds_since_last_poll or 0, result
        )

        return result

    @callback
    def _async_process_pending_poll(self, _event=None) -> None:
        """Process pending poll request when HA is ready."""
        if self._pending_service_info:
            _LOGGER.debug("Processing buffered poll request now that HA is started")
            service_info = self._pending_service_info
            self._pending_service_info = None
            # Trigger poll by calling _async_update as a task
            self.hass.async_create_task(self._async_update(service_info))

    async def _async_update(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Poll the device."""
        _LOGGER.debug("Coordinator _async_update called, calling device.update()...")
        try:
            await self.device.update()
            # Note: Coordinator updates are triggered by device callbacks when data changes
            # See _handle_data_update() which is called from device
            _LOGGER.debug("Coordinator _async_update completed successfully")
        except Exception as ex:
            _LOGGER.warning("Error updating Tesla device: %s", ex, exc_info=True)

    @callback
    def _handle_data_update(self) -> None:
        """Handle data update from device."""
        _LOGGER.debug("Data update callback triggered from device")
        # Notify entities that device data has been updated
        # ActiveBluetoothDataUpdateCoordinator uses async_update_listeners, not async_set_updated_data
        self.async_update_listeners()

    @callback
    def _async_handle_unavailable(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""
        super()._async_handle_unavailable(service_info)
        self._was_unavailable = True
        self.device.set_ble_available(False)
        _LOGGER.info("Tesla device %s is unavailable (out of BLE range)", self.device_name)

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        _LOGGER.debug("_async_handle_bluetooth_event called, change=%s, address=%s", change, service_info.device.address)
        self.ble_device = service_info.device

        # Device is in range since we're receiving advertisements
        self.device.set_ble_available(True)

        # Update device with new BLE device and advertisement data (Yale pattern)
        self.device.update_advertisement(service_info.device, service_info.advertisement)
        if hasattr(service_info, "rssi") and service_info.rssi is not None:
            self.device.update_signal_strength(service_info.rssi)

        # Set ready when we first see the device
        if not self._ready_event.is_set():
            self._ready_event.set()

        if self._was_unavailable:
            self._was_unavailable = False
            _LOGGER.info("Tesla device %s is online", self.device_name)

        super()._async_handle_bluetooth_event(service_info, change)

    async def async_wait_ready(self) -> bool:
        """Wait for the device to be ready."""
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(DEVICE_STARTUP_TIMEOUT):
                await self._ready_event.wait()
                return True
        return False

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if self._periodic_poll_cancel:
            self._periodic_poll_cancel()
            self._periodic_poll_cancel = None
        _LOGGER.debug("Coordinator shutdown complete")
