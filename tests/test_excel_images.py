import io
from pathlib import Path

import openpyxl
from openpyxl.drawing.image import Image as ExcelImage
from PIL import Image
import pytest

from src.api.extensions import db
from src.api.models import Project, ProjectFile
from src.api.services.excel_images import extract_excel_images

FILES = Path(__file__).resolve().parents[1] / 'files'


def png(size):
    stream = io.BytesIO()
    Image.new('RGB', size, 'white').save(stream, format='PNG')
    return stream.getvalue()


def pack(tmp_path, suffix='.xlsx'):
    workbook = openpyxl.Workbook()
    bom = workbook.active
    bom.title = 'BOM'
    bom.append(['Item', 'Product Description'])
    bom.append(['Shell', 'Cotton'])
    sketches = workbook.create_sheet('Sketches')
    sketches.add_image(ExcelImage(io.BytesIO(png((400, 400)))), 'A1')
    sketches.add_image(ExcelImage(io.BytesIO(png((32, 32)))), 'J1')
    small_display = ExcelImage(io.BytesIO(png((500, 500))))
    small_display.width = small_display.height = 32
    sketches.add_image(small_display, 'M1')
    path = tmp_path / ('pack' + suffix)
    workbook.save(path)
    workbook.close()
    return path


@pytest.mark.parametrize('suffix', ['.xlsx', '.xlsm'])
def test_upload_extracts_sketches_skips_icons_and_serves_images(app, employee_client, tmp_path, suffix):
    path = pack(tmp_path, suffix)
    response = employee_client.post('/api/projects/import', data={'file': (io.BytesIO(path.read_bytes()), path.name)})
    assert response.status_code == 201, response.json
    assert response.json['images_created'] == 1
    assert response.json['images_skipped'] == 2
    project_id = response.json['project_id']
    db.session.remove()
    files = ProjectFile.query.filter_by(project_id=project_id).all()
    assert len(files) == 2  # Original workbook and one sketch.
    sketch = next(f for f in files if f.source_sheet)
    assert sketch.source_sheet == 'Sketches'
    assert sketch.source_file_id == response.json['file_id']
    assert Path(sketch.file_path).read_bytes() == png((400, 400))
    listed = employee_client.get(f'/api/projects/{project_id}/images').json['images']
    assert len(listed) == 1
    assert listed[0]['source_sheet'] == 'Sketches'
    assert listed[0]['source_file_id'] == response.json['file_id']
    served = employee_client.get(listed[0]['url'])
    assert served.status_code == 200
    assert served.mimetype == 'image/png'
    assert served.data == png((400, 400))


@pytest.mark.parametrize(('filename', 'tab', 'count'), [
    ("DW11038_M's Snowcrest_Shirt Jac_ REV2 BTUSA PO 1654 07.10.2026 (2).xlsx", 'FRONT', 18),
    ('NS008C_Zip Jacket (2).xlsm', 'Sketch', 3),
])
def test_sample_tech_pack_upload_saves_its_sketches(employee_client, filename, tab, count):
    path = FILES / filename
    response = employee_client.post('/api/projects/import', data={'file': (io.BytesIO(path.read_bytes()), filename)})
    assert response.status_code == 201, response.json
    assert response.json['images_created'] == count
    project_id = response.json['project_id']
    db.session.remove()
    saved = ProjectFile.query.filter_by(project_id=project_id, source_file_id=response.json['file_id']).all()
    assert len(saved) == count
    assert any(image.source_sheet == tab for image in saved)
    for image in saved:
        assert Path(image.file_path).is_file()
        assert image.source_sheet
        assert image.file_type.startswith('image/')
    listed = employee_client.get(f'/api/projects/{project_id}/images').json['images']
    sketch = next(image for image in listed if image['source_sheet'] == tab)
    assert employee_client.get(sketch['url']).status_code == 200
    original = db.session.get(ProjectFile, response.json['file_id'])
    assert Path(original.file_path).read_bytes() == path.read_bytes()


def test_failed_commit_removes_workbook_and_extracted_images(app, employee_client, tmp_path, monkeypatch):
    path = pack(tmp_path)
    def fail_commit():
        raise OSError('test database failure')
    monkeypatch.setattr(db.session, 'commit', fail_commit)
    response = employee_client.post('/api/projects/import', data={'file': (io.BytesIO(path.read_bytes()), path.name)})
    assert response.status_code == 400
    assert 'test database failure' in response.json['error']
    assert Project.query.count() == 0
    assert not [p for p in Path(app.config['UPLOAD_FOLDER']).rglob('*') if p.is_file()]


def test_non_excel_upload_has_no_extracted_images(tmp_path):
    path = tmp_path / 'bom.csv'
    path.write_text('Item,Description\nShell,Cotton\n')
    assert extract_excel_images(path).images == []
