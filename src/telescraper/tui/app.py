"""
Main Textual Application for TeleScraper TUI.
Full Telegram Desktop Experience in the Terminal.
"""

from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Label

from ..client import TeleScraper
from .screens.call import CallScreen
from .screens.contacts import ContactsModal
from .screens.login import LoginScreen
from .screens.new_chat import NewChatModal
from .screens.profile import ProfileModal
from .screens.settings import SettingsModal
from .widgets.chat_info import RightChatInfoWidget
from .widgets.chat_view import ChatViewWidget
from .widgets.sidebar import LeftSidebarWidget


class TelegramApp(App):
    """TeleScraper Telegram-like Full TUI Client."""

    CSS_PATH = "theme.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+f", "search", "Search", show=True),
        Binding("ctrl+n", "new_chat", "New Chat", show=True),
        Binding("ctrl+i", "toggle_info", "Chat Info", show=True),
        Binding("ctrl+p", "open_profile", "My Profile", show=True),
        Binding("ctrl+s", "open_settings", "Settings", show=True),
        Binding("ctrl+c", "start_call", "Call", show=False),
        Binding("escape", "dismiss_modal", "Back / Close", show=True, priority=True),
    ]

    def __init__(self, client: Optional[TeleScraper] = None):
        super().__init__()
        self.client = client or TeleScraper("my_telegram", 22129668, "e162d3534a83f695c5f5c5b2005bee3e")
        self._show_info = False

    def on_mount(self) -> None:
        self.title = "TeleScraper Telegram"
        self.sub_title = "Pure Synchronous MTProto 2.0"

        # Check authorization
        try:
            self.client.connect()
            if not self.client.is_user_authorized():
                self.push_screen(LoginScreen(self.client, on_success=self.on_login_success))
            else:
                self.load_main_ui()
        except Exception:
            self.push_screen(LoginScreen(self.client, on_success=self.on_login_success))

    def on_login_success(self) -> None:
        self.pop_screen()
        self.load_main_ui()

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-container"):
            yield LeftSidebarWidget(
                client=self.client,
                on_chat_selected=self.on_chat_selected,
                on_hamburger_click=self.on_hamburger_menu,
                on_new_chat_click=self.on_new_chat_dialog,
            )
            yield ChatViewWidget(
                client=self.client,
                on_call_click=self.on_call_start,
                on_info_click=self.action_toggle_info,
                on_send_message=self.on_send_message_submit,
                on_attach_file=self.on_attach_file_dialog,
                on_create_poll=self.on_poll_creator_dialog,
            )
            yield RightChatInfoWidget(
                client=self.client,
                on_export=self.on_export_data,
                on_extract_data=self.on_extract_wallets,
                on_close=self.action_toggle_info,
            )
        yield Footer()

    def load_main_ui(self) -> None:
        # Hide right sidebar initially
        right = self.query_one(RightChatInfoWidget)
        right.display = False

        # Refresh left sidebar chats
        sidebar = self.query_one(LeftSidebarWidget)
        sidebar.load_dialogs()
        self.notify("Connected to Telegram DC!", title="TeleScraper", severity="information")

    def on_chat_selected(self, chat_id: int, title: str, username: Optional[str] = None) -> None:
        target = username or str(chat_id)
        chat_view = self.query_one(ChatViewWidget)
        chat_view.load_chat(target=target, title=title, username=username)

        right_info = self.query_one(RightChatInfoWidget)
        right_info.update_chat_info(target=target, title=title, username=username)

    def on_send_message_submit(self, text: str, reply_to: Optional[int] = None) -> None:
        chat_view = self.query_one(ChatViewWidget)
        target = chat_view.active_target
        if target:
            try:
                self.client.send_message(target, text, reply_to=reply_to)
                self.notify("Message sent!", title="Sent")
                chat_view.load_chat(target, chat_view.current_chat_title, chat_view.active_username)
            except Exception as e:
                self.notify(f"Send failed: {e}", title="Error", severity="error")

    def on_attach_file_dialog(self) -> None:
        chat_view = self.query_one(ChatViewWidget)
        target = chat_view.active_target
        if not target:
            self.notify("Select a chat first to attach files.", severity="warning")
            return

        from .screens.dialogs import FilePickerModal, NotSupportedModal

        def handle_file(file_path: Optional[str]):
            if file_path:
                try:
                    self.notify(f"Uploading file: {file_path}...", title="Upload")
                    self.client.send_file(target, file_path)
                    self.notify("File sent successfully!", title="Sent")
                    chat_view.load_chat(target, chat_view.current_chat_title, chat_view.active_username)
                except Exception as e:
                    self.push_screen(NotSupportedModal("File Upload", f"Upload failed: {e}"))

        self.push_screen(FilePickerModal(), handle_file)

    def on_poll_creator_dialog(self) -> None:
        from .screens.dialogs import NotSupportedModal

        self.push_screen(
            NotSupportedModal(
                "Telegram Poll Creation", "Poll creation via pure MTProto is not supported yet in this version."
            )
        )

    def on_hamburger_menu(self) -> None:
        """Hamburger Menu actions modal."""
        from textual.screen import ModalScreen

        class HamburgerModal(ModalScreen):
            BINDINGS = [
                Binding("escape", "dismiss", "Close", priority=True),
            ]

            def compose(self_inner) -> ComposeResult:
                with Vertical(classes="modal-dialog"):
                    yield Label("☰ Telegram Menu", classes="text-bold text-cyan")
                    yield Button("👤 My Profile", id="menu-profile", variant="primary")
                    yield Button("👥 Contacts", id="menu-contacts", variant="default")
                    yield Button("🔖 Saved Messages", id="menu-saved", variant="default")
                    yield Button("⚙️ Settings & Sessions", id="menu-settings", variant="default")
                    yield Button("📢 New Channel", id="menu-new-channel", variant="default")
                    yield Button("👥 New Group", id="menu-new-group", variant="default")
                    yield Button("🚪 Log Out", id="menu-logout", variant="error")
                    yield Button("Close", id="menu-close", variant="default")

            def on_button_pressed(self_inner, event: Button.Pressed) -> None:
                self_inner.dismiss()
                if event.button.id == "menu-profile":
                    self.action_open_profile()
                elif event.button.id == "menu-contacts":
                    self.action_open_contacts()
                elif event.button.id == "menu-saved":
                    self.on_chat_selected(0, "Saved Messages", "me")
                elif event.button.id == "menu-settings":
                    self.action_open_settings()
                elif event.button.id == "menu-new-channel":
                    self.on_new_chat_dialog("channel")
                elif event.button.id == "menu-new-group":
                    self.on_new_chat_dialog("group")
                elif event.button.id == "menu-logout":
                    self.client.log_out()
                    self.notify("Logged out successfully.")
                    self.exit()

        self.push_screen(HamburgerModal())

    def on_call_start(self, target: str, is_video: bool = False) -> None:
        self.push_screen(CallScreen(self.client, target=target, is_video=is_video))

    def on_new_chat_dialog(self, chat_type: str = "channel") -> None:
        self.push_screen(NewChatModal(self.client, chat_type=chat_type))

    def on_export_data(self, target: str, format_type: str) -> None:
        out_file = f"{target}_export.{format_type if format_type != 'sqlite' else 'db'}"
        try:
            if format_type == "xlsx":
                self.client.export_to_excel(target, out_file, limit=500)
            elif format_type == "sqlite":
                self.client.export_to_sqlite(target, out_file, limit=500)
            else:
                self.client.export_to_json(target, out_file, limit=500)
            self.notify(f"Dataset exported to {out_file}!", title="Exported")
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    def on_extract_wallets(self, target: str) -> None:
        try:
            data = self.client.extract_from_messages(target, limit=100)
            btc_count = len(data.get("wallets", {}).get("bitcoin", []))
            eth_count = len(data.get("wallets", {}).get("ethereum", []))
            emails_count = len(data.get("emails", []))
            self.notify(f"Discovered: {btc_count} BTC, {eth_count} ETH, {emails_count} Emails!", title="Extracted Data")
        except Exception as e:
            self.notify(f"Extraction failed: {e}", severity="error")

    # Action Handlers for Shortcuts
    def action_dismiss_modal(self) -> None:
        """Close topmost active modal or hide right info sidebar on Escape."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
        elif self._show_info:
            self.action_toggle_info()

    def action_toggle_info(self) -> None:
        right = self.query_one(RightChatInfoWidget)
        self._show_info = not self._show_info
        right.display = self._show_info

    def action_search(self) -> None:
        inp = self.query_one("#search-input")
        inp.focus()

    def action_new_chat(self) -> None:
        self.on_new_chat_dialog("channel")

    def action_open_profile(self) -> None:
        self.push_screen(ProfileModal(self.client))

    def action_open_contacts(self) -> None:
        def on_pick(c_id: Optional[str]):
            if c_id:
                self.on_chat_selected(int(c_id) if c_id.isdigit() else 0, f"Contact {c_id}", None)

        self.push_screen(ContactsModal(self.client, on_select_contact=on_pick))

    def action_open_settings(self) -> None:
        self.push_screen(SettingsModal(self.client))


def run_tui(client: Optional[TeleScraper] = None) -> None:
    """Entrypoint to launch TeleScraper Textual TUI."""
    app = TelegramApp(client)
    app.run()
