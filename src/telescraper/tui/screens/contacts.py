"""
Contacts Screen & Manager for TeleScraper TUI.
"""

from typing import Callable, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView

from ...client import TeleScraper
from ...models import MemberData


class AddContactModal(ModalScreen[Optional[dict]]):
    """Modal dialog to add or import a new contact."""

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("➕ Add New Contact", classes="text-bold text-cyan", markup=False)
            yield Label("Phone Number (with country code):", classes="subtext", markup=False)
            yield Input(placeholder="+919876543210", id="input-phone")
            yield Label("First Name:", classes="subtext", markup=False)
            yield Input(placeholder="First Name (Required)", id="input-fname")
            yield Label("Last Name (Optional):", classes="subtext", markup=False)
            yield Input(placeholder="Last Name", id="input-lname")
            with Horizontal(classes="margin-top"):
                yield Button("Save Contact", id="btn-save-contact", variant="success")
                yield Button("Cancel", id="btn-cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save-contact":
            phone = self.query_one("#input-phone", Input).value.strip()
            fname = self.query_one("#input-fname", Input).value.strip()
            lname = self.query_one("#input-lname", Input).value.strip()

            if not phone or not fname:
                self.notify("Phone number and First Name are required!", title="Error", severity="error")
                return

            self.dismiss(
                {
                    "phone": phone,
                    "first_name": fname,
                    "last_name": lname,
                }
            )


class ContactsModal(ModalScreen[Optional[str]]):
    """Contacts list modal with search, chat launcher, add contact, and sorting (By Name / Last Seen)."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close / Back", priority=True),
        Binding("ctrl+s", "toggle_sort", "Toggle Sort", priority=True),
    ]

    def __init__(self, client: TeleScraper, on_select_contact: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.client = client
        self.on_select_contact = on_select_contact
        self._contacts_cache: List[MemberData] = []
        self.sort_mode: str = "name"  # 'name' or 'last_seen'

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog-large"):
            with Horizontal():
                yield Label("👥 Telegram Contacts", classes="text-bold text-cyan width-1fr", markup=False)
                yield Button("🔤 Sort: By Name", id="btn-toggle-sort", variant="default")
            yield Input(placeholder="🔍 Search contacts by name, phone, or @username...", id="contact-search")
            yield ListView(id="contacts-list-view")
            with Horizontal(classes="margin-top"):
                yield Button("Open Chat", id="btn-open-chat", variant="primary")
                yield Button("➕ Add Contact", id="btn-add-contact", variant="success")
                yield Button("Close", id="btn-close", variant="error")

    def on_mount(self) -> None:
        self.load_contacts()

    def action_toggle_sort(self) -> None:
        self._toggle_sort()

    def _toggle_sort(self) -> None:
        btn = self.query_one("#btn-toggle-sort", Button)
        if self.sort_mode == "name":
            self.sort_mode = "last_seen"
            btn.label = "⏱️ Sort: Last Seen"
            btn.variant = "primary"
        else:
            self.sort_mode = "name"
            btn.label = "🔤 Sort: By Name"
            btn.variant = "default"

        self._sort_and_refresh()

    def load_contacts(self) -> None:
        lv = self.query_one("#contacts-list-view", ListView)
        lv.clear()
        try:
            contacts = self.client.get_contacts(sort_by=self.sort_mode)
            self._contacts_cache = contacts
            self._sort_and_refresh()
        except Exception as e:
            lv.append(ListItem(Label(f"Error loading contacts: {e}", markup=False)))

    def _sort_and_refresh(self) -> None:
        if self.sort_mode == "last_seen":
            self._contacts_cache.sort(key=lambda m: m.last_seen_time or 0.0, reverse=True)
        else:
            self._contacts_cache.sort(key=lambda m: (m.full_name or "").lower())

        q = self.query_one("#contact-search", Input).value.strip().lower()
        if not q:
            self._render_contacts(self._contacts_cache)
        else:
            filtered = [
                m
                for m in self._contacts_cache
                if q in (m.full_name or "").lower() or q in (m.username or "").lower() or q in (m.phone or "").lower()
            ]
            self._render_contacts(filtered)

    def _render_contacts(self, contacts: List[MemberData]) -> None:
        lv = self.query_one("#contacts-list-view", ListView)
        lv.clear()
        if not contacts:
            lv.append(ListItem(Label("No contacts found", classes="subtext", markup=False)))
            return

        for m in contacts:
            name = m.full_name or "User"
            uname = f"@{m.username}" if m.username else (m.phone or "")
            if (
                m.status
                and "online" in m.status.lower()
                and "offline" not in m.status.lower()
                and "seen" not in m.status.lower()
            ):
                status_str = "🟢 Online"
            elif m.status:
                status_str = f"⚪ {m.status}"
            else:
                status_str = "⚪ Offline"

            item = ListItem(
                Horizontal(
                    Label(
                        f"👤 {name} ({uname})".strip() if uname else f"👤 {name}",
                        classes="text-bold width-1fr",
                        markup=False,
                    ),
                    Label(status_str, classes="subtext", markup=False),
                ),
                name=str(m.user_id),
            )
            lv.append(item)

    def on_input_changed(self, event: Input.Changed) -> None:
        q = event.value.lower().strip()
        if not q:
            self._render_contacts(self._contacts_cache)
            return

        filtered = []
        for m in self._contacts_cache:
            name = (m.full_name or "").lower()
            uname = (m.username or "").lower()
            phone = (m.phone or "").lower()
            if q in name or q in uname or q in phone:
                filtered.append(m)
        self._render_contacts(filtered)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(None)
        elif event.button.id == "btn-toggle-sort":
            self._toggle_sort()
        elif event.button.id == "btn-open-chat":
            lv = self.query_one("#contacts-list-view", ListView)
            if lv.highlighted_child and lv.highlighted_child.name:
                contact_id = lv.highlighted_child.name
                if self.on_select_contact:
                    self.on_select_contact(contact_id)
                self.dismiss(contact_id)
        elif event.button.id == "btn-add-contact":

            def on_added(res: Optional[dict]):
                if res:
                    try:
                        imported = self.client.import_contacts([res])
                        if imported:
                            self.notify(f"Contact {res['first_name']} added successfully!", title="Success")
                            self.load_contacts()
                        else:
                            self.notify(
                                "Could not import contact (user may not be registered on Telegram).",
                                title="Notice",
                                severity="warning",
                            )
                    except Exception as e:
                        self.notify(f"Failed to add contact: {e}", title="Error", severity="error")

            self.app.push_screen(AddContactModal(), on_added)
