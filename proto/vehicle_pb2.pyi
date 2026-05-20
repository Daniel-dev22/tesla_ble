from google.protobuf import timestamp_pb2 as _timestamp_pb2
import vcsec_pb2 as _vcsec_pb2
import common_pb2 as _common_pb2
import managed_charging_pb2 as _managed_charging_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor
MediaSourceType_AM: MediaSourceType
MediaSourceType_AuxIn: MediaSourceType
MediaSourceType_Bluetooth: MediaSourceType
MediaSourceType_Browser: MediaSourceType
MediaSourceType_DAB: MediaSourceType
MediaSourceType_EURadio: MediaSourceType
MediaSourceType_FM: MediaSourceType
MediaSourceType_Game: MediaSourceType
MediaSourceType_HomeApps: MediaSourceType
MediaSourceType_LocalFiles: MediaSourceType
MediaSourceType_MediaFile: MediaSourceType
MediaSourceType_NetEaseMusic: MediaSourceType
MediaSourceType_None: MediaSourceType
MediaSourceType_OnlineRadio: MediaSourceType
MediaSourceType_OnlineRadio2: MediaSourceType
MediaSourceType_QQMusic: MediaSourceType
MediaSourceType_QQMusic2: MediaSourceType
MediaSourceType_Rdio: MediaSourceType
MediaSourceType_RecentsFavorites: MediaSourceType
MediaSourceType_Search: MediaSourceType
MediaSourceType_SiriusXM: MediaSourceType
MediaSourceType_Slacker: MediaSourceType
MediaSourceType_Spotify: MediaSourceType
MediaSourceType_Stingray: MediaSourceType
MediaSourceType_Theater: MediaSourceType
MediaSourceType_Tidal: MediaSourceType
MediaSourceType_Toybox: MediaSourceType
MediaSourceType_TuneIn: MediaSourceType
MediaSourceType_Tutorial: MediaSourceType
MediaSourceType_USRadio: MediaSourceType
MediaSourceType_XM: MediaSourceType
MediaSourceType_Ximalaya: MediaSourceType
MediaSourceType_iPod: MediaSourceType

class ChargeOnSolarState(_message.Message):
    __slots__ = ["charging_on_anything", "charging_on_excess_solar", "error", "no_charge_recommended", "not_allowed", "user_disabled", "user_stopped", "waiting_for_server"]
    CHARGING_ON_ANYTHING_FIELD_NUMBER: _ClassVar[int]
    CHARGING_ON_EXCESS_SOLAR_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    NOT_ALLOWED_FIELD_NUMBER: _ClassVar[int]
    NO_CHARGE_RECOMMENDED_FIELD_NUMBER: _ClassVar[int]
    USER_DISABLED_FIELD_NUMBER: _ClassVar[int]
    USER_STOPPED_FIELD_NUMBER: _ClassVar[int]
    WAITING_FOR_SERVER_FIELD_NUMBER: _ClassVar[int]
    charging_on_anything: ChargeOnSolarStateChargingOnAnything
    charging_on_excess_solar: ChargeOnSolarStateChargingOnExcessSolar
    error: ChargeOnSolarStateError
    no_charge_recommended: ChargeOnSolarStateNoChargeRecommended
    not_allowed: ChargeOnSolarStateNotAllowed
    user_disabled: ChargeOnSolarStateUserDisabled
    user_stopped: ChargeOnSolarStateUserStopped
    waiting_for_server: ChargeOnSolarStateWaitingForServer
    def __init__(self, not_allowed: _Optional[_Union[ChargeOnSolarStateNotAllowed, _Mapping]] = ..., no_charge_recommended: _Optional[_Union[ChargeOnSolarStateNoChargeRecommended, _Mapping]] = ..., charging_on_excess_solar: _Optional[_Union[ChargeOnSolarStateChargingOnExcessSolar, _Mapping]] = ..., charging_on_anything: _Optional[_Union[ChargeOnSolarStateChargingOnAnything, _Mapping]] = ..., user_disabled: _Optional[_Union[ChargeOnSolarStateUserDisabled, _Mapping]] = ..., waiting_for_server: _Optional[_Union[ChargeOnSolarStateWaitingForServer, _Mapping]] = ..., error: _Optional[_Union[ChargeOnSolarStateError, _Mapping]] = ..., user_stopped: _Optional[_Union[ChargeOnSolarStateUserStopped, _Mapping]] = ...) -> None: ...

