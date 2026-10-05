"""
Poll & Quiz Creator Modal for TeleScraper TUI.
"""

from typing import Optional
from textual.binding import Binding
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, Checkbox
from textual.containers import Vertical, Horizontal


class PollCreatorModal(ModalScreen[Optional[dict]]):
    """Create and dispatch Telegram Polls / Quizzes."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close / Back", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("📊 Create New Telegram Poll", classes="text-bold text-cyan")
            
            yield Input(placeholder="Ask a question...", id="poll-question")
            yield Input(placeholder="Option 1", id="poll-opt-1")
            yield Input(placeholder="Option 2", id="poll-opt-2")
            yield Input(placeholder="Option 3 (optional)", id="poll-opt-3")
            yield Input(placeholder="Option 4 (optional)", id="poll-opt-4")
            
            with Horizontal(classes="margin-top"):
                yield Checkbox("Anonymous Voting", value=True, id="poll-anon")
                yield Checkbox("Multiple Answers", value=False, id="poll-multi")

            with Horizontal(classes="margin-top"):
                yield Button("Send Poll", id="btn-send-poll", variant="success")
                yield Button("Cancel", id="btn-cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-send-poll":
            q = self.query_one("#poll-question", Input).value.strip()
            o1 = self.query_one("#poll-opt-1", Input).value.strip()
            o2 = self.query_one("#poll-opt-2", Input).value.strip()
            o3 = self.query_one("#poll-opt-3", Input).value.strip()
            o4 = self.query_one("#poll-opt-4", Input).value.strip()
            
            if not q or not o1 or not o2:
                self.notify("Question and at least 2 options are required", severity="warning")
                return

            opts = [o for o in [o1, o2, o3, o4] if o]
            anon = self.query_one("#poll-anon", Checkbox).value
            multi = self.query_one("#poll-multi", Checkbox).value

            self.dismiss({
                "question": q,
                "options": opts,
                "anonymous": anon,
                "multiple": multi
            })
