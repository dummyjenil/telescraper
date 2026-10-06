"""
Left Sidebar Widget (Chat List & Categories) for TeleScraper Textual TUI.
"""

from typing import Callable, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView

from ...client import TeleScraper
from ...models import ChatData


class ChatListItemWidget(ListItem):
    """Rich visual item in the Telegram Chat List."""

    def __init__(
        self,
        chat_id: int,
        title: str,
        username: Optional[str] = None,
        last_message: str = "",
        timestamp: str = "",
        unread_count: int = 0,
        is_channel: bool = False,
        is_group: bool = False,
        is_pinned: bool = False,
    ):
        super().__init__(classes="chat-item", name=str(chat_id))
        self.chat_id = chat_id
        self.chat_title = title
        self.username = username
        self.last_message = last_message
        self.timestamp = timestamp
        self.unread_count = unread_count
        self.is_channel = is_channel
        self.is_group = is_group
        self.is_pinned = is_pinned

    def compose(self) -> ComposeResult:
        with Horizontal():
            # Initials / Icon Avatar
            type_icon = "📢" if self.is_channel else ("👥" if self.is_group else "👤")
            yield Label(f" {type_icon} ", classes="chat-avatar", markup=False)

            with Vertical(classes="chat-info-box"):
                with Horizontal(classes="chat-title-row"):
                    pin_str = "📌 " if self.is_pinned else ""
                    yield Label(f"{pin_str}{self.chat_title}", classes="chat-title-text", markup=False)
                    yield Label(self.timestamp, classes="chat-time-text", markup=False)

                with Horizontal(classes="chat-msg-row"):
                    yield Label(self.last_message or "No messages yet", classes="chat-last-msg", markup=False)
                    if self.unread_count > 0:
                        yield Label(f" {self.unread_count} ", classes="chat-unread-badge", markup=False)


class LeftSidebarWidget(Widget):
    """Full Telegram-like Left Sidebar with Search, Categories, and Chat List."""

    active_category = reactive("all")

    def __init__(
        self,
        client: TeleScraper,
        on_chat_selected: Callable[[int, str, Optional[str]], None],
        on_hamburger_click: Callable[[], None],
        on_new_chat_click: Callable[[], None],
    ):
        super().__init__(id="left-sidebar")
        self.client = client
        self.on_chat_selected = on_chat_selected
        self.on_hamburger_click = on_hamburger_click
        self.on_new_chat_click = on_new_chat_click
        self._chats_cache: List[ChatData] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            # Top Search Bar & Hamburger
            with Horizontal(id="sidebar-search-bar"):
                yield Button("☰", id="btn-hamburger", variant="default")
                yield Input(placeholder="🔍 Search chats...", id="search-input")

            # Categories Row
            with Horizontal(id="category-tabs"):
                yield Button("All", id="tab-cat-all", classes="category-tab -active")
                yield Button("Direct", id="tab-cat-direct", classes="category-tab")
                yield Button("Groups", id="tab-cat-groups", classes="category-tab")
                yield Button("Channels", id="tab-cat-channels", classes="category-tab")

            # Chat List
            yield ListView(id="chat-list-view")

            # Bottom Bar
            with Horizontal(id="sidebar-bottom-bar"):
                yield Button("➕ New Chat / Channel", id="btn-new-chat", variant="primary", classes="width-1fr")

    def on_mount(self) -> None:
        self.load_dialogs()

    def load_dialogs(self) -> None:
        """Fetch chats from Telegram DC."""
        lv = self.query_one("#chat-list-view", ListView)
        lv.clear()
        try:
            self._chats_cache = self.client.get_chats()
            self.filter_and_render_chats()
        except Exception as e:
            lv.append(ListItem(Label(f"Failed to load chats: {e}")))

    def filter_and_render_chats(self, search_query: str = "") -> None:
        lv = self.query_one("#chat-list-view", ListView)
        lv.clear()
        q = search_query.lower().strip()

        # Add Saved Messages by default
        if not q or "saved" in q:
            lv.append(
                ChatListItemWidget(
                    chat_id=0,
                    title="Saved Messages",
                    username="me",
                    last_message="Cloud Storage",
                    timestamp="Now",
                    is_pinned=True,
                )
            )

        for c in self._chats_cache:
            if self.active_category == "direct" and (c.is_channel or c.is_group):
                continue
            elif self.active_category == "groups" and not c.is_group:
                continue
            elif self.active_category == "channels" and not c.is_channel:
                continue

            if q:
                title_match = q in c.title.lower()
                uname_match = q in (c.username.lower() if c.username else "")
                if not (title_match or uname_match):
                    continue

            lv.append(
                ChatListItemWidget(
                    chat_id=c.id,
                    title=c.title,
                    username=c.username,
                    last_message=f"{c.participants_count or 0} members",
                    timestamp="12:45",
                    unread_count=0,
                    is_channel=c.is_channel,
                    is_group=c.is_group,
                )
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.filter_and_render_chats(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-hamburger":
            self.on_hamburger_click()
        elif btn_id == "btn-new-chat":
            self.on_new_chat_click()
        elif btn_id.startswith("tab-cat-"):
            for t in ["all", "direct", "groups", "channels"]:
                b = self.query_one(f"#tab-cat-{t}", Button)
                b.remove_class("-active")
            event.button.add_class("-active")
            self.active_category = btn_id.replace("tab-cat-", "")
            self.filter_and_render_chats(self.query_one("#search-input", Input).value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, ChatListItemWidget):
            self.on_chat_selected(event.item.chat_id, event.item.chat_title, event.item.username)
