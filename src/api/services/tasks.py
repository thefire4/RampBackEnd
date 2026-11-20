from src.api.extensions import db
from src.api.models import ProjectColor, ProjectMaterial, Task

REQUIRED_FIELDS = (
    "material",
    "supplier",
    "supplier_contact",
    "location",
    "material_size",
    "uom",
    "color",
)


def missing_bom_fields(material: ProjectMaterial) -> list[str]:
    missing = [
        field
        for field in REQUIRED_FIELDS
        if not (getattr(material, field) or "").strip()
    ]
    if material.quantity is None or material.quantity <= 0:
        missing.append("quantity")
    return missing


def sync_project_tasks(project_id: int) -> None:
    materials = (
        db.session.query(ProjectMaterial)
        .join(ProjectColor, ProjectMaterial.colorway_id == ProjectColor.id)
        .filter(ProjectColor.project_id == project_id)
        .all()
    )
    tasks_by_line = {
        task.bom_line_id: task
        for task in Task.query.filter_by(project_id=project_id).all()
    }

    for material in materials:
        missing = missing_bom_fields(material)
        task = tasks_by_line.get(material.id)
        if missing:
            if task is None:
                task = Task(
                    bom_line_id=material.id,
                    project_id=project_id,
                    missing_fields=missing,
                )
                db.session.add(task)
                tasks_by_line[material.id] = task
            else:
                task.missing_fields = missing
                if task.status == "done":
                    task.status = "open"
        elif task is not None:
            task.missing_fields = []
            task.status = "done"
