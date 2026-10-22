from argon2 import PasswordHasher

from app.security import hash_password


def test_hash_password_uses_argon2id():
    hashed = hash_password("MyPassword@123")
    assert hashed.startswith("$argon2id$")
    assert "MyPassword@123" not in hashed
    assert PasswordHasher().verify(hashed, "MyPassword@123")


def test_same_password_hashes_differently_each_time():
    assert hash_password("MyPassword@123") != hash_password("MyPassword@123")


def test_password_is_not_trimmed():
    hashed = hash_password(" abc12345")
    assert PasswordHasher().verify(hashed, " abc12345")
    try:
        PasswordHasher().verify(hashed, "abc12345")
    except Exception:
        pass
    else:
        raise AssertionError("a password with a leading space must differ from one without")


def test_hashes_khmer_password():
    hashed = hash_password("ពាក្យសម្ងាត់១២៣")
    assert PasswordHasher().verify(hashed, "ពាក្យសម្ងាត់១២៣")
