"""Ρύθμιση περιβάλλοντος Alembic.

Το URL της βάσης **δεν** διαβάζεται από το ``alembic.ini`` αλλά από τις
ρυθμίσεις της εφαρμογής, ώστε migrations και εφαρμογή να μιλούν πάντα στην ίδια
βάση — τοπικά, στο docker-compose και στο Render, χωρίς τρία διαφορετικά
αρχεία ρυθμίσεων που πρέπει να μένουν συγχρονισμένα.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  — καταχώριση των mappers στο Base.metadata
from app.config import get_settings
from app.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Παράγει SQL χωρίς σύνδεση — χρήσιμο για έλεγχο πριν την εκτέλεση."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Το SQLite δεν υποστηρίζει ALTER TABLE για περιορισμούς· το batch
            # mode ξαναχτίζει τον πίνακα. Αδιάφορο για PostgreSQL, απαραίτητο
            # για να τρέχουν τα ίδια migrations και στα δύο.
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
