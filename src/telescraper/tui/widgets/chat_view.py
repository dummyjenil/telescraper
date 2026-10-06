"""
Main Chat Area Widget for TeleScraper Textual TUI.
"""

from typing import Any, Callable, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label

from ...client import TeleScraper
from .composer import ComposerWidget
from .message_bubble import MessageBubbleWidget


class ChatViewWidget(Widget):
    """Main Chat Panel with Header, Pinned Banner, Message List, and Composer."""

    current_chat_title = reactive("Select a Chat")
    current_chat_subtitle = reactive("No chat selected")

    def __init__(
        self,
        client: TeleScraper,
        on_call_click: Callable[[str, bool], None],
        on_info_click: Callable[[], None],
        on_send_message: Callable[[str, Optional[int]], None],
        on_attach_file: Callable[[], None],
        on_create_poll: Callable[[], None],
    ):
        super().__init__(id="chat-area")
        self.client = client
        self.on_call_click = on_call_click
        self.on_info_click = on_info_click
        self.on_send_message = on_send_message
        self.on_attach_file = on_attach_file
        self.on_create_poll = on_create_poll
        self.active_target: Optional[str] = None
        self.active_username: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Vertical():
            # Top Chat Header
            with Horizontal(id="chat-header"):
                with Vertical(id="chat-header-info"):
                    yield Label(self.current_chat_title, id="chat-header-title", markup=False)
                    yield Label(self.current_chat_subtitle, id="chat-header-subtitle", markup=False)

                with Horizontal(id="chat-header-actions"):
                    yield Button("📞", id="btn-header-call", variant="default", classes="min-width-4")
                    yield Button("📹", id="btn-header-video", variant="default", classes="min-width-4")
                    yield Button("ℹ️", id="btn-header-info", variant="default", classes="min-width-4")

            # Messages History Container
            with ScrollableContainer(id="messages-container"):
                yield Label(
                    "Select a conversation from the left sidebar to start chatting.",
                    classes="subtext text-center margin-top",
                    markup=False,
                )

            # Bottom Composer
            yield ComposerWidget(
                on_send_message=self._handle_send,
                on_attach_file=self.on_attach_file,
                on_create_poll=self.on_create_poll,
            )

    def load_chat(self, target: str, title: str, username: Optional[str] = None) -> None:
        self.active_target = str(target)
        self.active_username = username
        self.current_chat_title = title
        self.current_chat_subtitle = f"@{username}" if username else f"ID: {target}"

        self.query_one("#chat-header-title", Label).update(title)
        self.query_one("#chat-header-subtitle", Label).update(self.current_chat_subtitle)

        # Load messages from Telegram
        container = self.query_one("#messages-container", ScrollableContainer)
        container.remove_children()

        try:
            msgs = self.client.get_messages(target, limit=30)
            if not msgs:
                container.mount(Label("No messages in this chat yet.", classes="subtext text-center", markup=False))
                return

            for m in reversed(msgs):
                is_out = (m.sender_id == getattr(self.client.session, "user_id", None)) or (target in ("me", "0"))
                m_type = m.media.media_type if m.media else None
                m_name = m.media.file_name if m.media else None
                m_size = m.media.file_size if m.media else None
                date_s = str(m.date)[11:16] if m.date else "12:00"

                bubble = MessageBubbleWidget(
                    msg_id=m.id,
                    sender_name=m.sender_name or ("You" if is_out else "User"),
                    text=m.text,
                    date_str=date_s,
                    is_outgoing=is_out,
                    media_type=m_type,
                    media_name=m_name,
                    media_size=m_size,
                    views=m.views,
                    on_action=self._handle_message_action,
                )
                container.mount(bubble)

            container.scroll_end(animate=False)
        except Exception as e:
            container.mount(Label(f"Error loading messages: {e}", markup=False))

    def _handle_send(self, text: str) -> None:
        composer = self.query_one(ComposerWidget)
        reply_to = composer.replying_to_id
        if self.active_target:
            self.on_send_message(text, reply_to)

    def _handle_message_action(self, action: str, data: Any) -> None:
        from ..screens.dialogs import ConfirmModal, EditMessageModal, NotSupportedModal, ReactionPickerModal

        if action == "reply":
            msg_id = data
            composer = self.query_one(ComposerWidget)
            composer.set_reply(msg_id, f"Message #{msg_id}")

        elif action == "pin" and self.active_target:
            msg_id = data
            try:
                self.client.pin_message(self.active_target, msg_id)
                self.notify(f"Pinned message #{msg_id}", title="Pinned")
            except Exception as e:
                self.app.push_screen(
                    NotSupportedModal(
                        "Pin Message", f"Could not pin message #{msg_id}: {e} (Admin rights may be required)"
                    )
                )

        elif action == "delete" and self.active_target:
            msg_id = data

            def confirm_del(confirmed: bool):
                if confirmed:
                    try:
                        self.client.delete_messages(self.active_target, [msg_id])
                        self.notify(f"Deleted message #{msg_id}", title="Deleted")
                        self.load_chat(self.active_target, self.current_chat_title, self.active_username)
                    except Exception as e:
                        self.app.push_screen(
                            NotSupportedModal("Delete Message", f"Telegram server rejected deletion: {e}")
                        )

            self.app.push_screen(
                ConfirmModal("🗑️ Delete Message", f"Are you sure you want to delete message #{msg_id}?", "Delete"),
                confirm_del,
            )

        elif action == "edit" and self.active_target:
            msg_id, original_text = data

            def save_edit(new_text: Optional[str]):
                if new_text and new_text != original_text:
                    try:
                        self.client.edit_message(self.active_target, msg_id, new_text)
                        self.notify("Message edited successfully!", title="Edited")
                        self.load_chat(self.active_target, self.current_chat_title, self.active_username)
                    except Exception as e:
                        self.app.push_screen(
                            NotSupportedModal("Edit Message", f"Failed to edit message #{msg_id}: {e}")
                        )

            self.app.push_screen(EditMessageModal(original_text), save_edit)

        elif action == "react" and self.active_target:
            msg_id = data

            def handle_reaction(emoji: Optional[str]):
                if emoji:
                    try:
                        self.client.send_reaction(self.active_target, msg_id, emoji)
                        self.notify(f"Reacted with {emoji}!")
                    except Exception as e:
                        self.app.push_screen(
                            NotSupportedModal("Reactions", f"Reactions not allowed or failed in this chat: {e}")
                        )

            self.app.push_screen(ReactionPickerModal(), handle_reaction)

        elif action == "vote":
            msg_id, opt_idx = data
            self.app.push_screen(
                NotSupportedModal(
                    "Interactive Poll Voting",
                    "Voting on Telegram polls is not supported yet in TeleScraper MTProto library.",
                )
            )

        elif action == "download" and self.active_target:
            msg_id = data
            try:
                msgs = self.client.get_messages(self.active_target, limit=50)
                for m in msgs:
                    if m.id == msg_id:
                        saved = m.download(output_dir="./downloads")
                        self.notify(f"Saved file to {saved}", title="Downloaded")
                        break
            except Exception as e:
                self.app.push_screen(NotSupportedModal("Media Download", f"Download failed: {e}"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-header-call" and self.active_target:
            self.on_call_click(self.active_target, False)
        elif event.button.id == "btn-header-video" and self.active_target:
            self.on_call_click(self.active_target, True)
        elif event.button.id == "btn-header-info":
            self.on_info_click()
