"""TCP Full Transport (12-byte header + CRC32)."""

import struct
import zlib
from .base import SyncConnection


class ConnectionTcpFull(SyncConnection):
    """
    Default MTProto TCP Full connection framing:
    - 4 bytes: total packet length (including header & CRC32)
    - 4 bytes: sequence number
    - N bytes: payload
    - 4 bytes: CRC32 checksum of above data
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._send_seq = 0
        self._recv_seq = 0

    def send(self, data: bytes) -> None:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")

        # total length = 4 (length) + 4 (seq) + len(data) + 4 (crc32)
        total_len = len(data) + 12
        packet = struct.pack('<ii', total_len, self._send_seq) + data
        crc = struct.pack('<I', zlib.crc32(packet))
        self._send_seq += 1
        self._socket.sendall(packet + crc)

    def recv(self) -> bytes:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")

        header = self._recv_exact(8)
        total_len, seq = struct.unpack('<ii', header)
        if total_len <= 12 or total_len > 2 * 1024 * 1024:
            raise ValueError(f"Invalid TCP Full packet length: {total_len}")

        payload_len = total_len - 12
        payload = self._recv_exact(payload_len)
        expected_crc = struct.unpack('<I', self._recv_exact(4))[0]

        computed_crc = zlib.crc32(header + payload)
        if computed_crc != expected_crc:
            raise ValueError(f"CRC32 mismatch in TCP Full: {computed_crc} != {expected_crc}")

        self._recv_seq += 1
        return payload
