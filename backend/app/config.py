"""Ρυθμίσεις εφαρμογής από μεταβλητές περιβάλλοντος.

Καμία τιμή δεν είναι σκληροκωδικοποιημένη στον κώδικα: το Render περνά το
``DATABASE_URL`` ως μεταβλητή περιβάλλοντος, το docker-compose επίσης, και
τοπικά ισχύει η προεπιλογή με SQLite ώστε να τρέχει η εφαρμογή χωρίς στήσιμο.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings", "normalize_database_url"]

# Οι πάροχοι φιλοξενίας (Render, Heroku, Railway) δίνουν URL της μορφής
# postgres:// ή postgresql://. Το SQLAlchemy 2 όμως χρειάζεται ρητά τον οδηγό:
# postgresql+psycopg://. Χωρίς μετατροπή, η εφαρμογή σκάει στην εκκίνηση με
# «Can't load plugin: sqlalchemy.dialects:postgres» — και σκάει ΜΟΝΟ στην
# παραγωγή, γιατί τοπικά τρέχει SQLite.
_POSTGRES_PREFIXES = ("postgres://", "postgresql://")


def normalize_database_url(url: str) -> str:
    """Προσθέτει τον οδηγό psycopg σε URL της PostgreSQL, αν λείπει."""
    for prefix in _POSTGRES_PREFIXES:
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Προεπιλογή για τοπική ανάπτυξη. Στην παραγωγή δίνεται PostgreSQL URL.
    database_url: str = "sqlite+pysqlite:///./mmm.db"

    # Εμφανίζει τα SQL statements στην κονσόλα. Ποτέ True στην παραγωγή.
    sql_echo: bool = False

    # ⚠️ Η προεπιλογή είναι ΜΟΝΟ για τοπική ανάπτυξη. Στην παραγωγή ορίζεται
    # μέσω μεταβλητής περιβάλλοντος JWT_SECRET και δεν βρίσκεται πουθενά στο
    # repository. Ένα μυστικό μέσα στον κώδικα δεν είναι μυστικό.
    jwt_secret: str = "dev-only-insecure-secret-change-in-production"
    jwt_expire_minutes: int = 60 * 24

    @field_validator("database_url")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_database_url(value)


@lru_cache
def get_settings() -> Settings:
    """Μονήρες αντικείμενο ρυθμίσεων.

    Η ``lru_cache`` επιτρέπει στα tests να καθαρίσουν την προσωρινή μνήμη με
    ``get_settings.cache_clear()`` όταν χρειάζεται άλλη βάση.
    """
    return Settings()
