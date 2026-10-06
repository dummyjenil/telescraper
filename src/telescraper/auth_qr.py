"""
QR Code Login Support for Telegram.
Generates tg://login URL and handles polling/approval in pure synchronous Python.
"""

import base64
import getpass
import time
from typing import Any, Callable, List, Optional

from .errors import RPCError, SessionPasswordNeededError
from .tl import functions, types


class QRLogin:
    """
    Handles Telegram QR Code authentication synchronously.
    """

    def __init__(self, client: Any, ignored_ids: Optional[List[int]] = None):
        self._client = client
        self.ignored_ids = ignored_ids or []
        self._token: Optional[bytes] = None
        self._expires: int = 0
        self.recreate()

    def recreate(self) -> "QRLogin":
        """Request a new login token from Telegram servers."""
        res = self._client._invoke(
            functions.auth.ExportLoginTokenRequest(
                api_id=self._client.api_id, api_hash=self._client.api_hash, except_ids=self.ignored_ids
            )
        )
        if isinstance(res, types.auth.LoginToken):
            self._token = res.token
            self._expires = int(res.expires.timestamp()) if hasattr(res.expires, "timestamp") else int(time.time() + 30)
        return self

    @property
    def token(self) -> bytes:
        return self._token or b""

    @property
    def url(self) -> str:
        """The `tg://login?token=...` URL for scanning in Telegram mobile app."""
        if not self._token:
            return ""
        encoded = base64.urlsafe_b64encode(self._token).decode("utf-8").rstrip("=")
        return f"tg://login?token={encoded}"

    def print_qr(self) -> None:
        """Print instructions and QR code to the terminal."""
        print("\n" + "=" * 60)
        print("📱 TELEGRAM QR CODE LOGIN")
        print("=" * 60)
        print("1. Open Telegram on your phone.")
        print("2. Go to Settings -> Devices -> Link Desktop Device.")
        print("3. Point your camera at the QR code below:")
        print("=" * 60 + "\n")

        try:
            import qrcode

            qr = qrcode.QRCode(border=2)
            qr.add_data(self.url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        except ImportError:
            pass

        print(f"\nDirect Login URL: {self.url}\n")
        print("Waiting for QR code scan on mobile app...\n")

    def _handle_2fa(self, password_callback: Optional[Callable[[], str]] = None) -> Any:
        """Authenticate 2FA password after QR scan."""
        if password_callback:
            pwd = password_callback()
        else:
            print("\n🔐 2FA Cloud Password is required on this account.")
            pwd = getpass.getpass("Enter 2FA Password: ")

        from . import password as pwd_mod

        pwd_info = self._client._invoke(functions.account.GetPasswordRequest())
        input_check = pwd_mod.compute_check(pwd_info, pwd)
        res = self._client._invoke(functions.auth.CheckPasswordRequest(password=input_check))
        user = res.user
        self._client.session.user_id = user.id
        if hasattr(self._client.session, "save"):
            self._client.session.save()
        print(f"[✔] 2FA Login approved! Logged in as: {getattr(user, 'first_name', user.id)} (ID: {user.id})")
        return user

    def wait(
        self,
        timeout: float = 120.0,
        password_callback: Optional[Callable[[], str]] = None,
        auto_handle_2fa: bool = True,
    ) -> Any:
        """
        Block and wait until the QR code is scanned on mobile or timeout expires.

        :param timeout: Maximum seconds to wait
        :param password_callback: Optional function returning 2FA password
        :param auto_handle_2fa: If True, automatically prompts/handles 2FA password if required
        :return: Authorized User object
        """
        start = time.time()
        last_token = self._token

        while time.time() - start < timeout:
            # Check if token expired
            if time.time() >= self._expires:
                self.recreate()
                if self._token != last_token:
                    last_token = self._token
                    print("\n[!] QR Code refreshed:")
                    self.print_qr()

            try:
                res = self._client._invoke(
                    functions.auth.ExportLoginTokenRequest(
                        api_id=self._client.api_id, api_hash=self._client.api_hash, except_ids=self.ignored_ids
                    )
                )

                if isinstance(res, types.auth.LoginTokenSuccess):
                    user = res.authorization.user
                    self._client.session.user_id = user.id
                    if hasattr(self._client.session, "save"):
                        self._client.session.save()
                    print(
                        f"[✔] QR Login approved! Logged in as: {getattr(user, 'first_name', user.id)} (ID: {user.id})"
                    )
                    return user

                elif isinstance(res, types.auth.LoginTokenMigrateTo):
                    # Migrate to target DC
                    self._client._switch_dc(res.dc_id)
                    import_res = self._client._invoke(functions.auth.ImportLoginTokenRequest(token=res.token))
                    if isinstance(import_res, types.auth.LoginTokenSuccess):
                        user = import_res.authorization.user
                        self._client.session.user_id = user.id
                        if hasattr(self._client.session, "save"):
                            self._client.session.save()
                        print(
                            f"[✔] QR Login approved on migrated DC! Logged in as: {getattr(user, 'first_name', user.id)} (ID: {user.id})"
                        )
                        return user

            except SessionPasswordNeededError as e:
                if auto_handle_2fa:
                    return self._handle_2fa(password_callback)
                raise e
            except RPCError:
                pass

            time.sleep(2.0)

        raise TimeoutError("QR Login timed out without being scanned.")
