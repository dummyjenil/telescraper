"""
Inline Audio & Voice Message Player Widget for TeleScraper TUI.
"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Button, Static, ProgressBar
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive


class AudioPlayerWidget(Widget):
    """Interactive player bar for Voice notes, Music, and Audio files."""

    is_playing = reactive(False)
    progress = reactive(0.0)

    def __init__(self, filename: str, duration: int = 180, is_voice: bool = False):
        super().__init__()
        self.filename = filename
        self.duration = duration
        self.is_voice = is_voice
        self._timer = None

    def compose(self) -> ComposeResult:
        type_icon = "🎙️ Voice Message" if self.is_voice else "🎵 Audio Track"
        with Vertical(classes="media-card"):
            yield Label(f"{type_icon}: {self.filename}", classes="text-bold text-cyan")
            with Horizontal(classes="align-middle"):
                yield Button("▶ Play", id="btn-play-pause", variant="primary", classes="min-width-8")
                yield ProgressBar(total=100, show_percentage=False, show_eta=False, id="audio-progress", classes="width-1fr")
                yield Label(f"00:00 / {self._format_time(self.duration)}", id="audio-time-label", classes="subtext")

    def _format_time(self, seconds: int) -> str:
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-play-pause":
            self.is_playing = not self.is_playing
            event.button.label = "⏸ Pause" if self.is_playing else "▶ Play"
            event.button.variant = "error" if self.is_playing else "primary"
            
            if self.is_playing:
                self._timer = self.set_interval(0.5, self._tick_progress)
            else:
                if self._timer:
                    self._timer.stop()

    def _tick_progress(self) -> None:
        if self.is_playing:
            self.progress += 2.0
            if self.progress > 100.0:
                self.progress = 0.0
                self.is_playing = False
                self.query_one("#btn-play-pause", Button).label = "▶ Play"
                self.query_one("#btn-play-pause", Button).variant = "primary"
                if self._timer:
                    self._timer.stop()

            bar = self.query_one("#audio-progress", ProgressBar)
            bar.progress = self.progress
            curr_sec = int((self.progress / 100.0) * self.duration)
            self.query_one("#audio-time-label", Label).update(
                f"{self._format_time(curr_sec)} / {self._format_time(self.duration)}"
            )
