from pathlib import Path

import pytest

from src.api.extensions import db
from src.api.models import (
    PointsMeasured,
    Project,
    ProjectChangeLog,
    ProjectColor,
    ProjectFile,
    ProjectMaterial,
    User,
    ValueSource,
)


def test_archiving_and_restoring_filters_project_list(employee_client, app):
    with app.app_context():
        active = Project(name="Active")
        archived = Project(name="Archived", archived=True)
        db.session.add_all([active, archived])
        db.session.commit()
        active_id, archived_id = active.id, archived.id

    default_list = employee_client.get("/api/projects")
    assert default_list.status_code == 200
    assert {project["id"] for project in default_list.get_json()["projects"]} == {
        active_id
    }

    archived_list = employee_client.get(
        "/api/projects", query_string={"archived": "true"}
    )
    assert {project["id"] for project in archived_list.get_json()["projects"]} == {
        archived_id
    }

    archive_response = employee_client.post(f"/api/projects/{active_id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.get_json()["project"]["archived"] is True
    assert employee_client.get("/api/projects").get_json()["projects"] == []

    restore_response = employee_client.post(f"/api/projects/{active_id}/restore")
    assert restore_response.status_code == 200
    assert restore_response.get_json()["project"]["archived"] is False
    assert {
        project["id"]
        for project in employee_client.get("/api/projects").get_json()["projects"]
    } == {active_id}


@pytest.mark.parametrize("endpoint", ["project", "file"])
def test_project_deletion_endpoints_require_admin(
    employee_client, app, endpoint
):
    with app.app_context():
        project = Project(name="Protected")
        db.session.add(project)
        db.session.flush()
        project_file = ProjectFile(
            project_id=project.id,
            user_id=User.query.filter_by(username="employee").one().id,
            file_name="protected.pdf",
        )
        db.session.add(project_file)
        db.session.commit()
        path = (
            f"/api/projects/{project.id}"
            if endpoint == "project"
            else f"/api/projects/{project.id}/files/{project_file.id}"
        )

    response = employee_client.delete(path)
    assert response.status_code == 403


def test_admin_project_delete_removes_related_rows_and_stored_files(
    admin_client, admin, app
):
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_paths = [upload_dir / "source.pdf", upload_dir / "preview.png"]
    for path in stored_paths:
        path.write_bytes(b"stored")

    with app.app_context():
        db.session.execute(db.text(
            "CREATE TABLE tasks (id INTEGER PRIMARY KEY, project_id INTEGER)"
        ))
        db.session.execute(db.text(
            "CREATE TABLE comments (id INTEGER PRIMARY KEY, project_id INTEGER, file_id INTEGER)"
        ))
        db.session.execute(db.text(
            "CREATE TABLE project_users (project_id INTEGER, user_id INTEGER)"
        ))
        project = Project(name="Delete me")
        other_project = Project(name="Keep me")
        colorway = ProjectColor(name="Navy", project=project)
        material = ProjectMaterial(colorway=colorway, material="Cotton")
        measurement = PointsMeasured(project=project, code="A")
        db.session.add_all([project, other_project, material, measurement])
        db.session.flush()
        source_file = ProjectFile(
            project_id=project.id,
            user_id=admin.id,
            file_name="source.pdf",
            file_path=str(stored_paths[0]),
        )
        db.session.add(source_file)
        db.session.flush()
        preview_file = ProjectFile(
            project_id=project.id,
            user_id=admin.id,
            file_name="preview.png",
            file_path=str(stored_paths[1]),
            source_file_id=source_file.id,
        )
        keep_file = ProjectFile(
            project_id=other_project.id,
            user_id=admin.id,
            file_name="keep.pdf",
        )
        db.session.add_all([source_file, preview_file, keep_file])
        db.session.flush()
        project_id = project.id
        keep_file_id = keep_file.id
        db.session.add_all([
            ValueSource(
                project_id=project.id,
                entity_type="project",
                entity_id=project.id,
                field="name",
                kind="file",
                file_id=source_file.id,
            ),
            ValueSource(
                project_id=project.id,
                entity_type="project",
                entity_id=project.id,
                field="description",
                kind="file",
                file_id=preview_file.id,
            ),
            ProjectChangeLog(
                project_id=project.id,
                user_id=admin.id,
                action="updated",
                entity_type="project",
            ),
        ])
        db.session.execute(
            db.text("INSERT INTO tasks (project_id) VALUES (:project_id)"),
            {"project_id": project.id},
        )
        db.session.execute(
            db.text(
                "INSERT INTO comments (project_id, file_id) "
                "VALUES (:project_id, :file_id)"
            ),
            {"project_id": project.id, "file_id": source_file.id},
        )
        db.session.execute(
            db.text(
                "INSERT INTO project_users (project_id, user_id) "
                "VALUES (:project_id, :user_id)"
            ),
            {"project_id": project.id, "user_id": admin.id},
        )
        db.session.commit()

    response = admin_client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.get_json() == {"deleted": True, "id": project_id}
    assert all(not path.exists() for path in stored_paths)

    with app.app_context():
        assert db.session.get(Project, project_id) is None
        assert ProjectColor.query.filter_by(project_id=project_id).count() == 0
        assert ProjectMaterial.query.count() == 0
        assert PointsMeasured.query.filter_by(project_id=project_id).count() == 0
        assert ProjectFile.query.count() == 1
        assert db.session.get(ProjectFile, keep_file_id) is not None
        assert ValueSource.query.filter_by(project_id=project_id).count() == 0
        assert ProjectChangeLog.query.filter_by(project_id=project_id).count() == 0
        for table_name in ("tasks", "comments", "project_users"):
            assert db.session.execute(
                db.text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar_one() == 0


def test_admin_file_delete_removes_file_and_file_sources(
    admin_client, admin, app
):
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / "remove.pdf"
    stored_path.write_bytes(b"stored")

    with app.app_context():
        db.session.execute(db.text(
            "CREATE TABLE comments (id INTEGER PRIMARY KEY, project_id INTEGER, file_id INTEGER)"
        ))
        project = Project(name="Keep project")
        db.session.add(project)
        db.session.flush()
        project_file = ProjectFile(
            project_id=project.id,
            user_id=admin.id,
            file_name="remove.pdf",
            file_path=str(stored_path),
        )
        db.session.add(project_file)
        db.session.flush()
        file_id, project_id = project_file.id, project.id
        db.session.add(ValueSource(
            project_id=project.id,
            entity_type="project",
            entity_id=project.id,
            field="name",
            kind="file",
            file_id=file_id,
        ))
        db.session.execute(
            db.text(
                "INSERT INTO comments (project_id, file_id) "
                "VALUES (:project_id, :file_id)"
            ),
            {"project_id": project_id, "file_id": file_id},
        )
        db.session.commit()

    response = admin_client.delete(
        f"/api/projects/{project_id}/files/{file_id}"
    )
    assert response.status_code == 200
    assert response.get_json() == {"deleted": True, "id": file_id}
    assert not stored_path.exists()

    with app.app_context():
        assert db.session.get(Project, project_id) is not None
        assert db.session.get(ProjectFile, file_id) is None
        assert ValueSource.query.filter_by(file_id=file_id).count() == 0
        assert db.session.execute(
            db.text("SELECT file_id FROM comments")
        ).scalar_one() is None
