"""POST /api/v1/auth/logout (spec section 11). Tokens are stateless: nothing is revoked."""

from app.security import create_refresh_token

URL = "/api/v1/auth/logout"


def test_logout_without_body(client, make_user, auth_headers):
    response = client.post(URL, headers=auth_headers(make_user()))
    assert response.status_code == 204
    assert response.content == b""


def test_logout_with_refresh_token(client, make_user, auth_headers, settings):
    user = make_user()
    body = {"refresh_token": create_refresh_token(user, settings)}
    assert client.post(URL, json=body, headers=auth_headers(user)).status_code == 204


def test_logout_with_empty_json_body(client, make_user, auth_headers):
    assert client.post(URL, json={}, headers=auth_headers(make_user())).status_code == 204


def test_allowed_while_password_change_required(client, make_user, auth_headers):
    user = make_user(must_change_password=True)
    assert client.post(URL, headers=auth_headers(user)).status_code == 204


def test_needs_a_token(client):
    response = client.post(URL)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_unknown_field(client, make_user, auth_headers):
    response = client.post(URL, json={"everywhere": True}, headers=auth_headers(make_user()))
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"everywhere": "Unknown field."}


def test_tokens_keep_working_after_logout(client, make_user, auth_headers, settings):
    """Known limit (spec section 9): the client must delete its tokens itself."""
    user = make_user()
    headers = auth_headers(user)
    refresh_token = create_refresh_token(user, settings)
    client.post(URL, json={"refresh_token": refresh_token}, headers=headers)
    assert client.post(URL, headers=headers).status_code == 204
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
