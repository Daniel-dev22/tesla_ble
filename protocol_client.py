"""Tesla BLE protocol builder and parser."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .crypto import TeslaEncryptedPayload, TeslaKeyManager
from .protocol import BLECarServerVehicleAction, UniversalMessageDomain
from .proto import car_server_pb2, common_pb2, signatures_pb2, universal_message_pb2, vcsec_pb2


def _random_bytes(length: int = 16) -> bytes:
    return os.urandom(length)


@dataclass
class ParsedCarServerResponse:
    response: car_server_pb2.Response
    fault: int


class TeslaBleProtocolClient:
    """Mirror ESPHome TeslaBLE::Client behaviour using protobufs."""

    def __init__(self, key_manager: TeslaKeyManager, vin: Optional[str] = None) -> None:
        self._key_manager = key_manager
        if vin:
            self._key_manager.set_vin(vin)
        self._connection_id: bytes = _random_bytes(16)

    @property
    def connection_id(self) -> bytes:
        return self._connection_id

    def set_connection_id(self, connection_id: Optional[bytes] = None) -> None:
        self._connection_id = connection_id or _random_bytes(16)

    def set_vin(self, vin: str) -> None:
        self._key_manager.set_vin(vin)

    def _public_key(self) -> bytes:
        return self._key_manager.get_public_key_data()

    # ---------------------------------------------------------------------
    # Session / Universal message helpers
    # ---------------------------------------------------------------------
    def build_session_info_request(self, domain: int) -> bytes:
        domain_value = int(domain)
        public_key, challenge = self._key_manager.prepare_session_request(domain_value)

        routable = universal_message_pb2.RoutableMessage()

        to_dest = universal_message_pb2.Destination()
        to_dest.domain = domain_value
        routable.to_destination.CopyFrom(to_dest)

        from_dest = universal_message_pb2.Destination()
        from_dest.routing_address = self._connection_id
        routable.from_destination.CopyFrom(from_dest)

        session_request = universal_message_pb2.SessionInfoRequest()
        session_request.public_key = public_key
        if challenge:
            session_request.challenge = challenge
        routable.session_info_request.CopyFrom(session_request)

        routable.uuid = _random_bytes(16)

        encoded = routable.SerializeToString()
        return len(encoded).to_bytes(2, "big") + encoded

    def _wrap_universal_message(
        self,
        payload: bytes,
        domain: int,
        encrypt: bool,
    ) -> bytes:
        routable = universal_message_pb2.RoutableMessage()

        to_dest = universal_message_pb2.Destination()
        to_dest.domain = domain
        routable.to_destination.CopyFrom(to_dest)

        from_dest = universal_message_pb2.Destination()
        from_dest.routing_address = self._connection_id
        routable.from_destination.CopyFrom(from_dest)

        routable.flags = TeslaKeyManager.REQUEST_FLAGS

        if encrypt:
            session = self._key_manager.get_session(domain)
            if session is None:
                raise RuntimeError(f"No session for domain {domain}")

            encrypted = self._key_manager.encrypt_payload(domain, payload)

            routable.protobuf_message_as_bytes = encrypted.ciphertext

            signature_data = signatures_pb2.SignatureData()
            signature_data.signer_identity.public_key = self._public_key()
            aes_sig = signature_data.AES_GCM_Personalized_data
            aes_sig.epoch = session.epoch or b"\x00" * 16
            aes_sig.nonce = encrypted.nonce
            aes_sig.counter = encrypted.counter
            aes_sig.expires_at = encrypted.expires_at
            aes_sig.tag = encrypted.tag

            routable.signature_data.CopyFrom(signature_data)
        else:
            routable.protobuf_message_as_bytes = payload

        routable.uuid = _random_bytes(16)

        encoded = routable.SerializeToString()
        return len(encoded).to_bytes(2, "big") + encoded

    # ------------------------------------------------------------------
    # VCSEC builders
    # ------------------------------------------------------------------
    def build_whitelist_message(self, role: int, form_factor: int) -> bytes:
        permissions = vcsec_pb2.PermissionChange()
        permissions.key.PublicKeyRaw = self._public_key()
        permissions.keyRole = role

        whitelist = vcsec_pb2.WhitelistOperation()
        whitelist.metadataForKey.keyFormFactor = form_factor
        whitelist.addKeyToWhitelistAndAddPermissions.CopyFrom(permissions)

        payload = vcsec_pb2.UnsignedMessage()
        payload.WhitelistOperation.CopyFrom(whitelist)

        return self._wrap_universal_message(
            payload.SerializeToString(),
            domain=UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
            encrypt=False,
        )

    def build_vcsec_information_request(self, request_type: int, encrypt: bool = False) -> bytes:
        info_req = vcsec_pb2.InformationRequest()
        info_req.informationRequestType = request_type

        unsigned = vcsec_pb2.UnsignedMessage()
        unsigned.InformationRequest.CopyFrom(info_req)

        payload = unsigned.SerializeToString()
        return self._wrap_universal_message(
            payload,
            domain=UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
            encrypt=encrypt,
        )

    def build_vcsec_action_message(self, action: int) -> bytes:
        unsigned = vcsec_pb2.UnsignedMessage()
        unsigned.RKEAction = action

        payload = unsigned.SerializeToString()
        return self._wrap_universal_message(
            payload,
            domain=UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
            encrypt=True,
        )

    def build_vcsec_closure_move_request(self, closure_request: vcsec_pb2.ClosureMoveRequest) -> bytes:
        unsigned = vcsec_pb2.UnsignedMessage()
        unsigned.closureMoveRequest.CopyFrom(closure_request)

        payload = unsigned.SerializeToString()
        return self._wrap_universal_message(
            payload,
            domain=UniversalMessageDomain.DOMAIN_VEHICLE_SECURITY,
            encrypt=True,
        )

    # ------------------------------------------------------------------
    # CarServer builders
    # ------------------------------------------------------------------
    def build_carserver_get_vehicle_data(self, action: BLECarServerVehicleAction) -> bytes:
        get_data = car_server_pb2.GetVehicleData()

        if action == BLECarServerVehicleAction.GET_CHARGE_STATE:
            get_data.getChargeState.CopyFrom(car_server_pb2.GetChargeState())
        elif action == BLECarServerVehicleAction.GET_CLIMATE_STATE:
            get_data.getClimateState.CopyFrom(car_server_pb2.GetClimateState())
        elif action == BLECarServerVehicleAction.GET_DRIVE_STATE:
            get_data.getDriveState.CopyFrom(car_server_pb2.GetDriveState())
        elif action == BLECarServerVehicleAction.GET_LOCATION_STATE:
            get_data.getLocationState.CopyFrom(car_server_pb2.GetLocationState())
        elif action == BLECarServerVehicleAction.GET_CLOSURES_STATE:
            get_data.getClosuresState.CopyFrom(car_server_pb2.GetClosuresState())
        elif action == BLECarServerVehicleAction.GET_TIRE_PRESSURE_STATE:
            get_data.getTirePressureState.CopyFrom(car_server_pb2.GetTirePressureState())
        else:
            raise ValueError(f"Unsupported get vehicle data action: {action}")

        vehicle_action = car_server_pb2.VehicleAction()
        vehicle_action.getVehicleData.CopyFrom(get_data)

        action_wrapper = car_server_pb2.Action()
        action_wrapper.vehicleAction.CopyFrom(vehicle_action)

        payload = action_wrapper.SerializeToString()
        return self._wrap_universal_message(
            payload,
            domain=UniversalMessageDomain.DOMAIN_INFOTAINMENT,
            encrypt=True,
        )

    def build_carserver_vehicle_action(
        self,
        action: BLECarServerVehicleAction,
        parameter: int = 0,
        parameter_bool: Optional[bool] = None,
        parameter_float: Optional[float] = None,
        parameter2: Optional[int] = None,
    ) -> bytes:
        vehicle_action = car_server_pb2.VehicleAction()

        if action == BLECarServerVehicleAction.SET_CHARGING_SWITCH:
            charging = car_server_pb2.ChargingStartStopAction()
            if parameter_bool:
                charging.start.CopyFrom(common_pb2.Void())
            else:
                charging.stop.CopyFrom(common_pb2.Void())
            vehicle_action.chargingStartStopAction.CopyFrom(charging)

        elif action == BLECarServerVehicleAction.SET_CHARGING_AMPS:
            amps = car_server_pb2.SetChargingAmpsAction()
            amps.charging_amps = parameter
            vehicle_action.setChargingAmpsAction.CopyFrom(amps)

        elif action == BLECarServerVehicleAction.SET_CHARGING_LIMIT:
            limit = car_server_pb2.ChargingSetLimitAction()
            limit.percent = parameter
            vehicle_action.chargingSetLimitAction.CopyFrom(limit)

        elif action == BLECarServerVehicleAction.SET_SENTRY_SWITCH:
            sentry = car_server_pb2.VehicleControlSetSentryModeAction()
            sentry.on = bool(parameter_bool)
            vehicle_action.vehicleControlSetSentryModeAction.CopyFrom(sentry)

        elif action == BLECarServerVehicleAction.SET_HVAC_SWITCH:
            hvac = car_server_pb2.HvacAutoAction()
            hvac.power_on = bool(parameter_bool)
            hvac.manual_override = False
            vehicle_action.hvacAutoAction.CopyFrom(hvac)

        elif action == BLECarServerVehicleAction.SET_HVAC_STEERING_HEATER_SWITCH:
            steering = car_server_pb2.HvacSteeringWheelHeaterAction()
            steering.power_on = bool(parameter_bool)
            vehicle_action.hvacSteeringWheelHeaterAction.CopyFrom(steering)

        elif action == BLECarServerVehicleAction.SET_OPEN_CHARGE_PORT_DOOR:
            vehicle_action.chargePortDoorOpen.CopyFrom(car_server_pb2.ChargePortDoorOpen())

        elif action == BLECarServerVehicleAction.SET_CLOSE_CHARGE_PORT_DOOR:
            vehicle_action.chargePortDoorClose.CopyFrom(car_server_pb2.ChargePortDoorClose())

        elif action == BLECarServerVehicleAction.SOUND_HORN:
            vehicle_action.vehicleControlHonkHornAction.CopyFrom(car_server_pb2.VehicleControlHonkHornAction())

        elif action == BLECarServerVehicleAction.FLASH_LIGHT:
            vehicle_action.vehicleControlFlashLightsAction.CopyFrom(car_server_pb2.VehicleControlFlashLightsAction())

        elif action == BLECarServerVehicleAction.SET_WINDOWS_SWITCH:
            window = car_server_pb2.VehicleControlWindowAction()
            if parameter_bool:
                window.vent.CopyFrom(common_pb2.Void())
            else:
                window.close.CopyFrom(common_pb2.Void())
            vehicle_action.vehicleControlWindowAction.CopyFrom(window)

        elif action == BLECarServerVehicleAction.DEFROST_CAR:
            defrost = car_server_pb2.HvacSetPreconditioningMaxAction()
            defrost.on = bool(parameter_bool)
            defrost.manual_override = False
            vehicle_action.hvacSetPreconditioningMaxAction.CopyFrom(defrost)

        else:
            raise ValueError(f"Unsupported vehicle action: {action}")

        action_wrapper = car_server_pb2.Action()
        action_wrapper.vehicleAction.CopyFrom(vehicle_action)

        payload = action_wrapper.SerializeToString()
        return self._wrap_universal_message(
            payload,
            domain=UniversalMessageDomain.DOMAIN_INFOTAINMENT,
            encrypt=True,
        )

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------
    def parse_carserver_response(self, message: universal_message_pb2.RoutableMessage) -> ParsedCarServerResponse:
        fault = 0
        if message.HasField("signedMessageStatus"):
            fault = message.signedMessageStatus.signed_message_fault

        payload_bytes = bytes(message.protobuf_message_as_bytes)

        if message.WhichOneof("sub_sigData") == "signature_data":
            sig_choice = message.signature_data.WhichOneof("sig_type")
            if sig_choice == "AES_GCM_Response_data":
                session = self._key_manager.get_session(UniversalMessageDomain.DOMAIN_INFOTAINMENT)
                if session is None:
                    raise RuntimeError("No infotainment session to decrypt response")

                response_sig = message.signature_data.AES_GCM_Response_data
                nonce = bytes(response_sig.nonce)
                tag = bytes(response_sig.tag)
                response_counter = response_sig.counter
                payload_bytes = self._key_manager.decrypt_payload(
                    UniversalMessageDomain.DOMAIN_INFOTAINMENT,
                    payload_bytes,
                    nonce,
                    tag,
                    fault,
                    response_counter,
                    message.flags,
                )

        response = car_server_pb2.Response()
        response.ParseFromString(payload_bytes)
        return ParsedCarServerResponse(response=response, fault=fault)
