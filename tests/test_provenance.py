from io import BytesIO
from test_document_import import app
from src.api.extensions import db
from src.api.models import Project, ValueSource


def test_sources_and_manual_edit(app, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = '1'
        session['_fresh'] = True
    original = b'Material Name,Supplier,Color,Quantity\nButton,Acme,Blue,4\n'
    response = client.post('/api/projects/import', data={'file': (BytesIO(original), 'original.csv')})
    assert response.status_code == 201
    pid = response.json['project_id']
    dashboard = client.get(f'/api/projects/{pid}').json['project']
    material = dashboard['materials'][0]
    source = material['fields']['supplier']['source']
    assert source['file_name'] == 'original.csv'
    assert source['row'] == 2
    assert client.get(source['url']).data == original
    response = client.patch(f'/api/projects/{pid}/materials/{material["id"]}', json={'supplier': 'Hand typed'})
    assert response.status_code == 200
    fields = response.json['project']['materials'][0]['fields']
    assert fields['supplier']['source']['kind'] == 'manual'
    assert fields['supplier']['source']['url'] is None
    assert fields['color']['source']['kind'] == 'file'
    assert client.get(f'/api/projects/{pid + 1}/files/{source["file_id"]}').status_code == 404
    with app.app_context():
        assert app.test_client().get(source['url']).status_code == 401
    with app.app_context():
        db.session.expire_all()
        assert ValueSource.query.filter_by(entity_type='material', field='supplier').one().kind == 'manual'


def test_manual_and_legacy(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = '1'
        session['_fresh'] = True
    response = client.post('/api/projects', json={'name': 'Typed'})
    pid = response.json['project']['id']
    dashboard = client.get(f'/api/projects/{pid}').json['project']
    assert dashboard['fields']['name']['source']['kind'] == 'manual'
    assert dashboard['fields']['season']['source']['kind'] == 'missing'
    with app.app_context():
        db.session.get(Project, pid).customer = 'Legacy'
        db.session.commit()
    assert client.get(f'/api/projects/{pid}').json['project']['fields']['customer']['source']['kind'] == 'unknown'
    assert client.patch(f'/api/projects/{pid}', json={'project_date': 'bad'}).status_code == 400
    assert client.patch(f'/api/projects/{pid}', json={'season': 'FW26'}).status_code == 200
