"""Upload each sample and print committed BOM rows for human review."""
import io
import logging
from pathlib import Path
import textwrap

import pytest

from src.api.extensions import db
from src.api.models import (
    Project, ProjectColor, ProjectMaterial, ProjectFile,
    ValueSource, ProjectChangeLog, PointsMeasured,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SUFFIXES = {'.xlsx', '.xlsm', '.xltx', '.xltm', '.csv', '.pdf'}
SAMPLES = sorted(path for path in (ROOT / 'files').iterdir()
                 if path.is_file() and path.suffix.lower() in SAMPLE_SUFFIXES)
BOM_FIELDS = ('name', 'material', 'supplier', 'supplier_contact', 'quantity', 'location',
              'article_no', 'material_size', 'uom', 'color', 'notes')
LOGGER = logging.getLogger(__name__)
pytestmark = pytest.mark.filterwarnings(
    'ignore:Data Validation extension is not supported and will be removed:UserWarning:openpyxl.*'
)


def summary(request, message):
    request.node.user_properties.append(('bom_summary', message))


def fail(request, filename, reasons):
    summary(request, '\n' + filename + '\n' + '\n'.join('  FAILED: ' + r for r in reasons))
    for reason in reasons:
        LOGGER.error('%s: %s', filename, reason)
    pytest.fail('\n'.join(reasons), pytrace=False)


@pytest.fixture(params=SAMPLES or [None], ids=[p.name for p in SAMPLES] or ['no-samples'])
def uploaded_bom(request, app, employee_client):
    path = request.param
    if path is None:
        fail(request, 'Sample files', ['No supported sample files found in files/.'])
    project_id = None
    material_ids = []
    upload_dir = Path(app.config['UPLOAD_FOLDER'])
    previous_files = set(upload_dir.rglob('*')) if upload_dir.exists() else set()
    try:
        response = employee_client.post('/api/projects/import', data={
            'name': path.stem[:100], 'file': (io.BytesIO(path.read_bytes()), path.name),
        }, content_type='multipart/form-data')
        if response.status_code != 201:
            fail(request, path.name, [f'Upload returned HTTP {response.status_code}: {response.get_json()}'])
        project_id = response.json['project_id']
        # Reload committed records, not the import response or cached ORM objects.
        db.session.remove()
        materials = (ProjectMaterial.query.join(ProjectColor)
                     .filter(ProjectColor.project_id == project_id)
                     .order_by(ProjectColor.id, ProjectMaterial.import_source_row, ProjectMaterial.id).all())
        material_ids = [m.id for m in materials]
        saved_lines = [{'source_row': m.import_source_row, 'colorway': m.colorway.name,
                        'source_file': m.import_source_file,
                        'values': {f: getattr(m, f) for f in BOM_FIELDS}} for m in materials]
        yield path.name, project_id, saved_lines
    finally:
        db.session.rollback()
        if project_id is not None:
            ValueSource.query.filter_by(project_id=project_id).delete()
            ProjectChangeLog.query.filter_by(project_id=project_id).delete()
            project = db.session.get(Project, project_id)
            if project is not None:
                db.session.delete(project)
            db.session.commit()
            assert db.session.get(Project, project_id) is None
            if material_ids:
                assert ProjectMaterial.query.filter(ProjectMaterial.id.in_(material_ids)).count() == 0
            for model in (ProjectColor, ProjectFile, PointsMeasured, ValueSource, ProjectChangeLog):
                assert model.query.filter_by(project_id=project_id).count() == 0
        if upload_dir.exists():
            for uploaded_path in set(upload_dir.rglob('*')) - previous_files:
                if uploaded_path.is_file():
                    uploaded_path.unlink()
        summary(request, '  Cleanup: test project, related rows, and uploaded copy removed.\n')


def test_sample_upload_commits_and_prints_bom_rows(uploaded_bom, request):
    filename, project_id, saved_lines = uploaded_bom
    output = [f'\n{filename}', f'  Saved BOM lines: {len(saved_lines)}']
    previous_colorway = None
    for line in saved_lines:
        if line['colorway'] != previous_colorway:
            output.append(f"\n  Colorway: {line['colorway']}")
            previous_colorway = line['colorway']
        output.append(f"    Source row: {line['source_row']}")
        for field, value in line['values'].items():
            display_value = '<missing>' if value is None else repr(value)
            output.append(textwrap.fill(f'{field}: {display_value}', width=110,
                                        initial_indent='      ', subsequent_indent='        '))
        output.append('')
    summary(request, '\n'.join(output))

    reasons = []
    if not saved_lines:
        reasons.append('Upload succeeded but no BOM lines were committed to the database.')
    for line in saved_lines:
        if line['source_file'] != filename or line['source_row'] is None:
            reasons.append(f"Row {line['source_row']}, {line['colorway']}: incorrect source-file/row tracking.")
    if ProjectFile.query.filter_by(project_id=project_id, file_name=filename).count() != 1:
        reasons.append('Expected one saved original-file record linked to the project.')
    if reasons:
        fail(request, filename, reasons)
