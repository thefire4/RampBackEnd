import io
from pathlib import Path

import pytest

from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectFile, ProjectMaterial
from sample_bom import COLORWAYS, SAMPLE_LINES, SAMPLE_PROJECT, build_sample_bom

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'


@pytest.fixture
def uploaded(app, employee_client, tmp_path):
    """A project created by uploading the sample BOM, like a real user would."""
    path = build_sample_bom(tmp_path / "sample_bom.xlsx")
    res = employee_client.post(
        "/api/projects/import",
        data={"file": (io.BytesIO(path.read_bytes()), "sample_bom.xlsx"), "name": "Sample Jacket"},
        content_type="multipart/form-data",
    )
    return db.session.get(Project, res.get_json()["project_id"])


@pytest.fixture
def sketch(app, uploaded, employee):
    """A sketch file in the upload folder, attached to the project."""
    folder = Path(app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "front.svg").write_bytes(SVG)
    record = ProjectFile(project_id=uploaded.id, user_id=employee.id, file_name="front.svg",
                         file_path=str(folder / "front.svg"), file_type="image/svg+xml")
    db.session.add(record)
    db.session.commit()
    return record


def test_project_page_gets_everything_in_one_call(employee_client, uploaded, sketch):
    res = employee_client.get(f"/api/projects/{uploaded.id}")
    assert res.status_code == 200
    body = res.get_json()

    project = body["project"]
    assert project["name"] == "Sample Jacket"
    assert project["stage"] == "in progress"
    assert project["style_description"] == SAMPLE_PROJECT["description"]
    assert project["customer"] == SAMPLE_PROJECT["customer"]
    assert project["created_at"]

    assert [c["name"] for c in body["colorways"]] == COLORWAYS
    navy = body["colorways"][0]["materials"]
    assert [m["name"] for m in navy] == [line[0] for line in SAMPLE_LINES]
    shell = navy[0]
    assert (shell["material"], shell["supplier"], shell["quantity"], shell["uom"]) == ("100% cotton twill", "Acme Mills", 2, "yd")

    files = {f["file_name"]: f for f in body["files"]}
    assert set(files) == {"sample_bom.xlsx", "front.svg"}
    assert files["front.svg"]["url"] == f"/api/files/{sketch.id}"


def test_each_line_lists_the_fields_it_is_missing(employee_client, uploaded):
    body = employee_client.get(f"/api/projects/{uploaded.id}").get_json()
    flags = {m["name"]: m["missing_fields"] for m in body["colorways"][0]["materials"]}

    assert flags == {"Shell fabric": [], "Button": [], "Hang tag": ["supplier"]}
    # Same rule as the projects list: one flagged line per colorway
    assert body["missing_bom_items"] == len(COLORWAYS)


def test_zero_quantity_counts_as_missing(employee_client, uploaded):
    line = ProjectMaterial.query.join(ProjectColor).filter(
        ProjectColor.project_id == uploaded.id, ProjectMaterial.name == "Button").first()
    line.quantity = 0
    db.session.commit()

    materials = employee_client.get(f"/api/projects/{uploaded.id}").get_json()["colorways"][0]["materials"]
    button = next(m for m in materials if m["id"] == line.id)
    assert button["missing_fields"] == ["quantity"]


def test_project_with_no_bom_or_files(employee_client):
    project = Project(name="Blank")
    db.session.add(project)
    db.session.commit()

    body = employee_client.get(f"/api/projects/{project.id}").get_json()
    assert body["colorways"] == [] and body["files"] == [] and body["missing_bom_items"] == 0


def test_wrong_project_id_is_a_404(employee_client):
    res = employee_client.get("/api/projects/9999")
    assert res.status_code == 404
    assert res.get_json() == {"error": "Project not found."}


def test_sketch_loads_from_the_file_endpoint(employee_client, sketch):
    res = employee_client.get(f"/api/files/{sketch.id}")

    assert res.status_code == 200
    assert res.data == SVG
    assert res.mimetype == "image/svg+xml"
    assert "attachment" not in res.headers.get("Content-Disposition", "")
    assert "sandbox" in res.headers["Content-Security-Policy"]
    assert res.headers["X-Content-Type-Options"] == "nosniff"


def test_uploaded_bom_can_be_downloaded(employee_client, uploaded):
    record = ProjectFile.query.filter_by(project_id=uploaded.id, file_name="sample_bom.xlsx").one()
    res = employee_client.get(f"/api/files/{record.id}?download=1")

    assert res.status_code == 200
    assert res.data[:2] == b"PK"  # xlsx files are zip archives
    assert "spreadsheetml" in res.mimetype  # stored type was just "xlsx"
    assert "attachment" in res.headers["Content-Disposition"]


@pytest.mark.parametrize("file_path", ["gone.png", "../../secret.txt"])
def test_missing_or_outside_files_are_not_served(app, employee_client, uploaded, employee, tmp_path, file_path):
    (tmp_path / "secret.txt").write_text("not for you")
    record = ProjectFile(project_id=uploaded.id, user_id=employee.id, file_name="x", file_path=file_path)
    db.session.add(record)
    db.session.commit()

    res = employee_client.get(f"/api/files/{record.id}")
    assert res.status_code == 404
    assert res.get_json() == {"error": "This file is missing from storage."}


def test_unknown_file_is_a_404(employee_client):
    res = employee_client.get("/api/files/9999")
    assert res.status_code == 404
    assert res.get_json() == {"error": "File not found."}


def test_both_endpoints_need_login(app, uploaded, sketch):
    project_id, file_id = uploaded.id, sketch.id
    # A fresh app context, so nothing from the logged-in requests above carries over
    with app.app_context():
        anon = app.test_client()
        assert anon.get(f"/api/projects/{project_id}").status_code == 401
        assert anon.get(f"/api/files/{file_id}").status_code == 401