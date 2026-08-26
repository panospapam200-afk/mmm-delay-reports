"""Έλεγχοι της μηχανής συνάθροισης — της κρισιμότερης λειτουργίας του συστήματος.

Η είσοδος του συστήματος είναι θορυβώδης εξ ορισμού: άνθρωποι υπερβάλλουν,
κάνουν λάθος ή αναφέρουν κακόβουλα. Τα παρακάτω tests περιγράφουν ακριβώς πώς
ο θόρυβος αυτός εξουδετερώνεται.
"""

from datetime import datetime, timedelta
from itertools import count

import pytest

from app.core.aggregation import (
    LOW_CONFIDENCE_THRESHOLD,
    DelayReport,
    assess_line,
    weighted_median,
)
from app.core.status import LineStatus

NOW = datetime(2026, 9, 15, 8, 30, 0)
LINE_ID = 42

_ids = count(1)


def report(
    delay: float,
    *,
    minutes_ago: float = 0,
    author: int | None = None,
    reliability: float = 1.0,
) -> DelayReport:
    """Βοηθός δημιουργίας αναφοράς. Κάθε κλήση παίρνει νέο id και νέο συντάκτη."""
    report_id = next(_ids)
    return DelayReport(
        id=report_id,
        line_id=LINE_ID,
        author_id=author if author is not None else report_id,
        delay_minutes=delay,
        created_at=NOW - timedelta(minutes=minutes_ago),
        author_reliability=reliability,
    )


class TestInsufficientData:
    """Όταν δεν ξέρουμε, το λέμε. Ποτέ δεν μαντεύουμε κατάσταση γραμμής."""

    def test_no_reports(self) -> None:
        result = assess_line([], NOW)
        assert result.status == LineStatus.UNKNOWN
        assert result.estimated_delay is None
        assert result.confidence == 0.0
        assert result.is_actionable is False

    def test_single_report_is_not_enough(self) -> None:
        result = assess_line([report(12)], NOW)
        assert result.status == LineStatus.UNKNOWN
        assert result.sample_size == 1

    def test_single_report_suffices_when_configured(self) -> None:
        result = assess_line([report(12)], NOW, min_reports=1)
        assert result.status == LineStatus.MINOR
        assert result.estimated_delay == 12.0

    def test_invalid_min_reports_rejected(self) -> None:
        with pytest.raises(ValueError):
            assess_line([], NOW, min_reports=0)


class TestTimeWindow:
    def test_expired_reports_are_ignored(self) -> None:
        """Αναφορά 45 λεπτών πριν περιγράφει άλλο δρομολόγιο."""
        stale = [report(30, minutes_ago=45), report(30, minutes_ago=50)]
        assert assess_line(stale, NOW).status == LineStatus.UNKNOWN

    def test_report_exactly_at_window_edge_is_kept(self) -> None:
        edge = [report(20, minutes_ago=30), report(20, minutes_ago=29)]
        result = assess_line(edge, NOW)
        assert result.sample_size == 2

    def test_future_reports_are_discarded_as_tampered(self) -> None:
        reports = [report(5, minutes_ago=-10), report(5, minutes_ago=-20)]
        assert assess_line(reports, NOW).status == LineStatus.UNKNOWN

    def test_custom_window(self) -> None:
        reports = [report(20, minutes_ago=8), report(20, minutes_ago=9)]
        narrow = assess_line(reports, NOW, window=timedelta(minutes=5))
        assert narrow.status == LineStatus.UNKNOWN


class TestOneVoicePerUser:
    def test_repeat_reports_from_same_author_count_once(self) -> None:
        spam = [
            report(60, minutes_ago=1, author=7),
            report(60, minutes_ago=2, author=7),
            report(60, minutes_ago=3, author=7),
        ]
        result = assess_line(spam, NOW)
        assert result.sample_size == 1
        assert result.status == LineStatus.UNKNOWN

    def test_identical_timestamps_break_ties_deterministically(self) -> None:
        """Δύο αναφορές του ίδιου χρήστη την ίδια στιγμή: κερδίζει η νεότερη εγγραφή."""
        first = report(5, author=7)
        second = report(25, author=7)
        assert second.id > first.id
        result = assess_line([first, second, report(25, author=8)], NOW)
        assert result.sample_size == 2
        assert result.estimated_delay == 25.0

    def test_most_recent_report_of_an_author_wins(self) -> None:
        reports = [
            report(50, minutes_ago=20, author=7),
            report(3, minutes_ago=1, author=7),
            report(3, minutes_ago=1, author=8),
        ]
        result = assess_line(reports, NOW)
        assert result.sample_size == 2
        assert result.estimated_delay == 3.0
        assert result.status == LineStatus.NORMAL


