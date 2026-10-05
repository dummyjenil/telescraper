"""
Message Bubble Widget for TeleScraper Textual TUI.
Renders text formatting, media attachments, polls, replies, forwards, reactions, and action menus.
"""

from typing import Optional, Callable, Any
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Button, Static, ProgressBar
from textual.containers import Vertical, Horizontal
from .audio_player import AudioPlayerWidget


class MessageBubbleWidget(Widget):
    """Rich Telegram Message Bubble with clean Unicode support."""

    def __init__(
        self,
        msg_id: int,
        sender_name: str,
        text: str,
        date_str: str,
        is_outgoing: bool = False,
        media_type: Optional[str] = None,
        media_name: Optional[str] = None,
        media_size: Optional[int] = None,
        reply_to_text: Optional[str] = None,
        forward_from: Optional[str] = None,
        views: Optional[int] = None,
        reactions: Optional[dict] = None,
        is_pinned: bool = False,
        poll_data: Optional[dict] = None,
        on_action: Optional[Callable[[str, Any], None]] = None
    ):
        super().__init__()
        self.msg_id = msg_id
        self.sender_name = sender_name
        self.msg_text = text or ""
        self.date_str = date_str
        self.is_outgoing = is_outgoing
        self.media_type = media_type
        self.media_name = media_name
        self.media_size = media_size
        self.reply_to_text = reply_to_text
        self.forward_from = forward_from
        self.views = views
        self.reactions = reactions or {}
        self.is_pinned = is_pinned
        self.poll_data = poll_data
        self.on_action = on_action

    def compose(self) -> ComposeResult:
        bubble_class = "-outgoing" if self.is_outgoing else "-incoming"
        row_class = "-outgoing" if self.is_outgoing else "-incoming"

        with Horizontal(classes=f"message-row {row_class}"):
            with Vertical(classes=f"message-bubble {bubble_class}"):
                
                # 1. Sender Header (for incoming messages)
                if not self.is_outgoing and self.sender_name:
                    yield Label(f"👤 {self.sender_name}", classes="sender-name", markup=False)

                # 2. Pinned Indicator
                if self.is_pinned:
                    yield Label("📌 Pinned Message", classes="text-yellow text-bold", markup=False)

                # 3. Forward Header
                if self.forward_from:
                    yield Label(f"Forwarded from {self.forward_from}", classes="forward-header", markup=False)

                # 4. Reply-To Header
                if self.reply_to_text:
                    yield Label(f"↩ Replying to: {self.reply_to_text}", classes="reply-header", markup=False)

                # 5. Media Attachments
                if self.media_type == "photo":
                    with Vertical(classes="media-card"):
                        yield Label("📷 [Photo Attachment]", classes="media-badge", markup=False)
                        yield Static(
                            "┌────────────────────────────┐\n"
                            "│     [ 🖼️ Photo Preview ]    │\n"
                            "└────────────────────────────┘",
                            classes="text-center",
                            markup=False
                        )
                        yield Button("👁️ View Photo", id=f"btn-view-{self.msg_id}", variant="primary")

                elif self.media_type in ("audio", "voice"):
                    yield AudioPlayerWidget(
                        filename=self.media_name or "Voice Message",
                        duration=120,
                        is_voice=(self.media_type == "voice")
                    )

                elif self.media_type in ("document", "video"):
                    with Vertical(classes="media-card"):
                        icon = "🎬 Video" if self.media_type == "video" else "📄 Document"
                        size_mb = (self.media_size or 0) / (1024 * 1024)
                        size_str = f"({size_mb:.2f} MB)" if size_mb > 0 else ""
                        yield Label(f"{icon}: {self.media_name or 'file'} {size_str}", classes="media-badge", markup=False)
                        yield Button("⬇️ Download File", id=f"btn-download-{self.msg_id}", variant="default")

                elif self.poll_data:
                    with Vertical(classes="media-card"):
                        yield Label(f"📊 Poll: {self.poll_data.get('question', 'Vote')}", classes="text-bold text-cyan", markup=False)
                        for idx, opt in enumerate(self.poll_data.get('options', [])):
                            with Horizontal(classes="margin-top"):
                                yield Button(f"Vote: {opt}", id=f"btn-vote-{self.msg_id}-{idx}", variant="primary")

                # 6. Main Message Text (with markup=False for exact Hindi / Gujarati / special chars rendering)
                if self.msg_text:
                    yield Static(self.msg_text, classes="message-text", markup=False)

                # 7. Reactions Row
                if self.reactions:
                    with Horizontal(classes="reactions-bar"):
                        for emo, count in self.reactions.items():
                            yield Label(f"{emo} {count} ", classes="text-cyan", markup=False)

                # 8. Footer: Views & Time
                views_str = f"👁️ {self.views}  " if self.views is not None else ""
                tick_str = " ✓✓" if self.is_outgoing else ""
                yield Label(f"{views_str}{self.date_str}{tick_str}", classes="message-meta", markup=False)

                # 9. Quick Actions Row
                with Horizontal(classes="margin-top"):
                    yield Button("↩ Reply", id=f"btn-reply-{self.msg_id}", variant="default")
                    yield Button("⚡ React", id=f"btn-react-{self.msg_id}", variant="default")
                    yield Button("📌 Pin", id=f"btn-pin-{self.msg_id}", variant="default")
                    if self.is_outgoing:
                        yield Button("✎ Edit", id=f"btn-edit-{self.msg_id}", variant="default")
                        yield Button("🗑️ Delete", id=f"btn-del-{self.msg_id}", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if not self.on_action:
            return

        if btn_id.startswith("btn-reply-"):
            self.on_action("reply", self.msg_id)
        elif btn_id.startswith("btn-pin-"):
            self.on_action("pin", self.msg_id)
        elif btn_id.startswith("btn-edit-"):
            self.on_action("edit", (self.msg_id, self.msg_text))
        elif btn_id.startswith("btn-del-"):
            self.on_action("delete", self.msg_id)
        elif btn_id.startswith("btn-react-"):
            self.on_action("react", self.msg_id)
        elif btn_id.startswith("btn-view-"):
            self.on_action("view", self.msg_id)
        elif btn_id.startswith("btn-download-"):
            self.on_action("download", self.msg_id)
        elif btn_id.startswith("btn-vote-"):
            parts = btn_id.split("-")
            opt_idx = int(parts[-1]) if parts[-1].isdigit() else 0
            self.on_action("vote", (self.msg_id, opt_idx))
