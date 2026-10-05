"""
Multi-DC Persistent Synchronous Sender Pool.
Maintains persistent SyncMTProtoSender connections to foreign Telegram Data Centers (DC 1-5)
and manages transparent cross-DC authorization export and import.
100% Pure Synchronous, Zero Asyncio.
"""

import threading
from typing import Dict, Optional, Any, Type
from .connection import SyncConnection, ConnectionTcpIntermediate
from .mtproto_sender import SyncMTProtoSender
from .authenticator import do_authentication
from ..tl import functions, types


class SyncSenderPool:
    """
    Manages persistent synchronous MTProto connections to different Telegram Data Centers.
    """

    # Telegram DC default IP addresses
    DC_ADDRESSES = {
        1: ("149.154.175.53", 443),
        2: ("149.154.167.51", 443),
        3: ("149.154.175.100", 443),
        4: ("149.154.167.91", 443),
        5: ("91.108.56.130", 443),
    }

    def __init__(
        self,
        main_client: Any,
        connection_class: Type[SyncConnection] = ConnectionTcpIntermediate,
        proxy: Optional[dict] = None
    ):
        self.main_client = main_client
        self.connection_class = connection_class
        self.proxy = proxy
        self._senders: Dict[int, SyncMTProtoSender] = {}
        self._lock = threading.Lock()

    def get_sender(self, dc_id: int) -> SyncMTProtoSender:
        """
        Get or establish an authenticated SyncMTProtoSender for the given DC ID.
        Exports authorization from the primary DC if not already authenticated.
        """
        with self._lock:
            if dc_id in self._senders:
                sender = self._senders[dc_id]
                if sender.is_connected:
                    return sender

            if dc_id not in self.DC_ADDRESSES:
                raise ValueError(f"Unknown Telegram Data Center DC {dc_id}")

            ip, port = self.DC_ADDRESSES[dc_id]
            conn = self.connection_class(ip, port, proxy=self.proxy)
            conn.connect()

            auth_key = do_authentication(conn)
            sender = SyncMTProtoSender(auth_key, conn)
            sender.connect()

            # Export authorization from main client if main client is logged in
            if self.main_client and hasattr(self.main_client, "_sender") and self.main_client._sender:
                try:
                    exported_auth = self.main_client._invoke(
                        functions.auth.ExportAuthorizationRequest(dc_id=dc_id)
                    )
                    sender.invoke(
                        functions.auth.ImportAuthorizationRequest(
                            id=exported_auth.id,
                            bytes=exported_auth.bytes
                        )
                    )
                except Exception:
                    # Anonymous or download-only DC authorization
                    pass

            self._senders[dc_id] = sender
            return sender

    def close_all(self):
        """Disconnect all pooled senders."""
        with self._lock:
            for dc_id, sender in list(self._senders.items()):
                try:
                    sender.disconnect()
                except Exception:
                    pass
            self._senders.clear()
