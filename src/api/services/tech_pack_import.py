from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pdfplumber

from src.api.lib.material_fields import PROJECT_DETAIL_LABELS, normalize_header
from src.api.models import Project
from src.api.services.import_errors import DocumentImportError
from src.api.services.spreadsheet_utils import (
    cell_text,
    list_workbook_sheets,
    load_sheet_rows,
    pick_sheet_names,
)


def extract_project_details_from_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_from_pdf(path)
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm", ".csv"}:
        return _extract_from_spreadsheet(path)
    raise DocumentImportError(
        f"Unsupported tech pack format '{suffix}'. Use PDF or Excel.",
        status_code=415,
    )


def apply_project_details(project: Project, details: dict[str, Any]) -> list[str]:
    """Fill blank project fields only. Returns list of field names updated."""
    updated: list[str] = []
    for field, value in details.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        current = getattr(project, field, None)
        if current is not None and str(current).strip():
            continue
        setattr(project, field, value)
        updated.append(field)
    return updated


def _extract_from_pdf(path: Path) -> dict[str, Any]:
    try:
        with pdfplumber.open(path) as pdf:
            text_chunks = []
            for page in pdf.pages[:5]:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
            text = "\n".join(text_chunks)
    except OSError as exc:
        raise DocumentImportError(f"Could not read PDF file: {exc}") from exc
    except Exception as exc:
        raise DocumentImportError(f"Invalid or corrupt PDF file: {exc}") from exc

    if not text.strip():
        raise DocumentImportError("PDF contained no readable text.")

    return _parse_label_value_text(text)


def _extract_from_spreadsheet(path: Path) -> dict[str, Any]:
    sheet_names = pick_sheet_names(
        path,
        (
            "make sheet",
            "details",
            "front",
            "bill of material",
            "bom",
            "spec",
            "measurement",
        ),
    )
    combined: dict[str, Any] = {}
    for sheet_name in sheet_names[:6]:
        rows = load_sheet_rows(path, sheet_name)
        details = _parse_metadata_rows(rows)
        for key, value in details.items():
            if key not in combined and value not in (None, ""):
                combined[key] = value
    return combined


def _parse_metadata_rows(rows: list[tuple[int, tuple[Any, ...]]]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for _, row in rows[:25]:
        cells = [cell_text(c) for c in row]
        for index, cell in enumerate(cells):
            if not cell:
                continue
            label = normalize_header(cell)
            for field, labels in PROJECT_DETAIL_LABELS.items():
                if not _header_matches_field(label, field, labels):
                    continue
                value = _value_after_label(cells, index)
                if value is not None:
                    parsed = _coerce_project_value(field, value)
                    if parsed is not None:
                        details[field] = parsed
                        break
                break
    return details


def _header_matches_field(label: str, field: str, labels: tuple[str, ...]) -> bool:
    if label in labels:
        return True
    if field == "description":
        return label.startswith("description")
    if field == "style_no":
        return label.startswith("style no") or label.startswith("style #")
    if field == "po_no":
        return label.startswith("po no") or label.startswith("po #") or label == "po"
    return any(label.startswith(f"{alias}:") or label.startswith(f"{alias} ") for alias in labels)


def _value_after_label(cells: list[Optional[str]], label_index: int) -> Optional[str]:
    if label_index + 1 < len(cells) and cells[label_index + 1]:
        return cells[label_index + 1]
    for idx in range(label_index + 1, min(label_index + 6, len(cells))):
        if cells[idx]:
            return cells[idx]
    return None


def _parse_label_value_text(text: str) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for field, labels in PROJECT_DETAIL_LABELS.items():
            for label in labels:
                pattern = rf"{re.escape(label)}\s*:?\s*(.+)$"
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    parsed = _coerce_project_value(field, value)
                    if parsed is not None:
                        details[field] = parsed
    return details


def _coerce_project_value(field: str, value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date() if field == "project_date" else value.isoformat()
    if isinstance(value, date):
        return value if field == "project_date" else value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    if field == "project_date":
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None
    if field == "po_no":
        if text.endswith(".0"):
            text = text[:-2]
    return text[:1000]
