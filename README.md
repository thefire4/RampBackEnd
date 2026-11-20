# RampCoreOs

Start server with python run.py
Server uses cors and CSRF tokens for security and cookies

## Database setup

Run `SQL_Setup.sql` in MySQL to create the database and tables. 

## BOM line API

- `GET /api/projects` lists all projects with their style, description, stage,
  PO number, project date, total and missing BOM line counts, and integer
  completion percentage. Archived projects are hidden by default; pass
  `archived=true` to list archived projects.
- `POST /api/projects/<project_id>/archive` archives a project, and
  `POST /api/projects/<project_id>/restore` restores it.
- Admins can `DELETE /api/projects/<project_id>` to remove the project and its
  related data and stored files, or
  `DELETE /api/projects/<project_id>/files/<file_id>` to remove one file and its
  source references.
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
- `GET /api/vendors` lists vendors; `POST /api/vendors` creates one with a
  required `name` and optional `contact_name`, `email`, `phone`, and `notes`.
- `GET /api/vendors/<vendor_id>` retrieves a vendor,
  `PATCH /api/vendors/<vendor_id>` edits supplied fields, and
  `DELETE /api/vendors/<vendor_id>` removes it and unlinks its BOM lines.
- `GET /api/vendors/<vendor_id>/bom-lines` lists the vendor's BOM lines with
  project and colorway context. BOM line create/edit endpoints accept a nullable
  `vendor_id`; the legacy `supplier` text remains available independently.
- `POST /api/projects/<project_id>/tasks` creates a task for an incomplete BOM
  line; `GET /api/projects/<project_id>/tasks` lists the project's tasks.
  `PATCH /api/tasks/<task_id>` updates `owner_id`, `status` (`open`,
  `in progress`, or `done`), and/or `due_date` (`YYYY-MM-DD` or null).
  BOM imports create tasks for incomplete lines, and completing a line
  automatically closes its task.

Quantities must be finite numbers greater than or equal to zero. Whitespace-only
values are rejected for required material fields. Each successful create, edit, or
delete records old and new values in `project_change_log` and returns the updated
`missing_bom_items` count. For an existing database, apply
`migrations/001_bom_line_audit.sql`, `migrations/003_project_archiving.sql`, and
`migrations/004_vendors.sql`, and `migrations/005_tasks.sql` if they have not
already been applied. For a fresh database, use `SQL_Setup.sql`.