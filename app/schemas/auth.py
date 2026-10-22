from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.common import RequestModel, Text


class LoginRequest(RequestModel):
    email: Text(254)  # trimmed here; lowercased by the service
    # Not trimmed. The upper bound only stops absurdly large bodies from being hashed.
    password: Annotated[str, Field(min_length=1, max_length=1024)]


class RefreshRequest(RequestModel):
    refresh_token: Annotated[str, Field(min_length=1, max_length=4096)]


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # seconds the access token is valid
    must_change_password: bool
