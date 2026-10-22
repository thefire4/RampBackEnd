from __future__ import annotations

from pathlib import Path

import pytest

from src.api.extensions import db
from src.api.models import PointsMeasured, Project, ProjectMaterial, User
from src.api.services.document_import import import_document_path
from src.api.services.import_errors import DocumentImportError
from src.api.services.tech_pack_import import apply_project_details, extract_project_details_from_file

FILES_DIR = Path(__file__).resolve().parents[1] / "files"
DUCKWORTH_BOM = FILES_DIR / "DW11038_M's Snowcrest_Shirt Jac_ REV2 BTUSA PO 1654 07.10.2026 (2).xlsx"


@pytest.fixture
def app():
    from src.api import create_app

    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with application.app_context():
        db.create_all()
        user = User(username="tester", email="tester@example.com", password_hash="hash", role="user")
        db.session.add(user)
        db.session.commit()
        yield application


def test_duckworth_bom_import(app):
    with app.app_context():
        user = User.query.first()
        project = Project(name="Duckworth import")
        db.session.add(project)
        db.session.flush()

        summary = import_document_path(DUCKWORTH_BOM, project=project, user_id=user.id)

        assert summary.bom is not None
        assert summary.bom.sheet_name == "BILL OF MATERIALS"
        assert summary.bom.rows_processed == 13
        assert summary.bom.materials_created == 39
        assert summary.bom.colorways_created == 3
        assert ProjectMaterial.query.count() == 39

        snap = ProjectMaterial.query.filter_by(name="Snap").first()
        assert snap is not None
        assert snap.supplier == "YKK"
        assert snap.supplier_contact == "DUCKWORTH"
        assert snap.import_source_file == DUCKWORTH_BOM.name
        assert snap.import_source_row == 14


def test_duckworth_project_details_and_measurements(app):
    with app.app_context():
        user = User.query.first()
        project = Project(name="Duckworth details")
        db.session.add(project)
        db.session.flush()

        summary = import_document_path(DUCKWORTH_BOM, project=project, user_id=user.id)

        assert project.style_no == "DW11038"
        assert project.customer == "DUCKWORTH"
        assert project.season == "FW26"
        assert project.po_no == "1654"
        assert summary.measurements is not None
        assert summary.measurements.sheet_name == "SPEC"
        assert summary.measurements.points_created == 205
        assert PointsMeasured.query.count() == 205


def test_does_not_overwrite_existing_project_fields(app):
    with app.app_context():
        details = extract_project_details_from_file(DUCKWORTH_BOM)
        project = Project(name="Existing", style_no="KEEP-ME", customer="Manual")
        updated = apply_project_details(project, details)
        assert "style_no" not in updated
        assert "customer" not in updated
        assert project.style_no == "KEEP-ME"
        assert project.season == "FW26"


def test_broken_spreadsheet_returns_clear_error(app, tmp_path):
    with app.app_context():
        user = User.query.first()
        project = Project(name="Broken")
        db.session.add(project)
        db.session.flush()

        bad_file = tmp_path / "broken.xlsx"
        bad_file.write_bytes(b"not an excel file")

        with pytest.raises(DocumentImportError) as exc_info:
            import_document_path(bad_file, project=project, user_id=user.id)

        assert "Excel" in exc_info.value.message or "corrupt" in exc_info.value.message.lower()
