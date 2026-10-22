import pytest
from pydantic import ValidationError

from app.config import Settings

DB_URL = "mysql+pymysql://app:app@localhost:3307/rooms_test?charset=utf8mb4"


def make_settings(**overrides):
    values = {"database_url": DB_URL, "jwt_secret": "s" * 32}
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_refuses_missing_jwt_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError, match="jwt_secret"):
        Settings(_env_file=None, database_url=DB_URL)


def test_refuses_jwt_secret_shorter_than_32():
    with pytest.raises(ValidationError, match="jwt_secret"):
        make_settings(jwt_secret="s" * 31)


def test_accepts_jwt_secret_of_32():
    assert make_settings(jwt_secret="s" * 32).jwt_secret == "s" * 32


def test_refuses_missing_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None, jwt_secret="s" * 32)


def test_defaults_match_spec(monkeypatch):
    for name in ("ACCESS_TOKEN_MINUTES", "REFRESH_TOKEN_DAYS", "MAX_UPLOAD_MB", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    settings = make_settings()
    assert settings.access_token_minutes == 15
    assert settings.refresh_token_days == 7
    assert settings.max_upload_mb == 5
    assert settings.max_photos_per_room == 20
    assert settings.cors_origin_list == []


def test_reads_values_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("JWT_SECRET", "e" * 40)
    monkeypatch.setenv("ACCESS_TOKEN_MINUTES", "30")
    settings = Settings(_env_file=None)
    assert settings.jwt_secret == "e" * 40
    assert settings.access_token_minutes == 30


def test_cors_origins_are_comma_separated():
    settings = make_settings(cors_origins=" https://a.com , https://b.com,, ")
    assert settings.cors_origin_list == ["https://a.com", "https://b.com"]
