from __future__ import annotations

import pytest

from src.api.extensions import db
from src.api.models import (
    PointsMeasured,
    Project,
    ProjectChangeLog,
    ProjectColor,
    ProjectMaterial,
    User,
)
from src.api.routes.projects import MATERIAL_FIELDS, MISSING_BOM_ITEM, _summary_payload
from src.api.services.document_import import import_document_path
from src.api.services.import_errors import DocumentImportError
from src.api.services.tech_pack_import import apply_project_details, extract_project_details_from_file

from sample_bom import COLORWAYS, SAMPLE_LINES, SAMPLE_MEASUREMENTS, SAMPLE_PROJECT, SIZES, build_sample_bom


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
        user = User(username="tester", email="tester@example.com", password_hash="hash", role="employee")
        db.session.add(user)
        db.session.commit()
        yield application


@pytest.fixture
def sample_bom(tmp_path):
    #Mock data created since ticket states no real data to be used. 
    return build_sample_bom(tmp_path / "sample_bom.xlsx")


def test_sample_bom_import(app, sample_bom):
    with app.app_context():
        user = User.query.first()
        project = Project(name="Sample import")
        db.session.add(project)
        db.session.flush()

        summary = import_document_path(sample_bom, project=project, user_id=user.id)

        assert summary.bom is not None
        assert summary.bom.sheet_name == "BILL OF MATERIALS"
        assert summary.bom.rows_processed == len(SAMPLE_LINES)
        assert summary.bom.materials_created == len(SAMPLE_LINES) * len(COLORWAYS)
        assert summary.bom.colorways_created == len(COLORWAYS)
        assert ProjectMaterial.query.count() == len(SAMPLE_LINES) * len(COLORWAYS)

        button = ProjectMaterial.query.filter_by(name="Button").first()
        assert button is not None
        assert button.supplier == "Button Co"
        assert button.supplier_contact == "Jane Doe"
        assert button.import_source_file == sample_bom.name
        assert button.import_source_row == 11
        expected_missing = (
            db.session.query(ProjectMaterial.id)
            .join(ProjectColor)
            .filter(ProjectColor.project_id == project.id, MISSING_BOM_ITEM)
            .count()
        )
        assert _summary_payload(summary)["missing_bom_items"] == expected_missing


def test_sample_project_details_and_measurements(app, sample_bom):
    with app.app_context():
        user = User.query.first()
        project = Project(name="Sample details")
        db.session.add(project)
        db.session.flush()

        summary = import_document_path(sample_bom, project=project, user_id=user.id)

        assert project.style_no == SAMPLE_PROJECT["style_no"]
        assert project.customer == SAMPLE_PROJECT["customer"]
        assert project.season == SAMPLE_PROJECT["season"]
        assert project.po_no == SAMPLE_PROJECT["po_no"]
        assert summary.measurements is not None
        assert summary.measurements.sheet_name == "SPEC"
        expected_points = len(SAMPLE_MEASUREMENTS) * len(SIZES)
        assert summary.measurements.points_created == expected_points
        assert PointsMeasured.query.count() == expected_points

        front_m = PointsMeasured.query.filter_by(code="A", sizes="M").one()
        assert (front_m.name, front_m.measure, front_m.tol) == ("Front length", "29 1/2", "1/2")


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


