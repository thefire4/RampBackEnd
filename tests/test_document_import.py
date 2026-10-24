from __future__ import annotations

from pathlib import Path

import pytest

from src.api.extensions import db
from src.api.models import PointsMeasured, Project, ProjectColor, ProjectMaterial, User
from src.api.routes.projects import MISSING_BOM_ITEM, _summary_payload
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
        expected_missing = (
            db.session.query(ProjectMaterial.id)
            .join(ProjectColor)
            .filter(ProjectColor.project_id == project.id, MISSING_BOM_ITEM)
            .count()
        )
        assert _summary_payload(summary)["missing_bom_items"] == expected_missing


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


def test_project_missing_bom_count_checks_required_material_fields(app):
    with app.app_context():
        project = Project(name="BOM completeness")
        db.session.add(project)
        db.session.flush()
        colorway = ProjectColor(name="Black", project_id=project.id)
        db.session.add(colorway)
        db.session.flush()

        complete_fields = {
            "material": "100% cotton",
            "supplier": "Mill",
            "supplier_contact": "Contact",
            "location": "Front panel",
            "material_size": "60 in",
            "color": "Black",
            "uom": "yd",
            "quantity": 2,
        }
        db.session.add(ProjectMaterial(colorway_id=colorway.id, **complete_fields))
        for field, value in (
            ("material", ""),
            ("supplier", ""),
            ("supplier_contact", ""),
            ("location", ""),
            ("material_size", ""),
            ("color", ""),
            ("uom", ""),
            ("quantity", 0),
        ):
            db.session.add(
                ProjectMaterial(
                    colorway_id=colorway.id,
                    **{**complete_fields, field: value},
                )
            )
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(User.query.first().id)
            session["_fresh"] = True

        response = client.get("/api/projects")
        assert response.status_code == 200
        payload = response.get_json()
        project_payload = next(row for row in payload["projects"] if row["id"] == project.id)
        assert project_payload["missing_bom_items"] == 8


def test_editing_bom_line_rechecks_project_missing_count(app):
    with app.app_context():
        project = Project(name="BOM edit check")
        colorway = ProjectColor(name="Black", project=project)
        material = ProjectMaterial(
            colorway=colorway,
            name="Shell",
            material="Cotton",
            supplier="Mill",
            supplier_contact="Contact",
            quantity=2,
            location="Body",
            material_size="60 in",
            uom="yd",
            color="Black",
        )
        db.session.add(project)
        db.session.add(material)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(User.query.first().id)
            session["_fresh"] = True

        response = client.patch(
            f"/api/materials/{material.id}",
            json={"supplier": ""},
        )
        assert response.status_code == 200
        assert response.get_json()["missing_bom_items"] == 1

        response = client.patch(
            f"/api/materials/{material.id}",
            json={"supplier": "Mill"},
        )
        assert response.status_code == 200
        assert response.get_json()["missing_bom_items"] == 0


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
