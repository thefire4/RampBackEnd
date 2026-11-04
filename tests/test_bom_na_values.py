import io

import pytest

from src.api.services.bom_import import _build_row_payload


@pytest.mark.parametrize('marker', ['N/A', 'n/a', ' N/A '])
@pytest.mark.parametrize('field', ['name', 'material', 'supplier', 'supplier_contact', 'quantity',
                                   'location', 'article_no', 'material_size', 'uom', 'color', 'notes'])
def test_na_fields_are_missing(marker, field):
    assert _build_row_payload((marker,), {0: field}).get(field) is None


def test_na_does_not_replace_real_text_or_populate_fallbacks():
    payload = _build_row_payload(('N/A', 'N/A', 'N/A finish'),
                                 {0: 'material_size', 1: 'supplier', 2: 'material'})
    assert payload.get('uom') is None
    assert payload.get('supplier_contact') is None
    assert payload['material'] == 'N/A finish'


@pytest.mark.parametrize('color_header', ['Color', 'Black'])
def test_na_imports_as_null_including_colorway_values(employee_client, color_header):
    content = f'Item,Product Description,Vendor,Size,Quantity,{color_header}\nShell,N/A,N/A,N/A,N/A,N/A\n'
    response = employee_client.post('/api/projects/import', data={
        'file': (io.BytesIO(content.encode()), 'na.csv'),
    })
    assert response.status_code == 201, response.json
    project_id = response.json['project_id']
    detail = employee_client.get(f'/api/projects/{project_id}').json
    material = detail['colorways'][0]['materials'][0]
    for field in ('material', 'supplier', 'supplier_contact', 'material_size', 'uom', 'quantity', 'color'):
        assert material[field] is None, field
        assert field in material['missing_fields']
    missing = employee_client.get(f'/api/projects/{project_id}/missing-items').json
    assert missing['total'] == 1


@pytest.mark.parametrize('marker', ['TBD', 'tbd', ' TBD '])
@pytest.mark.parametrize('field', ['name', 'material', 'supplier', 'supplier_contact', 'quantity',
                                   'location', 'article_no', 'material_size', 'uom', 'color', 'notes'])
def test_tbd_fields_are_missing(marker, field):
    assert _build_row_payload((marker,), {0: field}).get(field) is None


@pytest.mark.parametrize('color_header', ['Color', 'Black'])
def test_tbd_imports_as_missing_before_fallbacks(employee_client, color_header):
    content = f'Item,Product Description,Vendor,Size,Quantity,{color_header}\nShell,TBD,TBD,TBD,TBD,TBD\n'
    response = employee_client.post('/api/projects/import', data={
        'file': (io.BytesIO(content.encode()), 'tbd.csv'),
    })
    assert response.status_code == 201, response.json
    part = employee_client.get(f'/api/projects/{response.json["project_id"]}').json['colorways'][0]['materials'][0]
    for field in ('material', 'supplier', 'supplier_contact', 'material_size', 'uom', 'quantity', 'color'):
        assert part[field] is None
        assert field in part['missing_fields']
    assert _build_row_payload(('TBD supplier confirmation',), {0: 'notes'})['notes'] == 'TBD supplier confirmation'
