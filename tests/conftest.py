from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from pumpkincarriageco.repositories.database import make_engine


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.sqlite3'}"


@pytest.fixture
def migration_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture
def engine(migration_config: Config):
    command.upgrade(migration_config, "head")
    engine = make_engine(migration_config.attributes["database_url"])
    yield engine
    engine.dispose()
