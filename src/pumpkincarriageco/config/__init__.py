"""Environment-based local configuration; never display database URLs in the UI."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default="sqlite:///data/demo.sqlite3", repr=False)
    shop_id: str = "synthetic-demo"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        shop_id = os.getenv("PCC_SHOP_ID", "synthetic-demo").strip()
        database_url = os.getenv("PCC_DATABASE_URL", "sqlite:///data/demo.sqlite3").strip()
        if not shop_id or not database_url:
            raise ValueError("PCC_SHOP_ID and PCC_DATABASE_URL must not be empty")
        return cls(database_url=database_url, shop_id=shop_id)


@dataclass(frozen=True)
class StatementSettings:
    database_url: str = field(default="sqlite:///data/shop.sqlite3", repr=False)
    shop_id: str = ""

    @classmethod
    def from_env(cls) -> "StatementSettings":
        load_dotenv()
        database_url = os.getenv("PCC_STATEMENTS_DATABASE_URL", "sqlite:///data/shop.sqlite3")
        try:
            url = make_url(database_url)
            demo = make_url(Settings.from_env().database_url)
        except ArgumentError:
            raise ValueError("Invalid database configuration") from None
        if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
            raise ValueError("Statement storage currently requires a local SQLite file")
        target = Path(url.database).resolve()
        demo_target = Path(demo.database).resolve() if demo.database else None
        if target == demo_target or target == Path("data/demo.sqlite3").resolve():
            raise ValueError("Statement storage must be separate from the demo database")
        shop_id = os.getenv("PCC_STATEMENTS_SHOP_ID", "").strip()
        if shop_id == "synthetic-demo" or len(shop_id) > 100:
            raise ValueError("Choose a separate internal shop ID of at most 100 characters")
        return cls(database_url, shop_id)
