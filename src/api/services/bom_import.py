from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.api.lib.material_fields import is_colorway_column, match_bom_field, normalize_header
from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial
from src.api.services.import_errors import DocumentImportError
from src.api.services.spreadsheet_utils import (
    cell_text,
    find_header_row,
    load_sheet_rows,
    parse_quantity,
    pick_sheet_names,
    row_has_content,
)


@dataclass
class BomImportResult:
    materials_created: int = 0
    colorways_created: int = 0
    rows_processed: int = 0
    sheet_name: Optional[str] = None
    skipped_rows: list[int] = field(default_factory=list)


def import_bom_from_file(
    path: Path,
    project: Project,
    *,
    file_name: Optional[str] = None,
) -> BomImportResult:
    file_name = file_name or path.name
    sheet_names = pick_sheet_names(path, ("bill of material", "bom"))
    last_error: Optional[str] = None
    for sheet_name in sheet_names:
        try:
            rows = load_sheet_rows(path, sheet_name)
            header = find_header_row(rows)
            if header is None:
                last_error = f"No BOM header row found in sheet '{sheet_name}'."
                continue
            header_row_number, field_map, raw_headers = header
            color_columns = _detect_colorway_columns(raw_headers, field_map)
            if color_columns:
                return _import_wide_bom(
                    project,
                    rows,
                    header_row_number,
                    field_map,
                    color_columns,
                    file_name=file_name,
                    sheet_name=sheet_name,
                )
            return _import_long_bom(
                project,
                rows,
                header_row_number,
                field_map,
                raw_headers,
                file_name=file_name,
                sheet_name=sheet_name,
            )
        except DocumentImportError:
            raise
        except Exception as exc:
            last_error = str(exc)
    raise DocumentImportError(
        last_error or "Could not locate a bill of materials in this file."
    )


def _detect_colorway_columns(
    raw_headers: dict[int, str],
    field_map: dict[int, str],
) -> list[tuple[int, str]]:
    columns: list[tuple[int, str]] = []
    for col_index, header in raw_headers.items():
        mapped = field_map.get(col_index)
        if is_colorway_column(header, mapped):
            columns.append((col_index, str(header).strip()))
    return columns


def _get_or_create_colorway(project: Project, name: str) -> tuple[ProjectColor, bool]:
    normalized = name.strip()
    existing = ProjectColor.query.filter_by(
        project_id=project.id,
        name=normalized,
    ).first()
    if existing:
        return existing, False
    colorway = ProjectColor(name=normalized, project_id=project.id)
    project.colorways.append(colorway)
    db.session.add(colorway)
    return colorway, True


