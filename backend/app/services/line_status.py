"""Υπολογισμός κατάστασης γραμμής από τα δεδομένα της βάσης.

Η μοναδική ευθύνη αυτού του module είναι η **μετάφραση**: φορτώνει εγγραφές
``Report``, τις μετατρέπει σε ``DelayReport`` του πυρήνα μαζί με τον
υπολογισμένο βαθμό αξιοπιστίας του συντάκτη, και παραδίδει τη δουλειά στο
``assess_line()``. Οποιαδήποτε αλλαγή στον αλγόριθμο γίνεται στον πυρήνα, όχι
εδώ.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.aggregation import (
    DEFAULT_MIN_REPORTS,
    DEFAULT_WINDOW,
    DelayReport,
    LineAssessment,
    assess_line,
)
from app.core.ratelimit import DEFAULT_COOLDOWN, RateLimitDecision, check_rate_limit
from app.models import Line, Report

__all__ = [
    "assess",
    "assess_all_lines",
    "check_submission_allowed",
    "recent_submission_times",
]


def _to_core(row: Report) -> DelayReport:
    """ORM -> δομή του πυρήνα. Εδώ «παγώνει» ο βαθμός αξιοπιστίας του συντάκτη."""
    return DelayReport(
        id=row.id,
        line_id=row.line_id,
        author_id=row.author_id,
        delay_minutes=row.delay_minutes,
        created_at=row.created_at,
        author_reliability=row.author.reliability,
    )


def _load_window(session: Session, line_id: int, now: datetime, window: timedelta) -> list[Report]:
    """Φορτώνει τις αναφορές μιας γραμμής μέσα στο χρονικό παράθυρο.

    Το φιλτράρισμα γίνεται και εδώ (για να μη μεταφέρουμε άχρηστες γραμμές από
    τη βάση) και ξανά μέσα στον πυρήνα (γιατί ο πυρήνας δεν εμπιστεύεται τον
    καλούντα). Η διπλή δικλείδα είναι σκόπιμη.
    """
    statement = (
        select(Report)
        .options(joinedload(Report.author))
        .where(Report.line_id == line_id, Report.created_at >= now - window)
    )
    return list(session.scalars(statement).unique())


def assess(
    session: Session,
    line_id: int,
    now: datetime,
    *,
    window: timedelta = DEFAULT_WINDOW,
    min_reports: int = DEFAULT_MIN_REPORTS,
) -> LineAssessment:
    """Η τρέχουσα κατάσταση μιας γραμμής."""
    rows = _load_window(session, line_id, now, window)
    return assess_line([_to_core(row) for row in rows], now, window=window, min_reports=min_reports)


def assess_all_lines(
    session: Session, now: datetime, *, window: timedelta = DEFAULT_WINDOW
) -> list[tuple[Line, LineAssessment]]:
    """Κατάσταση όλων των γραμμών, για τη λίστα του επιβάτη και το dashboard.

    Ταξινομείται με τις πιο προβληματικές γραμμές πρώτες· οι γραμμές χωρίς
    επαρκή δεδομένα πάνε στο τέλος, γιατί «άγνωστο» δεν είναι «σοβαρό».
    """
    lines = list(session.scalars(select(Line).order_by(Line.code)))
    results = [(line, assess(session, line.id, now, window=window)) for line in lines]
    return sorted(
        results,
        key=lambda pair: (
            pair[1].estimated_delay is None,
            -(pair[1].estimated_delay or 0.0),
        ),
    )


def recent_submission_times(
    session: Session,
    user_id: int,
    line_id: int,
    now: datetime,
    *,
    window: timedelta = DEFAULT_COOLDOWN,
) -> list[datetime]:
    """Χρόνοι προηγούμενων υποβολών του χρήστη για τη γραμμή, μέσα στο παράθυρο."""
    statement = select(Report.created_at).where(
        Report.author_id == user_id,
        Report.line_id == line_id,
        Report.created_at >= now - window,
    )
    return list(session.scalars(statement))


def check_submission_allowed(
    session: Session,
    user_id: int,
    line_id: int,
    now: datetime,
    *,
    window: timedelta = DEFAULT_COOLDOWN,
) -> RateLimitDecision:
    """Επιτρέπεται νέα αναφορά αυτού του χρήστη για αυτή τη γραμμή;"""
    history = recent_submission_times(session, user_id, line_id, now, window=window)
    return check_rate_limit(history, now, window=window)
