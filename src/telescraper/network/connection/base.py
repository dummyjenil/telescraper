"""Base synchronous TCP connection class."""

import socket
import ssl
from typing import Optional, Tuple


class SyncConnection:
    """Base synchronous connection over standard blocking TCP socket."""

    def __init__(
        self,
        ip: str,
        port: int,
        timeout: float = 20.0,
        proxy: Optional[Tuple[str, int]] = None
    ):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.proxy = proxy
        self._socket: Optional[socket.socket] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._socket is not None

    def connect(self) -> None:
        """Create socket and perform initial transport handshake."""
        if self._connected:
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.ip, self.port))
            self._socket = sock
            self._connected = True
            self._send_handshake()
        except Exception as e:
            self.close()
            raise ConnectionError(f"Failed to connect to {self.ip}:{self.port}: {e}") from e

    def _send_handshake(self) -> None:
        """Subclasses can send transport header bytes."""
        pass

    def send(self, data: bytes) -> None:
        """Encode and send framed packet."""
        raise NotImplementedError

    def recv(self) -> bytes:
        """Read and decode framed packet."""
        raise NotImplementedError

    def _recv_exact(self, n: int) -> bytes:
        """Read exactly n bytes from the socket."""
        if not self._connected or not self._socket:
            raise ConnectionError("Socket is not connected")
        data = bytearray()
        while len(data) < n:
            chunk = self._socket.recv(n - len(data))
            if not chunk:
                raise ConnectionResetError("Telegram server closed the connection")
            data.extend(chunk)
        return bytes(data)

    def close(self) -> None:
        """Close the socket connection."""
        self._connected = False
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
