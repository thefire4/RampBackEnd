import mimetypes
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required
from sqlalchemy.orm import joinedload

from src.api.extensions import db
from src.api.models import Project, ProjectFile, ProjectColor, ProjectMaterial, ValueSource
from src.api.services.provenance import serialize_values
from src.api.routes.projects import (
    MATERIAL_FIELDS,
    MISSING_BOM_ITEM,
    REQUIRED_MATERIAL_FIELDS,
    _completeness,
    _material_payload,
    _missing_bom_count,
    _project_bom_counts,
    _upload_dir,
    project_source_payload,
)

project_detail_bp = Blueprint("project_detail", __name__)

#windows doesn't know .xlsx
for _ext, _type in {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    ".xltx": "application/vnd.openxmlformats-officedocument.spreadsheetml.template",
    ".xltm": "application/vnd.ms-excel.template.macroEnabled.12",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}.items():
    mimetypes.add_type(_type, _ext)


def _iso(value):
    return value.isoformat() if value else None


def _is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def missing_fields(material):
    missing = [f for f in MATERIAL_FIELDS if f in REQUIRED_MATERIAL_FIELDS and _is_blank(getattr(material, f))]
    if material.quantity is None or material.quantity <= 0:
        missing.append("quantity")
    return missing


def _project_payload(project):
    return {
        "id": project.id,
        "name": project.name,
        "stage": project.status,
        "style_no": project.style_no,
        "po_no": project.po_no,
        "project_date": _iso(project.project_date),
        "customer": project.customer,
        "size_range": project.size_range,
        "season": project.season,
        "fabric_yarn": project.fabric_yarn,
        "designer": project.designer,
        "weight": project.weight,
        "style_description": project.description,
        "created_at": _iso(getattr(project, "created_at", None)),
    }


def _file_payload(file):
    return {
        "id": file.id,
        "file_name": file.file_name,
        "file_type": file.file_type,
        "url": f"/api/files/{file.id}",
        "created_at": _iso(getattr(file, "created_at", None)),
    }


@project_detail_bp.route("/projects/<int:project_id>", methods=["GET"])
@login_required
def get_project(project_id):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Project not found."}), 404

    colorways = [
        {
            "id": colorway.id,
            "name": colorway.name,
            "materials": [
                {**_material_payload(m), "missing_fields": missing_fields(m)}
                for m in sorted(colorway.materials, key=lambda m: m.id)
            ],
        }
        for colorway in sorted(project.colorways, key=lambda c: c.id)
    ]

    source_payload = project_source_payload(project)
    by_id = {m["id"]: m["fields"] for m in source_payload["materials"]}
    for colorway in colorways:
        for material in colorway["materials"]:
            material["fields"] = by_id[material["id"]]

    return jsonify({
        "project": {
            **source_payload,
            **_project_payload(project),
            **_completeness(*_project_bom_counts(project.id)),
        },
        "colorways": colorways,
        "files": [_file_payload(f) for f in sorted(project.files, key=lambda f: f.id)],
        "missing_bom_items": _missing_bom_count(project.id),
    }), 200


def _part_payload(material, sources):
    project_id = material.colorway.project_id
    return {
        **_material_payload(material),
        "project_id": project_id,
        "colorway_name": material.colorway.name,
        "missing_fields": missing_fields(material),
        "details_url": f"/api/projects/{project_id}/materials/{material.id}",
        "fields": serialize_values(material, MATERIAL_FIELDS, sources),
    }


@project_detail_bp.route("/projects/<int:project_id>/missing-items", methods=["GET"])
@project_detail_bp.route("/projects/<int:project_id>/incomplete-materials", methods=["GET"])
@login_required
def get_missing_items(project_id):
    if db.session.get(Project, project_id) is None:
        return jsonify(error="Project not found."), 404

    materials = (
        ProjectMaterial.query.join(ProjectColor)
        .options(joinedload(ProjectMaterial.colorway))
        .filter(ProjectColor.project_id == project_id, MISSING_BOM_ITEM)
        .order_by(ProjectColor.id, ProjectMaterial.id)
        .all()
    )
    sources = {}
    if materials:
        for source in ValueSource.query.filter(
            ValueSource.project_id == project_id,
            ValueSource.entity_type == "material",
            ValueSource.entity_id.in_([m.id for m in materials]),
        ).all():
            sources.setdefault(source.entity_id, {})[source.field] = source
    items = [_part_payload(m, sources.get(m.id, {})) for m in materials]
    return jsonify(project_id=project_id, missing_items=items, total=len(items)), 200


@project_detail_bp.route("/projects/<int:project_id>/materials/<int:material_id>", methods=["GET"])
@login_required
def get_part_details(project_id, material_id):
    if db.session.get(Project, project_id) is None:
        return jsonify(error="Project not found."), 404
    material = (
        ProjectMaterial.query.join(ProjectColor)
        .options(joinedload(ProjectMaterial.colorway))
        .filter(ProjectColor.project_id == project_id, ProjectMaterial.id == material_id)
        .first()
    )
    if material is None:
        return jsonify(error="BOM line not found."), 404
    sources = ValueSource.query.filter_by(
        project_id=project_id, entity_type="material", entity_id=material_id,
    ).all()
    return jsonify(material=_part_payload(material, {s.field: s for s in sources})), 200


def _resolve_stored_path(file):
    """Where the file is on disk, or None if it's missing or outside the upload folder."""
    if not file.file_path:
        return None
    root = _upload_dir().resolve()
    stored = Path(file.file_path)
    path = (stored if stored.is_absolute() else root / stored).resolve()
    # Never serve anything outside the upload folder, whatever file_path

    if not path.is_relative_to(root) or not path.is_file():
        return None
    return path


@project_detail_bp.route("/files/<int:file_id>", methods=["GET"])
@login_required
def get_file(file_id):
    file = db.session.get(ProjectFile, file_id)
    if file is None:
        return jsonify({"error": "File not found."}), 404

    path = _resolve_stored_path(file)
    if path is None:
        return jsonify({"error": "This file is missing from storage."}), 404

    # The import stores types like "xlsx" or "pdf"; turn those into real content types
    mimetype = file.file_type if file.file_type and "/" in file.file_type else None
    mimetype = mimetype or mimetypes.guess_type(file.file_name)[0] or "application/octet-stream"

    response = send_file(
        path,
        mimetype=mimetype,
        as_attachment=request.args.get("download") == "1",
        download_name=file.file_name,
    )
    # Uploaded files (an SVG sketch, say) must never run scripts on our site
    response.headers["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
