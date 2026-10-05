"""
Telegram VoIP and Video Call MTProto Signalling Engine.
Handles call creation, acceptance, discard, and Diffie-Hellman cryptographic key fingerprint exchange.
100% Pure Synchronous, Zero Asyncio.
"""

import os
import hashlib
from typing import Optional, Dict, Any, Tuple
from .tl import functions, types
from .helpers import generate_random_long
from .utils import get_input_user


from .crypto import rsa


# Standard Telegram 2048-bit MODP Group 14 DH prime and generator
DH_PRIME_2048 = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AACAA68FFFFFFFFFFFFFFFF",
    16
)
DH_G = 3


class VoIPSignalling:
    """
    MTProto VoIP / Video Call Signalling and Cryptographic Key Exchange Manager.
    """

    def __init__(self, client: Any):
        self.client = client
        self._dh_a: Optional[int] = None
        self._g_a: Optional[int] = None
        self._g_a_hash: Optional[bytes] = None

    def _generate_dh_pair(self) -> Tuple[int, int, bytes]:
        """Generate local Diffie-Hellman private exponent a and public g_a."""
        a = int.from_bytes(os.urandom(256), 'big') % (DH_PRIME_2048 - 1)
        g_a = pow(DH_G, a, DH_PRIME_2048)
        g_a_bytes = rsa.get_byte_array(g_a)
        g_a_hash = hashlib.sha256(g_a_bytes).digest()
        self._dh_a = a
        self._g_a = g_a
        self._g_a_hash = g_a_hash
        return a, g_a, g_a_hash

    def request_call(
        self,
        user_id: Any,
        video: bool = False
    ) -> Any:
        """
        Initiate a private Telegram voice or video call.

        :param user_id: Target user username, phone, or ID
        :param video: True to request a video call
        :return: phone.PhoneCall result containing call state and protocol configs
        """
        input_user = get_input_user(self.client.get_input_entity(user_id))
        _, _, g_a_hash = self._generate_dh_pair()
        random_id = generate_random_long()

        protocol = types.PhoneCallProtocol(
            min_layer=65,
            max_layer=92,
            udp_p2p=True,
            udp_reflector=True,
            library_versions=["1.3.0", "2.0.0"]
        )

        req = functions.phone.RequestCallRequest(
            user_id=input_user,
            random_id=random_id,
            g_a_hash=g_a_hash,
            protocol=protocol,
            video=video
        )
        return self.client._invoke(req)

    def accept_call(
        self,
        call_id: int,
        access_hash: int,
        g_a: bytes
    ) -> Tuple[Any, int]:
        """
        Accept an incoming Telegram voice or video call.

        :param call_id: Phone call ID
        :param access_hash: Phone call access hash
        :param g_a: Sender's public DH bytes
        :return: (PhoneCall result, shared key fingerprint)
        """
        b = int.from_bytes(os.urandom(256), 'big') % (DH_PRIME_2048 - 1)
        g_b = pow(DH_G, b, DH_PRIME_2048)
        g_b_bytes = rsa.get_byte_array(g_b)

        # Compute shared key: K = (g_a)^b mod p
        g_a_int = int.from_bytes(g_a, 'big')
        shared_key = pow(g_a_int, b, DH_PRIME_2048)
        shared_key_bytes = rsa.get_byte_array(shared_key)
        key_fingerprint = int.from_bytes(hashlib.sha256(shared_key_bytes).digest()[:8], 'little')

        input_call = types.InputPhoneCall(id=call_id, access_hash=access_hash)
        protocol = types.PhoneCallProtocol(
            min_layer=65,
            max_layer=92,
            udp_p2p=True,
            udp_reflector=True,
            library_versions=["1.3.0", "2.0.0"]
        )

        req = functions.phone.AcceptCallRequest(
            peer=input_call,
            g_b=g_b_bytes,
            protocol=protocol
        )
        res = self.client._invoke(req)
        return res, key_fingerprint

    def discard_call(
        self,
        call_id: int,
        access_hash: int,
        duration: int = 0,
        reason: Optional[types.TypePhoneCallDiscardReason] = None,
        video: bool = False
    ) -> Any:
        """
        End, decline, or hang up an active or incoming call.
        """
        input_call = types.InputPhoneCall(id=call_id, access_hash=access_hash)
        req = functions.phone.DiscardCallRequest(
            peer=input_call,
            duration=duration,
            reason=reason or types.PhoneCallDiscardReasonHangup(),
            connection_id=0,
            video=video
        )
        return self.client._invoke(req)

    def get_call_config(self) -> Any:
        """
        Fetch global VoIP STUN, TURN, and WebRTC relay server configurations.
        """
        return self.client._invoke(functions.phone.GetCallConfigRequest())
