from datetime import date, datetime
from decimal import Decimal
import json

VALID_ACTIONS = {
    "created",
    "updated",
    "deleted",
    "imported",
}

VALID_ENTITY_TYPES = {
    "project",
    "colorway",
    "material",
    "measurement",
    "file",
    "comment",
}

def _serialize_value(value):
    """Convert values into strings suitable for text columns."""
    if value is None:
        return None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)

    return str(value)

"""Record one project-related change."""
def log_project_change(
    cursor,
    project_id,
    user_id,
    action,
    entity_type,
    entity_id=None,
    field_name=None,
    old_value=None,
    new_value=None,
):
    if action not in VALID_ACTIONS:
        raise ValueError(f"Invalid audit action: {action}")

    if entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"Invalid entity type: {entity_type}")

    cursor.execute(
        """
        INSERT INTO project_change_log (
            project_id,
            user_id,
            action,
            entity_type,
            entity_id,
            field_name,
            old_value,
            new_value,
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            project_id,
            user_id,
            action,
            entity_type,
            entity_id,
            field_name,
            _serialize_value(old_value),
            _serialize_value(new_value)
        ),
    )

"""Record project creation or document-based import."""
def log_project_created(
    cursor,
    project_id,
    user_id,
    project_name,
    action="created",
):
    if action not in {"created", "imported"}:
        raise ValueError("Expected 'created' or 'imported'")

    log_project_change(
        cursor=cursor,
        project_id=project_id,
        user_id=user_id,
        action=action,
        entity_type="project",
        entity_id=project_id,
        field_name=None,
        old_value=None,
        new_value=project_name
    )

"""Return project history with newest changes first."""
def get_project_history(cursor, project_id, limit=100, offset=0):

    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")

    if offset < 0:
        raise ValueError("offset cannot be negative")

    cursor.execute(
        """
        SELECT
            l.id,
            l.project_id,
            l.user_id,
            u.username,
            l.action,
            l.entity_type,
            l.entity_id,
            l.field_name,
            l.old_value,
            l.new_value,
            l.changed_at
        FROM project_change_log AS l
        LEFT JOIN users AS u
            ON u.id = l.user_id
        WHERE l.project_id = %s
        ORDER BY l.changed_at DESC, l.id DESC
        LIMIT %s OFFSET %s
        """,
        (project_id, limit, offset),
    )
    entries = cursor.fetchall()
    for entry in entries:
        if entry.get("changed_at"):
            entry["changed_at"] = (
                entry["changed_at"].isoformat()
            )

    return entries

