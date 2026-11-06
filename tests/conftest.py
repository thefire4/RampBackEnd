from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from src.api import create_app
from src.api.extensions import db
from src.api.models import User

PASSWORD = "correct-horse-1"


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def make_user(app):
    def make(username, role="user", password=PASSWORD):
        user = User(
            username=username,
            email=f"{username}@example.com",
            password_hash=generate_password_hash(password),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        return user
    return make


@pytest.fixture
def employee(make_user):
    return make_user("employee")


@pytest.fixture
def admin(make_user):
    return make_user("boss", role="admin")


def logged_in_client(app, user):
    """A test client already logged in as `user` (skips the login form)."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    return client


@pytest.fixture
def employee_client(app, employee):
    return logged_in_client(app, employee)


@pytest.fixture
def admin_client(app, admin):
    return logged_in_client(app, admin)

def pytest_configure(config):
    # Apply before pytest prints its header; leave other suites' defaults alone.
    if config.args and all(Path(str(arg).split("::", 1)[0]).name in {"test_bom_hand_counts.py", "test_bom_upload_values.py"} for arg in config.args):
        config.option.verbose = -1
        config.option.reportchars = "s"
        config.option.tbstyle = "no"


def pytest_terminal_summary(terminalreporter):
    """Show BOM details, including failed uploads and teardown cleanup results."""
    printed = set()
    for reports in terminalreporter.stats.values():
        for report in reports:
            for name, text in getattr(report, "user_properties", []):
                key = (report.nodeid, text)
                if name == "bom_summary" and key not in printed:
                    terminalreporter.write_line(text)
                    printed.add(key)
