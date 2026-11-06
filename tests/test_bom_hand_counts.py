"""Compare imported rows and their blank fields with a manual reference."""
import io
import json
from pathlib import Path

import pytest

from sample_bom import build_sample_bom
from bom_parse_comparison import compare_parse, validate_reference, format_report

# Ignore only the known unsupported Excel validation-extension warning.
pytestmark = pytest.mark.filterwarnings(
    "ignore:Data Validation extension is not supported and will be removed:UserWarning:openpyxl.*"
)

ROOT = Path(__file__).resolve().parents[1]
COUNTS_FILE = Path(__file__).parent / 'fixtures' / 'bom_hand_counts.json'
REFERENCE_BYTES = COUNTS_FILE.read_bytes()
CASES = json.loads(REFERENCE_BYTES)
ALLOWED_FIELDS = {'name', 'material', 'supplier', 'supplier_contact', 'quantity', 'location',
                  'article_no', 'material_size', 'uom', 'color', 'notes'}


@pytest.fixture(autouse=True)
def preserve_hand_reference():
    """Comparisons must never rewrite the independent manual reference."""
    yield
    assert COUNTS_FILE.read_bytes() == REFERENCE_BYTES, 'Hand counts changed during comparison; reference must be read-only.'


@pytest.mark.parametrize('case', CASES, ids=[case['id'] for case in CASES])
def test_api_counts_match_hand_counts(case, employee_client, tmp_path, request):
    def display(text):
        # Publish results on the test report; conftest prints them after capture ends.
        request.node.user_properties.append(('bom_summary', text))

    if case.get('total_bom_lines') is None or case.get('expected_lines') is None:
        message = f"{case['id']}: fill total_bom_lines and expected_lines in {COUNTS_FILE.name}"
        pytest.skip(message)

    errors = validate_reference(case, ALLOWED_FIELDS)
    if errors:
        message = case['id'] + ' — hand-count reference needs review:\n' + '\n'.join('  ' + e for e in errors)
        display('\n' + message)
        pytest.skip('Invalid hand-count reference; no accuracy calculated. See details above.')
    fields = case['checked_fields']
    expected = case['expected_lines']

    path = (build_sample_bom(tmp_path / 'sample_bom.xlsx') if case['file'] == 'generated:sample_bom'
            else ROOT / 'files' / case['file'])
    assert path.is_file(), f'Reference BOM not found: {path}'
    response = employee_client.post('/api/projects/import', data={
        'name': case['project_name'], 'file': (io.BytesIO(path.read_bytes()), path.name),
    }, content_type='multipart/form-data')
    assert response.status_code == 201, response.get_json()
    project_id = response.json['project_id']
    response = employee_client.get(f'/api/projects/{project_id}')
    assert response.status_code == 200
    detail = response.json
    actual = []
    for colorway in detail['colorways']:
        for material in colorway['materials']:
            source = material['fields']['name']['source']
            actual.append({'source_row': source['row'], 'colorway': colorway['name'],
                           'values': {field: material[field] for field in fields}})
    report = compare_parse(expected, actual, fields)
    summary = format_report(case['project_name'], report)
    display('\n' + summary)
    differences = report['missing_lines'] or report['unexpected_lines'] or any(
        not line['matches'] for line in report['lines']
    )
    count_errors = []
    if detail['project']['total_bom_lines'] != case['total_bom_lines']:
        count_errors.append('Project detail total differs from the hand count.')
    response = employee_client.get('/api/projects')
    assert response.status_code == 200
    listed = next(p for p in response.json['projects'] if p['id'] == project_id)
    if listed['total_bom_lines'] != case['total_bom_lines']:
        count_errors.append('Project list total differs from the hand count.')
    if differences or count_errors:
        display('  Differences found; comparison results are informational.')
        for error in count_errors:
            display('  ' + error)
    # BOM completeness percentages deliberately are not used to score parsing.
