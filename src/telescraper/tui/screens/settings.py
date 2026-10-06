"""
Settings & Session Management Screen for TeleScraper TUI.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Select, Static, TabbedContent, TabPane

from ...client import TeleScraper


class SettingsModal(ModalScreen):
    """Settings, Active Sessions/Devices, Transports, and Session Management."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close / Back", priority=True),
    ]

    def __init__(self, client: TeleScraper):
        super().__init__()
        self.client = client

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog-large"):
            yield Label("⚙️ TeleScraper Settings & Sessions", classes="text-bold text-cyan")

            with TabbedContent():
                with TabPane("💻 Active Devices", id="tab-devices"):
                    yield Label("Authorized Telegram Devices & Logins:")
                    yield ListView(id="devices-list-view")
                    with Horizontal(classes="margin-top"):
                        yield Button("🔄 Refresh List", id="btn-refresh-devices")
                        yield Button("🗑️ Terminate Other Sessions", id="btn-terminate-others", variant="error")

                with TabPane("🛡️ Transports & DPI", id="tab-transports"):
                    yield Label("Anti-Censorship MTProto Connection Transports:")
                    yield Select(
                        [
                            ("Intermediate (Standard MTProto)", "intermediate"),
                            ("Randomized Intermediate (DPI Evasion)", "randomized"),
                            ("Obfuscated2 (AES-CTR Handshake)", "obfuscated"),
                            ("MTProxy (Telegram MTProxy Support)", "mtproxy"),
                            ("HTTP POST Fallback (Port 80/443)", "http"),
                        ],
                        value="intermediate",
                        id="select-transport",
                    )
                    yield Static("Choose transport to evade ISP censorship or firewalls.", classes="subtext")

                with TabPane("🔑 StringSession", id="tab-string-session"):
                    yield Label("Export Account Session as Base64 String (Telethon / TeleScraper):")
                    yield Static(id="string-session-box", classes="media-card")
                    yield Button("📋 Copy StringSession", id="btn-copy-string", variant="primary")

            with Horizontal(classes="margin-top"):
                yield Button("🚪 Log Out", id="btn-logout", variant="error")
                yield Button("Close", id="btn-close", variant="default")

    def on_mount(self) -> None:
        self.load_devices()
        self.load_string_session()

    def load_devices(self) -> None:
        lv = self.query_one("#devices-list-view", ListView)
        lv.clear()
        try:
            auths = self.client.get_authorizations()
            for a in auths:
                is_cur = " (Current Device)" if getattr(a, "current", False) else ""
                dev_str = f"💻 {a.device_model} - {a.platform} {is_cur}"
                ip_str = f"IP: {a.ip} ({a.country}) | App: {a.app_name} {a.app_version}"
                lv.append(
                    ListItem(
                        Vertical(Label(dev_str, classes="text-bold"), Label(ip_str, classes="subtext")),
                        name=str(a.hash),
                    )
                )
        except Exception as e:
            lv.append(ListItem(Label(f"Error loading devices: {e}")))

    def load_string_session(self) -> None:
        try:
            from ...sessions.string_session import StringSession

            ss = StringSession.save(self.client.session)
            preview = f"{ss[:40]}...{ss[-20:]}"
            self.query_one("#string-session-box", Static).update(preview)
            self._full_string_session = ss
        except Exception as e:
            self.query_one("#string-session-box", Static).update(f"Error: {e}")
            self._full_string_session = ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()
        elif event.button.id == "btn-refresh-devices":
            self.load_devices()
        elif event.button.id == "btn-terminate-others":
            try:
                self.client.reset_authorizations()
                self.notify("All other sessions terminated successfully!", title="Sessions")
                self.load_devices()
            except Exception as e:
                self.notify(f"Failed to reset: {e}", severity="error")
        elif event.button.id == "btn-copy-string":
            if getattr(self, "_full_string_session", None):
                self.app.copy_to_clipboard(self._full_string_session)
                self.notify("StringSession copied to clipboard!", title="Copied")
        elif event.button.id == "btn-logout":
            try:
                self.client.log_out()
                self.notify("Logged out successfully.", title="Logout")
                self.dismiss()
                self.app.exit()
            except Exception as e:
                self.notify(f"Logout error: {e}", severity="error")
