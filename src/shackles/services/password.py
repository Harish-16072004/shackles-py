"""Password hashing — bcrypt wrapper.

Uses bcrypt directly (not passlib, which wraps bcrypt but has
deprecation warnings on newer Python versions).
"""

import bcrypt

from shackles.config import settings


# Cost factor — higher is slower but more secure. Matches the Node
# app's BCRYPT_ROUNDS = 12.
_BCRYPT_ROUNDS = 12


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password for storage.

    Returns a 60-character bcrypt hash string starting with `$2b$`.
    """
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plaintext.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash.

    Constant-time comparison — safe against timing attacks.
    """
    if not plaintext or not hashed:
        return False
    try:
        return bcrypt.checkpw(
            plaintext.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Malformed hash — treat as a mismatch
        return False


def needs_rehash(hashed: str) -> bool:
    """Check whether a stored hash was generated with a weaker cost factor.

    Used during login to transparently upgrade old hashes. Returns True
    if the hash uses a cost factor lower than the current setting.
    """
    if not hashed.startswith("$2b$"):
        return True
    try:
        parts = hashed.split("$")
        current_rounds = int(parts[2])
        return current_rounds < _BCRYPT_ROUNDS
    except (IndexError, ValueError):
        return True