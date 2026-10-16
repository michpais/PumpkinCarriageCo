"""Environment-based local configuration; never display database URLs in the UI."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


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
