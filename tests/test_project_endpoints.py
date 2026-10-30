from datetime import date

import pytest

from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial, User


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
        db.session.add(
            User(
                username="tester",
                email="tester@example.com",
                password_hash="hash",
                role="user",
            )
        )
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    test_client = app.test_client()
    with test_client.session_transaction() as session:
        session["_user_id"] = str(User.query.first().id)
        session["_fresh"] = True
    return test_client


def _complete_material(**overrides):
    values = {
        "name": "Shell",
        "material": "Cotton twill",
        "supplier": "Mill",
        "supplier_contact": "Contact",
        "location": "Body",
        "material_size": "60 in",
        "color": "Navy",
        "uom": "yd",
        "quantity": 2,
    }
    values.update(overrides)
    return values


def test_get_projects_returns_details_and_bom_completeness(client, app):
    with app.app_context():
        project = Project(
            name="Winter Jacket",
            status="blocked",
            style_no="ST-100",
            description="Insulated jacket",
            po_no="PO-42",
            project_date=date(2026, 10, 1),
        )
        colorway = ProjectColor(name="Navy", project=project)
        colorway.materials.extend(
            [
                ProjectMaterial(**_complete_material()),
                ProjectMaterial(**_complete_material(supplier=" ")),
                ProjectMaterial(**_complete_material(quantity=0)),
            ]
        )
        no_bom_project = Project(name="New project")
        db.session.add_all([project, no_bom_project])
        db.session.commit()
        project_id = project.id
        no_bom_project_id = no_bom_project.id

        response = client.get("/api/projects")

        assert response.status_code == 200
        projects = {row["id"]: row for row in response.get_json()["projects"]}
        assert set(projects) == {project_id, no_bom_project_id}
        listed = projects[project_id]
        assert listed["style_no"] == "ST-100"
        assert listed["description"] == "Insulated jacket"
        assert listed["style_description"] == "Insulated jacket"
        assert listed["stage"] == "blocked"
        assert listed["po_no"] == "PO-42"
        assert listed["project_date"] == "2026-10-01"
        assert listed["total_bom_lines"] == 3
        assert listed["missing_bom_items"] == 2
        assert listed["percent_complete"] == 33

        empty = projects[no_bom_project_id]
        assert empty["total_bom_lines"] == 0
        assert empty["missing_bom_items"] == 0
        assert empty["percent_complete"] == 0


def test_get_project_returns_overview_and_bom_completeness(client, app):
    with app.app_context():
        project = Project(
            name="Summer Shirt",
            status="in progress",
            style_no="SH-25",
            description="Linen shirt",
            po_no="PO-99",
            project_date=date(2026, 6, 15),
        )
        colorway = ProjectColor(name="White", project=project)
        colorway.materials.extend(
            [
                ProjectMaterial(**_complete_material()),
                ProjectMaterial(**_complete_material(location=None)),
            ]
        )
        db.session.add(project)
        db.session.commit()
        project_id = project.id

        response = client.get(f"/api/projects/{project_id}")

        assert response.status_code == 200
        payload = response.get_json()
        overview = payload["project"]
        assert overview["name"] == "Summer Shirt"
        assert overview["stage"] == "in progress"
        assert overview["style_no"] == "SH-25"
        assert overview["description"] == "Linen shirt"
        assert overview["po_no"] == "PO-99"
        assert overview["project_date"] == "2026-06-15"
        assert overview["total_bom_lines"] == 2
        assert overview["missing_bom_items"] == 1
        assert overview["percent_complete"] == 50
        assert len(payload["colorways"]) == 1
        assert payload["colorways"][0]["name"] == "White"
        assert len(payload["colorways"][0]["materials"]) == 2
        assert payload["files"] == []


def test_get_project_returns_not_found_for_unknown_project(client):
    response = client.get("/api/projects/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Project not found."}


def test_patch_project_updates_details_and_returns_current_completeness(client, app):
    with app.app_context():
        project = Project(name="Old name")
        colorway = ProjectColor(name="Black", project=project)
        colorway.materials.append(
            ProjectMaterial(**_complete_material(supplier=""))
        )
        db.session.add(project)
        db.session.commit()
        project_id = project.id

        response = client.patch(
            f"/api/projects/{project_id}",
            json={
                "name": "Updated name",
                "stage": "finished",
                "style_no": "ST-200",
                "project_date": "2026-10-30",
                "description": "Hand-updated project",
            },
        )

        assert response.status_code == 200
        payload = response.get_json()["project"]
        assert payload["name"] == "Updated name"
        assert payload["stage"] == "finished"
        assert payload["style_no"] == "ST-200"
        assert payload["project_date"] == "2026-10-30"
        assert payload["description"] == "Hand-updated project"
        assert payload["total_bom_lines"] == 1
        assert payload["missing_bom_items"] == 1
        assert payload["percent_complete"] == 0
        assert db.session.get(Project, project_id).name == "Updated name"


def test_patch_project_rejects_invalid_updates_without_saving(client, app):
    with app.app_context():
        project = Project(name="Original", status="in progress")
        db.session.add(project)
        db.session.commit()
        project_id = project.id

        for invalid_update in (
            {"name": "   "},
            {"status": "planning"},
            {"project_date": "10/30/2026"},
            {"name": 42},
            {"unknown": "value"},
        ):
            response = client.patch(
                f"/api/projects/{project_id}",
                json=invalid_update,
            )
            assert response.status_code == 400
            db.session.refresh(project)
            assert project.name == "Original"
            assert project.status == "in progress"


def test_patch_bom_line_recalculates_completeness(client, app):
    with app.app_context():
        project = Project(name="BOM edit")
        colorway = ProjectColor(name="Black", project=project)
        material = ProjectMaterial(
            colorway=colorway,
            **_complete_material(supplier=""),
        )
        db.session.add(project)
        db.session.add(material)
        db.session.commit()

        response = client.patch(
            f"/api/bom-lines/{material.id}",
            json={"supplier": "New Mill"},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["material"]["supplier"] == "New Mill"
        assert payload["total_bom_lines"] == 1
        assert payload["missing_bom_items"] == 0
        assert payload["percent_complete"] == 100
