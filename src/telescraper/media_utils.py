"""
Media Processing Utilities:
- Pillow image resizing & JPEG progressive optimization.
- Hachoir video dimensions & audio duration inspector.
"""

import io
import os
from typing import Any, Dict, Tuple


def resize_image_sync(
    file_source: Any, max_dimension: int = 2560, quality: int = 85
) -> Tuple[io.BytesIO, Tuple[int, int]]:
    """
    Resize image to Telegram acceptable bounds (max 2560x2560) and encode to JPEG.
    Uses PIL / Pillow if installed.

    :param file_source: File path, bytes, or BytesIO
    :param max_dimension: Maximum allowed width or height
    :param quality: JPEG quality
    :return: (BytesIO buffer, (width, height))
    """
    try:
        from PIL import Image
    except ImportError:
        # If Pillow is not installed, return raw input without modification
        if isinstance(file_source, bytes):
            return io.BytesIO(file_source), (0, 0)
        elif isinstance(file_source, str):
            with open(file_source, "rb") as f:
                return io.BytesIO(f.read()), (0, 0)
        return file_source, (0, 0)

    if isinstance(file_source, (str, os.PathLike)):
        img = Image.open(file_source)
    elif isinstance(file_source, bytes):
        img = Image.open(io.BytesIO(file_source))
    else:
        img = Image.open(file_source)

    w, h = img.size
    if w > max_dimension or h > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        w, h = img.size

    # Convert RGBA to RGB for JPEG
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, progressive=True)
    output.seek(0)
    return output, (w, h)


def inspect_media_metadata(file_path: str) -> Dict[str, Any]:
    """
    Inspect media file dimensions and duration using hachoir if available.
    """
    metadata: Dict[str, Any] = {
        "duration": None,
        "width": None,
        "height": None,
        "mime_type": None,
    }

    try:
        from hachoir.metadata import extractMetadata
        from hachoir.parser import createParser

        parser = createParser(file_path)
        if not parser:
            return metadata

        with parser:
            meta = extractMetadata(parser)
            if meta:
                if meta.has("duration"):
                    metadata["duration"] = int(meta.get("duration").total_seconds())
                if meta.has("width"):
                    metadata["width"] = int(meta.get("width"))
                if meta.has("height"):
                    metadata["height"] = int(meta.get("height"))
                if meta.has("mime_type"):
                    metadata["mime_type"] = meta.get("mime_type")
    except Exception:
        pass

    return metadata
