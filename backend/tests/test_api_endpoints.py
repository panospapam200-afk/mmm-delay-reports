"""Έλεγχοι των endpoints γραμμών, αναφορών και dashboard.

Εδώ δοκιμάζεται η **συμπεριφορά του API**: κωδικοί κατάστασης, κεφαλίδες,
δικαιώματα. Η ορθότητα του αλγορίθμου έχει ήδη αποδειχθεί στα tests του πυρήνα
και δεν επαναλαμβάνεται.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.status import LineStatus
from app.models import UserRole

# ------------------------------------------------------------------- γραμμές


class TestListLines:
    def test_readable_without_login(self, client: TestClient, make_line) -> None:
        """Η ανάγνωση δεν απαιτεί λογαριασμό — απόφαση από τη User Journey Α."""
        make_line(code="550")
        response = client.get("/api/v1/lines")
        assert response.status_code == 200
        assert response.json()[0]["code"] == "550"

    def test_line_without_reports_is_unknown(self, client: TestClient, make_line) -> None:
        make_line()
        body = client.get("/api/v1/lines").json()[0]
        assert body["current_status"]["status"] == LineStatus.UNKNOWN
        assert body["current_status"]["estimated_delay"] is None
        assert body["current_status"]["confidence"] == 0.0

    def test_status_includes_a_greek_label(self, client: TestClient, make_line) -> None:
        make_line()
        assert client.get("/api/v1/lines").json()[0]["current_status"]["label"] == "Άγνωστο"

    def test_reports_produce_a_status(
        self, client: TestClient, make_line, make_user, make_live_report
    ) -> None:
        line = make_line()
        for _ in range(3):
            make_live_report(line=line, author=make_user(), delay=12, minutes_ago=1)

        status_body = client.get(f"/api/v1/lines/{line.id}").json()["current_status"]
        assert status_body["status"] == LineStatus.MINOR
        assert status_body["estimated_delay"] == 12.0
        assert status_body["sample_size"] == 3

    def test_detail_includes_ordered_stops(self, client: TestClient, make_line) -> None:
        line = make_line(stops=("Πρώτη", "Δεύτερη", "Τρίτη"))
        stops = client.get(f"/api/v1/lines/{line.id}").json()["stops"]
        assert [stop["name"] for stop in stops] == ["Πρώτη", "Δεύτερη", "Τρίτη"]

    def test_lookup_by_code(self, client: TestClient, make_line) -> None:
        make_line(code="Χ95")
        response = client.get("/api/v1/lines/by-code/Χ95")
        assert response.status_code == 200
        assert response.json()["code"] == "Χ95"

    def test_unknown_line_is_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/lines/9999").status_code == 404
        assert client.get("/api/v1/lines/by-code/ΔΕΝ-ΥΠΑΡΧΕΙ").status_code == 404


# ------------------------------------------------------------------ αναφορές


class TestCreateReport:
    def test_requires_authentication(self, client: TestClient, make_line) -> None:
        line = make_line()
        response = client.post("/api/v1/reports", json={"line_id": line.id, "delay_minutes": 10})
        assert response.status_code == 401

    def test_creates_a_report(self, client: TestClient, make_line, make_user, auth_headers) -> None:
        line = make_line()
        response = client.post(
            "/api/v1/reports",
            json={"line_id": line.id, "delay_minutes": 12.5, "note": "Δεν ήρθε ακόμα"},
            headers=auth_headers(make_user()),
        )
        assert response.status_code == 201
        assert response.json()["delay_minutes"] == 12.5
        assert response.headers["Location"].startswith("/api/v1/reports/")

    def test_report_is_visible_in_line_status(
        self, client: TestClient, make_line, make_user, auth_headers
    ) -> None:
        line = make_line()
        for _ in range(2):
            client.post(
                "/api/v1/reports",
                json={"line_id": line.id, "delay_minutes": 20},
                headers=auth_headers(make_user()),
            )
        body = client.get(f"/api/v1/lines/{line.id}").json()["current_status"]
        assert body["status"] == LineStatus.SEVERE
        assert body["sample_size"] == 2

    def test_unknown_line_is_404(self, client: TestClient, make_user, auth_headers) -> None:
        response = client.post(
            "/api/v1/reports",
            json={"line_id": 9999, "delay_minutes": 10},
            headers=auth_headers(make_user()),
        )
        assert response.status_code == 404

    def test_absurd_delay_is_rejected(
        self, client: TestClient, make_line, make_user, auth_headers
    ) -> None:
        response = client.post(
            "/api/v1/reports",
            json={"line_id": make_line().id, "delay_minutes": 5000},
            headers=auth_headers(make_user()),
        )
        assert response.status_code == 422

    def test_stop_from_another_line_is_rejected(
        self, client: TestClient, make_line, make_user, auth_headers
    ) -> None:
        target, other = make_line(), make_line(stops=("Ξένη στάση",))
        response = client.post(
            "/api/v1/reports",
            json={
                "line_id": target.id,
                "delay_minutes": 10,
                "stop_id": other.stops[0].id,
            },
            headers=auth_headers(make_user()),
        )
        assert response.status_code == 422


class TestRateLimit:
    def test_second_report_is_throttled(
        self, client: TestClient, make_line, make_user, auth_headers
    ) -> None:
        line, headers = make_line(), auth_headers(make_user())
        payload = {"line_id": line.id, "delay_minutes": 10}

        assert client.post("/api/v1/reports", json=payload, headers=headers).status_code == 201
        second = client.post("/api/v1/reports", json=payload, headers=headers)

        assert second.status_code == 429
        assert int(second.headers["Retry-After"]) > 0

    def test_throttle_is_per_line(
        self, client: TestClient, make_line, make_user, auth_headers
    ) -> None:
        first, second = make_line(), make_line()
        headers = auth_headers(make_user())

        client.post(
            "/api/v1/reports", json={"line_id": first.id, "delay_minutes": 10}, headers=headers
        )
        response = client.post(
            "/api/v1/reports", json={"line_id": second.id, "delay_minutes": 10}, headers=headers
        )
        assert response.status_code == 201

    def test_throttle_is_per_user(
        self, client: TestClient, make_line, make_user, auth_headers
    ) -> None:
        line = make_line()
        payload = {"line_id": line.id, "delay_minutes": 10}

        client.post("/api/v1/reports", json=payload, headers=auth_headers(make_user()))
        response = client.post("/api/v1/reports", json=payload, headers=auth_headers(make_user()))
        assert response.status_code == 201


# ---------------------------------------------------------------- ψηφοφορία


class TestConfirm:
    def test_confirmation_raises_author_reliability(
        self,
        session: Session,
        client: TestClient,
        make_line,
        make_user,
        make_live_report,
        auth_headers,
    ) -> None:
        author = make_user()
        report = make_live_report(line=make_line(), author=author, delay=10)
        before = author.reliability

        response = client.post(
            f"/api/v1/reports/{report.id}/confirm",
            json={"agrees": True},
            headers=auth_headers(make_user()),
        )
        assert response.status_code == 200
        assert response.json()["author_reliability"] > before

    def test_dispute_lowers_author_reliability(
        self, client: TestClient, make_line, make_user, make_live_report, auth_headers
    ) -> None:
        author = make_user()
        report = make_live_report(line=make_line(), author=author, delay=10)
        before = author.reliability

        response = client.post(
            f"/api/v1/reports/{report.id}/confirm",
            json={"agrees": False},
            headers=auth_headers(make_user()),
        )
        assert response.json()["author_reliability"] < before

    def test_cannot_vote_on_own_report(
        self, client: TestClient, make_line, make_user, make_live_report, auth_headers
    ) -> None:
        """Αλλιώς ο καθένας ανεβάζει μόνος του τον βαθμό αξιοπιστίας του."""
        author = make_user()
        report = make_live_report(line=make_line(), author=author, delay=10)

        response = client.post(
            f"/api/v1/reports/{report.id}/confirm",
            json={"agrees": True},
            headers=auth_headers(author),
        )
        assert response.status_code == 403

    def test_cannot_vote_twice(
        self, client: TestClient, make_line, make_user, make_live_report, auth_headers
    ) -> None:
        report = make_live_report(line=make_line(), author=make_user(), delay=10)
        headers = auth_headers(make_user())

        first = client.post(
            f"/api/v1/reports/{report.id}/confirm", json={"agrees": True}, headers=headers
        )
        second = client.post(
            f"/api/v1/reports/{report.id}/confirm", json={"agrees": False}, headers=headers
        )
        assert first.status_code == 200
        assert second.status_code == 409

    def test_unknown_report_is_404(self, client: TestClient, make_user, auth_headers) -> None:
        response = client.post(
            "/api/v1/reports/9999/confirm",
            json={"agrees": True},
            headers=auth_headers(make_user()),
        )
        assert response.status_code == 404

    def test_requires_authentication(
        self, client: TestClient, make_line, make_user, make_live_report
    ) -> None:
        report = make_live_report(line=make_line(), author=make_user(), delay=10)
        response = client.post(f"/api/v1/reports/{report.id}/confirm", json={"agrees": True})
        assert response.status_code == 401


# ---------------------------------------------------------------- dashboard


class TestDashboard:
    def test_ranks_the_worst_line_first(
        self, client: TestClient, make_line, make_user, make_live_report, auth_headers
    ) -> None:
        calm, troubled = make_line(code="calm"), make_line(code="troubled")
        for _ in range(3):
            make_live_report(line=calm, author=make_user(), delay=2, minutes_ago=1)
            make_live_report(line=troubled, author=make_user(), delay=40, minutes_ago=1)

        body = client.get(
            "/api/v1/admin/dashboard", headers=auth_headers(make_user(role=UserRole.OPERATOR))
        ).json()
        assert body["lines"][0]["code"] == "troubled"
        assert body["lines"][0]["status"] == LineStatus.SEVERE

    def test_counts_reports_in_window(
        self, client: TestClient, make_line, make_user, make_live_report, auth_headers
    ) -> None:
        line = make_line()
        for _ in range(4):
            make_live_report(line=line, author=make_user(), delay=10, minutes_ago=1)
        make_live_report(line=line, author=make_user(), delay=10, minutes_ago=120)

        body = client.get(
            "/api/v1/admin/dashboard", headers=auth_headers(make_user(role=UserRole.OPERATOR))
        ).json()
        assert body["total_reports_in_window"] == 4

    def test_sample_size_counts_distinct_users_not_reports(
        self, client: TestClient, make_line, make_user, make_live_report, auth_headers
    ) -> None:
        """User Journey Β, στάδιο 2: ο χειριστής πρέπει να βλέπει ανθρώπους, όχι υποβολές."""
        line = make_line()
        noisy = make_user()
        for minutes in (1, 2, 3, 4, 5):
            make_live_report(line=line, author=noisy, delay=45, minutes_ago=minutes)

        body = client.get(
            "/api/v1/admin/dashboard", headers=auth_headers(make_user(role=UserRole.OPERATOR))
        ).json()
        line_row = next(row for row in body["lines"] if row["code"] == line.code)
        assert line_row["sample_size"] == 1
        assert body["total_reports_in_window"] == 5
