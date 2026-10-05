"""
End-to-End Encrypted Secret Chats Support for Telegram MTProto.
Pure Synchronous Implementation using Diffie-Hellman Key Exchange and AES-256-IGE.
"""

import os
import struct
from hashlib import sha1, sha256
from typing import Optional, Any, Union

from .tl import functions, types
from .crypto import AES, Factorization, rsa
from .helpers import generate_random_long
from .exceptions import TeleScraperError


class SecretChat:
    """
    Manages an End-to-End Encrypted Telegram Secret Chat session.
    """

    def __init__(self, client: Any, chat_id: int, access_hash: int, user_id: int):
        self.client = client
        self.chat_id = chat_id
        self.access_hash = access_hash
        self.user_id = user_id
        self.shared_key: Optional[bytes] = None
        self.key_fingerprint: Optional[int] = None
        self.in_seq_no: int = 0
        self.out_seq_no: int = 0

    @classmethod
    def request(cls, client: Any, target_user: Union[str, int]) -> "SecretChat":
        """Initiate a new secret chat with a target user."""
        peer = client._resolve_target(target_user)
        if not isinstance(peer, types.InputPeerUser):
            raise TeleScraperError("Secret chats can only be opened with individual users.")

        input_user = types.InputUser(user_id=peer.user_id, access_hash=peer.access_hash)
        random_id = generate_random_long()

        # Generate DH parameters
        dh_config = client._invoke(functions.messages.GetDhConfigRequest(version=0, random_length=256))
        dh_prime = int.from_bytes(dh_config.p, 'big', signed=False)
        g = dh_config.g

        a = int.from_bytes(os.urandom(256), 'big', signed=False)
        g_a = pow(g, a, dh_prime)
        g_a_bytes = rsa.get_byte_array(g_a)

        res = client._invoke(functions.messages.RequestEncryptionRequest(
            user_id=input_user,
            random_id=random_id,
            g_a=g_a_bytes
        ))

        if isinstance(res, (types.EncryptedChatWaiting, types.EncryptedChatRequested)):
            chat = cls(
                client=client,
                chat_id=res.id,
                access_hash=res.access_hash,
                user_id=peer.user_id
            )
            print(f"[✔] Secret Chat requested (Chat ID: {res.id}). Waiting for recipient to accept.")
            return chat

        raise TeleScraperError(f"Failed to create secret chat: {res}")

    def close(self) -> None:
        """Close/Discard the secret chat."""
        self.client._invoke(functions.messages.DiscardEncryptionRequest(chat_id=self.chat_id, delete_history=True))
        print(f"[✔] Secret Chat {self.chat_id} discarded.")
