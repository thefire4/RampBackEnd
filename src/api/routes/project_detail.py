import mimetypes
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required

from src.api.extensions import db
from src.api.models import Project, ProjectFile
from src.api.routes.projects import (
    MATERIAL_FIELDS,
    REQUIRED_MATERIAL_FIELDS,
    _material_payload,
    _missing_bom_count,
    _upload_dir,
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

    return jsonify({
        "project": _project_payload(project),
        "colorways": colorways,
        "files": [_file_payload(f) for f in sorted(project.files, key=lambda f: f.id)],
        "missing_bom_items": _missing_bom_count(project.id),
    }), 200


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