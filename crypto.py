"""Tesla BLE cryptography and session management."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


_LOGGER = logging.getLogger(__name__)


def _import_crypto_modules() -> None:
    """Import heavy cryptography modules on demand."""
    global serialization, ec, AESGCM

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM


serialization = None
ec = None
AESGCM = None


@dataclass
class TeslaEncryptedPayload:
    """Container for encrypted payload details."""

    ciphertext: bytes
    nonce: bytes
    tag: bytes
    expires_at: int
    request_hash: bytes
    counter: int


@dataclass
class TeslaSession:
    """Mirrors ESPHome TeslaBLE::Peer behaviour."""

    domain: int
    vin: str = ""
    aes_key: Optional[bytes] = None
    peer_public_key: Optional[bytes] = None
    epoch: bytes = field(default_factory=bytes)
    counter: int = 0
    time_zero: int = 0
    handle: int = 0
    status: int = 0
    initialized: bool = False
    last_used: float = 0.0
    last_request_hash: Optional[bytes] = None
    last_request_counter: int = 0
    created_at: Optional[float] = None  # Timestamp when session was created (for accurate time_zero calculation when loading)

    def set_vin(self, vin: str) -> None:
        self.vin = vin or ""

    def set_shared_secret(self, shared_secret: bytes) -> None:
        digest = hashlib.sha1(shared_secret).digest()
        self.aes_key = digest[:16]
        _LOGGER.debug("Set AES key for domain %s: shared_secret_sha1=%s, aes_key=%s",
                     self.domain, digest.hex(), self.aes_key.hex())
        _LOGGER.debug("Session %s derived AES key", self.domain)

    def update_from_session_info(self, session_info, created_at: Optional[float] = None) -> None:
        epoch_bytes = bytes(session_info.epoch)
        if len(epoch_bytes) < 16:
            epoch_bytes = epoch_bytes.ljust(16, b"\x00")
        elif len(epoch_bytes) > 16:
            epoch_bytes = epoch_bytes[:16]

        self.epoch = epoch_bytes
        self.counter = int(session_info.counter)
        self.handle = int(session_info.handle)
        self.status = int(session_info.status)
        pubkey_preview = bytes(session_info.publicKey)[:8].hex() if session_info.publicKey else None
        _LOGGER.debug("Domain %d session update: epoch=%s, counter=%d, handle=%d, pubkey=%s",
                     self.domain, self.epoch[:8].hex() if self.epoch else None, self.counter, self.handle, pubkey_preview)

        # Calculate time_zero using created_at if available (matching Tesla Go SDK)
        # When loading from storage, created_at is the original timestamp when SessionInfo was received
        # This ensures correct time_zero calculation even after restart
        generated_at = created_at if created_at is not None else time.time()
        self.time_zero = int(generated_at) - int(session_info.clock_time)
        _LOGGER.debug("time_zero calculation: generated_at=%d, clock_time=%d, time_zero=%d, created_at=%s",
                     int(generated_at), int(session_info.clock_time), self.time_zero, created_at)
        if created_at is None:
            self.created_at = time.time()  # Store creation time for future loads
        self.initialized = True
        self.last_used = time.time()

    def increment_counter(self) -> None:
        self.counter += 1

    def generate_expires_at(self, seconds: int = 10) -> int:
        """Generate expiration timestamp relative to vehicle clock.

        Uses 10 seconds to account for:
        - Network latency between SessionInfo response and command TX
        - Processing delays
        - Clock drift between system and vehicle
        """
        current = int(time.time())
        return max(0, current + seconds - self.time_zero)

    def _construct_ad_buffer(
        self,
        signature_type: int,
        expires_at: int,
        flags: int = 0,
        request_hash: Optional[bytes] = None,
        fault: int = 0,
    ) -> bytes:
        from .proto import signatures_pb2

        buffer = bytearray()

        def _write(tag: int, payload: bytes) -> None:
            buffer.append(tag)
            buffer.append(len(payload))
            buffer.extend(payload)

        _write(signatures_pb2.Tag.TAG_SIGNATURE_TYPE, bytes([signature_type]))
        _write(signatures_pb2.Tag.TAG_DOMAIN, bytes([self.domain]))

        vin_bytes = self.vin.encode("utf-8") if self.vin else b""
        _write(signatures_pb2.Tag.TAG_PERSONALIZATION, vin_bytes)

        # CRITICAL: Epoch and expires_at are ONLY included in PERSONALIZED (request) signatures
        # Response signatures do NOT include epoch or expires_at (matching Tesla Go SDK)
        if signature_type != signatures_pb2.SignatureType.SIGNATURE_TYPE_AES_GCM_RESPONSE:
            _write(signatures_pb2.Tag.TAG_EPOCH, self.epoch or b"\x00" * 16)
            expires_payload = expires_at.to_bytes(4, "big")
            _write(signatures_pb2.Tag.TAG_EXPIRES_AT, expires_payload)

        counter_payload = self.counter.to_bytes(4, "big")
        _write(signatures_pb2.Tag.TAG_COUNTER, counter_payload)

        if flags or signature_type == signatures_pb2.SignatureType.SIGNATURE_TYPE_AES_GCM_RESPONSE:
            flag_payload = flags.to_bytes(4, "big")
            _write(signatures_pb2.Tag.TAG_FLAGS, flag_payload)

        if signature_type == signatures_pb2.SignatureType.SIGNATURE_TYPE_AES_GCM_RESPONSE:
            if request_hash:
                _write(signatures_pb2.Tag.TAG_REQUEST_HASH, request_hash)
            fault_payload = fault.to_bytes(4, "big")
            _write(signatures_pb2.Tag.TAG_FAULT, fault_payload)

        buffer.append(signatures_pb2.Tag.TAG_END)
        return bytes(buffer)

    def construct_request_hash(self, signature_type: int, tag: bytes) -> bytes:
        return bytes([signature_type]) + tag[:16]

    def encrypt_payload(self, payload: bytes, flags: int) -> TeslaEncryptedPayload:
        from .proto import signatures_pb2

        if not self.initialized or not self.aes_key:
            raise RuntimeError("Session is not initialized for encryption")

        if AESGCM is None:
            _import_crypto_modules()

        aesgcm = AESGCM(self.aes_key)

        self.increment_counter()
        counter_value = self.counter

        expires_at = self.generate_expires_at(5)
        ad_buffer = self._construct_ad_buffer(
            signatures_pb2.SignatureType.SIGNATURE_TYPE_AES_GCM_PERSONALIZED,
            expires_at,
            flags,
        )
        aad_hash = hashlib.sha256(ad_buffer).digest()
        _LOGGER.debug("Encrypt payload: counter=%d, expires_at=%d", counter_value, expires_at)

        nonce = secrets.token_bytes(12)
        encrypted = aesgcm.encrypt(nonce, payload, aad_hash)
        ciphertext, tag = encrypted[:-16], encrypted[-16:]

        request_hash = self.construct_request_hash(
            signatures_pb2.SignatureType.SIGNATURE_TYPE_AES_GCM_PERSONALIZED,
            tag,
        )

        self.last_request_hash = request_hash
        self.last_request_counter = counter_value
        self.last_used = time.time()

        return TeslaEncryptedPayload(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=tag,
            expires_at=expires_at,
            request_hash=request_hash,
            counter=counter_value,
        )

    def decrypt_response(self, ciphertext: bytes, nonce: bytes, tag: bytes, flags: int, fault: int, response_counter: Optional[int] = None) -> bytes:
        from .proto import signatures_pb2

        if not self.initialized or not self.aes_key:
            raise RuntimeError("Session is not initialized for decryption")

        if self.last_request_hash is None:
            raise RuntimeError("No request hash stored for response decryption")

        if AESGCM is None:
            _import_crypto_modules()

        aesgcm = AESGCM(self.aes_key)

        # CRITICAL: Use the RESPONSE counter from the message (matching Tesla Go SDK)
        # The vehicle encrypted the response using response_counter in the AAD
        # NOT the request counter!
        if response_counter is None:
            raise RuntimeError("Response counter is required for decryption")

        _LOGGER.debug("Decrypt response: response_counter=%d, session_counter=%d, flags=%d, fault=%d",
                     response_counter, self.counter, flags, fault)
        _LOGGER.debug("Decrypt response session state: vin=%s, request_hash=%s",
                     self.vin[:8] if self.vin else None,
                     self.last_request_hash[:8].hex() if self.last_request_hash else None)

        # Temporarily set counter to the response counter for AD buffer construction
        saved_counter = self.counter
        self.counter = response_counter

        ad_buffer = self._construct_ad_buffer(
            signatures_pb2.SignatureType.SIGNATURE_TYPE_AES_GCM_RESPONSE,
            expires_at=0,
            flags=flags,
            request_hash=self.last_request_hash,
            fault=fault,
        )

        # Restore the current counter
        self.counter = saved_counter
        _LOGGER.debug("Decrypt AD buffer: %s", ad_buffer.hex())
        aad_hash = hashlib.sha256(ad_buffer).digest()
        _LOGGER.debug("Decrypt AAD hash: %s", aad_hash.hex())
        _LOGGER.debug("Decrypt inputs: nonce=%s, tag=%s, ciphertext_len=%d",
                     nonce.hex(), tag.hex(), len(ciphertext))

        combined = ciphertext + tag
        plaintext = aesgcm.decrypt(nonce, combined, aad_hash)
        self.last_used = time.time()
        return plaintext


class TeslaCrypto:
    """Maintain local key pair for BLE communication."""

    def __init__(self) -> None:
        if serialization is None:
            _import_crypto_modules()
        self._private_key: Optional[ec.EllipticCurvePrivateKey] = None

    def ensure_private_key(self) -> None:
        if self._private_key is None:
            self.generate_private_key()

    def generate_private_key(self) -> None:
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        _LOGGER.debug("Generated Tesla BLE private key")

    def load_private_key(self, private_key_data: bytes) -> None:
        try:
            self._private_key = serialization.load_der_private_key(
                private_key_data, password=None
            )
            _LOGGER.debug("Loaded Tesla BLE private key from storage")
        except Exception as ex:
            _LOGGER.error("Failed to load private key: %s", ex)
            raise

    def get_private_key_bytes(self) -> bytes:
        if not self._private_key:
            raise ValueError("Private key not available")
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def get_public_key_bytes(self) -> bytes:
        if not self._private_key:
            raise ValueError("Private key not available")
        public_key = self._private_key.public_key()
        return public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )

    def perform_ecdh(self, peer_public_key: bytes) -> bytes:
        if not self._private_key:
            raise ValueError("Private key not available")
        peer = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), peer_public_key
        )
        shared = self._private_key.exchange(ec.ECDH(), peer)
        _LOGGER.debug("Completed ECDH exchange")
        return shared


class TeslaKeyManager:
    """Manage keys and sessions for both VCSEC and Infotainment domains."""

    REQUEST_FLAGS = 1 << 1  # FLAG_ENCRYPT_RESPONSE

    def __init__(self) -> None:
        self.crypto = TeslaCrypto()
        self._sessions: Dict[int, TeslaSession] = {}
        self._vin: str = ""

    def set_vin(self, vin: str) -> None:
        self._vin = vin or ""
        for session in self._sessions.values():
            session.set_vin(self._vin)

    async def initialize_keys(self, private_key_data: Optional[bytes] = None) -> None:
        if private_key_data:
            self.crypto.load_private_key(private_key_data)
        else:
            self.crypto.generate_private_key()

    def get_private_key_data(self) -> bytes:
        return self.crypto.get_private_key_bytes()

    def get_public_key_data(self) -> bytes:
        return self.crypto.get_public_key_bytes()

    def prepare_session_request(self, domain: int) -> Tuple[bytes, Optional[bytes]]:
        public_key = self.get_public_key_data()
        return public_key, None

    def get_session(self, domain: int) -> Optional[TeslaSession]:
        return self._sessions.get(domain)

    def _ensure_session(self, domain: int, peer_public_key: bytes) -> TeslaSession:
        session = self._sessions.get(domain)
        if session and session.peer_public_key == peer_public_key:
            # Re-derive shared secret to ensure it's correct (matching ESPHome's loadTeslaKey)
            # This is critical when sessions are loaded from storage
            shared_secret = self.crypto.perform_ecdh(peer_public_key)
            session.set_shared_secret(shared_secret)
            return session

        shared_secret = self.crypto.perform_ecdh(peer_public_key)
        session = TeslaSession(domain=domain, vin=self._vin)
        session.peer_public_key = peer_public_key
        session.set_shared_secret(shared_secret)
        session.last_used = time.time()
        self._sessions[domain] = session
        _LOGGER.info("Created session for domain %s", domain)
        return session

    def update_session_from_info(self, domain: int, session_info, signature_data=None, created_at: Optional[float] = None) -> TeslaSession:
        peer_public_key = bytes(session_info.publicKey)
        _LOGGER.debug("Updating session %d with pubkey=%s epoch=%s counter=%d",
                     domain, peer_public_key[:8].hex(), bytes(session_info.epoch)[:8].hex(), session_info.counter)
        session = self._ensure_session(domain, peer_public_key)
        session.update_from_session_info(session_info, created_at=created_at)
        session.set_vin(self._vin)
        if signature_data is not None:
            session.signature_data = signature_data  # type: ignore[attr-defined]
        return session

    def is_session_valid(self, domain: int) -> bool:
        """Validate session matching ESPHome's isInitialized() logic."""
        session = self._sessions.get(domain)
        if not session or not session.initialized:
            return False

        # Check if epoch is valid (not all zeros) - matching ESPHome's hasValidEpoch()
        if session.epoch is None or session.epoch == b'\x00' * 16:
            _LOGGER.debug("Session for domain %s has invalid epoch (all zeros)", domain)
            return False

        # Check if AES key was derived from ECDH
        if not session.aes_key:
            _LOGGER.debug("Session for domain %s has no AES key", domain)
            return False

        if time.time() - session.last_used > 86400:
            _LOGGER.debug("Session for domain %s expired (last used > 24h)", domain)
            return False
        return True

    def invalidate_session(self, domain: int) -> None:
        if domain in self._sessions:
            _LOGGER.debug("Invalidating session for domain %s", domain)
            del self._sessions[domain]

    def encrypt_payload(self, domain: int, payload: bytes) -> TeslaEncryptedPayload:
        session = self._sessions.get(domain)
        if not session:
            raise RuntimeError(f"No session for domain {domain}")
        return session.encrypt_payload(payload, self.REQUEST_FLAGS)

    def decrypt_payload(self, domain: int, payload: bytes, nonce: bytes, tag: bytes, fault: int, response_counter: int, response_flags: int) -> bytes:
        session = self._sessions.get(domain)
        if not session:
            raise RuntimeError(f"No session for domain {domain}")
        # Use response message flags (matching Tesla Go SDK - they use message.Flags from response)
        return session.decrypt_response(payload, nonce, tag, response_flags, fault, response_counter)

    def serialize_sessions(self) -> dict[str, str]:
        """Return a serialisable snapshot of active sessions."""
        from .proto import signatures_pb2
        import json

        snapshot: dict[str, str] = {}
        for domain, session in self._sessions.items():
            info = signatures_pb2.SessionInfo()
            if session.peer_public_key:
                info.publicKey = session.peer_public_key
            if session.epoch:
                info.epoch = session.epoch
            info.counter = session.counter
            info.handle = session.handle
            info.status = session.status
            clock_time = int(time.time()) - session.time_zero if session.time_zero else 0
            info.clock_time = max(clock_time, 0)

            # Store both SessionInfo and created_at timestamp (matching Tesla Go SDK pattern)
            cache_entry = {
                "session_info": base64.b64encode(info.SerializeToString()).decode("utf-8"),
                "created_at": session.created_at if session.created_at else time.time()
            }
            snapshot[str(domain)] = json.dumps(cache_entry)
        return snapshot

    def load_sessions(self, sessions: dict[str, str]) -> None:
        """Restore sessions from a previously saved snapshot."""
        from .proto import signatures_pb2
        import json

        for domain_str, payload in sessions.items():
            try:
                domain = int(domain_str)
            except ValueError:  # pragma: no cover - defensive guard
                _LOGGER.debug("Skipping invalid session domain key: %s", domain_str)
                continue

            # Load new format (with created_at timestamp matching Tesla Go SDK)
            try:
                cache_entry = json.loads(payload)
                session_bytes = base64.b64decode(cache_entry["session_info"])
                created_at = cache_entry["created_at"]
            except (json.JSONDecodeError, KeyError):
                # Old format without created_at - skip and request fresh SessionInfo
                _LOGGER.info("Skipping session in old format for domain %s (will request fresh SessionInfo)", domain)
                continue

            info = signatures_pb2.SessionInfo()
            info.ParseFromString(session_bytes)
            session = self.update_session_from_info(domain, info, created_at=created_at)
