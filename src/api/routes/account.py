
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from src.api.extensions import db

account_bp = Blueprint("account", __name__)


@account_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    # Validate required fields
    if not current_password or not new_password or not confirm_password:
        return jsonify({
            "error": "All password fields are required"
        }), 400

    # Verify the current password
    if not check_password_hash(
        current_user.password_hash,
        current_password
    ):
        return jsonify({
            "error": "Current password is incorrect"
        }), 400

    # Validate the new password
    if len(new_password) < 8:
        return jsonify({
            "error": "New password must be at least 8 characters"
        }), 400

    if new_password != confirm_password:
        return jsonify({
            "error": "New passwords do not match"
        }), 400

    if check_password_hash(
        current_user.password_hash,
        new_password
    ):
        return jsonify({
            "error": "New password must differ from the current password"
        }), 400

    # Hash the new password before saving it
    current_user.password_hash = generate_password_hash(new_password)

    db.session.commit()

    return jsonify({
        "message": "Password changed successfully"
    }), 200
