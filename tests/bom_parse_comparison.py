"""Independent scoring of line detection and blank/populated field parsing."""
from collections import defaultdict


def compare_parse(expected_lines, actual_lines, checked_fields):
    """Missing/extra/duplicate lines lose credit, even if total counts happen to match."""
    actual_by_key = defaultdict(list)
    for line in actual_lines:
        actual_by_key[(line['source_row'], line['colorway'])].append(line)
    correct_checks = 0
    results = []
    for expected in expected_lines:
        key = (expected['source_row'], expected['colorway'])
        candidates = actual_by_key.get(key, [])
        actual = candidates.pop(0) if candidates else None
        expected_blank = set(expected['blank_fields'])
        actual_blank = None
        if actual is not None:
            correct_checks += 1  # This expected row/colorway was found.
            actual_blank = {
                field for field in checked_fields
                if actual['values'][field] is None
                or isinstance(actual['values'][field], str) and not actual['values'][field].strip()
            }
            correct_checks += sum((f in actual_blank) == (f in expected_blank) for f in checked_fields)
        results.append({
            'source_row': key[0], 'colorway': key[1],
            'hand_blank_count': expected['blank_field_count'],
            'api_blank_count': len(actual_blank) if actual_blank is not None else None,
            'hand_blank_fields': sorted(expected_blank),
            'api_blank_fields': sorted(actual_blank) if actual_blank is not None else None,
            'matches': actual is not None and actual_blank == expected_blank,
        })
    extras = [line for candidates in actual_by_key.values() for line in candidates]
    possible_checks = (len(expected_lines) + len(extras)) * (1 + len(checked_fields))
    return {
        'hand_total_lines': len(expected_lines), 'api_total_lines': len(actual_lines),
        'missing_lines': sum(r['api_blank_count'] is None for r in results),
        'unexpected_lines': len(extras),
        'unexpected_line_details': [{'source_row': line['source_row'], 'colorway': line['colorway']} for line in extras],
        'correct_checks': correct_checks, 'possible_checks': possible_checks,
        'parse_accuracy_percent': round(100 * correct_checks / possible_checks, 2) if possible_checks else 100,
        'lines': results,
    }


def validate_reference(case, allowed_fields):
    """Return actionable reference errors before attempting a parse."""
    errors = []
    fields = case.get('checked_fields')
    if not isinstance(fields, list) or not fields or any(not isinstance(f, str) for f in fields):
        return ['checked_fields must be a nonempty list of field names.']
    if len(set(fields)) != len(fields) or not set(fields) <= allowed_fields:
        errors.append('checked_fields contains duplicate or unsupported fields.')
    lines = case.get('expected_lines')
    if not isinstance(lines, list):
        return errors + ['expected_lines must be a list.']
    total = case.get('total_bom_lines')
    if type(total) is not int or total < 0 or total != len(lines):
        errors.append(f'total_bom_lines is {total}; expected_lines contains {len(lines)} entries.')
    keys = set()
    for index, line in enumerate(lines, 1):
        if not isinstance(line, dict):
            errors.append(f'Entry {index} must be an object.')
            continue
        row, color = line.get('source_row'), line.get('colorway')
        label = f'Row {row}, {color}'
        if type(row) is not int or row <= 0 or not isinstance(color, str) or not color.strip():
            errors.append(f'Entry {index}: enter a positive source_row and a colorway name.')
        elif (row, color) in keys:
            errors.append(f'{label}: duplicate reference line.')
        else:
            keys.add((row, color))
        blanks = line.get('blank_fields')
        if not isinstance(blanks, list) or any(not isinstance(f, str) for f in blanks):
            errors.append(f'{label}: blank_fields must be a list of field names.')
            continue
        if len(set(blanks)) != len(blanks) or not set(blanks) <= set(fields):
            errors.append(f'{label}: blank_fields contains duplicate or unchecked fields.')
        count = line.get('blank_field_count')
        if type(count) is not int or count != len(blanks):
            errors.append(f'{label}: blank_field_count is {count}, but blank_fields lists {len(blanks)}: {", ".join(blanks)}. Review which is correct.')
    return errors


def format_report(project_name, report):
    """Readable output without dumping the entire test function or JSON."""
    lines = [
        project_name,
        f"  Lines: hand {report['hand_total_lines']}, API {report['api_total_lines']}",
        f"  Missing lines: {report['missing_lines']}; extra/duplicate lines: {report['unexpected_lines']}",
        f"  Parse accuracy: {report['parse_accuracy_percent']}%",
    ]
    mismatches = [line for line in report['lines'] if not line['matches']]
    if not mismatches and not report['unexpected_lines']:
        lines.append('  All lines and blank fields match.')
    for line in mismatches:
        label = f"  Row {line['source_row']}, {line['colorway']}"
        if line['api_blank_fields'] is None:
            lines.append(f'{label}: line not found by the API.')
            continue
        lines.append(f"{label}: blanks hand {line['hand_blank_count']}, API {line['api_blank_count']}")
        for title, fields in (
            ('API blank, hand populated', set(line['api_blank_fields']) - set(line['hand_blank_fields'])),
            ('API populated, hand blank', set(line['hand_blank_fields']) - set(line['api_blank_fields'])),
        ):
            if fields:
                lines.append(f"    {title}: {', '.join(sorted(fields))}")
    for line in report.get('unexpected_line_details', []):
        lines.append(f"  Extra API line: row {line['source_row']}, {line['colorway']}")
    return '\n'.join(lines)
