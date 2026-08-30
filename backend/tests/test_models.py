"""Έλεγχοι του μοντέλου δεδομένων.

Στόχος: να αποδειχθεί ότι οι κανόνες ακεραιότητας επιβάλλονται **στη βάση** και
όχι μόνο στον κώδικα της εφαρμογής. Ένας κανόνας που ζει μόνο σε ένα ``if``
σπάει την πρώτη φορά που δύο αιτήματα φτάνουν ταυτόχρονα.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.reliability import NEUTRAL_WEIGHT
from app.models import (
    MAX_DELAY_MINUTES,
    Confirmation,
    Line,
    Report,
    Stop,
    User,
    UserRole,
    utcnow,
)


class TestUser:
    def test_email_is_unique(self, session: Session, make_user) -> None:
        make_user()
        duplicate = User(email="user1@example.com", password_hash="x")
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_default_role_is_passenger(self, session: Session, make_user) -> None:
        user = make_user()
        assert user.role is UserRole.PASSENGER
        assert user.is_operator is False

    def test_new_user_reliability_is_neutral(self, make_user) -> None:
        assert make_user().reliability == pytest.approx(NEUTRAL_WEIGHT)

    def test_reliability_follows_vote_history(self, make_user) -> None:
        trusted = make_user(confirmations=25, disputes=1)
        distrusted = make_user(confirmations=0, disputes=25)
        assert trusted.reliability > NEUTRAL_WEIGHT > distrusted.reliability

    def test_negative_vote_counts_rejected(self, session: Session) -> None:
        session.add(User(email="bad@example.com", password_hash="x", confirmations_received=-1))
        with pytest.raises(IntegrityError):
            session.commit()


class TestLineAndStops:
    def test_line_code_is_unique(self, session: Session, make_line) -> None:
        make_line(code="550")
        session.add(Line(code="550", name="Άλλη", mode="BUS"))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_stops_are_ordered_by_position(self, make_line) -> None:
        line = make_line(stops=("Πρώτη", "Δεύτερη", "Τρίτη"))
        assert [stop.name for stop in line.stops] == ["Πρώτη", "Δεύτερη", "Τρίτη"]

    def test_two_stops_cannot_share_a_position(self, session: Session, make_line) -> None:
        line = make_line()
        session.add(Stop(name="Διπλή", line_id=line.id, position=0))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_deleting_a_line_removes_its_stops(self, session: Session, make_line) -> None:
        line = make_line(stops=("Α", "Β", "Γ"))
        session.delete(line)
        session.commit()
        assert session.scalars(select(Stop)).all() == []


class TestReport:
    def test_delay_above_upper_bound_rejected(self, session: Session, make_line, make_user) -> None:
        line, author = make_line(), make_user()
        session.add(
            Report(
                line_id=line.id,
                author_id=author.id,
                delay_minutes=MAX_DELAY_MINUTES + 1,
                created_at=utcnow(),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    def test_absurdly_negative_delay_rejected(self, session: Session, make_line, make_user) -> None:
        line, author = make_line(), make_user()
        session.add(
            Report(line_id=line.id, author_id=author.id, delay_minutes=-500, created_at=utcnow())
        )
        with pytest.raises(IntegrityError):
            session.commit()

    def test_small_negative_delay_is_allowed(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        """Όχημα που πέρασε νωρίτερα από το δρομολόγιο είναι έγκυρη αναφορά."""
        report = make_report(line=make_line(), author=make_user(), delay=-4)
        assert report.id is not None

    def test_report_requires_an_existing_line(self, session: Session, make_user) -> None:
        """Απόδειξη ότι τα foreign keys όντως επιβάλλονται στο SQLite."""
        session.add(
            Report(line_id=9999, author_id=make_user().id, delay_minutes=5, created_at=utcnow())
        )
        with pytest.raises(IntegrityError):
            session.commit()

    def test_deleting_a_line_removes_its_reports(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        line = make_line()
        make_report(line=line, author=make_user(), delay=10)
        session.delete(line)
        session.commit()
        assert session.scalars(select(Report)).all() == []


class TestConfirmation:
    def test_one_vote_per_user_per_report(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        report = make_report(line=make_line(), author=make_user(), delay=10)
        voter = make_user()
        session.add(Confirmation(report_id=report.id, user_id=voter.id, agrees=True))
        session.commit()

        session.add(Confirmation(report_id=report.id, user_id=voter.id, agrees=False))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_different_users_can_vote_on_the_same_report(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        report = make_report(line=make_line(), author=make_user(), delay=10)
        session.add(Confirmation(report_id=report.id, user_id=make_user().id, agrees=True))
        session.add(Confirmation(report_id=report.id, user_id=make_user().id, agrees=False))
        session.commit()
        assert len(session.scalars(select(Confirmation)).all()) == 2


class TestTimestamps:
    def test_utcnow_is_naive(self) -> None:
        """Σύμβαση του έργου: naive UTC παντού, ώστε SQLite και PostgreSQL να συμφωνούν."""
        assert utcnow().tzinfo is None
