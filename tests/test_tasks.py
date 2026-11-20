import io

from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial, Task, User


def test_project_tasks_can_be_created_listed_and_updated(employee_client, app):
    with app.app_context():
        project = Project(name="Task project")
        colorway = ProjectColor(name="Navy", project=project)
        material = ProjectMaterial(
            colorway=colorway,
            name="Shell",
            material="Cotton",
        )
        db.session.add_all([project, material])
        owner = User(
            username="task-owner",
            email="task-owner@example.com",
            password_hash="hash",
        )
        db.session.add(owner)
        db.session.commit()
        project_id, material_id, owner_id = project.id, material.id, owner.id

    created = employee_client.post(
        f"/api/projects/{project_id}/tasks",
        json={"bom_line_id": material_id},
    )
    assert created.status_code == 201
    task = created.get_json()["task"]
    assert task["project_id"] == project_id
    assert task["bom_line_id"] == material_id
    assert task["status"] == "open"
    assert "supplier" in task["missing_fields"]
    assert task["owner_id"] is None
    assert task["due_date"] is None
    assert task["created_at"]
    assert task["updated_at"]

    updated = employee_client.patch(
        f"/api/tasks/{task['id']}",
        json={
            "owner_id": owner_id,
            "status": "in progress",
            "due_date": "2026-12-01",
        },
    )
    assert updated.status_code == 200
    updated_task = updated.get_json()["task"]
    assert updated_task["owner_id"] == owner_id
    assert updated_task["owner"] == "task-owner"
    assert updated_task["status"] == "in progress"
    assert updated_task["due_date"] == "2026-12-01"

    listed = employee_client.get(f"/api/projects/{project_id}/tasks")
    assert listed.status_code == 200
    assert listed.get_json()["tasks"] == [updated_task]


def test_tasks_are_created_after_upload_and_closed_when_bom_line_is_completed(
    employee_client, app
):
    content = (
        "Item,Product Description,Vendor,Size,Quantity,Color\n"
        "Shell,Cotton,Mill,60 in,2,\n"
    )
    uploaded = employee_client.post(
        "/api/projects/import",
        data={"file": (io.BytesIO(content.encode()), "incomplete.csv")},
    )
    assert uploaded.status_code == 201, uploaded.get_json()
    project_id = uploaded.get_json()["project_id"]

    details = employee_client.get(f"/api/projects/{project_id}")
    assert details.status_code == 200
    material = details.get_json()["colorways"][0]["materials"][0]
    material_id = material["id"]
    assert material["missing_fields"]

    tasks_response = employee_client.get(f"/api/projects/{project_id}/tasks")
    assert tasks_response.status_code == 200
    tasks = tasks_response.get_json()["tasks"]
    assert len(tasks) == 1
    task = tasks[0]
    assert task["bom_line_id"] == material_id
    assert task["status"] == "open"
    assert task["missing_fields"] == material["missing_fields"]

    patched = employee_client.patch(
        f"/api/bom-lines/{material_id}",
        json={
            "material": "Cotton",
            "supplier": "Mill",
            "supplier_contact": "Mill contact",
            "location": "Body",
            "material_size": "60 in",
            "uom": "60 in",
            "color": "Navy",
            "quantity": 2,
        },
    )
    assert patched.status_code == 200
    refreshed = employee_client.get(f"/api/projects/{project_id}/tasks")
    task_after_completion = refreshed.get_json()["tasks"][0]
    assert task_after_completion["id"] == task["id"]
    assert task_after_completion["status"] == "done"
    assert task_after_completion["missing_fields"] == []


def test_task_patch_validates_status_owner_and_due_date(employee_client, app):
    with app.app_context():
        project = Project(name="Task validation")
        colorway = ProjectColor(name="Navy", project=project)
        material = ProjectMaterial(colorway=colorway, material="Cotton")
        db.session.add_all([project, material])
        db.session.flush()
        task = Task(
            project_id=project.id,
            bom_line_id=material.id,
            missing_fields=["supplier"],
        )
        db.session.add(task)
        db.session.commit()
        task_id, project_id = task.id, project.id

    for invalid_change in (
        {"status": "closed"},
        {"owner_id": True},
        {"owner_id": 9999},
        {"due_date": "12/01/2026"},
        {"unknown": "value"},
    ):
        response = employee_client.patch(
            f"/api/tasks/{task_id}", json=invalid_change
        )
        assert response.status_code in {400, 404}

    assert employee_client.get(
        f"/api/projects/{project_id}/tasks"
    ).get_json()["tasks"][0]["status"] == "open"
