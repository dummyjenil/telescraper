"""MTProto 2.0 State management, packet encryption and decryption."""

import io
import os
import struct
import time
from collections import deque
from hashlib import sha256
from typing import Optional, Tuple

from ..crypto import AES, AuthKey
from ..errors import InvalidBufferError, SecurityError
from ..extensions import BinaryReader
from ..tl.core import GzipPacked, TLMessage
from ..tl.functions import InvokeAfterMsgRequest
from ..tl.tlobject import TLRequest

MAX_RECENT_MSG_IDS = 500
MSG_TOO_NEW_DELTA = 30
MSG_TOO_OLD_DELTA = 300


class _OpaqueRequest(TLRequest):
    def __init__(self, data: bytes):
        self.data = data

    def _bytes(self):
        return self.data


class MTProtoState:
    """
    Holds session state, message IDs, salts, sequence numbers,
    and handles MTProto 2.0 encryption/decryption.
    """

    def __init__(self, auth_key: Optional[AuthKey]):
        self.auth_key = auth_key
        self.time_offset = 0
        self.salt = 0
        self.id = 0
        self._sequence = 0
        self._last_msg_id = 0
        self._recent_remote_ids = deque(maxlen=MAX_RECENT_MSG_IDS)
        self.reset()

    def reset(self) -> None:
        self.id = struct.unpack("q", os.urandom(8))[0]
        self._sequence = 0
        self._last_msg_id = 0
        self._recent_remote_ids.clear()

    def _get_new_msg_id(self) -> int:
        now = time.time() + self.time_offset
        nanoseconds = int((now - int(now)) * 1e9)
        new_msg_id = (int(now) << 32) | (nanoseconds << 2)

        if self._last_msg_id >= new_msg_id:
            new_msg_id = self._last_msg_id + 4

        self._last_msg_id = new_msg_id
        return new_msg_id

    def _get_seq_no(self, content_related: bool) -> int:
        if content_related:
            result = self._sequence * 2 + 1
            self._sequence += 1
            return result
        else:
            return self._sequence * 2

    @staticmethod
    def _calc_key(auth_key: bytes, msg_key: bytes, client: bool) -> Tuple[bytes, bytes]:
        x = 0 if client else 8
        sha256a = sha256(msg_key + auth_key[x : x + 36]).digest()
        sha256b = sha256(auth_key[x + 40 : x + 76] + msg_key).digest()

        aes_key = sha256a[:8] + sha256b[8:24] + sha256a[24:32]
        aes_iv = sha256b[:8] + sha256a[8:24] + sha256b[24:32]
        return aes_key, aes_iv

    def write_data_as_message(
        self, buffer: io.BytesIO, data: bytes, content_related: bool = True, after_id: Optional[int] = None
    ) -> int:
        msg_id = self._get_new_msg_id()
        seq_no = self._get_seq_no(content_related)

        if after_id is None:
            body = GzipPacked.gzip_if_smaller(content_related, data)
        else:
            body = GzipPacked.gzip_if_smaller(
                content_related, bytes(InvokeAfterMsgRequest(after_id, _OpaqueRequest(data)))
            )

        buffer.write(struct.pack("<qii", msg_id, seq_no, len(body)))
        buffer.write(body)
        return msg_id

    def encrypt_message_data(self, data: bytes) -> bytes:
        if not self.auth_key:
            raise SecurityError("Cannot encrypt message without AuthKey")

        data = struct.pack("<qq", self.salt, self.id) + data
        padding = os.urandom(-(len(data) + 12) % 16 + 12)

        msg_key_large = sha256(self.auth_key.key[88 : 88 + 32] + data + padding).digest()
        msg_key = msg_key_large[8:24]
        aes_key, aes_iv = self._calc_key(self.auth_key.key, msg_key, True)

        key_id = struct.pack("<Q", self.auth_key.key_id)
        return key_id + msg_key + AES.encrypt_ige(data + padding, aes_key, aes_iv)

    def decrypt_message_data(self, body: bytes) -> TLMessage:
        if len(body) < 24:
            raise InvalidBufferError(body)

        key_id = struct.unpack("<Q", body[:8])[0]
        if not self.auth_key or key_id != self.auth_key.key_id:
            raise SecurityError("Server replied with an invalid auth key ID")

        msg_key = body[8:24]
        aes_key, aes_iv = self._calc_key(self.auth_key.key, msg_key, False)
        decrypted = AES.decrypt_ige(body[24:], aes_key, aes_iv)

        our_key = sha256(self.auth_key.key[96 : 96 + 32] + decrypted)
        if msg_key != our_key.digest()[8:24]:
            raise SecurityError("Received msg_key does not match expected SHA256")

        reader = BinaryReader(decrypted)
        self.salt = reader.read_long()
        server_session_id = reader.read_long()
        if server_session_id != self.id:
            raise SecurityError(f"Server replied with wrong session ID: {server_session_id} != {self.id}")

        remote_msg_id = reader.read_long()
        remote_seq_no = reader.read_int()
        _msg_len = reader.read_int()
        obj = reader.tgread_object()
        return TLMessage(remote_msg_id, remote_seq_no, obj)
