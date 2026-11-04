# RampCoreOs

Start server with python run.py
Server uses cors and CSRF tokens for security and cookies

## Database setup

Run `SQL_Setup.sql` in MySQL to create the database and tables. 

## BOM line API

- `GET /api/projects` lists all projects with their style, description, stage,
  PO number, project date, total and missing BOM line counts, and integer
  completion percentage.
- `GET /api/projects/<project_id>` returns one project's overview, colorways,
  BOM lines, files, and the same completeness counts. Projects with no BOM
  lines report `0` percent complete.
- `GET /api/projects/<project_id>/images` lists that project's images with
  their file name, MIME type, upload date, and image URL.
- `GET /api/projects/<project_id>/images/<file_id>` serves the full-size image.
  Missing files return `404`; files that cannot be opened return `500`.
- `PATCH /api/bom-lines/<line_id>` updates one or more editable BOM fields.
- `PATCH /api/projects/<project_id>` updates project details. It accepts
  `name`, `stage` (or `status`), `style_no`, `po_no`, `project_date`, `customer`,
  `size_range`, `season`, `fabric_yarn`, `designer`, `weight`, and
  `description`; dates use `YYYY-MM-DD`.
- `POST /api/projects/<project_id>/bom-lines` creates a line; include the project's
  `colorway_id` and any BOM fields in the JSON body.
- `DELETE /api/bom-lines/<line_id>` deletes a line.
- `GET /api/projects/<project_id>/history` returns field-level change-log entries,
  including the user and timestamp.

Quantities must be finite numbers greater than or equal to zero. Whitespace-only
values are rejected for required material fields. Each successful create, edit, or
delete records old and new values in `project_change_log` and returns the updated
`missing_bom_items` count. For an existing database, run
`migrations/001_bom_line_audit.sql`; for a fresh database, use the updated
`SQL_Setup.sql`.
## Spreadsheet visibility

Excel imports ignore hidden rows and columns, including hidden colorway columns.
Original row numbers and column positions are retained for source tracking.
This applies to BOMs, measurements, and project details; CSV imports are unchanged.
Existing imported records are not changed automatically.

If an imported BOM has no visible UOM column, `uom` is copied from the measured
size (`material_size`). An existing UOM column takes precedence, including blank
cells. If both are absent/blank, `uom` remains blank. The UOM storage limit is
50 characters to accommodate size text. For a database created before this
change, run `ALTER TABLE project_materials MODIFY COLUMN uom VARCHAR(50);`;
fresh databases already use this limit in `SQL_Setup.sql`.

Sectioned BOMs with SYMBOL and CONTENT columns retain the symbol as the part
identifier when present, or use the adjacent section's description when the
symbol is blank (for example, thread and packaging lines). CONTENT remains the
material field. Repeated section headers and trailing general-instruction
blocks are excluded. Blank color cells stay blank rather than being filled
with the colorway's name.

When no supplier-contact column exists, the importer copies the supplier/vendor
value into `supplier_contact`. An explicit contact column takes precedence,
including blanks. Missing supplier values leave the contact blank too.

BOM imports treat a whole-cell `N/A` as missing (case-insensitive, ignoring
surrounding whitespace). This applies to colorway values too, before any size
or supplier fallback. Text merely containing `N/A` is preserved.

Whole-cell `TBD` is also missing in every imported BOM field, ignoring case
and surrounding spaces. Placeholder normalization happens before supplier-contact
and UOM fallbacks. A missing/hidden contact column uses the normalized supplier
value; a missing supplier cannot provide a contact. These import rules do not
read or update hand-count references. Re-import existing projects to apply them.


For console-only BOM comparisons, run
`./venv/bin/python -m pytest tests/test_bom_hand_counts.py`.
Readable results are displayed without extra options or report files. Differences
are informational, and there are no extra comparison options.
See `tests/HAND_COUNTS.md` for details.
