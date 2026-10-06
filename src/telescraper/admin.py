"""
Group & Channel Moderation and Administration Module.
Provides pure synchronous methods for user restrictions, kicking, channel creation, and admin audit logs.
"""

from typing import Any, List, Optional, Union

from .exceptions import TeleScraperError
from .tl import functions
from .tl.types import (
    ChatBannedRights,
    InputChannel,
    InputPeerChannel,
    InputUser,
)


class AdminManager:
    """Group and channel administration manager."""

    def __init__(self, client: Any):
        self.client = client

    def create_channel(self, title: str, about: str = "") -> Any:
        """Create a new broadcast channel."""
        res = self.client._invoke(
            functions.channels.CreateChannelRequest(title=title, about=about, broadcast=True, megagroup=False)
        )
        if res.chats:
            return self.client._parse_chat(res.chats[0])
        return res

    def create_group(self, title: str, users: Optional[List[Union[str, int]]] = None) -> Any:
        """Create a new supergroup."""
        res = self.client._invoke(
            functions.channels.CreateChannelRequest(title=title, about="", broadcast=False, megagroup=True)
        )
        if res.chats:
            chat = self.client._parse_chat(res.chats[0])
            if users:
                for user in users:
                    try:
                        self.invite_to_group(chat.id, user)
                    except Exception:
                        pass
            return chat
        return res

    def invite_to_group(self, target: Union[str, int], user: Union[str, int]) -> Any:
        """Invite a user to a group or channel."""
        peer = self.client._resolve_target(target)
        user_peer = self.client._resolve_target(user)
        if isinstance(peer, InputPeerChannel):
            input_ch = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
            input_u = InputUser(user_id=user_peer.user_id, access_hash=user_peer.access_hash)
            return self.client._invoke(functions.channels.InviteToChannelRequest(channel=input_ch, users=[input_u]))
        raise TeleScraperError("Inviting is supported on supergroups/channels")

    def edit_permissions(
        self,
        target: Union[str, int],
        user: Union[str, int],
        until_date: Optional[Any] = None,
        view_messages: bool = False,
        send_messages: bool = False,
        send_media: bool = False,
        send_stickers: bool = False,
        send_gifs: bool = False,
        send_games: bool = False,
        send_inline: bool = False,
        embed_links: bool = False,
        send_polls: bool = False,
        change_info: bool = False,
        invite_users: bool = False,
        pin_messages: bool = False,
    ) -> Any:
        """Restrict or ban a participant in a supergroup/channel."""
        peer = self.client._resolve_target(target)
        user_peer = self.client._resolve_target(user)

        if not isinstance(peer, InputPeerChannel):
            raise TeleScraperError("Moderation is only supported on supergroups/channels")

        input_ch = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
        input_u = InputUser(user_id=user_peer.user_id, access_hash=user_peer.access_hash)

        banned_rights = ChatBannedRights(
            until_date=until_date,
            view_messages=view_messages,
            send_messages=not send_messages,
            send_media=not send_media,
            send_stickers=not send_stickers,
            send_gifs=not send_gifs,
            send_games=not send_games,
            send_inline=not send_inline,
            embed_links=not embed_links,
            send_polls=not send_polls,
            change_info=not change_info,
            invite_users=not invite_users,
            pin_messages=not pin_messages,
        )

        return self.client._invoke(
            functions.channels.EditBannedRequest(channel=input_ch, participant=input_u, banned_rights=banned_rights)
        )

    def kick_participant(self, target: Union[str, int], user: Union[str, int]) -> Any:
        """Kick a user from a group (temporarily bans and unbans to remove)."""
        peer = self.client._resolve_target(target)
        user_peer = self.client._resolve_target(user)

        if not isinstance(peer, InputPeerChannel):
            raise TeleScraperError("Kicking is supported on supergroups/channels")

        input_ch = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
        input_u = InputUser(user_id=user_peer.user_id, access_hash=user_peer.access_hash)

        # Kick by banning view_messages
        banned = ChatBannedRights(until_date=None, view_messages=True)
        res = self.client._invoke(
            functions.channels.EditBannedRequest(channel=input_ch, participant=input_u, banned_rights=banned)
        )
        # Unban immediately so they can re-join if invited
        unbanned = ChatBannedRights(until_date=None, view_messages=False)
        self.client._invoke(
            functions.channels.EditBannedRequest(channel=input_ch, participant=input_u, banned_rights=unbanned)
        )
        return res

    def get_admin_log(self, target: Union[str, int], limit: int = 50, search_query: str = "") -> List[Any]:
        """Fetch admin audit log events from a channel or supergroup."""
        peer = self.client._resolve_target(target)
        if not isinstance(peer, InputPeerChannel):
            raise TeleScraperError("Admin logs are only available for channels and supergroups")

        input_ch = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
        res = self.client._invoke(
            functions.channels.GetAdminLogRequest(
                channel=input_ch, q=search_query, events_filter=None, admins=[], max_id=0, min_id=0, limit=limit
            )
        )
        return getattr(res, "events", [])