def test_bom_line_patch_rechecks_and_logs_field_changes(app):
    with app.app_context():
        project = Project(name="BOM edit check")
        colorway = ProjectColor(name="Black", project=project)
        material = ProjectMaterial(
            colorway=colorway,
            name="Shell",
            material="Cotton",
            supplier="Mill",
            supplier_contact="Contact",
            quantity=0,
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

        response = client.patch(f"/api/bom-lines/{material.id}", json={"supplier": "   "})
        assert response.status_code == 400
        assert ProjectChangeLog.query.count() == 0
        assert material.supplier == "Mill"

        response = client.patch(
            f"/api/bom-lines/{material.id}",
            json={"quantity": 2.5, "supplier": "New Mill"},
        )
        assert response.status_code == 200
        assert response.get_json()["missing_bom_items"] == 0

        entries = ProjectChangeLog.query.filter_by(action="updated").all()
        assert {(entry.field_name, entry.old_value, entry.new_value) for entry in entries} == {
            ("quantity", "0.0", "2.5"),
            ("supplier", "Mill", "New Mill"),
        }
        assert all(entry.user_id == User.query.first().id for entry in entries)
        assert all(entry.changed_at is not None for entry in entries)

        response = client.patch(f"/api/bom-lines/{material.id}", json={"quantity": 0})
        assert response.status_code == 200
        assert response.get_json()["missing_bom_items"] == 1


def test_create_and_delete_bom_line_are_logged_and_recheck_missing_info(app):
    with app.app_context():
        project = Project(name="BOM create delete")
        colorway = ProjectColor(name="Navy", project=project)
        db.session.add(project)
        db.session.add(colorway)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(User.query.first().id)
            session["_fresh"] = True

        response = client.post(
            f"/api/projects/{project.id}/bom-lines",
            json={
                "colorway_id": colorway.id,
                "name": "Shell",
                "material": "Cotton twill",
            },
        )
        assert response.status_code == 201
        result = response.get_json()
        line_id = result["material"]["id"]
        assert result["missing_bom_items"] == 1
        assert ProjectChangeLog.query.filter_by(
            action="created",
            entity_id=line_id,
        ).count() == len(MATERIAL_FIELDS)

        response = client.get(f"/api/projects/{project.id}/history")
        assert response.status_code == 200
        history = response.get_json()["history"]
        assert history[0]["username"] == "tester"
        assert history[0]["action"] == "created"
        assert history[0]["field_name"] in MATERIAL_FIELDS
        assert history[0]["changed_at"]

        response = client.patch(
            f"/api/bom-lines/{line_id}",
            json={
                "supplier": "Mill",
                "supplier_contact": "Contact",
                "quantity": 12.5,
                "location": "Body",
                "material_size": "60 in",
                "uom": "yd",
                "color": "Navy",
            },
        )
        assert response.status_code == 200
        assert response.get_json()["missing_bom_items"] == 0

        response = client.delete(f"/api/bom-lines/{line_id}")
        assert response.status_code == 200
        assert response.get_json()["missing_bom_items"] == 0
        deleted = ProjectChangeLog.query.filter_by(
            action="deleted",
            entity_id=line_id,
        ).all()
        assert deleted
        assert all(entry.old_value is not None and entry.new_value is None for entry in deleted)


def test_bom_line_endpoints_reject_invalid_values(app):
    with app.app_context():
        project = Project(name="BOM validation")
        colorway = ProjectColor(name="Black", project=project)
        material = ProjectMaterial(colorway=colorway, material="Cotton", quantity=1)
        db.session.add_all([project, material])
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(User.query.first().id)
            session["_fresh"] = True

        for invalid_quantity in (-1, 1.2e309, "3", True):
            response = client.patch(
                f"/api/bom-lines/{material.id}",
                json={"quantity": invalid_quantity},
            )
            assert response.status_code == 400
            assert "Quantity" in response.get_json()["error"]

        response = client.post(
            f"/api/projects/{project.id}/bom-lines",
            json={"colorway_id": colorway.id, "material": "   "},
        )
        assert response.status_code == 400
        assert "Material cannot be blank" in response.get_json()["error"]
        assert ProjectMaterial.query.count() == 1
        assert ProjectChangeLog.query.count() == 0


def test_does_not_overwrite_existing_project_fields(app, sample_bom):
    with app.app_context():
        details = extract_project_details_from_file(sample_bom)
        project = Project(name="Existing", style_no="KEEP-ME", customer="Manual")
        updated = apply_project_details(project, details)
        assert "style_no" not in updated
        assert "customer" not in updated
        assert project.style_no == "KEEP-ME"
        assert project.season == SAMPLE_PROJECT["season"]


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