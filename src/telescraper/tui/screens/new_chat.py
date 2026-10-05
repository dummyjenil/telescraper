"""
New Channel & Group Creator Modals for TeleScraper TUI.
"""

from typing import Optional, Callable
from textual.binding import Binding
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, Select
from textual.containers import Vertical, Horizontal

from ...client import TeleScraper


class NewChatModal(ModalScreen[Optional[dict]]):
    """Create a new Broadcast Channel or Supergroup."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close / Back", priority=True),
    ]

    def __init__(self, client: TeleScraper, chat_type: str = "channel"):
        super().__init__()
        self.client = client
        self.chat_type = chat_type

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            is_ch = self.chat_type == "channel"
            title_text = "📢 New Telegram Channel" if is_ch else "👥 New Telegram Supergroup"
            yield Label(title_text, classes="text-bold text-cyan")
            
            yield Input(placeholder="Channel Name" if is_ch else "Group Name", id="chat-title-input")
            yield Input(placeholder="Description / About (optional)", id="chat-about-input")
            
            if not is_ch:
                yield Input(placeholder="Initial members (usernames comma-separated, e.g. @user1, @user2)", id="chat-users-input")

            with Horizontal(classes="margin-top"):
                yield Button("Create", id="btn-create", variant="success")
                yield Button("Cancel", id="btn-cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-create":
            title = self.query_one("#chat-title-input", Input).value.strip()
            about = self.query_one("#chat-about-input", Input).value.strip()
            
            if not title:
                self.notify("Title is required", severity="warning")
                return

            try:
                if self.chat_type == "channel":
                    res = self.client.create_channel(title=title, about=about)
                    self.notify(f"Channel '{title}' created successfully!", title="Created")
                else:
                    users_raw = self.query_one("#chat-users-input", Input).value.strip()
                    users = [u.strip() for u in users_raw.split(",") if u.strip()] if users_raw else None
                    res = self.client.create_group(title=title, users=users)
                    self.notify(f"Group '{title}' created successfully!", title="Created")
                self.dismiss({"title": title, "result": res})
            except Exception as e:
                self.notify(f"Creation failed: {e}", title="Error", severity="error")
