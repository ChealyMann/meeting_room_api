"""Rule R18 for every new password: create user, admin reset, change password."""

from app.errors import AppError, ErrorCode


def _invalid(field: str, message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", {field: message})


def check_new_password(
    password: str, email: str, field: str, current_password: str | None = None
) -> None:
    """Raise 422 on `field` if `password` breaks R18.

    8 to 128 characters (also checked by the `Password` schema type), not the user's email
    (ignoring case), and, when changing, different from the current password.
    Passwords are never trimmed.
    """
    if not 8 <= len(password) <= 128:
        raise _invalid(field, "Password must be 8 to 128 characters.")
    if password.lower() == email.strip().lower():
        raise _invalid(field, "Password cannot be your email.")
    if current_password is not None and password == current_password:
        raise _invalid(field, "Use a new password.")
