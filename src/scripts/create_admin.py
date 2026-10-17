
import getpass

from src.api import create_app
from src.api.extensions import db
from src.api.models import User
from werkzeug.security import generate_password_hash


def main():
    app = create_app()

    with app.app_context():
        username = input("Admin username: ").strip()
        email = input("Admin email: ").strip().lower()
        password = getpass.getpass("Admin password: ")
        confirm_password = getpass.getpass("Confirm password: ")

        if not username or not email or not password:
            print("Error: All fields are required.")
            return

        if len(username) > 80 or len(email) > 254:
            print("Error: Username or email is too long.")
            return

        if len(password) < 8:
            print("Error: Password must be at least 8 characters.")
            return

        if password != confirm_password:
            print("Error: Passwords do not match.")
            return

        existing_user = User.query.filter(
            db.or_(
                User.username == username,
                User.email == email
            )
        ).first()

        if existing_user:
            print("Error: Username or email already exists.")
            return

        admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="admin",
        )

        db.session.add(admin)

        try:
            db.session.commit()
            print(f"Admin account '{username}' created successfully.")
        except Exception:
            db.session.rollback()
            raise


if __name__ == "__main__":
    main()
