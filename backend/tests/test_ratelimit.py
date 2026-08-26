"""Έλεγχοι περιορισμού ρυθμού υποβολής."""

from datetime import datetime, timedelta

import pytest

from app.core.ratelimit import DEFAULT_COOLDOWN, check_rate_limit

NOW = datetime(2026, 9, 15, 8, 30, 0)


class TestFirstSubmission:
    def test_no_history_is_allowed(self) -> None:
        decision = check_rate_limit([], NOW)
        assert decision.allowed is True
        assert decision.retry_after_seconds == 0
        assert bool(decision) is True


class TestCooldown:
    def test_second_submission_within_window_blocked(self) -> None:
        decision = check_rate_limit([NOW - timedelta(minutes=3)], NOW)
        assert decision.allowed is False
        assert decision.reports_in_window == 1

    def test_retry_after_counts_down(self) -> None:
        decision = check_rate_limit([NOW - timedelta(minutes=4)], NOW)
        # Απομένουν 6 λεπτά από το παράθυρο των 10.
        assert decision.retry_after_seconds == 6 * 60

    def test_submission_exactly_at_window_edge_is_allowed(self) -> None:
        """Το παράθυρο είναι ανοιχτό από πάνω: στα ακριβώς 10 λεπτά ελευθερώνεται."""
        decision = check_rate_limit([NOW - DEFAULT_COOLDOWN], NOW)
        assert decision.allowed is True

    def test_old_submissions_do_not_count(self) -> None:
        history = [NOW - timedelta(hours=3), NOW - timedelta(minutes=45)]
        assert check_rate_limit(history, NOW).allowed is True

    def test_retry_after_is_never_zero_when_blocked(self) -> None:
        """Στρογγυλοποίηση προς τα πάνω: ο πελάτης δεν πρέπει να ξαναπροσπαθήσει αμέσως."""
        almost_expired = NOW - DEFAULT_COOLDOWN + timedelta(milliseconds=200)
        decision = check_rate_limit([almost_expired], NOW)
        assert decision.allowed is False
        assert decision.retry_after_seconds >= 1


class TestHigherLimits:
    def test_allows_up_to_max_reports(self) -> None:
        history = [NOW - timedelta(minutes=2)]
        assert check_rate_limit(history, NOW, max_reports=3).allowed is True

    def test_blocks_after_max_reports(self) -> None:
        history = [
            NOW - timedelta(minutes=1),
            NOW - timedelta(minutes=2),
            NOW - timedelta(minutes=3),
        ]
        decision = check_rate_limit(history, NOW, max_reports=3)
        assert decision.allowed is False
        assert decision.reports_in_window == 3

    def test_unordered_history_is_handled(self) -> None:
        """Το ιστορικό μπορεί να φτάσει σε οποιαδήποτε σειρά από τη βάση."""
        history = [
            NOW - timedelta(minutes=3),
            NOW - timedelta(minutes=1),
            NOW - timedelta(minutes=2),
        ]
        decision = check_rate_limit(history, NOW, max_reports=2)
        assert decision.allowed is False
        # Δεσμευτική είναι η δεύτερη νεότερη (πριν 2 λεπτά) -> απομένουν 8 λεπτά.
        assert decision.retry_after_seconds == 8 * 60

    def test_invalid_max_reports_rejected(self) -> None:
        with pytest.raises(ValueError):
            check_rate_limit([], NOW, max_reports=0)


class TestClockSkew:
    def test_future_submissions_are_ignored(self) -> None:
        """Χρόνος στο μέλλον σημαίνει αλλοιωμένα δεδομένα, όχι έγκυρο ιστορικό."""
        decision = check_rate_limit([NOW + timedelta(minutes=5)], NOW)
        assert decision.allowed is True
