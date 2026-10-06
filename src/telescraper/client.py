"""
Pure Synchronous Telegram Client.
Full-featured: Scraping, Media Downloader/Uploader, Transports, Moderation, QR Login, Takeout, Discussion Comments.
100% Pure Blocking Sockets, Zero Asyncio.
"""

import getpass
import mimetypes
import os
from typing import Any, Callable, Dict, Generator, List, Optional, Type, Union

from .admin import AdminManager
from .auth_qr import QRLogin
from .checkpoint import ScrapeCheckpoint
from .contacts import ContactsManager
from .downloader import download_media_sync
from .errors import (
    ConnectionNotInitedError,
    FileMigrateError,
    PhoneMigrateError,
    RPCError,
    SessionPasswordNeededError,
    UserMigrateError,
)
from .exceptions import AuthenticationError, TargetNotFoundError
from .exporter import (
    export_to_csv,
    export_to_excel,
    export_to_json,
    export_to_sqlite,
    to_dataframe,
)
from .extractor import extract_data
from .helpers import generate_random_long
from .models import ChatData, MediaInfo, MemberData, MessageData
from .network.authenticator import do_authentication
from .network.connection import (
    ConnectionTcpIntermediate,
    SyncConnection,
)
from .network.mtproto_sender import SyncMTProtoSender
from .network.mtprotoplainsender import SyncMTProtoPlainSender
from .network.sender_pool import SyncSenderPool
from .parallel_downloader import download_file_parallel_sync
from .secret_chat import SecretChat
from .sessions.session import SyncSession
from .sessions.string_session import StringSession
from .sync_engine import SyncUpdateEngine, UpdateSyncState
from .takeout import TakeoutSession
from .tl import functions, types
from .tl.types import (
    Channel,
    ChannelParticipantsRecent,
    Chat,
    CodeSettings,
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    InputChannel,
    InputMediaUploadedDocument,
    InputMediaUploadedPhoto,
    InputPeerChannel,
    InputPeerChat,
    InputPeerEmpty,
    InputPeerSelf,
    InputPeerUser,
    InputUser,
    MessageMediaDocument,
    MessageMediaPhoto,
    MessageMediaWebPage,
    ReactionEmoji,
)
from .uploader import upload_file_sync
from .utils import get_display_name, get_input_user
from .voip import VoIPSignalling

DC_ADDRESSES = {
    1: ("149.154.175.53", 443),
    2: ("149.154.167.50", 443),
    3: ("149.154.175.100", 443),
    4: ("149.154.167.91", 443),
    5: ("91.108.56.130", 443),
}

FILTER_MAP = {
    "photos": types.InputMessagesFilterPhotos,
    "photo": types.InputMessagesFilterPhotos,
    "videos": types.InputMessagesFilterVideo,
    "video": types.InputMessagesFilterVideo,
    "documents": types.InputMessagesFilterDocument,
    "document": types.InputMessagesFilterDocument,
    "audio": types.InputMessagesFilterMusic,
    "music": types.InputMessagesFilterMusic,
    "voice": types.InputMessagesFilterVoice,
    "urls": types.InputMessagesFilterUrl,
    "links": types.InputMessagesFilterUrl,
    "round_videos": types.InputMessagesFilterRoundVideo,
    "gifs": types.InputMessagesFilterGif,
    "pinned": types.InputMessagesFilterPinned,
}


