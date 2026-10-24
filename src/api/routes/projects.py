from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import func, or_
import math

from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial
from pathlib import Path

from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required

from src.api.extensions import db
from src.api.models import Project
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

EDITABLE_MATERIAL_FIELDS = {
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
}


def _missing_bom_count(project_id: int) -> int:
    count = (
        db.session.query(func.count(ProjectMaterial.id))
        .join(ProjectColor, ProjectMaterial.colorway_id == ProjectColor.id)
        .filter(ProjectColor.project_id == project_id, MISSING_BOM_ITEM)
        .scalar()
    )
    return int(count or 0)


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


@projects_bp.route("/projects", methods=["GET"])
@login_required
def get_projects():
    # Missing-item count per project, computed in one query instead of per row
    missing_counts = (
        db.session.query(
            ProjectColor.project_id.label("project_id"),
            func.count(ProjectMaterial.id).label("missing")
        )
        .join(ProjectMaterial, ProjectMaterial.colorway_id == ProjectColor.id)
        .filter(MISSING_BOM_ITEM)
        .group_by(ProjectColor.project_id)
        .subquery()
    )

    rows = (
        db.session.query(
            Project,
            func.coalesce(missing_counts.c.missing, 0)
        )
        .outerjoin(missing_counts, missing_counts.c.project_id == Project.id)
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
                "style_description": project.description,
                "stage": project.status,
                "po_no": project.po_no,
                "created_at": (
                    project.created_at.isoformat()
                    if project.created_at else None
                ),
                "missing_bom_items": int(missing),
            }
            for project, missing in rows
        ]
    }), 200
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


@projects_bp.route("/materials/<int:material_id>", methods=["PATCH"])
@login_required
def update_material(material_id: int):
    material = db.session.get(ProjectMaterial, material_id)
    if material is None:
        return jsonify({"error": "BOM line not found."}), 404

    changes = request.get_json(silent=True)
    if not isinstance(changes, dict) or not changes:
        return jsonify({"error": "Provide at least one BOM field to update."}), 400

    unknown_fields = set(changes) - EDITABLE_MATERIAL_FIELDS
    if unknown_fields:
        return jsonify({"error": "One or more BOM fields cannot be edited."}), 400

    for field, value in changes.items():
        if field == "quantity":
            if value is None:
                material.quantity = None
                continue
            if isinstance(value, bool):
                return jsonify({"error": "Quantity must be a non-negative number."}), 400
            try:
                quantity = float(value)
            except (TypeError, ValueError):
                return jsonify({"error": "Quantity must be a non-negative number."}), 400
            if not math.isfinite(quantity) or quantity < 0:
                return jsonify({"error": "Quantity must be a non-negative number."}), 400
            material.quantity = quantity
            continue

        if value is not None and not isinstance(value, str):
            return jsonify({"error": f"{field} must be text or null."}), 400
        setattr(material, field, value.strip() or None if isinstance(value, str) else None)

    db.session.commit()
    project_id = material.colorway.project_id
    return jsonify({
        "material": _material_payload(material),
        "missing_bom_items": _missing_bom_count(project_id),
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
