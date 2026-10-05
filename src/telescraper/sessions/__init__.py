"""Session modules for TeleScraper."""

from .session import SyncSession
from .string_session import StringSession

__all__ = ["SyncSession", "StringSession"]
