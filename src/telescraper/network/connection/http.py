"""HTTP Transport Fallback."""

import struct
from .base import SyncConnection


class ConnectionHttp(SyncConnection):
    """
    MTProto HTTP transport:
    Sends serialized MTProto payload wrapped in standard HTTP POST request.
    """

    def send(self, data: bytes) -> None:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")

        http_req = (
            f"POST /api HTTP/1.1\r\n"
            f"Host: {self.ip}\r\n"
            f"Content-Type: application/x-binary\r\n"
            f"Content-Length: {len(data)}\r\n"
            f"Connection: keep-alive\r\n\r\n"
        ).encode('latin-1') + data
        self._socket.sendall(http_req)

    def recv(self) -> bytes:
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")

        # Read HTTP headers
        header_data = bytearray()
        while b'\r\n\r\n' not in header_data:
            chunk = self._socket.recv(1)
            if not chunk:
                raise ConnectionResetError("HTTP connection closed while reading headers")
            header_data.extend(chunk)

        headers_text = bytes(header_data).decode('latin-1', errors='ignore')
        content_length = 0
        for line in headers_text.split('\r\n'):
            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':')[1].strip())
                break

        if content_length <= 0:
            raise ValueError("Invalid HTTP response content length")

        return self._recv_exact(content_length)
