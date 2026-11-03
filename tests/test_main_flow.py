import io
from pathlib import Path

import pytest

from src.api.extensions import db
from src.api.models import Project, ProjectChangeLog, ProjectColor, ProjectFile, ProjectMaterial
from sample_bom import COLORWAYS, SAMPLE_LINES, SAMPLE_PROJECT, build_sample_bom


@pytest.fixture
def sample_bom(tmp_path):
    return build_sample_bom(tmp_path / "sample_bom.xlsx")


def upload(client, path, url="/api/projects/import", **form):
    data = {**form, "file": (io.BytesIO(Path(path).read_bytes()), Path(path).name)}
    return client.post(url, data=data, content_type="multipart/form-data")


# ---------- creating a project ----------

def test_creating_a_project_saves_it_to_the_database(employee_client):
    res = employee_client.post("/api/projects", json={"name": "  Sample Jacket  "})

    assert res.status_code == 201
    body = res.get_json()["project"]
    assert body["name"] == "Sample Jacket"
    assert body["status"] == "in progress"
    assert db.session.get(Project, body["id"]).name == "Sample Jacket"


def test_a_project_needs_a_name(employee_client):
    assert employee_client.post("/api/projects", json={"name": "   "}).status_code == 400
    assert Project.query.count() == 0


def test_creating_a_project_needs_login(app):
    assert app.test_client().post("/api/projects", json={"name": "X"}).status_code == 401
    assert Project.query.count() == 0


# ---------- uploading a BOM ----------

def test_uploading_a_sample_bom_saves_project_details_and_bom_lines(employee_client, employee, sample_bom):
    res = upload(employee_client, sample_bom, name="Sample Jacket")

    assert res.status_code == 201
    body = res.get_json()
    assert body["bom"]["sheet_name"] == "BILL OF MATERIALS"
    assert body["bom"]["rows_processed"] == len(SAMPLE_LINES)
    assert body["bom"]["colorways_created"] == len(COLORWAYS)
    assert body["bom"]["materials_created"] == len(SAMPLE_LINES) * len(COLORWAYS)

    # Project details read from the top of the sheet
    project = db.session.get(Project, body["project_id"])
    assert project.name == "Sample Jacket"
    for field, expected in SAMPLE_PROJECT.items():
        assert getattr(project, field) == expected, field
    assert str(project.project_date) == "2026-01-15"

    # One colorway per colorway column, one line per part per colorway
    assert sorted(c.name for c in project.colorways) == sorted(COLORWAYS)
    navy = ProjectColor.query.filter_by(project_id=project.id, name="NAVY").one()
    lines = {m.name: m for m in navy.materials}
    assert set(lines) == {line[0] for line in SAMPLE_LINES}

    shell = lines["Shell fabric"]
    assert (shell.material, shell.supplier, shell.supplier_contact) == ("100% cotton twill", "Acme Mills", "Jane Doe")
    assert (shell.location, shell.article_no, shell.material_size) == ("Body", "TW-100", "58 in")
    assert (shell.quantity, shell.uom, shell.color) == (2, "yd", "NAVY")
    assert shell.import_source_file == "sample_bom.xlsx"

    stone_button = ProjectMaterial.query.join(ProjectColor).filter(
        ProjectColor.name == "STONE", ProjectMaterial.name == "Button").one()
    assert stone_button.color == "Stone horn"

    # The uploaded file is recorded and kept on disk
    [record] = ProjectFile.query.filter_by(project_id=project.id).all()
    assert record.file_name == "sample_bom.xlsx"
    assert record.user_id == employee.id
    assert Path(record.file_path).is_file()


def test_project_name_defaults_to_the_file_name(employee_client, sample_bom):
    body = upload(employee_client, sample_bom).get_json()
    assert db.session.get(Project, body["project_id"]).name == "sample_bom"


def test_uploading_more_files_adds_to_an_existing_project(employee_client, sample_bom):
    project_id = upload(employee_client, sample_bom).get_json()["project_id"]

    res = upload(employee_client, sample_bom, url=f"/api/projects/{project_id}/import")
    assert res.status_code == 200
    assert ProjectFile.query.filter_by(project_id=project_id).count() == 2


@pytest.mark.parametrize("filename, content, status", [
    ("notes.txt", b"hello", 415),
    ("broken.xlsx", b"not really excel", 400),
])
def test_bad_uploads_get_a_clear_error_and_create_nothing(employee_client, tmp_path, filename, content, status):
    bad = tmp_path / filename
    bad.write_bytes(content)

    res = upload(employee_client, bad)
    assert res.status_code == status
    assert res.get_json()["error"]
    assert Project.query.count() == 0


def test_upload_without_a_file_is_rejected(employee_client):
    res = employee_client.post("/api/projects/import", data={"name": "X"}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert Project.query.count() == 0


# ---------- missing info and the change log ----------

def test_missing_bom_fields_are_flagged_after_upload(employee_client, sample_bom):
    body = upload(employee_client, sample_bom).get_json()

    # Only the hang tag has a gap (no supplier), once per colorway
    assert body["missing_bom_items"] == len(COLORWAYS)
    listed = {p["id"]: p for p in employee_client.get("/api/projects").get_json()["projects"]}
    assert listed[body["project_id"]]["missing_bom_items"] == len(COLORWAYS)


def test_fixing_a_line_clears_the_flag_and_is_recorded_in_the_change_log(employee_client, employee, sample_bom):
    project_id = upload(employee_client, sample_bom).get_json()["project_id"]
    hang_tag = ProjectMaterial.query.join(ProjectColor).filter(
        ProjectColor.project_id == project_id,
        ProjectColor.name == "NAVY",
        ProjectMaterial.name == "Hang tag",
    ).one()

    res = employee_client.patch(f"/api/bom-lines/{hang_tag.id}", json={"supplier": "Tag Printers"})

    assert res.status_code == 200
    assert res.get_json()["material"]["supplier"] == "Tag Printers"
    assert res.get_json()["missing_bom_items"] == len(COLORWAYS) - 1
    db.session.refresh(hang_tag)
    assert hang_tag.supplier == "Tag Printers"

    [entry] = ProjectChangeLog.query.filter_by(action="updated", entity_id=hang_tag.id).all()
    assert (entry.field_name, entry.old_value, entry.new_value) == ("supplier", None, "Tag Printers")
    assert entry.user_id == employee.id
    assert entry.project_id == project_id

    history = employee_client.get(f"/api/projects/{project_id}/history").get_json()["history"]
    assert history[0]["username"] == "employee"
    assert history[0]["new_value"] == "Tag Printers"


def test_bad_edits_are_rejected_and_not_logged(employee_client, sample_bom):
    project_id = upload(employee_client, sample_bom).get_json()["project_id"]
    line = ProjectMaterial.query.join(ProjectColor).filter(ProjectColor.project_id == project_id).first()

    for bad in ({"quantity": -1}, {"quantity": "lots"}, {"supplier": "   "}):
        res = employee_client.patch(f"/api/bom-lines/{line.id}", json=bad)
        assert res.status_code == 400
        assert res.get_json()["error"]
    assert ProjectChangeLog.query.filter_by(action="updated").count() == 0