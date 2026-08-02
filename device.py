"""Tesla BLE Device implementation."""

from __future__ import annotations

import asyncio
import base64
import logging
from collections import deque
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakError,
    establish_connection,
    close_stale_connections_by_address,
    get_device,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components import bluetooth
from homeassistant.helpers.storage import Store

from .const import (
    CHARGING_STATE_CHARGING,
    CHARGING_STATE_COMPLETE,
    CHARGING_STATE_DISCONNECTED,
    CHARGING_STATE_STOPPED,
    COMMAND_TIMEOUT,
    MAX_LATENCY,
    DEFAULT_BLE_DISCONNECTED_MIN_TIME,
    DEFAULT_FAST_POLL_IF_UNLOCKED,
    DEFAULT_POLL_ASLEEP_PERIOD,
    DEFAULT_POLL_CHARGING_PERIOD,
    DEFAULT_POLL_DATA_PERIOD,
    DEFAULT_POST_WAKE_POLL_TIME,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_WAKE_ON_BOOT,
    READ_UUID,
    SERVICE_UUID,
    SHIFT_STATE_DRIVE,
    SHIFT_STATE_INVALID,
    SHIFT_STATE_NEUTRAL,
    SHIFT_STATE_PARK,
    SHIFT_STATE_REVERSE,
    VEHICLE_STATE_ASLEEP,
    VEHICLE_STATE_AWAKE,
    WRITE_UUID,
)
from .messages import (
    MAX_MESSAGE_LENGTH,
    FramingError,
    IncompleteMessageError,
    TeslaMessageDecoder,
)
from .protocol import (
    ACTION_SPECIFICS,
    ActionMessageDetail,
    AllowedMsg,
    BLECarServerVehicleAction,
    BLECommand,
    BLECommandState,
    FOLLOW_UP_ACTION,
    GetOnSet,
    UniversalMessageDomain,
)
from .protocol_client import ParsedCarServerResponse, TeslaBleProtocolClient

SESSION_RETRY_INTERVAL = 1.0
MAX_SESSION_RETRIES = 3
WAKE_RETRY_INTERVAL = 5.0
MAX_WAKE_RETRIES = 3
MAX_RESPONSE_RETRIES = 3  # 3 retries = 4 total attempts (5s timeout each = 20s max)
MAX_REQUEUE_ATTEMPTS = 3  # Maximum times to re-queue a HIGH priority command after timeout
FOLLOW_UP_DELAY = 1.0
FOLLOW_UP_DELAY_MECHANICAL = 3.0  # Delay for mechanical actuators (charge port, trunk, etc)
SESSION_RETRY_MAX_DELAY = 8.0
WAKE_RETRY_MAX_DELAY = 20.0
VCSEC_STALE_THRESHOLD = 180  # seconds without VCSEC responses before assuming asleep

# Hard cap on buffered, undecoded notification bytes. Must exceed MAX_MESSAGE_LENGTH
# (a single legitimate frame has to fit) with headroom for a few queued frames,
# while still bounding memory if the stream desynchronises. Exceeding it forces a
# resync. This is the backstop; the length-prefix check usually resyncs first.
MAX_RX_BUFFER = 4 * MAX_MESSAGE_LENGTH
# Minimum gap between decode-failure recoveries. Recovery invalidates both domain
# sessions, so running it per failed packet (as the old code did) meant ~1 full
# session teardown per second during a desync storm.
DECODE_RECOVERY_COOLDOWN = 30.0

# Connection optimization constants
CONNECTION_TIMEOUT = 10.0  # Timeout for BLE connection attempts (default bleak is 20s)

# Proxy rotation: when a car is reachable by multiple ESPHome BLE proxies, flip away
# from a proxy that keeps failing instead of retrying the same one forever. Cooldowns use a
# monotonic clock and grow exponentially per proxy (capped), so a flaky proxy is benched longer
# each time it fails — but it is ALWAYS released again once its cooldown expires. We never
# permanently exclude a proxy, so we can't end up sitting dead with no proxy we're willing to try.
PROXY_FLIP_FAILURE_THRESHOLD = 3  # consecutive connect failures before rotating proxies
PROXY_COOLDOWN_BASE = 90.0  # base seconds to bench a proxy after a failure (decoupled from poll periods)
PROXY_COOLDOWN_MAX = 600.0  # cap on the per-proxy exponential backoff

# Push an entity refresh from advertisements at most this often, so the BLE RSSI sensor
# stays current even while the car is unreachable (no command completions to drive updates).
# Teslas advertise several times/sec across all proxies, so this must be throttled.
RSSI_PUSH_INTERVAL = 10.0  # seconds between advertisement-driven entity refreshes


class DomainQueueState:
    """Track commands and execution state for a protocol domain."""

    def __init__(self) -> None:
        self.high: deque[BLECommand] = deque()
        self.normal: deque[BLECommand] = deque()
        self.current_command: BLECommand | None = None

    def iter_all(self) -> list[BLECommand]:
        commands: list[BLECommand] = []
        if self.current_command is not None:
            commands.append(self.current_command)
        commands.extend(self.high)
        commands.extend(self.normal)
        return commands

    def add_command(self, command: BLECommand, priority: int) -> None:
        if priority > 0:
            self.high.append(command)
        else:
            self.normal.append(command)

    def has_pending(self) -> bool:
        return bool(self.current_command) or bool(self.high) or bool(self.normal)

    def peek(self) -> BLECommand | None:
        if self.current_command is not None:
            return self.current_command
        if self.high:
            self.current_command = self.high[0]
        elif self.normal:
            self.current_command = self.normal[0]
        return self.current_command

    def pop_current(self) -> BLECommand | None:
        command = self.current_command
        if command is None:
            return None
        if self.high and self.high[0] is command:
            self.high.popleft()
        elif self.normal and self.normal[0] is command:
            self.normal.popleft()
        self.current_command = None
        return command

    def clear(self) -> None:
        """Clear all queued commands."""
        self.high.clear()
        self.normal.clear()
        self.current_command = None

    def remove_low_priority_by_action(self, action: BLECarServerVehicleAction) -> int:
        """Remove all LOW priority (polling) queued commands matching the given action.

        Used when starting a delayed follow-up GET for mechanical actions to prevent
        stale polling responses from overwriting optimistic state updates.

        Returns the number of commands removed.
        """
        normal_before = len(self.normal)
        self.normal = deque([cmd for cmd in self.normal if cmd.action != action])
        return normal_before - len(self.normal)


CHARGING_STATE_LOOKUP = {
    "Starting": CHARGING_STATE_CHARGING,
    "Charging": CHARGING_STATE_CHARGING,
    "Complete": CHARGING_STATE_COMPLETE,
    "Stopped": CHARGING_STATE_STOPPED,
    "Disconnected": CHARGING_STATE_DISCONNECTED,
    "Idle": CHARGING_STATE_STOPPED,
}

SHIFT_STATE_LOOKUP = {
    "Park": SHIFT_STATE_PARK,
    "Drive": SHIFT_STATE_DRIVE,
    "Reverse": SHIFT_STATE_REVERSE,
    "Neutral": SHIFT_STATE_NEUTRAL,
    "Invalid": SHIFT_STATE_INVALID,
}

DEFROST_ACTIVE_STATES = {"Normal", "Max"}
SENTRY_ACTIVE_STATES = {"Idle", "Armed", "Aware", "Panic", "Quiet"}

_LOGGER = logging.getLogger(__name__)


BLE_WRITE_MAX_ATTEMPTS = 1  # Fail fast - single attempt, command timeout handles retry
BLE_WRITE_RETRY_BACKOFF = 0.3
BLE_WRITE_TIMEOUT = 5.0  # Allow longer BLE writes before transport-level retry kicks in
BLE_ATT_HEADER_SIZE = 3  # ATT opcode + handle overhead deducted from the MTU
BLE_DEFAULT_CHUNK_SIZE = 20  # Payload of the guaranteed 23-byte minimum ATT MTU


