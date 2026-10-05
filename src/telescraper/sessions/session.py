"""Session storage for saving DC credentials and AuthKeys to disk."""

import sqlite3
import os
from typing import Optional
from ..crypto import AuthKey


DEFAULT_DC_IP = "149.154.167.50"
DEFAULT_DC_PORT = 443
DEFAULT_DC_ID = 2


class SyncSession:
    """
    SQLite-backed synchronous session storage.
    Compatible with standard Telegram sessions.
    """

    def __init__(self, session_path: str):
        if not session_path.endswith('.session'):
            session_path += '.session'
        self.filename = session_path
        self.dc_id = DEFAULT_DC_ID
        self.server_address = DEFAULT_DC_IP
        self.port = DEFAULT_DC_PORT
        self.auth_key: Optional[AuthKey] = None
        self.user_id: Optional[int] = None
        self._load()

    def _load(self) -> None:
        """Load session from SQLite database."""
        if not os.path.exists(self.filename):
            return

        try:
            conn = sqlite3.connect(self.filename)
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS sessions (dc_id INTEGER, server_address TEXT, port INTEGER, auth_key BLOB, user_id INTEGER)")
            row = c.execute("SELECT dc_id, server_address, port, auth_key, user_id FROM sessions LIMIT 1").fetchone()
            if row:
                self.dc_id = row[0] or DEFAULT_DC_ID
                self.server_address = row[1] or DEFAULT_DC_IP
                self.port = row[2] or DEFAULT_DC_PORT
                if row[3]:
                    self.auth_key = AuthKey(data=row[3])
                self.user_id = row[4]
            conn.close()
        except Exception:
            pass

    def save(self) -> None:
        """Save session state to SQLite database."""
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS sessions (dc_id INTEGER, server_address TEXT, port INTEGER, auth_key BLOB, user_id INTEGER)")
        c.execute("DELETE FROM sessions")
        auth_bytes = self.auth_key.key if self.auth_key else None
        c.execute(
            "INSERT INTO sessions (dc_id, server_address, port, auth_key, user_id) VALUES (?, ?, ?, ?, ?)",
            (self.dc_id, self.server_address, self.port, auth_bytes, self.user_id)
        )
        conn.commit()
        conn.close()

    def set_dc(self, dc_id: int, server_address: str, port: int) -> None:
        self.dc_id = dc_id
        self.server_address = server_address
        self.port = port
        self.save()

    def set_auth_key(self, auth_key: AuthKey) -> None:
        self.auth_key = auth_key
        self.save()
