from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Optional

from src.api.lib.material_fields import is_size_column, normalize_header
from src.api.extensions import db
from src.api.models import PointsMeasured, Project
from src.api.services.import_errors import DocumentImportError
from src.api.services.spreadsheet_utils import (
    cell_text,
    load_sheet_rows,
    pick_sheet_names,
    row_has_content,
)


@dataclass
class MeasurementImportResult:
    points_created: int = 0
    sheet_name: Optional[str] = None


def import_measurements_from_file(path: Path, project: Project) -> MeasurementImportResult:
    sheet_names = pick_sheet_names(
        path,
        ("measurement", "spec", "specification", "grading"),
    )
    best: Optional[tuple[int, str, tuple]] = None
    for sheet_name in sheet_names:
        rows = load_sheet_rows(path, sheet_name)
        header = _find_measurement_header(rows)
        if header is None:
            continue
        score = _measurement_sheet_score(sheet_name, header)
        if best is None or score > best[0]:
            best = (score, sheet_name, header)

    if best is None:
        return MeasurementImportResult()

    _, sheet_name, header = best
    header_row, code_col, name_col, tol_col, size_cols, grade_col, note_col = header
    created = 0
    rows = load_sheet_rows(path, sheet_name)
    for row_number, row in rows:
        if row_number <= header_row:
            continue
        if not row_has_content(row):
            continue
        name = cell_text(row[name_col]) if name_col < len(row) else None
        if not name:
            continue
        if "difference" in name.lower() and not cell_text(
            row[code_col] if code_col < len(row) else None
        ):
            continue
        code = cell_text(row[code_col]) if code_col < len(row) else None
        tol = (
            _format_inches(row[tol_col])
            if tol_col is not None and tol_col < len(row)
            else None
        )
        grade = (
            _format_inches(row[grade_col])
            if grade_col is not None and grade_col < len(row)
            else None
        )
        notes = (
            cell_text(row[note_col])
            if note_col is not None and note_col < len(row)
            else None
        )

        for size_col, size_label in size_cols:
            if size_col >= len(row):
                continue
            measure_raw = row[size_col]
            if measure_raw is None or str(measure_raw).strip() == "":
                continue
            measure = _format_inches(measure_raw)
            point = PointsMeasured(
                project_id=project.id,
                code=code,
                name=name,
                tol=tol,
                sizes=size_label,
                measure=measure,
                grade=grade,
                notes=notes,
            )
            db.session.add(point)
            created += 1

    return MeasurementImportResult(points_created=created, sheet_name=sheet_name)


def _measurement_sheet_score(sheet_name: str, header: tuple) -> int:
    size_cols = header[4]
    score = len(size_cols) * 10
    lowered = sheet_name.lower()
    if "measurement" in lowered or "grading" in lowered:
        score += 20
    if lowered == "spec" or lowered.endswith(" spec"):
        score += 15
    if "old" in lowered or "approval" in lowered or "eval" in lowered:
        score -= 30
    if "comment" in lowered:
        score -= 40
    return score


def _find_measurement_header(
    rows: list[tuple[int, tuple[Any, ...]]],
) -> Optional[tuple[int, int, int, Optional[int], list[tuple[int, str]], Optional[int], Optional[int]]]:
    best = None
    for row_number, row in rows[:80]:
        size_cols: list[tuple[int, str]] = []
        code_col = None
        name_col = None
        tol_col = None
        grade_col = None
        note_col = None
        for col_index, cell in enumerate(row):
            header = cell_text(cell)
            if not header:
                continue
            normalized = normalize_header(header)
            if normalized in {"ref", "code", "point", "pom", "pom code"}:
                code_col = col_index
            elif normalized in {"points measured", "point name", "description", "measurement"}:
                name_col = col_index
            elif normalized.startswith("tol"):
                tol_col = col_index
            elif normalized == "grade":
                grade_col = col_index
            elif normalized in {"note", "notes"}:
                note_col = col_index
            elif is_size_column(header):
                size_cols.append((col_index, str(header).strip().upper()))

        if name_col is not None and size_cols:
            score = len(size_cols)
            if best is None or score > best[0]:
                best = (
                    score,
                    row_number,
                    code_col or 0,
                    name_col,
                    tol_col,
                    size_cols,
                    grade_col,
                    note_col,
                )
    if best is None:
        return None
    _, row_number, code_col, name_col, tol_col, size_cols, grade_col, note_col = best
    return row_number, code_col, name_col, tol_col, size_cols, grade_col, note_col


def _format_inches(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _decimal_to_fraction_str(Decimal(str(value)))
    return cell_text(value)


def _decimal_to_fraction_str(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole = int(value)
    remainder = value - Decimal(whole)
    if remainder == 0:
        return f"{sign}{whole}"
    frac = Fraction(remainder).limit_denominator(16)
    if frac.numerator == 0:
        return f"{sign}{whole}"
    if whole == 0:
        return f"{sign}{frac.numerator}/{frac.denominator}"
    return f"{sign}{whole} {frac.numerator}/{frac.denominator}"
