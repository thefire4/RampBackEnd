from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from src.api.extensions import db
from src.api.models import Project, ProjectFile
from src.api.services.bom_import import BomImportResult, import_bom_from_file
from src.api.services.import_errors import DocumentImportError
from src.api.services.measurements_import import (
    MeasurementImportResult,
    import_measurements_from_file,
)
from src.api.services.tech_pack_import import (
    apply_project_details,
    extract_project_details_from_file,
)


@dataclass
class DocumentImportSummary:
    project_id: int
    project_fields_updated: list[str] = field(default_factory=list)
    bom: Optional[BomImportResult] = None
    measurements: Optional[MeasurementImportResult] = None
    file_record_id: Optional[int] = None


def import_uploaded_document(
    *,
    upload: FileStorage,
    project: Project,
    user_id: int,
    upload_dir: Path,
    import_bom: bool = True,
    import_measurements: bool = True,
    import_project_details: bool = True,
) -> DocumentImportSummary:
    if not upload or not upload.filename:
        raise DocumentImportError("No file was uploaded.")

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in {".xlsx", ".xlsm", ".csv", ".pdf", ".xltx", ".xltm"}:
        raise DocumentImportError(
            f"Unsupported file type '{suffix}'. Upload Excel, CSV, or PDF.",
            status_code=415,
        )

    stored_path = _persist_upload(upload, upload_dir, suffix)
    try:
        return _import_saved_file(
            stored_path,
            project=project,
            user_id=user_id,
            original_filename=upload.filename,
            import_bom=import_bom,
            import_measurements=import_measurements,
            import_project_details=import_project_details,
        )
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise


def import_document_path(
    path: Path,
    *,
    project: Project,
    user_id: int,
    original_filename: Optional[str] = None,
    import_bom: bool = True,
    import_measurements: bool = True,
    import_project_details: bool = True,
) -> DocumentImportSummary:
    return _import_saved_file(
        path,
        project=project,
        user_id=user_id,
        original_filename=original_filename or path.name,
        import_bom=import_bom,
        import_measurements=import_measurements,
        import_project_details=import_project_details,
    )


def _import_saved_file(
    path: Path,
    *,
    project: Project,
    user_id: int,
    original_filename: str,
    import_bom: bool,
    import_measurements: bool,
    import_project_details: bool,
) -> DocumentImportSummary:
    file_name = original_filename
    summary = DocumentImportSummary(project_id=project.id)

    if import_project_details and path.suffix.lower() in {
        ".xlsx",
        ".xlsm",
        ".csv",
        ".pdf",
        ".xltx",
        ".xltm",
    }:
        details = extract_project_details_from_file(path)
        summary.project_fields_updated = apply_project_details(project, details)

    if import_bom and path.suffix.lower() in {".xlsx", ".xlsm", ".csv", ".xltx", ".xltm"}:
        summary.bom = import_bom_from_file(path, project, file_name=file_name)

    if import_measurements and path.suffix.lower() in {
        ".xlsx",
        ".xlsm",
        ".csv",
        ".xltx",
        ".xltm",
    }:
        summary.measurements = import_measurements_from_file(path, project)

    file_record = ProjectFile(
        project=project,
        user_id=user_id,
        file_name=file_name,
        file_path=str(path),
        file_type=path.suffix.lower().lstrip("."),
    )
    db.session.add(file_record)
    db.session.commit()
    summary.file_record_id = file_record.id
    return summary


def _persist_upload(upload: FileStorage, upload_dir: Path, suffix: str) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = secure_filename(Path(upload.filename).stem) or "upload"
    unique = uuid.uuid4().hex[:8]
    target = upload_dir / f"{safe_stem}_{unique}{suffix}"
    try:
        upload.save(target)
    except OSError as exc:
        raise DocumentImportError(f"Could not save uploaded file: {exc}") from exc
    return target
