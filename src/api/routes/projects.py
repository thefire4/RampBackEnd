import math
import mimetypes
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from flask import Blueprint, jsonify, request, current_app, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func, or_

from src.api.extensions import db
from src.api.models import (
    Project,
    ProjectChangeLog,
    ProjectColor,
    ProjectFile,
    ProjectMaterial,
    User,
)
from src.api.services.document_import import import_uploaded_document
from src.api.services.import_errors import DocumentImportError

projects_bp = Blueprint("projects", __name__)


def _blank(column):
    return func.coalesce(func.trim(column), "") == ""


# Keep this rule aligned with the required material details in materials.ts.
MISSING_BOM_ITEM = or_(
    _blank(ProjectMaterial.material),
    _blank(ProjectMaterial.supplier),
    _blank(ProjectMaterial.supplier_contact),
    _blank(ProjectMaterial.location),
    _blank(ProjectMaterial.material_size),
    _blank(ProjectMaterial.color),
    _blank(ProjectMaterial.uom),
    ProjectMaterial.quantity.is_(None) | (ProjectMaterial.quantity <= 0),
)

MATERIAL_FIELDS = (
    "name",
    "material",
    "supplier",
    "supplier_contact",
    "quantity",
    "location",
    "article_no",
    "material_size",
    "uom",
    "color",
    "notes",
)
EDITABLE_MATERIAL_FIELDS = set(MATERIAL_FIELDS)
REQUIRED_MATERIAL_FIELDS = {
    "material",
    "supplier",
    "supplier_contact",
    "location",
    "material_size",
    "uom",
    "color",
}
MATERIAL_FIELD_LENGTHS = {
    "name": 50,
    "material": 100,
    "supplier": 100,
    "supplier_contact": 255,
    "location": 1000,
    "article_no": 100,
    "material_size": 50,
    "uom": 10,
    "color": 50,
}
PROJECT_FIELDS = {
    "name": 100,
    "status": 20,
    "style_no": 100,
    "po_no": 100,
    "customer": 255,
    "size_range": 50,
    "season": 50,
    "fabric_yarn": 100,
    "designer": 100,
    "weight": 100,
    "description": 1000,
}
PROJECT_STATUSES = {"blocked", "in progress", "finished"}
IMAGE_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}


def _missing_bom_count(project_id: int) -> int:
    count = (
        db.session.query(func.count(ProjectMaterial.id))
        .join(ProjectColor, ProjectMaterial.colorway_id == ProjectColor.id)
        .filter(ProjectColor.project_id == project_id, MISSING_BOM_ITEM)
        .scalar()
    )
    return int(count or 0)


def _project_bom_counts(project_id: int) -> tuple[int, int]:
    total, missing = (
        db.session.query(
            func.count(ProjectMaterial.id),
            func.coalesce(func.sum(case((MISSING_BOM_ITEM, 1), else_=0)), 0),
        )
        .join(ProjectColor, ProjectMaterial.colorway_id == ProjectColor.id)
        .filter(ProjectColor.project_id == project_id)
        .one()
    )
    return int(total), int(missing)


def _bom_counts_query():
    return (
        db.session.query(
            ProjectColor.project_id.label("project_id"),
            func.count(ProjectMaterial.id).label("total"),
            func.sum(case((MISSING_BOM_ITEM, 1), else_=0)).label("missing"),
        )
        .join(ProjectMaterial, ProjectMaterial.colorway_id == ProjectColor.id)
        .group_by(ProjectColor.project_id)
        .subquery()
    )


def _completeness(total: int, missing: int) -> dict:
    return {
        "total_bom_lines": total,
        "missing_bom_items": missing,
        "percent_complete": (
            round((total - missing) / total * 100)
            if total
            else 0
        ),
    }


