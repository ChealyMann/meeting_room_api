"""R18: a new password is not a pattern, not a common password, and not the person's name."""

import pytest

from app.errors import AppError
from app.services.passwords import check_new_password

EMAIL = "sok.dara@company.com"
NAME = "Sok Dara"

REPEAT = "Do not repeat the same characters, like aaaaaaaa or 12121212."
RUN = "Do not use keys or letters in a row, like 12345678, abcdefgh or qwerty."
COMMON = "This password is too common. Pick one that is hard to guess."
PERSONAL = "Do not use your name or email in the password."


def problem(password: str, email: str = EMAIL, name: str = NAME) -> str | None:
    try:
        check_new_password(password, email, "new_password", name=name)
    except AppError as error:
        return error.fields["new_password"]
    return None


@pytest.mark.parametrize(
    "password",
    [
        "aaaaaaaa",
        "11111111",
        "12121212",
        "abcabcab",
        "ABababAB",
        "zz9!zz9!",
        "aaaa1111",
        "12312344",
        "11223344",
        "aabbccdd",
        "4567456799",
    ],
)
def test_repeats_are_refused(password):
    assert problem(password) == REPEAT


@pytest.mark.parametrize(
    "password",
    [
        "12345678",
        "87654321",
        "abcdefgh",
        "HGFEDCBA",
        "qwertyui",
        "asdfghjkl",
        "qwerty123",
        "1q2w3e4r",
        "a1b2c3d4",
        "abc!def@",
        "zxcvbnm1",
        "zxc123zxc",
        "x1234567",
    ],
)
def test_runs_are_refused(password):
    assert problem(password) == RUN


@pytest.mark.parametrize(
    "password",
    [
        "password",
        "Password1",
        "P@ssw0rd2026!",
        "Welcome@2026",
        "admin1234",
        "iloveyou",
        "2026Letmein!",
        "nbc@2026!!",
    ],
)
def test_common_passwords_are_refused(password):
    assert problem(password) == COMMON


@pytest.mark.parametrize(
    ("password", "email", "name"),
    [
        ("Dara@2026!", EMAIL, NAME),
        ("mysokdara9", EMAIL, NAME),
        ("D4r4-Kampot", EMAIL, NAME),
        ("chanthy.rain", "chanthy@company.com", "Lim Chanthy"),
        ("vibol#River7", "x.vibol@company.com", "X"),
    ],
)
def test_name_or_email_is_refused(password, email, name):
    assert problem(password, email, name) == PERSONAL


@pytest.mark.parametrize(
    "password",
    [
        "Mekong River 7",
        "q7!x2#m9",
        "aB3$kP9!",
        "Tonle-Sap-Blue",
        "green tea at 4",
        "Kampot pepper 88",
        "Sok7!rain-kite",  # a 3-letter name part alone is too short to count
        "Kite@Mekong-7",
        "93817264",
        "pepper and tea 88",
    ],
)
def test_good_passwords_pass(password):
    assert problem(password) is None


def test_old_rules_come_first():
    assert problem("aaaa") == "Password must be 8 to 128 characters."
    assert problem("Sok.Dara@company.com") == "Password cannot be your email."


def test_same_as_current_is_still_refused():
    with pytest.raises(AppError) as caught:
        check_new_password("Mekong River 7", EMAIL, "new_password", "Mekong River 7", name=NAME)
    assert caught.value.fields == {"new_password": "Use a new password."}


def test_name_is_optional():
    assert problem("Mekong River 7", name="") is None