class TeleScraper:
    """
    Pure Synchronous Telegram MTProto Client.
    """

    def __init__(
        self,
        session: Union[str, StringSession, SyncSession] = "telescraper",
        api_id: int = 0,
        api_hash: str = "",
        phone: Optional[str] = None,
        proxy: Optional[tuple] = None,
        connection: Type[SyncConnection] = ConnectionTcpIntermediate,
        connection_kwargs: Optional[dict] = None,
    ):
        if isinstance(session, (StringSession, SyncSession)):
            self.session = session
        elif isinstance(session, str) and (len(session) > 100 or session.startswith("1")):
            self.session = StringSession(session)
        else:
            self.session = SyncSession(session if isinstance(session, str) else "telescraper")

        self.api_id = int(api_id) if api_id else 0
        self.api_hash = str(api_hash)
        self.phone = phone
        self.proxy = proxy
        self.connection_class = connection
        self.connection_kwargs = connection_kwargs or {}

        self.device_model = "Desktop"
        self.system_version = "Linux"
        self.app_version = "1.0.0"
        self.lang_code = "en"
        self.system_lang_code = "en"
        self._init_connection_done = False

        self._connection: Optional[SyncConnection] = None
        self._sender: Optional[SyncMTProtoSender] = None
        self._admin = AdminManager(self)
        self._contacts = ContactsManager(self)
        self._sender_pool: Optional[SyncSenderPool] = None
        self._sync_engine = SyncUpdateEngine(self)
        self._voip = VoIPSignalling(self)

    @property
    def contacts(self) -> ContactsManager:
        """Contacts manager for Telegram contacts, address book, search and blocking."""
        return self._contacts

    @property
    def is_connected(self) -> bool:
        return self._sender is not None and self._connection is not None and self._connection.is_connected

    @property
    def sender_pool(self) -> SyncSenderPool:
        """Get or initialize the Multi-DC Sender Pool."""
        if self._sender_pool is None:
            self._sender_pool = SyncSenderPool(
                main_client=self, connection_class=self.connection_class, proxy=self.proxy
            )
        return self._sender_pool

    @property
    def sync_engine(self) -> SyncUpdateEngine:
        """State sync and update difference engine."""
        return self._sync_engine

    @property
    def voip(self) -> VoIPSignalling:
        """VoIP and video call signalling manager."""
        return self._voip

    def connect(self) -> "TeleScraper":
        """Connect to Telegram data center and perform handshake if needed."""
        if self.is_connected:
            return self

        ip = self.session.server_address
        port = self.session.port

        self._connection = self.connection_class(ip, port, proxy=self.proxy, **self.connection_kwargs)
        self._connection.connect()

        # DH Handshake if AuthKey not created yet
        if not self.session.auth_key:
            plain_sender = SyncMTProtoPlainSender(self._connection)
            auth_key, time_offset = do_authentication(plain_sender)
            self.session.set_auth_key(auth_key)

        self._sender = SyncMTProtoSender(self._connection, self.session.auth_key)
        return self

    def disconnect(self) -> None:
        """Close connection and any open foreign DC pooled senders."""
        self._init_connection_done = False
        if self._sender_pool:
            self._sender_pool.close_all()
            self._sender_pool = None
        if self._connection:
            self._connection.close()
            self._connection = None
        self._sender = None

    def __enter__(self) -> "TeleScraper":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def _init_request(self, query: Any) -> Any:
        from .tl.alltlobjects import LAYER

        return functions.InvokeWithLayerRequest(
            layer=LAYER,
            query=functions.InitConnectionRequest(
                api_id=self.api_id,
                device_model=self.device_model,
                system_version=self.system_version,
                app_version=self.app_version,
                system_lang_code=self.system_lang_code,
                lang_pack="",
                lang_code=self.lang_code,
                query=query,
            ),
        )

    def _invoke(self, request: Any, dc_id: Optional[int] = None) -> Any:
        """Execute MTProto request with automatic DC migration handling."""
        if not self.is_connected:
            self.connect()

        req_to_send = request
        if not self._init_connection_done:
            req_to_send = self._init_request(request)

        try:
            res = self._sender.send(req_to_send)
            self._init_connection_done = True
            return res
        except ConnectionNotInitedError:
            self._init_connection_done = False
            req_to_send = self._init_request(request)
            res = self._sender.send(req_to_send)
            self._init_connection_done = True
            return res
        except (UserMigrateError, PhoneMigrateError, FileMigrateError) as e:
            target_dc = e.new_dc
            self._switch_dc(target_dc)
            return self._invoke(request)

    def _switch_dc(self, new_dc_id: int) -> None:
        """Migrate to another Telegram DC."""
        self.disconnect()
        self._init_connection_done = False
        ip, port = DC_ADDRESSES.get(new_dc_id, ("149.154.167.50", 443))
        self.session.set_dc(new_dc_id, ip, port)
        self.session.set_auth_key(None)
        self.connect()

    # -------------------------------------------------------------------------
    # Authentication & QR Login
    # -------------------------------------------------------------------------

    def is_user_authorized(self) -> bool:
        """Check if logged in."""
        if not self.is_connected:
            self.connect()
        try:
            res = self._invoke(functions.users.GetUsersRequest(id=[types.InputUserSelf()]))
            return bool(res and not isinstance(res[0], types.UserEmpty))
        except RPCError:
            return False

    def bot_login(self, bot_token: str) -> "TeleScraper":
        """
        Authenticate as a Telegram bot using a Bot Token from @BotFather.
        """
        self.connect()
        res = self._invoke(
            functions.auth.ImportBotAuthorizationRequest(
                flags=0, api_id=self.api_id, api_hash=self.api_hash, bot_auth_token=bot_token
            )
        )
        user = res.user
        self.session.user_id = user.id
        if hasattr(self.session, "save"):
            self.session.save()
        print(f"[✔] Logged in as Bot @{getattr(user, 'username', 'bot')} (ID: {user.id})")
        return self

    def start(
        self,
        phone: Optional[str] = None,
        bot_token: Optional[str] = None,
        code_callback: Optional[Callable[[], str]] = None,
        password_callback: Optional[Callable[[], str]] = None,
    ) -> "TeleScraper":
        """Start client and authenticate with OTP code or bot token interactively."""
        self.connect()
        if bot_token:
            return self.bot_login(bot_token)

        if self.is_user_authorized():
            return self

        phone_number = phone or self.phone
        if not phone_number:
            phone_number = input("Enter your phone number: ").strip()

        send_code_res = self._invoke(
            functions.auth.SendCodeRequest(
                phone_number=phone_number, api_id=self.api_id, api_hash=self.api_hash, settings=CodeSettings()
            )
        )

        phone_code_hash = send_code_res.phone_code_hash
        code = code_callback() if code_callback else input(f"Enter OTP code for {phone_number}: ").strip()

        try:
            sign_in_res = self._invoke(
                functions.auth.SignInRequest(
                    phone_number=phone_number, phone_code_hash=phone_code_hash, phone_code=code
                )
            )
            user = sign_in_res.user
            self.session.user_id = user.id
            if hasattr(self.session, "save"):
                self.session.save()
            print(f"[✔] Logged in as {get_display_name(user)} (ID: {user.id})")
            return self
        except SessionPasswordNeededError:
            pwd = password_callback() if password_callback else getpass.getpass("Enter 2FA Password: ")
            from . import password as pwd_mod

            pwd_info = self._invoke(functions.account.GetPasswordRequest())
            input_check = pwd_mod.compute_check(pwd_info, pwd)
            res = self._invoke(functions.auth.CheckPasswordRequest(password=input_check))
            user = res.user
            self.session.user_id = user.id
            if hasattr(self.session, "save"):
                self.session.save()
            print(f"[✔] Logged in with 2FA as {get_display_name(user)}")
            return self

    def get_authorizations(self) -> List[types.Authorization]:
        """Fetch all active authorized sessions and devices."""
        res = self._invoke(functions.account.GetAuthorizationsRequest())
        return res.authorizations

    def reset_authorizations(self) -> bool:
        """Terminate all other active sessions and logins except the current one."""
        return bool(self._invoke(functions.account.ResetAuthorizationsRequest()))

    def terminate_session(self, hash: int) -> bool:
        """Terminate a specific remote session by authorization hash."""
        return bool(self._invoke(functions.account.ResetAuthorizationRequest(hash=hash)))

    def log_out(self) -> bool:
        """Log out of Telegram, invalidating the session auth key."""
        try:
            res = self._invoke(functions.auth.LogOutRequest())
        except Exception:
            res = True
        if hasattr(self.session, "set_auth_key"):
            self.session.set_auth_key(None)
        if hasattr(self.session, "save"):
            self.session.save()
        self.disconnect()
        return bool(res)

    def qr_login(self, print_qr: bool = True) -> QRLogin:
        """Initiate QR code desktop authentication."""
        self.connect()
        qr = QRLogin(self)
        if print_qr:
            qr.print_qr()
        return qr

    def takeout(self, **kwargs) -> TakeoutSession:
        """Start a Telegram Takeout Data Export Session."""
        self.connect()
        return TakeoutSession(self, **kwargs)

    def get_me(self) -> MemberData:
        """Get authenticated account profile."""
        res = self._invoke(functions.users.GetUsersRequest(id=[types.InputUserSelf()]))
        if not res:
            raise AuthenticationError("Not logged in")
        return self._parse_user(res[0])

    # -------------------------------------------------------------------------
    # Entity Resolution & Parsing
    # -------------------------------------------------------------------------

    def _resolve_target(self, target: Union[str, int]) -> Any:
        if isinstance(target, str):
            target_str = target.strip()
            if target_str.lower() in ("me", "self"):
                return InputPeerSelf()
            if target_str.startswith("@"):
                target_str = target_str[1:]
            if target_str.startswith("https://t.me/"):
                target_str = target_str.replace("https://t.me/", "")

            if target_str.lstrip("-").isdigit():
                return self._resolve_target(int(target_str))

            res = self._invoke(functions.contacts.ResolveUsernameRequest(username=target_str))
            if res.chats:
                chat = res.chats[0]
                if isinstance(chat, Channel):
                    return InputPeerChannel(channel_id=chat.id, access_hash=chat.access_hash)
                return InputPeerChat(chat_id=chat.id)
            elif res.users:
                user = res.users[0]
                return InputPeerUser(user_id=user.id, access_hash=user.access_hash)
            raise TargetNotFoundError(f"Username @{target_str} not found")

        elif isinstance(target, int):
            dialogs = self._invoke(
                functions.messages.GetDialogsRequest(
                    offset_date=None, offset_id=0, offset_peer=InputPeerEmpty(), limit=100, hash=0
                )
            )
            for chat in dialogs.chats:
                if chat.id == abs(target) or chat.id == target:
                    if isinstance(chat, Channel):
                        return InputPeerChannel(channel_id=chat.id, access_hash=chat.access_hash)
                    return InputPeerChat(chat_id=chat.id)
            for user in dialogs.users:
                if user.id == target:
                    return InputPeerUser(user_id=user.id, access_hash=user.access_hash)

            raise TargetNotFoundError(f"Chat/User ID {target} not found")

        return target

    def _parse_chat(self, entity: Any) -> ChatData:
        is_channel = isinstance(entity, Channel) and entity.broadcast
        is_megagroup = isinstance(entity, Channel) and entity.megagroup
        is_group = isinstance(entity, Chat) or is_megagroup

        return ChatData(
            id=entity.id,
            title=getattr(entity, "title", get_display_name(entity)),
            username=getattr(entity, "username", None),
            is_channel=is_channel,
            is_group=is_group,
            is_megagroup=is_megagroup,
            participants_count=getattr(entity, "participants_count", None),
            raw_chat=entity,
        )

    def _parse_user(self, user: Any) -> MemberData:
        st = getattr(user, "status", None)
        st_name = None
        last_seen_dt = None
        last_seen_score = 0.0

        if st:
            st_cls = type(st).__name__
            if st_cls == "UserStatusOnline":
                st_name = "Online"
                last_seen_score = float("inf")
            elif st_cls == "UserStatusOffline":
                dt = getattr(st, "was_online", None)
                if dt:
                    last_seen_dt = dt
                    last_seen_score = dt.timestamp() if hasattr(dt, "timestamp") else 0.0
                    st_name = f"Last seen {dt.strftime('%d %b %Y, %H:%M') if hasattr(dt, 'strftime') else dt}"
                else:
                    st_name = "Offline"
            elif st_cls == "UserStatusRecently":
                st_name = "Last seen recently"
                last_seen_score = 1000.0
            elif st_cls == "UserStatusLastWeek":
                st_name = "Last seen last week"
                last_seen_score = 500.0
            elif st_cls == "UserStatusLastMonth":
                st_name = "Last seen last month"
                last_seen_score = 100.0
            else:
                st_name = "Offline"

        return MemberData(
            id=user.id,
            username=getattr(user, "username", None),
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
            phone=getattr(user, "phone", None),
            is_bot=getattr(user, "bot", False),
            is_contact=getattr(user, "contact", False),
            mutual_contact=getattr(user, "mutual_contact", False),
            status=st_name,
            last_seen=last_seen_dt,
            last_seen_time=last_seen_score,
            raw_user=user,
        )

    def _parse_media(self, message: Any) -> Optional[MediaInfo]:
        if not message or not getattr(message, "media", None):
            return None

        media = message.media
        media_type = "other"
        file_name = None
        file_size = None
        mime_type = None
        width = None
        height = None
        duration = None

        if isinstance(media, MessageMediaPhoto):
            media_type = "photo"
            file_name = f"photo_{message.id}.jpg"
        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            media_type = "document"
            if doc:
                file_size = getattr(doc, "size", None)
                mime_type = getattr(doc, "mime_type", None)
                for attr in getattr(doc, "attributes", []):
                    if isinstance(attr, DocumentAttributeFilename):
                        file_name = attr.file_name
                    elif isinstance(attr, DocumentAttributeVideo):
                        media_type = "video"
                        duration = getattr(attr, "duration", None)
                        width = getattr(attr, "w", None)
                        height = getattr(attr, "h", None)
                    elif isinstance(attr, DocumentAttributeAudio):
                        media_type = "voice" if getattr(attr, "voice", False) else "audio"
                        duration = getattr(attr, "duration", None)
        elif isinstance(media, MessageMediaWebPage):
            media_type = "web_page"

        return MediaInfo(
            media_type=media_type,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            width=width,
            height=height,
            duration=duration,
        )

    def _parse_message(self, message: Any, chat_title: Optional[str] = None) -> MessageData:
        media_info = self._parse_media(message)
        reply_to_id = None
        if getattr(message, "reply_to", None):
            reply_to_id = getattr(message.reply_to, "reply_to_msg_id", None)

        return MessageData(
            id=message.id,
            chat_id=getattr(message.peer_id, "channel_id", None)
            or getattr(message.peer_id, "chat_id", None)
            or getattr(message.peer_id, "user_id", 0),
            chat_title=chat_title,
            date=message.date,
            text=getattr(message, "message", "") or "",
            sender_id=getattr(message.from_id, "user_id", None) if getattr(message, "from_id", None) else None,
            sender_name=None,
            views=getattr(message, "views", None),
            forwards=getattr(message, "forwards", None),
            reply_to_msg_id=reply_to_id,
            is_reply=bool(reply_to_id),
            has_media=bool(getattr(message, "media", None)),
            media=media_info,
            raw_message=message,
            _downloader_fn=lambda **kwargs: download_media_sync(self, **kwargs),
        )

    # -------------------------------------------------------------------------
    # Channel / Group / Dialogs
    # -------------------------------------------------------------------------

    def get_chats(self, types_filter: Optional[List[str]] = None) -> List[ChatData]:
        """Get all dialogs/chats."""
        res = self._invoke(
            functions.messages.GetDialogsRequest(
                offset_date=None, offset_id=0, offset_peer=InputPeerEmpty(), limit=100, hash=0
            )
        )
        chats = []
        for entity in res.chats:
            chat_data = self._parse_chat(entity)
            if types_filter:
                include = False
                if "channel" in types_filter and chat_data.is_channel:
                    include = True
                if "group" in types_filter and chat_data.is_group:
                    include = True
                if include:
                    chats.append(chat_data)
            else:
                chats.append(chat_data)
        return chats

    def get_chat_info(self, target: Union[str, int]) -> ChatData:
        """Get detailed chat information."""
        peer = self._resolve_target(target)
        if isinstance(peer, InputPeerChannel):
            input_channel = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
            full_ch = self._invoke(functions.channels.GetFullChannelRequest(channel=input_channel))
            chat_entity = full_ch.chats[0]
            chat_data = self._parse_chat(chat_entity)
            chat_data.description = full_ch.full_chat.about
            chat_data.participants_count = full_ch.full_chat.participants_count
            return chat_data
        elif isinstance(peer, InputPeerChat):
            full_chat = self._invoke(functions.messages.GetFullChatRequest(chat_id=peer.chat_id))
            chat_entity = full_chat.chats[0]
            chat_data = self._parse_chat(chat_entity)
            chat_data.description = full_chat.full_chat.about
            chat_data.participants_count = len(getattr(full_chat.full_chat.participants, "participants", []))
            return chat_data

        raise TargetNotFoundError(f"Could not get chat info for '{target}'")

    def iter_members(self, target: Union[str, int], limit: Optional[int] = None) -> Generator[MemberData, None, None]:
        """Iterate group/channel members."""
        peer = self._resolve_target(target)
        if not isinstance(peer, InputPeerChannel):
            raise TargetNotFoundError("Member scraping is only supported on channels/supergroups")

        input_channel = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
        offset = 0
        chunk_size = 100
        yielded = 0

        while True:
            fetch_count = chunk_size if limit is None else min(chunk_size, limit - yielded)
            if fetch_count <= 0:
                break

            res = self._invoke(
                functions.channels.GetParticipantsRequest(
                    channel=input_channel, filter=ChannelParticipantsRecent(), offset=offset, limit=fetch_count, hash=0
                )
            )

            if not res or not res.users:
                break

            for user in res.users:
                yield self._parse_user(user)
                yielded += 1
                if limit and yielded >= limit:
                    return

            offset += len(res.users)
            if len(res.users) < fetch_count:
                break

    def get_members(self, target: Union[str, int], limit: Optional[int] = None) -> List[MemberData]:
        """Get members list."""
        return list(self.iter_members(target, limit=limit))

    # -------------------------------------------------------------------------
    # Message Scraping with Server-Side Filters & Checkpoints
    # -------------------------------------------------------------------------

    def iter_messages(
        self,
        target: Union[str, int],
        limit: Optional[int] = None,
        search: Optional[str] = None,
        filter_type: Optional[str] = None,
        min_id: int = 0,
        max_id: int = 0,
        reverse: bool = False,
        checkpoint: Optional[Union[str, ScrapeCheckpoint]] = None,
    ) -> Generator[MessageData, None, None]:
        """
        Iterate and scrape messages synchronously.

        :param target: Username or ID
        :param limit: Maximum messages to fetch
        :param search: Keyword search string
        :param filter_type: Server-side filter: 'photos', 'videos', 'documents', 'audio', 'voice', 'urls', 'pinned', 'gifs'
        :param min_id: Minimum message ID
        :param max_id: Maximum message ID
        :param reverse: Iterate oldest to newest
        :param checkpoint: Checkpoint file path or ScrapeCheckpoint object for resumable scraping
        """
        peer = self._resolve_target(target)
        chat_title = str(target)
        try:
            info = self.get_chat_info(target)
            chat_title = info.title
        except Exception:
            pass

        # Checkpoint handling
        cp_mgr: Optional[ScrapeCheckpoint] = None
        if isinstance(checkpoint, str):
            cp_mgr = ScrapeCheckpoint(checkpoint)
        elif isinstance(checkpoint, ScrapeCheckpoint):
            cp_mgr = checkpoint

        if cp_mgr:
            last_saved_id = cp_mgr.get_offset(str(target))
            if last_saved_id > 0 and not min_id:
                min_id = last_saved_id

        # Server-side MTProto message filter
        mtproto_filter = types.InputMessagesFilterEmpty()
        if filter_type and filter_type.lower() in FILTER_MAP:
            mtproto_filter = FILTER_MAP[filter_type.lower()]()

        offset_id = 0
        chunk_size = 100
        yielded = 0

        while True:
            fetch_count = chunk_size if limit is None else min(chunk_size, limit - yielded)
            if fetch_count <= 0:
                break

            if search or filter_type:
                res = self._invoke(
                    functions.messages.SearchRequest(
                        peer=peer,
                        q=search or "",
                        filter=mtproto_filter,
                        min_date=None,
                        max_date=None,
                        offset_id=offset_id,
                        add_offset=0,
                        limit=fetch_count,
                        max_id=max_id,
                        min_id=min_id,
                        hash=0,
                    )
                )
            else:
                res = self._invoke(
                    functions.messages.GetHistoryRequest(
                        peer=peer,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        limit=fetch_count,
                        max_id=max_id,
                        min_id=min_id,
                        hash=0,
                    )
                )

            messages = getattr(res, "messages", [])
            if not messages:
                break

            if reverse:
                messages = list(reversed(messages))

            for raw_msg in messages:
                if isinstance(raw_msg, types.Message):
                    parsed = self._parse_message(raw_msg, chat_title=chat_title)
                    yield parsed
                    yielded += 1

                    if cp_mgr:
                        cp_mgr.update(str(target), parsed.id)

                    if limit and yielded >= limit:
                        return

            offset_id = messages[-1].id if not reverse else messages[0].id
            if len(messages) < fetch_count:
                break

    def get_messages(self, target: Union[str, int], limit: Optional[int] = 100, **kwargs) -> List[MessageData]:
        return list(self.iter_messages(target, limit=limit, **kwargs))

    # -------------------------------------------------------------------------
    # Linked Discussion / Comments Scraping
    # -------------------------------------------------------------------------

    def iter_comments(
        self, target: Union[str, int], post_id: int, limit: Optional[int] = None
    ) -> Generator[MessageData, None, None]:
        """
        Scrape comments from a broadcast channel post's linked discussion group.

        :param target: Channel username or ID
        :param post_id: Message ID of the channel post
        :param limit: Maximum comments to scrape
        """
        peer = self._resolve_target(target)
        try:
            disc = self._invoke(functions.messages.GetDiscussionMessageRequest(peer=peer, msg_id=post_id))
        except Exception as e:
            raise TargetNotFoundError(f"Could not fetch discussion group for post {post_id}: {e}") from e

        if not disc or not disc.messages:
            return

        top_msg = disc.messages[0]
        disc_peer = self._resolve_target(top_msg.peer_id.channel_id)

        # Scrape replies in thread
        offset_id = 0
        chunk_size = 100
        yielded = 0

        while True:
            fetch_count = chunk_size if limit is None else min(chunk_size, limit - yielded)
            if fetch_count <= 0:
                break

            res = self._invoke(
                functions.messages.GetRepliesRequest(
                    peer=disc_peer,
                    msg_id=top_msg.id,
                    offset_id=offset_id,
                    offset_date=None,
                    add_offset=0,
                    limit=fetch_count,
                    max_id=0,
                    min_id=0,
                    hash=0,
                )
            )

            messages = getattr(res, "messages", [])
            if not messages:
                break

            for raw_msg in messages:
                if isinstance(raw_msg, types.Message):
                    yield self._parse_message(raw_msg)
                    yielded += 1
                    if limit and yielded >= limit:
                        return

            offset_id = messages[-1].id
            if len(messages) < fetch_count:
                break

    # -------------------------------------------------------------------------
    # Write Operations: Send, Edit, Delete, Forward, Pin, Reactions, Drafts
    # -------------------------------------------------------------------------

    def send_message(
        self, target: Union[str, int], message: str, reply_to: Optional[int] = None, no_webpage: bool = False
    ) -> MessageData:
        peer = self._resolve_target(target)
        random_id = generate_random_long()
        res = self._invoke(
            functions.messages.SendMessageRequest(
                peer=peer,
                message=message,
                random_id=random_id,
                reply_to=types.InputReplyToMessage(reply_to_msg_id=reply_to) if reply_to else None,
                no_webpage=no_webpage,
            )
        )

        if hasattr(res, "updates"):
            for u in res.updates:
                if isinstance(u, (types.UpdateNewMessage, types.UpdateNewChannelMessage)):
                    return self._parse_message(u.message)
        return MessageData(id=0, chat_id=0, chat_title="", date=None, text=message)

    def edit_message(self, target: Union[str, int], message_id: int, text: str) -> Any:
        peer = self._resolve_target(target)
        return self._invoke(functions.messages.EditMessageRequest(peer=peer, id=message_id, message=text))

    def delete_messages(self, target: Union[str, int], message_ids: Union[int, List[int]], revoke: bool = True) -> Any:
        peer = self._resolve_target(target)
        ids = [message_ids] if isinstance(message_ids, int) else message_ids
        if isinstance(peer, InputPeerChannel):
            input_channel = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
            return self._invoke(functions.channels.DeleteMessagesRequest(channel=input_channel, id=ids))
        return self._invoke(functions.messages.DeleteMessagesRequest(id=ids, revoke=revoke))

    def forward_messages(
        self, target_to: Union[str, int], message_ids: Union[int, List[int]], from_peer: Union[str, int]
    ) -> Any:
        to_peer = self._resolve_target(target_to)
        from_p = self._resolve_target(from_peer)
        ids = [message_ids] if isinstance(message_ids, int) else message_ids
        random_ids = [generate_random_long() for _ in ids]
        return self._invoke(
            functions.messages.ForwardMessagesRequest(to_peer=to_peer, from_peer=from_p, id=ids, random_id=random_ids)
        )

    def pin_message(self, target: Union[str, int], message_id: int, notify: bool = False) -> Any:
        peer = self._resolve_target(target)
        return self._invoke(functions.messages.UpdatePinnedMessageRequest(peer=peer, id=message_id, silent=not notify))

    def unpin_message(self, target: Union[str, int], message_id: Optional[int] = None) -> Any:
        peer = self._resolve_target(target)
        if message_id:
            return self._invoke(functions.messages.UpdatePinnedMessageRequest(peer=peer, id=message_id, unpin=True))
        return self._invoke(functions.messages.UnpinAllMessagesRequest(peer=peer))

    def send_reaction(self, target: Union[str, int], message_id: int, reaction: str = "👍") -> Any:
        peer = self._resolve_target(target)
        return self._invoke(
            functions.messages.SendReactionRequest(
                peer=peer, msg_id=message_id, reaction=[ReactionEmoji(emoticon=reaction)]
            )
        )

    def mark_read(self, target: Union[str, int], max_id: int = 0) -> Any:
        peer = self._resolve_target(target)
        if isinstance(peer, InputPeerChannel):
            input_channel = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
            return self._invoke(functions.channels.ReadHistoryRequest(channel=input_channel, max_id=max_id))
        return self._invoke(functions.messages.ReadHistoryRequest(peer=peer, max_id=max_id))

    def save_draft(self, target: Union[str, int], message: str, reply_to: Optional[int] = None) -> Any:
        peer = self._resolve_target(target)
        return self._invoke(functions.messages.SaveDraftRequest(peer=peer, message=message, reply_to_msg_id=reply_to))

    def get_drafts(self) -> Any:
        return self._invoke(functions.messages.GetAllDraftsRequest())

    # -------------------------------------------------------------------------
    # Uploads & Media
    # -------------------------------------------------------------------------

    def upload_file(
        self,
        file_path: Union[str, bytes, Any],
        filename: Optional[str] = None,
        workers: int = 1,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Union[types.InputFile, types.InputFileBig]:
        """Upload file synchronously with optional multi-threaded chunk workers."""
        return upload_file_sync(
            self, file_path=file_path, filename=filename, workers=workers, progress_callback=progress_callback
        )

    def send_file(
        self,
        target: Union[str, int],
        file: Union[str, bytes, Any],
        caption: str = "",
        reply_to: Optional[int] = None,
        workers: int = 1,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Any:
        peer = self._resolve_target(target)
        input_file = self.upload_file(file, workers=workers, progress_callback=progress_callback)
        random_id = generate_random_long()

        mime = "application/octet-stream"
        is_photo = False
        if isinstance(file, str):
            guessed, _ = mimetypes.guess_type(file)
            mime = guessed or mime
            if mime.startswith("image/"):
                is_photo = True

        if is_photo:
            media = InputMediaUploadedPhoto(file=input_file)
        else:
            media = InputMediaUploadedDocument(
                file=input_file,
                mime_type=mime,
                attributes=[DocumentAttributeFilename(file_name=getattr(input_file, "name", "file.bin"))],
            )

        return self._invoke(
            functions.messages.SendMediaRequest(
                peer=peer,
                media=media,
                message=caption,
                random_id=random_id,
                reply_to=types.InputReplyToMessage(reply_to_msg_id=reply_to) if reply_to else None,
            )
        )

    def set_profile_photo(self, file_path: Union[str, bytes], workers: int = 1) -> Any:
        """Upload and set account profile avatar."""
        input_file = self.upload_file(file_path, workers=workers)
        if isinstance(input_file, types.InputFileBig):
            req = functions.photos.UploadProfilePhotoRequest(file=input_file)
        else:
            req = functions.photos.UploadProfilePhotoRequest(file=input_file)
        return self._invoke(req)

    def delete_profile_photos(self, photo_ids: List[int]) -> List[int]:
        """Delete profile photos by photo ID list."""
        input_photos = [types.InputPhoto(id=pid, access_hash=0, file_reference=b"") for pid in photo_ids]
        return self._invoke(functions.photos.DeletePhotosRequest(id=input_photos))

    def get_profile_photos(self, user: Union[str, int] = "me", limit: int = 10, offset: int = 0) -> List[types.Photo]:
        """Fetch historical profile photos for a user."""
        input_user = get_input_user(self.get_input_entity(user))
        res = self._invoke(
            functions.photos.GetUserPhotosRequest(user_id=input_user, offset=offset, max_id=0, limit=limit)
        )
        return res.photos

    # -------------------------------------------------------------------------
    # Chat Invite Links Management
    # -------------------------------------------------------------------------

    def create_invite_link(
        self,
        chat: Union[str, int],
        title: Optional[str] = None,
        expire_date: Optional[int] = None,
        usage_limit: Optional[int] = None,
        request_needed: bool = False,
    ) -> Any:
        """Create a new invite link for a channel or group."""
        peer = self._resolve_target(chat)
        req = functions.messages.ExportChatInviteRequest(
            peer=peer, expire_date=expire_date, usage_limit=usage_limit, request_needed=request_needed, title=title
        )
        return self._invoke(req)

    def edit_invite_link(
        self,
        chat: Union[str, int],
        link: str,
        title: Optional[str] = None,
        expire_date: Optional[int] = None,
        usage_limit: Optional[int] = None,
        request_needed: Optional[bool] = None,
        revoked: Optional[bool] = None,
    ) -> Any:
        """Edit or revoke an existing chat invite link."""
        peer = self._resolve_target(chat)
        req = functions.messages.EditExportedChatInviteRequest(
            peer=peer,
            link=link,
            expire_date=expire_date,
            usage_limit=usage_limit,
            request_needed=request_needed,
            title=title,
            revoked=revoked,
        )
        return self._invoke(req)

    def revoke_invite_link(self, chat: Union[str, int], link: str) -> Any:
        """Revoke an active invite link."""
        return self.edit_invite_link(chat=chat, link=link, revoked=True)

    def get_invite_links(
        self,
        chat: Union[str, int],
        admin_id: Union[str, int] = "me",
        revoked: bool = False,
        limit: int = 100,
        offset_date: Optional[int] = None,
        offset_link: Optional[str] = None,
    ) -> List[Any]:
        """Get all exported invite links created for a chat."""
        peer = self._resolve_target(chat)
        input_admin = get_input_user(self.get_input_entity(admin_id))
        req = functions.messages.GetExportedChatInvitesRequest(
            peer=peer,
            admin_id=input_admin,
            revoked=revoked,
            offset_date=offset_date,
            offset_link=offset_link,
            limit=limit,
        )
        res = self._invoke(req)
        return getattr(res, "invites", [])

    # -------------------------------------------------------------------------
    # Telegram Stories
    # -------------------------------------------------------------------------

    def get_peer_stories(self, target: Union[str, int]) -> Any:
        """Fetch active stories for a user or channel."""
        peer = self._resolve_target(target)
        req = functions.stories.GetPeerStoriesRequest(peer=peer)
        return self._invoke(req)

    def post_story(
        self,
        target: Union[str, int] = "me",
        file_path: Optional[Union[str, bytes]] = None,
        caption: Optional[str] = None,
        period: int = 86400,
        pinned: bool = False,
        workers: int = 1,
    ) -> Any:
        """Post a new story with photo/video media and optional caption."""
        peer = self._resolve_target(target)
        if not file_path:
            raise ValueError("Story requires a media file")

        input_file = self.upload_file(file_path, workers=workers)
        media = types.InputMediaUploadedPhoto(file=input_file)

        req = functions.stories.SendStoryRequest(
            peer=peer,
            media=media,
            caption=caption or "",
            period=period,
            pinned=pinned,
            privacy=[types.InputPrivacyValueAllowAll()],
        )
        return self._invoke(req)

    def delete_stories(self, target: Union[str, int] = "me", story_ids: Optional[List[int]] = None) -> List[int]:
        """Delete stories by ID list."""
        peer = self._resolve_target(target)
        req = functions.stories.DeleteStoriesRequest(peer=peer, id=story_ids or [])
        return self._invoke(req)

    # -------------------------------------------------------------------------
    # State Synchronization & Gap Recovery
    # -------------------------------------------------------------------------

    def get_state(self) -> UpdateSyncState:
        """Fetch current Telegram state (pts, qts, date, seq)."""
        return self._sync_engine.get_state()

    def get_difference(
        self,
        pts: Optional[int] = None,
        date: Optional[int] = None,
        qts: Optional[int] = None,
        pts_total_limit: Optional[int] = None,
    ) -> Any:
        """Fetch missed updates difference since a specific state."""
        return self._sync_engine.get_difference(pts=pts, date=date, qts=qts, pts_total_limit=pts_total_limit)

    def get_channel_difference(self, channel: Union[str, int], pts: int, limit: int = 100) -> Any:
        """Fetch missed updates difference for a specific channel since pts."""
        return self._sync_engine.get_channel_difference(channel=channel, pts=pts, limit=limit)

    def download_media(
        self,
        message: Union[MessageData, Any],
        output_dir: str = "./downloads",
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Optional[str]:
        return download_media_sync(
            self, message, output_dir=output_dir, filename=filename, progress_callback=progress_callback
        )

    def download_parallel(
        self,
        message: Union[MessageData, Any],
        output_dir: str = "./downloads",
        filename: Optional[str] = None,
        num_threads: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Download file 4x faster using multi-threaded chunk workers."""
        return download_file_parallel_sync(
            self,
            message,
            output_dir=output_dir,
            filename=filename,
            num_threads=num_threads,
            progress_callback=progress_callback,
        )

    def download_all_media(
        self,
        target: Union[str, int],
        output_dir: str = "./downloads",
        limit: Optional[int] = None,
        media_types: Optional[List[str]] = None,
        show_progress: bool = True,
    ) -> List[str]:
        downloaded = []
        os.makedirs(output_dir, exist_ok=True)
        for msg in self.iter_messages(target, limit=limit):
            if not msg.has_media or not msg.media:
                continue
            if media_types and msg.media.media_type not in media_types:
                continue

            def cb(rec, total, _msg=msg):
                if show_progress and total > 0:
                    pct = (rec / total) * 100
                    print(
                        f"Downloading [{_msg.media.media_type}] {_msg.media.file_name or _msg.id}: {pct:.1f}%", end="\r"
                    )

            try:
                saved = msg.download(output_dir=output_dir, progress_callback=cb if show_progress else None)
                if saved:
                    downloaded.append(saved)
                    if show_progress:
                        print(f"\n[✔] Saved: {saved}")
            except Exception as e:
                print(f"\n[!] Failed to download media from msg {msg.id}: {e}")
        return downloaded

    def download_profile_photo(self, target: Union[str, int], output_dir: str = "./downloads") -> Optional[str]:
        peer = self._resolve_target(target)
        if isinstance(peer, InputPeerUser):
            input_user = InputUser(user_id=peer.user_id, access_hash=peer.access_hash)
            res = self._invoke(functions.photos.GetUserPhotosRequest(user_id=input_user, offset=0, max_id=0, limit=1))
            if res.photos:
                photo = res.photos[0]
                return download_media_sync(
                    self,
                    types.Message(
                        id=photo.id, peer_id=peer, date=None, message="", media=MessageMediaPhoto(photo=photo)
                    ),
                    output_dir=output_dir,
                )
        return None

    # -------------------------------------------------------------------------
    # Group & Channel Administration
    # -------------------------------------------------------------------------

    def create_channel(self, title: str, about: str = "") -> Any:
        return self._admin.create_channel(title, about)

    def create_group(self, title: str, users: Optional[List[Union[str, int]]] = None) -> Any:
        return self._admin.create_group(title, users)

    def edit_permissions(self, target: Union[str, int], user: Union[str, int], **kwargs) -> Any:
        return self._admin.edit_permissions(target, user, **kwargs)

    def kick_participant(self, target: Union[str, int], user: Union[str, int]) -> Any:
        return self._admin.kick_participant(target, user)

    def get_admin_log(self, target: Union[str, int], limit: int = 50, search_query: str = "") -> List[Any]:
        return self._admin.get_admin_log(target, limit=limit, search_query=search_query)

    # -------------------------------------------------------------------------
    # Secret Chats (End-to-End Encryption)
    # -------------------------------------------------------------------------

    def create_secret_chat(self, target_user: Union[str, int]) -> SecretChat:
        return SecretChat.request(self, target_user)

    # -------------------------------------------------------------------------
    # Data Extractors & Exporters
    # -------------------------------------------------------------------------

    def extract_data(self, text: str) -> dict:
        """Extract emails, phones, URLs, mentions, and crypto wallets from text."""
        return extract_data(text)

    def extract_from_messages(self, target: Union[str, int], limit: Optional[int] = 100, **kwargs) -> dict:
        """
        Scrape messages from a channel and aggregate all extracted emails, phones,
        URLs, mentions, and crypto wallets across all messages.
        """
        aggregated = {
            "emails": set(),
            "phones": set(),
            "urls": set(),
            "mentions": set(),
            "wallets": {"bitcoin": set(), "ethereum": set(), "solana": set(), "ton": set(), "tron": set()},
        }

        for msg in self.iter_messages(target, limit=limit, **kwargs):
            if msg.text:
                res = msg.extract_data()
                aggregated["emails"].update(res["emails"])
                aggregated["phones"].update(res["phones"])
                aggregated["urls"].update(res["urls"])
                aggregated["mentions"].update(res["mentions"])
                for coin, wallets in res["wallets"].items():
                    aggregated["wallets"][coin].update(wallets)

        return {
            "emails": sorted(list(aggregated["emails"])),
            "phones": sorted(list(aggregated["phones"])),
            "urls": sorted(list(aggregated["urls"])),
            "mentions": sorted(list(aggregated["mentions"])),
            "wallets": {coin: sorted(list(wallets)) for coin, wallets in aggregated["wallets"].items()},
        }

    def get_comments(self, target: Union[str, int], post_id: int, limit: Optional[int] = 100) -> List[MessageData]:
        """Fetch comments for a channel post as a list."""
        return list(self.iter_comments(target, post_id, limit=limit))

    def export_messages(
        self, target: Union[str, int], output_file: str, format: str = "json", limit: Optional[int] = None, **kwargs
    ) -> str:
        messages = self.get_messages(target, limit=limit, **kwargs)
        fmt = format.lower()
        if fmt == "csv":
            return export_to_csv(messages, output_file)
        elif fmt in ("excel", "xlsx"):
            return export_to_excel(messages, output_file)
        elif fmt in ("sqlite", "db"):
            return export_to_sqlite(messages, output_file)
        return export_to_json(messages, output_file)

    def export_to_excel(self, target: Union[str, int], output_file: str, limit: Optional[int] = None, **kwargs) -> str:
        """Direct export to Excel (.xlsx)."""
        return self.export_messages(target, output_file, format="excel", limit=limit, **kwargs)

    def export_to_sqlite(
        self,
        target: Union[str, int],
        db_path: str,
        table_name: str = "scraped_messages",
        limit: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Direct export to SQLite database."""
        messages = self.get_messages(target, limit=limit, **kwargs)
        return export_to_sqlite(messages, db_path, table_name=table_name)

    def export_to_json(self, target: Union[str, int], output_file: str, limit: Optional[int] = None, **kwargs) -> str:
        """Direct export to JSON."""
        return self.export_messages(target, output_file, format="json", limit=limit, **kwargs)

    def export_to_csv(self, target: Union[str, int], output_file: str, limit: Optional[int] = None, **kwargs) -> str:
        """Direct export to CSV."""
        return self.export_messages(target, output_file, format="csv", limit=limit, **kwargs)

    def to_dataframe(self, target: Union[str, int], limit: Optional[int] = None, **kwargs) -> Any:
        """Fetch messages and convert directly to a Pandas DataFrame."""
        messages = self.get_messages(target, limit=limit, **kwargs)
        return to_dataframe(messages)

    # -------------------------------------------------------------------------
    # Contacts Management Convenience Methods
    # -------------------------------------------------------------------------

    def get_contacts(self, hash: int = 0, sort_by: str = "name", reverse: Optional[bool] = None) -> List[MemberData]:
        """Fetch user contacts list with sorting ('name' for A-Z, 'last_seen' for online/recent first)."""
        return self.contacts.get_contacts(hash=hash, sort_by=sort_by, reverse=reverse)

    def add_contact(
        self,
        user: Union[int, str, types.TypeInputUser],
        first_name: str,
        last_name: str = "",
        phone: str = "",
        add_phone_privacy_exception: bool = False,
    ) -> bool:
        """Add or update a contact in user's address book."""
        return self.contacts.add_contact(
            user=user,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            add_phone_privacy_exception=add_phone_privacy_exception,
        )

    def delete_contacts(self, users: Union[List[Any], Any]) -> bool:
        """Delete one or multiple contacts."""
        return self.contacts.delete_contacts(users)

    def import_contacts(self, contacts: List[Union[dict, tuple]]) -> List[MemberData]:
        """Import contacts by phone numbers."""
        return self.contacts.import_contacts(contacts)

    def search_contacts(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """Search global Telegram users and contacts. Returns dict with 'my_results', 'users', and 'chats'."""
        return self.contacts.search(query=query, limit=limit)

    def block_user(self, user: Union[int, str, types.TypeInputPeer, types.TypeInputUser]) -> bool:
        """Block a user or peer."""
        return self.contacts.block(user)

    def unblock_user(self, user: Union[int, str, types.TypeInputPeer, types.TypeInputUser]) -> bool:
        """Unblock a user or peer."""
        return self.contacts.unblock(user)

    def get_blocked_users(self, offset: int = 0, limit: int = 100) -> List[MemberData]:
        """Get list of blocked users."""
        return self.contacts.get_blocked(offset=offset, limit=limit)