def _validate_project_changes(changes: dict) -> Tuple[Optional[dict], Optional[str]]:
    changes = dict(changes)
    if "stage" in changes:
        if "status" in changes:
            return None, "Provide either stage or status, not both."
        changes["status"] = changes.pop("stage")

    unknown_fields = set(changes) - (set(PROJECT_FIELDS) | {"project_date"})
    if unknown_fields:
        return None, "One or more project fields cannot be edited."

    normalized = {}
    for field, value in changes.items():
        if field == "project_date":
            if value is None or value == "":
                normalized[field] = None
                continue
            if not isinstance(value, str):
                return None, "Project date must be a date in YYYY-MM-DD format or null."
            try:
                parsed_date = date.fromisoformat(value)
            except ValueError:
                return None, "Project date must be a date in YYYY-MM-DD format or null."
            if parsed_date.isoformat() != value:
                return None, "Project date must be a date in YYYY-MM-DD format or null."
            normalized[field] = parsed_date
            continue

        if value is not None and not isinstance(value, str):
            return None, f"{field.replace('_', ' ').capitalize()} must be text or null."
        if value is None:
            if field in {"name", "status"}:
                return None, f"{field.capitalize()} cannot be blank."
            normalized[field] = None
            continue

        value = value.strip()
        if field in {"name", "status"} and not value:
            return None, f"{field.capitalize()} cannot be blank."
        if len(value) > PROJECT_FIELDS[field]:
            return None, f"{field.replace('_', ' ').capitalize()} is too long."
        if field == "status" and value not in PROJECT_STATUSES:
            return None, "Stage must be blocked, in progress, or finished."
        normalized[field] = value or None

    return normalized, None


def _material_payload(material: ProjectMaterial) -> dict:
    return {
        "id": material.id,
        "colorway_id": material.colorway_id,
        "name": material.name,
        "material": material.material,
        "supplier": material.supplier,
        "supplier_contact": material.supplier_contact,
        "quantity": material.quantity,
        "location": material.location,
        "article_no": material.article_no,
        "material_size": material.material_size,
        "uom": material.uom,
        "color": material.color,
        "notes": material.notes,
    }


def _image_mimetype(project_file: ProjectFile) -> Optional[str]:
    file_type = (project_file.file_type or "").strip().lower()
    if file_type.startswith("image/"):
        return file_type

    extension = Path(project_file.file_name).suffix.lower()
    if extension not in IMAGE_EXTENSIONS:
        extension = f".{file_type.lstrip('.')}"
    if extension not in IMAGE_EXTENSIONS:
        return None
    return mimetypes.guess_type(f"image{extension}")[0]


def _serve_project_file(
    project_file: ProjectFile,
    mimetype: Optional[str] = None,
    file_label: str = "Project file",
):
    if not project_file.file_path:
        return jsonify({"error": f"{file_label} is missing."}), 404

    path = Path(project_file.file_path)
    if not path.is_file():
        return jsonify({"error": f"{file_label} is missing."}), 404

    try:
        with path.open("rb") as image_file:
            image_file.read(1)
    except OSError:
        current_app.logger.exception("Could not open %s %s", file_label.lower(), path)
        return jsonify({"error": f"{file_label} could not be opened."}), 500

    try:
        return send_file(
            path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=project_file.file_name,
        )
    except OSError:
        current_app.logger.exception("Could not serve %s %s", file_label.lower(), path)
        return jsonify({"error": f"{file_label} could not be opened."}), 500


def _validate_material_changes(
    changes: dict,
) -> Tuple[Optional[dict], Optional[str]]:
    unknown_fields = set(changes) - EDITABLE_MATERIAL_FIELDS
    if unknown_fields:
        return None, "One or more BOM fields cannot be edited."

    normalized = {}
    for field, value in changes.items():
        if field == "quantity":
            if value is None:
                normalized[field] = None
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None, "Quantity must be a number of 0 or more."
            quantity = float(value)
            if not math.isfinite(quantity) or quantity < 0:
                return None, "Quantity must be a number of 0 or more."
            normalized[field] = quantity
            continue

        if value is not None and not isinstance(value, str):
            return None, f"{field} must be text or null."
        if isinstance(value, str):
            value = value.strip()
            if field in REQUIRED_MATERIAL_FIELDS and not value:
                return None, f"{field.replace('_', ' ').capitalize()} cannot be blank."
            if len(value) > MATERIAL_FIELD_LENGTHS.get(field, 1000):
                return None, f"{field.replace('_', ' ').capitalize()} is too long."
            normalized[field] = value or None
        else:
            normalized[field] = None

    return normalized, None


def _change_entries(
    *,
    project_id: int,
    user_id: int,
    action: str,
    material_id: int,
    values: dict,
    old_values: Optional[dict] = None,
) -> List[ProjectChangeLog]:
    old_values = old_values or {}
    return [
        ProjectChangeLog(
            project_id=project_id,
            user_id=user_id,
            action=action,
            entity_type="material",
            entity_id=material_id,
            field_name=field,
            old_value=None if old_values.get(field) is None else str(old_values[field]),
            new_value=None if value is None else str(value),
        )
        for field, value in values.items()
        if field not in old_values or old_values[field] != value
    ]


