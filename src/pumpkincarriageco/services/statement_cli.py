"""Explicit local CLI. Preview never connects to a database or Etsy."""

import argparse
import json
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pumpkincarriageco.analytics.statement_fees import preview_fee_summary
from pumpkincarriageco.config import StatementSettings
from pumpkincarriageco.ingestion.statements import (
    Preview,
    StatementError,
    category_label,
    preview_path,
)
from pumpkincarriageco.repositories.database import make_engine
from pumpkincarriageco.services.backups import BackupError, create_backup
from pumpkincarriageco.services.statement_operations import import_statements, initialize_statements
from pumpkincarriageco.services.statements import (
    check_real_database,
    monthly_fee_summary,
    monthly_summary,
)


def scan(directory: Path) -> list[Preview]:
    if not directory.is_dir():
        raise StatementError("Statement directory is unavailable")
    paths = sorted(directory.glob("*.csv"))
    if not paths:
        raise StatementError("No CSV files found")
    return [preview_path(path) for path in paths]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "init", "import", "report", "backup"))
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--confirm", action="store_true", help="Accept validated local imports")
    args = parser.parse_args()
    try:
        previews: list[Preview] = []
        if args.action in ("preview", "import"):
            if args.directory is None:
                raise StatementError("Supply --directory")
            previews = scan(args.directory)
            print(
                json.dumps(
                    [
                        {
                            "month": item.period.isoformat()[:7],
                            "rows": len(item.rows),
                            "valid": item.valid,
                            "file_hash": item.file_hash,
                            "fee_subtypes": preview_fee_summary(item),
                            "issues": [
                                {"row": issue.row, "code": issue.code, "blocking": issue.blocking}
                                for issue in item.issues
                            ],
                        }
                        for item in sorted(previews, key=lambda item: item.period)
                    ],
                    indent=2,
                )
            )
            if not all(item.valid for item in previews):
                raise StatementError("Validation failed; no import performed")
            if args.action == "preview":
                return
            if not args.confirm:
                raise StatementError("Review preview first, then pass --confirm to import")
        settings = StatementSettings.from_env()
        if args.action == "init":
            backup = initialize_statements(settings)
            if backup:
                print(f"Pre-migration backup verified: {settings.backup_dir / backup.filename}")
            print("Statement schema ready. No source files were imported.")
            return
        if args.action == "backup":
            backup = create_backup(settings.database_url, settings.backup_dir)
            print(f"Backup verified: {settings.backup_dir / backup.filename}")
            return
        if not settings.shop_id:
            raise StatementError("Set PCC_STATEMENTS_SHOP_ID to an internal shop identifier")
        if args.action == "import":
            results = import_statements(settings, previews)
            print(
                json.dumps(
                    [
                        {
                            "month": result.period.isoformat()[:7],
                            "status": result.status,
                            "rows": result.rows,
                            "classified_fees": result.classified_fees,
                        }
                        for result in results
                    ],
                    indent=2,
                )
            )
            return
        engine = make_engine(settings.database_url)
        try:
            with Session(engine) as session, session.begin():
                check_real_database(session)
                output = {
                    "monthly_categories": [
                        row | {"category": category_label(str(row["category"]))}
                        for row in monthly_summary(session, settings.shop_id)
                    ],
                    "fee_subtypes": monthly_fee_summary(session, settings.shop_id),
                }
            print(json.dumps(output, indent=2))
        finally:
            engine.dispose()
    except (StatementError, BackupError) as error:
        parser.exit(1, f"{error}. No source files were changed.\n")
    except (ValueError, OSError, SQLAlchemyError):
        # Do not print raw exception/arguments: SQL errors can include IDs and connection URLs.
        parser.exit(
            1,
            "Operation failed. Check validation, configuration, schema, and month conflicts. "
            "No source files were changed.\n",
        )


if __name__ == "__main__":
    main()
