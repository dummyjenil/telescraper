"""Data models representing channels, groups, messages, members and media."""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Any, Dict, Callable


@dataclass
class MediaInfo:
    """Detailed information about an attached media item."""
    media_type: str  # 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'web_page', 'other'
    file_name: Optional[str] = None
    file_size: Optional[int] = None  # in bytes
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None  # in seconds

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChatData:
    """Information about a Telegram channel or group."""
    id: int
    title: str
    username: Optional[str] = None
    is_channel: bool = False
    is_group: bool = False
    is_megagroup: bool = False
    participants_count: Optional[int] = None
    description: Optional[str] = None
    raw_chat: Any = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop('raw_chat', None)
        return data


@dataclass
class MemberData:
    """Information about a Telegram chat member or contact."""
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_bot: bool = False
    is_contact: bool = False
    mutual_contact: bool = False
    status: Optional[str] = None
    last_seen: Optional[datetime] = None
    last_seen_time: Optional[float] = None
    raw_user: Any = field(default=None, repr=False)

    @property
    def user_id(self) -> int:
        return self.id

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join([p for p in parts if p]).strip()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop('raw_user', None)
        data['full_name'] = self.full_name
        return data


@dataclass
class MessageData:
    """Clean structured data of a scraped Telegram message."""
    id: int
    chat_id: int
    chat_title: Optional[str]
    date: datetime
    text: str
    sender_id: Optional[int] = None
    sender_name: Optional[str] = None
    views: Optional[int] = None
    forwards: Optional[int] = None
    reply_to_msg_id: Optional[int] = None
    is_reply: bool = False
    has_media: bool = False
    media: Optional[MediaInfo] = None
    raw_message: Any = field(default=None, repr=False)
    _downloader_fn: Optional[Callable[..., str]] = field(default=None, repr=False)

    def download(
        self,
        output_dir: str = "./downloads",
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[str]:
        """Download this message's attached media directly."""
        if not self.has_media or not self._downloader_fn:
            return None
        return self._downloader_fn(
            message=self.raw_message,
            output_dir=output_dir,
            filename=filename,
            progress_callback=progress_callback
        )

    def extract_data(self) -> Dict[str, Any]:
        """Extract emails, phones, URLs, mentions, and crypto wallets from this message."""
        from .extractor import extract_data
        return extract_data(self.text)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop('raw_message', None)
        data.pop('_downloader_fn', None)
        if isinstance(data.get('date'), datetime):
            data['date'] = data['date'].isoformat()
        if self.media:
            data['media'] = self.media.to_dict()
        return data
