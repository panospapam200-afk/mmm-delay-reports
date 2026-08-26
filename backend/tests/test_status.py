"""Έλεγχοι ταξινόμησης κατάστασης γραμμής.

Έμφαση στις *οριακές* τιμές: εκεί κρύβονται τα σφάλματα off-by-one σε κάθε
σύστημα με κατώφλια.
"""

import pytest

from app.core.status import (
    MINOR_THRESHOLD_MINUTES,
    SEVERE_THRESHOLD_MINUTES,
    LineStatus,
    classify,
)


class TestClassifyBoundaries:
    """Τα όρια είναι κλειστά από κάτω: 5.0 είναι ήδη MINOR, 15.0 ήδη SEVERE."""

    @pytest.mark.parametrize(
        ("delay", "expected"),
        [
            (0.0, LineStatus.NORMAL),
            (4.99, LineStatus.NORMAL),
            (5.0, LineStatus.MINOR),
            (5.01, LineStatus.MINOR),
            (14.99, LineStatus.MINOR),
            (15.0, LineStatus.SEVERE),
            (15.01, LineStatus.SEVERE),
            (120.0, LineStatus.SEVERE),
        ],
    )
    def test_thresholds(self, delay: float, expected: LineStatus) -> None:
        assert classify(delay) == expected

    def test_thresholds_are_consistent_with_constants(self) -> None:
        assert classify(MINOR_THRESHOLD_MINUTES) == LineStatus.MINOR
        assert classify(SEVERE_THRESHOLD_MINUTES) == LineStatus.SEVERE
        assert MINOR_THRESHOLD_MINUTES < SEVERE_THRESHOLD_MINUTES


class TestClassifyEdgeCases:
    def test_none_is_unknown(self) -> None:
        assert classify(None) == LineStatus.UNKNOWN

    def test_negative_delay_is_normal_operation(self) -> None:
        """Όχημα που πέρασε νωρίτερα δεν είναι σφάλμα — είναι κανονική λειτουργία."""
        assert classify(-3.0) == LineStatus.NORMAL


class TestGreekLabels:
    def test_every_status_has_a_label(self) -> None:
        for status in LineStatus:
            assert status.label_el
            assert isinstance(status.label_el, str)

    def test_labels_are_distinct(self) -> None:
        labels = {status.label_el for status in LineStatus}
        assert len(labels) == len(LineStatus)
