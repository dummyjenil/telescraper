"""TCP Intermediate & Randomized Intermediate Transports."""

import os
import random
import struct
from .base import SyncConnection


class ConnectionTcpIntermediate(SyncConnection):
    """
    MTProto TCP Intermediate connection framing:
    - Initial connection sends 4-byte handshake `b'\xee\xee\xee\xee'`
    - Packets are prefixed with 4-byte length (`<i`)
    """

    def _send_handshake(self) -> None:
        if self._socket:
            self._socket.sendall(b'\xee\xee\xee\xee')

    def send(self, data: bytes) -> None:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")
        packet = struct.pack('<i', len(data)) + data
        self._socket.sendall(packet)

    def recv(self) -> bytes:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")
        length = struct.unpack('<i', self._recv_exact(4))[0]
        if length <= 0 or length > 2 * 1024 * 1024:
            raise ValueError(f"Invalid TCP Intermediate packet length: {length}")
        return self._recv_exact(length)


class ConnectionTcpRandomizedIntermediate(ConnectionTcpIntermediate):
    """
    Intermediate transport with 0 to 3 random padding bytes aligned to 4 bytes.
    Used for MTProxies and obfuscation.
    """

    def send(self, data: bytes) -> None:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")
        pad_size = random.randint(0, 3)
        padding = os.urandom(pad_size)
        packet = struct.pack('<i', len(data) + pad_size) + data + padding
        self._socket.sendall(packet)

    def recv(self) -> bytes:
        packet_with_padding = super().recv()
        pad_size = len(packet_with_padding) % 4
        if pad_size > 0:
            return packet_with_padding[:-pad_size]
        return packet_with_padding