def _build_row_payload(
    row: tuple[Any, ...],
    field_map: dict[int, str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for col_index, canonical in field_map.items():
        if col_index >= len(row):
            continue
        value = cell_text(row[col_index])
        if value is None:
            continue
        if canonical == "quantity":
            payload[canonical] = parse_quantity(row[col_index])
        else:
            payload[canonical] = value
    return payload


def _should_skip_bom_row(name: Optional[str]) -> bool:
    if not name:
        return True
    upper = name.upper()
    if name.startswith("*") or "DO NOT PURCHASE" in upper:
        return True
    if "STREET" in upper and any(token in upper for token in ("MT", "AVE", "BOZEMAN")):
        return True
    normalized = normalize_header(name)
    if "match to bom" in normalized:
        return True
    if normalized in {"fabric", "trims", "thread", "colorways"}:
        return True
    return False


def _compose_notes(payload: dict[str, Any]) -> Optional[str]:
    parts: list[str] = []
    for key in ("category", "yield", "measurement"):
        value = payload.get(key)
        if value is None or str(value).strip() == "":
            continue
        label = key.replace("_", " ").title()
        parts.append(f"{label}: {value}")
    existing = payload.get("notes")
    if existing:
        parts.append(str(existing))
    if not parts:
        return None
    return " | ".join(parts)[:1000]


def _create_material(
    colorway: ProjectColor,
    payload: dict[str, Any],
    *,
    file_name: str,
    row_number: int,
) -> ProjectMaterial:
    notes_payload = dict(payload)
    material = ProjectMaterial(
        colorway=colorway,
        name=payload.get("name"),
        material=payload.get("material"),
        supplier=payload.get("supplier"),
        supplier_contact=payload.get("supplier_contact"),
        quantity=payload.get("quantity"),
        location=payload.get("location"),
        article_no=payload.get("article_no"),
        material_size=payload.get("material_size"),
        uom=payload.get("uom"),
        color=payload.get("color"),
        notes=_compose_notes(notes_payload),
        import_source_file=file_name,
        import_source_row=row_number,
        import_field_sources=_field_sources(
            file_name=file_name,
            row_number=row_number,
            payload=payload,
        ),
    )
    colorway.materials.append(material)
    return material


def _field_sources(
    *,
    file_name: str,
    row_number: int,
    payload: dict[str, Any],
) -> str:
    fields = {key: {"file": file_name, "row": row_number} for key in payload}
    return json.dumps({"import": {"file": file_name, "row": row_number, "fields": fields}})


def _import_wide_bom(
    project: Project,
    rows: list[tuple[int, tuple[Any, ...]]],
    header_row_number: int,
    field_map: dict[int, str],
    color_columns: list[tuple[int, str]],
    *,
    file_name: str,
    sheet_name: str,
) -> BomImportResult:
    result = BomImportResult(sheet_name=sheet_name)
    colorway_cache: dict[str, ProjectColor] = {}

    for row_number, row in rows:
        if row_number <= header_row_number:
            continue
        if not row_has_content(row):
            continue
        name = cell_text(row[0]) if row else None
        if _should_skip_bom_row(name):
            result.skipped_rows.append(row_number)
            continue

        base_payload = _build_row_payload(row, field_map)
        if not base_payload.get("name"):
            base_payload["name"] = name
        result.rows_processed += 1

        for col_index, colorway_name in color_columns:
            color_value = cell_text(row[col_index]) if col_index < len(row) else None
            if colorway_name not in colorway_cache:
                colorway, created = _get_or_create_colorway(project, colorway_name)
                colorway_cache[colorway_name] = colorway
                if created:
                    result.colorways_created += 1
            else:
                colorway = colorway_cache[colorway_name]

            payload = dict(base_payload)
            payload["color"] = color_value or colorway_name
            _create_material(
                colorway,
                payload,
                file_name=file_name,
                row_number=row_number,
            )
            result.materials_created += 1

    if result.materials_created == 0:
        raise DocumentImportError(
            f"No BOM rows were imported from sheet '{sheet_name}'."
        )
    return result


def _import_long_bom(
    project: Project,
    rows: list[tuple[int, tuple[Any, ...]]],
    header_row_number: int,
    field_map: dict[int, str],
    raw_headers: dict[int, str],
    *,
    file_name: str,
    sheet_name: str,
) -> BomImportResult:
    result = BomImportResult(sheet_name=sheet_name)
    color_columns = _detect_colorway_columns(raw_headers, field_map)
    colorway_cache: dict[str, ProjectColor] = {}

    for row_number, row in rows:
        if row_number <= header_row_number:
            continue
        if not row_has_content(row):
            continue

        base_payload = _build_row_payload(row, field_map)
        name = base_payload.get("name") or (cell_text(row[0]) if row else None)
        if _should_skip_bom_row(name):
            result.skipped_rows.append(row_number)
            continue
        if not name and not base_payload.get("material"):
            result.skipped_rows.append(row_number)
            continue

        base_payload["name"] = name
        result.rows_processed += 1

        row_colors: list[tuple[str, Optional[str]]] = []
        explicit_color = base_payload.pop("color", None)
        if explicit_color:
            row_colors.append((explicit_color, explicit_color))
        for _, color_header in color_columns:
            col_index = next(
                (idx for idx, raw in raw_headers.items() if raw == color_header),
                None,
            )
            if col_index is None or col_index >= len(row):
                continue
            value = cell_text(row[col_index])
            if value:
                row_colors.append((color_header, value))

        if not row_colors:
            row_colors.append(("Default", explicit_color))

        for colorway_name, color_value in row_colors:
            if colorway_name not in colorway_cache:
                colorway, created = _get_or_create_colorway(project, colorway_name)
                colorway_cache[colorway_name] = colorway
                if created:
                    result.colorways_created += 1
            else:
                colorway = colorway_cache[colorway_name]

            payload = dict(base_payload)
            payload["color"] = color_value or colorway_name
            _create_material(
                colorway,
                payload,
                file_name=file_name,
                row_number=row_number,
            )
            result.materials_created += 1

    if result.materials_created == 0:
        raise DocumentImportError(
            f"No BOM rows were imported from sheet '{sheet_name}'."
        )
    return result
