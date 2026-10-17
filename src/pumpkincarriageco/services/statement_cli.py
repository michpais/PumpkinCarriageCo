"""Explicit local CLI. Preview never connects to a database or Etsy."""

import argparse
import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pumpkincarriageco.config import StatementSettings
from pumpkincarriageco.ingestion.statements import Preview, StatementError, preview_path
from pumpkincarriageco.repositories.database import make_engine
from pumpkincarriageco.services.statements import (
    accept_previews,
    check_real_database,
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
    parser.add_argument("action", choices=("preview", "init", "import", "report"))
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
            config = Config("alembic.ini")
            config.attributes["database_url"] = settings.database_url
            command.upgrade(config, "head")
            print("Statement schema ready. No source files were imported.")
            return
        if not settings.shop_id:
            raise StatementError("Set PCC_STATEMENTS_SHOP_ID to an internal shop identifier")
        engine = make_engine(settings.database_url)
        try:
            with Session(engine) as session, session.begin():
                check_real_database(session)
                if args.action == "import":
                    results = accept_previews(session, settings.shop_id, previews)
                    output: object = [
                        {
                            "month": result.period.isoformat()[:7],
                            "status": result.status,
                            "rows": result.rows,
                        }
                        for result in results
                    ]
                else:
                    output = monthly_summary(session, settings.shop_id)
            print(json.dumps(output, indent=2))
        finally:
            engine.dispose()
    except StatementError as error:
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
