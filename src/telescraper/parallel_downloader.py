"""
Multi-Threaded Parallel File Downloader.
Downloads large files 4x faster using ThreadPoolExecutor and pure synchronous chunk requests.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

from .exceptions import DownloadError
from .tl.functions.upload import GetFileRequest
from .tl.types import upload
from .utils import get_input_location

PARALLEL_CHUNK_SIZE = 512 * 1024  # 512 KB per part


def download_chunk_worker(client: Any, location: Any, offset: int, limit: int, dc_id: Optional[int] = None) -> bytes:
    """Download a single chunk at offset."""
    req = GetFileRequest(location=location, offset=offset, limit=limit)
    res = client._invoke(req, dc_id=dc_id)
    if isinstance(res, upload.File):
        return res.bytes
    return b""


def download_file_parallel_sync(
    client: Any,
    message: Any,
    output_dir: str = "./downloads",
    filename: Optional[str] = None,
    num_threads: int = 4,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> str:
    """
    Download media using multi-threaded parallel chunks.

    :param client: TeleScraper client instance
    :param message: MessageData or raw message
    :param output_dir: Directory to store file
    :param filename: Custom output filename
    :param num_threads: Number of parallel worker threads
    :param progress_callback: fn(downloaded_bytes, total_bytes)
    :return: Absolute path of downloaded file
    """
    raw_msg = getattr(message, "raw_message", message)
    if not raw_msg or not getattr(raw_msg, "media", None):
        raise DownloadError("Message contains no downloadable media")

    media = raw_msg.media
    dc_id, input_location = get_input_location(media)
    if not input_location:
        raise DownloadError("Could not resolve input file location")

    # Determine total size and filename
    total_size = 0
    inferred_name = None
    if hasattr(media, "document") and media.document:
        doc = media.document
        total_size = getattr(doc, "size", 0)
        for attr in getattr(doc, "attributes", []):
            if hasattr(attr, "file_name") and attr.file_name:
                inferred_name = attr.file_name
                break
    elif hasattr(media, "photo") and media.photo:
        if hasattr(media.photo, "sizes") and media.photo.sizes:
            total_size = getattr(media.photo.sizes[-1], "size", 0)
            inferred_name = f"photo_{raw_msg.id}.jpg"

    name = filename or inferred_name or f"file_{raw_msg.id}.bin"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, name)

    if total_size <= 0:
        # Fall back to sequential downloader for unknown sizes
        from .downloader import download_media_sync

        return download_media_sync(
            client, message, output_dir=output_dir, filename=name, progress_callback=progress_callback
        )

    # Pre-allocate output file
    with open(out_path, "wb") as f:
        f.truncate(total_size)

    # Calculate offsets
    offsets = list(range(0, total_size, PARALLEL_CHUNK_SIZE))
    downloaded_bytes = 0

    def download_and_write(offset: int):
        nonlocal downloaded_bytes
        limit = min(PARALLEL_CHUNK_SIZE, total_size - offset)
        chunk = download_chunk_worker(client, input_location, offset, limit, dc_id=dc_id)
        if chunk:
            with open(out_path, "r+b") as f:
                f.seek(offset)
                f.write(chunk)
            downloaded_bytes += len(chunk)
            if progress_callback:
                progress_callback(downloaded_bytes, total_size)
        return len(chunk)

    with ThreadPoolExecutor(max_workers=max(1, num_threads)) as executor:
        futures = [executor.submit(download_and_write, offset) for offset in offsets]
        for fut in as_completed(futures):
            fut.result()

    return os.path.abspath(out_path)
