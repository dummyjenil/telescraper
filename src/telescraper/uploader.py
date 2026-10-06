"""
Pure Synchronous File and Media Uploader for Telegram.
Handles small files, documents, photos, audio and 2GB large files.
Supports multi-threaded parallel chunk uploads using ThreadPoolExecutor.
100% Pure Synchronous, Zero Asyncio.
"""

import io
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import md5
from typing import Any, Callable, List, Optional, Tuple, Union

from .helpers import generate_random_long
from .tl import functions, types

UPLOAD_CHUNK_SIZE = 512 * 1024  # 512 KB per part


def upload_file_sync(
    client: Any,
    file_path: Union[str, bytes, io.BytesIO],
    filename: Optional[str] = None,
    workers: int = 1,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Union[types.InputFile, types.InputFileBig]:
    """
    Upload a local file or bytes buffer to Telegram servers synchronously.

    :param client: TeleScraper instance
    :param file_path: File system path, raw bytes, or BytesIO stream
    :param filename: Optional custom filename
    :param workers: Number of parallel thread workers (default 1 for sequential, 4-8 for fast)
    :param progress_callback: fn(sent_bytes, total_bytes)
    :return: InputFile or InputFileBig ready to attach to messages
    """
    if isinstance(file_path, str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        file_size = os.path.getsize(file_path)
        inferred_name = os.path.basename(file_path)
        stream = open(file_path, "rb")
        should_close = True
    elif isinstance(file_path, bytes):
        file_size = len(file_path)
        inferred_name = "file.bin"
        stream = io.BytesIO(file_path)
        should_close = True
    elif hasattr(file_path, "read"):
        stream = file_path
        stream.seek(0, os.SEEK_END)
        file_size = stream.tell()
        stream.seek(0)
        inferred_name = getattr(file_path, "name", "file.bin")
        should_close = False
    else:
        raise ValueError("Invalid file input")

    name = filename or inferred_name or "file.bin"
    file_id = generate_random_long()
    is_big = file_size > 10 * 1024 * 1024  # > 10 MB uses BigFilePart
    total_parts = max(1, math.ceil(file_size / UPLOAD_CHUNK_SIZE))
    uploaded_bytes = 0
    progress_lock = threading.Lock()
    file_hash = md5()

    try:
        if workers <= 1:
            # Sequential chunk upload
            for part_index in range(total_parts):
                chunk = stream.read(UPLOAD_CHUNK_SIZE)
                if not chunk and part_index > 0:
                    break

                if not is_big:
                    file_hash.update(chunk)
                    req = functions.upload.SaveFilePartRequest(file_id=file_id, file_part=part_index, bytes=chunk)
                else:
                    req = functions.upload.SaveBigFilePartRequest(
                        file_id=file_id, file_part=part_index, file_total_parts=total_parts, bytes=chunk
                    )

                client._invoke(req)
                uploaded_bytes += len(chunk)

                if progress_callback:
                    progress_callback(uploaded_bytes, file_size)
        else:
            # Multi-threaded parallel chunk upload
            chunks: List[Tuple[int, bytes]] = []
            for part_index in range(total_parts):
                chunk = stream.read(UPLOAD_CHUNK_SIZE)
                if not chunk and part_index > 0:
                    break
                if not is_big:
                    file_hash.update(chunk)
                chunks.append((part_index, chunk))

            def _upload_chunk_task(part_idx: int, part_data: bytes):
                nonlocal uploaded_bytes
                if not is_big:
                    req = functions.upload.SaveFilePartRequest(file_id=file_id, file_part=part_idx, bytes=part_data)
                else:
                    req = functions.upload.SaveBigFilePartRequest(
                        file_id=file_id, file_part=part_idx, file_total_parts=total_parts, bytes=part_data
                    )
                client._invoke(req)
                with progress_lock:
                    uploaded_bytes += len(part_data)
                    if progress_callback:
                        progress_callback(uploaded_bytes, file_size)

            with ThreadPoolExecutor(max_workers=min(workers, total_parts)) as executor:
                futures = [executor.submit(_upload_chunk_task, idx, data) for idx, data in chunks]
                for future in as_completed(futures):
                    future.result()

        if is_big:
            return types.InputFileBig(id=file_id, parts=total_parts, name=name)
        else:
            return types.InputFile(id=file_id, parts=total_parts, name=name, md5_checksum=file_hash.hexdigest())
    finally:
        if should_close:
            stream.close()
