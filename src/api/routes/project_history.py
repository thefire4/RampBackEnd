from flask import Blueprint, jsonify, request
from src.api.services.project_log_service import get_project_history

project_history_bp = Blueprint("project_history", __name__)

@project_history_bp.get("/api/projects/<int:project_id>/history")
def project_history(project_id):
    user_id = get_authenticated_user_id()
    authorize_project_access(user_id, project_id)

    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)

    if not 1 <= limit <= 500 or offset < 0:
        return jsonify({"error": "Invalid pagination"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id FROM projects WHERE id = %s",
            (project_id,),
        )

        if cursor.fetchone() is None:
            return jsonify({"error": "Project not found"}), 404

        history = get_project_history(
            cursor,
            project_id,
            limit=limit,
            offset=offset,
        )

        return jsonify({"history": history}), 200

    finally:
        cursor.close()
        connection.close()

