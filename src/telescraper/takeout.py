"""
Telegram Data Takeout Session.
Enables high-volume scraping and mass media downloading with reduced flood limits.
"""

from typing import Any, Generator, Optional, Union

from .exceptions import TeleScraperError
from .models import MessageData
from .tl import functions, types


class TakeoutSession:
    """
    Synchronous context manager for Telegram Takeout Session.
    """

    def __init__(
        self,
        client: Any,
        contacts: bool = True,
        message_users: bool = True,
        message_chats: bool = True,
        message_megagroups: bool = True,
        message_channels: bool = True,
        files: bool = True,
        max_file_size: Optional[int] = None,
    ):
        self._client = client
        self.contacts = contacts
        self.message_users = message_users
        self.message_chats = message_chats
        self.message_megagroups = message_megagroups
        self.message_channels = message_channels
        self.files = files
        self.max_file_size = max_file_size
        self.takeout_id: Optional[int] = None

    def __enter__(self) -> "TakeoutSession":
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.finish(success=(exc_type is None))

    def init(self) -> None:
        """Initialize the takeout session with Telegram servers."""
        res = self._client._invoke(
            functions.account.InitTakeoutSessionRequest(
                contacts=self.contacts,
                message_users=self.message_users,
                message_chats=self.message_chats,
                message_megagroups=self.message_megagroups,
                message_channels=self.message_channels,
                files=self.files,
                file_max_size=self.max_file_size,
            )
        )
        if isinstance(res, types.account.Takeout):
            self.takeout_id = res.id
            print(f"[✔] Takeout Session initialized (ID: {self.takeout_id})")
        else:
            raise TeleScraperError(f"Unexpected response initializing takeout: {res}")

    def finish(self, success: bool = True) -> None:
        """Finish and close the takeout session."""
        if self.takeout_id:
            try:
                flags = 1 if success else 0
                self._client._invoke(functions.account.FinishTakeoutSessionRequest(flags=flags))
                print(f"[✔] Takeout Session {self.takeout_id} finalized.")
            except Exception:
                pass
            self.takeout_id = None

    def _invoke(self, request: Any) -> Any:
        """Wraps any request in InvokeWithTakeoutRequest."""
        if not self.takeout_id:
            raise TeleScraperError("Takeout session is not active.")
        wrapped = functions.InvokeWithTakeoutRequest(takeout_id=self.takeout_id, query=request)
        return self._client._invoke(wrapped)

    def iter_messages(
        self, target: Union[str, int], limit: Optional[int] = None, **kwargs
    ) -> Generator[MessageData, None, None]:
        """Scrape messages using high-throughput takeout session."""
        peer = self._client._resolve_target(target)
        offset_id = 0
        chunk_size = 100
        yielded = 0

        while True:
            fetch_count = chunk_size if limit is None else min(chunk_size, limit - yielded)
            if fetch_count <= 0:
                break

            req = functions.messages.GetHistoryRequest(
                peer=peer,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=fetch_count,
                max_id=0,
                min_id=0,
                hash=0,
            )
            res = self._invoke(req)
            messages = getattr(res, "messages", [])
            if not messages:
                break

            for raw_msg in messages:
                if isinstance(raw_msg, types.Message):
                    yield self._client._parse_message(raw_msg)
                    yielded += 1
                    if limit and yielded >= limit:
                        return

            offset_id = messages[-1].id
            if len(messages) < fetch_count:
                break