class TestConsensus:
    def test_unanimous_reports_produce_that_value(self) -> None:
        reports = [report(10, minutes_ago=i) for i in range(3)]
        result = assess_line(reports, NOW)
        assert result.estimated_delay == 10.0
        assert result.status == LineStatus.MINOR
        assert result.confidence > LOW_CONFIDENCE_THRESHOLD

    def test_confidence_grows_with_sample_size(self) -> None:
        small = assess_line([report(10), report(10)], NOW)
        large = assess_line([report(10) for _ in range(12)], NOW)
        assert large.confidence > small.confidence

    def test_used_report_ids_are_reported_for_auditability(self) -> None:
        reports = [report(10), report(11), report(9)]
        result = assess_line(reports, NOW)
        assert set(result.used_report_ids) == {r.id for r in reports}
        assert list(result.used_report_ids) == sorted(result.used_report_ids)


class TestOutlierRejection:
    def test_wild_outlier_is_discarded(self) -> None:
        """Ένας που αναφέρει 90 λεπτά ενώ τέσσερις αναφέρουν ~12 δεν παρασύρει την εκτίμηση."""
        reports = [report(10), report(11), report(12), report(13), report(90)]
        result = assess_line(reports, NOW)
        assert result.discarded_as_outliers == 1
        assert result.sample_size == 4
        assert 10.0 <= result.estimated_delay <= 13.0
        assert result.status == LineStatus.MINOR

    def test_two_reports_are_never_treated_as_outliers(self) -> None:
        """Με δύο τιμές δεν υπάρχει έννοια ακραίας τιμής — η μία ορίζει την άλλη."""
        result = assess_line([report(5), report(50)], NOW)
        assert result.discarded_as_outliers == 0

    def test_unanimous_input_discards_nothing(self) -> None:
        reports = [report(7) for _ in range(5)]
        result = assess_line(reports, NOW)
        assert result.discarded_as_outliers == 0
        assert result.estimated_delay == 7.0


class TestWeighting:
    def test_fresh_reports_outweigh_stale_ones(self) -> None:
        """Δύο πρόσφατες αναφορές για 20΄ υπερισχύουν δύο σχεδόν ληγμένων για 2΄."""
        reports = [
            report(20, minutes_ago=0),
            report(20, minutes_ago=1),
            report(2, minutes_ago=25),
            report(2, minutes_ago=26),
        ]
        result = assess_line(reports, NOW)
        assert result.estimated_delay == 20.0

    def test_unreliable_author_cannot_move_the_estimate(self) -> None:
        reports = [
            report(3, reliability=1.0),
            report(3, reliability=1.0),
            report(3, reliability=1.0),
            report(60, reliability=0.25),
        ]
        result = assess_line(reports, NOW)
        assert result.estimated_delay == 3.0
        assert result.status == LineStatus.NORMAL

    def test_all_authors_untrusted_yields_unknown(self) -> None:
        reports = [report(30, reliability=0.0), report(30, reliability=0.0)]
        result = assess_line(reports, NOW)
        assert result.status == LineStatus.UNKNOWN
        assert result.estimated_delay is None


class TestDisagreement:
    def test_wide_disagreement_suppresses_the_status(self) -> None:
        """Δύο χρήστες που διαφωνούν ριζικά δεν παράγουν αξιόπιστη κατάσταση."""
        result = assess_line([report(2), report(40)], NOW)
        assert result.confidence < LOW_CONFIDENCE_THRESHOLD
        assert result.status == LineStatus.UNKNOWN
        # Ο αριθμός υπάρχει για moderation, απλώς δεν παρουσιάζεται ως κατάσταση.
        assert result.estimated_delay is not None

    def test_agreement_beats_disagreement_in_confidence(self) -> None:
        agreeing = assess_line([report(10) for _ in range(4)], NOW)
        disagreeing = assess_line([report(0), report(10), report(20), report(30)], NOW)
        assert agreeing.confidence > disagreeing.confidence


class TestWeightedMedian:
    def test_simple_case_matches_plain_median(self) -> None:
        assert weighted_median([1, 2, 3], [1, 1, 1]) == 2

    def test_even_count_averages_the_middle_pair(self) -> None:
        assert weighted_median([10, 20], [1, 1]) == 15

    def test_weight_shifts_the_result(self) -> None:
        assert weighted_median([10, 20], [9, 1]) == 10

    def test_ignores_input_order(self) -> None:
        assert weighted_median([30, 10, 20], [1, 1, 1]) == weighted_median([10, 20, 30], [1, 1, 1])

    @pytest.mark.parametrize(
        ("values", "weights"),
        [
            ([], []),
            ([1, 2], [1]),
            ([1, 2], [1, -1]),
            ([1, 2], [0, 0]),
        ],
    )
    def test_invalid_input_rejected(self, values: list[float], weights: list[float]) -> None:
        with pytest.raises(ValueError):
            weighted_median(values, weights)