class ChargeOnSolarStateChargingOnAnything(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ChargeOnSolarStateChargingOnExcessSolar(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ChargeOnSolarStateError(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ChargeOnSolarStateNoChargeRecommended(_message.Message):
    __slots__ = ["reason"]
    REASON_FIELD_NUMBER: _ClassVar[int]
    reason: _managed_charging_pb2.ChargeOnSolarNoChargeReason
    def __init__(self, reason: _Optional[_Union[_managed_charging_pb2.ChargeOnSolarNoChargeReason, str]] = ...) -> None: ...

class ChargeOnSolarStateNotAllowed(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ChargeOnSolarStateUserDisabled(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ChargeOnSolarStateUserStopped(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ChargeOnSolarStateWaitingForServer(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ChargeScheduleState(_message.Message):
    __slots__ = ["charge_buffer", "charge_schedule_window", "charge_schedules", "max_num_charge_schedules", "next_schedule", "show_schedule_complete_state", "timestamp"]
    CHARGE_BUFFER_FIELD_NUMBER: _ClassVar[int]
    CHARGE_SCHEDULES_FIELD_NUMBER: _ClassVar[int]
    CHARGE_SCHEDULE_WINDOW_FIELD_NUMBER: _ClassVar[int]
    MAX_NUM_CHARGE_SCHEDULES_FIELD_NUMBER: _ClassVar[int]
    NEXT_SCHEDULE_FIELD_NUMBER: _ClassVar[int]
    SHOW_SCHEDULE_COMPLETE_STATE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    charge_buffer: int
    charge_schedule_window: _common_pb2.ChargeSchedule
    charge_schedules: _containers.RepeatedCompositeFieldContainer[_common_pb2.ChargeSchedule]
    max_num_charge_schedules: int
    next_schedule: bool
    show_schedule_complete_state: bool
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, charge_schedules: _Optional[_Iterable[_Union[_common_pb2.ChargeSchedule, _Mapping]]] = ..., charge_schedule_window: _Optional[_Union[_common_pb2.ChargeSchedule, _Mapping]] = ..., charge_buffer: _Optional[int] = ..., max_num_charge_schedules: _Optional[int] = ..., next_schedule: bool = ..., show_schedule_complete_state: bool = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ChargeState(_message.Message):
    __slots__ = ["battery_level", "battery_range", "charge_cable_unlatched", "charge_current_request", "charge_current_request_max", "charge_enable_request", "charge_energy_added", "charge_limit_reason", "charge_limit_soc", "charge_limit_soc_max", "charge_limit_soc_min", "charge_limit_soc_std", "charge_miles_added_ideal", "charge_miles_added_rated", "charge_port_cold_weather_mode", "charge_port_color", "charge_port_door_open", "charge_port_latch", "charge_rate_mph", "charge_rate_mph_float", "charger_actual_current", "charger_phases", "charger_pilot_current", "charger_power", "charger_voltage", "charging_amps", "charging_state", "conn_charge_cable", "est_battery_range", "fast_charger_brand", "fast_charger_present", "fast_charger_type", "home_location", "ideal_battery_range", "managed_charging_active", "managed_charging_start_time", "managed_charging_state", "managed_charging_user_canceled", "max_range_charge_counter", "minutes_to_charge_limit", "minutes_to_full_charge", "off_peak_charging_times", "off_peak_hours_end_time", "one_time_soc_limit", "outlet_max_timer_minutes", "outlet_soc_limit", "outlet_state", "outlet_time_remaining", "power_feed_soc_limit", "power_feed_state", "power_feed_time_remaining", "powershare_feature_allowed", "powershare_feature_enabled", "powershare_instantaneous_load_kw", "powershare_request", "powershare_soc_limit", "powershare_status", "powershare_stop_reason", "powershare_type", "powershare_vehicle_energy_left_hr", "preconditioning_enabled", "preconditioning_times", "scheduled_charging_mode", "scheduled_charging_pending", "scheduled_charging_start_time", "scheduled_charging_start_time_app", "scheduled_charging_start_time_minutes", "scheduled_departure_time", "scheduled_departure_time_minutes", "supercharger_session_trip_planner", "timestamp", "trip_charging", "usable_battery_level", "user_charge_enable_request", "work_location"]
    class ChargeLimitReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class ChargePortColor_E(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class OutletState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class PowerFeedState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class PowershareStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class PowershareStopReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class PowershareType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class ScheduledChargingMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class CableType(_message.Message):
        __slots__ = ["GB_AC", "GB_DC", "IEC", "SAE", "SNA"]
        GB_AC: _common_pb2.Void
        GB_AC_FIELD_NUMBER: _ClassVar[int]
        GB_DC: _common_pb2.Void
        GB_DC_FIELD_NUMBER: _ClassVar[int]
        IEC: _common_pb2.Void
        IEC_FIELD_NUMBER: _ClassVar[int]
        SAE: _common_pb2.Void
        SAE_FIELD_NUMBER: _ClassVar[int]
        SNA: _common_pb2.Void
        SNA_FIELD_NUMBER: _ClassVar[int]
        def __init__(self, SNA: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., IEC: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., SAE: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., GB_AC: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., GB_DC: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    class ChargerBrand(_message.Message):
        __slots__ = ["SNA", "Tesla"]
        SNA: _common_pb2.Void
        SNA_FIELD_NUMBER: _ClassVar[int]
        TESLA_FIELD_NUMBER: _ClassVar[int]
        Tesla: _common_pb2.Void
        def __init__(self, Tesla: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., SNA: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    class ChargerType(_message.Message):
        __slots__ = ["ACSingleWireCAN", "Chademo", "Combo", "Gb", "MCSingleWireCAN", "Other", "SNA", "Supercharger", "Tesla"]
        ACSINGLEWIRECAN_FIELD_NUMBER: _ClassVar[int]
        ACSingleWireCAN: _common_pb2.Void
        CHADEMO_FIELD_NUMBER: _ClassVar[int]
        COMBO_FIELD_NUMBER: _ClassVar[int]
        Chademo: _common_pb2.Void
        Combo: _common_pb2.Void
        GB_FIELD_NUMBER: _ClassVar[int]
        Gb: _common_pb2.Void
        MCSINGLEWIRECAN_FIELD_NUMBER: _ClassVar[int]
        MCSingleWireCAN: _common_pb2.Void
        OTHER_FIELD_NUMBER: _ClassVar[int]
        Other: _common_pb2.Void
        SNA: _common_pb2.Void
        SNA_FIELD_NUMBER: _ClassVar[int]
        SUPERCHARGER_FIELD_NUMBER: _ClassVar[int]
        Supercharger: _common_pb2.Void
        TESLA_FIELD_NUMBER: _ClassVar[int]
        Tesla: _common_pb2.Void
        def __init__(self, SNA: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Supercharger: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Chademo: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Gb: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., ACSingleWireCAN: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Combo: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., MCSingleWireCAN: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Other: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Tesla: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    class ChargingState(_message.Message):
        __slots__ = ["Calibrating", "Charging", "Complete", "Disconnected", "NoPower", "Starting", "Stopped", "Unknown"]
        CALIBRATING_FIELD_NUMBER: _ClassVar[int]
        CHARGING_FIELD_NUMBER: _ClassVar[int]
        COMPLETE_FIELD_NUMBER: _ClassVar[int]
        Calibrating: _common_pb2.Void
        Charging: _common_pb2.Void
        Complete: _common_pb2.Void
        DISCONNECTED_FIELD_NUMBER: _ClassVar[int]
        Disconnected: _common_pb2.Void
        NOPOWER_FIELD_NUMBER: _ClassVar[int]
        NoPower: _common_pb2.Void
        STARTING_FIELD_NUMBER: _ClassVar[int]
        STOPPED_FIELD_NUMBER: _ClassVar[int]
        Starting: _common_pb2.Void
        Stopped: _common_pb2.Void
        UNKNOWN_FIELD_NUMBER: _ClassVar[int]
        Unknown: _common_pb2.Void
        def __init__(self, Unknown: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Disconnected: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., NoPower: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Starting: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Charging: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Complete: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Stopped: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Calibrating: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    BATTERY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    BATTERY_RANGE_FIELD_NUMBER: _ClassVar[int]
    CHARGER_ACTUAL_CURRENT_FIELD_NUMBER: _ClassVar[int]
    CHARGER_PHASES_FIELD_NUMBER: _ClassVar[int]
    CHARGER_PILOT_CURRENT_FIELD_NUMBER: _ClassVar[int]
    CHARGER_POWER_FIELD_NUMBER: _ClassVar[int]
    CHARGER_VOLTAGE_FIELD_NUMBER: _ClassVar[int]
    CHARGE_CABLE_UNLATCHED_FIELD_NUMBER: _ClassVar[int]
    CHARGE_CURRENT_REQUEST_FIELD_NUMBER: _ClassVar[int]
    CHARGE_CURRENT_REQUEST_MAX_FIELD_NUMBER: _ClassVar[int]
    CHARGE_ENABLE_REQUEST_FIELD_NUMBER: _ClassVar[int]
    CHARGE_ENERGY_ADDED_FIELD_NUMBER: _ClassVar[int]
    CHARGE_LIMIT_REASON_FIELD_NUMBER: _ClassVar[int]
    CHARGE_LIMIT_SOC_FIELD_NUMBER: _ClassVar[int]
    CHARGE_LIMIT_SOC_MAX_FIELD_NUMBER: _ClassVar[int]
    CHARGE_LIMIT_SOC_MIN_FIELD_NUMBER: _ClassVar[int]
    CHARGE_LIMIT_SOC_STD_FIELD_NUMBER: _ClassVar[int]
    CHARGE_MILES_ADDED_IDEAL_FIELD_NUMBER: _ClassVar[int]
    CHARGE_MILES_ADDED_RATED_FIELD_NUMBER: _ClassVar[int]
    CHARGE_PORT_COLD_WEATHER_MODE_FIELD_NUMBER: _ClassVar[int]
    CHARGE_PORT_COLOR_FIELD_NUMBER: _ClassVar[int]
    CHARGE_PORT_DOOR_OPEN_FIELD_NUMBER: _ClassVar[int]
    CHARGE_PORT_LATCH_FIELD_NUMBER: _ClassVar[int]
    CHARGE_RATE_MPH_FIELD_NUMBER: _ClassVar[int]
    CHARGE_RATE_MPH_FLOAT_FIELD_NUMBER: _ClassVar[int]
    CHARGING_AMPS_FIELD_NUMBER: _ClassVar[int]
    CHARGING_STATE_FIELD_NUMBER: _ClassVar[int]
    CONN_CHARGE_CABLE_FIELD_NUMBER: _ClassVar[int]
    ChargeLimitReasonBattTempLow: ChargeState.ChargeLimitReason
    ChargeLimitReasonCabin: ChargeState.ChargeLimitReason
    ChargeLimitReasonEvse: ChargeState.ChargeLimitReason
    ChargeLimitReasonHighSoc: ChargeState.ChargeLimitReason
    ChargeLimitReasonNone: ChargeState.ChargeLimitReason
    ChargeLimitReasonUnknown: ChargeState.ChargeLimitReason
    ChargePortColorAmber: ChargeState.ChargePortColor_E
    ChargePortColorBlue: ChargeState.ChargePortColor_E
    ChargePortColorDebug: ChargeState.ChargePortColor_E
    ChargePortColorFlashingAmber: ChargeState.ChargePortColor_E
    ChargePortColorFlashingBlue: ChargeState.ChargePortColor_E
    ChargePortColorFlashingGreen: ChargeState.ChargePortColor_E
    ChargePortColorGreen: ChargeState.ChargePortColor_E
    ChargePortColorOff: ChargeState.ChargePortColor_E
    ChargePortColorRave: ChargeState.ChargePortColor_E
    ChargePortColorRed: ChargeState.ChargePortColor_E
    ChargePortColorWhite: ChargeState.ChargePortColor_E
    EST_BATTERY_RANGE_FIELD_NUMBER: _ClassVar[int]
    FAST_CHARGER_BRAND_FIELD_NUMBER: _ClassVar[int]
    FAST_CHARGER_PRESENT_FIELD_NUMBER: _ClassVar[int]
    FAST_CHARGER_TYPE_FIELD_NUMBER: _ClassVar[int]
    HOME_LOCATION_FIELD_NUMBER: _ClassVar[int]
    IDEAL_BATTERY_RANGE_FIELD_NUMBER: _ClassVar[int]
    MANAGED_CHARGING_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    MANAGED_CHARGING_START_TIME_FIELD_NUMBER: _ClassVar[int]
    MANAGED_CHARGING_STATE_FIELD_NUMBER: _ClassVar[int]
    MANAGED_CHARGING_USER_CANCELED_FIELD_NUMBER: _ClassVar[int]
    MAX_RANGE_CHARGE_COUNTER_FIELD_NUMBER: _ClassVar[int]
    MINUTES_TO_CHARGE_LIMIT_FIELD_NUMBER: _ClassVar[int]
    MINUTES_TO_FULL_CHARGE_FIELD_NUMBER: _ClassVar[int]
    OFF_PEAK_CHARGING_TIMES_FIELD_NUMBER: _ClassVar[int]
    OFF_PEAK_HOURS_END_TIME_FIELD_NUMBER: _ClassVar[int]
    ONE_TIME_SOC_LIMIT_FIELD_NUMBER: _ClassVar[int]
    OUTLET_MAX_TIMER_MINUTES_FIELD_NUMBER: _ClassVar[int]
    OUTLET_SOC_LIMIT_FIELD_NUMBER: _ClassVar[int]
    OUTLET_STATE_FIELD_NUMBER: _ClassVar[int]
    OUTLET_TIME_REMAINING_FIELD_NUMBER: _ClassVar[int]
    OutletStateCabin: ChargeState.OutletState
    OutletStateCabinAndBed: ChargeState.OutletState
    OutletStateOff: ChargeState.OutletState
    POWERSHARE_FEATURE_ALLOWED_FIELD_NUMBER: _ClassVar[int]
    POWERSHARE_FEATURE_ENABLED_FIELD_NUMBER: _ClassVar[int]
    POWERSHARE_INSTANTANEOUS_LOAD_KW_FIELD_NUMBER: _ClassVar[int]
    POWERSHARE_REQUEST_FIELD_NUMBER: _ClassVar[int]
    POWERSHARE_SOC_LIMIT_FIELD_NUMBER: _ClassVar[int]
    POWERSHARE_STATUS_FIELD_NUMBER: _ClassVar[int]
    POWERSHARE_STOP_REASON_FIELD_NUMBER: _ClassVar[int]
    POWERSHARE_TYPE_FIELD_NUMBER: _ClassVar[int]
    POWERSHARE_VEHICLE_ENERGY_LEFT_HR_FIELD_NUMBER: _ClassVar[int]
    POWER_FEED_SOC_LIMIT_FIELD_NUMBER: _ClassVar[int]
    POWER_FEED_STATE_FIELD_NUMBER: _ClassVar[int]
    POWER_FEED_TIME_REMAINING_FIELD_NUMBER: _ClassVar[int]
    PRECONDITIONING_ENABLED_FIELD_NUMBER: _ClassVar[int]
    PRECONDITIONING_TIMES_FIELD_NUMBER: _ClassVar[int]
    PowerFeedStateCabin: ChargeState.PowerFeedState
    PowerFeedStateCabinAndBed: ChargeState.PowerFeedState
    PowerFeedStateOff: ChargeState.PowerFeedState
    PowershareStatusActive: ChargeState.PowershareStatus
    PowershareStatusActiveReconnectingSoon: ChargeState.PowershareStatus
    PowershareStatusHandshaking: ChargeState.PowershareStatus
    PowershareStatusInactive: ChargeState.PowershareStatus
    PowershareStatusInit: ChargeState.PowershareStatus
    PowershareStatusStopped: ChargeState.PowershareStatus
    PowershareStopReasonAuthentication: ChargeState.PowershareStopReason
    PowershareStopReasonFault: ChargeState.PowershareStopReason
    PowershareStopReasonNone: ChargeState.PowershareStopReason
    PowershareStopReasonReconnecting: ChargeState.PowershareStopReason
    PowershareStopReasonRetry: ChargeState.PowershareStopReason
    PowershareStopReasonSOCTooLow: ChargeState.PowershareStopReason
    PowershareStopReasonUser: ChargeState.PowershareStopReason
    PowershareTypeHome: ChargeState.PowershareType
    PowershareTypeLoad: ChargeState.PowershareType
    PowershareTypeNone: ChargeState.PowershareType
    SCHEDULED_CHARGING_MODE_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_CHARGING_PENDING_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_CHARGING_START_TIME_APP_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_CHARGING_START_TIME_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_CHARGING_START_TIME_MINUTES_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_DEPARTURE_TIME_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_DEPARTURE_TIME_MINUTES_FIELD_NUMBER: _ClassVar[int]
    SUPERCHARGER_SESSION_TRIP_PLANNER_FIELD_NUMBER: _ClassVar[int]
    ScheduledChargingModeDepartBy: ChargeState.ScheduledChargingMode
    ScheduledChargingModeOff: ChargeState.ScheduledChargingMode
    ScheduledChargingModeStartAt: ChargeState.ScheduledChargingMode
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TRIP_CHARGING_FIELD_NUMBER: _ClassVar[int]
    USABLE_BATTERY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    USER_CHARGE_ENABLE_REQUEST_FIELD_NUMBER: _ClassVar[int]
    WORK_LOCATION_FIELD_NUMBER: _ClassVar[int]
    battery_level: int
    battery_range: float
    charge_cable_unlatched: bool
    charge_current_request: int
    charge_current_request_max: int
    charge_enable_request: bool
    charge_energy_added: float
    charge_limit_reason: ChargeState.ChargeLimitReason
    charge_limit_soc: int
    charge_limit_soc_max: int
    charge_limit_soc_min: int
    charge_limit_soc_std: int
    charge_miles_added_ideal: float
    charge_miles_added_rated: float
    charge_port_cold_weather_mode: bool
    charge_port_color: ChargeState.ChargePortColor_E
    charge_port_door_open: bool
    charge_port_latch: _common_pb2.ChargePortLatchState
    charge_rate_mph: int
    charge_rate_mph_float: float
    charger_actual_current: int
    charger_phases: int
    charger_pilot_current: int
    charger_power: int
    charger_voltage: int
    charging_amps: int
    charging_state: ChargeState.ChargingState
    conn_charge_cable: ChargeState.CableType
    est_battery_range: float
    fast_charger_brand: ChargeState.ChargerBrand
    fast_charger_present: bool
    fast_charger_type: ChargeState.ChargerType
    home_location: _common_pb2.LatLong
    ideal_battery_range: float
    managed_charging_active: bool
    managed_charging_start_time: int
    managed_charging_state: ManagedChargingState
    managed_charging_user_canceled: bool
    max_range_charge_counter: int
    minutes_to_charge_limit: int
    minutes_to_full_charge: int
    off_peak_charging_times: _common_pb2.OffPeakChargingTimes
    off_peak_hours_end_time: int
    one_time_soc_limit: int
    outlet_max_timer_minutes: int
    outlet_soc_limit: int
    outlet_state: ChargeState.OutletState
    outlet_time_remaining: int
    power_feed_soc_limit: int
    power_feed_state: ChargeState.PowerFeedState
    power_feed_time_remaining: int
    powershare_feature_allowed: bool
    powershare_feature_enabled: bool
    powershare_instantaneous_load_kw: float
    powershare_request: bool
    powershare_soc_limit: int
    powershare_status: ChargeState.PowershareStatus
    powershare_stop_reason: ChargeState.PowershareStopReason
    powershare_type: ChargeState.PowershareType
    powershare_vehicle_energy_left_hr: int
    preconditioning_enabled: bool
    preconditioning_times: _common_pb2.PreconditioningTimes
    scheduled_charging_mode: ChargeState.ScheduledChargingMode
    scheduled_charging_pending: bool
    scheduled_charging_start_time: int
    scheduled_charging_start_time_app: int
    scheduled_charging_start_time_minutes: int
    scheduled_departure_time: _timestamp_pb2.Timestamp
    scheduled_departure_time_minutes: int
    supercharger_session_trip_planner: bool
    timestamp: _timestamp_pb2.Timestamp
    trip_charging: bool
    usable_battery_level: int
    user_charge_enable_request: bool
    work_location: _common_pb2.LatLong
    def __init__(self, charging_state: _Optional[_Union[ChargeState.ChargingState, _Mapping]] = ..., fast_charger_type: _Optional[_Union[ChargeState.ChargerType, _Mapping]] = ..., fast_charger_brand: _Optional[_Union[ChargeState.ChargerBrand, _Mapping]] = ..., charge_limit_soc: _Optional[int] = ..., charge_limit_soc_std: _Optional[int] = ..., charge_limit_soc_min: _Optional[int] = ..., charge_limit_soc_max: _Optional[int] = ..., max_range_charge_counter: _Optional[int] = ..., fast_charger_present: bool = ..., battery_range: _Optional[float] = ..., est_battery_range: _Optional[float] = ..., ideal_battery_range: _Optional[float] = ..., battery_level: _Optional[int] = ..., usable_battery_level: _Optional[int] = ..., charge_energy_added: _Optional[float] = ..., charge_miles_added_rated: _Optional[float] = ..., charge_miles_added_ideal: _Optional[float] = ..., charger_voltage: _Optional[int] = ..., charger_pilot_current: _Optional[int] = ..., charger_actual_current: _Optional[int] = ..., charger_power: _Optional[int] = ..., minutes_to_full_charge: _Optional[int] = ..., minutes_to_charge_limit: _Optional[int] = ..., trip_charging: bool = ..., charge_rate_mph: _Optional[int] = ..., charge_port_door_open: bool = ..., conn_charge_cable: _Optional[_Union[ChargeState.CableType, _Mapping]] = ..., scheduled_charging_start_time: _Optional[int] = ..., scheduled_charging_pending: bool = ..., scheduled_departure_time: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., user_charge_enable_request: bool = ..., charge_enable_request: bool = ..., charger_phases: _Optional[int] = ..., charge_port_latch: _Optional[_Union[_common_pb2.ChargePortLatchState, _Mapping]] = ..., charge_port_cold_weather_mode: bool = ..., charge_current_request: _Optional[int] = ..., charge_current_request_max: _Optional[int] = ..., managed_charging_active: bool = ..., managed_charging_user_canceled: bool = ..., managed_charging_start_time: _Optional[int] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., preconditioning_times: _Optional[_Union[_common_pb2.PreconditioningTimes, _Mapping]] = ..., off_peak_charging_times: _Optional[_Union[_common_pb2.OffPeakChargingTimes, _Mapping]] = ..., off_peak_hours_end_time: _Optional[int] = ..., scheduled_charging_mode: _Optional[_Union[ChargeState.ScheduledChargingMode, str]] = ..., charging_amps: _Optional[int] = ..., scheduled_charging_start_time_minutes: _Optional[int] = ..., scheduled_departure_time_minutes: _Optional[int] = ..., preconditioning_enabled: bool = ..., scheduled_charging_start_time_app: _Optional[int] = ..., supercharger_session_trip_planner: bool = ..., charge_port_color: _Optional[_Union[ChargeState.ChargePortColor_E, str]] = ..., charge_rate_mph_float: _Optional[float] = ..., charge_limit_reason: _Optional[_Union[ChargeState.ChargeLimitReason, str]] = ..., managed_charging_state: _Optional[_Union[ManagedChargingState, _Mapping]] = ..., charge_cable_unlatched: bool = ..., outlet_state: _Optional[_Union[ChargeState.OutletState, str]] = ..., power_feed_state: _Optional[_Union[ChargeState.PowerFeedState, str]] = ..., outlet_soc_limit: _Optional[int] = ..., power_feed_soc_limit: _Optional[int] = ..., outlet_time_remaining: _Optional[int] = ..., power_feed_time_remaining: _Optional[int] = ..., powershare_feature_allowed: bool = ..., powershare_feature_enabled: bool = ..., powershare_request: bool = ..., powershare_type: _Optional[_Union[ChargeState.PowershareType, str]] = ..., powershare_status: _Optional[_Union[ChargeState.PowershareStatus, str]] = ..., powershare_stop_reason: _Optional[_Union[ChargeState.PowershareStopReason, str]] = ..., powershare_instantaneous_load_kw: _Optional[float] = ..., powershare_vehicle_energy_left_hr: _Optional[int] = ..., powershare_soc_limit: _Optional[int] = ..., one_time_soc_limit: _Optional[int] = ..., home_location: _Optional[_Union[_common_pb2.LatLong, _Mapping]] = ..., work_location: _Optional[_Union[_common_pb2.LatLong, _Mapping]] = ..., outlet_max_timer_minutes: _Optional[int] = ...) -> None: ...

class ClimateState(_message.Message):
    __slots__ = ["allow_cabin_overheat_protection", "auto_seat_climate_left", "auto_seat_climate_right", "auto_steering_wheel_heat", "battery_heater", "battery_heater_no_power", "bioweapon_mode_on", "cabin_overheat_protection", "cabin_overheat_protection_actively_cooling", "climate_keeper_mode", "cop_activation_temperature", "cop_not_running_reason", "defrost_mode", "driver_temp_setting", "fan_status", "hvac_auto_request", "inside_temp_celsius", "is_auto_conditioning_on", "is_climate_on", "is_front_defroster_on", "is_preconditioning", "is_rear_defroster_on", "left_temp_direction", "max_avail_temp_celsius", "min_avail_temp_celsius", "outside_temp_celsius", "passenger_temp_setting", "remote_heater_control_enabled", "right_temp_direction", "seat_fan_front_left", "seat_fan_front_right", "seat_heater_left", "seat_heater_rear_center", "seat_heater_rear_left", "seat_heater_rear_left_back", "seat_heater_rear_right", "seat_heater_rear_right_back", "seat_heater_right", "seat_heater_third_row_left", "seat_heater_third_row_right", "side_mirror_heaters", "steering_wheel_heat_level", "steering_wheel_heater", "supports_fan_only_cabin_overheat_protection", "timestamp", "wiper_blade_heater"]
    class COPNotRunningReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class CabinOverheatProtection_E(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class CopActivationTemp(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class HvacAutoRequest(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class SeatCoolingLevel_E(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class SeatHeaterLevel_E(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class ClimateKeeperMode(_message.Message):
        __slots__ = ["Dog", "Off", "On", "Party", "Unknown"]
        DOG_FIELD_NUMBER: _ClassVar[int]
        Dog: _common_pb2.Void
        OFF_FIELD_NUMBER: _ClassVar[int]
        ON_FIELD_NUMBER: _ClassVar[int]
        Off: _common_pb2.Void
        On: _common_pb2.Void
        PARTY_FIELD_NUMBER: _ClassVar[int]
        Party: _common_pb2.Void
        UNKNOWN_FIELD_NUMBER: _ClassVar[int]
        Unknown: _common_pb2.Void
        def __init__(self, Unknown: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Off: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., On: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Dog: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Party: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    class DefrostMode(_message.Message):
        __slots__ = ["Max", "Normal", "Off"]
        MAX_FIELD_NUMBER: _ClassVar[int]
        Max: _common_pb2.Void
        NORMAL_FIELD_NUMBER: _ClassVar[int]
        Normal: _common_pb2.Void
        OFF_FIELD_NUMBER: _ClassVar[int]
        Off: _common_pb2.Void
        def __init__(self, Off: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Normal: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Max: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    ALLOW_CABIN_OVERHEAT_PROTECTION_FIELD_NUMBER: _ClassVar[int]
    AUTO_SEAT_CLIMATE_LEFT_FIELD_NUMBER: _ClassVar[int]
    AUTO_SEAT_CLIMATE_RIGHT_FIELD_NUMBER: _ClassVar[int]
    AUTO_STEERING_WHEEL_HEAT_FIELD_NUMBER: _ClassVar[int]
    BATTERY_HEATER_FIELD_NUMBER: _ClassVar[int]
    BATTERY_HEATER_NO_POWER_FIELD_NUMBER: _ClassVar[int]
    BIOWEAPON_MODE_ON_FIELD_NUMBER: _ClassVar[int]
    CABIN_OVERHEAT_PROTECTION_ACTIVELY_COOLING_FIELD_NUMBER: _ClassVar[int]
    CABIN_OVERHEAT_PROTECTION_FIELD_NUMBER: _ClassVar[int]
    CLIMATE_KEEPER_MODE_FIELD_NUMBER: _ClassVar[int]
    COPNotRunningReasonCabinBelowThreshold: ClimateState.COPNotRunningReason
    COPNotRunningReasonEnergyConsumptionReached: ClimateState.COPNotRunningReason
    COPNotRunningReasonFault: ClimateState.COPNotRunningReason
    COPNotRunningReasonLowSolarLoad: ClimateState.COPNotRunningReason
    COPNotRunningReasonNoReason: ClimateState.COPNotRunningReason
    COPNotRunningReasonTimeout: ClimateState.COPNotRunningReason
    COPNotRunningReasonUserInteraction: ClimateState.COPNotRunningReason
    COP_ACTIVATION_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    COP_NOT_RUNNING_REASON_FIELD_NUMBER: _ClassVar[int]
    CabinOverheatProtectionFanOnly: ClimateState.CabinOverheatProtection_E
    CabinOverheatProtectionOff: ClimateState.CabinOverheatProtection_E
    CabinOverheatProtectionOn: ClimateState.CabinOverheatProtection_E
    CopActivationTempHigh: ClimateState.CopActivationTemp
    CopActivationTempLow: ClimateState.CopActivationTemp
    CopActivationTempMedium: ClimateState.CopActivationTemp
    CopActivationTempUnspecified: ClimateState.CopActivationTemp
    DEFROST_MODE_FIELD_NUMBER: _ClassVar[int]
    DRIVER_TEMP_SETTING_FIELD_NUMBER: _ClassVar[int]
    FAN_STATUS_FIELD_NUMBER: _ClassVar[int]
    HVAC_AUTO_REQUEST_FIELD_NUMBER: _ClassVar[int]
    HvacAutoRequestOn: ClimateState.HvacAutoRequest
    HvacAutoRequestOverride: ClimateState.HvacAutoRequest
    INSIDE_TEMP_CELSIUS_FIELD_NUMBER: _ClassVar[int]
    IS_AUTO_CONDITIONING_ON_FIELD_NUMBER: _ClassVar[int]
    IS_CLIMATE_ON_FIELD_NUMBER: _ClassVar[int]
    IS_FRONT_DEFROSTER_ON_FIELD_NUMBER: _ClassVar[int]
    IS_PRECONDITIONING_FIELD_NUMBER: _ClassVar[int]
    IS_REAR_DEFROSTER_ON_FIELD_NUMBER: _ClassVar[int]
    LEFT_TEMP_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    MAX_AVAIL_TEMP_CELSIUS_FIELD_NUMBER: _ClassVar[int]
    MIN_AVAIL_TEMP_CELSIUS_FIELD_NUMBER: _ClassVar[int]
    OUTSIDE_TEMP_CELSIUS_FIELD_NUMBER: _ClassVar[int]
    PASSENGER_TEMP_SETTING_FIELD_NUMBER: _ClassVar[int]
    REMOTE_HEATER_CONTROL_ENABLED_FIELD_NUMBER: _ClassVar[int]
    RIGHT_TEMP_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SEAT_FAN_FRONT_LEFT_FIELD_NUMBER: _ClassVar[int]
    SEAT_FAN_FRONT_RIGHT_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_LEFT_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_REAR_CENTER_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_REAR_LEFT_BACK_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_REAR_LEFT_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_REAR_RIGHT_BACK_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_REAR_RIGHT_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_RIGHT_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_THIRD_ROW_LEFT_FIELD_NUMBER: _ClassVar[int]
    SEAT_HEATER_THIRD_ROW_RIGHT_FIELD_NUMBER: _ClassVar[int]
    SIDE_MIRROR_HEATERS_FIELD_NUMBER: _ClassVar[int]
    STEERING_WHEEL_HEATER_FIELD_NUMBER: _ClassVar[int]
    STEERING_WHEEL_HEAT_LEVEL_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_FAN_ONLY_CABIN_OVERHEAT_PROTECTION_FIELD_NUMBER: _ClassVar[int]
    SeatCoolingLevelHigh: ClimateState.SeatCoolingLevel_E
    SeatCoolingLevelLow: ClimateState.SeatCoolingLevel_E
    SeatCoolingLevelMed: ClimateState.SeatCoolingLevel_E
    SeatCoolingLevelOff: ClimateState.SeatCoolingLevel_E
    SeatHeaterLevelHigh: ClimateState.SeatHeaterLevel_E
    SeatHeaterLevelLow: ClimateState.SeatHeaterLevel_E
    SeatHeaterLevelMed: ClimateState.SeatHeaterLevel_E
    SeatHeaterLevelOff: ClimateState.SeatHeaterLevel_E
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    WIPER_BLADE_HEATER_FIELD_NUMBER: _ClassVar[int]
    allow_cabin_overheat_protection: bool
    auto_seat_climate_left: bool
    auto_seat_climate_right: bool
    auto_steering_wheel_heat: bool
    battery_heater: bool
    battery_heater_no_power: bool
    bioweapon_mode_on: bool
    cabin_overheat_protection: ClimateState.CabinOverheatProtection_E
    cabin_overheat_protection_actively_cooling: bool
    climate_keeper_mode: ClimateState.ClimateKeeperMode
    cop_activation_temperature: ClimateState.CopActivationTemp
    cop_not_running_reason: ClimateState.COPNotRunningReason
    defrost_mode: ClimateState.DefrostMode
    driver_temp_setting: float
    fan_status: int
    hvac_auto_request: ClimateState.HvacAutoRequest
    inside_temp_celsius: float
    is_auto_conditioning_on: bool
    is_climate_on: bool
    is_front_defroster_on: bool
    is_preconditioning: bool
    is_rear_defroster_on: bool
    left_temp_direction: int
    max_avail_temp_celsius: float
    min_avail_temp_celsius: float
    outside_temp_celsius: float
    passenger_temp_setting: float
    remote_heater_control_enabled: bool
    right_temp_direction: int
    seat_fan_front_left: int
    seat_fan_front_right: int
    seat_heater_left: int
    seat_heater_rear_center: int
    seat_heater_rear_left: int
    seat_heater_rear_left_back: int
    seat_heater_rear_right: int
    seat_heater_rear_right_back: int
    seat_heater_right: int
    seat_heater_third_row_left: int
    seat_heater_third_row_right: int
    side_mirror_heaters: bool
    steering_wheel_heat_level: _common_pb2.StwHeatLevel
    steering_wheel_heater: bool
    supports_fan_only_cabin_overheat_protection: bool
    timestamp: _timestamp_pb2.Timestamp
    wiper_blade_heater: bool
    def __init__(self, inside_temp_celsius: _Optional[float] = ..., outside_temp_celsius: _Optional[float] = ..., driver_temp_setting: _Optional[float] = ..., passenger_temp_setting: _Optional[float] = ..., left_temp_direction: _Optional[int] = ..., right_temp_direction: _Optional[int] = ..., is_front_defroster_on: bool = ..., is_rear_defroster_on: bool = ..., fan_status: _Optional[int] = ..., is_climate_on: bool = ..., min_avail_temp_celsius: _Optional[float] = ..., max_avail_temp_celsius: _Optional[float] = ..., seat_heater_left: _Optional[int] = ..., seat_heater_right: _Optional[int] = ..., seat_heater_rear_left: _Optional[int] = ..., seat_heater_rear_right: _Optional[int] = ..., seat_heater_rear_center: _Optional[int] = ..., seat_heater_rear_right_back: _Optional[int] = ..., seat_heater_rear_left_back: _Optional[int] = ..., seat_heater_third_row_right: _Optional[int] = ..., seat_heater_third_row_left: _Optional[int] = ..., battery_heater: bool = ..., battery_heater_no_power: bool = ..., steering_wheel_heater: bool = ..., wiper_blade_heater: bool = ..., side_mirror_heaters: bool = ..., is_preconditioning: bool = ..., remote_heater_control_enabled: bool = ..., climate_keeper_mode: _Optional[_Union[ClimateState.ClimateKeeperMode, _Mapping]] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., bioweapon_mode_on: bool = ..., defrost_mode: _Optional[_Union[ClimateState.DefrostMode, _Mapping]] = ..., is_auto_conditioning_on: bool = ..., auto_seat_climate_left: bool = ..., auto_seat_climate_right: bool = ..., seat_fan_front_left: _Optional[int] = ..., seat_fan_front_right: _Optional[int] = ..., allow_cabin_overheat_protection: bool = ..., supports_fan_only_cabin_overheat_protection: bool = ..., cabin_overheat_protection: _Optional[_Union[ClimateState.CabinOverheatProtection_E, str]] = ..., cabin_overheat_protection_actively_cooling: bool = ..., cop_activation_temperature: _Optional[_Union[ClimateState.CopActivationTemp, str]] = ..., auto_steering_wheel_heat: bool = ..., steering_wheel_heat_level: _Optional[_Union[_common_pb2.StwHeatLevel, str]] = ..., hvac_auto_request: _Optional[_Union[ClimateState.HvacAutoRequest, str]] = ..., cop_not_running_reason: _Optional[_Union[ClimateState.COPNotRunningReason, str]] = ...) -> None: ...

class ClosuresState(_message.Message):
    __slots__ = ["center_display_state", "door_open_driver_front", "door_open_driver_rear", "door_open_passenger_front", "door_open_passenger_rear", "door_open_trunk_front", "door_open_trunk_rear", "is_user_present", "locked", "remote_start", "sentry_mode_available", "sentry_mode_state", "speed_limit_mode", "sun_roof_percent_open", "sun_roof_state", "timestamp", "tonneau_in_motion", "tonneau_percent_open", "tonneau_state", "valet_mode", "valet_pin_needed", "window_open_driver_front", "window_open_driver_rear", "window_open_passenger_front", "window_open_passenger_rear"]
    class DisplayState(_message.Message):
        __slots__ = ["Accessory", "Charging", "Dim", "Dog", "Driving", "Entertainment", "Lock", "Off", "On", "Sentry"]
        ACCESSORY_FIELD_NUMBER: _ClassVar[int]
        Accessory: _common_pb2.Void
        CHARGING_FIELD_NUMBER: _ClassVar[int]
        Charging: _common_pb2.Void
        DIM_FIELD_NUMBER: _ClassVar[int]
        DOG_FIELD_NUMBER: _ClassVar[int]
        DRIVING_FIELD_NUMBER: _ClassVar[int]
        Dim: _common_pb2.Void
        Dog: _common_pb2.Void
        Driving: _common_pb2.Void
        ENTERTAINMENT_FIELD_NUMBER: _ClassVar[int]
        Entertainment: _common_pb2.Void
        LOCK_FIELD_NUMBER: _ClassVar[int]
        Lock: _common_pb2.Void
        OFF_FIELD_NUMBER: _ClassVar[int]
        ON_FIELD_NUMBER: _ClassVar[int]
        Off: _common_pb2.Void
        On: _common_pb2.Void
        SENTRY_FIELD_NUMBER: _ClassVar[int]
        Sentry: _common_pb2.Void
        def __init__(self, Off: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Dim: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Accessory: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., On: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Driving: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Charging: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Lock: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Sentry: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Dog: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Entertainment: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    class SentryModeState(_message.Message):
        __slots__ = ["Armed", "Aware", "Idle", "Off", "Panic", "Quiet"]
        ARMED_FIELD_NUMBER: _ClassVar[int]
        AWARE_FIELD_NUMBER: _ClassVar[int]
        Armed: _common_pb2.Void
        Aware: _common_pb2.Void
        IDLE_FIELD_NUMBER: _ClassVar[int]
        Idle: _common_pb2.Void
        OFF_FIELD_NUMBER: _ClassVar[int]
        Off: _common_pb2.Void
        PANIC_FIELD_NUMBER: _ClassVar[int]
        Panic: _common_pb2.Void
        QUIET_FIELD_NUMBER: _ClassVar[int]
        Quiet: _common_pb2.Void
        def __init__(self, Off: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Idle: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Armed: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Aware: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Panic: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Quiet: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    class SunRoofState(_message.Message):
        __slots__ = ["Calibrating", "Closed", "Moving", "Open", "Unknown", "Vent"]
        CALIBRATING_FIELD_NUMBER: _ClassVar[int]
        CLOSED_FIELD_NUMBER: _ClassVar[int]
        Calibrating: _common_pb2.Void
        Closed: _common_pb2.Void
        MOVING_FIELD_NUMBER: _ClassVar[int]
        Moving: _common_pb2.Void
        OPEN_FIELD_NUMBER: _ClassVar[int]
        Open: _common_pb2.Void
        UNKNOWN_FIELD_NUMBER: _ClassVar[int]
        Unknown: _common_pb2.Void
        VENT_FIELD_NUMBER: _ClassVar[int]
        Vent: _common_pb2.Void
        def __init__(self, Unknown: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Calibrating: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Closed: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Open: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Moving: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Vent: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    CENTER_DISPLAY_STATE_FIELD_NUMBER: _ClassVar[int]
    DOOR_OPEN_DRIVER_FRONT_FIELD_NUMBER: _ClassVar[int]
    DOOR_OPEN_DRIVER_REAR_FIELD_NUMBER: _ClassVar[int]
    DOOR_OPEN_PASSENGER_FRONT_FIELD_NUMBER: _ClassVar[int]
    DOOR_OPEN_PASSENGER_REAR_FIELD_NUMBER: _ClassVar[int]
    DOOR_OPEN_TRUNK_FRONT_FIELD_NUMBER: _ClassVar[int]
    DOOR_OPEN_TRUNK_REAR_FIELD_NUMBER: _ClassVar[int]
    IS_USER_PRESENT_FIELD_NUMBER: _ClassVar[int]
    LOCKED_FIELD_NUMBER: _ClassVar[int]
    REMOTE_START_FIELD_NUMBER: _ClassVar[int]
    SENTRY_MODE_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    SENTRY_MODE_STATE_FIELD_NUMBER: _ClassVar[int]
    SPEED_LIMIT_MODE_FIELD_NUMBER: _ClassVar[int]
    SUN_ROOF_PERCENT_OPEN_FIELD_NUMBER: _ClassVar[int]
    SUN_ROOF_STATE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TONNEAU_IN_MOTION_FIELD_NUMBER: _ClassVar[int]
    TONNEAU_PERCENT_OPEN_FIELD_NUMBER: _ClassVar[int]
    TONNEAU_STATE_FIELD_NUMBER: _ClassVar[int]
    VALET_MODE_FIELD_NUMBER: _ClassVar[int]
    VALET_PIN_NEEDED_FIELD_NUMBER: _ClassVar[int]
    WINDOW_OPEN_DRIVER_FRONT_FIELD_NUMBER: _ClassVar[int]
    WINDOW_OPEN_DRIVER_REAR_FIELD_NUMBER: _ClassVar[int]
    WINDOW_OPEN_PASSENGER_FRONT_FIELD_NUMBER: _ClassVar[int]
    WINDOW_OPEN_PASSENGER_REAR_FIELD_NUMBER: _ClassVar[int]
    center_display_state: ClosuresState.DisplayState
    door_open_driver_front: bool
    door_open_driver_rear: bool
    door_open_passenger_front: bool
    door_open_passenger_rear: bool
    door_open_trunk_front: bool
    door_open_trunk_rear: bool
    is_user_present: bool
    locked: bool
    remote_start: bool
    sentry_mode_available: bool
    sentry_mode_state: ClosuresState.SentryModeState
    speed_limit_mode: SpeedLimitMode
    sun_roof_percent_open: int
    sun_roof_state: ClosuresState.SunRoofState
    timestamp: _timestamp_pb2.Timestamp
    tonneau_in_motion: bool
    tonneau_percent_open: int
    tonneau_state: _vcsec_pb2.ClosureState_E
    valet_mode: bool
    valet_pin_needed: bool
    window_open_driver_front: bool
    window_open_driver_rear: bool
    window_open_passenger_front: bool
    window_open_passenger_rear: bool
    def __init__(self, door_open_driver_front: bool = ..., door_open_driver_rear: bool = ..., door_open_passenger_front: bool = ..., door_open_passenger_rear: bool = ..., door_open_trunk_front: bool = ..., door_open_trunk_rear: bool = ..., window_open_driver_front: bool = ..., window_open_passenger_front: bool = ..., window_open_driver_rear: bool = ..., window_open_passenger_rear: bool = ..., sun_roof_state: _Optional[_Union[ClosuresState.SunRoofState, _Mapping]] = ..., sun_roof_percent_open: _Optional[int] = ..., locked: bool = ..., is_user_present: bool = ..., center_display_state: _Optional[_Union[ClosuresState.DisplayState, _Mapping]] = ..., remote_start: bool = ..., valet_mode: bool = ..., valet_pin_needed: bool = ..., sentry_mode_state: _Optional[_Union[ClosuresState.SentryModeState, _Mapping]] = ..., sentry_mode_available: bool = ..., speed_limit_mode: _Optional[_Union[SpeedLimitMode, _Mapping]] = ..., tonneau_state: _Optional[_Union[_vcsec_pb2.ClosureState_E, str]] = ..., tonneau_percent_open: _Optional[int] = ..., tonneau_in_motion: bool = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class DriveState(_message.Message):
    __slots__ = ["active_route_coordinates", "active_route_destination", "active_route_energy_at_arrival", "active_route_miles_to_arrival", "active_route_minutes_to_arrival", "active_route_traffic_minutes_delay", "last_route_update", "last_traffic_update", "odometer_in_hundredths_of_a_mile", "power", "shift_state", "speed", "speed_float", "timestamp"]
    ACTIVE_ROUTE_COORDINATES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ROUTE_DESTINATION_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ROUTE_ENERGY_AT_ARRIVAL_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ROUTE_MILES_TO_ARRIVAL_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ROUTE_MINUTES_TO_ARRIVAL_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_ROUTE_TRAFFIC_MINUTES_DELAY_FIELD_NUMBER: _ClassVar[int]
    LAST_ROUTE_UPDATE_FIELD_NUMBER: _ClassVar[int]
    LAST_TRAFFIC_UPDATE_FIELD_NUMBER: _ClassVar[int]
    ODOMETER_IN_HUNDREDTHS_OF_A_MILE_FIELD_NUMBER: _ClassVar[int]
    POWER_FIELD_NUMBER: _ClassVar[int]
    SHIFT_STATE_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    SPEED_FLOAT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    active_route_coordinates: _common_pb2.LatLong
    active_route_destination: str
    active_route_energy_at_arrival: float
    active_route_miles_to_arrival: float
    active_route_minutes_to_arrival: float
    active_route_traffic_minutes_delay: float
    last_route_update: int
    last_traffic_update: _timestamp_pb2.Timestamp
    odometer_in_hundredths_of_a_mile: int
    power: int
    shift_state: ShiftState
    speed: int
    speed_float: float
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, shift_state: _Optional[_Union[ShiftState, _Mapping]] = ..., speed: _Optional[int] = ..., power: _Optional[int] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., odometer_in_hundredths_of_a_mile: _Optional[int] = ..., speed_float: _Optional[float] = ..., active_route_destination: _Optional[str] = ..., active_route_minutes_to_arrival: _Optional[float] = ..., active_route_miles_to_arrival: _Optional[float] = ..., active_route_traffic_minutes_delay: _Optional[float] = ..., active_route_energy_at_arrival: _Optional[float] = ..., last_route_update: _Optional[int] = ..., last_traffic_update: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., active_route_coordinates: _Optional[_Union[_common_pb2.LatLong, _Mapping]] = ...) -> None: ...

class LocationState(_message.Message):
    __slots__ = ["corrected_latitude", "corrected_longitude", "estimated_gps_valid", "estimated_to_raw_distance", "geo_accuracy", "geo_elevation", "geo_heading", "geo_latitude", "geo_longitude", "gps_as_of", "heading", "homelink_nearby", "latitude", "location_name", "longitude", "native_latitude", "native_location_supported", "native_longitude", "native_type", "timestamp"]
    class GPSCoordinateType(_message.Message):
        __slots__ = ["GCJ", "WGS"]
        GCJ: _common_pb2.Void
        GCJ_FIELD_NUMBER: _ClassVar[int]
        WGS: _common_pb2.Void
        WGS_FIELD_NUMBER: _ClassVar[int]
        def __init__(self, GCJ: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., WGS: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    CORRECTED_LATITUDE_FIELD_NUMBER: _ClassVar[int]
    CORRECTED_LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_GPS_VALID_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_TO_RAW_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    GEO_ACCURACY_FIELD_NUMBER: _ClassVar[int]
    GEO_ELEVATION_FIELD_NUMBER: _ClassVar[int]
    GEO_HEADING_FIELD_NUMBER: _ClassVar[int]
    GEO_LATITUDE_FIELD_NUMBER: _ClassVar[int]
    GEO_LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    GPS_AS_OF_FIELD_NUMBER: _ClassVar[int]
    HEADING_FIELD_NUMBER: _ClassVar[int]
    HOMELINK_NEARBY_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LOCATION_NAME_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    NATIVE_LATITUDE_FIELD_NUMBER: _ClassVar[int]
    NATIVE_LOCATION_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    NATIVE_LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    NATIVE_TYPE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    corrected_latitude: float
    corrected_longitude: float
    estimated_gps_valid: bool
    estimated_to_raw_distance: float
    geo_accuracy: float
    geo_elevation: float
    geo_heading: float
    geo_latitude: float
    geo_longitude: float
    gps_as_of: int
    heading: int
    homelink_nearby: bool
    latitude: float
    location_name: str
    longitude: float
    native_latitude: float
    native_location_supported: bool
    native_longitude: float
    native_type: LocationState.GPSCoordinateType
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ..., heading: _Optional[int] = ..., gps_as_of: _Optional[int] = ..., native_location_supported: bool = ..., native_latitude: _Optional[float] = ..., native_longitude: _Optional[float] = ..., native_type: _Optional[_Union[LocationState.GPSCoordinateType, _Mapping]] = ..., corrected_latitude: _Optional[float] = ..., corrected_longitude: _Optional[float] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., homelink_nearby: bool = ..., location_name: _Optional[str] = ..., geo_latitude: _Optional[float] = ..., geo_longitude: _Optional[float] = ..., geo_heading: _Optional[float] = ..., geo_elevation: _Optional[float] = ..., geo_accuracy: _Optional[float] = ..., estimated_gps_valid: bool = ..., estimated_to_raw_distance: _Optional[float] = ...) -> None: ...

class ManagedChargingState(_message.Message):
    __slots__ = ["charge_on_solar_gateway_din", "charge_on_solar_state", "minutes_to_lower_limit", "tesla_electric_asset_id"]
    CHARGE_ON_SOLAR_GATEWAY_DIN_FIELD_NUMBER: _ClassVar[int]
    CHARGE_ON_SOLAR_STATE_FIELD_NUMBER: _ClassVar[int]
    MINUTES_TO_LOWER_LIMIT_FIELD_NUMBER: _ClassVar[int]
    TESLA_ELECTRIC_ASSET_ID_FIELD_NUMBER: _ClassVar[int]
    charge_on_solar_gateway_din: str
    charge_on_solar_state: ChargeOnSolarState
    minutes_to_lower_limit: int
    tesla_electric_asset_id: str
    def __init__(self, charge_on_solar_state: _Optional[_Union[ChargeOnSolarState, _Mapping]] = ..., charge_on_solar_gateway_din: _Optional[str] = ..., tesla_electric_asset_id: _Optional[str] = ..., minutes_to_lower_limit: _Optional[int] = ...) -> None: ...

class MediaDetailState(_message.Message):
    __slots__ = ["a2dp_source_name", "now_playing_album", "now_playing_duration", "now_playing_elapsed", "now_playing_source_string", "now_playing_station", "timestamp"]
    A2DP_SOURCE_NAME_FIELD_NUMBER: _ClassVar[int]
    NOW_PLAYING_ALBUM_FIELD_NUMBER: _ClassVar[int]
    NOW_PLAYING_DURATION_FIELD_NUMBER: _ClassVar[int]
    NOW_PLAYING_ELAPSED_FIELD_NUMBER: _ClassVar[int]
    NOW_PLAYING_SOURCE_STRING_FIELD_NUMBER: _ClassVar[int]
    NOW_PLAYING_STATION_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    a2dp_source_name: str
    now_playing_album: str
    now_playing_duration: int
    now_playing_elapsed: int
    now_playing_source_string: str
    now_playing_station: str
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., now_playing_duration: _Optional[int] = ..., now_playing_elapsed: _Optional[int] = ..., now_playing_source_string: _Optional[str] = ..., now_playing_album: _Optional[str] = ..., now_playing_station: _Optional[str] = ..., a2dp_source_name: _Optional[str] = ...) -> None: ...

class MediaState(_message.Message):
    __slots__ = ["audio_volume", "audio_volume_increment", "audio_volume_max", "media_playback_status", "now_playing_artist", "now_playing_source", "now_playing_title", "remote_control_enabled", "timestamp"]
    AUDIO_VOLUME_FIELD_NUMBER: _ClassVar[int]
    AUDIO_VOLUME_INCREMENT_FIELD_NUMBER: _ClassVar[int]
    AUDIO_VOLUME_MAX_FIELD_NUMBER: _ClassVar[int]
    MEDIA_PLAYBACK_STATUS_FIELD_NUMBER: _ClassVar[int]
    NOW_PLAYING_ARTIST_FIELD_NUMBER: _ClassVar[int]
    NOW_PLAYING_SOURCE_FIELD_NUMBER: _ClassVar[int]
    NOW_PLAYING_TITLE_FIELD_NUMBER: _ClassVar[int]
    REMOTE_CONTROL_ENABLED_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    audio_volume: float
    audio_volume_increment: float
    audio_volume_max: float
    media_playback_status: _common_pb2.MediaPlaybackStatus
    now_playing_artist: str
    now_playing_source: MediaSourceType
    now_playing_title: str
    remote_control_enabled: bool
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., remote_control_enabled: bool = ..., now_playing_artist: _Optional[str] = ..., now_playing_title: _Optional[str] = ..., audio_volume: _Optional[float] = ..., audio_volume_increment: _Optional[float] = ..., audio_volume_max: _Optional[float] = ..., now_playing_source: _Optional[_Union[MediaSourceType, str]] = ..., media_playback_status: _Optional[_Union[_common_pb2.MediaPlaybackStatus, str]] = ...) -> None: ...

class ParentalControlsSettings(_message.Message):
    __slots__ = ["chill_acceleration_enabled", "curfew_enabled", "curfew_end_time", "curfew_start_time", "current_limit_mph", "max_limit_mph", "min_limit_mph", "require_safety_settings_enabled", "speed_limit_enabled"]
    CHILL_ACCELERATION_ENABLED_FIELD_NUMBER: _ClassVar[int]
    CURFEW_ENABLED_FIELD_NUMBER: _ClassVar[int]
    CURFEW_END_TIME_FIELD_NUMBER: _ClassVar[int]
    CURFEW_START_TIME_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_MPH_FIELD_NUMBER: _ClassVar[int]
    MAX_LIMIT_MPH_FIELD_NUMBER: _ClassVar[int]
    MIN_LIMIT_MPH_FIELD_NUMBER: _ClassVar[int]
    REQUIRE_SAFETY_SETTINGS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    SPEED_LIMIT_ENABLED_FIELD_NUMBER: _ClassVar[int]
    chill_acceleration_enabled: bool
    curfew_enabled: bool
    curfew_end_time: int
    curfew_start_time: int
    current_limit_mph: float
    max_limit_mph: float
    min_limit_mph: float
    require_safety_settings_enabled: bool
    speed_limit_enabled: bool
    def __init__(self, speed_limit_enabled: bool = ..., max_limit_mph: _Optional[float] = ..., min_limit_mph: _Optional[float] = ..., current_limit_mph: _Optional[float] = ..., chill_acceleration_enabled: bool = ..., require_safety_settings_enabled: bool = ..., curfew_enabled: bool = ..., curfew_start_time: _Optional[int] = ..., curfew_end_time: _Optional[int] = ...) -> None: ...

class ParentalControlsState(_message.Message):
    __slots__ = ["parental_controls_active", "parental_controls_pin_set", "parental_controls_settings", "timestamp"]
    PARENTAL_CONTROLS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    PARENTAL_CONTROLS_PIN_SET_FIELD_NUMBER: _ClassVar[int]
    PARENTAL_CONTROLS_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    parental_controls_active: bool
    parental_controls_pin_set: bool
    parental_controls_settings: ParentalControlsSettings
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., parental_controls_active: bool = ..., parental_controls_pin_set: bool = ..., parental_controls_settings: _Optional[_Union[ParentalControlsSettings, _Mapping]] = ...) -> None: ...

class PreconditioningScheduleState(_message.Message):
    __slots__ = ["max_num_precondition_schedules", "next_schedule", "precondition_schedules", "preconditioning_schedule_window", "timestamp"]
    MAX_NUM_PRECONDITION_SCHEDULES_FIELD_NUMBER: _ClassVar[int]
    NEXT_SCHEDULE_FIELD_NUMBER: _ClassVar[int]
    PRECONDITIONING_SCHEDULE_WINDOW_FIELD_NUMBER: _ClassVar[int]
    PRECONDITION_SCHEDULES_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    max_num_precondition_schedules: int
    next_schedule: bool
    precondition_schedules: _containers.RepeatedCompositeFieldContainer[_common_pb2.PreconditionSchedule]
    preconditioning_schedule_window: _common_pb2.PreconditionSchedule
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, precondition_schedules: _Optional[_Iterable[_Union[_common_pb2.PreconditionSchedule, _Mapping]]] = ..., preconditioning_schedule_window: _Optional[_Union[_common_pb2.PreconditionSchedule, _Mapping]] = ..., max_num_precondition_schedules: _Optional[int] = ..., next_schedule: bool = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ShiftState(_message.Message):
    __slots__ = ["D", "Invalid", "N", "P", "R", "SNA"]
    D: _common_pb2.Void
    D_FIELD_NUMBER: _ClassVar[int]
    INVALID_FIELD_NUMBER: _ClassVar[int]
    Invalid: _common_pb2.Void
    N: _common_pb2.Void
    N_FIELD_NUMBER: _ClassVar[int]
    P: _common_pb2.Void
    P_FIELD_NUMBER: _ClassVar[int]
    R: _common_pb2.Void
    R_FIELD_NUMBER: _ClassVar[int]
    SNA: _common_pb2.Void
    SNA_FIELD_NUMBER: _ClassVar[int]
    def __init__(self, Invalid: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., P: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., R: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., N: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., D: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., SNA: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...

class SoftwareUpdateState(_message.Message):
    __slots__ = ["download_perc", "expected_duration_sec", "install_perc", "scheduled_time_ms", "status", "timestamp", "version", "warning_time_remaining_ms"]
    class SoftwareUpdateStatus(_message.Message):
        __slots__ = ["Available", "Downloading", "DownloadingWifiWait", "Installing", "Scheduled", "Unknown"]
        AVAILABLE_FIELD_NUMBER: _ClassVar[int]
        Available: _common_pb2.Void
        DOWNLOADINGWIFIWAIT_FIELD_NUMBER: _ClassVar[int]
        DOWNLOADING_FIELD_NUMBER: _ClassVar[int]
        Downloading: _common_pb2.Void
        DownloadingWifiWait: _common_pb2.Void
        INSTALLING_FIELD_NUMBER: _ClassVar[int]
        Installing: _common_pb2.Void
        SCHEDULED_FIELD_NUMBER: _ClassVar[int]
        Scheduled: _common_pb2.Void
        UNKNOWN_FIELD_NUMBER: _ClassVar[int]
        Unknown: _common_pb2.Void
        def __init__(self, Unknown: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Installing: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Scheduled: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Available: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., DownloadingWifiWait: _Optional[_Union[_common_pb2.Void, _Mapping]] = ..., Downloading: _Optional[_Union[_common_pb2.Void, _Mapping]] = ...) -> None: ...
    DOWNLOAD_PERC_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_DURATION_SEC_FIELD_NUMBER: _ClassVar[int]
    INSTALL_PERC_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    WARNING_TIME_REMAINING_MS_FIELD_NUMBER: _ClassVar[int]
    download_perc: int
    expected_duration_sec: int
    install_perc: int
    scheduled_time_ms: int
    status: SoftwareUpdateState.SoftwareUpdateStatus
    timestamp: _timestamp_pb2.Timestamp
    version: str
    warning_time_remaining_ms: int
    def __init__(self, status: _Optional[_Union[SoftwareUpdateState.SoftwareUpdateStatus, _Mapping]] = ..., scheduled_time_ms: _Optional[int] = ..., warning_time_remaining_ms: _Optional[int] = ..., expected_duration_sec: _Optional[int] = ..., download_perc: _Optional[int] = ..., install_perc: _Optional[int] = ..., version: _Optional[str] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class SpeedLimitMode(_message.Message):
    __slots__ = ["active", "current_limit_mph", "max_limit_mph", "min_limit_mph", "pin_code_set"]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_LIMIT_MPH_FIELD_NUMBER: _ClassVar[int]
    MAX_LIMIT_MPH_FIELD_NUMBER: _ClassVar[int]
    MIN_LIMIT_MPH_FIELD_NUMBER: _ClassVar[int]
    PIN_CODE_SET_FIELD_NUMBER: _ClassVar[int]
    active: bool
    current_limit_mph: float
    max_limit_mph: float
    min_limit_mph: float
    pin_code_set: bool
    def __init__(self, active: bool = ..., pin_code_set: bool = ..., max_limit_mph: _Optional[float] = ..., min_limit_mph: _Optional[float] = ..., current_limit_mph: _Optional[float] = ...) -> None: ...

class TirePressureState(_message.Message):
    __slots__ = ["timestamp", "tpms_hard_warning_fl", "tpms_hard_warning_fr", "tpms_hard_warning_rl", "tpms_hard_warning_rr", "tpms_last_seen_pressure_time_fl", "tpms_last_seen_pressure_time_fr", "tpms_last_seen_pressure_time_rl", "tpms_last_seen_pressure_time_rr", "tpms_pressure_fl", "tpms_pressure_fr", "tpms_pressure_rl", "tpms_pressure_rr", "tpms_rcp_front_value", "tpms_rcp_rear_value", "tpms_soft_warning_fl", "tpms_soft_warning_fr", "tpms_soft_warning_rl", "tpms_soft_warning_rr"]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TPMS_HARD_WARNING_FL_FIELD_NUMBER: _ClassVar[int]
    TPMS_HARD_WARNING_FR_FIELD_NUMBER: _ClassVar[int]
    TPMS_HARD_WARNING_RL_FIELD_NUMBER: _ClassVar[int]
    TPMS_HARD_WARNING_RR_FIELD_NUMBER: _ClassVar[int]
    TPMS_LAST_SEEN_PRESSURE_TIME_FL_FIELD_NUMBER: _ClassVar[int]
    TPMS_LAST_SEEN_PRESSURE_TIME_FR_FIELD_NUMBER: _ClassVar[int]
    TPMS_LAST_SEEN_PRESSURE_TIME_RL_FIELD_NUMBER: _ClassVar[int]
    TPMS_LAST_SEEN_PRESSURE_TIME_RR_FIELD_NUMBER: _ClassVar[int]
    TPMS_PRESSURE_FL_FIELD_NUMBER: _ClassVar[int]
    TPMS_PRESSURE_FR_FIELD_NUMBER: _ClassVar[int]
    TPMS_PRESSURE_RL_FIELD_NUMBER: _ClassVar[int]
    TPMS_PRESSURE_RR_FIELD_NUMBER: _ClassVar[int]
    TPMS_RCP_FRONT_VALUE_FIELD_NUMBER: _ClassVar[int]
    TPMS_RCP_REAR_VALUE_FIELD_NUMBER: _ClassVar[int]
    TPMS_SOFT_WARNING_FL_FIELD_NUMBER: _ClassVar[int]
    TPMS_SOFT_WARNING_FR_FIELD_NUMBER: _ClassVar[int]
    TPMS_SOFT_WARNING_RL_FIELD_NUMBER: _ClassVar[int]
    TPMS_SOFT_WARNING_RR_FIELD_NUMBER: _ClassVar[int]
    timestamp: _timestamp_pb2.Timestamp
    tpms_hard_warning_fl: bool
    tpms_hard_warning_fr: bool
    tpms_hard_warning_rl: bool
    tpms_hard_warning_rr: bool
    tpms_last_seen_pressure_time_fl: _timestamp_pb2.Timestamp
    tpms_last_seen_pressure_time_fr: _timestamp_pb2.Timestamp
    tpms_last_seen_pressure_time_rl: _timestamp_pb2.Timestamp
    tpms_last_seen_pressure_time_rr: _timestamp_pb2.Timestamp
    tpms_pressure_fl: float
    tpms_pressure_fr: float
    tpms_pressure_rl: float
    tpms_pressure_rr: float
    tpms_rcp_front_value: float
    tpms_rcp_rear_value: float
    tpms_soft_warning_fl: bool
    tpms_soft_warning_fr: bool
    tpms_soft_warning_rl: bool
    tpms_soft_warning_rr: bool
    def __init__(self, timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., tpms_pressure_fl: _Optional[float] = ..., tpms_pressure_fr: _Optional[float] = ..., tpms_pressure_rl: _Optional[float] = ..., tpms_pressure_rr: _Optional[float] = ..., tpms_last_seen_pressure_time_fl: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., tpms_last_seen_pressure_time_fr: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., tpms_last_seen_pressure_time_rl: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., tpms_last_seen_pressure_time_rr: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., tpms_hard_warning_fl: bool = ..., tpms_hard_warning_fr: bool = ..., tpms_hard_warning_rl: bool = ..., tpms_hard_warning_rr: bool = ..., tpms_soft_warning_fl: bool = ..., tpms_soft_warning_fr: bool = ..., tpms_soft_warning_rl: bool = ..., tpms_soft_warning_rr: bool = ..., tpms_rcp_front_value: _Optional[float] = ..., tpms_rcp_rear_value: _Optional[float] = ...) -> None: ...

class VehicleData(_message.Message):
    __slots__ = ["charge_schedule_state", "charge_state", "climate_state", "closures_state", "drive_state", "location_state", "media_detail_state", "media_state", "parental_controls_state", "preconditioning_schedule_state", "software_update_state", "tire_pressure_state"]
    CHARGE_SCHEDULE_STATE_FIELD_NUMBER: _ClassVar[int]
    CHARGE_STATE_FIELD_NUMBER: _ClassVar[int]
    CLIMATE_STATE_FIELD_NUMBER: _ClassVar[int]
    CLOSURES_STATE_FIELD_NUMBER: _ClassVar[int]
    DRIVE_STATE_FIELD_NUMBER: _ClassVar[int]
    LOCATION_STATE_FIELD_NUMBER: _ClassVar[int]
    MEDIA_DETAIL_STATE_FIELD_NUMBER: _ClassVar[int]
    MEDIA_STATE_FIELD_NUMBER: _ClassVar[int]
    PARENTAL_CONTROLS_STATE_FIELD_NUMBER: _ClassVar[int]
    PRECONDITIONING_SCHEDULE_STATE_FIELD_NUMBER: _ClassVar[int]
    SOFTWARE_UPDATE_STATE_FIELD_NUMBER: _ClassVar[int]
    TIRE_PRESSURE_STATE_FIELD_NUMBER: _ClassVar[int]
    charge_schedule_state: ChargeScheduleState
    charge_state: ChargeState
    climate_state: ClimateState
    closures_state: ClosuresState
    drive_state: DriveState
    location_state: LocationState
    media_detail_state: MediaDetailState
    media_state: MediaState
    parental_controls_state: ParentalControlsState
    preconditioning_schedule_state: PreconditioningScheduleState
    software_update_state: SoftwareUpdateState
    tire_pressure_state: TirePressureState
    def __init__(self, charge_state: _Optional[_Union[ChargeState, _Mapping]] = ..., climate_state: _Optional[_Union[ClimateState, _Mapping]] = ..., drive_state: _Optional[_Union[DriveState, _Mapping]] = ..., location_state: _Optional[_Union[LocationState, _Mapping]] = ..., closures_state: _Optional[_Union[ClosuresState, _Mapping]] = ..., charge_schedule_state: _Optional[_Union[ChargeScheduleState, _Mapping]] = ..., preconditioning_schedule_state: _Optional[_Union[PreconditioningScheduleState, _Mapping]] = ..., tire_pressure_state: _Optional[_Union[TirePressureState, _Mapping]] = ..., media_state: _Optional[_Union[MediaState, _Mapping]] = ..., media_detail_state: _Optional[_Union[MediaDetailState, _Mapping]] = ..., software_update_state: _Optional[_Union[SoftwareUpdateState, _Mapping]] = ..., parental_controls_state: _Optional[_Union[ParentalControlsState, _Mapping]] = ...) -> None: ...

class VehicleState(_message.Message):
    __slots__ = ["guestMode"]
    class GuestMode(_message.Message):
        __slots__ = ["GuestModeActive"]
        GUESTMODEACTIVE_FIELD_NUMBER: _ClassVar[int]
        GuestModeActive: bool
        def __init__(self, GuestModeActive: bool = ...) -> None: ...
    GUESTMODE_FIELD_NUMBER: _ClassVar[int]
    guestMode: VehicleState.GuestMode
    def __init__(self, guestMode: _Optional[_Union[VehicleState.GuestMode, _Mapping]] = ...) -> None: ...

class MediaSourceType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
