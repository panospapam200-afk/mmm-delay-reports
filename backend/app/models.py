"""Μοντέλα ORM.

Σχέσεις:

    User ──1:N──> Report ──N:1──> Line ──1:N──> Stop
     │              │
     │              └──1:N──> Confirmation
     └──1:N──> Confirmation

Σχεδιαστική απόφαση: **ο βαθμός αξιοπιστίας δεν αποθηκεύεται.** Αποθηκεύονται
μόνο τα σωρευτικά πλήθη επιβεβαιώσεων και διαψεύσεων, και ο βαθμός υπολογίζεται
τη στιγμή της συνάθροισης από το ``app/core/reliability.py``. Έτσι μια αλλαγή
στον τύπο υπολογισμού ισχύει αναδρομικά, χωρίς migration και χωρίς κίνδυνο να
μείνουν ασυνεπείς αποθηκευμένες τιμές.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.reliability import compute_reliability
from app.db import Base

# Λογικά όρια τιμής αναφοράς. Πέρα από αυτά η αναφορά είναι σχεδόν βέβαια
# λάθος πληκτρολόγησης ή κακόβουλη — απορρίπτεται στο επίπεδο της βάσης, όχι
# μόνο στο επίπεδο της εφαρμογής.
MIN_DELAY_MINUTES = -30.0
MAX_DELAY_MINUTES = 180.0


def utcnow() -> datetime:
    """Τρέχουσα ώρα UTC **χωρίς ζώνη ώρας**.

    Σύμβαση του έργου: κάθε χρονοσήμανση αποθηκεύεται ως naive UTC. Ο λόγος
    είναι πρακτικός — το SQLite (που χρησιμοποιούν τα tests) δεν διατηρεί
    πληροφορία ζώνης ώρας, ενώ η PostgreSQL (που χρησιμοποιεί η παραγωγή) τη
    διατηρεί. Αν αφήναμε τη διαφορά ανοιχτή, τα tests θα σύγκριναν naive με
    aware χρόνους και θα έσπαγαν μόνο στην παραγωγή. Μία σύμβαση παντού είναι
    προτιμότερη από δύο συμπεριφορές.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class TransportMode(StrEnum):
    BUS = "BUS"
    TROLLEY = "TROLLEY"
    METRO = "METRO"
    TRAM = "TRAM"
    SUBURBAN = "SUBURBAN"


class UserRole(StrEnum):
    PASSENGER = "PASSENGER"
    OPERATOR = "OPERATOR"


class ReportCategory(StrEnum):
    DELAY = "DELAY"  # Το όχημα αργεί
    NO_SHOW = "NO_SHOW"  # Το δρομολόγιο δεν εκτελέστηκε καθόλου
    OVERCROWDED = "OVERCROWDED"  # Ήρθε αλλά δεν χωρούσε επιβάτες


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.PASSENGER
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow)

    # Σωρευτικά πλήθη ψήφων που έλαβαν οι αναφορές αυτού του χρήστη.
    confirmations_received: Mapped[int] = mapped_column(Integer, default=0)
    disputes_received: Mapped[int] = mapped_column(Integer, default=0)

    reports: Mapped[list[Report]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    votes: Mapped[list[Confirmation]] = relationship(
        back_populates="voter", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("confirmations_received >= 0", name="ck_users_confirmations_non_negative"),
        CheckConstraint("disputes_received >= 0", name="ck_users_disputes_non_negative"),
    )

    @property
    def reliability(self) -> float:
        """Πολλαπλασιαστής βαρύτητας, υπολογισμένος — ποτέ αποθηκευμένος."""
        return compute_reliability(self.confirmations_received, self.disputes_received)

    @property
    def is_operator(self) -> bool:
        return self.role is UserRole.OPERATOR


class Line(Base):
    __tablename__ = "lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    mode: Mapped[TransportMode] = mapped_column(Enum(TransportMode, native_enum=False, length=20))

    stops: Mapped[list[Stop]] = relationship(
        back_populates="line", cascade="all, delete-orphan", order_by="Stop.position"
    )
    reports: Mapped[list[Report]] = relationship(
        back_populates="line", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Line {self.code}: {self.name}>"


class Stop(Base):
    __tablename__ = "stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    line_id: Mapped[int] = mapped_column(ForeignKey("lines.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)

    line: Mapped[Line] = relationship(back_populates="stops")

    __table_args__ = (
        # Δύο στάσεις της ίδιας γραμμής δεν μπορούν να έχουν την ίδια σειρά.
        UniqueConstraint("line_id", "position", name="uq_stops_line_position"),
        CheckConstraint("position >= 0", name="ck_stops_position_non_negative"),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("lines.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stop_id: Mapped[int | None] = mapped_column(
        ForeignKey("stops.id", ondelete="SET NULL"), nullable=True
    )

    delay_minutes: Mapped[float] = mapped_column(Float)
    category: Mapped[ReportCategory] = mapped_column(
        Enum(ReportCategory, native_enum=False, length=20), default=ReportCategory.DELAY
    )
    note: Mapped[str | None] = mapped_column(String(280), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, index=True
    )

    line: Mapped[Line] = relationship(back_populates="reports")
    author: Mapped[User] = relationship(back_populates="reports")
    confirmations: Mapped[list[Confirmation]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            f"delay_minutes >= {MIN_DELAY_MINUTES} AND delay_minutes <= {MAX_DELAY_MINUTES}",
            name="ck_reports_delay_within_bounds",
        ),
    )


class Confirmation(Base):
    """Ψήφος επιβεβαίωσης ή διάψευσης σε υπάρχουσα αναφορά."""

    __tablename__ = "confirmations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    agrees: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow)

    report: Mapped[Report] = relationship(back_populates="confirmations")
    voter: Mapped[User] = relationship(back_populates="votes")

    __table_args__ = (
        # Μία ψήφος ανά χρήστη ανά αναφορά. Ο κανόνας επιβάλλεται στη βάση:
        # ένας έλεγχος μόνο στην εφαρμογή θα έσπαγε σε ταυτόχρονα αιτήματα.
        UniqueConstraint("report_id", "user_id", name="uq_confirmations_report_user"),
    )
