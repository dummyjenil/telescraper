"""Pure Synchronous Media Downloader using MTProto upload.GetFileRequest."""

import os
from typing import Optional, Callable, Any
from .tl.functions.upload import GetFileRequest
from .tl.types import upload, Message, MessageMediaPhoto, MessageMediaDocument
from .utils import get_input_location, get_extension
from .exceptions import DownloadError

CHUNK_SIZE = 128 * 1024  # 128 KB chunks (must be divisible by 4KB)


def download_media_sync(
    client: Any,
    message: Any,
    output_dir: str = "./downloads",
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Optional[str]:
    """
    Pure synchronous media downloader for Telegram messages.

    :param client: TeleScraper client instance
    :param message: MessageData or raw TL Message object
    :param output_dir: Directory to save file
    :param filename: Custom output file name
    :param progress_callback: fn(received_bytes, total_bytes)
    :return: Absolute path of downloaded file
    """
    raw_msg = getattr(message, 'raw_message', message)
    if not raw_msg or not getattr(raw_msg, 'media', None):
        return None

    media = raw_msg.media
    dc_id, input_location = get_input_location(media)
    if not input_location:
        return None

    # Determine file size & name
    total_size = 0
    inferred_name = None

    if isinstance(media, MessageMediaPhoto):
        inferred_name = f"photo_{raw_msg.id}.jpg"
        # Total size from largest photo size if available
        if hasattr(media.photo, 'sizes') and media.photo.sizes:
            largest = media.photo.sizes[-1]
            total_size = getattr(largest, 'size', 0)
    elif isinstance(media, MessageMediaDocument):
        doc = media.document
        total_size = getattr(doc, 'size', 0)
        ext = get_extension(media) or '.bin'
        inferred_name = f"doc_{raw_msg.id}{ext}"
        if doc and hasattr(doc, 'attributes'):
            for attr in doc.attributes:
                if hasattr(attr, 'file_name') and attr.file_name:
                    inferred_name = attr.file_name
                    break

    final_name = filename or inferred_name or f"file_{raw_msg.id}.bin"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, final_name)

    offset = 0
    received = 0

    try:
        with open(out_path, 'wb') as f:
            while True:
                req = GetFileRequest(
                    location=input_location,
                    offset=offset,
                    limit=CHUNK_SIZE
                )
                res = client._invoke(req, dc_id=dc_id)

                if isinstance(res, upload.File):
                    chunk = res.bytes
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    offset += len(chunk)

                    if progress_callback:
                        progress_callback(received, total_size or received)

                    if len(chunk) < CHUNK_SIZE:
                        break
                else:
                    break

        return os.path.abspath(out_path)
    except Exception as e:
        if os.path.exists(out_path) and os.path.getsize(out_path) == 0:
            os.remove(out_path)
        raise DownloadError(f"Failed to download media: {e}") from e
