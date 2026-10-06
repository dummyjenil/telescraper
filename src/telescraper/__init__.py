"""
TeleScraper - 100% Pure Synchronous Telegram MTProto Client & Scraping Suite.
Zero asyncio, pure blocking sockets.
"""

from .admin import AdminManager
from .auth_qr import QRLogin
from .checkpoint import ScrapeCheckpoint
from .cli import main as cli_main
from .client import TeleScraper
from .downloader import download_media_sync
from .downloader import download_media_sync as download_message_media
from .exceptions import AuthenticationError, DownloadError, TargetNotFoundError, TeleScraperError
from .exporter import (
    export_to_csv,
    export_to_excel,
    export_to_json,
    export_to_sqlite,
    to_dataframe,
)
from .extractor import extract_data
from .media_utils import inspect_media_metadata, resize_image_sync
from .models import ChatData, MediaInfo, MemberData, MessageData
from .network.connection import (
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
)
from .parallel_downloader import download_file_parallel_sync
from .secret_chat import SecretChat
from .sessions.session import SyncSession
from .sessions.string_session import StringSession
from .takeout import TakeoutSession
from .tui import TelegramApp, run_tui
from .uploader import upload_file_sync

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
