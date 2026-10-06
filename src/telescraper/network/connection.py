"""Re-export all connection classes for backward compatibility."""

from .connection import (
    ConnectionHttp,
    ConnectionTcpAbridged,
    ConnectionTcpFull,
    ConnectionTcpIntermediate,
    ConnectionTcpMTProxyAbridged,
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpMTProxyRandomizedIntermediate,
    ConnectionTcpObfuscated,
    ConnectionTcpRandomizedIntermediate,
    SyncConnection,
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
