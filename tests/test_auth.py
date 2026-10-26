from conftest import PASSWORD


def login(client, username, password):
    return client.post("/api/login", json={"username": username, "password": password})


def test_login_works_with_the_right_password(app, employee):
    client = app.test_client()
    res = login(client, "employee", PASSWORD)

    assert res.status_code == 200
    assert res.get_json()["user"]["username"] == "employee"
    assert client.get("/api/me").status_code == 200  # the session cookie now works


def test_login_fails_with_the_wrong_password(app, employee):
    client = app.test_client()
    res = login(client, "employee", "wrong-password")

    assert res.status_code == 401
    assert res.get_json()["error"] == "Invalid username or password"
    assert client.get("/api/me").status_code == 401


def test_login_fails_for_an_unknown_user(app, employee):
    res = login(app.test_client(), "nobody", PASSWORD)
    assert res.status_code == 401
    assert res.get_json()["error"] == "Invalid username or password"


def test_login_needs_both_fields(app):
    assert app.test_client().post("/api/login", json={"username": "employee"}).status_code == 400


def test_me_returns_the_role_the_frontend_needs(app, admin):
    client = app.test_client()
    login(client, "boss", PASSWORD)

    me = client.get("/api/me").get_json()
    assert me["username"] == "boss"
    assert me["role"] == "admin"  # the frontend shows admin pages based on this


def test_logout_ends_the_session(app, employee):
    client = app.test_client()
    login(client, "employee", PASSWORD)

    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401


def test_csrf_token_is_served_where_the_frontend_asks_for_it(app):
    res = app.test_client().get("/api/csrf-token")
    assert res.status_code == 200
    assert res.get_json()["csrf_token"]


def test_writes_are_rejected_without_a_csrf_token(app, employee):
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()

    res = login(client, "employee", PASSWORD)
    assert res.status_code == 400
    assert res.get_json()["error"] == "CSRF validation failed"

    token = client.get("/api/csrf-token").get_json()["csrf_token"]
    res = client.post("/api/login", json={"username": "employee", "password": PASSWORD},
                      headers={"X-CSRFToken": token})
    assert res.status_code == 200