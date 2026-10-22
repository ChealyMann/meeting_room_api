import logging
import re
import uuid
from contextvars import ContextVar

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import ErrorCode, error_response

logger = logging.getLogger("app")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


class RequestIdLogFilter(logging.Filter):
    """Adds `request_id` to every log record so log formats can include it."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class RequestIdMiddleware:
    """Sets `X-Request-ID` on every response and turns unexpected errors into a plain 500.

    The id comes from the request header when it is safe to log, else a new UUID.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get("x-request-id", "")
        request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else str(uuid.uuid4())
        token = request_id_var.set(request_id)
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            logger.exception("Unexpected error on %s %s", scope["method"], scope["path"])
            if response_started:
                raise
            response = error_response(
                ErrorCode.INTERNAL_ERROR,
                500,
                "Something went wrong.",
                headers={"X-Request-ID": request_id},
            )
            await response(scope, receive, send)
        finally:
            request_id_var.reset(token)
