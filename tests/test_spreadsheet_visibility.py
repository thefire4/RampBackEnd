import io

import openpyxl

from src.api.services.spreadsheet_utils import load_sheet_rows


def test_hidden_rows_and_grouped_columns_preserve_source_positions(tmp_path):
    path = tmp_path / 'hidden.xlsx'
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(['Visible', 'Hidden B', 'Hidden C', 'Visible D'])
    sheet.append(['Hidden row', 1, 2, 3])
    sheet.append(['Visible row', 4, 5, 6])
    sheet.row_dimensions[2].hidden = True
    sheet.column_dimensions.group('B', 'C', hidden=True)
    workbook.save(path)
    workbook.close()
    assert load_sheet_rows(path) == [
        (1, ('Visible', None, None, 'Visible D')),
        (3, ('Visible row', None, None, 6)),
    ]


def test_hidden_colorway_and_bom_row_not_imported(employee_client, tmp_path):
    path = tmp_path / 'bom.xlsx'
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'BOM'
    sheet.append(['Item', 'Product Description', 'BLACK', 'CHARCOAL', 'OLIVE'])
    sheet.append(['Shell', 'Cotton', 'Black', 'Charcoal', 'Olive'])
    sheet.append(['Hidden part', 'Wool', 'Black', 'Charcoal', 'Olive'])
    sheet.column_dimensions['D'].hidden = True
    sheet.row_dimensions[3].hidden = True
    workbook.save(path)
    workbook.close()
    response = employee_client.post('/api/projects/import', data={
        'file': (io.BytesIO(path.read_bytes()), path.name),
    })
    assert response.status_code == 201, response.json
    assert response.json['bom']['materials_created'] == 2
    project = employee_client.get(f'/api/projects/{response.json["project_id"]}').json
    assert [c['name'] for c in project['colorways']] == ['BLACK', 'OLIVE']
    for colorway in project['colorways']:
        assert [m['name'] for m in colorway['materials']] == ['Shell']
        assert colorway['materials'][0]['fields']['name']['source']['row'] == 2


def test_csv_rows_are_unchanged(tmp_path):
    path = tmp_path / 'bom.csv'
    path.write_text('Item,Color\nShell,Black\n')
    assert load_sheet_rows(path) == [(1, ('Item', 'Color')), (2, ('Shell', 'Black'))]
