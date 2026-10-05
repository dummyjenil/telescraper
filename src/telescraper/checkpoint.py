"""
Resumable Scraping Checkpoint Manager.
Saves scraping offset progress to disk so interrupted scraping jobs resume seamlessly.
"""

import json
import os
import time
from typing import Optional, Dict, Any


class ScrapeCheckpoint:
    """Manages persistent progress for long-running scraping tasks."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_offset(self, target: str) -> int:
        """Get the last processed message ID for target."""
        return self.data.get(str(target), {}).get("last_id", 0)

    def update(self, target: str, last_message_id: int, total_increment: int = 1) -> None:
        """Update and save the last message ID."""
        key = str(target)
        if key not in self.data:
            self.data[key] = {"last_id": last_message_id, "total": 0, "last_updated": time.time()}

        self.data[key]["last_id"] = last_message_id
        self.data[key]["total"] = self.data[key].get("total", 0) + total_increment
        self.data[key]["last_updated"] = time.time()
        self.save()

    def save(self) -> None:
        """Write checkpoint to file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def reset(self, target: Optional[str] = None) -> None:
        """Reset progress for a target or all."""
        if target and str(target) in self.data:
            del self.data[str(target)]
        else:
            self.data.clear()
        self.save()
