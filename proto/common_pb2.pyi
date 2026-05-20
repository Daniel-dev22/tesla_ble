from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor
INVALID: Invalid
Paused: MediaPlaybackStatus
Playing: MediaPlaybackStatus
Stopped: MediaPlaybackStatus
StwHeatLevel_High: StwHeatLevel
StwHeatLevel_Low: StwHeatLevel
StwHeatLevel_Off: StwHeatLevel
StwHeatLevel_Unknown: StwHeatLevel

class ChargePortLatchState(_message.Message):
    __slots__ = ["Blocking", "Disengaged", "Engaged", "SNA"]
    BLOCKING_FIELD_NUMBER: _ClassVar[int]
    Blocking: Void
    DISENGAGED_FIELD_NUMBER: _ClassVar[int]
    Disengaged: Void
    ENGAGED_FIELD_NUMBER: _ClassVar[int]
    Engaged: Void
    SNA: Void
    SNA_FIELD_NUMBER: _ClassVar[int]
    def __init__(self, SNA: _Optional[_Union[Void, _Mapping]] = ..., Disengaged: _Optional[_Union[Void, _Mapping]] = ..., Engaged: _Optional[_Union[Void, _Mapping]] = ..., Blocking: _Optional[_Union[Void, _Mapping]] = ...) -> None: ...

class ChargeSchedule(_message.Message):
    __slots__ = ["days_of_week", "enabled", "end_enabled", "end_time", "id", "latitude", "longitude", "name", "one_time", "start_enabled", "start_time"]
    DAYS_OF_WEEK_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    END_ENABLED_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ONE_TIME_FIELD_NUMBER: _ClassVar[int]
    START_ENABLED_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    days_of_week: int
    enabled: bool
    end_enabled: bool
    end_time: int
    id: int
    latitude: float
    longitude: float
    name: str
    one_time: bool
    start_enabled: bool
    start_time: int
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., days_of_week: _Optional[int] = ..., start_enabled: bool = ..., start_time: _Optional[int] = ..., end_enabled: bool = ..., end_time: _Optional[int] = ..., one_time: bool = ..., enabled: bool = ..., latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...

class LatLong(_message.Message):
    __slots__ = ["latitude", "longitude"]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...

class OffPeakChargingTimes(_message.Message):
    __slots__ = ["all_week", "weekdays"]
    ALL_WEEK_FIELD_NUMBER: _ClassVar[int]
    WEEKDAYS_FIELD_NUMBER: _ClassVar[int]
    all_week: Void
    weekdays: Void
    def __init__(self, all_week: _Optional[_Union[Void, _Mapping]] = ..., weekdays: _Optional[_Union[Void, _Mapping]] = ...) -> None: ...

class PreconditionSchedule(_message.Message):
    __slots__ = ["days_of_week", "enabled", "id", "latitude", "longitude", "name", "one_time", "precondition_time"]
    DAYS_OF_WEEK_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ONE_TIME_FIELD_NUMBER: _ClassVar[int]
    PRECONDITION_TIME_FIELD_NUMBER: _ClassVar[int]
    days_of_week: int
    enabled: bool
    id: int
    latitude: float
    longitude: float
    name: str
    one_time: bool
    precondition_time: int
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., days_of_week: _Optional[int] = ..., precondition_time: _Optional[int] = ..., one_time: bool = ..., enabled: bool = ..., latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...

class PreconditioningTimes(_message.Message):
    __slots__ = ["all_week", "weekdays"]
    ALL_WEEK_FIELD_NUMBER: _ClassVar[int]
    WEEKDAYS_FIELD_NUMBER: _ClassVar[int]
    all_week: Void
    weekdays: Void
    def __init__(self, all_week: _Optional[_Union[Void, _Mapping]] = ..., weekdays: _Optional[_Union[Void, _Mapping]] = ...) -> None: ...

class Void(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class Invalid(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class MediaPlaybackStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class StwHeatLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
