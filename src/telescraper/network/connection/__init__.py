"""Connection transports package."""

from .abridged import ConnectionTcpAbridged
from .base import SyncConnection
from .full import ConnectionTcpFull
from .http import ConnectionHttp
from .intermediate import (
    ConnectionTcpIntermediate,
    ConnectionTcpRandomizedIntermediate,
)
from .mtproxy import (
    ConnectionTcpMTProxyAbridged,
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpMTProxyRandomizedIntermediate,
)
from .obfuscated import ConnectionTcpObfuscated

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
