from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import create_engine
from app.core.config import settings  # để lấy DB URL từ settings

# Import toàn bộ models để Alembic "biết"
from app.domain.models import Base
from app.domain.models.category import Category
from app.domain.models.product import Product, ProductImage
from app.domain.models.customer import Customer
from app.domain.models.order import Order, OrderItem
from app.domain.models.contact import Contact
from app.domain.models.role import Role
from app.domain.models.user import User
from app.domain.models.shipping_config import ShippingConfig
from app.domain.models.shipping_info import ShippingInfo
from app.domain.models.viettelpost_status_logs import ViettelPostStatusLog

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = settings.DATABASE_URL.replace('+asyncpg', '').replace('?sslmode=require', '')
    print("📡 [OFFLINE] Running migration on DB URL:", url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(settings.DATABASE_URL.replace('+asyncpg', ''))

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
