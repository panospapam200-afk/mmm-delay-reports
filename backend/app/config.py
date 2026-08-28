"""Ρυθμίσεις εφαρμογής από μεταβλητές περιβάλλοντος.

Καμία τιμή δεν είναι σκληροκωδικοποιημένη στον κώδικα: το Render περνά το
``DATABASE_URL`` ως μεταβλητή περιβάλλοντος, το docker-compose επίσης, και
τοπικά ισχύει η προεπιλογή με SQLite ώστε να τρέχει η εφαρμογή χωρίς στήσιμο.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Προεπιλογή για τοπική ανάπτυξη. Στην παραγωγή δίνεται PostgreSQL URL.
    database_url: str = "sqlite+pysqlite:///./mmm.db"

    # Εμφανίζει τα SQL statements στην κονσόλα. Ποτέ True στην παραγωγή.
    sql_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    """Μονήρες αντικείμενο ρυθμίσεων.

    Η ``lru_cache`` επιτρέπει στα tests να καθαρίσουν την προσωρινή μνήμη με
    ``get_settings.cache_clear()`` όταν χρειάζεται άλλη βάση.
    """
    return Settings()
