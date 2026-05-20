"""Tesla BLE Protocol implementation."""

from __future__ import annotations

import enum
import logging
import time
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


class UniversalMessageDomain(enum.IntEnum):
    """Tesla Universal Message domains."""
    DOMAIN_BROADCAST = 0
    DOMAIN_VEHICLE_SECURITY = 2
    DOMAIN_INFOTAINMENT = 3


class VCSECRKEAction(enum.IntEnum):
    """VCSEC RKE (Remote Keyless Entry) actions."""
    RKE_ACTION_LOCK = 1
    RKE_ACTION_UNLOCK = 2


class VCSECClosureMoveType(enum.IntEnum):
    """VCSEC Closure move types."""
    CLOSURE_MOVE_TYPE_NONE = 0
    CLOSURE_MOVE_TYPE_MOVE = 1
    CLOSURE_MOVE_TYPE_STOP = 2


class BLECarServerVehicleAction(enum.IntEnum):
    """BLE CarServer vehicle actions."""
    DO_NOTHING = 0
    GET_CHARGE_STATE = 1
    GET_CLIMATE_STATE = 2
    GET_DRIVE_STATE = 3
    GET_LOCATION_STATE = 4
    GET_CLOSURES_STATE = 5
    SET_CHARGING_SWITCH = 6
    SET_CHARGING_AMPS = 7
    SET_CHARGING_LIMIT = 8
    SET_SENTRY_SWITCH = 9
    SET_HVAC_SWITCH = 10
    SET_HVAC_STEERING_HEATER_SWITCH = 11
    SET_OPEN_CHARGE_PORT_DOOR = 12
    SET_CLOSE_CHARGE_PORT_DOOR = 13
    SOUND_HORN = 14
    FLASH_LIGHT = 15
    SET_WINDOWS_SWITCH = 16
    DEFROST_CAR = 17
    GET_TIRE_PRESSURE_STATE = 18


class AllowedMsg(enum.IntEnum):
    """Allowed message types."""
    VehicleActionMessage = 0
    GetVehicleDataMessage = 1
    Empty = 2


class GetOnSet(enum.IntEnum):
    """Get operation types to perform after set commands."""
    GetChargeState = 0
    GetClimateState = 1
    GetDriveState = 2
    GetLocationState = 3
    GetClosureState = 4
    Invalid = 5


class TeslaKeysRole(enum.IntEnum):
    """Tesla Keys Role enum (from keys.pb.h)."""
    ROLE_NONE = 0
    ROLE_SERVICE = 1
    ROLE_OWNER = 2
    ROLE_DRIVER = 3
    ROLE_FM = 4
    ROLE_VEHICLE_MONITOR = 5
    ROLE_CHARGING_MANAGER = 6


class TeslaKeyFormFactor(enum.IntEnum):
    """Tesla Key Form Factor enum (from vcsec.pb.h)."""
    KEY_FORM_FACTOR_UNKNOWN = 0
    KEY_FORM_FACTOR_NFC_CARD = 1
    KEY_FORM_FACTOR_IOS_DEVICE = 6
    KEY_FORM_FACTOR_ANDROID_DEVICE = 7
    KEY_FORM_FACTOR_CLOUD_KEY = 9


class BLECommandState(enum.IntEnum):
    """BLE command processing states."""
    IDLE = 0
    WAITING_FOR_VCSEC_AUTH = 1
    WAITING_FOR_VCSEC_AUTH_RESPONSE = 2
    WAITING_FOR_INFOTAINMENT_AUTH = 3
    WAITING_FOR_INFOTAINMENT_AUTH_RESPONSE = 4
    WAITING_FOR_WAKE = 5
    READY = 6
    WAITING_FOR_RESPONSE = 7
    WAITING_FOR_GET_POST_SET = 8


@dataclass
class ActionMessageDetail:
    """Tesla action message specification."""
    local_action_def: BLECarServerVehicleAction
    action_str: str
    which_msg: AllowedMsg
    action_tag: int
    get_on_set: GetOnSet


