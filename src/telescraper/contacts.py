"""
Contacts Manager for TeleScraper.
Full Telegram Contacts integration: fetch contacts, add/delete, import by phone, search, block/unblock, and resolve.
Pure Synchronous MTProto 2.0.
"""

from typing import Optional, List, Union, Dict, Any, TYPE_CHECKING
from .tl import functions, types
from .models import MemberData
from .helpers import generate_random_long

if TYPE_CHECKING:
    from .client import TeleScraper


class ContactsManager:
    """Synchronous Telegram Contacts Management API."""

    def __init__(self, client: "TeleScraper"):
        self._client = client

    def get_contacts(
        self,
        hash: int = 0,
        sort_by: str = "name",
        reverse: Optional[bool] = None
    ) -> List[MemberData]:
        """
        Fetch all Telegram contacts for the authenticated user.
        
        :param hash: Hash for caching (0 for full list)
        :param sort_by: Sorting method ('name' for alphabetical A-Z, 'last_seen' / 'time' for online/recently seen activity)
        :param reverse: Custom reverse boolean (default False for name, default True for last_seen)
        :return: List of MemberData contacts with full name, username, phone and status
        """
        res = self._client._invoke(functions.contacts.GetContactsRequest(hash=hash))
        users = getattr(res, 'users', [])
        contacts = [self._client._parse_user(u) for u in users]

        if sort_by in ("last_seen", "time", "recent"):
            is_rev = True if reverse is None else reverse
            contacts.sort(key=lambda m: m.last_seen_time or 0.0, reverse=is_rev)
        elif sort_by == "name":
            is_rev = False if reverse is None else reverse
            contacts.sort(key=lambda m: (m.full_name or "").lower(), reverse=is_rev)

        return contacts

    def add_contact(
        self,
        user: Union[str, int, types.InputUser],
        first_name: str,
        last_name: str = "",
        phone: str = "",
        add_phone_privacy_exception: bool = False
    ) -> Any:
        """
        Add an existing Telegram user to contacts.

        :param user: Username, user_id, or InputUser
        :param first_name: First name
        :param last_name: Last name (optional)
        :param phone: Phone number (optional)
        :param add_phone_privacy_exception: Allow contact to see phone number
        """
        peer = self._client._resolve_target(user)
        input_user = types.InputUser(user_id=peer.user_id, access_hash=peer.access_hash) if isinstance(peer, types.InputPeerUser) else peer
        return self._client._invoke(functions.contacts.AddContactRequest(
            id=input_user,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            add_phone_privacy_exception=add_phone_privacy_exception
        ))

    def delete_contacts(self, users: Union[str, int, List[Union[str, int]]]) -> Any:
        """
        Delete one or more users from Telegram contacts.

        :param users: User ID, username or list of user targets
        """
        user_list = [users] if not isinstance(users, (list, tuple)) else users
        input_users = []
        for u in user_list:
            peer = self._client._resolve_target(u)
            if isinstance(peer, types.InputPeerUser):
                input_users.append(types.InputUser(user_id=peer.user_id, access_hash=peer.access_hash))
            elif isinstance(peer, types.InputUser):
                input_users.append(peer)
            elif isinstance(peer, types.InputPeerSelf):
                input_users.append(types.InputUserSelf())

        return self._client._invoke(functions.contacts.DeleteContactsRequest(id=input_users))

    def import_contacts(self, contacts: List[Union[dict, types.InputPhoneContact]]) -> List[MemberData]:
        """
        Import new phone contacts into Telegram.

        :param contacts: List of dicts like [{"phone": "+123456", "first_name": "John", "last_name": "Doe"}]
                         or list of InputPhoneContact TL objects.
        :return: List of imported users as MemberData
        """
        tl_contacts = []
        for idx, c in enumerate(contacts):
            if isinstance(c, types.InputPhoneContact):
                tl_contacts.append(c)
            elif isinstance(c, dict):
                tl_contacts.append(types.InputPhoneContact(
                    client_id=generate_random_long(),
                    phone=str(c.get("phone", "")).strip(),
                    first_name=str(c.get("first_name", "")).strip(),
                    last_name=str(c.get("last_name", "")).strip()
                ))

        res = self._client._invoke(functions.contacts.ImportContactsRequest(contacts=tl_contacts))
        users = getattr(res, 'users', [])
        return [self._client._parse_user(u) for u in users]

    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """
        Search Telegram globally for contacts, users, and channels by keyword.

        :param query: Keyword string
        :param limit: Maximum results
        :return: Dict containing matching 'my_results', 'users', and 'chats'
        """
        res = self._client._invoke(functions.contacts.SearchRequest(q=query, limit=limit))
        return {
            "my_results": getattr(res, 'my_results', []),
            "users": [self._client._parse_user(u) for u in getattr(res, 'users', [])],
            "chats": [self._client._parse_chat(c) for c in getattr(res, 'chats', [])]
        }

    def get_statuses(self) -> List[Any]:
        """Fetch online/offline timestamp statuses for all contacts."""
        return self._client._invoke(functions.contacts.GetStatusesRequest())

    def block(self, user: Union[str, int]) -> bool:
        """
        Block a user from sending messages or calling.

        :param user: Username or user_id
        """
        peer = self._client._resolve_target(user)
        return bool(self._client._invoke(functions.contacts.BlockRequest(id=peer)))

    def unblock(self, user: Union[str, int]) -> bool:
        """
        Unblock a previously blocked user.

        :param user: Username or user_id
        """
        peer = self._client._resolve_target(user)
        return bool(self._client._invoke(functions.contacts.UnblockRequest(id=peer)))

    def get_blocked(self, offset: int = 0, limit: int = 100) -> List[MemberData]:
        """
        Fetch list of blocked users.

        :param offset: Pagination offset
        :param limit: Maximum items to retrieve
        :return: List of blocked MemberData
        """
        res = self._client._invoke(functions.contacts.GetBlockedRequest(offset=offset, limit=limit))
        users = getattr(res, 'users', [])
        return [self._client._parse_user(u) for u in users]

    def resolve_phone(self, phone: str) -> Optional[MemberData]:
        """
        Resolve a phone number to a Telegram user.

        :param phone: Phone number with country code (e.g. +919876543210)
        """
        clean_phone = phone.strip().replace(" ", "").replace("-", "")
        try:
            res = self._client._invoke(functions.contacts.ResolvePhoneRequest(phone=clean_phone))
            users = getattr(res, 'users', [])
            if users:
                return self._client._parse_user(users[0])
        except Exception:
            pass
        return None

    def resolve_username(self, username: str) -> Optional[Union[MemberData, Any]]:
        """
        Resolve @username to Telegram User or Chat entity.
        """
        clean_uname = username.strip().lstrip("@")
        res = self._client._invoke(functions.contacts.ResolveUsernameRequest(username=clean_uname))
        if getattr(res, 'users', None):
            return self._client._parse_user(res.users[0])
        elif getattr(res, 'chats', None):
            return self._client._parse_chat(res.chats[0])
        return None
