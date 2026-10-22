from flask import Blueprint, request, jsonify
from flask_login import current_user
from src.api.decorators import admin_required
from src.api.models import User
from src.api.extensions import db
from werkzeug.security import generate_password_hash
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="A JSON request body is required"), 400
  
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")
   
    if not all(
        isinstance(value, str) and value.strip()
        for value in (username, email, password)
    ):
        return jsonify(
            error="Username, email, and password are required"
        ), 400
   
  
    if len(username) > 80 or len(email) > 255:
        return jsonify(error="Username or email is too long"), 400
    
    if len(password) < 8:
        return jsonify(
            error="Password must be at least 8 characters"
        ), 400

    if role not in ("user", "admin"):
        return jsonify({"error": "Invalid role"}), 400

    
    existing_user = User.query.filter(
        or_(
            User.username == username,
            User.email == email
        )
    ).first()
   
    if existing_user:
        return jsonify(
            error="Username or email is already registered"
        ), 409
  
    user = User(
        username = username,
        email = email,
        password_hash=generate_password_hash(password),
        role=role
    )
    
    try:
        db.session.add(user)
        db.session.commit()
  
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
            "email": user.email,
            "role": user.role
        }
    }), 201


@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    users = User.query.order_by(User.id.asc()).all()

    if users is None:
        return jsonify({
            "error": "No users to display"
        }), 400

    
    return jsonify({
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
            for user in users
        ]
    }), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    # Prevent an admin from deleting their own account
    if user.id == current_user.id:
        return jsonify({
            "error": "You cannot delete your own account"
        }), 400

    try:
        db.session.delete(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "Cannot delete this user"
        }), 409

    return jsonify({
        "message": "User deleted successfully",
        "user_id": user_id
    }), 200