def _bom_line_response(material: ProjectMaterial, project_id: int):
    total, missing = _project_bom_counts(project_id)
    return jsonify({
        "material": _material_payload(material),
        **_completeness(total, missing),
    })


@projects_bp.route("/projects", methods=["GET"])
@login_required
def get_projects():
    bom_counts = _bom_counts_query()

    rows = (
        db.session.query(
            Project,
            func.coalesce(bom_counts.c.total, 0),
            func.coalesce(bom_counts.c.missing, 0),
        )
        .outerjoin(bom_counts, bom_counts.c.project_id == Project.id)
        .order_by(Project.created_at.desc(), Project.id.desc())
        .all()
    )

    return jsonify({
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "customer": project.customer,
                "style_no": project.style_no,
                "description": project.description,
                "style_description": project.description,
                "stage": project.status,
                "po_no": project.po_no,
                "project_date": (
                    project.project_date.isoformat()
                    if project.project_date else None
                ),
                "created_at": (
                    project.created_at.isoformat()
                    if project.created_at else None
                ),
                **_completeness(int(total), int(missing)),
            }
            for project, total, missing in rows
        ]
    }), 200


@projects_bp.route("/projects/<int:project_id>", methods=["GET"])
@login_required
def get_project(project_id: int):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Project not found."}), 404

    total, missing = _project_bom_counts(project_id)
    project_payload = {
        **_project_payload(project),
        "stage": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        **_completeness(total, missing),
    }
    return jsonify({
        "project": project_payload,
        "colorways": [
            {
                "id": colorway.id,
                "name": colorway.name,
                "materials": [
                    _material_payload(material)
                    for material in colorway.materials
                ],
            }
            for colorway in project.colorways
        ],
        "files": [
            {
                "id": file.id,
                "file_name": file.file_name,
                "file_type": file.file_type,
                "url": url_for(
                    "projects.get_project_file",
                    file_id=file.id,
                ),
                "created_at": file.created_at.isoformat() if file.created_at else None,
            }
            for file in project.files
        ],
    }), 200


@projects_bp.route("/projects/<int:project_id>/images", methods=["GET"])
@login_required
def get_project_images(project_id: int):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Project not found."}), 404

    images = (
        ProjectFile.query
        .filter_by(project_id=project_id)
        .order_by(ProjectFile.created_at.desc(), ProjectFile.id.desc())
        .all()
    )
    image_payloads = []
    for image in images:
        mimetype = _image_mimetype(image)
        if mimetype is None:
            continue
        image_payloads.append({
            "id": image.id,
            "file_name": image.file_name,
            "file_type": mimetype,
            "uploaded_at": image.created_at.isoformat() if image.created_at else None,
            "url": url_for(
                "projects.get_project_image",
                project_id=project_id,
                file_id=image.id,
            ),
        })

    return jsonify({"images": image_payloads}), 200


@projects_bp.route(
    "/projects/<int:project_id>/images/<int:file_id>",
    methods=["GET"],
)
@login_required
def get_project_image(project_id: int, file_id: int):
    image = ProjectFile.query.filter_by(
        id=file_id,
        project_id=project_id,
    ).first()
    if image is None:
        return jsonify({"error": "Project image not found."}), 404

    mimetype = _image_mimetype(image)
    if mimetype is None:
        return jsonify({"error": "Project file is not an image."}), 404
    return _serve_project_file(image, mimetype, file_label="Image file")


@projects_bp.route("/projects/<int:project_id>", methods=["PATCH"])
@login_required
def update_project(project_id: int):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Project not found."}), 404

    changes = request.get_json(silent=True)
    if not isinstance(changes, dict) or not changes:
        return jsonify({"error": "Provide at least one project field to update."}), 400

    normalized, error = _validate_project_changes(changes)
    if error:
        return jsonify({"error": error}), 400

    for field, value in normalized.items():
        setattr(project, field, value)
    db.session.commit()

    total, missing = _project_bom_counts(project_id)
    return jsonify({
        "project": {
            **_project_payload(project),
            "stage": project.status,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            **_completeness(total, missing),
        }
    }), 200


