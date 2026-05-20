from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor
SESSION_INFO_STATUS_KEY_NOT_ON_WHITELIST: Session_Info_Status
SESSION_INFO_STATUS_OK: Session_Info_Status
SIGNATURE_TYPE_AES_GCM: SignatureType
SIGNATURE_TYPE_AES_GCM_PERSONALIZED: SignatureType
SIGNATURE_TYPE_AES_GCM_RESPONSE: SignatureType
SIGNATURE_TYPE_HMAC: SignatureType
SIGNATURE_TYPE_HMAC_PERSONALIZED: SignatureType
TAG_CHALLENGE: Tag
TAG_COUNTER: Tag
TAG_DOMAIN: Tag
TAG_END: Tag
TAG_EPOCH: Tag
TAG_EXPIRES_AT: Tag
TAG_FAULT: Tag
TAG_FLAGS: Tag
TAG_PERSONALIZATION: Tag
TAG_REQUEST_HASH: Tag
TAG_SIGNATURE_TYPE: Tag

class AES_GCM_Personalized_Signature_Data(_message.Message):
    __slots__ = ["counter", "epoch", "expires_at", "nonce", "tag"]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    EPOCH_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    counter: int
    epoch: bytes
    expires_at: int
    nonce: bytes
    tag: bytes
    def __init__(self, epoch: _Optional[bytes] = ..., nonce: _Optional[bytes] = ..., counter: _Optional[int] = ..., expires_at: _Optional[int] = ..., tag: _Optional[bytes] = ...) -> None: ...

class AES_GCM_Response_Signature_Data(_message.Message):
    __slots__ = ["counter", "nonce", "tag"]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    counter: int
    nonce: bytes
    tag: bytes
    def __init__(self, nonce: _Optional[bytes] = ..., counter: _Optional[int] = ..., tag: _Optional[bytes] = ...) -> None: ...

class GetSessionInfoRequest(_message.Message):
    __slots__ = ["key_identity"]
    KEY_IDENTITY_FIELD_NUMBER: _ClassVar[int]
    key_identity: KeyIdentity
    def __init__(self, key_identity: _Optional[_Union[KeyIdentity, _Mapping]] = ...) -> None: ...

class HMAC_Personalized_Signature_Data(_message.Message):
    __slots__ = ["counter", "epoch", "expires_at", "tag"]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    EPOCH_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    counter: int
    epoch: bytes
    expires_at: int
    tag: bytes
    def __init__(self, epoch: _Optional[bytes] = ..., counter: _Optional[int] = ..., expires_at: _Optional[int] = ..., tag: _Optional[bytes] = ...) -> None: ...

class HMAC_Signature_Data(_message.Message):
    __slots__ = ["tag"]
    TAG_FIELD_NUMBER: _ClassVar[int]
    tag: bytes
    def __init__(self, tag: _Optional[bytes] = ...) -> None: ...

class KeyIdentity(_message.Message):
    __slots__ = ["handle", "public_key"]
    HANDLE_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    handle: int
    public_key: bytes
    def __init__(self, public_key: _Optional[bytes] = ..., handle: _Optional[int] = ...) -> None: ...

class SessionInfo(_message.Message):
    __slots__ = ["clock_time", "counter", "epoch", "handle", "publicKey", "status"]
    CLOCK_TIME_FIELD_NUMBER: _ClassVar[int]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    EPOCH_FIELD_NUMBER: _ClassVar[int]
    HANDLE_FIELD_NUMBER: _ClassVar[int]
    PUBLICKEY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    clock_time: int
    counter: int
    epoch: bytes
    handle: int
    publicKey: bytes
    status: Session_Info_Status
    def __init__(self, counter: _Optional[int] = ..., publicKey: _Optional[bytes] = ..., epoch: _Optional[bytes] = ..., clock_time: _Optional[int] = ..., status: _Optional[_Union[Session_Info_Status, str]] = ..., handle: _Optional[int] = ...) -> None: ...

class SignatureData(_message.Message):
    __slots__ = ["AES_GCM_Personalized_data", "AES_GCM_Response_data", "HMAC_Personalized_data", "session_info_tag", "signer_identity"]
    AES_GCM_PERSONALIZED_DATA_FIELD_NUMBER: _ClassVar[int]
    AES_GCM_Personalized_data: AES_GCM_Personalized_Signature_Data
    AES_GCM_RESPONSE_DATA_FIELD_NUMBER: _ClassVar[int]
    AES_GCM_Response_data: AES_GCM_Response_Signature_Data
    HMAC_PERSONALIZED_DATA_FIELD_NUMBER: _ClassVar[int]
    HMAC_Personalized_data: HMAC_Personalized_Signature_Data
    SESSION_INFO_TAG_FIELD_NUMBER: _ClassVar[int]
    SIGNER_IDENTITY_FIELD_NUMBER: _ClassVar[int]
    session_info_tag: HMAC_Signature_Data
    signer_identity: KeyIdentity
    def __init__(self, signer_identity: _Optional[_Union[KeyIdentity, _Mapping]] = ..., AES_GCM_Personalized_data: _Optional[_Union[AES_GCM_Personalized_Signature_Data, _Mapping]] = ..., session_info_tag: _Optional[_Union[HMAC_Signature_Data, _Mapping]] = ..., HMAC_Personalized_data: _Optional[_Union[HMAC_Personalized_Signature_Data, _Mapping]] = ..., AES_GCM_Response_data: _Optional[_Union[AES_GCM_Response_Signature_Data, _Mapping]] = ...) -> None: ...

class Tag(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class SignatureType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class Session_Info_Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
