"""Shared at-rest encryption for third-party credentials and signing secrets.

Reuses the platform Fernet key (settings.ZATCA_KEY_ENCRYPTION_KEY) so one
rotated secret protects all encrypted columns. The financials.zatca module
keeps its own thin wrappers for compliance-specific error semantics.
"""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class SecretEncryptionError(Exception):
    """The encryption key is missing/invalid or a ciphertext is corrupt."""


def _fernet():
    key = settings.ZATCA_KEY_ENCRYPTION_KEY
    if not key:
        raise SecretEncryptionError(
            "ZATCA_KEY_ENCRYPTION_KEY is not configured; refusing to store "
            "secrets without encryption at rest."
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise SecretEncryptionError(
            "The encryption key is not a valid Fernet key."
        ) from exc


def encrypt_secret(plaintext):
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext):
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise SecretEncryptionError("Stored secret failed decryption.") from exc
