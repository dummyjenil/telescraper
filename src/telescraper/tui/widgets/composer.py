"""
Message Composer Bar Widget for TeleScraper Textual TUI.
"""

from typing import Callable, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label


class ComposerWidget(Widget):
    """Bottom input bar with attachments, voice messages, polls, and emoji support."""

    def __init__(
        self,
        on_send_message: Callable[[str], None],
        on_attach_file: Optional[Callable[[], None]] = None,
        on_create_poll: Optional[Callable[[], None]] = None,
        on_record_voice: Optional[Callable[[], None]] = None,
    ):
        super().__init__(id="composer-container")
        self.on_send_message = on_send_message
        self.on_attach_file = on_attach_file
        self.on_create_poll = on_create_poll
        self.on_record_voice = on_record_voice
        self.replying_to_id: Optional[int] = None

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="composer-actions-row"):
                yield Button("📎 Attach", id="btn-attach", variant="default")
                yield Button("📊 Poll", id="btn-poll", variant="default")
                yield Button("🎙️ Voice Note", id="btn-voice", variant="default")
                yield Button("😀 Emoji", id="btn-emoji", variant="default")
                yield Label("", id="reply-indicator-label", classes="text-yellow")

            with Horizontal(id="composer-input-row"):
                yield Input(placeholder="Write a message...", id="message-input")
                yield Button("Send 📤", id="send-button", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-button":
            self.submit_message()
        elif event.button.id == "btn-attach" and self.on_attach_file:
            self.on_attach_file()
        elif event.button.id == "btn-poll" and self.on_create_poll:
            self.on_create_poll()
        elif event.button.id == "btn-voice":
            from ..screens.dialogs import NotSupportedModal

            self.app.push_screen(
                NotSupportedModal(
                    "Live Voice Recording", "Microphone audio capture is not supported in the terminal environment."
                )
            )
        elif event.button.id == "btn-emoji":
            from ..screens.dialogs import ReactionPickerModal

            def insert_emoji(emo: Optional[str]):
                if emo:
                    inp = self.query_one("#message-input", Input)
                    inp.value += f" {emo} "
                    inp.focus()

            self.app.push_screen(ReactionPickerModal(), insert_emoji)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit_message()

    def submit_message(self) -> None:
        inp = self.query_one("#message-input", Input)
        txt = inp.value.strip()
        if txt:
            self.on_send_message(txt)
            inp.value = ""
            self.clear_reply()

    def set_reply(self, msg_id: int, snippet: str) -> None:
        self.replying_to_id = msg_id
        self.query_one("#reply-indicator-label", Label).update(f"↩ Replying to #{msg_id} (Esc to cancel)")

    def clear_reply(self) -> None:
        self.replying_to_id = None
        self.query_one("#reply-indicator-label", Label).update("")
