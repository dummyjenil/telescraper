"""TCP Abridged Transport (0xef header + compact length)."""

import struct

from .base import SyncConnection


class ConnectionTcpAbridged(SyncConnection):
    """
    MTProto TCP Abridged connection framing:
    - Initial connection sends 1-byte handshake `b'\xef'`
    - Packets with length < 127 4-byte words send 1-byte length (`len(data) // 4`)
    - Packets >= 127 words send `b'\x7f'` + 3-byte length
    """

    def _send_handshake(self) -> None:
        if self._socket:
            self._socket.sendall(b"\xef")

    def send(self, data: bytes) -> None:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")

        length = len(data) // 4
        if length < 127:
            header = struct.pack("B", length)
        else:
            header = b"\x7f" + struct.pack("<I", length)[:3]

        self._socket.sendall(header + data)

    def recv(self) -> bytes:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")

        first_byte = self._recv_exact(1)[0]
        if first_byte < 127:
            length = first_byte * 4
        else:
            length = struct.unpack("<I", self._recv_exact(3) + b"\x00")[0] * 4

        return self._recv_exact(length)
