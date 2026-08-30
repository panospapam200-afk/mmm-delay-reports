"""Έλεγχος ότι τα migrations συμφωνούν με τα μοντέλα.

Το πιο συνηθισμένο σφάλμα σε έργα με ORM και migrations: κάποιος αλλάζει ένα
μοντέλο και ξεχνά να παράγει migration. Τοπικά όλα δουλεύουν, γιατί η βάση
ανάπτυξης φτιάχτηκε με ``create_all``. Στην παραγωγή η εφαρμογή σκάει, γιατί
εκεί το σχήμα το έφτιαξαν τα migrations.

Αυτό το test ανεβάζει μια καθαρή βάση **μόνο με migrations** και τη συγκρίνει
με τα μοντέλα. Αν αποκλίνουν, το pipeline κοκκινίζει πριν φτάσει η αλλαγή στην
παραγωγή.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

import app.models  # noqa: F401  — καταχώριση των mappers
from app.config import get_settings
from app.db import Base

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Config, str]:
    url = f"sqlite+pysqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))

    yield config, url

    get_settings.cache_clear()


def test_migrations_produce_the_model_schema(alembic_config) -> None:
    config, url = alembic_config
    command.upgrade(config, "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        differences = compare_metadata(context, Base.metadata)
    engine.dispose()

    assert differences == [], (
        "Τα migrations απέκλιναν από τα μοντέλα. Τρέξε: "
        "alembic revision --autogenerate -m '<περιγραφή>'"
    )


def test_migrations_are_reversible(alembic_config) -> None:
    """Ένα migration που δεν γυρίζει πίσω δεν είναι migration — είναι μονόδρομος."""
    config, url = alembic_config
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        differences = compare_metadata(context, Base.metadata)
    engine.dispose()

    # Μετά το downgrade δεν πρέπει να υπάρχει κανένας πίνακας του μοντέλου,
    # άρα κάθε πίνακας εμφανίζεται ως «λείπει».
    added_tables = {diff[1].name for diff in differences if diff[0] == "add_table"}
    assert added_tables == set(Base.metadata.tables)
