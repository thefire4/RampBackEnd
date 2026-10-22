from flask import Blueprint, jsonify
from flask_login import login_required, current_user

main_bp = Blueprint("main", __name__)

@main_bp.route("/health")
def health():
    return jsonify(status="healthy"), 200

@main_bp.route("/me", methods=["GET"])
@login_required
def profile():
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }, 200