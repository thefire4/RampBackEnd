# RampCoreOs

Start server with python run.py
Server uses cors and CSRF tokens for security and cookies

## BOM line API

- `GET /api/projects` lists all projects with their style, description, stage,
  PO number, project date, total and missing BOM line counts, and integer
  completion percentage.
- `GET /api/projects/<project_id>` returns one project's overview, colorways,
  BOM lines, files, and the same completeness counts. Projects with no BOM
  lines report `0` percent complete.
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