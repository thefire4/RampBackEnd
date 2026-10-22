from pathlib import Path

from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required

from src.api.extensions import db
from src.api.models import Project
from src.api.services.document_import import import_uploaded_document
from src.api.services.import_errors import DocumentImportError

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/projects", methods=["POST"])
@login_required
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Project name is required."}), 400

    project = Project(name=name, status=data.get("status") or "in progress")
    db.session.add(project)
    db.session.commit()
    return jsonify({"project": _project_payload(project)}), 201


@projects_bp.route("/projects/<int:project_id>/import", methods=["POST"])
@login_required
def import_project_document(project_id: int):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Project not found."}), 404

    upload = request.files.get("file")
    try:
        summary = import_uploaded_document(
            upload=upload,
            project=project,
            user_id=current_user.id,
            upload_dir=_upload_dir(),
        )
    except DocumentImportError as exc:
        return jsonify({"error": exc.message}), exc.status_code

    return jsonify(_summary_payload(summary)), 200


@projects_bp.route("/projects/import", methods=["POST"])
@login_required
def import_new_project_document():
    upload = request.files.get("file")
    name = (request.form.get("name") or "").strip()
    if not name and upload and upload.filename:
        name = Path(upload.filename).stem[:100]
    if not name:
        name = "Imported project"

    project = Project(name=name, status="in progress")
    db.session.add(project)
    db.session.flush()

    try:
        summary = import_uploaded_document(
            upload=upload,
            project=project,
            user_id=current_user.id,
            upload_dir=_upload_dir(),
        )
    except DocumentImportError as exc:
        db.session.rollback()
        return jsonify({"error": exc.message}), exc.status_code

    if summary.project_fields_updated:
        description = project.description
        if description and not project.name.startswith(description[:20]):
            pass
    db.session.commit()
    return jsonify(_summary_payload(summary)), 201


def _project_payload(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "style_no": project.style_no,
        "po_no": project.po_no,
        "project_date": project.project_date.isoformat() if project.project_date else None,
        "customer": project.customer,
        "size_range": project.size_range,
        "season": project.season,
        "fabric_yarn": project.fabric_yarn,
        "designer": project.designer,
        "weight": project.weight,
        "description": project.description,
    }


def _summary_payload(summary) -> dict:
    payload = {
        "project_id": summary.project_id,
        "project_fields_updated": summary.project_fields_updated,
        "file_id": summary.file_record_id,
    }
    if summary.bom:
        payload["bom"] = {
            "materials_created": summary.bom.materials_created,
            "colorways_created": summary.bom.colorways_created,
            "rows_processed": summary.bom.rows_processed,
            "sheet_name": summary.bom.sheet_name,
            "skipped_rows": summary.bom.skipped_rows,
        }
    if summary.measurements:
        payload["measurements"] = {
            "points_created": summary.measurements.points_created,
            "sheet_name": summary.measurements.sheet_name,
        }
    return payload


def _upload_dir() -> Path:
    base = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    if not base.is_absolute():
        base = Path(current_app.root_path).parent / base
    return base