@projects_bp.route("/files/<int:file_id>", methods=["GET"])
@login_required
def get_project_file(file_id: int):
    project_file = db.session.get(ProjectFile, file_id)
    if project_file is None:
        return jsonify({"error": "Project file not found."}), 404

    return _serve_project_file(
        project_file,
        mimetypes.guess_type(project_file.file_name)[0],
    )


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


@projects_bp.route("/bom-lines/<int:material_id>", methods=["PATCH"])
@projects_bp.route("/materials/<int:material_id>", methods=["PATCH"])
@login_required
def update_material(material_id: int):
    material = db.session.get(ProjectMaterial, material_id)
    if material is None:
        return jsonify({"error": "BOM line not found."}), 404

    changes = request.get_json(silent=True)
    if not isinstance(changes, dict) or not changes:
        return jsonify({"error": "Provide at least one BOM field to update."}), 400

    normalized, error = _validate_material_changes(changes)
    if error:
        return jsonify({"error": error}), 400

    old_values = {field: getattr(material, field) for field in normalized}
    project_id = material.colorway.project_id
    for field, value in normalized.items():
        setattr(material, field, value)
    db.session.add_all(_change_entries(
        project_id=project_id,
        user_id=current_user.id,
        action="updated",
        material_id=material.id,
        values=normalized,
        old_values=old_values,
    ))

    db.session.commit()
    return _bom_line_response(material, project_id), 200


@projects_bp.route("/projects/<int:project_id>/bom-lines", methods=["POST"])
@login_required
def create_bom_line(project_id: int):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Project not found."}), 404

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "A JSON object is required."}), 400
    if "colorway_id" not in body:
        return jsonify({"error": "A colorway_id is required."}), 400

    colorway_id = body.pop("colorway_id")
    if isinstance(colorway_id, bool) or not isinstance(colorway_id, int):
        return jsonify({"error": "colorway_id must be an integer."}), 400
    colorway = ProjectColor.query.filter_by(
        id=colorway_id,
        project_id=project_id,
    ).first()
    if colorway is None:
        return jsonify({"error": "Colorway not found for this project."}), 404

    if "quantity" not in body:
        body["quantity"] = None
    normalized, error = _validate_material_changes(body)
    if error:
        return jsonify({"error": error}), 400

    material = ProjectMaterial(colorway=colorway, **normalized)
    db.session.add(material)
    db.session.flush()
    db.session.add_all(_change_entries(
        project_id=project_id,
        user_id=current_user.id,
        action="created",
        material_id=material.id,
        values={field: getattr(material, field) for field in MATERIAL_FIELDS},
    ))
    db.session.commit()
    return _bom_line_response(material, project_id), 201


@projects_bp.route("/bom-lines/<int:material_id>", methods=["DELETE"])
@login_required
def delete_bom_line(material_id: int):
    material = db.session.get(ProjectMaterial, material_id)
    if material is None:
        return jsonify({"error": "BOM line not found."}), 404

    project_id = material.colorway.project_id
    old_values = {field: getattr(material, field) for field in MATERIAL_FIELDS}
    db.session.add_all(_change_entries(
        project_id=project_id,
        user_id=current_user.id,
        action="deleted",
        material_id=material.id,
        values={field: None for field in MATERIAL_FIELDS},
        old_values=old_values,
    ))
    db.session.delete(material)
    db.session.commit()
    return jsonify({
        "deleted": True,
        "id": material_id,
        "missing_bom_items": _missing_bom_count(project_id),
    }), 200


@projects_bp.route("/projects/<int:project_id>/history", methods=["GET"])
@login_required
def project_history(project_id: int):
    if db.session.get(Project, project_id) is None:
        return jsonify({"error": "Project not found."}), 404

    entries = (
        db.session.query(ProjectChangeLog, User.username)
        .outerjoin(User, ProjectChangeLog.user_id == User.id)
        .filter(ProjectChangeLog.project_id == project_id)
        .order_by(ProjectChangeLog.changed_at.desc(), ProjectChangeLog.id.desc())
        .limit(500)
        .all()
    )
    return jsonify({
        "history": [
            {
                "id": entry.id,
                "project_id": entry.project_id,
                "user_id": entry.user_id,
                "username": username,
                "action": entry.action,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "field_name": entry.field_name,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "changed_at": entry.changed_at.isoformat() if entry.changed_at else None,
            }
            for entry, username in entries
        ]
    }), 200


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
        "missing_bom_items": _missing_bom_count(summary.project_id),
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
