from datetime import date
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_login import login_required

from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial, Task, User
from src.api.services.tasks import missing_bom_fields

tasks_bp = Blueprint("tasks", __name__)
TASK_STATUSES = {"open", "in progress", "done"}
TASK_FIELDS = {"owner_id", "status", "due_date"}


def _task_payload(task: Task) -> dict:
    return {
        "id": task.id,
        "bom_line_id": task.bom_line_id,
        "project_id": task.project_id,
        "missing_fields": task.missing_fields,
        "owner_id": task.owner_id,
        "owner": task.owner.username if task.owner else None,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _normalize_task_fields(changes: dict):
    unknown_fields = set(changes) - TASK_FIELDS
    if unknown_fields:
        return None, "One or more task fields cannot be edited.", 400

    normalized = {}
    for field, value in changes.items():
        if field == "owner_id":
            if value is None:
                normalized[field] = None
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                return None, "Owner ID must be an integer or null.", 400
            if db.session.get(User, value) is None:
                return None, "Owner not found.", 404
            normalized[field] = value
        elif field == "status":
            if not isinstance(value, str) or value not in TASK_STATUSES:
                return None, "Status must be open, in progress, or done.", 400
            normalized[field] = value
        else:
            if value is None or value == "":
                normalized[field] = None
                continue
            if not isinstance(value, str):
                return None, "Due date must be a date in YYYY-MM-DD format or null.", 400
            try:
                parsed_date = date.fromisoformat(value)
            except ValueError:
                return None, "Due date must be a date in YYYY-MM-DD format or null.", 400
            if parsed_date.isoformat() != value:
                return None, "Due date must be a date in YYYY-MM-DD format or null.", 400
            normalized[field] = parsed_date
    return normalized, None, None


@tasks_bp.route("/projects/<int:project_id>/tasks", methods=["GET"])
@login_required
def list_project_tasks(project_id: int):
    if db.session.get(Project, project_id) is None:
        return jsonify({"error": "Project not found."}), 404
    tasks = (
        Task.query.filter_by(project_id=project_id)
        .order_by(Task.created_at.desc(), Task.id.desc())
        .all()
    )
    return jsonify({"tasks": [_task_payload(task) for task in tasks]}), 200


@tasks_bp.route("/projects/<int:project_id>/tasks", methods=["POST"])
@login_required
def create_task(project_id: int):
    if db.session.get(Project, project_id) is None:
        return jsonify({"error": "Project not found."}), 404
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or "bom_line_id" not in body:
        return jsonify({"error": "A bom_line_id is required."}), 400
    if isinstance(body["bom_line_id"], bool) or not isinstance(body["bom_line_id"], int):
        return jsonify({"error": "BOM line ID must be an integer."}), 400

    material = (
        db.session.query(ProjectMaterial)
        .join(ProjectColor, ProjectMaterial.colorway_id == ProjectColor.id)
        .filter(
            ProjectColor.project_id == project_id,
            ProjectMaterial.id == body["bom_line_id"],
        )
        .first()
    )
    if material is None:
        return jsonify({"error": "BOM line not found for this project."}), 404

    missing = missing_bom_fields(material)
    if not missing:
        return jsonify({"error": "The BOM line has no missing information."}), 400
    if Task.query.filter_by(bom_line_id=material.id).first() is not None:
        return jsonify({"error": "A task already exists for this BOM line."}), 409

    changes, error, status_code = _normalize_task_fields(
        {field: value for field, value in body.items() if field != "bom_line_id"}
    )
    if error:
        return jsonify({"error": error}), status_code

    task = Task(
        bom_line_id=material.id,
        project_id=project_id,
        missing_fields=missing,
        **changes,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({"task": _task_payload(task)}), 201


@tasks_bp.route("/tasks/<int:task_id>", methods=["PATCH"])
@tasks_bp.route(
    "/projects/<int:project_id>/tasks/<int:task_id>",
    methods=["PATCH"],
)
@login_required
def update_task(task_id: int, project_id: Optional[int] = None):
    task = db.session.get(Task, task_id)
    if task is None or (project_id is not None and task.project_id != project_id):
        return jsonify({"error": "Task not found."}), 404
    changes = request.get_json(silent=True)
    if not isinstance(changes, dict) or not changes:
        return jsonify({"error": "Provide at least one task field to update."}), 400

    normalized, error, status_code = _normalize_task_fields(changes)
    if error:
        return jsonify({"error": error}), status_code
    for field, value in normalized.items():
        setattr(task, field, value)
    db.session.commit()
    return jsonify({"task": _task_payload(task)}), 200
