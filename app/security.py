from argon2 import PasswordHasher

# Argon2id with the library defaults (spec section 9). Not bcrypt: it cuts passwords at 72 bytes.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password exactly as typed. Passwords are never trimmed."""
    return _hasher.hash(password)