# Action specifications mapping ESPHome ACTION_SPECIFICS table
ACTION_SPECIFICS = {
    BLECarServerVehicleAction.DO_NOTHING: ActionMessageDetail(
        BLECarServerVehicleAction.DO_NOTHING,
        "",
        AllowedMsg.Empty,
        0,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.GET_CHARGE_STATE: ActionMessageDetail(
        BLECarServerVehicleAction.GET_CHARGE_STATE,
        "getChargeState",
        AllowedMsg.GetVehicleDataMessage,
        1,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.GET_CLIMATE_STATE: ActionMessageDetail(
        BLECarServerVehicleAction.GET_CLIMATE_STATE,
        "getClimateState",
        AllowedMsg.GetVehicleDataMessage,
        2,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.GET_DRIVE_STATE: ActionMessageDetail(
        BLECarServerVehicleAction.GET_DRIVE_STATE,
        "getDriveState",
        AllowedMsg.GetVehicleDataMessage,
        3,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.GET_LOCATION_STATE: ActionMessageDetail(
        BLECarServerVehicleAction.GET_LOCATION_STATE,
        "getLocationState",
        AllowedMsg.GetVehicleDataMessage,
        4,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.GET_CLOSURES_STATE: ActionMessageDetail(
        BLECarServerVehicleAction.GET_CLOSURES_STATE,
        "getClosuresState",
        AllowedMsg.GetVehicleDataMessage,
        5,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.SET_CHARGING_SWITCH: ActionMessageDetail(
        BLECarServerVehicleAction.SET_CHARGING_SWITCH,
        "setChargingSwitch",
        AllowedMsg.VehicleActionMessage,
        10,
        GetOnSet.GetChargeState,
    ),
    BLECarServerVehicleAction.SET_CHARGING_AMPS: ActionMessageDetail(
        BLECarServerVehicleAction.SET_CHARGING_AMPS,
        "setChargingAmps",
        AllowedMsg.VehicleActionMessage,
        11,
        GetOnSet.GetChargeState,
    ),
    BLECarServerVehicleAction.SET_CHARGING_LIMIT: ActionMessageDetail(
        BLECarServerVehicleAction.SET_CHARGING_LIMIT,
        "setChargingLimit",
        AllowedMsg.VehicleActionMessage,
        12,
        GetOnSet.GetChargeState,
    ),
    BLECarServerVehicleAction.SET_SENTRY_SWITCH: ActionMessageDetail(
        BLECarServerVehicleAction.SET_SENTRY_SWITCH,
        "setSentrySwitch",
        AllowedMsg.VehicleActionMessage,
        30,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.SET_HVAC_SWITCH: ActionMessageDetail(
        BLECarServerVehicleAction.SET_HVAC_SWITCH,
        "setHVACSwitch",
        AllowedMsg.VehicleActionMessage,
        20,
        GetOnSet.GetClimateState,
    ),
    BLECarServerVehicleAction.SET_HVAC_STEERING_HEATER_SWITCH: ActionMessageDetail(
        BLECarServerVehicleAction.SET_HVAC_STEERING_HEATER_SWITCH,
        "setHVACSteeringHeatSwitch",
        AllowedMsg.VehicleActionMessage,
        21,
        GetOnSet.GetClimateState,
    ),
    BLECarServerVehicleAction.SET_OPEN_CHARGE_PORT_DOOR: ActionMessageDetail(
        BLECarServerVehicleAction.SET_OPEN_CHARGE_PORT_DOOR,
        "setOpenChargePortDoor",
        AllowedMsg.VehicleActionMessage,
        40,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.SET_CLOSE_CHARGE_PORT_DOOR: ActionMessageDetail(
        BLECarServerVehicleAction.SET_CLOSE_CHARGE_PORT_DOOR,
        "setCloseChargePortDoor",
        AllowedMsg.VehicleActionMessage,
        41,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.SOUND_HORN: ActionMessageDetail(
        BLECarServerVehicleAction.SOUND_HORN,
        "soundHorn",
        AllowedMsg.VehicleActionMessage,
        50,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.FLASH_LIGHT: ActionMessageDetail(
        BLECarServerVehicleAction.FLASH_LIGHT,
        "flashLights",
        AllowedMsg.VehicleActionMessage,
        51,
        GetOnSet.Invalid,
    ),
    BLECarServerVehicleAction.SET_WINDOWS_SWITCH: ActionMessageDetail(
        BLECarServerVehicleAction.SET_WINDOWS_SWITCH,
        "setWindowsSwitch",
        AllowedMsg.VehicleActionMessage,
        60,
        GetOnSet.GetClosureState,
    ),
    BLECarServerVehicleAction.DEFROST_CAR: ActionMessageDetail(
        BLECarServerVehicleAction.DEFROST_CAR,
        "defrostCar",
        AllowedMsg.VehicleActionMessage,
        70,
        GetOnSet.GetClimateState,
    ),
    BLECarServerVehicleAction.GET_TIRE_PRESSURE_STATE: ActionMessageDetail(
        BLECarServerVehicleAction.GET_TIRE_PRESSURE_STATE,
        "getTirePressureState",
        AllowedMsg.GetVehicleDataMessage,
        14,
        GetOnSet.Invalid,
    ),
}

FOLLOW_UP_ACTION: Dict[GetOnSet, BLECarServerVehicleAction] = {
    GetOnSet.GetChargeState: BLECarServerVehicleAction.GET_CHARGE_STATE,
    GetOnSet.GetClimateState: BLECarServerVehicleAction.GET_CLIMATE_STATE,
    GetOnSet.GetDriveState: BLECarServerVehicleAction.GET_DRIVE_STATE,
    GetOnSet.GetLocationState: BLECarServerVehicleAction.GET_LOCATION_STATE,
    GetOnSet.GetClosureState: BLECarServerVehicleAction.GET_CLOSURES_STATE,
}


@dataclass
class BLECommand:
    """BLE command structure."""
    execute_name: str
    action: BLECarServerVehicleAction
    domain: UniversalMessageDomain
    parameter: Optional[int] = None
    parameter_bool: Optional[bool] = None
    parameter_float: Optional[float] = None
    parameter2: Optional[int] = None
    started_at: float = 0
    last_tx_at: float = 0
    state: BLECommandState = BLECommandState.IDLE
    retry_count: int = 0
    done_times: int = 0
    retry_delay: float = 0.0
    priority: int = 0  # 0=normal (polling), 1=high (user commands)
    follow_up_get: Optional[BLECarServerVehicleAction] = None  # GET command to queue after SET completes
    timeout_handle: asyncio.TimerHandle | None = None
    requeue_count: int = 0  # Track how many times command has been re-queued after timeout


@dataclass
class SessionInfo:
    """Session information for domains."""
    clock_time: int = 0
    counter: int = 0
    public_key: bytes = b""
    epoch: bytes = b""


@dataclass
class VehicleStatus:
    """Vehicle status from VCSEC."""
    vehicle_sleep_status: int = 0
    vehicle_lock_state: int = 0
    user_presence: int = 0


@dataclass
class ChargeState:
    """Vehicle charge state."""
    charging_state: str = ""
    battery_level: int = 0
    charge_limit_soc: int = 0
    charge_current_request: int = 0
    charge_actual_current: int = 0
    charger_voltage: int = 0
    charger_power: int = 0
    battery_range: float = 0
    charge_port_door_open: bool = False


@dataclass
class ClimateState:
    """Vehicle climate state."""
    inside_temp: float = 0
    outside_temp: float = 0
    is_climate_on: bool = False
    is_preconditioning: bool = False
    driver_temp_setting: float = 0
    passenger_temp_setting: float = 0
    defrost_mode: int = 0


@dataclass
class DriveState:
    """Vehicle drive state."""
    shift_state: str = ""
    speed: int = 0
    power: int = 0
    latitude: float = 0
    longitude: float = 0
    heading: int = 0
    gps_as_of: int = 0


class TeslaProtocolError(Exception):
    """Tesla protocol specific errors."""
    pass


class TeslaSessionError(TeslaProtocolError):
    """Tesla session authentication errors."""
    pass


class TeslaCommandError(TeslaProtocolError):
    """Tesla command execution errors."""
    pass
