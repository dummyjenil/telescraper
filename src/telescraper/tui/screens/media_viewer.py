"""
Media & ASCII Image Viewer Modal for TeleScraper TUI.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class MediaViewerModal(ModalScreen):
    """Full-screen image/media viewer with ASCII rendering and file details."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close / Back", priority=True),
    ]

    def __init__(self, file_path: str, title: str = "Media Viewer"):
        super().__init__()
        self.file_path = file_path
        self.viewer_title = title

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog-large"):
            yield Label(f"🖼️ {self.viewer_title}", classes="text-bold text-cyan")
            yield Label(f"File: {self.file_path}", classes="subtext")

            with ScrollableContainer(classes="media-card height-1fr"):
                yield Static(self._generate_ascii_preview(), id="media-ascii-preview")

            with Horizontal(classes="margin-top"):
                yield Button("📋 Copy Path", id="btn-copy-path", variant="primary")
                yield Button("Close", id="btn-close", variant="default")

    def _generate_ascii_preview(self) -> str:
        """Render ASCII representation of image if pillow is available, else banner."""
        p = Path(self.file_path)
        if not p.exists():
            return f"[red]File not found on disk: {self.file_path}[/red]"

        try:
            from PIL import Image

            img = Image.open(p)
            img = img.convert("L")
            w, h = img.size
            aspect_ratio = h / w
            new_w = 60
            new_h = int(aspect_ratio * new_w * 0.55)
            img = img.resize((new_w, new_h))

            chars = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
            pixels = img.getdata()
            ascii_str = ""
            for i, px in enumerate(pixels):
                ascii_str += chars[px // 25]
                if (i + 1) % new_w == 0:
                    ascii_str += "\n"
            return ascii_str
        except Exception:
            size_mb = p.stat().st_size / (1024 * 1024)
            return (
                f"┌────────────────────────────────────────────────────────┐\n"
                f"│                📷 MEDIA FILE DETAILS                   │\n"
                f"├────────────────────────────────────────────────────────┤\n"
                f"│ File Name: {p.name:<43} │\n"
                f"│ Size:      {size_mb:.2f} MB{' ':34} │\n"
                f"│ Path:      {str(p.resolve())[:43]:<43} │\n"
                f"└────────────────────────────────────────────────────────┘"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()
        elif event.button.id == "btn-copy-path":
            self.app.copy_to_clipboard(str(Path(self.file_path).resolve()))
            self.notify("File path copied to clipboard!", title="Copied")
