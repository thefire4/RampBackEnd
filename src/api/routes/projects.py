from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import func, or_

from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial

projects_bp = Blueprint("projects", __name__)


def _blank(column):
    return func.coalesce(func.trim(column), "") == ""


# A BOM item counts as missing when any key field hasn't been filled in.
# Change this one rule if the team settles on a different definition.
MISSING_BOM_ITEM = or_(
    _blank(ProjectMaterial.material),
    _blank(ProjectMaterial.supplier),
    _blank(ProjectMaterial.color),
    ProjectMaterial.quantity.is_(None),
)


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
