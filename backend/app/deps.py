"""Εξαρτήσεις FastAPI: συνεδρία βάσης, τρέχων χρήστης, έλεγχος ρόλου."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.security import decode_access_token

__all__ = ["CurrentUser", "DbSession", "OperatorUser", "get_current_user", "require_operator"]

# auto_error=False ώστε να παράγουμε εμείς το μήνυμα, στα ελληνικά και ενιαίο
# με τα υπόλοιπα σφάλματα του API.
_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_session)]

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Απαιτείται έγκυρη σύνδεση.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    """Ο συνδεδεμένος χρήστης, ή 401.

    Όλες οι αιτίες αποτυχίας —απόν token, ληγμένο, πλαστό, χρήστης που
    διαγράφηκε— δίνουν την ίδια απόκριση. Διαφορετικά μηνύματα θα επέτρεπαν
    σε επιτιθέμενο να απαριθμήσει λογαριασμούς.
    """
    if credentials is None:
        raise _CREDENTIALS_ERROR

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise _CREDENTIALS_ERROR

    user = session.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_ERROR

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_operator(user: CurrentUser) -> User:
    """Περιορίζει ένα endpoint στους χειριστές του φορέα.

    Επιστρέφει 403 και όχι 404: ο χρήστης είναι ταυτοποιημένος, απλώς δεν έχει
    δικαίωμα. Το να κρύβαμε την ύπαρξη του endpoint δεν προσθέτει ασφάλεια εδώ,
    αφού είναι δημοσιευμένο στο OpenAPI schema.
    """
    if not user.is_operator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Απαιτείται ρόλος χειριστή.",
        )
    return user


OperatorUser = Annotated[User, Depends(require_operator)]
