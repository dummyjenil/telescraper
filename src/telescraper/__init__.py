"""
TeleScraper - 100% Pure Synchronous Telegram MTProto Client & Scraping Suite.
Zero asyncio, pure blocking sockets.
"""

from .client import TeleScraper
from .models import ChatData, MessageData, MediaInfo, MemberData
from .downloader import download_media_sync, download_media_sync as download_message_media
from .parallel_downloader import download_file_parallel_sync
from .uploader import upload_file_sync
from .exporter import (
    export_to_json,
    export_to_csv,
    export_to_excel,
    export_to_sqlite,
    to_dataframe,
)
from .extractor import extract_data
from .checkpoint import ScrapeCheckpoint
from .admin import AdminManager
from .sessions.string_session import StringSession
from .sessions.session import SyncSession
from .auth_qr import QRLogin
from .cli import main as cli_main
from .tui import TelegramApp, run_tui
from .takeout import TakeoutSession
from .secret_chat import SecretChat
from .media_utils import resize_image_sync, inspect_media_metadata
from .network.connection import (
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
)
from .exceptions import (
    TeleScraperError,
    AuthenticationError,
    TargetNotFoundError,
    DownloadError
)

__version__ = "0.3.0"

__all__ = [
    "TeleScraper",
    "ChatData",
    "MessageData",
    "MediaInfo",
    "MemberData",
    "StringSession",
    "SyncSession",
    "QRLogin",
    "TakeoutSession",
    "SecretChat",
    "AdminManager",
    "ScrapeCheckpoint",
    "extract_data",
    "download_media_sync",
    "download_message_media",
    "download_file_parallel_sync",
    "upload_file_sync",
    "export_to_json",
    "export_to_csv",
    "export_to_excel",
    "export_to_sqlite",
    "to_dataframe",
    "resize_image_sync",
    "inspect_media_metadata",
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
    "TeleScraperError",
    "AuthenticationError",
    "TargetNotFoundError",
    "DownloadError",
]
