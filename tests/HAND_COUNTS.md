# Manual BOM parse checks

Edit `tests/fixtures/bom_hand_counts.json` to maintain your independent references.
Expected counts must come from reviewing the original workbook, not API output.

For each project, fill `total_bom_lines` and `expected_lines`. Count one line
per BOM item per colorway. A row used in 3 colorways needs 3 reference entries.
Ignore headings, section labels, instructions, and measurement rows.
Use the spreadsheet's visible, one-based row number for `source_row`, and the
exact colorway header for `colorway`. These identify the line even if two parts
have the same name or an imported part name is missing.

Each line should look like this (copy it for each row/colorway):

```json
{
  "source_row": 14,
  "colorway": "BLACK",
  "blank_field_count": 2,
  "blank_fields": ["supplier", "article_no"]
}
```

Enter both the number of blank values and their field names. For a line with
no blanks, use `blank_field_count: 0` and `blank_fields: []`. References must
contain exactly `total_bom_lines` entries with no duplicate row/colorway pairs.

`checked_fields` defines which columns you are counting. The default covers
name, material description, supplier, supplier contact, quantity, placement
(`location`), article number (`article_no`), material size (`material_size`),
unit (`uom`), and color. Optional fields count too. You may add `notes` if you
want to assess the notes saved by the importer; some notes are composed from
multiple columns, so review that mapping first. Only assess canonical fields
that the API actually stores, not unrecognized spreadsheet columns.

Null, empty, or whitespace-only values count as blank. **Zero is populated**,
even though a zero quantity is flagged as incomplete by the product's business
rules.

## What the tests measure

The tests upload each workbook through the API into an isolated in-memory test
database. They compare the parsed lines and API total counts with the hand
reference, then compare the number **and identity** of blank fields per line.
A line with the right number of blanks in the wrong fields is reported as a mismatch.

The report's `parse_accuracy_percent` measures line detection and blank/populated
classification. Each hand-counted line contributes one check for being found
plus one check per checked field. A missing line earns no credit. Each extra
or duplicate parsed line adds the same number of failed checks.

`accuracy = correct checks / possible checks * 100`, rounded to two decimals.

With 10 checked fields, each line contributes 11 checks. Six accurately parsed
lines score 100%, even if two source lines genuinely lack a supplier. The old
67% product-completeness score is not a parsing-accuracy score. The tests leave
the API's `percent_complete` unchanged and do not use it in this comparison.

This metric does **not** verify the exact text/numbers of populated cells: a
wrong supplier that is still populated needs a separate value-equality check.
A fully empty reference and empty parse score 100%; extra lines reduce accuracy.
The displayed percentage is rounded; individual mismatches remain visible.

## Run the checks

From `RampBackEnd`, run without additional options:

```bash
./venv/bin/python -m pytest tests/test_bom_hand_counts.py
```

The default run prints line counts, parsing accuracy, and mismatched rows/fields
in the terminal at the end of the test run. It does not create JSON, text, or
JUnit report files. Uploaded test inputs still use pytest's temporary storage.
The known openpyxl data-validation-extension warning is filtered for these tests.

For a standalone hand-count run, output is quiet, skip reasons are shown, and
tracebacks are hidden automatically. Other test modules keep their normal output
settings. Project summaries are printed after the progress indicators, including for
passing tests. They remain visible without `-s`, even in the full suite.

Differences are informational by default and do not fail the run; **a passing
run in this mode does not mean parsing accuracy is 100%**. Invalid references
are displayed and skipped with no accuracy score. API failures, missing source
files, and other execution errors still fail. There are no custom command-line
options or alternate comparison modes.

Neither the parser nor the comparison changes the hand-count file. When a blank
count disagrees with its field list, review the original workbook and correct
whichever entry is wrong; the test never repairs it automatically.

Add projects with unique IDs and filenames under `files/`. Never fill hand
references from parser-generated results.

### Quantity and contact mapping rules

The numeric quantity cannot store `TBC` or `TBD`; those source values are
intentionally parsed as blank quantities. Include `quantity` in the reference's
blank fields for those lines. When there is no supplier-contact column, the
supplier/vendor supplies the contact; a blank vendor leaves both fields blank.
The NS008C reference includes both shell-fabric rows (9 and 10), for 17 lines.
Its colorway is spelled `Black` in the workbook, including on row 26.

A whole-cell `N/A` (ignoring case and surrounding spaces) is treated as missing
in every imported BOM field. Include such fields in `blank_fields`. The NS008C
SIZE cells on rows 9–12 and 15–17 therefore count as missing `material_size`;
their explicit UOM values remain populated.

The parser never reads this reference file. The comparison reads it only and
checks that its bytes stay unchanged during the run. Parser fixes must be tested
against independent generated examples, not implemented as per-reference overrides.
Whole-cell `TBD` is normalized to missing across BOM fields, just like `N/A`.
Reference mismatches are reported rather than automatically repaired.
