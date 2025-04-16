import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# モデルのインポート
from app.db.base import Base
from app.models.user import AuthUser  # 他のモデルも必要に応じてインポート
from app.core.config import settings

# alembic.iniからの設定
config = context.config

# 環境変数からの設定を上書き
section = config.config_ini_section
config.set_section_option(section, "POSTGRES_USER", settings.POSTGRES_USER)
config.set_section_option(section, "POSTGRES_PASSWORD", settings.POSTGRES_PASSWORD)
config.set_section_option(section, "POSTGRES_HOST", settings.POSTGRES_HOST)
config.set_section_option(section, "POSTGRES_PORT", settings.POSTGRES_PORT)
config.set_section_option(section, "POSTGRES_DB", settings.POSTGRES_DB)

# ロギング設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# メタデータオブジェクトの設定
target_metadata = Base.metadata

# その他の設定
def run_migrations_offline() -> None:
    """オフラインマイグレーションの実行"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """オンラインマイグレーションの実行"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
