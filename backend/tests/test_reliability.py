"""Έλεγχοι βαθμού αξιοπιστίας χρήστη."""

import pytest

from app.core.reliability import (
    MAX_WEIGHT,
    MIN_WEIGHT,
    NEUTRAL_WEIGHT,
    compute_reliability,
    is_suspected_spammer,
)


class TestComputeReliability:
    def test_new_user_starts_neutral(self) -> None:
        """Χρήστης χωρίς ιστορικό δεν πρέπει ούτε να ευνοείται ούτε να τιμωρείται."""
        assert compute_reliability(0, 0) == pytest.approx(NEUTRAL_WEIGHT)

    def test_stays_within_bounds(self) -> None:
        for confirmations, disputes in [(0, 0), (0, 1000), (1000, 0), (7, 3), (1, 1)]:
            weight = compute_reliability(confirmations, disputes)
            assert MIN_WEIGHT <= weight <= MAX_WEIGHT

    def test_confirmations_increase_weight(self) -> None:
        assert compute_reliability(10, 0) > compute_reliability(1, 0) > NEUTRAL_WEIGHT

    def test_disputes_decrease_weight(self) -> None:
        assert compute_reliability(0, 10) < compute_reliability(0, 1) < NEUTRAL_WEIGHT

    def test_single_dispute_does_not_silence_a_good_user(self) -> None:
        """Η εξομάλυνση Laplace προστατεύει από μία άδικη διάψευση."""
        seasoned = compute_reliability(20, 1)
        assert seasoned > NEUTRAL_WEIGHT

    def test_ratio_alone_is_not_enough_evidence(self) -> None:
        """Ίδιος λόγος, περισσότερα στοιχεία -> πιο ακραίος βαθμός."""
        weak_evidence = compute_reliability(1, 0)
        strong_evidence = compute_reliability(50, 0)
        assert strong_evidence > weak_evidence

    @pytest.mark.parametrize(("confirmations", "disputes"), [(-1, 0), (0, -1), (-5, -5)])
    def test_negative_counts_rejected(self, confirmations: int, disputes: int) -> None:
        with pytest.raises(ValueError):
            compute_reliability(confirmations, disputes)


class TestSpammerDetection:
    def test_requires_minimum_evidence(self) -> None:
        """Μία ή δύο διαψεύσεις δεν αρκούν για να χαρακτηριστεί κάποιος spammer."""
        assert is_suspected_spammer(0, 2) is False

    def test_flags_consistently_disputed_user(self) -> None:
        assert is_suspected_spammer(0, 12) is True

    def test_does_not_flag_reliable_user(self) -> None:
        assert is_suspected_spammer(30, 2) is False
