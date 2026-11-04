import io


def test_sectioned_bom_keeps_unsymbolled_parts_and_stops_at_instructions(employee_client):
    data = (
        'SYMBOL,FABRIC,VENDOR,CONTENT,Black,SIZE,USAGE,UOM,POSITION\n'
        'L1,Lining,Mill,Cotton,Black,Wide,1,METERS,Body\n'
        'SYMBOL,TRIMS,VENDOR,CONTENT,Black,SIZE,USAGE,UOM,POSITION\n'
        'T1,Zipper,Factory,,Black,Long,1,EACH,Front\n'
        'SYMBOL,THREAD,VENDOR,CONTENT,Black,SIZE,USAGE,UOM,POSITION\n'
        ',Sewing thread,,,DTM,,1,YARD,\n'
        'SYMBOL,LABELS & PACKAGING:,VENDOR,CONTENT,Black,SIZE,USAGE,UOM,POSITION\n'
        ',Main label,Labels Ltd,,,,1,EACH,Neck\n'
        '\n'
        'General,,,,Style Specific,,,,\n'
        'Do not import these instructions,,,,Check sewing,,,,\n'
    )
    response = employee_client.post('/api/projects/import', data={
        'file': (io.BytesIO(data.encode()), 'sections.csv'),
    })
    assert response.status_code == 201, response.json
    assert response.json['bom']['materials_created'] == 4
    detail = employee_client.get(f'/api/projects/{response.json["project_id"]}').json
    parts = detail['colorways'][0]['materials']
    assert [p['name'] for p in parts] == ['L1', 'T1', 'Sewing thread', 'Main label']
    assert [p['material'] for p in parts] == ['Cotton', None, None, None]
    assert parts[-1]['color'] is None
    assert [p['fields']['name']['source']['row'] for p in parts] == [2, 4, 6, 8]


def test_part_named_general_is_kept_when_it_has_material_data(employee_client):
    data = b'Item,Product Description,Color\nGeneral,Cotton,Blue\n'
    response = employee_client.post('/api/projects/import', data={'file': (io.BytesIO(data), 'general.csv')})
    assert response.status_code == 201, response.json
    assert response.json['bom']['materials_created'] == 1
