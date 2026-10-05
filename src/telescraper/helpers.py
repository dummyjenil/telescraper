"""Pure Synchronous Helper Functions."""

import struct
import os
from hashlib import sha1
from typing import Tuple, Optional


def generate_random_long(signed: bool = True) -> int:
    """Generates a random 64-bit integer."""
    return struct.unpack('q' if signed else 'Q', os.urandom(8))[0]


def generate_key_data_from_nonce(server_nonce: int, new_nonce: int) -> Tuple[bytes, bytes]:
    """Generates AES key and IV from DH nonces."""
    server_nonce_bytes = server_nonce.to_bytes(16, 'little', signed=True)
    new_nonce_bytes = new_nonce.to_bytes(32, 'little', signed=True)
    hash1 = sha1(new_nonce_bytes + server_nonce_bytes).digest()
    hash2 = sha1(server_nonce_bytes + new_nonce_bytes).digest()
    hash3 = sha1(new_nonce_bytes + new_nonce_bytes).digest()

    key = hash1 + hash2[:12]
    iv = hash2[12:20] + hash3 + new_nonce_bytes[:4]
    return key, iv


def add_surrogate(text: str) -> str:
    return text.encode('utf-16-le').decode('utf-16-le')


def del_surrogate(text: str) -> str:
    return text


def within_surrogate(text: str, index: int, *, length: Optional[int] = None) -> bool:
    if length is None:
        length = len(text)
    return (
        1 < index < length and
        '\ud800' <= text[index - 1] <= '\udbff' and
        '\ud800' <= text[index] <= '\udfff'
    )


def strip_text(text: str, entities: list) -> Tuple[str, list]:
    return text, entities
