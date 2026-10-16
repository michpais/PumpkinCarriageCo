from alembic import context

from pumpkincarriageco.config import Settings
from pumpkincarriageco.models import Base
from pumpkincarriageco.repositories.database import make_engine

target_metadata = Base.metadata
url = context.config.attributes.get("database_url") or Settings.from_env().database_url

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
