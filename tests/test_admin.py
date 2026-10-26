import pytest

from src.api.extensions import db
from src.api.models import User

ADMIN_ENDPOINTS = [("get", "/api/users"), ("post", "/api/users"), ("delete", "/api/users/1")]


@pytest.mark.parametrize("method, path", ADMIN_ENDPOINTS)
def test_non_admins_are_blocked_from_admin_endpoints(employee_client, method, path):
    res = getattr(employee_client, method)(path, json={})
    assert res.status_code == 403
    assert res.get_json()["error"] == "Admin access required"


@pytest.mark.parametrize("method, path", ADMIN_ENDPOINTS)
def test_logged_out_users_are_blocked_from_admin_endpoints(app, method, path):
    assert getattr(app.test_client(), method)(path, json={}).status_code == 401


def test_non_admin_cannot_create_an_account(employee_client):
    employee_client.post("/api/users", json={
        "username": "sneaky", "email": "sneaky@example.com", "password": "password123", "role": "admin",
    })
    assert User.query.filter_by(username="sneaky").first() is None


def test_admin_can_add_list_and_remove_employees(admin_client, admin):
    res = admin_client.post("/api/users", json={
        "username": "jsmith", "email": "jsmith@example.com", "password": "temp-pass-1", "role": "user",
    })
    assert res.status_code == 201
    new_id = res.get_json()["user"]["id"]

    new_user = User.query.filter_by(username="jsmith").one()
    assert new_user.role == "user"
    assert new_user.password_hash != "temp-pass-1"  # stored hashed, never as plain text

    usernames = [u["username"] for u in admin_client.get("/api/users").get_json()["users"]]
    assert usernames == ["boss", "jsmith"]

    assert admin_client.delete(f"/api/users/{new_id}").status_code == 200
    assert User.query.filter_by(username="jsmith").first() is None


def test_admin_cannot_delete_themselves(admin_client, admin):
    assert admin_client.delete(f"/api/users/{admin.id}").status_code == 400
    assert db.session.get(User, admin.id) is not None


@pytest.mark.parametrize("payload, status", [
    ({"username": "x", "email": "x@example.com", "password": "short", "role": "user"}, 400),
    ({"username": "x", "email": "x@example.com", "password": "long-enough", "role": "owner"}, 400),
    ({"username": "", "email": "x@example.com", "password": "long-enough"}, 400),
    ({"username": "boss", "email": "other@example.com", "password": "long-enough"}, 409),
])
def test_admin_gets_clear_errors_for_bad_accounts(admin_client, payload, status):
    res = admin_client.post("/api/users", json=payload)
    assert res.status_code == status
    assert res.get_json()["error"]