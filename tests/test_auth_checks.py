"""The checks on every authenticated request, in the order of spec section 5."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends

from app.security import (
    CurrentUser,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_user_allow_password_change,
    hash_password,
    require_roles,
)
from tests.factories import set_roles

AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
PasswordChangeAllowed = Annotated[CurrentUser, Depends(get_current_user_allow_password_change)]
Admin = Annotated[CurrentUser, Depends(require_roles("ADMIN"))]
AdminOrOwner = Annotated[CurrentUser, Depends(require_roles("ADMIN", "ROOM_OWNER"))]


@pytest.fixture
def routes(app):
    @app.get("/t/any")
    def any_user(current: AnyUser):
        return {"id": current.id, "roles": current.role_codes}

    @app.get("/t/password-change-allowed")
    def allowed(current: PasswordChangeAllowed):
        return {"id": current.id}

    @app.get("/t/admin")
    def admin_only(current: Admin):
        return {"id": current.id}

    @app.get("/t/admin-or-owner")
    def admin_or_owner(current: AdminOrOwner):
        return {"id": current.id}

    return app


def _error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


# 1. Token present, valid, not expired, type access ------------------------------------


def test_no_token(routes, client):
    response = client.get("/t/any")
    assert _error(response) == (401, "UNAUTHORIZED")
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header", ["Basic dXNlcjpwYXNz", "Bearer", "Bearer not-a-token", "Token abc"]
)
def test_bad_authorization_header(routes, client, header):
    assert _error(client.get("/t/any", headers={"Authorization": header})) == (401, "UNAUTHORIZED")


def test_refresh_token_sent_as_bearer(routes, client, make_user, settings):
    token = create_refresh_token(make_user(), settings)
    response = client.get("/t/any", headers={"Authorization": f"Bearer {token}"})
    assert _error(response) == (401, "UNAUTHORIZED")


def test_expired_token(routes, client, make_user, settings):
    user = make_user()
    good = jwt.decode(
        create_access_token(user, settings), settings.jwt_secret, algorithms=["HS256"]
    )
    past = datetime.now(UTC) - timedelta(hours=1)
    expired = jwt.encode(
        {**good, "iat": past, "exp": past + timedelta(minutes=15)}, settings.jwt_secret
    )
    response = client.get("/t/any", headers={"Authorization": f"Bearer {expired}"})
    assert _error(response) == (401, "UNAUTHORIZED")


# 2. User exists and is active --------------------------------------------------------


def test_valid_token_works(routes, client, make_user, auth_headers):
    user = make_user(roles=["STAFF"])
    response = client.get("/t/any", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json() == {"id": user.id, "roles": ["STAFF"]}


def test_user_that_no_longer_exists(routes, client, make_user, auth_headers, db_session):
    user = make_user()
    headers = auth_headers(user)
    user.id = 999_999  # the token now points at nobody
    db_session.flush()
    assert _error(client.get("/t/any", headers=headers)) == (401, "UNAUTHORIZED")


def test_user_deactivated_after_token_issued(routes, client, make_user, auth_headers, db_session):
    user = make_user()
    headers = auth_headers(user)
    assert client.get("/t/any", headers=headers).status_code == 200
    user.is_active = False
    db_session.flush()
    assert _error(client.get("/t/any", headers=headers)) == (401, "UNAUTHORIZED")


# 3. Password fingerprint matches -----------------------------------------------------


def test_old_token_after_password_change(routes, client, make_user, auth_headers, db_session):
    user = make_user()
    headers = auth_headers(user)
    user.password_hash = hash_password("NewPassword@456")
    db_session.flush()
    assert _error(client.get("/t/any", headers=headers)) == (401, "UNAUTHORIZED")
    assert client.get("/t/any", headers=auth_headers(user)).status_code == 200


# 4. must_change_password (rule R16) --------------------------------------------------


def test_must_change_password_blocks_normal_endpoints(routes, client, make_user, auth_headers):
    user = make_user(roles=["STAFF"], must_change_password=True)
    response = client.get("/t/any", headers=auth_headers(user))
    assert _error(response) == (403, "PASSWORD_CHANGE_REQUIRED")


def test_must_change_password_allows_the_three_endpoints(routes, client, make_user, auth_headers):
    user = make_user(must_change_password=True)
    response = client.get("/t/password-change-allowed", headers=auth_headers(user))
    assert response.status_code == 200


def test_must_change_password_is_checked_before_roles(routes, client, make_user, auth_headers):
    user = make_user(roles=["STAFF"], must_change_password=True)
    response = client.get("/t/admin", headers=auth_headers(user))
    assert _error(response) == (403, "PASSWORD_CHANGE_REQUIRED")


def test_password_change_allowed_still_needs_a_valid_token(routes, client):
    assert _error(client.get("/t/password-change-allowed")) == (401, "UNAUTHORIZED")


# 5. Role check -----------------------------------------------------------------------


def test_admin_route_refuses_staff(routes, client, make_user, auth_headers):
    user = make_user(roles=["STAFF"])
    assert _error(client.get("/t/admin", headers=auth_headers(user))) == (403, "FORBIDDEN")


def test_admin_route_allows_admin(routes, client, make_user, auth_headers):
    user = make_user(roles=["ADMIN"])
    assert client.get("/t/admin", headers=auth_headers(user)).status_code == 200


def test_any_of_several_roles_passes(routes, client, make_user, auth_headers):
    owner = make_user(roles=["ROOM_OWNER"])
    staff = make_user(roles=["STAFF"])
    assert client.get("/t/admin-or-owner", headers=auth_headers(owner)).status_code == 200
    response = client.get("/t/admin-or-owner", headers=auth_headers(staff))
    assert _error(response) == (403, "FORBIDDEN")


def test_user_with_no_roles_passes_any(routes, client, make_user, auth_headers):
    user = make_user(roles=[])
    response = client.get("/t/any", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["roles"] == []


def test_role_changes_apply_on_next_request(routes, client, make_user, auth_headers, db_session):
    user = make_user(roles=["STAFF"])
    headers = auth_headers(user)
    assert client.get("/t/admin", headers=headers).status_code == 403
    set_roles(db_session, user, ["ADMIN"])
    assert client.get("/t/admin", headers=headers).status_code == 200
    set_roles(db_session, user, [])
    assert client.get("/t/admin", headers=headers).status_code == 403


def test_role_codes_in_seed_order(routes, client, make_user, auth_headers):
    user = make_user(roles=["IT_STAFF", "STAFF", "ADMIN", "PITIKA"])
    response = client.get("/t/any", headers=auth_headers(user))
    assert response.json()["roles"] == ["ADMIN", "STAFF", "PITIKA", "IT_STAFF"]


def test_require_roles_rejects_unknown_codes():
    with pytest.raises(ValueError, match="MANAGER"):
        require_roles("MANAGER")
