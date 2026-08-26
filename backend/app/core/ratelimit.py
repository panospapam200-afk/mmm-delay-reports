"""Περιορισμός ρυθμού υποβολής αναφορών.

Ένας χρήστης μπορεί να υποβάλει το πολύ ``max_reports`` αναφορές για την ίδια
γραμμή μέσα σε ``window``. Χωρίς αυτό, ένας μόνο κακόβουλος χρήστης θα μπορούσε
να κατακλύσει τη μηχανή συνάθροισης.

Καθαρή συνάρτηση: το ιστορικό υποβολών και η τρέχουσα ώρα περνούν ως ορίσματα.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

__all__ = ["RateLimitDecision", "DEFAULT_COOLDOWN", "DEFAULT_MAX_REPORTS", "check_rate_limit"]

DEFAULT_COOLDOWN = timedelta(minutes=10)
DEFAULT_MAX_REPORTS = 1


@dataclass(frozen=True)
class RateLimitDecision:
    """Το αποτέλεσμα του ελέγχου, έτοιμο για μετατροπή σε HTTP 429."""

    allowed: bool
    retry_after_seconds: int = 0
    reports_in_window: int = 0

    def __bool__(self) -> bool:
        return self.allowed


def check_rate_limit(
    previous_submissions: list[datetime],
    now: datetime,
    *,
    window: timedelta = DEFAULT_COOLDOWN,
    max_reports: int = DEFAULT_MAX_REPORTS,
) -> RateLimitDecision:
    """Ελέγχει αν επιτρέπεται νέα υποβολή.

    :param previous_submissions: χρόνοι προηγούμενων υποβολών του ίδιου χρήστη
        για την ίδια γραμμή (σε οποιαδήποτε σειρά).
    :param now: η στιγμή της νέας υποβολής.
    :param window: το κυλιόμενο παράθυρο.
    :param max_reports: πόσες υποβολές επιτρέπονται μέσα στο παράθυρο.

    Το ``retry_after_seconds`` στρογγυλοποιείται προς τα πάνω, ώστε ο πελάτης
    που περιμένει ακριβώς τόσο να μην απορριφθεί ξανά από στρογγυλοποίηση.
    """
    if max_reports < 1:
        raise ValueError("Το max_reports πρέπει να είναι τουλάχιστον 1")

    in_window = sorted(ts for ts in previous_submissions if timedelta(0) <= now - ts < window)

    if len(in_window) < max_reports:
        return RateLimitDecision(allowed=True, reports_in_window=len(in_window))

    # Το παράθυρο ελευθερώνεται όταν λήξει η παλαιότερη υποβολή που το γεμίζει.
    blocking = in_window[-max_reports]
    remaining = (blocking + window) - now
    return RateLimitDecision(
        allowed=False,
        retry_after_seconds=max(1, math.ceil(remaining.total_seconds())),
        reports_in_window=len(in_window),
    )
