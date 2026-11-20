from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial, Vendor


def test_vendor_list_create_and_get(employee_client, app):
    with app.app_context():
        db.session.add(Vendor(name="Zulu"))
        db.session.commit()

    created = employee_client.post(
        "/api/vendors",
        json={
            "name": "Acme Mills",
            "contact_name": "Avery Smith",
            "email": "avery@example.com",
            "phone": "555-0100",
            "notes": "Preferred supplier",
        },
    )
    assert created.status_code == 201
    vendor = created.get_json()["vendor"]
    assert vendor == {
        "id": vendor["id"],
        "name": "Acme Mills",
        "contact_name": "Avery Smith",
        "email": "avery@example.com",
        "phone": "555-0100",
        "notes": "Preferred supplier",
    }

    listed = employee_client.get("/api/vendors")
    assert listed.status_code == 200
    assert [row["name"] for row in listed.get_json()["vendors"]] == [
        "Acme Mills",
        "Zulu",
    ]

    fetched = employee_client.get(f"/api/vendors/{vendor['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json()["vendor"] == vendor


def test_vendor_create_requires_valid_name(employee_client):
    for payload in ({}, {"name": "  "}, {"name": 42}, {"name": "A", "other": 1}):
        response = employee_client.post("/api/vendors", json=payload)
        assert response.status_code == 400


def test_vendor_edit_updates_supplied_fields(employee_client, app):
    with app.app_context():
        vendor = Vendor(
            name="Old Name",
            contact_name="Old Contact",
            email="old@example.com",
            phone="555-0000",
            notes="Old notes",
        )
        db.session.add(vendor)
        db.session.commit()
        vendor_id = vendor.id

    response = employee_client.patch(
        f"/api/vendors/{vendor_id}",
        json={"name": "New Name", "phone": None},
    )

    assert response.status_code == 200
    assert response.get_json()["vendor"] == {
        "id": vendor_id,
        "name": "New Name",
        "contact_name": "Old Contact",
        "email": "old@example.com",
        "phone": None,
        "notes": "Old notes",
    }


def test_vendor_delete_detaches_bom_lines_and_keeps_supplier_text(
    employee_client, app
):
    with app.app_context():
        vendor = Vendor(name="Supplier")
        project = Project(name="Jacket")
        colorway = ProjectColor(name="Navy", project=project)
        material = ProjectMaterial(
            colorway=colorway,
            vendor=vendor,
            supplier="Legacy supplier text",
        )
        db.session.add_all([vendor, project, material])
        db.session.commit()
        vendor_id, material_id = vendor.id, material.id

    response = employee_client.delete(f"/api/vendors/{vendor_id}")

    assert response.status_code == 200
    assert response.get_json() == {"deleted": True, "id": vendor_id}
    with app.app_context():
        assert db.session.get(Vendor, vendor_id) is None
        line = db.session.get(ProjectMaterial, material_id)
        assert line.vendor_id is None
        assert line.supplier == "Legacy supplier text"


def test_vendor_bom_lines_lists_links_created_and_updated_through_api(
    employee_client, app
):
    with app.app_context():
        vendor = Vendor(name="Mill")
        project = Project(name="Jacket")
        colorway = ProjectColor(name="Navy", project=project)
        db.session.add_all([vendor, project])
        db.session.commit()
        vendor_id, project_id, colorway_id = vendor.id, project.id, colorway.id

    created = employee_client.post(
        f"/api/projects/{project_id}/bom-lines",
        json={
            "colorway_id": colorway_id,
            "vendor_id": vendor_id,
            "supplier": "Legacy supplier text",
            "material": "Cotton",
        },
    )
    assert created.status_code == 201
    material = created.get_json()["material"]
    material_id = material["id"]
    assert material["vendor_id"] == vendor_id
    assert material["supplier"] == "Legacy supplier text"

    response = employee_client.get(f"/api/vendors/{vendor_id}/bom-lines")
    assert response.status_code == 200
    lines = response.get_json()["bom_lines"]
    assert len(lines) == 1
    assert lines[0]["id"] == material_id
    assert lines[0]["vendor_id"] == vendor_id
    assert lines[0]["supplier"] == "Legacy supplier text"
    assert lines[0]["project_name"] == "Jacket"
    assert lines[0]["colorway_name"] == "Navy"

    updated = employee_client.patch(
        f"/api/bom-lines/{material_id}",
        json={"vendor_id": None},
    )
    assert updated.status_code == 200
    assert updated.get_json()["material"]["vendor_id"] is None
    assert updated.get_json()["material"]["supplier"] == "Legacy supplier text"
    assert employee_client.get(
        f"/api/vendors/{vendor_id}/bom-lines"
    ).get_json()["bom_lines"] == []


def test_bom_line_rejects_nonexistent_vendor(employee_client, app):
    with app.app_context():
        project = Project(name="Jacket")
        colorway = ProjectColor(name="Navy", project=project)
        db.session.add(project)
        db.session.commit()
        project_id, colorway_id = project.id, colorway.id

    response = employee_client.post(
        f"/api/projects/{project_id}/bom-lines",
        json={"colorway_id": colorway_id, "vendor_id": 9999},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Vendor not found."}
