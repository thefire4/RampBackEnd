"""Protect the accuracy score against falsely passing parses."""
import pytest
from bom_parse_comparison import compare_parse

FIELDS = ['supplier', 'quantity']
EXPECTED = [{'source_row': 10, 'colorway': 'Blue', 'blank_fields': ['supplier'], 'blank_field_count': 1}]


def actual(supplier=None, quantity=0, row=10):
    return {'source_row': row, 'colorway': 'Blue', 'values': {'supplier': supplier, 'quantity': quantity}}


def test_preserving_blank_and_zero_is_accurate():
    report = compare_parse(EXPECTED, [actual()], FIELDS)
    assert report['parse_accuracy_percent'] == 100
    assert report['lines'][0]['api_blank_count'] == 1


def test_same_blank_count_in_wrong_field_is_inaccurate():
    report = compare_parse(EXPECTED, [actual(supplier='Mill', quantity=None)], FIELDS)
    assert report['lines'][0]['api_blank_count'] == report['lines'][0]['hand_blank_count'] == 1
    assert report['lines'][0]['matches'] is False
    assert report['parse_accuracy_percent'] == 33.33


def test_missing_row_gets_no_credit():
    report = compare_parse(EXPECTED, [], FIELDS)
    assert report['missing_lines'] == 1
    assert report['parse_accuracy_percent'] == 0
    assert report['lines'][0]['api_blank_count'] is None


@pytest.mark.parametrize('row', [10, 11])
def test_duplicate_or_extra_rows_reduce_accuracy(row):
    report = compare_parse(EXPECTED, [actual(), actual(row=row)], FIELDS)
    assert report['unexpected_lines'] == 1
    assert report['parse_accuracy_percent'] == 50


def test_wrong_row_with_same_total_does_not_pass():
    report = compare_parse(EXPECTED, [actual(row=11)], FIELDS)
    assert report['missing_lines'] == report['unexpected_lines'] == 1
    assert report['parse_accuracy_percent'] == 0


def test_reference_errors_identify_every_inconsistent_line():
    from bom_parse_comparison import validate_reference
    case = {'checked_fields': FIELDS, 'total_bom_lines': 2, 'expected_lines': [
        {'source_row': 10, 'colorway': 'Blue', 'blank_field_count': 0, 'blank_fields': ['supplier']},
        {'source_row': 11, 'colorway': 'Blue', 'blank_field_count': 2, 'blank_fields': []},
    ]}
    errors = validate_reference(case, set(FIELDS))
    assert len(errors) == 2
    assert 'Row 10, Blue' in errors[0]
    assert 'Row 11, Blue' in errors[1]


def test_readable_report_identifies_missing_extra_and_wrong_blank_fields():
    from bom_parse_comparison import format_report
    report = compare_parse(EXPECTED, [actual(supplier='Mill', quantity=None), actual(row=99)], FIELDS)
    text = format_report('Test BOM', report)
    assert 'blanks hand 1, API 1' in text
    assert 'API blank, hand populated: quantity' in text
    assert 'API populated, hand blank: supplier' in text
    assert 'Extra API line: row 99, Blue' in text
    missing_text = format_report('Test BOM', compare_parse(EXPECTED, [], FIELDS))
    assert 'Row 10, Blue: line not found' in missing_text


def test_comparison_does_not_normalize_api_data_or_rewrite_reference():
    from copy import deepcopy
    expected = deepcopy(EXPECTED)
    api_lines = [actual(supplier='TBD')]
    before_expected, before_api = deepcopy(expected), deepcopy(api_lines)
    report = compare_parse(expected, api_lines, FIELDS)
    # An unnormalized TBD returned by the API is a parser failure, not something
    # the comparator is allowed to clean up to make the reference pass.
    assert report['lines'][0]['api_blank_count'] == 0
    assert report['lines'][0]['matches'] is False
    assert expected == before_expected
    assert api_lines == before_api
