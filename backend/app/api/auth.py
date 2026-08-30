"""Endpoints λογαριασμών: εγγραφή, σύνδεση, στοιχεία τρέχοντος χρήστη."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.models import User, utcnow
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: DbSession) -> User:
    """Δημιουργία λογαριασμού επιβάτη.

    Ο ρόλος χειριστή **δεν** δίνεται από αυτό το endpoint — θα ήταν κλιμάκωση
    δικαιωμάτων με μία γραμμή JSON. Αποδίδεται μόνο από τον διαχειριστή της
    βάσης.
    """
    existing = session.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Υπάρχει ήδη λογαριασμός με αυτό το email.",
        )

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    """Σύνδεση με email και κωδικό.

    Λάθος email και λάθος κωδικός επιστρέφουν **το ίδιο** μήνυμα, ώστε να μην
    μπορεί κανείς να διαπιστώσει ποια emails είναι εγγεγραμμένα.
    """
    user = session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Λανθασμένο email ή κωδικός.",
        )

    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user.id, now=utcnow()),
        expires_in_minutes=settings.jwt_expire_minutes,
    )


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user
