"""Field-level provenance shared by imports, manual edits, and dashboard responses."""
from src.api.extensions import db
from src.api.models import ValueSource

PROJECT_FIELDS = ("name", "status", "style_no", "po_no", "project_date", "customer", "size_range", "season", "fabric_yarn", "designer", "weight", "description")
MATERIAL_FIELDS = ("name", "material", "supplier", "supplier_contact", "quantity", "location", "article_no", "material_size", "uom", "color", "notes")
MEASUREMENT_FIELDS = ("code", "name", "tol", "sizes", "measure", "grade", "notes")


def record_source(project_id, entity_type, entity_id, field, *, kind, file=None, sheet=None, row=None, user_id=None):
    source = ValueSource.query.filter_by(project_id=project_id, entity_type=entity_type, entity_id=entity_id, field=field).first()
    if source is None:
        source = ValueSource(project_id=project_id, entity_type=entity_type, entity_id=entity_id, field=field)
        db.session.add(source)
    source.kind = kind
    source.file_id = file.id if file else None
    source.file_name = file.file_name if file else None
    source.sheet = sheet
    source.row = row
    source.user_id = user_id


def serialize_values(entity, fields, sources):
    values = {}
    for field in fields:
        value = getattr(entity, field)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        source = sources.get(field)
        provenance = {"kind": "missing" if value is None else "unknown", "file_name": None, "file_id": None, "url": None, "sheet": None, "row": None, "user_id": None}
        if source:
            provenance.update(kind=source.kind, file_name=source.file_name, file_id=source.file_id,
                              url=f"/api/projects/{source.project_id}/files/{source.file_id}" if source.file_id else None,
                              sheet=source.sheet, row=source.row, user_id=source.user_id)
        values[field] = {"value": value, "source": provenance}
    return values