class TeslaBleDevice:
    """Tesla BLE device implementation."""

    # Infotainment polling cycle - commands are queued in this order
    INFOTAINMENT_POLL_CYCLE = [
        ("get_charge_state", BLECarServerVehicleAction.GET_CHARGE_STATE),
        ("get_climate_state", BLECarServerVehicleAction.GET_CLIMATE_STATE),
        ("get_drive_state", BLECarServerVehicleAction.GET_DRIVE_STATE),
        ("get_closures_state", BLECarServerVehicleAction.GET_CLOSURES_STATE),
        ("get_tire_pressure_state", BLECarServerVehicleAction.GET_TIRE_PRESSURE_STATE),
    ]

    def __init__(
        self,
        ble_device: BLEDevice | None = None,
        address: str | None = None,
        vin: str | None = None,
        private_key: bytes | str | None = None,
        public_key: bytes | str | None = None,
        hass: HomeAssistant | None = None,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize Tesla BLE device."""
        self.ble_device = ble_device
        self.address = address
        self.vin = vin
        self.hass = hass
        self._config_entry: ConfigEntry | None = entry
        self._data_update_callback: Callable[[], None] | None = None
        # Every log line carries this so multi-vehicle installs can tell which car
        # emitted it — previously two vehicles produced byte-identical messages.
        self._log_prefix = f"[{vin[-6:]}] " if vin else ""

        # Handle key formats - convert bytes to hex strings for storage
        if isinstance(private_key, bytes):
            self.private_key = private_key.hex()
        else:
            self.private_key = private_key

        if isinstance(public_key, bytes):
            self.public_key = public_key.hex()
        else:
            self.public_key = public_key

        # Storage for session data
        self._storage_key = f"tesla_ble_{vin.lower()}"
        self._store: Store | None = None
        if hass:
            self._store = Store(hass, 1, self._storage_key)
        self._session_blobs: dict[str, str] = {}
        self._persistent_state_loaded = False
        self._save_task: asyncio.Task | None = None
        self._save_state_lock = asyncio.Lock()

        # Device state
        self.data: dict[str, Any] = {}
        self.data["ble_rssi"] = None
        # True when BLE connections are failing (out of slots / connect timeout). Distinct from
        # is_asleep: a charging car that we simply can't reach must NOT be reported as asleep.
        self.data["ble_unreachable"] = False
        self.last_update_time = time.time()  # Initialize to now so entities are available immediately
        self._ble_available = True  # Track BLE availability from coordinator
        self.is_connected = False
        self._notifications_started = False
        self.vehicle_state = VEHICLE_STATE_ASLEEP

        # BLE communication
        self._client: BleakClientWithServiceCache | None = None
        self._domain_queues = {
            UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY: DomainQueueState(),
            UniversalMessageDomain.DOMAIN_INFOTAINMENT: DomainQueueState(),
        }
        # Per-domain async locks — replaces DomainQueueState.processing boolean (TOCTOU race)
        self._queue_locks: dict[UniversalMessageDomain, asyncio.Lock] = {
            domain: asyncio.Lock() for domain in self._domain_queues
        }
        # Lock guarding _response_buffer reads/mutations across awaits
        self._buffer_lock = asyncio.Lock()
        # Lock guarding key_manager / protocol_client (re)initialization
        self._crypto_lock = asyncio.Lock()
        # True only after _initialize_crypto fully succeeds with a usable private key
        self._crypto_ready: bool = False
        # Tracked tasks so we can log their exceptions and cancel them on unload
        self._background_tasks: set[asyncio.Task] = set()
        # Track GET actions we're ignoring responses for during mechanical delays
        # When a mechanical SET completes, we delay the follow-up GET to allow physical
        # action to complete. During this delay, we ignore any stale polling GET responses.
        self._ignored_get_actions: set[BLECarServerVehicleAction] = set()
        self._response_buffer = bytearray()
        # Serialises whole outbound messages so two multi-chunk writes can never
        # interleave on the characteristic (which would desync the car's own
        # reassembler, not just ours).
        self._write_lock = asyncio.Lock()
        self._write_with_response = True
        self._decode_recovery_task: asyncio.Task | None = None
        # Decode-failure bookkeeping: recovery is debounced and repeat failures are
        # logged once per episode rather than once per BLE notification.
        self._decode_failures: int = 0
        self._decode_failure_started: float = 0.0
        self._last_decode_recovery: float = 0.0
        self._last_vcsec_update: float = 0.0
        self._was_out_of_range: bool = False  # Track if vehicle was out of range in previous cycle

        # Connection health tracking
        self._consecutive_connection_failures: int = 0
        self._last_successful_connection: float = 0.0
        self._last_advertisement_time: float = 0.0
        self._connection_in_progress: bool = False
        # Throttle for advertisement-driven entity refreshes (monotonic clock).
        self._last_rssi_push: float = 0.0
        # Proxy rotation state. In-memory by design: cooldowns track live connectivity, so
        # on restart the next cycle re-evaluates every proxy from scratch (best-RSSI first).
        # Timers use the monotonic clock so a wall-clock/NTP jump can't prematurely release a
        # benched proxy or trip the staleness threshold.
        self._current_proxy_source: str | None = None  # proxy of the device we're using
        self._proxy_cooldowns: dict[str, float] = {}  # proxy source -> monotonic time it may be retried
        self._proxy_fail_streaks: dict[str, int] = {}  # proxy source -> consecutive failures (drives backoff)
        self._proxy_flip_logged: bool = False  # INFO-log first flip per streak, DEBUG the rest

        # Cryptography and session management (initialized later to avoid blocking)
        self.key_manager = None
        self.protocol_client: TeslaBleProtocolClient | None = None

        # Pairing state tracking
        self._pairing_complete = False
        self._pairing_success = False
        self._pairing_failure_reason: str | None = None
        self._pairing_wait_info: int | None = None
        self._pairing_error_info: int | None = None

        # Polling configuration and cadence state. Initialised here so the object is
        # fully formed at construction; load_polling_parameters() overwrites these from
        # the config entry options during setup. These used to be initialised only
        # inside _recover_from_decode_failure, which made a decode failure silently
        # reset the user's configured polling — and left should_poll() raising
        # AttributeError on any path that ran before a decode failure.
        self.update_interval = DEFAULT_UPDATE_INTERVAL
        self.post_wake_poll_time = DEFAULT_POST_WAKE_POLL_TIME
        self.poll_data_period = DEFAULT_POLL_DATA_PERIOD
        self.poll_asleep_period = DEFAULT_POLL_ASLEEP_PERIOD
        self.poll_charging_period = DEFAULT_POLL_CHARGING_PERIOD
        self.ble_disconnected_min_time = DEFAULT_BLE_DISCONNECTED_MIN_TIME
        self.fast_poll_if_unlocked = bool(DEFAULT_FAST_POLL_IF_UNLOCKED)
        self.wake_on_boot = bool(DEFAULT_WAKE_ON_BOOT)
        self._last_wake_time = 0
        self._car_just_woken = False
        self._is_charging = False
        self._charging_just_started = False
        self._last_poll_time = 0

        # Protocol components
        self.decoder = TeslaMessageDecoder()

        # Optional BLE message logging to file for debugging
        self._ble_log_path: Path | None = None
        if hass and _LOGGER.isEnabledFor(logging.DEBUG):
            try:
                self._ble_log_path = Path(hass.config.path("tesla_ble_ble.log"))
            except Exception:  # pragma: no cover - defensive logging setup
                self._ble_log_path = None

    def _queue_state(self, domain: UniversalMessageDomain) -> DomainQueueState:
        return self._domain_queues[domain]

    def _active_command(self, domain: UniversalMessageDomain) -> BLECommand | None:
        return self._domain_queues[domain].current_command

    def _queue_length(self, domain: UniversalMessageDomain) -> int:
        state = self._domain_queues[domain]
        length = len(state.high) + len(state.normal)
        if state.current_command is not None:
            length += 1
        return length

    def _cancel_command_timeout(self, command: BLECommand) -> None:
        """Cancel any scheduled timeout watchdog for the command."""
        handle = getattr(command, "timeout_handle", None)
        if handle is not None:
            handle.cancel()
            command.timeout_handle = None

    def _schedule_command_timeout(self, domain: UniversalMessageDomain, command: BLECommand) -> None:
        """Ensure the domain queue runs exactly when a command should time out."""
        self._cancel_command_timeout(command)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Running outside of event loop (unlikely), skip watchdog
            return

        delay = COMMAND_TIMEOUT / 1000

        def _timeout_callback() -> None:
            # Guard against late callbacks after the command completed
            command.timeout_handle = None
            queue_state = self._queue_state(domain)
            if queue_state.current_command is command and command.state == BLECommandState.WAITING_FOR_RESPONSE:
                self._spawn_task(self._process_domain_queue(domain), f"timeout_kick.{domain.name}")

        command.timeout_handle = loop.call_later(delay, _timeout_callback)

    def _handle_decode_failure(self) -> None:
        """Kick off recovery when we fail to parse an incoming protobuf message.

        Debounced: recovery invalidates both domain sessions and issues two
        SessionInfo requests, so firing it per failed packet turned a single
        desync into ~1 full session teardown per second. One recovery per
        DECODE_RECOVERY_COOLDOWN is enough to resynchronise.
        """
        if self._decode_recovery_task is not None and not self._decode_recovery_task.done():
            return

        now = time.monotonic()
        if now - self._last_decode_recovery < DECODE_RECOVERY_COOLDOWN:
            _LOGGER.debug(
                "%sSkipping decode recovery; last ran %.1fs ago (cooldown %.0fs)",
                self._log_prefix,
                now - self._last_decode_recovery,
                DECODE_RECOVERY_COOLDOWN,
            )
            return

        self._last_decode_recovery = now
        self._decode_recovery_task = self._spawn_task(
            self._recover_from_decode_failure(), "decode_recovery"
        )

    def _assume_asleep_if_vcsec_stale(self) -> None:
        """Infer vehicle state from VCSEC silence — but only call it 'asleep' when that's plausible.

        A sleeping Tesla still advertises and answers VCSEC once a connect succeeds, so silence
        that coincides with connection failures means the car is *unreachable over BLE*, not
        asleep. Reporting asleep there would lie about a car that may be wide awake and charging
        (the exact failure we hit: 'out of connection slots' / connect timeout for hours while the
        car charged). In that case we raise ble_unreachable and leave the last authoritative sleep
        state untouched. Only genuine silence with no connection errors is treated as sleep.
        """
        if self._last_vcsec_update == 0:
            return

        now = time.monotonic()
        if now - self._last_vcsec_update < VCSEC_STALE_THRESHOLD:
            return

        # Silence caused by connection failures is a connectivity problem, not sleep.
        if self._consecutive_connection_failures > 0:
            if not self.data.get("ble_unreachable"):
                _LOGGER.warning(
                    "%sNo VCSEC response for %.1fs with %d consecutive connection failures; "
                    "flagging BLE unreachable (NOT asleep) — vehicle may be awake/charging",
                    self._log_prefix,
                    now - self._last_vcsec_update,
                    self._consecutive_connection_failures,
                )
            self.data["ble_unreachable"] = True
            return

        if not self.data.get("is_asleep", False):
            _LOGGER.debug(
                "No VCSEC response for %.1fs (threshold %.1fs); assuming vehicle asleep",
                now - self._last_vcsec_update,
                VCSEC_STALE_THRESHOLD,
            )
        self.data["is_asleep"] = True
        self.vehicle_state = VEHICLE_STATE_ASLEEP
        self._car_just_woken = False

    async def _recover_from_decode_failure(self) -> None:
        """Reset sessions and queues after a decode failure so commands can retry."""
        domains = (
            UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
            UniversalMessageDomain.DOMAIN_INFOTAINMENT,
        )

        if self.key_manager is not None:
            for domain in domains:
                self.key_manager.invalidate_session(int(domain))

        # Reset active commands so they'll request new sessions on retry
        for domain in domains:
            queue_state = self._queue_state(domain)
            for queued_command in queue_state.iter_all():
                if queued_command.state == BLECommandState.WAITING_FOR_RESPONSE:
                    self._cancel_command_timeout(queued_command)
                    queued_command.state = BLECommandState.READY

        # Proactively request fresh SessionInfo for both domains.
        # Failures here are non-fatal but should be visible — silent loss leaves
        # the integration stuck in the decode-failure loop.
        try:
            await self._send_session_info_request(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
        except Exception as ex:
            _LOGGER.warning(
                "%sUnable to send VCSEC SessionInfo after decode failure: %s", self._log_prefix, ex
            )
        try:
            await self._send_session_info_request(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
        except Exception as ex:
            _LOGGER.warning(
                "%sUnable to send Infotainment SessionInfo after decode failure: %s", self._log_prefix, ex
            )

        await self._process_domain_queue(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
        await self._process_domain_queue(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

        # NOTE: polling configuration and cadence state are deliberately NOT reset
        # here. They belong to the config entry (see load_polling_parameters) and to
        # the poll loop, not to transport recovery. Resetting them used to discard
        # the user's configured intervals on every stray byte, and zeroing
        # _last_poll_time forced an extra Infotainment poll per decode failure —
        # amplifying the very storm this function is trying to end.

    def load_polling_parameters(
        self,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        post_wake_poll_time: int = DEFAULT_POST_WAKE_POLL_TIME,
        poll_data_period: int = DEFAULT_POLL_DATA_PERIOD,
        poll_asleep_period: int = DEFAULT_POLL_ASLEEP_PERIOD,
        poll_charging_period: int = DEFAULT_POLL_CHARGING_PERIOD,
        ble_disconnected_min_time: int = DEFAULT_BLE_DISCONNECTED_MIN_TIME,
        fast_poll_if_unlocked: int = DEFAULT_FAST_POLL_IF_UNLOCKED,
        wake_on_boot: int = DEFAULT_WAKE_ON_BOOT,
    ) -> None:
        """Load polling parameters (matching ESPHome interface)."""
        self.update_interval = max(1, int(update_interval))
        self.post_wake_poll_time = post_wake_poll_time
        self.poll_data_period = poll_data_period
        self.poll_asleep_period = poll_asleep_period
        self.poll_charging_period = poll_charging_period
        self.ble_disconnected_min_time = ble_disconnected_min_time
        self.fast_poll_if_unlocked = bool(fast_poll_if_unlocked)
        self.wake_on_boot = bool(wake_on_boot)
        # Polling params live in the config entry options — no disk persistence here.
        _LOGGER.debug("Updated polling parameters")

    async def _ensure_persistent_state_loaded(self) -> None:
        """Load sessions from disk. Private key is loaded separately in _initialize_crypto.

        Why decoupled: an earlier version mixed key loading and Store loading and would
        latch _persistent_state_loaded=True on Store failure, permanently breaking the
        crypto path. Now Store failures are non-fatal — we just keep retrying next cycle.
        """
        if self._persistent_state_loaded or not self._store or self.key_manager is None:
            return

        try:
            stored = await self._store.async_load()
        except Exception as err:
            _LOGGER.warning("%sUnable to load Tesla BLE persistent state, will retry: %s", self._log_prefix, err)
            return  # Intentionally do NOT latch — let the next cycle try again.

        if stored:
            sessions = stored.get("sessions", {})
            if sessions:
                try:
                    self.key_manager.load_sessions(sessions)
                    # Only mirror to _session_blobs after a successful load so a save
                    # never writes empty over a non-empty disk copy.
                    self._session_blobs = sessions
                    _LOGGER.debug("Restored %d Tesla BLE sessions", len(sessions))
                except Exception as err:
                    _LOGGER.warning("%sFailed to restore Tesla BLE sessions: %s", self._log_prefix, err)
            # Polling parameters are sourced exclusively from the config entry options;
            # disk-store polling overrides removed to avoid divergence.

        self._persistent_state_loaded = True

    def _spawn_task(self, coro, name: str) -> asyncio.Task:
        """Create a tracked background task whose exceptions are logged.

        Why: ~12 sites used to call asyncio.create_task() with no done
        callback, so any failure (wake-poll queue push, follow-up GET,
        decode recovery, state save) vanished into the event loop. Routing
        them through this helper makes failures visible and lets unload
        cancel any in-flight tasks.
        """
        task = asyncio.create_task(coro, name=f"tesla_ble.{name}")
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        task.add_done_callback(self._log_task_exception)
        return task

    @staticmethod
    def _log_task_exception(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            _LOGGER.error(
                "Background task %s failed: %s",
                task.get_name(),
                exc,
                exc_info=exc,
            )

    def cancel_background_tasks(self) -> None:
        """Cancel any tracked background tasks (call on integration unload)."""
        for task in list(self._background_tasks):
            task.cancel()

    def _schedule_state_save(self) -> None:
        if not self._store:
            return
        if self._save_task and not self._save_task.done():
            return
        self._save_task = self._spawn_task(self._async_save_state(), "save_state")

    async def _async_save_state(self) -> None:
        if not self._store or self.key_manager is None:
            return
        async with self._save_state_lock:
            sessions = self.key_manager.serialize_sessions()
            self._session_blobs = sessions
            # Polling parameters live in the config entry options — single source of truth.
            payload = {"sessions": sessions}
            try:
                await self._store.async_save(payload)
            except Exception as err:
                _LOGGER.warning("%sFailed to persist Tesla BLE state: %s", self._log_prefix, err)

    async def _initialize_crypto(self) -> None:
        """Initialize crypto manager + protocol client and load the private key.

        Why: previously the private key was loaded only via _ensure_persistent_state_loaded,
        coupling key loading to Store I/O. Any Store failure flipped a one-shot latch True
        and left key_manager with no private key, causing a 10s-cadence
        "Private key not available" loop forever. The key load now lives here, raises on
        failure, and _crypto_ready gates downstream session-info sends.
        """
        async with self._crypto_lock:
            if self.key_manager is None:
                def _import_and_create_crypto():
                    from .crypto import _import_crypto_modules, TeslaKeyManager
                    _import_crypto_modules()
                    return TeslaKeyManager()

                if self.hass is not None:
                    self.key_manager = await self.hass.async_add_executor_job(_import_and_create_crypto)
                else:
                    loop = asyncio.get_running_loop()
                    self.key_manager = await loop.run_in_executor(None, _import_and_create_crypto)

            self.key_manager.set_vin(self.vin or "")

            if self.protocol_client is None:
                self.protocol_client = TeslaBleProtocolClient(self.key_manager, vin=self.vin or "")

            if self.private_key:
                current_key = getattr(self.key_manager.crypto, "_private_key", None)
                if current_key is None:
                    try:
                        key_bytes = bytes.fromhex(self.private_key)
                    except ValueError as err:
                        raise RuntimeError(
                            "Stored Tesla BLE private key is not valid hex"
                        ) from err
                    self.key_manager.crypto.load_private_key(key_bytes)
                    if self.public_key is None:
                        self.public_key = self.key_manager.get_public_key_data().hex()
                    _LOGGER.info("Loaded Tesla BLE private key for VIN %s", self.vin)

            self._crypto_ready = (
                getattr(self.key_manager.crypto, "_private_key", None) is not None
            )

        # Session/polling load happens outside the crypto lock — non-fatal on failure.
        await self._ensure_persistent_state_loaded()

    def _persist_keys_to_config_entry(self) -> None:
        """Write current private/public key into the config entry data dict.

        Why: pair_key may generate a fresh key when none exists. Without this
        persistence, the in-memory key is lost on integration reload and the
        just-paired device is unpaired on the next HA restart.
        """
        if self.hass is None or self._config_entry is None:
            return
        from .const import CONF_PRIVATE_KEY, CONF_PUBLIC_KEY

        entry = self._config_entry
        current_priv = entry.data.get(CONF_PRIVATE_KEY)
        current_pub = entry.data.get(CONF_PUBLIC_KEY)
        if current_priv == self.private_key and current_pub == self.public_key:
            return

        new_data = {
            **entry.data,
            CONF_PRIVATE_KEY: self.private_key,
            CONF_PUBLIC_KEY: self.public_key,
        }
        self.hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.info("Persisted Tesla BLE keys to config entry for VIN %s", self.vin)

    async def _reinitialize_crypto(self) -> None:
        """Reinitialize crypto with fresh instances after repeated session failures."""
        _LOGGER.info("Reinitializing crypto components with fresh instances")
        async with self._crypto_lock:
            self.key_manager = None
            self.protocol_client = None
            self._persistent_state_loaded = False
            self._crypto_ready = False
        # _initialize_crypto reacquires _crypto_lock; asyncio.Lock is non-reentrant, so
        # the reset and the recreation are deliberately separated.
        await self._initialize_crypto()

    def update_advertisement(self, ble_device: BLEDevice, advertisement_data) -> None:
        """Update the BLE device and advertisement data from any proxy."""
        old_device = self.ble_device
        self.ble_device = ble_device

        # Track when we last received an advertisement (for staleness detection)
        self._last_advertisement_time = time.time()

        # NOTE: do NOT reset _consecutive_connection_failures here. Teslas advertise
        # constantly, so resetting on every advertisement would erase the failure signal
        # between poll cycles and defeat proxy rotation. The counter is reset only on a
        # successful connect (_connect). BLE availability/recovery is handled separately
        # via set_ble_available and the _was_out_of_range path in update().

        # Log proxy changes for debugging
        _LOGGER.debug(
            "Updated BLE device to %s from advertisement via proxy",
            ble_device.address
        )

        rssi = getattr(ble_device, "rssi", None)
        if isinstance(rssi, int):
            self.update_signal_strength(rssi)

        # Push a throttled entity refresh so the RSSI sensor (and other coordinator-driven
        # entities) stay current from advertisements even when the car is unreachable and no
        # command completions are firing the callback. Throttled because Teslas advertise
        # several times/sec across every proxy.
        if self._data_update_callback is not None:
            now_mono = time.monotonic()
            if now_mono - self._last_rssi_push >= RSSI_PUSH_INTERVAL:
                self._last_rssi_push = now_mono
                self._data_update_callback()

        # If we have an active connection but device changed, we might need to reconnect
        # This handles proxy switching during active connections
        if (old_device and old_device != ble_device and
            self._client and not self._client.is_connected):
            _LOGGER.debug(
                "BLE device changed during connection, may need to reconnect"
            )

    async def _start_infotainment_polling(self) -> bool:
        """Start Infotainment polling cycle if not already running.

        Returns True if Infotainment was queued, False otherwise.
        """
        # Check if there's already an Infotainment command in the queue
        infotainment_queue = self._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
        has_infotainment_command = infotainment_queue.has_pending()

        if not has_infotainment_command:
            # On first wake, queue ALL infotainment commands immediately for fastest data refresh
            # If any timeout during wake, they'll be requeued at the back instead of discarded
            if self._car_just_woken:
                _LOGGER.debug("Car just woken - queuing all infotainment commands immediately")
                for name, action in self.INFOTAINMENT_POLL_CYCLE:
                    await self._queue_command(name, action, UniversalMessageDomain.DOMAIN_INFOTAINMENT)
            else:
                # Normal polling: queue first command, cycle continues after each completion
                name, action = self.INFOTAINMENT_POLL_CYCLE[0]
                await self._queue_command(name, action, UniversalMessageDomain.DOMAIN_INFOTAINMENT)
            return True

        _LOGGER.debug("Infotainment command already in queue, will queue next command after completion")
        return True

    def should_poll(self) -> bool:
        """Determine if we should poll Infotainment based on current state and timing.

        Note: VCSEC is always polled (handled in update()), this only gates Infotainment.
        Priority order matches ESPHome logic:
        1. Unlocked (with fast_poll_if_unlocked) or user present → use update_interval
        2. Charging → use poll_charging_period
        3. Just woken → use poll_data_period (for post_wake_poll_time duration)
        4. Asleep → use poll_asleep_period (if not 0)
        """
        now = time.time()
        time_since_last = now - self._last_poll_time

        # Priority 1: Fastest polling when unlocked (if enabled) or user present
        if (self.fast_poll_if_unlocked and not self.data.get("doors_locked", True)) or self.data.get("is_user_present", False):
            result = time_since_last >= self.update_interval
            _LOGGER.debug(
                "should_poll Infotainment: %s - UNLOCKED/USER_PRESENT (%.1fs since last, update interval %.1fs)",
                result, time_since_last, self.update_interval
            )
            return result

        # Priority 2: Charging polls
        # Match ESPHome: poll immediately on first charge detection, then at poll_charging_period interval
        if self._is_charging:
            # On first charge detection, poll immediately
            if self._charging_just_started:
                result = True
                _LOGGER.debug(
                    "should_poll Infotainment: %s - CHARGING (FIRST POLL - immediate)",
                    result
                )
            else:
                result = time_since_last >= self.poll_charging_period
                _LOGGER.debug(
                    "should_poll Infotainment: %s - CHARGING (%.1fs since last, charging period %.1fs)",
                    result, time_since_last, self.poll_charging_period
                )
            return result

        # Priority 3: Just woken polls (for post_wake_poll_time duration)
        # Match ESPHome: poll immediately on first wake, then at poll_data_period interval
        time_since_wake = now - self._last_wake_time
        if time_since_wake < self.post_wake_poll_time:
            # First poll after wake: immediate
            # Subsequent polls: use poll_data_period interval
            if self._car_just_woken:
                result = True
                _LOGGER.debug(
                    "should_poll Infotainment: %s - JUST_WOKEN (immediate on first detection)",
                    result
                )
            else:
                result = time_since_last >= self.poll_data_period
                _LOGGER.debug(
                    "should_poll Infotainment: %s - POST_WAKE (%.1fs since last, poll_data_period %.1fs, %.1fs since wake, post_wake_poll_time %.1fs)",
                    result, time_since_last, self.poll_data_period, time_since_wake, self.post_wake_poll_time
                )
            return result

        # Priority 4: Asleep polls (if poll_asleep_period not 0)
        is_asleep = self.data.get("is_asleep")
        if is_asleep is True and self.poll_asleep_period > 0:
            result = time_since_last >= self.poll_asleep_period
            _LOGGER.debug(
                "should_poll Infotainment: %s - ASLEEP (%.1fs since last, asleep period %.1fs)",
                result, time_since_last, self.poll_asleep_period
            )
            return result

        if is_asleep is True:
            _LOGGER.debug(
                "should_poll Infotainment: False - ASLEEP (poll_asleep_period disabled, %.1fs since last)",
                time_since_last,
            )
            return False

        # Priority 5: Normal awake polling when no higher priority matched
        result = time_since_last >= self.poll_data_period
        _LOGGER.debug(
            "should_poll Infotainment: %s - AWAKE (%.1fs since last, poll_data_period %.1fs)",
            result, time_since_last, self.poll_data_period
        )
        return result

    async def update(self) -> None:
        """Update device data with intelligent polling."""
        try:
            # Guard against partially constructed instances restored by HA reloads
            if not hasattr(self, "_last_poll_time"):
                self._last_poll_time = 0
            if not hasattr(self, "_is_charging"):
                self._is_charging = False
            if not hasattr(self, "_charging_just_started"):
                self._charging_just_started = False
            if not hasattr(self, "_car_just_woken"):
                self._car_just_woken = False
            if not hasattr(self, "_last_wake_time"):
                self._last_wake_time = 0
            if not hasattr(self, "_was_out_of_range"):
                self._was_out_of_range = False
            if not hasattr(self, "_ignored_get_actions"):
                self._ignored_get_actions = set()

            # Initialize crypto if needed (doesn't require BLE connection)
            await self._initialize_crypto()

            # Check if vehicle is in BLE range before proceeding
            # This prevents wasteful queue→execute→fail cycles when car is out of range
            if self.hass and self.address:
                in_range = bluetooth.async_address_present(self.hass, self.address, connectable=True)
                if not in_range:
                    _LOGGER.debug("Vehicle not in BLE range, clearing queues and skipping poll")
                    # Clear all stale commands from both domains
                    self._queue_state(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY).clear()
                    self._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT).clear()
                    self.is_connected = False
                    self._was_out_of_range = True
                    return
                elif self._was_out_of_range:
                    # Vehicle just came back into range - invalidate sessions and reinitialize crypto
                    # Sessions are likely stale after vehicle was gone
                    _LOGGER.info("Vehicle returned to BLE range after being away, invalidating sessions and reinitializing crypto")
                    if self.key_manager:
                        self.key_manager.invalidate_session(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
                        self.key_manager.invalidate_session(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
                    try:
                        await self._reinitialize_crypto()
                    except Exception as ex:
                        _LOGGER.error(
                            "%sCrypto reinitialization failed on returning to BLE range; will retry next cycle: %s", self._log_prefix,
                            ex,
                            exc_info=True,
                        )
                        return
                    self._was_out_of_range = False

            # Wake vehicle on boot if configured
            if self.wake_on_boot and self.last_update_time == 0:
                await self.wake_vehicle()

            # Always poll VCSEC to detect state changes (wake/sleep/lock status)
            # This is critical to detect when car wakes up
            # BLE connection and session establishment happen automatically in command queue processor
            _LOGGER.debug("Polling VCSEC for vehicle state...")
            await self._queue_command(
                "get_vehicle_state",
                BLECarServerVehicleAction.DO_NOTHING,
                UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY
            )

            # Process VCSEC command immediately so it always runs
            await self._process_domain_queue(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)

            self._assume_asleep_if_vcsec_stale()

            # Check if we should poll Infotainment based on timing and state
            _LOGGER.debug("Checking should_poll() for Infotainment polling...")
            should_poll_infotainment = self.should_poll()
            if not should_poll_infotainment:
                _LOGGER.debug("should_poll() returned False, processing in-flight queues only")
                await self._process_domain_queue(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
                # Ensure any in-flight Infotainment commands still progress (timeouts/retries)
                if self._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT).has_pending():
                    await self._process_domain_queue(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
                # DON'T update _last_poll_time here - that defeats the timing check!
                # Only update last_update_time to track that VCSEC poll happened
                self.last_update_time = time.time()
                return

            _LOGGER.debug("should_poll() returned True, checking if awake for Infotainment poll")

            # If awake, get additional data
            is_asleep = self.data.get("is_asleep", True)
            _LOGGER.debug("is_asleep check: is_asleep=%s, will_poll_infotainment=%s", is_asleep, not is_asleep)
            queued_infotainment = False
            if not is_asleep:
                queued_infotainment = await self._start_infotainment_polling()

            # Process pending commands for both domains
            await self._process_domain_queue(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
            await self._process_domain_queue(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

            # Update tracking variables
            self._last_poll_time = time.time()
            self.last_update_time = self._last_poll_time

            # Reset immediate poll flags ONLY after successfully queueing Infotainment commands
            # This ensures we don't lose the flag if car hasn't finished waking yet
            if queued_infotainment:
                if self._charging_just_started:
                    self._charging_just_started = False
                if self._car_just_woken:
                    self._car_just_woken = False

        except Exception as ex:
            _LOGGER.warning("%sError updating Tesla device: %s", self._log_prefix, ex, exc_info=True)
            self.is_connected = False

    def _proxy_cooldown_duration(self, source: str) -> float:
        """Exponential per-proxy backoff: longer after each consecutive failure, capped.

        Keyed on the proxy's failure streak so a chronically bad proxy is benched progressively
        longer (up to PROXY_COOLDOWN_MAX) while a momentarily-busy one returns quickly. Streaks
        reset on a successful connect, so a recovered proxy starts fresh.
        """
        streak = self._proxy_fail_streaks.get(source, 1)
        return min(PROXY_COOLDOWN_BASE * (2 ** (streak - 1)), PROXY_COOLDOWN_MAX)

    def _select_alternate_proxy_device(self) -> BLEDevice | None:
        """Pick a connectable BLEDevice from a proxy other than the one we keep failing on.

        Returns None when there's nothing better to try (single proxy, or no proxy data),
        in which case the caller keeps using the current device.
        """
        if not (self.hass and self.address):
            return None

        scanner_devices = bluetooth.async_scanner_devices_by_address(
            self.hass, self.address, connectable=True
        )
        _LOGGER.debug(
            "Proxy flip eval: %d connectable scanner(s) for %s: %s (current=%s, cooldowns=%s)",
            len(scanner_devices),
            self.address,
            [(sd.scanner.source, getattr(sd.advertisement, "rssi", None)) for sd in scanner_devices],
            self._current_proxy_source,
            list(self._proxy_cooldowns),
        )
        if len(scanner_devices) < 2:
            return None  # only one proxy sees the car — nothing to flip to

        now = time.monotonic()
        # Bench the proxy we've been failing on with an exponential backoff (longer each
        # consecutive flip-away, capped), then drop cooldowns that have since expired — that
        # expiry is how a benched proxy is automatically released back into rotation.
        if self._current_proxy_source:
            self._proxy_fail_streaks[self._current_proxy_source] = (
                self._proxy_fail_streaks.get(self._current_proxy_source, 0) + 1
            )
            self._proxy_cooldowns[self._current_proxy_source] = (
                now + self._proxy_cooldown_duration(self._current_proxy_source)
            )
        self._proxy_cooldowns = {
            source: until for source, until in self._proxy_cooldowns.items() if until > now
        }

        connectable = [sd for sd in scanner_devices if sd.scanner.connectable]
        candidates = [
            sd for sd in connectable if sd.scanner.source not in self._proxy_cooldowns
        ]
        if not candidates:
            # Every reachable proxy is still cooling down. Don't forgive them all at once (that
            # just thrashes); release only the one whose cooldown expires soonest, so we always
            # keep exactly one path forward and never sit dead with no proxy we'll try.
            if not connectable:
                return None
            soonest = min(
                connectable,
                key=lambda sd: self._proxy_cooldowns.get(sd.scanner.source, 0.0),
            )
            self._proxy_cooldowns.pop(soonest.scanner.source, None)
            candidates = [soonest]

        best = max(
            candidates,
            key=lambda sd: getattr(sd.advertisement, "rssi", -999) or -999,
        )
        if best.scanner.source != self._current_proxy_source:
            # Log the first flip of a failure streak at INFO so it's visible; subsequent
            # rotations (e.g. while a car is asleep and unreachable via any proxy) drop to
            # DEBUG to avoid per-cycle log spam. Re-armed on a successful connect.
            log = _LOGGER.info if not self._proxy_flip_logged else _LOGGER.debug
            log(
                "Flipping Tesla BLE proxy %s -> %s after %d consecutive failures (rssi=%s)",
                self._current_proxy_source,
                best.scanner.source,
                self._consecutive_connection_failures,
                getattr(best.advertisement, "rssi", None),
            )
            self._proxy_flip_logged = True
        self._current_proxy_source = best.scanner.source
        return best.ble_device

    async def _connect(self) -> None:
        """Connect to the Tesla BLE device using the best available handle."""
        _LOGGER.debug("_connect: self.ble_device=%s", self.ble_device)

        if self._client and self._client.is_connected:
            return

        if self._client:
            await self._disconnect()

        await self._initialize_crypto()

        address = self.address
        if address is None and self.ble_device:
            address = self.ble_device.address
        if address:
            address = address.upper()

        try:
            if address:
                await close_stale_connections_by_address(address)

            ble_device = self.ble_device
            _LOGGER.debug("_connect: ble_device from self=%s", ble_device)

            # Record which proxy delivered the device we're currently using BEFORE the flip
            # check, so the flip can cool that proxy down on the very first rotation.
            if self._current_proxy_source is None and self.hass and address:
                info = bluetooth.async_last_service_info(self.hass, address, connectable=True)
                if info is not None:
                    self._current_proxy_source = info.source

            # After repeated failures, rotate to a different connectable proxy that also
            # sees this car instead of retrying the same (likely flaky/overloaded) one.
            if self._consecutive_connection_failures >= PROXY_FLIP_FAILURE_THRESHOLD:
                alternate = self._select_alternate_proxy_device()
                if alternate is not None:
                    ble_device = alternate

            if ble_device is None and self.hass and address:
                ble_device = bluetooth.async_ble_device_from_address(
                    self.hass, address, connectable=True
                )

            if ble_device is None and address:
                ble_device = await get_device(address)

            if ble_device is None:
                raise RuntimeError("Unable to locate BLE device for Tesla")

            self.ble_device = ble_device
            self.address = ble_device.address

            _LOGGER.debug("_connect: calling establish_connection...")
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self.vin or self.address or (ble_device.address if ble_device else None),
                self._handle_disconnect,
                use_services_cache=True,
                ble_device_callback=lambda: self.ble_device,
                max_attempts=2,  # Reduced from 3 - faster failure detection
                timeout=CONNECTION_TIMEOUT,  # 10s instead of default 20s
            )
            _LOGGER.debug("_connect: establish_connection returned, client=%s, is_connected=%s",
                         self._client, self._client.is_connected if self._client else False)

            # Start every connection with an empty receive buffer. A torn frame left
            # over from the previous link would otherwise be prepended to the new
            # stream, permanently desynchronising a perfectly healthy connection.
            self._reset_response_buffer("connect")

            _LOGGER.debug("_connect: starting notifications...")
            await self._client.start_notify(READ_UUID, self._handle_notification)
            _LOGGER.debug("_connect: notifications started")

            if self.protocol_client:
                self.protocol_client.set_connection_id()

            self.is_connected = True
            self._notifications_started = True
            self._consecutive_connection_failures = 0  # Reset on success
            self._proxy_cooldowns.clear()  # this proxy works; forget prior cooldowns
            self._proxy_fail_streaks.clear()  # and reset their backoff streaks
            self._proxy_flip_logged = False  # re-arm INFO logging for the next streak
            self.data["ble_unreachable"] = False  # a successful connect proves we can reach the car
            self._last_successful_connection = time.time()
            _LOGGER.debug("Connected to Tesla BLE device %s via proxy %s",
                          ble_device.address, self._current_proxy_source)

        except (BleakError, TimeoutError, RuntimeError) as ex:
            _LOGGER.error("%sFailed to connect to Tesla device: %s", self._log_prefix, ex)
            self.is_connected = False
            self._notifications_started = False
            self._consecutive_connection_failures += 1
            _LOGGER.debug("Consecutive connection failures: %d", self._consecutive_connection_failures)
            if self._client:
                try:
                    await self._client.disconnect()
                except Exception:  # pragma: no cover
                    pass
                self._client = None
            raise

    def _reset_response_buffer(self, reason: str) -> None:
        """Drop any partially received frame; the byte stream is about to restart.

        Called on every connect/disconnect transition. Without this the buffer
        outlives the link it belongs to, so one torn frame poisons every subsequent
        connection and only an HA restart clears it.
        """
        if self._response_buffer:
            _LOGGER.debug(
                "%sDiscarding %d buffered RX byte(s) on %s",
                self._log_prefix,
                len(self._response_buffer),
                reason,
            )
            self._response_buffer.clear()
        self._decode_failures = 0
        self._decode_failure_started = 0.0

    def _handle_disconnect(self, client: BleakClientWithServiceCache) -> None:
        """Handle disconnection from BLE device."""
        _LOGGER.debug("%sDisconnected from Tesla BLE device", self._log_prefix)
        self.is_connected = False
        self._notifications_started = False
        self._client = None  # Clear stale client reference to force reconnect
        self._reset_response_buffer("disconnect callback")

    async def _disconnect(self) -> None:
        """Disconnect from the Tesla BLE device."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(READ_UUID)
            except Exception:
                pass  # Ignore errors during disconnection
            try:
                # Use 30-second timeout for disconnect to match ESPHome
                await self._client.disconnect()
            except Exception:
                pass  # Ignore errors during disconnection
        self.is_connected = False
        self._notifications_started = False
        self._client = None  # Clear client to prevent stale service cache issues
        self._reset_response_buffer("disconnect")

        if self.address:
            try:
                await close_stale_connections_by_address(self.address)
            except BleakError:
                _LOGGER.debug("Error closing stale connections for %s", self.address)

    async def _handle_notification(self, sender: int, data: bytes) -> None:
        """Handle BLE notification data.

        Extend is synchronous and atomic with respect to the event loop; the lock is
        only needed in _process_response_buffer where reads span awaits.
        """
        try:
            if self._ble_log_path:
                self._spawn_task(self._log_ble_bytes("RX", data), "log_ble_rx")
            self._response_buffer.extend(data)
            await self._process_response_buffer()
        except Exception as ex:
            _LOGGER.error("%sError handling notification: %s", self._log_prefix, ex, exc_info=True)

    async def _process_response_buffer(self) -> None:
        """Process accumulated response data, resynchronising on malformed frames.

        Why locked: reads/decodes span awaits during _handle_universal_message. Without
        the lock a concurrent invocation could read the same prefix twice.

        Why the whole examined window is discarded on a framing error: the stream is
        length-prefixed with no sync marker, so once it is misaligned no byte offset
        can be trusted. The previous implementation dropped a *single* leading byte
        and returned, consuming 1 byte per notification while each notification
        appended up to 20 — a guaranteed livelock that produced ~29k errors/19 days
        and never resynchronised. Snapshotting the length before the decode attempt
        (rather than calling clear()) guarantees we never discard bytes appended by a
        later notification while we were awaiting.

        A discarded response is safe: every command has a response timeout and retries.
        """
        async with self._buffer_lock:
            while self._response_buffer:
                # A real frame is at most MAX_MESSAGE_LENGTH; anything beyond this cap
                # means we are accumulating garbage, so reset rather than grow forever.
                if len(self._response_buffer) > MAX_RX_BUFFER:
                    dropped = len(self._response_buffer)
                    self._response_buffer.clear()
                    _LOGGER.warning(
                        "%sRX buffer exceeded %d bytes; discarded %d bytes and resynchronising",
                        self._log_prefix,
                        MAX_RX_BUFFER,
                        dropped,
                    )
                    self._handle_decode_failure()
                    return

                examined = len(self._response_buffer)
                try:
                    message, consumed = self.decoder.decode_universal_message(bytes(self._response_buffer))
                except IncompleteMessageError:
                    return
                except FramingError as ex:
                    # Expected when the stream is desynchronised. Discard exactly what
                    # we inspected — no await happens between the snapshot and this
                    # delete, so `examined` is still the live buffer length.
                    del self._response_buffer[:examined]
                    self._note_decode_failure(ex)
                    continue
                except Exception as ex:  # pragma: no cover - decoder bug, not a desync
                    # Never seen in practice; log with a traceback rather than
                    # quietly filing it as a framing problem, but still resync so a
                    # decoder bug cannot wedge the buffer.
                    _LOGGER.exception("%sUnexpected decoder failure", self._log_prefix)
                    del self._response_buffer[:examined]
                    self._note_decode_failure(ex)
                    continue

                del self._response_buffer[:consumed]
                self._note_decode_success()
                await self._handle_universal_message(message)

    def _note_decode_failure(self, ex: Exception) -> None:
        """Record a framing failure, logging once per episode instead of per packet.

        Per the logging-in-loops rule: first failure of an episode is ERROR, the rest
        are DEBUG, and _note_decode_success emits a single summary on recovery.
        """
        now = time.monotonic()
        if self._decode_failures == 0:
            self._decode_failure_started = now
            _LOGGER.error(
                "%sFailed to decode UniversalMessage: %s — resynchronising", self._log_prefix, ex
            )
        else:
            _LOGGER.debug(
                "%sFailed to decode UniversalMessage (%d in this episode): %s",
                self._log_prefix,
                self._decode_failures + 1,
                ex,
            )
        self._decode_failures += 1
        self._handle_decode_failure()

    def _note_decode_success(self) -> None:
        """Close out a decode-failure episode once a frame parses again."""
        if self._decode_failures == 0:
            return
        _LOGGER.warning(
            "%sResynchronised after %d decode failure(s) over %.1fs",
            self._log_prefix,
            self._decode_failures,
            time.monotonic() - self._decode_failure_started,
        )
        self._decode_failures = 0
        self._decode_failure_started = 0.0

    async def _handle_universal_message(self, message) -> None:
        """Route UniversalMessage to appropriate domain handlers."""

        domain = UniversalMessageDomain.DOMAIN_BROADCAST

        try:
            from_sub = message.from_destination.WhichOneof("sub_destination")
            if from_sub == "domain":
                domain = UniversalMessageDomain(message.from_destination.domain)
        except Exception:
            try:
                to_sub = message.to_destination.WhichOneof("sub_destination")
                if to_sub == "domain":
                    domain = UniversalMessageDomain(message.to_destination.domain)
            except Exception:
                domain = UniversalMessageDomain.DOMAIN_BROADCAST

        payload_type = message.WhichOneof("payload")

        # Handle SessionInfo first, THEN check for errors
        if payload_type == "session_info":
            await self._handle_session_info_response(domain, message)
            # AFTER processing SessionInfo, check for signedMessageStatus errors
            # Matching Tesla Go SDK: vehicle sends fresh SessionInfo WITH error when it detects stale session
            # We keep the new SessionInfo and abort the current command so it retries with fresh session
            if message.HasField("signedMessageStatus"):
                from .proto import universal_message_pb2
                if message.signedMessageStatus.operation_status == universal_message_pb2.OperationStatus_E.OPERATIONSTATUS_ERROR:
                    _LOGGER.info("SessionInfo with ERROR (fault=%s) - session was stale, now updated. Command will retry with fresh session.",
                        message.signedMessageStatus.signed_message_fault)
                    # Reset command state to retry with the fresh SessionInfo (don't remove from queue)
                    if domain in self._domain_queues:
                        current = self._active_command(domain)
                        if current and current.state == BLECommandState.WAITING_FOR_RESPONSE:
                            _LOGGER.debug(
                                "Resetting command %s to IDLE state to retry with updated session",
                                current.execute_name,
                            )
                            current.state = BLECommandState.IDLE
                            self._spawn_task(
                                self._process_domain_queue(domain),
                                f"session_retry.{domain.name}",
                            )
            return

        if payload_type == "session_info_request":
            _LOGGER.debug("Received unexpected SessionInfoRequest from vehicle")
            return

        if payload_type != "protobuf_message_as_bytes":
            _LOGGER.debug("Ignoring UniversalMessage payload type %s", payload_type)
            return

        if domain == UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY:
            # Don't parse here - let the handler decrypt first, then parse
            try:
                await self._handle_vcsec_response(None, message)
            except Exception as ex:  # pragma: no cover - stale session recovery
                payload_hex = message.protobuf_message_as_bytes.hex() if message.HasField("protobuf_message_as_bytes") else "none"
                _LOGGER.warning(
                    "%sFailed to parse VCSEC response (likely stale session): %s - payload_len=%d payload_hex=%s - invalidating session and disconnecting", self._log_prefix,
                    ex,
                    len(message.protobuf_message_as_bytes) if message.HasField("protobuf_message_as_bytes") else 0,
                    payload_hex[:100] if len(payload_hex) > 100 else payload_hex,
                )
                # Invalidate session for this domain to force fresh SessionInfo negotiation
                if self.key_manager:
                    self.key_manager.invalidate_session(domain)
                    _LOGGER.debug("Invalidated domain %s session after parse failure", domain)

                # Force disconnect to trigger fresh connection and session
                await self._disconnect()

                # Command will timeout and be retried with fresh session
            return

        if domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT:
            if self.protocol_client is None:
                _LOGGER.debug("Protocol client not initialised; dropping infotainment message")
                return

            try:
                parsed_response = self.protocol_client.parse_carserver_response(message)
                await self._handle_infotainment_response(parsed_response)
            except Exception as ex:  # pragma: no cover - stale session recovery
                payload_hex = message.protobuf_message_as_bytes.hex() if message.HasField("protobuf_message_as_bytes") else "none"
                _LOGGER.warning(
                    "%sFailed to parse CarServer response (likely stale session): %s - payload_len=%d payload_hex=%s - invalidating session and disconnecting", self._log_prefix,
                    ex,
                    len(message.protobuf_message_as_bytes) if message.HasField("protobuf_message_as_bytes") else 0,
                    payload_hex[:100] if len(payload_hex) > 100 else payload_hex,
                )
                # Invalidate session for this domain to force fresh SessionInfo negotiation
                if self.key_manager:
                    self.key_manager.invalidate_session(domain)
                    _LOGGER.debug("Invalidated domain %s session after parse failure", domain)

                # Force disconnect to trigger fresh connection and session
                await self._disconnect()

                # Command will timeout and be retried with fresh session
            return

        _LOGGER.debug("Unhandled UniversalMessage from domain %s", domain)

    async def _handle_session_info_response(self, domain: UniversalMessageDomain, message) -> None:
        """Process SessionInfo responses for a domain."""
        from .proto import signatures_pb2

        if message.WhichOneof("payload") != "session_info":
            return

        session_info = signatures_pb2.SessionInfo()
        session_info.ParseFromString(message.session_info)
        _LOGGER.debug("Received SessionInfo for domain %d (from message routing)", int(domain))

        if not session_info.publicKey:
            _LOGGER.debug(
                "Ignoring session info with empty public key for domain %s",
                domain,
            )
            return

        signature_data = message.signature_data if message.HasField("signature_data") else None

        try:
            self.key_manager.update_session_from_info(int(domain), session_info, signature_data)
            _LOGGER.debug(
                "Updated session info for domain %s (counter=%s handle=%s)",
                domain,
                session_info.counter,
                session_info.handle,
            )
            _LOGGER.info(
                "Received %s session (counter=%s handle=%s)",
                "VCSEC" if domain == UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY else "Infotainment",
                session_info.counter,
                session_info.handle,
            )
            self._session_blobs = self.key_manager.serialize_sessions()
            if self._persistent_state_loaded:
                self._schedule_state_save()
        except Exception as ex:
            _LOGGER.error("%sFailed to update session info for domain %s: %s", self._log_prefix, domain, ex)
            return

        updated = False
        if domain in self._domain_queues:
            queue_commands = self._queue_state(domain).iter_all()
            _LOGGER.debug("Checking %d commands in domain %s for state transition after session", len(queue_commands), domain)
            for command in queue_commands:
                _LOGGER.debug("Command %s in state %s", command.execute_name, command.state)
                if command.state in (
                    BLECommandState.WAITING_FOR_VCSEC_AUTH,
                    BLECommandState.WAITING_FOR_VCSEC_AUTH_RESPONSE,
                    BLECommandState.WAITING_FOR_INFOTAINMENT_AUTH,
                    BLECommandState.WAITING_FOR_INFOTAINMENT_AUTH_RESPONSE,
                ):
                    _LOGGER.info("Transitioning command %s from state %s to READY after session establishment", command.execute_name, command.state)
                    command.state = BLECommandState.READY
                    command.retry_count = 0
                    updated = True

        if updated:
            _LOGGER.debug("Commands transitioned to READY, triggering queue processing for domain %s", domain)
            self._spawn_task(self._process_domain_queue(domain), f"session_established.{domain.name}")

    async def _initialize_sessions(self) -> None:
        """Initialize cryptographic sessions."""
        try:
            if self.key_manager is None or self.protocol_client is None:
                await self._initialize_crypto()

            # Initialize key manager
            private_key_data = None
            if self.private_key:
                private_key_data = bytes.fromhex(self.private_key)

            await self.key_manager.initialize_keys(private_key_data)

            # Request session info for VCSEC domain
            await self._send_session_info_request(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
            await self._send_session_info_request(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

        except Exception as ex:
            _LOGGER.error("%sFailed to initialize sessions: %s", self._log_prefix, ex)
            raise

    async def _send_session_info_request(self, domain: UniversalMessageDomain) -> None:
        """Send session info request for domain."""
        # Gate on _crypto_ready: previously, a failed _reinitialize_crypto could leave
        # key_manager.crypto._private_key=None and this method would loop every 10s
        # with "Private key not available". Now we attempt one in-place recovery and
        # only fail loudly if that doesn't restore a usable key.
        if not self._crypto_ready:
            _LOGGER.warning(
                "%sCrypto not ready for domain %s; attempting reinitialization", self._log_prefix, domain
            )
            try:
                await self._initialize_crypto()
            except Exception as ex:
                _LOGGER.error("%sCrypto recovery failed: %s", self._log_prefix, ex, exc_info=True)
                raise
            if not self._crypto_ready:
                raise RuntimeError(
                    "Cannot send session info request: private key not loaded"
                )

        try:
            if self.protocol_client is None:
                raise RuntimeError("Protocol client not initialized")

            message = self.protocol_client.build_session_info_request(int(domain))

            # Send via BLE
            await self._write_ble_data(message)

        except Exception as ex:
            _LOGGER.error("%sFailed to send session info request: %s", self._log_prefix, ex)
            raise

    async def _log_ble_bytes(self, direction: str, payload: bytes) -> None:
        """Write BLE traffic to the optional debug log."""
        if not self._ble_log_path:
            return

        timestamp = datetime.now(timezone.utc).isoformat()
        line = f"{timestamp} {direction} {payload.hex()}\n"

        def _write_line() -> None:
            if not self._ble_log_path:
                return
            self._ble_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._ble_log_path, "a", encoding="utf-8") as handle:
                handle.write(line)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # pragma: no cover - defensive fallback
            _write_line()
            return

        if self.hass:
            await self.hass.async_add_executor_job(_write_line)
        else:
            await loop.run_in_executor(None, _write_line)

    def _chunk_size(self) -> int:
        """Payload bytes per GATT write, derived from the negotiated MTU.

        The old hardcoded 20 ignored the MTU that ESPHome proxies actually
        negotiate, so every message took 4-8x more writes than necessary — and
        each extra write is another chance to fail partway through a message.
        """
        mtu = getattr(self._client, "mtu_size", None) if self._client else None
        if not isinstance(mtu, int) or mtu <= BLE_ATT_HEADER_SIZE:
            return BLE_DEFAULT_CHUNK_SIZE
        return max(BLE_DEFAULT_CHUNK_SIZE, min(mtu - BLE_ATT_HEADER_SIZE, MAX_MESSAGE_LENGTH))

    async def _ensure_link_ready(self) -> None:
        """Connect and enable notifications before any part of a message is sent.

        Doing this once per message (rather than per chunk) is what makes a
        multi-chunk write atomic: the link can no longer be re-established
        *between* chunks, which would deliver the tail of a message on a fresh
        connection and leave the car reassembling a fragment.
        """
        last_exception: Exception | None = None

        for attempt in range(BLE_WRITE_MAX_ATTEMPTS):
            if not self._client or not self._client.is_connected:
                if self.hass and self.address:
                    if not bluetooth.async_address_present(self.hass, self.address, connectable=True):
                        _LOGGER.debug("%sVehicle not in BLE range, skipping connection attempt", self._log_prefix)
                        raise BleakError("Vehicle not in BLE range")
                try:
                    _LOGGER.debug(
                        "%sAttempting to connect (attempt %d/%d)",
                        self._log_prefix, attempt + 1, BLE_WRITE_MAX_ATTEMPTS,
                    )
                    await self._connect()
                except Exception as err:
                    in_range = True
                    if self.hass and self.address:
                        in_range = bluetooth.async_address_present(self.hass, self.address, connectable=True)
                    if in_range:
                        _LOGGER.warning(
                            "%sConnection attempt %d/%d failed: %s",
                            self._log_prefix, attempt + 1, BLE_WRITE_MAX_ATTEMPTS, err,
                        )
                    else:
                        _LOGGER.debug("%sConnection failed - vehicle not in BLE range", self._log_prefix)
                    last_exception = err
                    if attempt + 1 < BLE_WRITE_MAX_ATTEMPTS:
                        await asyncio.sleep(BLE_WRITE_RETRY_BACKOFF)
                    continue

            if self._client and self._client.is_connected and not self._notifications_started:
                try:
                    _LOGGER.debug("%sStarting BLE notifications for existing connection", self._log_prefix)
                    await self._client.start_notify(READ_UUID, self._handle_notification)
                    if self.protocol_client:
                        self.protocol_client.set_connection_id()
                    self._notifications_started = True
                except Exception as err:
                    if "already enabled" in str(err).lower():
                        _LOGGER.debug("%sNotifications already enabled, proceeding", self._log_prefix)
                        self._notifications_started = True
                        if self.protocol_client:
                            self.protocol_client.set_connection_id()
                    else:
                        _LOGGER.error("%sFailed to start notifications: %s", self._log_prefix, err)
                        last_exception = err
                        if attempt + 1 < BLE_WRITE_MAX_ATTEMPTS:
                            await asyncio.sleep(BLE_WRITE_RETRY_BACKOFF)
                        continue

            if self._client and self._client.is_connected:
                return

        if last_exception:
            raise RuntimeError("Failed to establish BLE link") from last_exception
        raise RuntimeError("Failed to establish BLE link")

    async def _write_ble_data(self, data: bytes) -> None:
        """Write one complete message to the BLE characteristic, atomically.

        Held under _write_lock so two messages can never interleave their chunks
        on the characteristic, and the link is established up-front so it cannot
        be swapped mid-message. If a chunk still fails after some of the message
        is on the wire, the link is torn down: the car is holding a partial frame
        and appending the next message to it would desynchronise its reassembler.
        """
        async with self._write_lock:
            await self._ensure_link_ready()

            if self._ble_log_path:
                self._spawn_task(self._log_ble_bytes("TX", data), "log_ble_tx")

            chunk_size = self._chunk_size()
            sent = 0
            try:
                for i in range(0, len(data), chunk_size):
                    await self._write_ble_chunk(data[i:i + chunk_size])
                    sent = min(i + chunk_size, len(data))
            except Exception:
                if sent:
                    _LOGGER.warning(
                        "%sWrite failed after %d/%d bytes of a message; dropping the link "
                        "so both ends resynchronise",
                        self._log_prefix, sent, len(data),
                    )
                await self._disconnect()
                raise

            _LOGGER.debug(
                "%sSent %d bytes to Tesla device in %d chunk(s) of %d",
                self._log_prefix, len(data),
                (len(data) + chunk_size - 1) // chunk_size or 1, chunk_size,
            )

    async def _write_ble_chunk(self, chunk: bytes) -> None:
        """Write a single chunk on an already-established link.

        Deliberately does NOT connect. Establishing a connection here would let a
        reconnect happen between two chunks of the same message; _write_ble_data
        owns link setup instead.
        """
        last_exception: Exception | None = None
        attempt = 0

        while attempt < BLE_WRITE_MAX_ATTEMPTS:
            if not self._client or not self._client.is_connected:
                raise BleakError("BLE link went down mid-message")

            try:
                write_coro = self._client.write_gatt_char(
                    WRITE_UUID,
                    chunk,
                    response=self._write_with_response,
                )
                await asyncio.wait_for(write_coro, timeout=BLE_WRITE_TIMEOUT)
                return
            except asyncio.TimeoutError as err:
                _LOGGER.debug(
                    "%sBLE write timed out (attempt %s/%s)",
                    self._log_prefix, attempt + 1, BLE_WRITE_MAX_ATTEMPTS,
                )
                last_exception = err
            except BleakError as err:
                error_text = str(err).lower()
                if self._write_with_response and "not support" in error_text:
                    _LOGGER.debug(
                        "%sWrite-with-response unsupported; falling back to write-without-response",
                        self._log_prefix,
                    )
                    self._write_with_response = False
                    continue
                _LOGGER.debug(
                    "%sBLE write failed (attempt %s/%s): %s",
                    self._log_prefix, attempt + 1, BLE_WRITE_MAX_ATTEMPTS, err,
                )
                last_exception = err
            except Exception as err:  # pragma: no cover - defensive guard
                last_exception = err
                _LOGGER.debug("%sUnexpected BLE write error: %s", self._log_prefix, err)

            attempt += 1

            if attempt < BLE_WRITE_MAX_ATTEMPTS:
                await asyncio.sleep(BLE_WRITE_RETRY_BACKOFF)

        if last_exception:
            raise RuntimeError("Failed to write BLE chunk") from last_exception
        raise RuntimeError("Failed to write BLE chunk")

    def update_signal_strength(self, rssi: int | None) -> None:
        """Store latest BLE RSSI value."""
        if rssi is None:
            return
        if self.data.get("ble_rssi") == rssi:
            return
        self.data["ble_rssi"] = rssi

    async def _handle_vcsec_response(self, vcsec_message, routable_message) -> None:
        """Handle VCSEC domain messages using protobuf structures."""
        from .proto import vcsec_pb2

        try:
            payload_bytes = bytes(routable_message.protobuf_message_as_bytes)
            domain_value = int(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)

            if routable_message.HasField("signature_data"):
                sig_choice = routable_message.signature_data.WhichOneof("sig_type")
                if sig_choice == "AES_GCM_Response_data":
                    response_sig = routable_message.signature_data.AES_GCM_Response_data
                    session = self.key_manager.get_session(domain_value)
                    if session is None:
                        raise RuntimeError(
                            "No session available to decrypt VCSEC response"
                        )
                    payload_bytes = self.key_manager.decrypt_payload(
                        domain_value,
                        payload_bytes,
                        bytes(response_sig.nonce),
                        bytes(response_sig.tag),
                        0,
                        response_sig.counter,
                        routable_message.flags,
                    )

            vcsec_message = vcsec_pb2.FromVCSECMessage()
            vcsec_message.ParseFromString(payload_bytes)

            sub_message = vcsec_message.WhichOneof("sub_message")
            _LOGGER.debug("VCSEC message fields: has vehicleStatus=%s, has commandStatus=%s, has whitelistInfo=%s, WhichOneof=%s",
                         vcsec_message.HasField("vehicleStatus"),
                         vcsec_message.HasField("commandStatus"),
                         vcsec_message.HasField("whitelistInfo"),
                         sub_message)

            if sub_message == "vehicleStatus":
                status = vcsec_message.vehicleStatus
                self._last_vcsec_update = time.monotonic()
                if self.data.get("ble_unreachable"):
                    _LOGGER.info("BLE reachable again — VCSEC responding (was flagged unreachable)")
                    self.data["ble_unreachable"] = False

                previous_asleep = self.vehicle_state == VEHICLE_STATE_ASLEEP
                current_asleep = (
                    status.vehicleSleepStatus
                    == vcsec_pb2.VehicleSleepStatus_E.VEHICLE_SLEEP_STATUS_ASLEEP
                )
                _LOGGER.debug("Sleep status: vehicleSleepStatus=%s, ASLEEP_ENUM=%s, current_asleep=%s, previous_asleep=%s",
                    status.vehicleSleepStatus,
                    vcsec_pb2.VehicleSleepStatus_E.VEHICLE_SLEEP_STATUS_ASLEEP,
                    current_asleep,
                    previous_asleep)

                if previous_asleep and not current_asleep:
                    self._car_just_woken = True
                    self._last_wake_time = time.time()
                    _LOGGER.debug("Vehicle just woke up - starting Infotainment polling immediately")

                    # Queue Infotainment poll immediately when car wakes up
                    # This avoids waiting for the next coordinator cycle
                    async def _queue_on_wake() -> None:
                        await self._start_infotainment_polling()
                        await self._process_domain_queue(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

                    self._spawn_task(_queue_on_wake(), "queue_on_wake")
                elif not previous_asleep and current_asleep:
                    self._car_just_woken = False
                    _LOGGER.debug("Vehicle went to sleep - clearing Infotainment queue")
                    # Clear Infotainment queue when vehicle goes to sleep
                    # These commands will timeout anyway, so clear them to prevent wasteful retries
                    self._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT).clear()

                doors_locked = (
                    status.vehicleLockState
                    == vcsec_pb2.VehicleLockState_E.VEHICLELOCKSTATE_LOCKED
                )
                user_present = (
                    status.userPresence
                    == vcsec_pb2.UserPresence_E.VEHICLE_USER_PRESENCE_PRESENT
                )

                self.data.update(
                    {
                        "is_asleep": current_asleep,
                        "is_user_present": user_present,
                        "doors_locked": doors_locked,
                    }
                )

                self.vehicle_state = (
                    VEHICLE_STATE_ASLEEP if current_asleep else VEHICLE_STATE_AWAKE
                )
                self._complete_domain_command(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
                return

            if sub_message == "commandStatus":
                command_status = vcsec_message.commandStatus
                op_status = command_status.operationStatus

                if op_status == vcsec_pb2.OperationStatus_E.OPERATIONSTATUS_OK:
                    self._complete_domain_command(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
                elif op_status == vcsec_pb2.OperationStatus_E.OPERATIONSTATUS_WAIT:
                    self._requeue_domain_command(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
                elif op_status == vcsec_pb2.OperationStatus_E.OPERATIONSTATUS_ERROR:
                    _LOGGER.error("%sVCSEC command returned ERROR status", self._log_prefix)
                    self._complete_domain_command(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)

                sub_status = command_status.WhichOneof("sub_message")
                if sub_status == "whitelistOperationStatus":
                    whitelist = command_status.whitelistOperationStatus
                    info_code = whitelist.whitelistOperationInformation
                    operation_state = whitelist.operationStatus
                    if operation_state == vcsec_pb2.OperationStatus_E.OPERATIONSTATUS_WAIT:
                        self._pairing_wait_info = info_code
                        self._pairing_failure_reason = self._pairing_reason_from_info(info_code)
                        _LOGGER.debug(
                            "VCSEC pairing wait status: %s",
                            vcsec_pb2.WhitelistOperation_information_E.Name(info_code),
                        )
                        return

                    self._pairing_complete = True
                    self._pairing_success = (
                        whitelist.operationStatus
                        == vcsec_pb2.OperationStatus_E.OPERATIONSTATUS_OK
                    )
                    info = whitelist.whitelistOperationInformation
                    info_name = None
                    if info is not None:
                        try:
                            info_name = vcsec_pb2.WhitelistOperation_information_E.Name(info)
                        except ValueError:  # pragma: no cover - defensive guard
                            info_name = f"UNKNOWN_{info}"
                    if self._pairing_success:
                        self._pairing_failure_reason = None
                        _LOGGER.info("Tesla BLE pairing completed successfully")
                    else:
                        self._pairing_error_info = info
                        self._pairing_failure_reason = self._pairing_reason_from_info(info)
                        _LOGGER.error(
                            "%sTesla BLE pairing failed: %s (%s)", self._log_prefix,
                            info,
                            info_name,
                        )
                elif sub_status == "signedMessageStatus":
                    signed_status = command_status.signedMessageStatus
                    session = self.key_manager.get_session(
                        int(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
                    )
                    if session is not None:
                        session["counter"] = max(
                            signed_status.counter, session.get("counter", 0)
                        )
                return

            if sub_message == "nominalError":
                _LOGGER.error(
                    "%sReceived VCSEC nominal error: %s", self._log_prefix,
                    vcsec_message.nominalError.genericError,
                )
                self._complete_domain_command(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
                return

            _LOGGER.debug("Unhandled VCSEC sub-message: %s", sub_message)

        except Exception as ex:
            _LOGGER.error("%sError handling VCSEC response: %s", self._log_prefix, ex)

    async def _handle_infotainment_response(self, parsed: ParsedCarServerResponse) -> None:
        """Handle Infotainment responses using protobuf structures."""
        try:
            response = parsed.response
            from .proto import car_server_pb2, universal_message_pb2

            active_command: BLECommand | None = None
            action_spec: ActionMessageDetail | None = None
            current = self._active_command(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
            if current is not None:
                active_command = current
                action_spec = ACTION_SPECIFICS.get(active_command.action)

            # Check for signedMessageStatus faults (e.g., TIME_EXPIRED)
            if parsed.fault != 0:
                fault_name = universal_message_pb2.MessageFault_E.Name(parsed.fault) if parsed.fault else "UNKNOWN"
                _LOGGER.warning("%sInfotainment response had fault %s (%s)", self._log_prefix, parsed.fault, fault_name)

                # TIME_EXPIRED means stale session - invalidate and let command retry
                if parsed.fault == universal_message_pb2.MessageFault_E.MESSAGEFAULT_ERROR_TIME_EXPIRED:
                    _LOGGER.info("TIME_EXPIRED error, invalidating Infotainment session")
                    self.key_manager.invalidate_session(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

                # Complete the command so it can be retried with fresh session
                if active_command:
                    self._complete_domain_command(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
                return

            # Handle actionStatus - check for errors
            if response.HasField("actionStatus") and active_command is not None:
                status = response.actionStatus
                result_name = car_server_pb2.OperationStatus_E.Name(status.result)
                reason_text = None
                if status.result_reason.WhichOneof("reason") == "plain_text":
                    reason_text = status.result_reason.plain_text

                _LOGGER.debug(
                    "actionStatus for %s result=%s reason=%s",
                    active_command.execute_name,
                    result_name,
                    reason_text,
                )

                if status.result == car_server_pb2.OperationStatus_E.OPERATIONSTATUS_ERROR:
                    reason = None
                    if status.result_reason.WhichOneof("reason") == "plain_text":
                        reason = status.result_reason.plain_text
                    if reason in {"is_charging", "is_not_charging"}:
                        _LOGGER.debug("Command %s returned benign error '%s'", active_command.execute_name, reason)
                        status.result = car_server_pb2.OperationStatus_E.OPERATIONSTATUS_OK
                    else:
                        _LOGGER.error("%sCommand %s failed: %s", self._log_prefix, active_command.execute_name, reason or "unknown")
                        self._complete_domain_command(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
                        return

                # SET commands (vehicle_action_*) complete on actionStatus OK
                # GET commands (get_*) continue to process vehicleData below
                is_set_command = active_command.execute_name.startswith("vehicle_action_")
                if is_set_command:
                    self._apply_optimistic_state_update(active_command)
                    _LOGGER.debug("SET command %s succeeded (actionStatus OK)", active_command.execute_name)
                    self._complete_domain_command(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
                    return

            # Handle vehicleData responses (GET commands)
            if response.WhichOneof("response_msg") != "vehicleData":
                _LOGGER.debug("Unhandled CarServer response type")
                return

            # Check if we should ignore this response (during mechanical delay period)
            if active_command and active_command.action in self._ignored_get_actions:
                _LOGGER.debug(
                    "Ignoring stale %s response during mechanical action delay period",
                    active_command.action.name,
                )
                self._complete_domain_command(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
                return

            vehicle_data = response.vehicleData

            if vehicle_data.HasField("charge_state"):
                charge_state = vehicle_data.charge_state

                charging_state_name = charge_state.charging_state.WhichOneof("type")
                if charging_state_name:
                    mapped_state = CHARGING_STATE_LOOKUP.get(charging_state_name, charging_state_name)
                    _LOGGER.debug(
                        "charge_state.charging_state=%s (mapped=%s)",
                        charging_state_name,
                        mapped_state,
                    )
                    self.data["charging_state"] = mapped_state
                    # Track first detection of charging (ESPHome car_is_charging_ == 1)
                    was_charging = self._is_charging
                    self._is_charging = mapped_state == CHARGING_STATE_CHARGING
                    if self._is_charging and not was_charging:
                        self._charging_just_started = True

                if charge_state.HasField("battery_level"):
                    self.data["charge_level"] = charge_state.battery_level
                if charge_state.HasField("charge_limit_soc"):
                    self.data["charge_limit"] = charge_state.charge_limit_soc
                if charge_state.HasField("charger_actual_current"):
                    self.data["charge_current"] = charge_state.charger_actual_current
                if charge_state.HasField("charger_voltage"):
                    self.data["charge_voltage"] = charge_state.charger_voltage
                if charge_state.HasField("charger_power"):
                    self.data["charge_power"] = charge_state.charger_power
                if charge_state.HasField("battery_range"):
                    self.data["battery_range"] = charge_state.battery_range
                if charge_state.HasField("charge_energy_added"):
                    self.data["charge_energy_added"] = charge_state.charge_energy_added
                if charge_state.HasField("charge_miles_added_ideal"):
                    self.data["charge_miles_added"] = charge_state.charge_miles_added_ideal
                if charge_state.HasField("minutes_to_charge_limit"):
                    self.data["minutes_to_limit"] = charge_state.minutes_to_charge_limit
                if charge_state.HasField("charging_amps"):
                    self.data["charging_amps"] = charge_state.charging_amps
                if charge_state.HasField("charge_current_request"):
                    self.data["charge_current_request"] = charge_state.charge_current_request
                if charge_state.HasField("charge_port_door_open"):
                    self.data["is_charge_flap_open"] = charge_state.charge_port_door_open

            if vehicle_data.HasField("climate_state"):
                climate_state = vehicle_data.climate_state

                if climate_state.HasField("is_climate_on"):
                    self.data["is_climate_on"] = climate_state.is_climate_on
                if climate_state.HasField("inside_temp_celsius"):
                    self.data["internal_temp"] = climate_state.inside_temp_celsius
                if climate_state.HasField("outside_temp_celsius"):
                    self.data["external_temp"] = climate_state.outside_temp_celsius
                if climate_state.HasField("defrost_mode"):
                    defrost_mode = climate_state.defrost_mode.WhichOneof("type")
                    self.data["defrost_mode"] = defrost_mode
                    self.data["defrost_active"] = defrost_mode in DEFROST_ACTIVE_STATES
                if climate_state.HasField("is_preconditioning"):
                    self.data["is_preconditioning"] = climate_state.is_preconditioning
                if climate_state.HasField("steering_wheel_heater"):
                    self.data["steering_wheel_heater"] = climate_state.steering_wheel_heater

            if vehicle_data.HasField("drive_state"):
                drive_state = vehicle_data.drive_state
                shift = drive_state.shift_state.WhichOneof("type")
                if shift:
                    self.data["shift_state"] = SHIFT_STATE_LOOKUP.get(shift, shift)
                if drive_state.HasField("odometer_in_hundredths_of_a_mile"):
                    self.data["odometer"] = drive_state.odometer_in_hundredths_of_a_mile / 100.0
                if drive_state.HasField("power"):
                    self.data["vehicle_power"] = drive_state.power

            if vehicle_data.HasField("closures_state"):
                closures = vehicle_data.closures_state
                if closures.HasField("door_open_trunk_rear"):
                    self.data["is_trunk_open"] = closures.door_open_trunk_rear
                if closures.HasField("door_open_trunk_front"):
                    self.data["is_frunk_open"] = closures.door_open_trunk_front
                if closures.HasField("locked"):
                    self.data["doors_locked"] = closures.locked
                if closures.HasField("is_user_present"):
                    self.data["is_user_present"] = closures.is_user_present
                door_field_map = {
                    "door_open_driver_front": "driver_front_door_open",
                    "door_open_driver_rear": "driver_rear_door_open",
                    "door_open_passenger_front": "passenger_front_door_open",
                    "door_open_passenger_rear": "passenger_rear_door_open",
                }
                for field_name, data_key in door_field_map.items():
                    value = getattr(closures, field_name, None)
                    if value is not None:
                        self.data[data_key] = value
                windows_open = any(
                    closures.HasField(name) and getattr(closures, name)
                    for name in (
                        "window_open_driver_front",
                        "window_open_passenger_front",
                        "window_open_driver_rear",
                        "window_open_passenger_rear",
                    )
                )
                self.data["windows_open"] = windows_open
                if closures.HasField("sentry_mode_state"):
                    sentry_state = closures.sentry_mode_state.WhichOneof("type")
                    self.data["sentry_mode_state"] = sentry_state
                    self.data["sentry_mode"] = sentry_state in SENTRY_ACTIVE_STATES

            if vehicle_data.HasField("tire_pressure_state"):
                tire_pressure = vehicle_data.tire_pressure_state
                # Convert bar to PSI (1 bar = 14.5038 PSI)
                BAR_TO_PSI = 14.5038

                # Tire pressures
                if tire_pressure.HasField("tpms_pressure_fl"):
                    self.data["tire_pressure_fl"] = tire_pressure.tpms_pressure_fl * BAR_TO_PSI
                if tire_pressure.HasField("tpms_pressure_fr"):
                    self.data["tire_pressure_fr"] = tire_pressure.tpms_pressure_fr * BAR_TO_PSI
                if tire_pressure.HasField("tpms_pressure_rl"):
                    self.data["tire_pressure_rl"] = tire_pressure.tpms_pressure_rl * BAR_TO_PSI
                if tire_pressure.HasField("tpms_pressure_rr"):
                    self.data["tire_pressure_rr"] = tire_pressure.tpms_pressure_rr * BAR_TO_PSI

                # Recommended cold pressures
                if tire_pressure.HasField("tpms_rcp_front_value"):
                    self.data["tire_pressure_rcp_front"] = tire_pressure.tpms_rcp_front_value * BAR_TO_PSI
                if tire_pressure.HasField("tpms_rcp_rear_value"):
                    self.data["tire_pressure_rcp_rear"] = tire_pressure.tpms_rcp_rear_value * BAR_TO_PSI

                # Warning states
                if tire_pressure.HasField("tpms_hard_warning_fl"):
                    self.data["tire_hard_warning_fl"] = tire_pressure.tpms_hard_warning_fl
                if tire_pressure.HasField("tpms_hard_warning_fr"):
                    self.data["tire_hard_warning_fr"] = tire_pressure.tpms_hard_warning_fr
                if tire_pressure.HasField("tpms_hard_warning_rl"):
                    self.data["tire_hard_warning_rl"] = tire_pressure.tpms_hard_warning_rl
                if tire_pressure.HasField("tpms_hard_warning_rr"):
                    self.data["tire_hard_warning_rr"] = tire_pressure.tpms_hard_warning_rr

                if tire_pressure.HasField("tpms_soft_warning_fl"):
                    self.data["tire_soft_warning_fl"] = tire_pressure.tpms_soft_warning_fl
                if tire_pressure.HasField("tpms_soft_warning_fr"):
                    self.data["tire_soft_warning_fr"] = tire_pressure.tpms_soft_warning_fr
                if tire_pressure.HasField("tpms_soft_warning_rl"):
                    self.data["tire_soft_warning_rl"] = tire_pressure.tpms_soft_warning_rl
                if tire_pressure.HasField("tpms_soft_warning_rr"):
                    self.data["tire_soft_warning_rr"] = tire_pressure.tpms_soft_warning_rr

            self.last_update_time = time.time()

            if active_command and action_spec and action_spec.which_msg == AllowedMsg.VehicleActionMessage:
                if action_spec.get_on_set != GetOnSet.Invalid:
                    active_command.state = BLECommandState.WAITING_FOR_GET_POST_SET
                    active_command.last_tx_at = time.time()
                    active_command.done_times = 0
                    self._spawn_task(
                        self._process_domain_queue(UniversalMessageDomain.DOMAIN_INFOTAINMENT),
                        "post_set_get",
                    )
                else:
                    self._complete_domain_command(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
            else:
                self._complete_domain_command(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

        except Exception as ex:
            _LOGGER.error("%sError handling Infotainment response: %s", self._log_prefix, ex, exc_info=True)
            # Complete the command so queue doesn't get stuck
            self._complete_domain_command(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

    async def _queue_command(
        self,
        execute_name: str,
        action: BLECarServerVehicleAction,
        domain: UniversalMessageDomain,
        parameter: Optional[int] = None,
        parameter_bool: Optional[bool] = None,
        parameter_float: Optional[float] = None,
        parameter2: Optional[int] = None,
        priority: int = 0,
        follow_up_get: Optional[BLECarServerVehicleAction] = None,
    ) -> None:
        """Queue a command for execution."""
        # Deduplicate: Don't queue the same command if it's already pending
        # This prevents queue buildup when connection is slow/failing
        queue_state = self._queue_state(domain)
        for existing_cmd in queue_state.iter_all():
            if (existing_cmd.execute_name == execute_name
                and existing_cmd.domain == domain
                and existing_cmd.parameter == parameter
                and existing_cmd.parameter_bool == parameter_bool):
                _LOGGER.debug("Command %s already in queue, skipping duplicate", execute_name)
                return

        command = BLECommand(
            execute_name=execute_name,
            action=action,
            domain=domain,
            parameter=parameter,
            parameter_bool=parameter_bool,
            parameter_float=parameter_float,
            parameter2=parameter2,
            started_at=0,  # Will be set when command actually starts executing
            done_times=0,
            priority=priority,
            follow_up_get=follow_up_get,
        )

        queue_state.add_command(command, priority)
        if priority > 0:
            _LOGGER.debug(
                "Queued HIGH priority command %s (domain=%s, queue size=%d)",
                execute_name,
                domain,
                self._queue_length(domain),
            )
        else:
            _LOGGER.debug(
                "Queued normal priority command %s (domain=%s, queue size=%d)",
                execute_name,
                domain,
                self._queue_length(domain),
            )

        await self._process_domain_queue(domain)

    async def _queue_follow_up_action(
        self,
        follow_action: BLECarServerVehicleAction,
    ) -> None:
        await self._queue_command(
            execute_name=f"followup_{follow_action.name.lower()}",
            action=follow_action,
            domain=UniversalMessageDomain.DOMAIN_INFOTAINMENT,
        )

    def _apply_optimistic_state_update(self, command: BLECommand) -> None:
        """Best-effort local state update after actionStatus OK."""
        updated = False
        action = command.action
        param_bool = command.parameter_bool

        if action == BLECarServerVehicleAction.SET_OPEN_CHARGE_PORT_DOOR:
            self.data["is_charge_flap_open"] = True
            updated = True
        elif action == BLECarServerVehicleAction.SET_CLOSE_CHARGE_PORT_DOOR:
            self.data["is_charge_flap_open"] = False
            updated = True
        elif action == BLECarServerVehicleAction.SET_HVAC_SWITCH and param_bool is not None:
            is_on = bool(param_bool)
            self.data["is_climate_on"] = is_on
            self.data["is_preconditioning"] = is_on
            updated = True
        elif action == BLECarServerVehicleAction.SET_HVAC_STEERING_HEATER_SWITCH and param_bool is not None:
            self.data["steering_wheel_heater"] = bool(param_bool)
            updated = True
        elif action == BLECarServerVehicleAction.SET_SENTRY_SWITCH and param_bool is not None:
            sentry_on = bool(param_bool)
            self.data["sentry_mode"] = sentry_on
            self.data["sentry_mode_state"] = "Armed" if sentry_on else "Off"
            updated = True
        elif action == BLECarServerVehicleAction.SET_CHARGING_SWITCH and param_bool is not None:
            charging = bool(param_bool)
            if charging:
                self.data["charging_state"] = CHARGING_STATE_CHARGING
                if not self._is_charging:
                    self._charging_just_started = True
                self._is_charging = True
            else:
                self.data["charging_state"] = CHARGING_STATE_STOPPED
                self._is_charging = False
            updated = True
        elif action == BLECarServerVehicleAction.SET_CHARGING_AMPS and command.parameter is not None:
            self.data["charging_amps"] = command.parameter
            updated = True
        elif action == BLECarServerVehicleAction.SET_CHARGING_LIMIT and command.parameter is not None:
            self.data["charge_limit"] = command.parameter
            updated = True

        if updated:
            self.last_update_time = time.time()

    async def send_vehicle_action(
        self,
        action: BLECarServerVehicleAction,
        *,
        parameter: Optional[int] = None,
        parameter_bool: Optional[bool] = None,
        parameter_float: Optional[float] = None,
        parameter2: Optional[int] = None,
        priority: int = 1,  # Default to HIGH priority for user actions
    ) -> None:
        """Queue an infotainment vehicle action and process immediately."""
        _LOGGER.info("Send vehicle action called: action=%s, param=%s, param_bool=%s, param_float=%s, priority=%d",
                     action, parameter, parameter_bool, parameter_float, priority)

        await self._initialize_crypto()

        if self.protocol_client is None:
            raise RuntimeError("Protocol client not initialized")

        if not self.is_connected:
            await self._connect()

        if not self.key_manager.is_session_valid(UniversalMessageDomain.DOMAIN_INFOTAINMENT):
            await self._send_session_info_request(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

        if parameter is None and parameter_bool is not None:
            parameter = 1 if parameter_bool else 0

        # Determine follow-up GET command based on the SET action
        # This will be queued AFTER the SET command completes (or times out)
        follow_up_get = None
        if action in (BLECarServerVehicleAction.SET_HVAC_SWITCH,
                      BLECarServerVehicleAction.SET_HVAC_STEERING_HEATER_SWITCH,
                      BLECarServerVehicleAction.DEFROST_CAR):
            follow_up_get = BLECarServerVehicleAction.GET_CLIMATE_STATE
        elif action in (BLECarServerVehicleAction.SET_CHARGING_SWITCH,
                        BLECarServerVehicleAction.SET_CHARGING_AMPS,
                        BLECarServerVehicleAction.SET_CHARGING_LIMIT,
                        BLECarServerVehicleAction.SET_OPEN_CHARGE_PORT_DOOR,
                        BLECarServerVehicleAction.SET_CLOSE_CHARGE_PORT_DOOR):
            follow_up_get = BLECarServerVehicleAction.GET_CHARGE_STATE
        elif action == BLECarServerVehicleAction.SET_SENTRY_SWITCH:
            follow_up_get = BLECarServerVehicleAction.GET_CLOSURES_STATE
        elif action == BLECarServerVehicleAction.SET_WINDOWS_SWITCH:
            follow_up_get = BLECarServerVehicleAction.GET_CLOSURES_STATE

        # Queue the SET command with follow_up_get metadata
        # The GET will be queued automatically after SET completes
        await self._queue_command(
            execute_name=f"vehicle_action_{action.name}",
            action=action,
            domain=UniversalMessageDomain.DOMAIN_INFOTAINMENT,
            parameter=parameter,
            parameter_bool=parameter_bool,
            parameter_float=parameter_float,
            parameter2=parameter2,
            priority=priority,
            follow_up_get=follow_up_get,
        )
        await self._process_domain_queue(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

    async def send_vcsec_closure_move(self, closure_type: str, move_type: str) -> None:
        """Send a VCSEC closure move request (e.g., frunk open)."""
        _LOGGER.info("Send VCSEC closure move called: closure=%s, move=%s", closure_type, move_type)

        await self._initialize_crypto()

        if self.protocol_client is None:
            raise RuntimeError("Protocol client not initialized")

        if not self.is_connected:
            await self._connect()

        if not self.key_manager.is_session_valid(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY):
            await self._send_session_info_request(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)

        # Queue closure move command with HIGH priority (user action)
        # Command format: closure_move_<closure>_<move> (e.g., closure_move_rearTrunk_open)
        execute_name = f"closure_move_{closure_type}_{move_type.lower()}"
        await self._queue_command(
            execute_name,
            BLECarServerVehicleAction.DO_NOTHING,
            UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
            priority=1,
        )
        await self._process_domain_queue(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)

        # Queue delayed Infotainment poll to get updated state after mechanical operation completes
        # Trunk/frunk/doors status comes from closures_state
        # Charge port status comes from charge_state
        if closure_type == "chargePort":
            poll_action = BLECarServerVehicleAction.GET_CHARGE_STATE
        else:
            poll_action = BLECarServerVehicleAction.GET_CLOSURES_STATE

        # Delay poll to give mechanical actuators time to complete (3s)
        async def _delayed_closure_poll() -> None:
            await asyncio.sleep(FOLLOW_UP_DELAY_MECHANICAL)
            await self._queue_command(
                poll_action.name.lower(),
                poll_action,
                UniversalMessageDomain.DOMAIN_INFOTAINMENT,
                priority=1,
            )
            await self._process_domain_queue(UniversalMessageDomain.DOMAIN_INFOTAINMENT)

        self._spawn_task(_delayed_closure_poll(), "delayed_closure_poll")

    async def _process_domain_queue(self, domain: UniversalMessageDomain) -> None:
        """Process commands for a single protocol domain.

        Why locked: the previous boolean self_queue_state.processing was a check-then-set
        with no mutex, so two coroutines could both observe False and both run the queue.
        The per-domain asyncio.Lock makes the single-consumer property a real invariant;
        concurrent callers wait their turn instead of racing.
        """
        queue_state = self._queue_state(domain)
        async with self._queue_locks[domain]:
            if not queue_state.has_pending():
                _LOGGER.debug("_process_domain_queue(%s): queue is empty", domain)
                return

            _LOGGER.debug(
                "_process_domain_queue(%s): starting, queue size: %d",
                domain,
                self._queue_length(domain),
            )

            try:
                while True:
                    command = queue_state.peek()
                    if command is None:
                        break

                    now = time.time()
                    max_total_time = COMMAND_TIMEOUT / 1000 * (MAX_RESPONSE_RETRIES + 1)
                    if command.started_at > 0 and now - command.started_at > max_total_time:
                        _LOGGER.warning(
                            "%sCommand %s timed out after %.1fs (max %.1fs)", self._log_prefix,
                            command.execute_name,
                            now - command.started_at,
                            max_total_time,
                        )
                        self._cancel_command_timeout(command)

                        # Handle HIGH priority (user) commands differently - re-queue and reconnect
                        if command.priority > 0:  # HIGH priority user command
                            if command.requeue_count < MAX_REQUEUE_ATTEMPTS:
                                _LOGGER.warning(
                                    "%sRe-queuing HIGH priority command %s after timeout (attempt %d/%d), forcing disconnect to reconnect via fresh proxy", self._log_prefix,
                                    command.execute_name,
                                    command.requeue_count + 1,
                                    MAX_REQUEUE_ATTEMPTS,
                                )

                                # Reset command state for retry after reconnect
                                command.state = BLECommandState.IDLE
                                command.started_at = 0
                                command.last_tx_at = 0
                                command.retry_count = 0  # Reset response retries
                                command.requeue_count += 1  # Track requeue attempts

                                # Clear current_command pointer but keep command in queue at position 0
                                # It will be re-peeked and retried after fresh connection
                                queue_state.current_command = None

                                # Force disconnect to get fresh connection/proxy
                                await self._disconnect()

                                # Exit queue processing - command will retry on next cycle with fresh connection
                                return
                            else:
                                _LOGGER.error(
                                    "%sHIGH priority command %s exceeded max requeue attempts (%d), giving up", self._log_prefix,
                                    command.execute_name,
                                    MAX_REQUEUE_ATTEMPTS,
                                )
                                if command.follow_up_get:
                                    self._queue_follow_up_get(
                                        command.follow_up_get,
                                        f"after {command.execute_name} failed",
                                        high_priority=True,
                                    )
                                queue_state.pop_current()
                                continue
                        else:
                            # LOW priority (polling) command timed out
                            # During initial wake burst (first 60s), requeue at back to retry
                            # This prevents losing all infotainment data if one command times out on wake
                            time_since_wake = now - self._last_wake_time
                            in_wake_burst = time_since_wake < 60.0

                            if in_wake_burst and command.requeue_count < MAX_REQUEUE_ATTEMPTS:
                                _LOGGER.warning(
                                    "%sRe-queuing LOW priority command %s after timeout during wake burst (attempt %d/%d, %.1fs since wake)", self._log_prefix,
                                    command.execute_name,
                                    command.requeue_count + 1,
                                    MAX_REQUEUE_ATTEMPTS,
                                    time_since_wake,
                                )
                                # Reset command state for retry
                                command.state = BLECommandState.IDLE
                                command.started_at = 0
                                command.last_tx_at = 0
                                command.retry_count = 0
                                command.requeue_count += 1

                                # Move to back of queue (pop then re-add)
                                queue_state.pop_current()
                                queue_state.normal.append(command)

                                # Force disconnect to get fresh connection
                                await self._disconnect()
                                return
                            else:
                                # Outside wake burst or max retries - discard and disconnect
                                _LOGGER.warning(
                                    "%sDiscarding LOW priority command %s (domain=%s) after timeout, invalidating domain session and disconnecting", self._log_prefix,
                                    command.execute_name,
                                    command.domain,
                                )
                                queue_state.pop_current()

                                # Invalidate only the session for the domain that timed out
                                # This prevents breaking working sessions in other domains
                                if self.key_manager:
                                    self.key_manager.invalidate_session(command.domain)
                                    _LOGGER.debug("Invalidated domain %s session after timeout", command.domain)

                                # Force disconnect - any timeout indicates bad connection
                                await self._disconnect()

                                # Exit queue processing - will reconnect on next cycle with fresh session for failed domain
                                return

                    success = await self._process_command_state(command, now)
                    if success:
                        _LOGGER.debug(
                            "_process_domain_queue(%s): command %s completed",
                            domain,
                            command.execute_name,
                        )
                        self._cancel_command_timeout(command)

                        # Reset requeue counter on successful command completion
                        if command.requeue_count > 0:
                            _LOGGER.debug(
                                "Command %s succeeded after %d requeue(s)",
                                command.execute_name,
                                command.requeue_count,
                            )
                            command.requeue_count = 0

                        # Note: SET commands complete in the message handler via _complete_domain_command
                        # and never return True from _process_command_state, so follow_up_get logic
                        # is handled there. This code path only executes for GET commands and other
                        # commands that complete within the state machine.

                        # If this GET command was being ignored during a mechanical delay, stop ignoring it now
                        # This handles both successful completion and timeout cases
                        if command.action in self._ignored_get_actions:
                            self._ignored_get_actions.discard(command.action)
                            _LOGGER.debug(
                                "Stopped ignoring %s responses - command completed/timed out in state machine",
                                command.action.name,
                            )

                        queue_state.pop_current()
                        if self._persistent_state_loaded:
                            self._schedule_state_save()
                    else:
                        break
            finally:
                _LOGGER.debug(
                    "_process_domain_queue(%s): finished, queue size: %d",
                    domain,
                    self._queue_length(domain),
                )

    async def _process_command_state(self, command: BLECommand, now: float) -> bool:
        """Process individual command state machine with retries."""
        if self.protocol_client is None:
            raise RuntimeError("Protocol client not initialized")

        action_spec: ActionMessageDetail | None = None
        if command.domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT:
            action_spec = ACTION_SPECIFICS.get(command.action)

        _LOGGER.debug("Processing command %s in state %s", command.execute_name, command.state)

        if command.state == BLECommandState.IDLE:
            # Skip only LOW priority (polling) Infotainment GET commands when asleep
            # HIGH priority GETs (user follow-ups) should wake the vehicle
            if (
                self.data.get("is_asleep")
                and command.execute_name.startswith("get")
                and command.domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT
                and command.priority == 0  # Only skip polling GETs, not user follow-up GETs
            ):
                _LOGGER.info("Car is asleep, skipping Infotainment polling GET command: %s", command.execute_name)
                return True

            # Auto-wake for user Infotainment commands (priority > 0) when car is asleep
            # This includes both SET commands and follow-up GET commands
            if (
                command.domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT
                and self.data.get("is_asleep")
                and command.priority > 0
            ):
                _LOGGER.info("Car asleep; requesting wake before executing user command %s", command.execute_name)
                command.state = BLECommandState.WAITING_FOR_WAKE
                command.retry_count = 0
                command.retry_delay = WAKE_RETRY_INTERVAL
                if await self.wake_vehicle():
                    command.last_tx_at = now
                else:
                    _LOGGER.error("%sFailed to request vehicle wake for command %s", self._log_prefix, command.execute_name)
                    return True
                return False

            if command.domain == UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY:
                if not self.key_manager.is_session_valid(command.domain):
                    if command.retry_count >= MAX_SESSION_RETRIES:
                        _LOGGER.error("%sFailed to authenticate VCSEC after retries", self._log_prefix)
                        return True
                    await self._send_session_info_request(command.domain)
                    # Transition to AUTH_RESPONSE state to wait for SessionInfo response
                    command.state = BLECommandState.WAITING_FOR_VCSEC_AUTH_RESPONSE
                    command.retry_delay = SESSION_RETRY_INTERVAL
                    command.last_tx_at = now
                    command.retry_count += 1
                    return False
                command.state = BLECommandState.READY
                command.retry_delay = 0

            elif command.domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT:
                session_valid = self.key_manager.is_session_valid(command.domain)
                _LOGGER.debug("Infotainment session valid check: %s", session_valid)
                if not session_valid:
                    if command.retry_count >= MAX_SESSION_RETRIES:
                        _LOGGER.error("%sFailed to authenticate Infotainment after retries", self._log_prefix)
                        return True
                    await self._send_session_info_request(command.domain)
                    # Transition to AUTH_RESPONSE state to wait for SessionInfo response
                    command.state = BLECommandState.WAITING_FOR_INFOTAINMENT_AUTH_RESPONSE
                    command.retry_delay = SESSION_RETRY_INTERVAL
                    command.last_tx_at = now
                    command.retry_count += 1
                    return False
                command.state = BLECommandState.READY
                command.retry_delay = 0

            else:
                command.state = BLECommandState.READY
                command.retry_delay = 0

        if command.state == BLECommandState.WAITING_FOR_WAKE:
            if not self.data.get("is_asleep"):
                _LOGGER.debug("Vehicle awake; resuming command %s", command.execute_name)
                # After wake, check if we need to establish a session for this command's domain
                if not self.key_manager.is_session_valid(command.domain):
                    _LOGGER.debug("No valid session for domain %s after wake, transitioning to auth", command.domain)
                    # Transition to appropriate auth state based on domain
                    if command.domain == UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY:
                        command.state = BLECommandState.WAITING_FOR_VCSEC_AUTH
                    elif command.domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT:
                        command.state = BLECommandState.WAITING_FOR_INFOTAINMENT_AUTH
                    else:
                        _LOGGER.error("%sUnknown domain %s for command %s after wake", self._log_prefix, command.domain, command.execute_name)
                        return True  # Remove command
                    command.retry_count = 0
                    command.retry_delay = 0
                    command.last_tx_at = 0  # Allow immediate session request
                else:
                    # Session already valid, can proceed directly to READY
                    command.state = BLECommandState.READY
                    command.retry_count = 0
                    command.retry_delay = 0
                return False

            retry_delay = command.retry_delay or WAKE_RETRY_INTERVAL
            if now - command.last_tx_at > retry_delay:
                if command.retry_count >= MAX_WAKE_RETRIES:
                    _LOGGER.error("%sFailed to wake vehicle for command %s", self._log_prefix, command.execute_name)
                    return True
                _LOGGER.debug("Retrying vehicle wake for command %s (attempt %s/%s)", command.execute_name, command.retry_count + 1, MAX_WAKE_RETRIES)
                if await self.wake_vehicle():
                    command.retry_count += 1
                    command.last_tx_at = now
                    command.retry_delay = min(retry_delay * 2, WAKE_RETRY_MAX_DELAY)
                else:
                    _LOGGER.error("%sWake request failed while preparing command %s", self._log_prefix, command.execute_name)
                    return True
            return False

        if command.state == BLECommandState.WAITING_FOR_VCSEC_AUTH:
            if self.key_manager.is_session_valid(command.domain):
                command.state = BLECommandState.READY
                command.retry_count = 0
                command.retry_delay = 0
            else:
                retry_delay = command.retry_delay or SESSION_RETRY_INTERVAL
                if now - command.last_tx_at >= retry_delay:
                    if command.retry_count >= MAX_SESSION_RETRIES:
                        _LOGGER.error("%sFailed to authenticate VCSEC after retries", self._log_prefix)
                        return True
                    await self._send_session_info_request(command.domain)
                    # Transition to AUTH_RESPONSE state to wait for SessionInfo response
                    command.state = BLECommandState.WAITING_FOR_VCSEC_AUTH_RESPONSE
                    command.last_tx_at = now
                    command.retry_count += 1
                    command.retry_delay = min(retry_delay * 2, SESSION_RETRY_MAX_DELAY)
            return False

        if command.state == BLECommandState.WAITING_FOR_VCSEC_AUTH_RESPONSE:
            # Wait for SessionInfo response (handled in _handle_session_info)
            # Timeout and retry if response doesn't arrive
            if now - command.last_tx_at > MAX_LATENCY:
                if command.retry_count >= MAX_SESSION_RETRIES:
                    _LOGGER.error(
                        "%sFailed to get VCSEC SessionInfo response after %d retries - vehicle not responding, invalidating session and disconnecting", self._log_prefix,
                        MAX_SESSION_RETRIES,
                    )
                    self.key_manager.invalidate_session(command.domain)
                    await self._disconnect()
                    # Reinitialize crypto with fresh instances to recover from stuck state.
                    # If reinit itself fails, keep the command around for retry rather than
                    # silently dropping it (the old code returned True regardless).
                    try:
                        await self._reinitialize_crypto()
                    except Exception as ex:
                        _LOGGER.error(
                            "%sCrypto reinitialization failed after VCSEC auth timeout: %s", self._log_prefix,
                            ex,
                            exc_info=True,
                        )
                        command.state = BLECommandState.IDLE
                        command.retry_count = 0
                        return False
                    return True  # Remove command, will be retried fresh on reconnect
                _LOGGER.warning(
                    "%sTimeout waiting for VCSEC SessionInfo response, retrying (attempt %d/%d)", self._log_prefix,
                    command.retry_count + 1,
                    MAX_SESSION_RETRIES,
                )
                command.state = BLECommandState.WAITING_FOR_VCSEC_AUTH
                command.retry_count += 1
            return False

        if command.state == BLECommandState.WAITING_FOR_INFOTAINMENT_AUTH:
            if self.key_manager.is_session_valid(command.domain):
                command.state = BLECommandState.READY
                command.retry_count = 0
                command.retry_delay = 0
            else:
                retry_delay = command.retry_delay or SESSION_RETRY_INTERVAL
                if now - command.last_tx_at >= retry_delay:
                    if command.retry_count >= MAX_SESSION_RETRIES:
                        _LOGGER.error("%sFailed to authenticate Infotainment after retries", self._log_prefix)
                        return True
                    await self._send_session_info_request(command.domain)
                    # Transition to AUTH_RESPONSE state to wait for SessionInfo response
                    command.state = BLECommandState.WAITING_FOR_INFOTAINMENT_AUTH_RESPONSE
                    command.last_tx_at = now
                    command.retry_count += 1
                    command.retry_delay = min(retry_delay * 2, SESSION_RETRY_MAX_DELAY)
            return False

        if command.state == BLECommandState.WAITING_FOR_INFOTAINMENT_AUTH_RESPONSE:
            # Wait for SessionInfo response (handled in _handle_session_info)
            # Timeout and retry if response doesn't arrive
            if now - command.last_tx_at > MAX_LATENCY:
                if command.retry_count >= MAX_SESSION_RETRIES:
                    _LOGGER.error(
                        "%sFailed to get Infotainment SessionInfo response after %d retries - vehicle not responding, invalidating session and disconnecting", self._log_prefix,
                        MAX_SESSION_RETRIES,
                    )
                    self.key_manager.invalidate_session(command.domain)
                    await self._disconnect()
                    try:
                        await self._reinitialize_crypto()
                    except Exception as ex:
                        _LOGGER.error(
                            "%sCrypto reinitialization failed after Infotainment auth timeout: %s", self._log_prefix,
                            ex,
                            exc_info=True,
                        )
                        command.state = BLECommandState.IDLE
                        command.retry_count = 0
                        return False
                    return True  # Remove command, will be retried fresh on reconnect
                _LOGGER.warning(
                    "%sTimeout waiting for Infotainment SessionInfo response, retrying (attempt %d/%d)", self._log_prefix,
                    command.retry_count + 1,
                    MAX_SESSION_RETRIES,
                )
                command.state = BLECommandState.WAITING_FOR_INFOTAINMENT_AUTH
                command.retry_count += 1
            return False

        if command.state == BLECommandState.READY:
            if command.domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT:
                queue_state = self._queue_state(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
                if queue_state.current_command is not command:
                    return False
                for other_cmd in queue_state.iter_all():
                    if other_cmd is command:
                        break
                    if other_cmd.state == BLECommandState.WAITING_FOR_RESPONSE:
                        _LOGGER.debug(
                            "Delaying %s until %s completes (counter sync)",
                            command.execute_name,
                            other_cmd.execute_name,
                        )
                        return False

            try:
                await self._execute_command(command)
                command.state = BLECommandState.WAITING_FOR_RESPONSE
                command.last_tx_at = time.time()  # Start response timer after BLE write completes
                self._schedule_command_timeout(command.domain, command)
                return False
            except Exception as ex:
                _LOGGER.error("%sFailed to execute command %s: %s, removing from queue", self._log_prefix, command.execute_name, ex)
                return True  # Remove failed command from queue

        if command.state == BLECommandState.WAITING_FOR_GET_POST_SET:
            if not action_spec or action_spec.get_on_set == GetOnSet.Invalid:
                return True
            if now - command.last_tx_at < FOLLOW_UP_DELAY:
                return False
            follow_action = FOLLOW_UP_ACTION.get(action_spec.get_on_set)
            if follow_action is not None:
                await self._queue_follow_up_action(follow_action)
            return True

        if command.state == BLECommandState.WAITING_FOR_RESPONSE:
            if now - command.last_tx_at > COMMAND_TIMEOUT / 1000:
                # Retry GET commands and user commands (priority > 0) up to MAX_RESPONSE_RETRIES times
                # Vehicle might be temporarily busy (Tesla app active, internal systems, etc.)
                is_get_command = (
                    command.execute_name.startswith("get_") or
                    command.action in (
                        BLECarServerVehicleAction.GET_CHARGE_STATE,
                        BLECarServerVehicleAction.GET_CLIMATE_STATE,
                        BLECarServerVehicleAction.GET_DRIVE_STATE,
                        BLECarServerVehicleAction.GET_CLOSURES_STATE,
                        BLECarServerVehicleAction.GET_TIRE_PRESSURE_STATE,
                    )
                )
                is_user_command = command.priority > 0

                if (is_get_command or is_user_command) and command.retry_count < MAX_RESPONSE_RETRIES:
                    _LOGGER.warning(
                        "%sCommand %s timed out waiting for response, retrying immediately (attempt %d/%d)", self._log_prefix,
                        command.execute_name,
                        command.retry_count + 1,
                        MAX_RESPONSE_RETRIES,
                    )
                    self._cancel_command_timeout(command)
                    command.state = BLECommandState.READY
                    command.retry_count += 1
                    return False
                else:
                    _LOGGER.warning(
                        "%sCommand %s timed out waiting for response after %d retries, removing from queue", self._log_prefix,
                        command.execute_name,
                        command.retry_count,
                    )
                    return True
            return False

        return False

    def set_data_update_callback(self, callback: Callable[[], None]) -> None:
        """Set callback to trigger when data is updated."""
        self._data_update_callback = callback

    def _queue_follow_up_get(
        self,
        follow_up_action: BLECarServerVehicleAction,
        reason: str,
        *,
        high_priority: bool = False,
    ) -> None:
        """Queue a follow-up GET command after a SET command completes or times out.

        Args:
            follow_up_action: The GET action to queue
            reason: Description of why it's being queued (e.g., "completed", "timed out")
            high_priority: Whether to insert the GET ahead of polling commands
        """
        _LOGGER.debug("Queuing follow-up GET %s (reason: %s)", follow_up_action.name, reason)

        async def _queue_follow_up() -> None:
            await self._queue_command(
                execute_name=follow_up_action.name.lower(),
                action=follow_up_action,
                domain=UniversalMessageDomain.DOMAIN_INFOTAINMENT,
                priority=1 if high_priority else 0,
            )

        self._spawn_task(_queue_follow_up(), f"queue_follow_up.{follow_up_action.name}")

    def _complete_domain_command(self, domain: UniversalMessageDomain) -> None:
        """Mark the active command for a domain as completed."""
        queue_state = self._queue_state(domain)
        command = queue_state.current_command
        if command is None:
            return

        completed_command_name = command.execute_name
        follow_up_get_action = command.follow_up_get
        follow_up_high_priority = command.priority > 0
        self._cancel_command_timeout(command)

        # If this GET command was being ignored during a mechanical delay, stop ignoring it now
        # This allows future responses of this type to be processed normally
        if command.action in self._ignored_get_actions:
            self._ignored_get_actions.discard(command.action)
            _LOGGER.debug(
                "Stopped ignoring %s responses - delayed follow-up GET completed",
                command.action.name,
            )

        queue_state.pop_current()

        # Save session state after successful command completion to keep counter in sync
        # This prevents stale session errors on HA restart
        if self._persistent_state_loaded:
            self._schedule_state_save()

        # Queue follow-up GET if this was a SET command with follow_up_get
        if follow_up_get_action:
            # Use longer delay for mechanical actuators (charge port, windows, closures, charging relay)
            # to give physical components time to complete movement
            mechanical_actions = {
                BLECarServerVehicleAction.SET_OPEN_CHARGE_PORT_DOOR,
                BLECarServerVehicleAction.SET_CLOSE_CHARGE_PORT_DOOR,
                BLECarServerVehicleAction.SET_WINDOWS_SWITCH,
                BLECarServerVehicleAction.SET_CHARGING_SWITCH,
            }
            is_mechanical = command.action in mechanical_actions
            delay = FOLLOW_UP_DELAY_MECHANICAL if is_mechanical else 0.5

            # Remove any queued low priority GETs of this type (polling)
            queue_state = self._queue_state(domain)
            removed = queue_state.remove_low_priority_by_action(follow_up_get_action)
            if removed > 0:
                _LOGGER.debug(
                    "Removed %d stale low-priority %s commands from queue during %.1fs delay",
                    removed,
                    follow_up_get_action.name,
                    delay,
                )

            # Mark this action as ignored to skip any in-flight response processing
            # This prevents stale polling responses from overwriting optimistic state during delay
            self._ignored_get_actions.add(follow_up_get_action)
            _LOGGER.debug(
                "Ignoring %s responses for %.1fs until delayed follow-up completes",
                follow_up_get_action.name,
                delay,
            )

            async def _delay_follow_up() -> None:
                await asyncio.sleep(delay)
                self._queue_follow_up_get(
                    follow_up_get_action,
                    f"after {completed_command_name} completed",
                    high_priority=follow_up_high_priority,
                )
                await self._process_domain_queue(domain)

            self._spawn_task(_delay_follow_up(), f"delay_follow_up.{follow_up_get_action.name}")

        # If a VCSEC command completed and there are commands WAITING_FOR_WAKE,
        # immediately check if vehicle is awake (don't wait for 10s interval)
        if domain == UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY:
            has_waiting_commands = any(
                cmd.state == BLECommandState.WAITING_FOR_WAKE
                for cmd in queue_state.iter_all()
            )
            # Treat the command that just completed as still covering the wake poll to avoid
            # immediately re-queueing the same get_vehicle_state request ahead of wake_vehicle.
            completed_was_poll = completed_command_name == "get_vehicle_state"
            has_pending_poll = completed_was_poll or any(
                cmd.execute_name == "get_vehicle_state" and cmd.priority > 0
                for cmd in queue_state.iter_all()
            )
            if has_waiting_commands and self.data.get("is_asleep") and not has_pending_poll:
                _LOGGER.debug("Commands waiting for wake, queuing immediate VCSEC poll to check status")
                async def _queue_wake_poll() -> None:
                    await self._queue_command(
                        "get_vehicle_state",
                        BLECarServerVehicleAction.DO_NOTHING,
                        UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
                        priority=1,  # HIGH priority
                    )
                self._spawn_task(_queue_wake_poll(), "queue_wake_poll")

        # For Infotainment, queue the next command in the cycle
        if domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT:
            # Find the next command in the cycle
            current_index = next((i for i, (name, _) in enumerate(self.INFOTAINMENT_POLL_CYCLE) if name == completed_command_name), -1)
            if current_index >= 0:
                next_index = (current_index + 1) % len(self.INFOTAINMENT_POLL_CYCLE)
                next_name, next_action = self.INFOTAINMENT_POLL_CYCLE[next_index]

                # Queue the next command asynchronously
                async def _queue_next_infotainment() -> None:
                    await self._queue_command(next_name, next_action, UniversalMessageDomain.DOMAIN_INFOTAINMENT)

                self._spawn_task(_queue_next_infotainment(), f"next_infotainment.{next_name}")

        # Trigger coordinator update when data has changed
        if self._data_update_callback:
            _LOGGER.debug("Triggering data update callback for domain %s", domain)
            self._data_update_callback()
        else:
            _LOGGER.warning("%sNo data update callback registered", self._log_prefix)

        self._spawn_task(self._process_domain_queue(domain), f"complete_kick.{domain.name}")

    def _requeue_domain_command(self, domain: UniversalMessageDomain) -> None:
        """Requeue the active command for a domain to retry later."""
        queue_state = self._queue_state(domain)
        command = queue_state.current_command
        if command is None:
            return

        self._cancel_command_timeout(command)
        command.state = BLECommandState.READY
        command.last_tx_at = time.time()
        self._spawn_task(self._process_domain_queue(domain), f"requeue_kick.{domain.name}")

    async def _execute_command(self, command: BLECommand) -> None:
        """Execute a specific command."""
        if self.protocol_client is None:
            raise RuntimeError("Protocol client not initialized")

        try:
            # Set started_at when command actually starts executing (not when queued)
            if command.started_at == 0:
                command.started_at = time.time()

            _LOGGER.debug("Executing command: %s", command.execute_name)

            message_bytes: bytes | None = None
            action_spec: ActionMessageDetail | None = None

            if command.domain == UniversalMessageDomain.DOMAIN_INFOTAINMENT:
                action_spec = ACTION_SPECIFICS.get(command.action)
                if not action_spec:
                    _LOGGER.error("%sUnknown action: %s", self._log_prefix, command.action)
                    return

                if action_spec.which_msg == AllowedMsg.VehicleActionMessage:
                    parameter = command.parameter or 0
                    parameter_bool = command.parameter_bool
                    if parameter_bool is None and command.parameter is not None:
                        parameter_bool = bool(command.parameter)

                    message_bytes = self.protocol_client.build_carserver_vehicle_action(
                        command.action,
                        parameter=parameter,
                        parameter_bool=parameter_bool,
                        parameter_float=command.parameter_float,
                        parameter2=command.parameter2,
                    )
                elif action_spec.which_msg == AllowedMsg.GetVehicleDataMessage:
                    message_bytes = self.protocol_client.build_carserver_get_vehicle_data(
                        command.action
                    )
                else:
                    _LOGGER.error("%sUnhandled message type for action %s", self._log_prefix, command.action)
                    return

            elif command.domain == UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY:
                from .proto import vcsec_pb2

                if command.execute_name == "wake_vehicle":
                    message_bytes = self.protocol_client.build_vcsec_action_message(
                        vcsec_pb2.RKEAction_E.RKE_ACTION_WAKE_VEHICLE
                    )
                elif command.execute_name == "get_vehicle_state":
                    message_bytes = self.protocol_client.build_vcsec_information_request(
                        vcsec_pb2.InformationRequestType.INFORMATION_REQUEST_TYPE_GET_STATUS,
                        encrypt=False,
                    )
                elif command.execute_name == "lock_doors":
                    message_bytes = self.protocol_client.build_vcsec_action_message(
                        vcsec_pb2.RKEAction_E.RKE_ACTION_LOCK
                    )
                elif command.execute_name == "unlock_doors":
                    message_bytes = self.protocol_client.build_vcsec_action_message(
                        vcsec_pb2.RKEAction_E.RKE_ACTION_UNLOCK
                    )
                elif command.execute_name.startswith("closure_move_"):
                    # Parse closure_move_<closure>_<move> format (e.g., closure_move_rearTrunk_open)
                    parts = command.execute_name.split("_", 3)
                    if len(parts) >= 4:
                        closure_type = parts[2]
                        move_type = parts[3]
                        closure_request = vcsec_pb2.ClosureMoveRequest()

                        if move_type == "open":
                            move_enum = vcsec_pb2.ClosureMoveType_E.CLOSURE_MOVE_TYPE_OPEN
                        elif move_type == "close":
                            move_enum = vcsec_pb2.ClosureMoveType_E.CLOSURE_MOVE_TYPE_CLOSE
                        else:
                            move_enum = vcsec_pb2.ClosureMoveType_E.CLOSURE_MOVE_TYPE_MOVE

                        mapping = {
                            "frontTrunk": "frontTrunk",
                            "rearTrunk": "rearTrunk",
                            "chargePort": "chargePort",
                            "frontDriverDoor": "frontDriverDoor",
                        }

                        if closure_type in mapping:
                            setattr(closure_request, mapping[closure_type], move_enum)
                            message_bytes = self.protocol_client.build_vcsec_closure_move_request(closure_request)
                        else:
                            _LOGGER.error("%sUnknown closure type: %s", self._log_prefix, closure_type)
                            return
                    else:
                        _LOGGER.error("%sInvalid closure_move command format: %s", self._log_prefix, command.execute_name)
                        return
                else:
                    _LOGGER.debug("Unhandled VCSEC command %s", command.execute_name)
                    return

            else:
                _LOGGER.debug("Unsupported command domain: %s", command.domain)
                return

            if message_bytes is None:
                _LOGGER.debug("No payload built for command %s", command.execute_name)
                return

            await self._write_ble_data(message_bytes)

        except Exception as ex:
            _LOGGER.error("%sFailed to execute command %s: %s", self._log_prefix, command.execute_name, ex)
            raise

    def set_ble_available(self, available: bool) -> None:
        """Set BLE availability from coordinator.

        Called by the coordinator when BLE advertisements are received (available=True)
        or when the BLE stack determines the device is gone (available=False).
        """
        if self._ble_available != available:
            _LOGGER.info(
                "BLE availability changed: %s -> %s",
                self._ble_available, available
            )
            self._ble_available = available

    def is_available(self) -> bool:
        """Check if device is available (BLE in range).

        Uses the BLE stack's detection of whether the device is advertising.
        No timeout logic - we trust the coordinator's unavailable callback.
        """
        _LOGGER.debug("is_available check: ble_available=%s", self._ble_available)
        return self._ble_available

    async def pair_key(self, timeout: float = 30.0, wait_for_completion: bool = True) -> bool:
        """Pair BLE key with vehicle, optionally waiting for completion."""
        try:
            if not self.is_connected:
                await self._connect()

            # Initialize crypto manager
            await self._initialize_crypto()

            # Initialize keys if not already done
            private_key_bytes: bytes | None = None
            if self.private_key:
                private_key_bytes = (
                    bytes.fromhex(self.private_key)
                    if isinstance(self.private_key, str)
                    else self.private_key
                )

            await self.key_manager.initialize_keys(private_key_bytes)

            if private_key_bytes is None:
                # Persist generated key material so subsequent sessions reuse it
                generated_key = self.key_manager.get_private_key_data()
                self.private_key = generated_key.hex()
                self.public_key = self.key_manager.get_public_key_data().hex()
                # Write back to the config entry so the key survives HA restart.
                # Without this, the in-memory key is lost on reload and the just-paired
                # device is effectively unpaired on the next boot.
                self._persist_keys_to_config_entry()
            elif self.public_key is None:
                self.public_key = self.key_manager.get_public_key_data().hex()
            # Crypto is now usable for this device after a successful pair_key call.
            self._crypto_ready = True

            # Set up pairing completion tracking
            self._pairing_complete = False
            self._pairing_success = False
            self._pairing_failure_reason = None
            self._pairing_wait_info = None
            self._pairing_error_info = None

            # Start pairing process by creating VCSEC whitelist message (ESPHome pattern)
            from .protocol import TeslaKeysRole, TeslaKeyFormFactor

            if self.protocol_client is None:
                raise RuntimeError("Protocol client not initialized")

            whitelist_message = self.protocol_client.build_whitelist_message(
                role=TeslaKeysRole.ROLE_DRIVER,
                form_factor=TeslaKeyFormFactor.KEY_FORM_FACTOR_CLOUD_KEY,
            )

            await self._write_ble_data(whitelist_message)
            _LOGGER.info("Started BLE whitelist pairing process - please tap your card on the reader now")

            # Only wait for completion if requested (config flow vs runtime)
            if wait_for_completion:
                # Wait for pairing completion with timeout
                start_time = time.time()
                while not self._pairing_complete and (time.time() - start_time) < timeout:
                    await asyncio.sleep(0.5)

                if self._pairing_complete:
                    _LOGGER.info("BLE key pairing completed successfully: %s", self._pairing_success)
                    return self._pairing_success
                else:
                    reason = self._pairing_failure_reason or self._pairing_reason_from_info(self._pairing_wait_info)
                    if reason:
                        _LOGGER.error(
                            "%sBLE key pairing timed out after %s seconds: %s", self._log_prefix,
                            timeout,
                            reason,
                        )
                        self._pairing_failure_reason = reason
                    else:
                        _LOGGER.error("%sBLE key pairing timed out after %s seconds", self._log_prefix, timeout)
                    return False
            else:
                # Async mode - return immediately after sending request
                _LOGGER.info("BLE key pairing request sent (async mode)")
                return True

        except Exception as ex:
            _LOGGER.error("%sFailed to pair BLE key: %s", self._log_prefix, ex)
            return False

    async def pair(self, wait_for_completion: bool = True) -> bool:
        """Pair with Tesla vehicle - wrapper for pair_key for config flow compatibility."""
        from homeassistant.components import bluetooth

        try:
            # If we don't have a BLE device yet, try to get it from address
            if self.ble_device is None and self.address and self.hass:
                self.ble_device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address.upper(), connectable=True
                )
                if self.ble_device is None:
                    _LOGGER.error("%sCould not find BLE device at address %s", self._log_prefix, self.address)
                    return False

            # Initialize crypto manager
            await self._initialize_crypto()

            # Initialize crypto keys if provided
            if self.private_key:
                # Convert hex strings back to bytes for crypto operations
                private_key_bytes = bytes.fromhex(self.private_key) if isinstance(self.private_key, str) else self.private_key

                # Initialize keys with provided private key data
                await self.key_manager.initialize_keys(private_key_bytes)

            # Perform the actual pairing
            return await self.pair_key(wait_for_completion=wait_for_completion)

        except Exception as ex:
            _LOGGER.error("%sFailed to pair with Tesla: %s", self._log_prefix, ex)
            if self._pairing_failure_reason is None:
                self._pairing_failure_reason = "pairing_failed"
            return False

    async def pair_async(self) -> bool:
        """Pair with Tesla vehicle asynchronously (for runtime use)."""
        return await self.pair_key(wait_for_completion=False)

    def _pairing_reason_from_info(self, info_code: int | None) -> str | None:
        """Convert whitelist information codes to user-facing reason keys."""
        if info_code is None:
            return None
        from .proto import vcsec_pb2

        mapping = {
            vcsec_pb2.WhitelistOperation_information_E.WHITELISTOPERATION_INFORMATION_LOCAL_ENTITY_AUTH_FAILED_TIMED_OUT_WAITING_FOR_TAP: "pairing_tap_timeout",
            vcsec_pb2.WhitelistOperation_information_E.WHITELISTOPERATION_INFORMATION_LOCAL_ENTITY_AUTH_FAILED_UI_DENIED: "pairing_ui_denied",
            vcsec_pb2.WhitelistOperation_information_E.WHITELISTOPERATION_INFORMATION_LOCAL_ENTITY_AUTH_FAILED_VALET_MODE: "pairing_valet_mode",
            vcsec_pb2.WhitelistOperation_information_E.WHITELISTOPERATION_INFORMATION_LOCAL_ENTITY_AUTH_FAILED_CANCELLED: "pairing_cancelled",
            vcsec_pb2.WhitelistOperation_information_E.WHITELISTOPERATION_INFORMATION_NO_PERMISSION_TO_ADD: "pairing_no_permission",
            vcsec_pb2.WhitelistOperation_information_E.WHITELISTOPERATION_INFORMATION_ATTEMPTING_TO_ADD_KEY_THAT_IS_ALREADY_ON_THE_WHITELIST: "pairing_already_on_whitelist",
        }
        return mapping.get(info_code, "pairing_failed")

    @property
    def pairing_failure_reason(self) -> str | None:
        """Return the last recorded pairing failure reason."""
        return self._pairing_failure_reason



    async def wake_vehicle(self) -> bool:
        """Wake the vehicle using command queue with retries.

        Queues wake command with high priority and follows up with VCSEC poll
        to detect wake status change quickly.
        """
        try:
            # Queue wake command with high priority
            await self._queue_command(
                "wake_vehicle",
                BLECarServerVehicleAction.DO_NOTHING,
                UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
                priority=1,
            )

            # Queue immediate VCSEC poll to detect wake (also high priority)
            await self._queue_command(
                "get_vehicle_state",
                BLECarServerVehicleAction.DO_NOTHING,
                UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
                priority=1,
            )

            # Process VCSEC commands immediately
            await self._process_domain_queue(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)
            return True
        except Exception as ex:
            _LOGGER.error("%sFailed to queue wake command: %s", self._log_prefix, ex)
            return False

    async def lock_unlock_vehicle(self, lock: bool) -> bool:
        """Lock or unlock the vehicle."""
        _LOGGER.info("Lock/unlock vehicle called: lock=%s", lock)
        try:
            await self._initialize_crypto()

            if self.protocol_client is None:
                raise RuntimeError("Protocol client not initialized")

            if not self.is_connected:
                await self._connect()

            if not self.key_manager.is_session_valid(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY):
                await self._send_session_info_request(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)

            # Queue lock/unlock command with HIGH priority (user action)
            execute_name = "lock_doors" if lock else "unlock_doors"
            await self._queue_command(
                execute_name,
                BLECarServerVehicleAction.DO_NOTHING,
                UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
                priority=1,
            )
            await self._process_domain_queue(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)

            # Queue immediate VCSEC poll to get updated lock state
            await self._queue_command(
                "get_vehicle_state",
                BLECarServerVehicleAction.DO_NOTHING,
                UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
                priority=1,
            )
            await self._process_domain_queue(UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY)

            return True

        except Exception as ex:
            _LOGGER.error("%sFailed to lock/unlock vehicle: %s", self._log_prefix, ex)
            return False
