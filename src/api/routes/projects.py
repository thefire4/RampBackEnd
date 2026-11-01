from pathlib import Path

from flask import Blueprint, jsonify, request, current_app, send_file
from flask_login import current_user, login_required

from src.api.extensions import db
from src.api.models import Project, ProjectMaterial, ProjectFile, PointsMeasured, ValueSource
from src.api.services.provenance import PROJECT_FIELDS, MATERIAL_FIELDS, MEASUREMENT_FIELDS, record_source, serialize_values
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
    db.session.flush()
    for field in ("name", "status"):
        record_source(project.id, "project", project.id, field, kind="manual", user_id=current_user.id)
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
        db.session.rollback()
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

    for field in ("name", "status"):
        record_source(project.id, "project", project.id, field,
                      kind="manual" if field == "name" and request.form.get("name") else "generated",
                      user_id=current_user.id)
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


@projects_bp.route("/projects/<int:project_id>", methods=["GET"])
@login_required
def project_dashboard(project_id):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify(error="Project not found."), 404
    sources = ValueSource.query.filter_by(project_id=project_id).all()
    def values(entity, kind, fields):
        return serialize_values(entity, fields, {s.field: s for s in sources if s.entity_type == kind and s.entity_id == entity.id})
    payload = _project_payload(project)
    payload["fields"] = values(project, "project", PROJECT_FIELDS)
    payload["materials"] = [{"id": m.id, "colorway_id": c.id, "fields": values(m, "material", MATERIAL_FIELDS)} for c in project.colorways for m in c.materials]
    payload["measurements"] = [{"id": p.id, "fields": values(p, "measurement", MEASUREMENT_FIELDS)} for p in project.measurement_points]
    return jsonify(project=payload)


@projects_bp.route("/projects/<int:project_id>", methods=["PATCH"])
@projects_bp.route("/projects/<int:project_id>/materials/<int:material_id>", methods=["PATCH"])
@projects_bp.route("/projects/<int:project_id>/measurements/<int:point_id>", methods=["PATCH"])
@login_required
def update_values(project_id, material_id=None, point_id=None):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify(error="Project not found."), 404
    entity, kind, fields = project, "project", PROJECT_FIELDS
    if material_id is not None:
        entity = ProjectMaterial.query.join(ProjectMaterial.colorway).filter_by(project_id=project_id).filter(ProjectMaterial.id == material_id).first()
        kind, fields = "material", MATERIAL_FIELDS
    elif point_id is not None:
        entity = PointsMeasured.query.filter_by(id=point_id, project_id=project_id).first()
        kind, fields = "measurement", MEASUREMENT_FIELDS
    if entity is None:
        return jsonify(error="Value record not found."), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data or any(k not in fields for k in data):
        return jsonify(error="Provide supported fields to update."), 400
    from datetime import date
    try:
        for field, value in data.items():
            column = entity.__table__.columns[field]
            if value is None and not column.nullable:
                raise ValueError(f"{field} is required.")
            if field == "quantity":
                if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                    raise ValueError("quantity must be an integer.")
            elif value is not None:
                if not isinstance(value, str):
                    raise ValueError(f"{field} must be text.")
                if getattr(column.type, "length", None) and len(value) > column.type.length:
                    raise ValueError(f"{field} is too long.")
                if field == "project_date":
                    value = date.fromisoformat(value)
                if field == "name" and entity is project and not value.strip():
                    raise ValueError("Project name is required.")
            setattr(entity, field, value)
            record_source(project_id, kind, entity.id, field, kind="manual", user_id=current_user.id)
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 400
    return project_dashboard(project_id)


@projects_bp.route("/projects/<int:project_id>/files/<int:file_id>", methods=["GET"])
@login_required
def open_source_file(project_id, file_id):
    file = ProjectFile.query.filter_by(id=file_id, project_id=project_id).first()
    if file is None or not file.file_path:
        return jsonify(error="Source file not found."), 404
    path = Path(file.file_path).resolve()
    if not path.is_file():
        return jsonify(error="Original source file is no longer available."), 404
    return send_file(path, download_name=file.file_name, as_attachment=True)
