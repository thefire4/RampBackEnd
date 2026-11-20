from datetime import date

import pytest

from src.api.extensions import db
from src.api.models import Project, ProjectColor, ProjectMaterial, ProjectChangeLog, ValueSource

FIELDS = ('supplied_by', 'required_arrival', 'sourcing_status', 'approvals_needed')
VALUES = {'supplied_by': 'Factory A', 'required_arrival': '2027-02-20',
          'sourcing_status': 'awaiting', 'approvals_needed': 'Lab dip and bulk sample approval'}


@pytest.fixture
def part(app):
    project = Project(name='Sourcing test')
    colorway = ProjectColor(project=project, name='Blue')
    material = ProjectMaterial(colorway=colorway, name='Shell', material='Cotton', supplier='Mill',
        supplier_contact='Jane', quantity=2, location='Body', material_size='58 in', uom='yd', color='Blue')
    db.session.add(project)
    db.session.commit()
    return project.id, colorway.id, material.id


def endpoint(kind, part):
    project_id, _, material_id = part
    return {'bom': f'/api/bom-lines/{material_id}', 'alias': f'/api/materials/{material_id}',
            'project': f'/api/projects/{project_id}/materials/{material_id}'}[kind]


@pytest.mark.parametrize('kind', ['bom', 'alias', 'project'])
@pytest.mark.parametrize('status', ['awaiting', 'delayed', 'in stock'])
def test_sourcing_is_saved_returned_and_audited(employee_client, part, kind, status):
    values = {**VALUES, 'sourcing_status': status}
    response = employee_client.patch(endpoint(kind, part), json=values)
    assert response.status_code == 200, response.json
    if kind != 'project':
        assert {field: response.json['material'][field] for field in FIELDS} == values
    db.session.remove()
    saved = db.session.get(ProjectMaterial, part[2])
    assert saved.required_arrival == date(2027, 2, 20)
    assert saved.supplied_by == 'Factory A'
    assert saved.sourcing_status == status
    assert saved.approvals_needed == VALUES['approvals_needed']
    detail = employee_client.get(f'/api/projects/{part[0]}/materials/{part[2]}').json['material']
    assert {f: detail[f] for f in FIELDS} == values
    project = employee_client.get(f'/api/projects/{part[0]}').json
    assert {f: project['colorways'][0]['materials'][0][f] for f in FIELDS} == values
    nested = project['project']['materials'][0]['fields']
    assert {f: nested[f]['value'] for f in FIELDS} == values
    assert all(nested[f]['source']['kind'] == 'manual' for f in FIELDS)
    assert project['missing_bom_items'] == 0
    logs = ProjectChangeLog.query.filter_by(entity_id=part[2], action='updated').all()
    assert {log.field_name for log in logs} == set(FIELDS)
    assert all(log.user_id is not None and log.changed_at is not None for log in logs)


@pytest.mark.parametrize('kind', ['bom', 'project'])
def test_text_and_nulls_round_trip(employee_client, part, kind):
    assert employee_client.patch(endpoint(kind, part), json=VALUES).status_code == 200
    assert employee_client.patch(endpoint(kind, part), json={'approvals_needed': 'Customer sign-off'}).status_code == 200
    db.session.expire_all()
    assert db.session.get(ProjectMaterial, part[2]).approvals_needed == 'Customer sign-off'
    response = employee_client.patch(endpoint(kind, part), json={f: None for f in FIELDS})
    assert response.status_code == 200
    saved = db.session.get(ProjectMaterial, part[2])
    assert all(getattr(saved, f) is None for f in FIELDS)
    detail = employee_client.get(f'/api/projects/{part[0]}/materials/{part[2]}').json['material']
    assert all(detail[f] is None for f in FIELDS)


@pytest.mark.parametrize(('field', 'value'), [
    ('supplied_by', 5), ('supplied_by', True), ('supplied_by', 'x' * 256),
    ('required_arrival', '2027-02-30'), ('required_arrival', '02/20/2027'),
    ('required_arrival', '20270220'), ('required_arrival', '2027-02-20T10:00:00'),
    ('required_arrival', 20270220), ('required_arrival', True),
    ('sourcing_status', 'ordered'), ('sourcing_status', 'AWAITING'),
    ('sourcing_status', ['awaiting']), ('sourcing_status', 1),
    ('approvals_needed', True), ('approvals_needed', False), ('approvals_needed', 1), ('approvals_needed', 0),
    ('approvals_needed', []), ('approvals_needed', 'x' * 1001),
])
@pytest.mark.parametrize('kind', ['bom', 'project'])
def test_invalid_sourcing_rejected_without_partial_update(employee_client, part, kind, field, value):
    response = employee_client.patch(endpoint(kind, part), json={'notes': 'Should not save', field: value})
    assert response.status_code == 400, response.json
    db.session.expire_all()
    saved = db.session.get(ProjectMaterial, part[2])
    assert saved.notes is None
    assert all(getattr(saved, f) is None for f in FIELDS)
    assert ProjectChangeLog.query.count() == 0
    assert ValueSource.query.count() == 0


def test_new_line_accepts_sourcing_and_defaults_are_null(employee_client, part):
    detail = employee_client.get(f'/api/projects/{part[0]}/materials/{part[2]}').json['material']
    assert all(detail[f] is None for f in FIELDS)
    response = employee_client.post(f'/api/projects/{part[0]}/bom-lines', json={
        'colorway_id': part[1], 'name': 'Button', **VALUES,
    })
    assert response.status_code == 201, response.json
    assert {f: response.json['material'][f] for f in FIELDS} == VALUES


def test_optional_text_trimming_and_empty_values(employee_client, part):
    response = employee_client.patch(endpoint('bom', part), json={
        'supplied_by': '  Factory B  ', 'sourcing_status': ' delayed ', 'required_arrival': '',
        'approvals_needed': '  Fabric approval\nBulk sample sign-off  ',
    })
    assert response.status_code == 200
    assert response.json['material']['supplied_by'] == 'Factory B'
    assert response.json['material']['approvals_needed'] == 'Fabric approval\nBulk sample sign-off'
    assert response.json['material']['sourcing_status'] == 'delayed'
    response = employee_client.patch(endpoint('bom', part), json={'supplied_by': '', 'sourcing_status': '', 'approvals_needed': '  '})
    assert response.status_code == 200
    assert response.json['material']['supplied_by'] is None
    assert response.json['material']['sourcing_status'] is None
    assert response.json['material']['approvals_needed'] is None


def test_sourcing_patch_requires_login_and_correct_project(app, employee_client, part):
    other = Project(name='Other')
    db.session.add(other)
    db.session.commit()
    assert employee_client.patch(f'/api/projects/{other.id}/materials/{part[2]}', json=VALUES).status_code == 404
    with app.app_context():
        assert app.test_client().patch(endpoint('bom', part), json=VALUES).status_code == 401


def test_approvals_accepts_text_at_limit(employee_client, part):
    response = employee_client.patch(endpoint('bom', part), json={'approvals_needed': 'x' * 1000})
    assert response.status_code == 200
    assert response.json['material']['approvals_needed'] == 'x' * 1000
