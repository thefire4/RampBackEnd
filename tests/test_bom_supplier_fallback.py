import io

import pytest

from src.api.services.bom_import import _build_row_payload


@pytest.mark.parametrize(('field_map', 'row', 'expected'), [
    ({0: 'supplier'}, ('Vendor Ltd',), 'Vendor Ltd'),
    ({0: 'supplier'}, (None,), None),
    ({0: 'supplier'}, ('  ',), None),
    ({0: 'name'}, ('Shell',), None),
    ({0: 'supplier', 1: 'supplier_contact'}, ('Vendor Ltd', 'Jane'), 'Jane'),
    ({0: 'supplier', 1: 'supplier_contact'}, ('Vendor Ltd', None), None),
    ({0: 'supplier', 1: 'supplier_contact'}, ('Vendor Ltd', '  '), None),
])
def test_supplier_contact_fallback_only_without_contact_column(field_map, row, expected):
    assert _build_row_payload(row, field_map).get('supplier_contact') == expected


@pytest.mark.parametrize('supplier_header', ['Vendor', 'Supplier', 'Supplier Name'])
def test_import_returns_vendor_contact_with_source(employee_client, supplier_header):
    content = f'Item,Product Description,{supplier_header},Color\nShell,Cotton,Vendor Ltd,Blue\n'
    response = employee_client.post('/api/projects/import', data={
        'file': (io.BytesIO(content.encode()), 'vendor.csv'),
    })
    assert response.status_code == 201, response.json
    project_id = response.json['project_id']
    material = employee_client.get(f'/api/projects/{project_id}').json['colorways'][0]['materials'][0]
    assert material['supplier_contact'] == material['supplier'] == 'Vendor Ltd'
    source = material['fields']['supplier_contact']['source']
    assert source['file_name'] == 'vendor.csv'
    assert source['row'] == 2


@pytest.mark.parametrize('unknown_quantity', ['TBC', 'TBD'])
def test_unknown_numeric_quantity_stays_blank_and_can_be_corrected(employee_client, unknown_quantity):
    content = f'Item,Product Description,Vendor,Color,Quantity\nShell,Cotton,Vendor Ltd,Blue,{unknown_quantity}\n'
    response = employee_client.post('/api/projects/import', data={
        'file': (io.BytesIO(content.encode()), 'unknown-quantity.csv'),
    })
    assert response.status_code == 201, response.json
    project_id = response.json['project_id']
    part = employee_client.get(f'/api/projects/{project_id}').json['colorways'][0]['materials'][0]
    assert part['quantity'] is None
    assert 'quantity' in part['missing_fields']
    assert part['supplier_contact'] == 'Vendor Ltd'
    response = employee_client.patch(f'/api/bom-lines/{part["id"]}', json={'quantity': 2.5})
    assert response.status_code == 200
    assert response.json['material']['quantity'] == 2.5


@pytest.mark.parametrize('contact_mode', ['absent', 'hidden', 'present'])
def test_excel_contact_column_detection_and_fallback(employee_client, tmp_path, contact_mode):
    import openpyxl
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'BOM'
    sheet.append(['SYMBOL', 'FABRIC', 'VENDOR', 'CONTENT', 'Black'])
    sheet.append(['L1', 'Lining', 'Kendor', 'Nylon', 'Black'])
    if contact_mode != 'absent':
        sheet.cell(1, 6, 'SUPPLIER CONTACT')
        sheet.cell(2, 6, 'Jane Doe')
        sheet.column_dimensions['F'].hidden = contact_mode == 'hidden'
    path = tmp_path / 'contact.xlsx'
    workbook.save(path)
    workbook.close()
    response = employee_client.post('/api/projects/import', data={'file': (io.BytesIO(path.read_bytes()), path.name)})
    assert response.status_code == 201, response.json
    part = employee_client.get(f'/api/projects/{response.json["project_id"]}').json['colorways'][0]['materials'][0]
    assert part['supplier'] == 'Kendor'
    assert part['supplier_contact'] == ('Jane Doe' if contact_mode == 'present' else 'Kendor')
