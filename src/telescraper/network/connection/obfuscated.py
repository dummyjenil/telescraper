"""Obfuscated2 Transport (AES-128-CTR stream cipher to bypass DPI)."""

import os
import struct
from typing import Optional

from ...crypto.aesctr import AESModeCTR
from .base import SyncConnection


class ConnectionTcpObfuscated(SyncConnection):
    """
    Obfuscated2 Transport:
    Wraps TCP traffic in a random 64-byte handshake + bidirectional AES-128-CTR encryption.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._encrypter: Optional[AESModeCTR] = None
        self._decrypter: Optional[AESModeCTR] = None

    def _send_handshake(self) -> None:
        while True:
            init = bytearray(os.urandom(64))
            # Validate forbidden prefixes
            val = (init[0] << 24) | (init[1] << 16) | (init[2] << 8) | init[3]
            if (
                init[0] != 0xEF
                and val != 0x48454144  # HEAD
                and val != 0x504F5354  # POST
                and val != 0x47455420  # GET
                and val != 0xEEEEEEEE
                and val != 0xDDDDDDDD
                and val != 0x00000000
            ):
                break

        # Intermediate transport tag (0xeeeeevee) embedded in bytes 56..60
        init[56] = 0xEE
        init[57] = 0xEE
        init[58] = 0xEE
        init[59] = 0xEE

        encrypt_key = bytes(init[8:40])
        encrypt_iv = bytes(init[40:56])

        decrypt_key = bytes(init[8:40][::-1])
        decrypt_iv = bytes(init[40:56][::-1])

        self._encrypter = AESModeCTR(encrypt_key, encrypt_iv)
        self._decrypter = AESModeCTR(decrypt_key, decrypt_iv)

        # Encrypt last 8 bytes of handshake
        init[56:64] = self._encrypter.encrypt(bytes(init[56:64]))
        self._socket.sendall(bytes(init))

    def send(self, data: bytes) -> None:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")
        packet = struct.pack("<i", len(data)) + data
        encrypted = self._encrypter.encrypt(packet)
        self._socket.sendall(encrypted)

    def recv(self) -> bytes:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")
        encrypted_len = self._recv_exact(4)
        decrypted_len = self._decrypter.decrypt(encrypted_len)
        length = struct.unpack("<i", decrypted_len)[0]
        if length <= 0 or length > 2 * 1024 * 1024:
            raise ValueError(f"Invalid Obfuscated packet length: {length}")

        encrypted_payload = self._recv_exact(length)
        return self._decrypter.decrypt(encrypted_payload)
