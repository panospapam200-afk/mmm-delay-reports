"""Έλεγχοι της υπηρεσίας που ενώνει βάση και πυρήνα.

Τα tests του ``app/core/`` αποδεικνύουν ότι ο αλγόριθμος είναι σωστός. Αυτά εδώ
αποδεικνύουν κάτι διαφορετικό και εξίσου απαραίτητο: ότι τα **πραγματικά
δεδομένα της βάσης** φτάνουν στον αλγόριθμο σωστά μεταφρασμένα — ιδίως ο
βαθμός αξιοπιστίας, που δεν αποθηκεύεται αλλά υπολογίζεται.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.status import LineStatus
from app.models import TransportMode
from app.seed import SEED_LINES, seed
from app.services import line_status
from tests.conftest import NOW


class TestAssess:
    def test_line_without_reports_is_unknown(self, session: Session, make_line) -> None:
        line = make_line()
        result = line_status.assess(session, line.id, NOW)
        assert result.status is LineStatus.UNKNOWN
        assert result.sample_size == 0

    def test_agreeing_reports_produce_a_status(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        line = make_line()
        for _ in range(4):
            make_report(line=line, author=make_user(), delay=12)

        result = line_status.assess(session, line.id, NOW)
        assert result.status is LineStatus.MINOR
        assert result.estimated_delay == 12.0
        assert result.sample_size == 4

    def test_reports_of_other_lines_are_not_mixed_in(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        target, other = make_line(), make_line()
        make_report(line=target, author=make_user(), delay=3)
        make_report(line=target, author=make_user(), delay=3)
        for _ in range(4):
            make_report(line=other, author=make_user(), delay=60)

        result = line_status.assess(session, target.id, NOW)
        assert result.estimated_delay == 3.0
        assert result.status is LineStatus.NORMAL

    def test_expired_reports_are_excluded(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        line = make_line()
        for _ in range(3):
            make_report(line=line, author=make_user(), delay=40, minutes_ago=90)

        assert line_status.assess(session, line.id, NOW).status is LineStatus.UNKNOWN

    def test_untrusted_author_carries_less_weight(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        """Ο βαθμός αξιοπιστίας υπολογίζεται από τη βάση και φτάνει στον πυρήνα."""
        line = make_line()
        for _ in range(3):
            make_report(line=line, author=make_user(confirmations=20), delay=3)
        make_report(line=line, author=make_user(disputes=30), delay=120)

        result = line_status.assess(session, line.id, NOW)
        assert result.estimated_delay == 3.0
        assert result.status is LineStatus.NORMAL

    def test_repeat_reports_from_one_user_count_once(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        line = make_line()
        spammer = make_user()
        for minutes in (1, 2, 3, 4, 5):
            make_report(line=line, author=spammer, delay=90, minutes_ago=minutes)

        result = line_status.assess(session, line.id, NOW)
        assert result.sample_size == 1
        assert result.status is LineStatus.UNKNOWN


class TestAssessAllLines:
    def test_worst_lines_come_first_and_unknown_last(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        calm, troubled, silent = make_line(), make_line(), make_line()
        for _ in range(3):
            make_report(line=calm, author=make_user(), delay=2)
            make_report(line=troubled, author=make_user(), delay=35)

        ranking = line_status.assess_all_lines(session, NOW)
        ordered_ids = [line.id for line, _ in ranking]

        assert ordered_ids.index(troubled.id) < ordered_ids.index(calm.id)
        assert ordered_ids[-1] == silent.id

    def test_every_line_appears_even_without_data(self, session: Session, make_line) -> None:
        for _ in range(3):
            make_line()
        assert len(line_status.assess_all_lines(session, NOW)) == 3


class TestRateLimiting:
    def test_first_report_is_allowed(self, session: Session, make_line, make_user) -> None:
        decision = line_status.check_submission_allowed(
            session, make_user().id, make_line().id, NOW
        )
        assert decision.allowed is True

    def test_second_report_within_cooldown_is_blocked(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        line, author = make_line(), make_user()
        make_report(line=line, author=author, delay=10, minutes_ago=4)

        decision = line_status.check_submission_allowed(session, author.id, line.id, NOW)
        assert decision.allowed is False
        assert decision.retry_after_seconds == 6 * 60

    def test_cooldown_is_per_line(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        """Ο περιορισμός δεν πρέπει να φιμώνει τον χρήστη σε *άλλη* γραμμή."""
        reported, other = make_line(), make_line()
        author = make_user()
        make_report(line=reported, author=author, delay=10, minutes_ago=1)

        assert (
            line_status.check_submission_allowed(session, author.id, other.id, NOW).allowed is True
        )

    def test_old_reports_do_not_block(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        line, author = make_line(), make_user()
        make_report(line=line, author=author, delay=10, minutes_ago=30)

        assert (
            line_status.check_submission_allowed(session, author.id, line.id, NOW).allowed is True
        )


class TestSeed:
    def test_seed_inserts_all_lines(self, session: Session) -> None:
        added = seed(session)
        assert added == len(SEED_LINES)

    def test_seed_is_idempotent(self, session: Session) -> None:
        """Καλείται σε κάθε εκκίνηση του container — δεν επιτρέπεται να διπλασιάζει."""
        seed(session)
        assert seed(session) == 0

    def test_seeded_lines_have_ordered_stops(self, session: Session, make_line) -> None:
        seed(session)
        results = line_status.assess_all_lines(session, NOW)
        metro = next(line for line, _ in results if line.code == "Μ1")
        assert [stop.position for stop in metro.stops] == list(range(len(metro.stops)))
        assert metro.mode is TransportMode.METRO

    def test_seeded_network_starts_with_no_data(self, session: Session) -> None:
        seed(session)
        results = line_status.assess_all_lines(session, NOW)
        assert all(assessment.status is LineStatus.UNKNOWN for _, assessment in results)


class TestWindowOverride:
    def test_narrow_window_excludes_older_reports(
        self, session: Session, make_line, make_user, make_report
    ) -> None:
        line = make_line()
        for _ in range(3):
            make_report(line=line, author=make_user(), delay=10, minutes_ago=8)

        wide = line_status.assess(session, line.id, NOW)
        narrow = line_status.assess(session, line.id, NOW, window=timedelta(minutes=5))

        assert wide.status is LineStatus.MINOR
        assert narrow.status is LineStatus.UNKNOWN
