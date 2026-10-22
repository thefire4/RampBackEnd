"""Import tech packs / BOM spreadsheets from a directory into projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from src.api.extensions import db
from src.api.models import Project, User
from src.api.services.document_import import DocumentImportSummary, import_document_path
from src.api.services.import_errors import DocumentImportError


SUPPORTED_SUFFIXES = {".xlsx", ".xlsm", ".csv", ".pdf", ".xltx", ".xltm"}


@dataclass
class BatchImportResult:
    imported: list[DocumentImportSummary] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


def import_projects_from_directory(
    directory: Path,
    *,
    user_id: int,
    patterns: Optional[Iterable[str]] = None,
) -> BatchImportResult:
    """
    Create one project per supported file in ``directory``.

    Skips hidden files and leaves failed files in ``errors`` with a clear message.
    """
    if not directory.is_dir():
        raise DocumentImportError(f"Directory not found: {directory}")

    user = db.session.get(User, user_id)
    if user is None:
        raise DocumentImportError(f"User id {user_id} was not found.")

    result = BatchImportResult()
    paths = _iter_import_paths(directory, patterns)

    for path in paths:
        project_name = path.stem[:100] or "Imported project"
        project = Project(name=project_name, status="in progress")
        db.session.add(project)
        db.session.flush()
        try:
            summary = import_document_path(
                path,
                project=project,
                user_id=user_id,
                original_filename=path.name,
            )
            result.imported.append(summary)
        except DocumentImportError as exc:
            db.session.rollback()
            result.errors.append((path.name, exc.message))
        except Exception as exc:
            db.session.rollback()
            result.errors.append((path.name, f"Unexpected error while importing file: {exc}"))

    return result


def _iter_import_paths(
    directory: Path,
    patterns: Optional[Iterable[str]],
) -> list[Path]:
    if patterns:
        paths: list[Path] = []
        for pattern in patterns:
            paths.extend(directory.glob(pattern))
    else:
        paths = [p for p in directory.iterdir() if p.is_file()]

    unique = sorted({p.resolve() for p in paths if p.suffix.lower() in SUPPORTED_SUFFIXES})
    return [Path(p) for p in unique if not p.name.startswith(".")]
