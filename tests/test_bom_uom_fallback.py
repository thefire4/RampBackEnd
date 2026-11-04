import io

import pytest

from src.api.services.bom_import import _build_row_payload
from src.api.extensions import db
from src.api.models import ProjectMaterial


@pytest.mark.parametrize(('field_map', 'row', 'expected'), [
    ({0: 'material_size'}, ('58 inches wide',), '58 inches wide'),
    ({0: 'material_size'}, (24,), '24'),
    ({0: 'material_size'}, (None,), None),
    ({0: 'name'}, ('Shell',), None),
    ({0: 'material_size', 1: 'uom'}, ('58 inches wide', 'yd'), 'yd'),
    ({0: 'material_size', 1: 'uom'}, ('58 inches wide', None), None),
    ({0: 'material_size', 1: 'uom'}, ('58 inches wide', '  '), None),
    ({0: 'material_size', 1: 'uom'}, ('58 inches wide',), None),
])
def test_size_fallback_only_when_uom_column_is_absent(field_map, row, expected):
    assert _build_row_payload(row, field_map).get('uom') == expected


@pytest.mark.parametrize('color_headers', ['Color', 'BLACK,OLIVE'])
@pytest.mark.parametrize('size_header', ['Size', 'measured_size', 'Measured Size'])
def test_import_saves_size_fallback_and_sources(employee_client, color_headers, size_header):
    colors = 'Black' if color_headers == 'Color' else 'Black,Olive'
    content = f'Item,Product Description,{size_header},{color_headers}\nShell,Cotton,58 inches wide,{colors}\n'
    response = employee_client.post('/api/projects/import', data={
        'file': (io.BytesIO(content.encode()), 'size.csv'),
    })
    assert response.status_code == 201, response.json
    project_id = response.json['project_id']
    detail = employee_client.get(f'/api/projects/{project_id}').json
    for colorway in detail['colorways']:
        part = colorway['materials'][0]
        assert part['uom'] == part['material_size'] == '58 inches wide'
        source = part['fields']['uom']['source']
        assert source['file_name'] == 'size.csv'
        assert source['row'] == 2
        assert employee_client.get(source['url']).status_code == 200
        db.session.expire_all()
        assert db.session.get(ProjectMaterial, part['id']).uom == '58 inches wide'
        assert employee_client.patch(f'/api/bom-lines/{part["id"]}', json={'uom': '60 inches wide'}).status_code == 200
