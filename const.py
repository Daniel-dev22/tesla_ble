"""Constants for Tesla BLE integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "tesla_ble"
MANUFACTURER = "Tesla"

# Bluetooth UUIDs
SERVICE_UUID = "00000211-b2d1-43f0-9b88-960cebf8b91e"
WRITE_UUID = "00000212-b2d1-43f0-9b88-960cebf8b91e"
READ_UUID = "00000213-b2d1-43f0-9b88-960cebf8b91e"

# Configuration
CONF_VIN = "vin"
CONF_PRIVATE_KEY = "private_key"
CONF_PUBLIC_KEY = "public_key"
CONF_SESSION_DATA = "session_data"

# Platforms
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.COVER,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Polling intervals (seconds) - matching ESPHome defaults
# DEFAULT_UPDATE_INTERVAL is used for VCSEC keepalive polling (matches ESPHome's 10s default)
DEFAULT_UPDATE_INTERVAL = 10
DEFAULT_POST_WAKE_POLL_TIME = 300
DEFAULT_POLL_DATA_PERIOD = 60
DEFAULT_POLL_ASLEEP_PERIOD = 60
DEFAULT_POLL_CHARGING_PERIOD = 10
DEFAULT_BLE_DISCONNECTED_MIN_TIME = 300
DEFAULT_FAST_POLL_IF_UNLOCKED = 0
DEFAULT_WAKE_ON_BOOT = 0
DEFAULT_DEBUG_LOGGING = False

# Configuration keys for polling settings
CONF_UPDATE_INTERVAL = "update_interval"
CONF_POST_WAKE_POLL_TIME = "post_wake_poll_time"
CONF_POLL_DATA_PERIOD = "poll_data_period"
CONF_POLL_ASLEEP_PERIOD = "poll_asleep_period"
CONF_POLL_CHARGING_PERIOD = "poll_charging_period"
CONF_BLE_DISCONNECTED_MIN_TIME = "ble_disconnected_min_time"
CONF_FAST_POLL_IF_UNLOCKED = "fast_poll_if_unlocked"
CONF_WAKE_ON_BOOT = "wake_on_boot"
CONF_DEBUG_LOGGING = "debug_logging"

# Command timeout
COMMAND_TIMEOUT = 2000  # 2 seconds in milliseconds
MAX_LATENCY = 2.0  # 2 seconds for SessionInfo response timeout

# Vehicle states
VEHICLE_STATE_ASLEEP = "asleep"
VEHICLE_STATE_AWAKE = "awake"

# Charging states
CHARGING_STATE_DISCONNECTED = "Disconnected"
CHARGING_STATE_STOPPED = "Stopped"
CHARGING_STATE_CHARGING = "Charging"
CHARGING_STATE_COMPLETE = "Complete"

# Shift states
SHIFT_STATE_INVALID = "Invalid"
SHIFT_STATE_PARK = "P"
SHIFT_STATE_REVERSE = "R"
SHIFT_STATE_NEUTRAL = "N"
SHIFT_STATE_DRIVE = "D"
