"""
Pure Synchronous CDN File Decrypter and Verifier.
Decrypts CDN-redirected files using AES-CTR and verifies SHA-256 piece hashes.
"""

from hashlib import sha256
from typing import List, Tuple
from .aesctr import AESModeCTR
from ..errors import SecurityError


class CdnDecrypter:
    """
    Handles transparent decryption and cryptographic piece verification of CDN files.
    """

    def __init__(self, key: bytes, iv: bytes):
        self.key = key
        self.iv = iv
        self._decrypter = AESModeCTR(key, iv)

    def decrypt_chunk(self, encrypted_bytes: bytes) -> bytes:
        """Decrypts a chunk of encrypted CDN data."""
        return self._decrypter.decrypt(encrypted_bytes)

    @staticmethod
    def verify_piece_hash(piece_bytes: bytes, expected_hash: bytes) -> bool:
        """Verify that decrypted piece matches its SHA-256 hash."""
        computed = sha256(piece_bytes).digest()
        if computed != expected_hash:
            raise SecurityError(
                f"CDN piece SHA-256 verification failed: {computed.hex()} != {expected_hash.hex()}"
            )
        return True
