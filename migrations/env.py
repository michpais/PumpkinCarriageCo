from alembic import context
from sqlalchemy import Connection

from pumpkincarriageco.config import Settings
from pumpkincarriageco.models import Base
from pumpkincarriageco.repositories.database import make_engine

target_metadata = Base.metadata
url = context.config.attributes.get("database_url") or Settings.from_env().database_url


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    run_migrations(context.config.attributes["connection"])
else:
    engine = make_engine(url)
    with engine.connect() as connection:
        run_migrations(connection)
    engine.dispose()
