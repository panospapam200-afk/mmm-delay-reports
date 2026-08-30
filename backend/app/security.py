"""Κρυπτογράφηση κωδικών και έκδοση/επαλήθευση JWT.

Χρησιμοποιείται απευθείας η βιβλιοθήκη ``bcrypt`` αντί για το ``passlib``: το
τελευταίο είναι αδρανές εδώ και χρόνια και σπάει με τις νεότερες εκδόσεις του
``bcrypt``. Ένα επιπλέον επίπεδο αφαίρεσης που δεν συντηρείται είναι ρίσκο, όχι
διευκόλυνση.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import get_settings

__all__ = [
    "BCRYPT_MAX_BYTES",
    "PasswordTooLongError",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]

# Το bcrypt αγνοεί σιωπηλά ό,τι ξεπερνά τα 72 bytes. Σιωπηλή περικοπή κωδικού
# είναι κενό ασφαλείας — δύο διαφορετικοί μακροί κωδικοί θα ταίριαζαν μεταξύ
# τους. Απορρίπτουμε ρητά αντί να περικόπτουμε.
BCRYPT_MAX_BYTES = 72

ALGORITHM = "HS256"


class PasswordTooLongError(ValueError):
    """Ο κωδικός ξεπερνά το όριο που μπορεί να χειριστεί το bcrypt."""


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise PasswordTooLongError(f"Ο κωδικός δεν μπορεί να ξεπερνά τα {BCRYPT_MAX_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        # Κατεστραμμένο ή μη έγκυρο hash στη βάση: αποτυχία ταυτοποίησης,
        # ποτέ σφάλμα 500 που θα αποκάλυπτε πληροφορία στον επιτιθέμενο.
        return False


def create_access_token(subject: int, *, now: datetime, expires_in: timedelta | None = None) -> str:
    """Εκδίδει JWT για τον χρήστη ``subject``.

    Το ``now`` περνάει ως όρισμα — ίδια αρχή με τον πυρήνα: κανένα module δεν
    διαβάζει μόνο του το ρολόι, ώστε τα tests να ελέγχουν και τη λήξη.
    """
    settings = get_settings()
    lifetime = expires_in or timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Επιστρέφει το id του χρήστη, ή ``None`` αν το token δεν είναι έγκυρο.

    Κάθε λόγος αποτυχίας —λήξη, πλαστή υπογραφή, κακοσχηματισμένο περιεχόμενο—
    επιστρέφει το ίδιο αποτέλεσμα. Ο πελάτης δεν χρειάζεται να μάθει *γιατί*
    απέτυχε· ο επιτιθέμενος ακόμη λιγότερο.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None
