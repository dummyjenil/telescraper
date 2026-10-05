"""Custom exceptions for TeleScraper."""


class TeleScraperError(Exception):
    """Base exception for all telescraper errors."""
    pass


class AuthenticationError(TeleScraperError):
    """Raised when Telegram login/authentication fails."""
    pass


class TargetNotFoundError(TeleScraperError):
    """Raised when a specified channel, group or user is not found."""
    pass


class DownloadError(TeleScraperError):
    """Raised when media downloading fails."""
    pass
