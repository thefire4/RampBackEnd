from flask import Blueprint, jsonify, request, redirect, url_for, render_template
from flask_login import login_user, login_required, logout_user
from src.api.models import User
from src.api.extensions import db
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError



auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="A JSON request body is required"), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (username, email, password)
    ):
        return jsonify(
            error="Username, email, and password are required"
        ), 400

    username = username.strip()
    email = email.strip().lower()

    if len(username) > 80 or len(email) > 255:
        return jsonify(error="Username or email is too long"), 400

    if len(password) < 8:
        return jsonify(
            error="Password must be at least 8 characters"
        ), 400

    existing_user = User.query.filter(
        or_(
            User.username == username
            User.email == email
        )
    ).first

    if existing_user:
        return jsonify(
            error="Username or email is already registered"
        ), 409

    user = User(
        username = username,
        email = email,
        password_hash=generate_password_hash(password)
    )

    try:
        db.session.add(user)
        db.session.commit()

        login_user(user)

    except IntegrityError:
        db.session.rollback()
        return jsonify(
            error="Username or email is already registered"
        ), 409

    return jsonify({
        "message": "Account created successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "error": "Username and password are required"
        }), 400

    user = User.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(
        user.password_hash, password
    ):
        return jsonify({
            "error": "Invalid username or password"
        }), 401

    login_user(user)

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username
        }
    }), 200



@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify(message="Logged out successfully"), 200