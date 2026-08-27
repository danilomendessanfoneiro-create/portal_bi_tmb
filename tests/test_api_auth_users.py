"""Smoke tests for FastAPI auth + users (TestClient)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app
from app.models import User

client = TestClient(app)


def _admin_user(**kwargs) -> User:
    defaults = dict(
        id=1,
        login="admin",
        password_hash="x",
        profile="admin",
        branch=None,
        display_name="Admin",
        name="Admin",
        code="admin",
        enabled=True,
    )
    defaults.update(kwargs)
    return User(**defaults)


def _filial_user(**kwargs) -> User:
    defaults = dict(
        id=2,
        login="filial1",
        password_hash="x",
        profile="filial",
        branch="SPO",
        display_name="Filial",
        name="Filial",
        code="filial1",
        enabled=True,
    )
    defaults.update(kwargs)
    return User(**defaults)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@patch("app.api.routers.auth.verify_hcaptcha")
@patch("app.api.routers.auth.AuthService")
def test_login_ok(mock_svc_cls, _mock_captcha):
    mock_svc_cls.return_value.authenticate.return_value = _admin_user()
    r = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "admin123", "hcaptcha_token": "ok"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["user"]["login"] == "admin"
    assert body["user"]["profile"] == "admin"


@patch("app.api.routers.auth.verify_hcaptcha")
@patch("app.api.routers.auth.AuthService")
def test_login_fail(mock_svc_cls, _mock_captcha):
    from app.services.auth_service import AuthError

    mock_svc_cls.return_value.authenticate.side_effect = AuthError("Usuário ou senha inválidos")
    r = client.post("/api/auth/login", json={"login": "x", "password": "y", "hcaptcha_token": "ok"})
    assert r.status_code == 401


@patch("app.api.deps.UserRepository")
@patch("app.api.routers.auth.verify_hcaptcha")
@patch("app.api.routers.auth.AuthService")
def test_me_and_users_admin(mock_auth_cls, _mock_captcha, mock_repo_cls):
    admin = _admin_user()
    mock_auth_cls.return_value.authenticate.return_value = admin
    mock_repo_cls.return_value.get_by_login.return_value = admin

    login = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "x", "hcaptcha_token": "ok"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["login"] == "admin"

    with patch("app.api.routers.users.UserService") as mock_us:
        mock_us.return_value.list.return_value = ([admin], 1)
        listed = client.get("/api/users", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


@patch("app.api.deps.UserRepository")
@patch("app.api.routers.auth.verify_hcaptcha")
@patch("app.api.routers.auth.AuthService")
def test_users_forbidden_for_filial(mock_auth_cls, _mock_captcha, mock_repo_cls):
    filial = _filial_user()
    mock_auth_cls.return_value.authenticate.return_value = filial
    mock_repo_cls.return_value.get_by_login.return_value = filial

    login = client.post(
        "/api/auth/login",
        json={"login": "filial1", "password": "x", "hcaptcha_token": "ok"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/users", headers=headers)
    assert r.status_code == 403


def test_users_unauthorized():
    r = client.get("/api/users")
    assert r.status_code == 401
