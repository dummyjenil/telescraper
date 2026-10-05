"""Re-export all connection classes for backward compatibility."""

from .connection import (
    SyncConnection,
    ConnectionTcpFull,
    ConnectionTcpAbridged,
    ConnectionTcpIntermediate,
    ConnectionTcpRandomizedIntermediate,
    ConnectionTcpObfuscated,
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpMTProxyAbridged,
    ConnectionTcpMTProxyRandomizedIntermediate,
    ConnectionHttp,
    SyncTcpIntermediateConnection,
)

__all__ = [
    "SyncConnection",
    "ConnectionTcpFull",
    "ConnectionTcpAbridged",
    "ConnectionTcpIntermediate",
    "ConnectionTcpRandomizedIntermediate",
    "ConnectionTcpObfuscated",
    "ConnectionTcpMTProxyIntermediate",
    "ConnectionTcpMTProxyAbridged",
    "ConnectionTcpMTProxyRandomizedIntermediate",
    "ConnectionHttp",
    "SyncTcpIntermediateConnection",
]
