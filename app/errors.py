from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(StrEnum):
    """The complete list of error codes (spec section 17). Do not add others."""

    WRONG_PASSWORD = "WRONG_PASSWORD"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    DUPLICATE = "DUPLICATE"
    INACTIVE_REFERENCE = "INACTIVE_REFERENCE"
    DIVISION_REQUIRED = "DIVISION_REQUIRED"
    OWNER_INVALID = "OWNER_INVALID"
    LAST_ADMIN = "LAST_ADMIN"
    SELF_ACTION_NOT_ALLOWED = "SELF_ACTION_NOT_ALLOWED"
    PHOTO_LIMIT_REACHED = "PHOTO_LIMIT_REACHED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_IMAGE = "INVALID_IMAGE"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode | str,
        status: int,
        message: str,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = ErrorCode(code)
        self.status = status
        self.message = message
        self.fields = fields
        self.headers = headers


def error_response(
    code: ErrorCode,
    status: int,
    message: str,
    fields: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict = {"code": code.value, "message": message}
    if fields:
        error["fields"] = fields
    return JSONResponse({"error": error}, status_code=status, headers=headers)


# Framework HTTP errors mapped to spec codes. Anything else becomes a validation error.
_HTTP_ERRORS: dict[int, tuple[ErrorCode, str]] = {
    401: (ErrorCode.UNAUTHORIZED, "Please sign in."),
    403: (ErrorCode.FORBIDDEN, "You are not allowed."),
    404: (ErrorCode.NOT_FOUND, "Not found."),
    405: (ErrorCode.METHOD_NOT_ALLOWED, "Method not allowed."),
    413: (ErrorCode.FILE_TOO_LARGE, "File too big."),
    415: (ErrorCode.UNSUPPORTED_FILE_TYPE, "Wrong file type."),
}

_LOCATIONS = {"body", "query", "path", "header", "cookie"}


def _field_path(loc: tuple) -> str:
    parts = [str(part) for part in loc]
    if len(parts) > 1 and parts[0] in _LOCATIONS:
        parts = parts[1:]
    if parts and parts[0] == "body" and len(parts) == 1:
        return "body"
    return ".".join(parts)


def _field_message(error: dict) -> str:
    context = error.get("ctx") or {}
    if error["type"] == "missing" or (error["input"] is None and error["type"].endswith("_type")):
        # Left out, or `null` sent for a required field.
        return "This field is required."
    match error["type"]:
        case "string_too_short" if context.get("min_length") == 1:
            return "This field is required."
        case "string_too_long":
            return f"Too long (max {context['max_length']})."
        case "extra_forbidden":
            return "Unknown field."
        case "json_invalid":
            return "Invalid JSON."
        case "value_error":
            # Our own validators: the message is written for the client already.
            return str(context["error"])
        case _:
            return error["msg"]


def _validation_fields(exc: RequestValidationError) -> dict[str, str]:
    fields: dict[str, str] = {}
    for error in exc.errors():
        if error["type"] == "json_invalid":
            fields["body"] = "Invalid JSON."
            continue
        fields.setdefault(_field_path(tuple(error["loc"])), _field_message(error))
    return fields


async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.code, exc.status, exc.message, exc.fields, exc.headers)


async def _validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        ErrorCode.VALIDATION_ERROR, 422, "Invalid request.", _validation_fields(exc)
    )


async def _http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _HTTP_ERRORS.get(exc.status_code, (ErrorCode.VALIDATION_ERROR, ""))
    status = exc.status_code if exc.status_code in _HTTP_ERRORS else 422
    return error_response(code, status, message or "Invalid request.", headers=exc.headers)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
