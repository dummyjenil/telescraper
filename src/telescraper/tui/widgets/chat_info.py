"""
Collapsible Right Sidebar (Chat & Channel Info) for TeleScraper Textual TUI.
"""

from typing import Optional, Callable
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Button, Static, TabbedContent, TabPane, Input
from textual.containers import Vertical, Horizontal, ScrollableContainer

from ...client import TeleScraper


class RightChatInfoWidget(Widget):
    """Collapsible panel showing chat metadata, moderation tools, and dataset exporters."""

    def __init__(
        self,
        client: TeleScraper,
        on_export: Optional[Callable[[str, str], None]] = None,
        on_extract_data: Optional[Callable[[str], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ):
        super().__init__(id="right-sidebar")
        self.client = client
        self.on_export = on_export
        self.on_extract_data = on_extract_data
        self.on_close = on_close
        self.current_target: Optional[str] = None
        self.current_title: str = "Chat Info"

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            with Horizontal(classes="align-middle margin-bottom"):
                yield Label("ℹ️ Chat Details", classes="text-bold text-cyan width-1fr", markup=False)
                yield Button("✖", id="btn-close-info", variant="default")

            with Vertical(classes="profile-avatar-large"):
                yield Label("╭─────────╮\n│   INFO  │\n╰─────────╯", id="info-avatar-icon", classes="text-cyan text-bold text-center", markup=False)
                yield Label("Select a chat", id="info-chat-title", classes="text-bold text-center", markup=False)
                yield Label("@username", id="info-chat-username", classes="subtext text-center", markup=False)
                yield Label("0 subscribers", id="info-chat-members", classes="text-green text-center", markup=False)

            yield Label("📝 Description / About:", classes="text-bold margin-top", markup=False)
            yield Static("No description available.", id="info-chat-about", classes="media-card", markup=False)

            yield Label("📊 Scrape & Export:", classes="text-bold margin-top", markup=False)
            with Horizontal():
                yield Button("📊 Excel", id="btn-exp-xlsx", variant="primary")
                yield Button("🗄️ SQLite", id="btn-exp-db", variant="default")
                yield Button("📄 JSON", id="btn-exp-json", variant="default")

            yield Button("💰 Extract Wallets & Emails", id="btn-extract-entities", variant="success", classes="margin-top width-1fr")

            yield Label("🛡️ Admin & Moderation:", classes="text-bold margin-top", markup=False)
            yield Button("🔗 Manage Invite Links", id="btn-admin-invites", variant="default", classes="width-1fr")
            yield Button("📜 Inspect Admin Audit Log", id="btn-admin-log", variant="default", classes="width-1fr")
            yield Button("👢 Kick Participant", id="btn-admin-kick", variant="error", classes="width-1fr margin-top")

    def update_chat_info(self, target: str, title: str, username: Optional[str] = None) -> None:
        self.current_target = target
        self.current_title = title
        self.query_one("#info-chat-title", Label).update(title)
        self.query_one("#info-chat-username", Label).update(f"@{username}" if username else f"ID: {target}")

        try:
            info = self.client.get_chat_info(target)
            self.query_one("#info-chat-members", Label).update(f"{info.participants_count or 0} members")
            self.query_one("#info-chat-about", Static).update(info.description or "No description provided.")
        except Exception:
            self.query_one("#info-chat-members", Label).update("N/A members")
            self.query_one("#info-chat-about", Static).update("Private chat or channel metadata.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from ..screens.dialogs import NotSupportedModal

        if event.button.id == "btn-close-info" and self.on_close:
            self.on_close()
        elif event.button.id == "btn-exp-xlsx" and self.current_target:
            if self.on_export:
                self.on_export(self.current_target, "xlsx")
        elif event.button.id == "btn-exp-db" and self.current_target:
            if self.on_export:
                self.on_export(self.current_target, "sqlite")
        elif event.button.id == "btn-exp-json" and self.current_target:
            if self.on_export:
                self.on_export(self.current_target, "json")
        elif event.button.id == "btn-extract-entities" and self.current_target:
            if self.on_extract_data:
                self.on_extract_data(self.current_target)
        elif event.button.id == "btn-admin-invites" and self.current_target:
            try:
                links = self.client.get_invite_links(self.current_target)
                self.notify(f"Found {len(links)} active invite links.", title="Invite Links")
            except Exception as e:
                self.app.push_screen(NotSupportedModal("Invite Links", f"Cannot fetch invite links: {e} (Admin rights required)"))
        elif event.button.id == "btn-admin-log" and self.current_target:
            try:
                events = self.client.get_admin_log(self.current_target, limit=20)
                self.notify(f"Loaded {len(events)} admin audit events.", title="Admin Log")
            except Exception as e:
                self.app.push_screen(NotSupportedModal("Admin Log", f"Cannot fetch admin logs: {e} (Admin rights required)"))
        elif event.button.id == "btn-admin-kick":
            self.app.push_screen(NotSupportedModal("Kick Participant", "Select a specific user from chat members list to execute kick/ban."))
