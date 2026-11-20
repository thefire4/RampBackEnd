from flask import Blueprint, jsonify, request
from flask_login import login_required

from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial, Vendor
from src.api.routes.projects import _material_payload

vendors_bp = Blueprint("vendors", __name__)

VENDOR_FIELD_LENGTHS = {
    "name": 255,
    "contact_name": 255,
    "email": 255,
    "phone": 50,
}
VENDOR_FIELDS = set(VENDOR_FIELD_LENGTHS) | {"notes"}


def _vendor_payload(vendor: Vendor) -> dict:
    return {
        "id": vendor.id,
        "name": vendor.name,
        "contact_name": vendor.contact_name,
        "email": vendor.email,
        "phone": vendor.phone,
        "notes": vendor.notes,
    }


def _validate_vendor_changes(changes: dict, *, require_name: bool = False):
    unknown_fields = set(changes) - VENDOR_FIELDS
    if unknown_fields:
        return None, "One or more vendor fields cannot be edited."
    if require_name and "name" not in changes:
        return None, "Vendor name is required."

    normalized = {}
    for field, value in changes.items():
        if value is not None and not isinstance(value, str):
            return None, f"{field.replace('_', ' ').capitalize()} must be text or null."
        if value is None:
            if field == "name":
                return None, "Vendor name cannot be blank."
            normalized[field] = None
            continue
        value = value.strip()
        if field == "name" and not value:
            return None, "Vendor name cannot be blank."
        if len(value) > VENDOR_FIELD_LENGTHS.get(field, 5000):
            return None, f"{field.replace('_', ' ').capitalize()} is too long."
        normalized[field] = value or None

    return normalized, None


@vendors_bp.route("/vendors", methods=["GET"])
@login_required
def list_vendors():
    vendors = Vendor.query.order_by(Vendor.name, Vendor.id).all()
    return jsonify({"vendors": [_vendor_payload(vendor) for vendor in vendors]}), 200


@vendors_bp.route("/vendors", methods=["POST"])
@login_required
def create_vendor():
    changes = request.get_json(silent=True)
    if not isinstance(changes, dict):
        return jsonify({"error": "A JSON object is required."}), 400
    normalized, error = _validate_vendor_changes(changes, require_name=True)
    if error:
        return jsonify({"error": error}), 400

    vendor = Vendor(**normalized)
    db.session.add(vendor)
    db.session.commit()
    return jsonify({"vendor": _vendor_payload(vendor)}), 201


@vendors_bp.route("/vendors/<int:vendor_id>", methods=["GET"])
@login_required
def get_vendor(vendor_id: int):
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None:
        return jsonify({"error": "Vendor not found."}), 404
    return jsonify({"vendor": _vendor_payload(vendor)}), 200


@vendors_bp.route("/vendors/<int:vendor_id>", methods=["PATCH"])
@login_required
def update_vendor(vendor_id: int):
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None:
        return jsonify({"error": "Vendor not found."}), 404
    changes = request.get_json(silent=True)
    if not isinstance(changes, dict) or not changes:
        return jsonify({"error": "Provide at least one vendor field to update."}), 400

    normalized, error = _validate_vendor_changes(changes)
    if error:
        return jsonify({"error": error}), 400
    for field, value in normalized.items():
        setattr(vendor, field, value)
    db.session.commit()
    return jsonify({"vendor": _vendor_payload(vendor)}), 200


@vendors_bp.route("/vendors/<int:vendor_id>", methods=["DELETE"])
@login_required
def delete_vendor(vendor_id: int):
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None:
        return jsonify({"error": "Vendor not found."}), 404

    ProjectMaterial.query.filter_by(vendor_id=vendor_id).update(
        {ProjectMaterial.vendor_id: None},
        synchronize_session=False,
    )
    db.session.delete(vendor)
    db.session.commit()
    return jsonify({"deleted": True, "id": vendor_id}), 200


@vendors_bp.route("/vendors/<int:vendor_id>/bom-lines", methods=["GET"])
@login_required
def list_vendor_bom_lines(vendor_id: int):
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None:
        return jsonify({"error": "Vendor not found."}), 404

    rows = (
        db.session.query(ProjectMaterial, ProjectColor, Project)
        .join(ProjectColor, ProjectMaterial.colorway_id == ProjectColor.id)
        .join(Project, ProjectColor.project_id == Project.id)
        .filter(ProjectMaterial.vendor_id == vendor_id)
        .order_by(Project.id, ProjectColor.id, ProjectMaterial.id)
        .all()
    )
    return jsonify({
        "vendor_id": vendor_id,
        "bom_lines": [
            {
                **_material_payload(material),
                "project_id": project.id,
                "project_name": project.name,
                "colorway_name": colorway.name,
            }
            for material, colorway, project in rows
        ],
    }), 200
