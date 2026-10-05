"""
StringSession - Export and Import Telegram sessions as Base64 strings.
100% compatible with Telethon StringSessions.
"""

import base64
import ipaddress
import struct
from typing import Optional
from ..crypto import AuthKey

_STRUCT_PREFORMAT = '>B{}sH256s'
CURRENT_VERSION = '1'


class StringSession:
    """
    In-memory session loaded and saved as a compact base64 string.
    No SQLite disk file required.
    """

    def __init__(self, string: Optional[str] = None):
        self.dc_id = 2
        self.server_address = "149.154.167.50"
        self.port = 443
        self.auth_key: Optional[AuthKey] = None
        self.user_id: Optional[int] = None

        if string:
            self._load_from_string(string)

    def _load_from_string(self, string: str) -> None:
        string = string.strip()
        if not string:
            return

        if string[0] != CURRENT_VERSION:
            raise ValueError(f'Unsupported string session version: {string[0]}')

        encoded = string[1:]
        decoded = base64.urlsafe_b64decode(encoded.encode('ascii') + b'==')
        ip_len = 4 if len(decoded) == 263 else 16

        self.dc_id, ip, self.port, key = struct.unpack(
            _STRUCT_PREFORMAT.format(ip_len), decoded
        )

        self.server_address = ipaddress.ip_address(ip).compressed
        if any(key):
            self.auth_key = AuthKey(key)

    def save(self) -> str:
        """Export session data into a portable Base64 string."""
        if not self.auth_key:
            return ''

        ip = ipaddress.ip_address(self.server_address).packed
        packed = struct.pack(
            _STRUCT_PREFORMAT.format(len(ip)),
            self.dc_id,
            ip,
            self.port,
            self.auth_key.key
        )
        return CURRENT_VERSION + base64.urlsafe_b64encode(packed).decode('ascii').rstrip('=')

    def set_dc(self, dc_id: int, server_address: str, port: int) -> None:
        self.dc_id = dc_id
        self.server_address = server_address
        self.port = port

    def set_auth_key(self, auth_key: Optional[AuthKey]) -> None:
        self.auth_key = auth_key
