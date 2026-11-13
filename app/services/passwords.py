"""Rule R18 for every new password: create user, admin reset, change password.

Besides length, email and "not the current one", a new password must not be a pattern
(owner decision, 13 Nov 2026): no repeats (aaaaaaaa, 12121212), no keys or letters in a row
(12345678, qwerty123, a1b2c3d4), no common password (P@ssw0rd2026!, Welcome@2026), and not the
person's name or email (Dara@2026). The dashboard runs the same checks while typing
(admin_dashboard/src/utils/password.ts); keep the two in step.
"""

import re

from app.errors import AppError, ErrorCode

REPEAT = "Do not repeat the same characters, like aaaaaaaa or 12121212."
RUN = "Do not use keys or letters in a row, like 12345678, abcdefgh or qwerty."
COMMON = "This password is too common. Pick one that is hard to guess."
PERSONAL = "Do not use your name or email in the password."

# Letters, digits and keyboard rows; a run is 3 or more of these in a row, either way.
SEQUENCES = (
    "abcdefghijklmnopqrstuvwxyz",
    "01234567890",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "qazwsxedcrfvtgbyhnujmikolp",
)
# Common passwords and words people build them from, once numbers and symbols are taken off
# the ends and look-alike swaps (p@ssw0rd) are undone.
COMMON_WORDS = frozenset(
    {
        "password", "passw", "pass", "passwd", "passcode", "welcome", "admin", "administrator",
        "root", "user", "login", "letmein", "iloveyou", "love", "loveyou", "monkey", "dragon",
        "master", "shadow", "sunshine", "princess", "football", "baseball", "soccer", "superman",
        "batman", "trustno", "whatever", "freedom", "hello", "secret", "changeme", "default",
        "guest", "test", "temp", "qwerty", "abc", "abcd", "asdf", "zxcv", "god", "money",
        "computer", "internet", "office", "company", "summer", "winter", "spring", "autumn",
        "nbc", "nationalbank", "bank", "cambodia", "kampuchea", "khmer", "phnompenh", "angkor",
        "meeting", "booking",
    }
)  # fmt: skip
LOOK_ALIKES = str.maketrans("@4310!$5", "aaeioiss")  # @→a 4→a 3→e 1→i 0→o !→i $→s 5→s
_EDGE = re.compile(r"^[^a-z]+|[^a-z]+$")


def _invalid(field: str, message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {field: message})


def _is_repeat(text: str) -> bool:
    """The text is one short block said again: aaaa, 1212, abcabcab."""
    if len(text) < 3:
        return False
    for size in range(1, len(text) // 2 + 1):
        if text == (text[:size] * (len(text) // size + 1))[: len(text)]:
            return True
    return False


def _is_run(text: str) -> bool:
    """3 or more keys or letters in a row, either way: abc, 4321, qwerty."""
    return len(text) >= 3 and any(text in seq or text in seq[::-1] for seq in SEQUENCES)


def _pattern(lower: str) -> str | None:
    """REPEAT or RUN when the password is only a pattern, else None.

    Looked at whole, then by kind (letters, digits, the rest): "qwerty123" and "a1b2c3d4" are
    two runs mixed. A kind with 1 or 2 characters says too little and does not count.
    """
    if _is_repeat(lower):
        return REPEAT
    kinds = [
        "".join(c for c in lower if c.isalpha()),
        "".join(c for c in lower if c.isdigit()),
        "".join(c for c in lower if not c.isalnum()),
    ]
    counted = [k for k in kinds if len(k) >= 3]
    if counted and all(_is_repeat(k) for k in counted):
        return REPEAT
    if counted and all(_is_repeat(k) or _is_run(k) for k in counted):
        return RUN
    return _pieces(lower)


def _pieces(lower: str) -> str | None:
    """REPEAT or RUN when the password is built from pattern pieces with at most 1 character
    left over: "12312344" is 123 + 123 again + 44; "4567456799" is 4567 + 4567 again + 99.

    From left to right, take the longest piece that starts here: the same character 2+ times
    (44), a run of 3+ (123, qwe), or 2+ characters already seen earlier (the second 123).
    The answer is REPEAT when something repeats in it (a doubled character, or 3 characters
    that come again: the 123 in 12312344), else RUN.
    """
    n = len(lower)
    i = left_over = 0
    while i < n:
        same = 1
        while i + same < n and lower[i + same] == lower[i]:
            same += 1
        run = next((k for k in range(n - i, 2, -1) if _is_run(lower[i : i + k])), 0)
        seen = next((k for k in range(n - i, 1, -1) if lower[i : i + k] in lower[:i]), 0)
        size = max(same if same >= 2 else 0, run, seen)
        if size:
            i += size
        else:
            left_over += 1
            i += 1
    if left_over > 1:
        return None
    return REPEAT if _has_repeat(lower) else RUN


def _has_repeat(lower: str) -> bool:
    """A doubled character (44), or 3 characters that come again later (123 ... 123)."""
    doubled = any(a == b for a, b in zip(lower, lower[1:], strict=False))
    return doubled or any(lower[j : j + 3] in lower[j + 3 :] for j in range(len(lower) - 2))


def _is_common(lower: str) -> bool:
    core = _EDGE.sub("", lower).translate(LOOK_ALIKES)
    return core in COMMON_WORDS or _EDGE.sub("", core) in COMMON_WORDS


def _personal_parts(email: str, name: str) -> set[str]:
    """Name and email words of 4 or more letters, and the email name joined (sokdara)."""
    local = email.strip().lower().split("@")[0]
    words = re.split(r"[^a-z]+", local) + re.split(r"[^a-z]+", name.lower())
    parts = {w for w in words if len(w) >= 4}
    joined = re.sub(r"[^a-z]+", "", local)
    if len(joined) >= 4:
        parts.add(joined)
    return parts


def check_new_password(
    password: str,
    email: str,
    field: str,
    current_password: str | None = None,
    *,
    name: str = "",
) -> None:
    """Raise 422 on `field` if `password` breaks R18.

    8 to 128 characters (also checked by the `Password` schema type), not the user's email
    (ignoring case), and, when changing, different from the current password. Then: not a
    pattern, not a common password, and no name or email word in it.
    Passwords are never trimmed.
    """
    if not 8 <= len(password) <= 128:
        raise _invalid(field, "Password must be 8 to 128 characters.")
    if password.lower() == email.strip().lower():
        raise _invalid(field, "Password cannot be your email.")
    if current_password is not None and password == current_password:
        raise _invalid(field, "Use a new password.")
    lower = password.lower()
    pattern = _pattern(lower)
    if pattern:
        raise _invalid(field, pattern)
    if _is_common(lower):
        raise _invalid(field, COMMON)
    plain = lower.translate(LOOK_ALIKES)
    if any(part in plain for part in _personal_parts(email, name)):
        raise _invalid(field, PERSONAL)
