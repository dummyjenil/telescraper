"""
Interactive Modals and Dialogs for TeleScraper TUI:
- NotSupportedModal
- ConfirmModal
- EditMessageModal
- ReactionPickerModal
- FilePickerModal
"""

from typing import Optional, Callable
from pathlib import Path
from textual.binding import Binding
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, Static
from textual.containers import Vertical, Horizontal, Grid


class NotSupportedModal(ModalScreen):
    """Clean modal explaining that a feature is not yet supported in the library/TUI."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("enter", "dismiss", "OK", priority=True),
    ]

    def __init__(self, feature_name: str, details: Optional[str] = None):
        super().__init__()
        self.feature_name = feature_name
        self.details = details or "This operation is not yet supported by TeleScraper pure synchronous MTProto client."

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"⚠️ Feature Not Supported: {self.feature_name}", classes="text-bold text-yellow", markup=False)
            yield Label(self.details, classes="margin-top subtext", markup=False)
            with Horizontal(classes="margin-top"):
                yield Button("OK", id="btn-ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class ConfirmModal(ModalScreen[bool]):
    """Confirmation Dialog for sensitive actions (e.g. message deletion)."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, title: str, message: str, confirm_label: str = "Confirm", is_danger: bool = True):
        super().__init__()
        self.modal_title = title
        self.message_text = message
        self.confirm_label = confirm_label
        self.is_danger = is_danger

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(self.modal_title, classes="text-bold text-cyan", markup=False)
            yield Label(self.message_text, classes="margin-top", markup=False)
            with Horizontal(classes="margin-top"):
                yield Button(self.confirm_label, id="btn-confirm", variant="error" if self.is_danger else "primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class EditMessageModal(ModalScreen[Optional[str]]):
    """Modal to edit an outgoing Telegram message."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, original_text: str):
        super().__init__()
        self.original_text = original_text

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog-large"):
            yield Label("✎ Edit Message", classes="text-bold text-cyan", markup=False)
            yield Input(value=self.original_text, id="edit-msg-input")
            with Horizontal(classes="margin-top"):
                yield Button("Save Changes", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            val = self.query_one("#edit-msg-input", Input).value.strip()
            self.dismiss(val if val else None)
        else:
            self.dismiss(None)


class ReactionPickerModal(ModalScreen[Optional[str]]):
    """Modal to pick a reaction emoji for a message."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    AVAILABLE_EMOJIS = ["👍", "❤️", "🔥", "👏", "🎉", "🤩", "😢", "😮", "😂", "👎", "💩", "🙏"]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("⚡ React to Message", classes="text-bold text-cyan", markup=False)
            with Horizontal(classes="margin-top"):
                for idx, emo in enumerate(self.AVAILABLE_EMOJIS[:6]):
                    yield Button(emo, id=f"btn-emo-{idx}", name=emo, classes="min-width-4")
            with Horizontal(classes="margin-top"):
                for idx, emo in enumerate(self.AVAILABLE_EMOJIS[6:], start=6):
                    yield Button(emo, id=f"btn-emo-{idx}", name=emo, classes="min-width-4")
            with Horizontal(classes="margin-top"):
                yield Button("Cancel", id="btn-cancel", variant="default")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("btn-emo-"):
            emoji = event.button.name or str(event.button.label)
            self.dismiss(emoji)
        else:
            self.dismiss(None)


class FilePickerModal(ModalScreen[Optional[str]]):
    """Modal to enter path of a local file/photo to send."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("📁 Send File / Media", classes="text-bold text-cyan", markup=False)
            yield Label("Enter local file path to upload:", classes="subtext", markup=False)
            yield Input(placeholder="/home/user/image.png or ./document.pdf", id="file-path-input")
            with Horizontal(classes="margin-top"):
                yield Button("Send File", id="btn-send-file", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-send-file":
            path_str = self.query_one("#file-path-input", Input).value.strip()
            if not path_str:
                self.notify("Please specify a file path", severity="warning")
                return
            p = Path(path_str).expanduser()
            if not p.exists():
                self.notify(f"File not found: {path_str}", severity="error")
                return
            self.dismiss(str(p.resolve()))
        else:
            self.dismiss(None)
