"""
Profile & WhoAmI Modal Screen for TeleScraper TUI.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from ...client import TeleScraper


class ProfileModal(ModalScreen):
    """Shows authenticated user/bot profile with account statistics."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close / Back", priority=True),
    ]

    def __init__(self, client: TeleScraper):
        super().__init__()
        self.client = client
        self.user_data = None

    def compose(self) -> ComposeResult:
        try:
            self.user_data = self.client.get_me()
        except Exception:
            self.user_data = None

        with Vertical(classes="modal-dialog"):
            yield Label("👤 My Telegram Profile", classes="text-bold text-cyan")

            initials = "TG"
            name_str = "Unknown User"
            username_str = "@none"
            user_id_str = "0"
            status_str = "Offline"

            if self.user_data:
                first = self.user_data.first_name or ""
                last = self.user_data.last_name or ""
                name_str = f"{first} {last}".strip() or "Telegram User"
                initials = (first[:1] + last[:1]).upper() if (first or last) else "U"
                username_str = f"@{self.user_data.username}" if self.user_data.username else "No username"
                user_id_str = str(self.user_data.id)
                status_str = str(self.user_data.status or "Online")

            with Horizontal(classes="margin-bottom"):
                with Vertical(classes="profile-avatar-large"):
                    yield Label(f"╭───────╮\n│  {initials:^3}  │\n╰───────╯", classes="text-cyan text-bold")
                with Vertical(classes="margin-left"):
                    yield Label(name_str, classes="text-bold")
                    yield Label(username_str, classes="text-cyan")
                    yield Label(f"ID: {user_id_str}", classes="subtext")
                    yield Label(f"Status: {status_str}", classes="text-green")

            yield Label("📁 Session Information:", classes="text-bold")
            session_file = getattr(self.client.session, "filename", "active session")
            yield Label(f"Session: {session_file}", classes="subtext")
            yield Label(f"Data Center: DC {getattr(self.client.session, 'dc_id', 2)}", classes="subtext")

            with Horizontal(classes="margin-top"):
                yield Button("📥 Download Avatar", id="btn-dl-avatar", variant="default")
                yield Button("🔑 Export StringSession", id="btn-export-str", variant="primary")
                yield Button("Close", id="btn-close", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()
        elif event.button.id == "btn-dl-avatar":
            try:
                path = self.client.download_profile_photo("me", output_dir="./downloads")
                self.notify(f"Avatar saved to {path or 'N/A'}", title="Downloaded")
            except Exception as e:
                self.notify(f"Download failed: {e}", title="Error", severity="error")
        elif event.button.id == "btn-export-str":
            try:
                from ...sessions.string_session import StringSession

                ss = StringSession.save(self.client.session)
                self.app.copy_to_clipboard(ss)
                self.notify("StringSession copied to clipboard!", title="Exported")
            except Exception as e:
                self.notify(f"Export failed: {e}", title="Error", severity="error")
