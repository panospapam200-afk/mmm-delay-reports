"""Έλεγχοι ρυθμίσεων — με έμφαση στο URL της βάσης.

Το test αυτού του module υπάρχει για έναν συγκεκριμένο λόγο: το σφάλμα που
αποτρέπει εμφανίζεται **μόνο στην παραγωγή**. Τοπικά και στα tests τρέχει
SQLite, οπότε ένα λάθος στη μετατροπή του URL της PostgreSQL δεν θα φαινόταν
ποτέ πριν το deployment.
"""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings, normalize_database_url


class TestNormalizeDatabaseUrl:
    @pytest.mark.parametrize(
        "given",
        [
            "postgres://user:pass@host:5432/db",
            "postgresql://user:pass@host:5432/db",
        ],
    )
    def test_adds_the_psycopg_driver(self, given: str) -> None:
        """Το Render δίνει postgres:// — το SQLAlchemy 2 απαιτεί ρητό οδηγό."""
        result = normalize_database_url(given)
        assert result.startswith("postgresql+psycopg://")
        assert result.endswith("user:pass@host:5432/db")

    def test_leaves_an_explicit_driver_alone(self) -> None:
        given = "postgresql+psycopg://user:pass@host:5432/db"
        assert normalize_database_url(given) == given

    def test_leaves_sqlite_alone(self) -> None:
        given = "sqlite+pysqlite:///./mmm.db"
        assert normalize_database_url(given) == given

    def test_credentials_survive_the_rewrite(self) -> None:
        """Λάθος στη μετατροπή θα έσπαγε σιωπηλά την ταυτοποίηση στη βάση."""
        given = "postgres://mmm_user:p%40ssw0rd@dpg-abc.frankfurt-postgres.render.com/mmm"
        assert normalize_database_url(given) == (
            "postgresql+psycopg://mmm_user:p%40ssw0rd@dpg-abc.frankfurt-postgres.render.com/mmm"
        )


class TestSettings:
    def test_normalization_applies_through_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")
        settings = Settings()
        assert settings.database_url.startswith("postgresql+psycopg://")

    def test_defaults_are_safe_for_local_development(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.database_url.startswith("sqlite")
        assert settings.sql_echo is False

    def test_get_settings_is_cached(self) -> None:
        assert get_settings() is get_settings()
