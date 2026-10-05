"""Connection transports package."""

from .base import SyncConnection
from .full import ConnectionTcpFull
from .abridged import ConnectionTcpAbridged
from .intermediate import (
    ConnectionTcpIntermediate,
    ConnectionTcpRandomizedIntermediate,
)
from .obfuscated import ConnectionTcpObfuscated
from .mtproxy import (
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpMTProxyAbridged,
    ConnectionTcpMTProxyRandomizedIntermediate,
)
from .http import ConnectionHttp

# Alias for backward compatibility
SyncTcpIntermediateConnection = ConnectionTcpIntermediate

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
