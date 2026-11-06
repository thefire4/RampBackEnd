# Upload and visually inspect saved BOM lines

Run from `RampBackEnd`, without extra options:

```bash
./venv/bin/python -m pytest tests/test_bom_upload_values.py
```

The test discovers every supported sample in `files/` and uploads it through
`POST /api/projects/import`. It reloads the committed database records in a
fresh session, then prints all saved BOM values for you to compare with the
original worksheet. No comparison file or report files are used or created.

Output is grouped by source file, colorway, and original spreadsheet row.
Each line shows name, material, supplier, supplier contact, quantity, placement,
article number, material size, UOM, color, and notes. Missing values appear as
`<missing>`. Long values wrap; quoted values preserve visible escape sequences
for embedded newlines and tabs. The output appears in the terminal summary,
including when pytest captures passing tests' output.

The automated checks verify that uploads succeed, BOM rows are committed, and
source-file/row tracking and the linked file record exist. They do not certify
that the parsed values or line counts match the original workbook: that is the
visual review this output supports. Upload/persistence failures still fail the
test and log the reason.

Tests use an isolated SQLite in-memory database and a temporary upload folder.
A finally block removes each test project, related rows, and uploaded copy,
even when an assertion fails. Cleanup is checked and its status is printed.
Original sample files are not changed. The app fixture also drops the temporary
test tables after each test. Add sample files to `files/` to include them in the
next run; hidden office lock files are excluded by their unsupported suffixes.
