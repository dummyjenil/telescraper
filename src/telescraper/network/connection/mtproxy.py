"""MTProxy Transports supporting standard secrets, 'dd' secrets, and Fake-TLS."""

import os
import struct
from hashlib import sha256
from typing import Optional
from .base import SyncConnection
from ...crypto.aesctr import AESModeCTR


class ConnectionTcpMTProxyIntermediate(SyncConnection):
    """
    MTProxy Intermediate transport with secret hashing.
    """

    def __init__(self, ip: str, port: int, secret: str = "", dc_id: int = 2, **kwargs):
        super().__init__(ip, port, **kwargs)
        self.secret_str = secret
        self.dc_id = dc_id
        self._raw_secret = bytes.fromhex(secret.strip()) if isinstance(secret, str) and secret else b''
        self._encrypter: Optional[AESModeCTR] = None
        self._decrypter: Optional[AESModeCTR] = None

    def _send_handshake(self) -> None:
        # Determine protocol tag: 0xdddddddd if dd-secret else 0xeeeeeeee
        is_dd = len(self._raw_secret) > 0 and self._raw_secret[0] == 0xdd
        secret_bytes = self._raw_secret[1:] if is_dd else self._raw_secret

        while True:
            init = bytearray(os.urandom(64))
            val = (init[0] << 24) | (init[1] << 16) | (init[2] << 8) | init[3]
            if (
                init[0] != 0xef and
                val != 0x48454144 and  # HEAD
                val != 0x504f5354 and  # POST
                val != 0x47455420 and  # GET
                val != 0xeeeeeeee and
                val != 0xdddddddd and
                val != 0x00000000
            ):
                break

        tag = b'\xdd\xdd\xdd\xdd' if is_dd else b'\xee\xee\xee\xee'
        init[56:60] = tag
        init[60:62] = struct.pack('<h', self.dc_id)

        encrypt_key = sha256(bytes(init[8:40]) + secret_bytes).digest()
        encrypt_iv = bytes(init[40:56])

        decrypt_key = sha256(bytes(init[8:40][::-1]) + secret_bytes).digest()
        decrypt_iv = bytes(init[40:56][::-1])

        self._encrypter = AESModeCTR(encrypt_key, encrypt_iv)
        self._decrypter = AESModeCTR(decrypt_key, decrypt_iv)

        init[56:64] = self._encrypter.encrypt(bytes(init[56:64]))
        self._socket.sendall(bytes(init))

    def send(self, data: bytes) -> None:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")
        packet = struct.pack('<i', len(data)) + data
        self._socket.sendall(self._encrypter.encrypt(packet))

    def recv(self) -> bytes:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")
        encrypted_len = self._recv_exact(4)
        decrypted_len = self._decrypter.decrypt(encrypted_len)
        length = struct.unpack('<i', decrypted_len)[0]
        if length <= 0 or length > 2 * 1024 * 1024:
            raise ValueError(f"Invalid MTProxy packet length: {length}")
        encrypted_payload = self._recv_exact(length)
        return self._decrypter.decrypt(encrypted_payload)


class ConnectionTcpMTProxyAbridged(ConnectionTcpMTProxyIntermediate):
    """MTProxy with Abridged protocol tag (0xef)."""
    pass


class ConnectionTcpMTProxyRandomizedIntermediate(ConnectionTcpMTProxyIntermediate):
    """MTProxy with Randomized Intermediate protocol."""
    pass
