"""
Login Screen for TeleScraper Textual TUI.
Supports QR Code Login (with ASCII QR widget), Phone+OTP Login, Bot Token, and 2FA Cloud Password.
"""

import time
from typing import Callable, Optional

import qrcode
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Label, Static, TabbedContent, TabPane

from ...client import TeleScraper
from ...errors import SessionPasswordNeededError
from ...tl import functions, types
from ...utils import get_display_name


def generate_ascii_qr(data: str) -> str:
    """Generate ASCII QR code string from data."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Render with Unicode half/full blocks for clean terminal view
    matrix = qr.get_matrix()
    lines = []
    for r in range(0, len(matrix), 2):
        line = ""
        for c in range(len(matrix[0])):
            top = matrix[r][c]
            bottom = matrix[r + 1][c] if r + 1 < len(matrix) else False
            if top and bottom:
                line += "█"
            elif top and not bottom:
                line += "▀"
            elif not top and bottom:
                line += "▄"
            else:
                line += " "
        lines.append(line)
    return "\n".join(lines)


class TwoFactorPasswordModal(ModalScreen[Optional[str]]):
    """Modal for entering 2FA Cloud Password."""

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("🔐 Two-Factor Authentication (2FA)", classes="text-bold")
            yield Label("Your Telegram account is protected with a cloud password.", classes="subtext")
            yield Input(placeholder="Enter 2FA Password", password=True, id="pwd-input")
            with Horizontal(classes="margin-top"):
                yield Button("Submit", variant="primary", id="btn-submit")
                yield Button("Cancel", variant="error", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            val = self.query_one("#pwd-input", Input).value
            self.dismiss(val)
        else:
            self.dismiss(None)


class LoginScreen(Screen):
    """Full-featured Telegram Authentication Screen."""

    qr_status = reactive("Initializing QR Code...")
    qr_ascii = reactive("")
    login_in_progress = reactive(False)

    def __init__(self, client: TeleScraper, on_success: Callable[[], None]):
        super().__init__()
        self.client = client
        self.on_success = on_success
        self._qr_login_obj = None
        self._qr_timer = None
        self._polling_active = False

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(classes="modal-dialog-large"):
                yield Label("⚡ TeleScraper Telegram Login", id="login-title", classes="text-bold text-cyan")
                yield Label("Pure Synchronous MTProto 2.0 Client", classes="subtext")

                with TabbedContent():
                    with TabPane("📱 QR Code Login", id="tab-qr"):
                        with Horizontal():
                            with Vertical(id="qr-box"):
                                yield Static(id="qr-display", classes="text-center")
                            with Vertical(id="qr-instructions"):
                                yield Label("1. Open Telegram on your phone.", classes="text-bold")
                                yield Label("2. Go to Settings -> Devices -> Link Desktop Device.")
                                yield Label("3. Point camera at the QR code.", classes="margin-bottom")
                                yield Static(id="qr-status-label")
                                yield Button("🔄 Refresh QR Code", id="btn-refresh-qr", variant="primary")

                    with TabPane("📞 Phone & OTP Code", id="tab-phone"):
                        with Vertical():
                            yield Label("Log in via SMS / Telegram App verification code:")
                            yield Input(placeholder="+1234567890 (Phone with country code)", id="phone-input")
                            yield Button("Send OTP Code", id="btn-send-code", variant="primary")
                            yield Input(placeholder="Enter received OTP code", id="code-input", disabled=True)
                            yield Button("Sign In", id="btn-phone-signin", variant="success", disabled=True)
                            yield Static(id="phone-status-label")

                    with TabPane("🤖 Bot Token", id="tab-bot"):
                        with Vertical():
                            yield Label("Authenticate as a Telegram Bot:")
                            yield Input(placeholder="123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ", id="bot-token-input")
                            yield Button("Log in as Bot", id="btn-bot-login", variant="primary")
                            yield Static(id="bot-status-label")

    def on_mount(self) -> None:
        self.start_qr_flow()

    def start_qr_flow(self) -> None:
        """Start or restart QR login flow."""
        try:
            self.client.connect()
            if self.client.is_user_authorized():
                self.on_success()
                return

            self._qr_login_obj = self.client.qr_login(print_qr=False)
            self.update_qr_display()
            self._polling_active = True
            self.set_timer(2.0, self.poll_qr_status)
        except Exception as e:
            self.query_one("#qr-status-label", Static).update(f"[red]Error initializing QR: {e}[/red]")

    def update_qr_display(self) -> None:
        if self._qr_login_obj and self._qr_login_obj.url:
            ascii_art = generate_ascii_qr(self._qr_login_obj.url)
            self.query_one("#qr-display", Static).update(ascii_art)
            self.query_one("#qr-status-label", Static).update("[cyan]Waiting for scan in Telegram app...[/cyan]")

    def poll_qr_status(self) -> None:
        """Poll Telegram server for QR approval."""
        if not self._polling_active or not self._qr_login_obj:
            return

        try:
            if time.time() >= self._qr_login_obj._expires:
                self._qr_login_obj.recreate()
                self.update_qr_display()

            res = self.client._invoke(
                functions.auth.ExportLoginTokenRequest(
                    api_id=self.client.api_id, api_hash=self.client.api_hash, except_ids=self._qr_login_obj.ignored_ids
                )
            )

            if isinstance(res, types.auth.LoginTokenSuccess):
                user = res.authorization.user
                self.client.session.user_id = user.id
                if hasattr(self.client.session, "save"):
                    self.client.session.save()
                self._polling_active = False
                self.notify(f"Logged in as {get_display_name(user)}!", title="Success", severity="information")
                self.on_success()
                return

            elif isinstance(res, types.auth.LoginTokenMigrateTo):
                self.client._switch_dc(res.dc_id)
                import_res = self.client._invoke(functions.auth.ImportLoginTokenRequest(token=res.token))
                if isinstance(import_res, types.auth.LoginTokenSuccess):
                    user = import_res.authorization.user
                    self.client.session.user_id = user.id
                    if hasattr(self.client.session, "save"):
                        self.client.session.save()
                    self._polling_active = False
                    self.notify(f"Logged in as {get_display_name(user)}!", title="Success", severity="information")
                    self.on_success()
                    return

        except SessionPasswordNeededError:
            self._polling_active = False
            self.app.push_screen(TwoFactorPasswordModal(), self.handle_2fa_result)
            return
        except Exception:
            pass

        if self._polling_active:
            self.set_timer(2.0, self.poll_qr_status)

    def handle_2fa_result(self, password: Optional[str]) -> None:
        if not password:
            self._polling_active = True
            self.poll_qr_status()
            return

        try:
            from ... import password as pwd_mod

            pwd_info = self.client._invoke(functions.account.GetPasswordRequest())
            input_check = pwd_mod.compute_check(pwd_info, password)
            res = self.client._invoke(functions.auth.CheckPasswordRequest(password=input_check))
            user = res.user
            self.client.session.user_id = user.id
            if hasattr(self.client.session, "save"):
                self.client.session.save()
            self.notify(f"2FA Approved: {get_display_name(user)}", title="Success", severity="information")
            self.on_success()
        except Exception as e:
            self.notify(f"2FA Failed: {e}", title="Error", severity="error")
            self.app.push_screen(TwoFactorPasswordModal(), self.handle_2fa_result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-qr":
            if self._qr_login_obj:
                self._qr_login_obj.recreate()
                self.update_qr_display()

        elif event.button.id == "btn-send-code":
            phone = self.query_one("#phone-input", Input).value.strip()
            if not phone:
                self.notify("Please enter a valid phone number", severity="warning")
                return
            try:
                self.client.connect()
                send_code_res = self.client._invoke(
                    functions.auth.SendCodeRequest(
                        phone_number=phone,
                        api_id=self.client.api_id,
                        api_hash=self.client.api_hash,
                        settings=types.CodeSettings(),
                    )
                )
                self._phone_code_hash = send_code_res.phone_code_hash
                self._phone_number = phone
                self.query_one("#code-input", Input).disabled = False
                self.query_one("#btn-phone-signin", Button).disabled = False
                self.query_one("#phone-status-label", Static).update(
                    "[green]OTP code sent! Check Telegram or SMS.[/green]"
                )
            except Exception as e:
                self.query_one("#phone-status-label", Static).update(f"[red]Error sending code: {e}[/red]")

        elif event.button.id == "btn-phone-signin":
            code = self.query_one("#code-input", Input).value.strip()
            try:
                sign_in_res = self.client._invoke(
                    functions.auth.SignInRequest(
                        phone_number=self._phone_number, phone_code_hash=self._phone_code_hash, phone_code=code
                    )
                )
                user = sign_in_res.user
                self.client.session.user_id = user.id
                if hasattr(self.client.session, "save"):
                    self.client.session.save()
                self.notify(f"Logged in as {get_display_name(user)}!", title="Success")
                self.on_success()
            except SessionPasswordNeededError:
                self.app.push_screen(TwoFactorPasswordModal(), self.handle_2fa_result)
            except Exception as e:
                self.query_one("#phone-status-label", Static).update(f"[red]Sign in error: {e}[/red]")

        elif event.button.id == "btn-bot-login":
            token = self.query_one("#bot-token-input", Input).value.strip()
            if token:
                try:
                    self.client.bot_login(token)
                    self.notify("Logged in as Bot!", title="Success")
                    self.on_success()
                except Exception as e:
                    self.query_one("#bot-status-label", Static).update(f"[red]Bot login error: {e}[/red]")
