#!/usr/bin/env python3
"""Import sample tech packs from the local ``files/`` folder into the database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api import create_app
from src.api.extensions import db
from src.api.models import User
from src.api.services.batch_import import import_projects_from_directory
from src.api.services.import_errors import DocumentImportError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        type=Path,
        default=ROOT / "files",
        help="Folder containing Excel/CSV/PDF tech packs (default: RampBackEnd/files)",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="Database user id to attach uploaded file records to",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if db.session.get(User, args.user_id) is None:
            print(f"User id {args.user_id} not found.", file=sys.stderr)
            return 1
        try:
            result = import_projects_from_directory(
                args.directory,
                user_id=args.user_id,
            )
        except DocumentImportError as exc:
            print(exc.message, file=sys.stderr)
            return 1

        for summary in result.imported:
            bom = summary.bom
            meas = summary.measurements
            print(
                f"Project {summary.project_id}: "
                f"fields={len(summary.project_fields_updated)} "
                f"bom_lines={bom.materials_created if bom else 0} "
                f"measurement_points={meas.points_created if meas else 0}"
            )
        for file_name, message in result.errors:
            print(f"FAILED {file_name}: {message}", file=sys.stderr)
        return 1 if result.errors and not result.imported else 0


if __name__ == "__main__":
    raise SystemExit(main())
