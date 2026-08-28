"""Έλεγχοι ταυτοποίησης και εξουσιοδότησης."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import UserRole, utcnow
from app.security import BCRYPT_MAX_BYTES, create_access_token, hash_password, verify_password

VALID = {"email": "maria@example.com", "password": "sup3r-secret-pass"}


class TestPasswordHashing:
    def test_hash_is_not_the_password(self) -> None:
        digest = hash_password("sup3r-secret-pass")
        assert "sup3r-secret-pass" not in digest
        assert verify_password("sup3r-secret-pass", digest) is True

    def test_wrong_password_rejected(self) -> None:
        assert verify_password("λάθος", hash_password("σωστό")) is False

    def test_same_password_hashes_differently(self) -> None:
        """Διαφορετικό salt κάθε φορά — αλλιώς ένα rainbow table σπάει τα πάντα."""
        assert hash_password("ίδιος") != hash_password("ίδιος")

    def test_corrupt_hash_fails_closed(self) -> None:
        """Κατεστραμμένο hash στη βάση: αποτυχία σύνδεσης, όχι σφάλμα 500."""
        assert verify_password("οτιδήποτε", "δεν-είναι-hash") is False

    def test_overlong_password_is_rejected_not_truncated(self) -> None:
        """Το bcrypt κόβει σιωπηλά στα 72 bytes· η σιωπηλή περικοπή είναι κενό ασφαλείας."""
        too_long = "α" * BCRYPT_MAX_BYTES
        assert len(too_long.encode()) > BCRYPT_MAX_BYTES
        assert verify_password(too_long, hash_password("κανονικός")) is False


class TestTokens:
    def test_valid_token_round_trip(self, session: Session, make_user, client: TestClient) -> None:
        user = make_user()
        token = create_access_token(user.id, now=utcnow())
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["id"] == user.id

    def test_expired_token_is_rejected(self, make_user, client: TestClient) -> None:
        user = make_user()
        token = create_access_token(
            user.id, now=utcnow() - timedelta(hours=2), expires_in=timedelta(minutes=1)
        )
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_tampered_token_is_rejected(self, make_user, client: TestClient) -> None:
        token = create_access_token(make_user().id, now=utcnow())
        forged = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert response.status_code == 401

    def test_missing_token_is_rejected(self, client: TestClient) -> None:
        assert client.get("/api/v1/auth/me").status_code == 401


class TestRegister:
    def test_creates_a_passenger(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/register", json=VALID)
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == VALID["email"]
        assert body["role"] == UserRole.PASSENGER
        assert "password" not in body
        assert "password_hash" not in body

    def test_duplicate_email_conflicts(self, client: TestClient) -> None:
        client.post("/api/v1/auth/register", json=VALID)
        assert client.post("/api/v1/auth/register", json=VALID).status_code == 409

    def test_short_password_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register", json={"email": "a@example.com", "password": "abc"}
        )
        assert response.status_code == 422

    def test_invalid_email_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register", json={"email": "όχι-email", "password": "sup3r-secret"}
        )
        assert response.status_code == 422

    def test_cannot_self_assign_operator_role(self, client: TestClient) -> None:
        """Κλιμάκωση δικαιωμάτων με μία γραμμή JSON — το πεδίο αγνοείται."""
        response = client.post("/api/v1/auth/register", json={**VALID, "role": UserRole.OPERATOR})
        assert response.status_code == 201
        assert response.json()["role"] == UserRole.PASSENGER


class TestLogin:
    def test_successful_login_returns_a_token(self, client: TestClient) -> None:
        client.post("/api/v1/auth/register", json=VALID)
        response = client.post("/api/v1/auth/login", json=VALID)
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert response.json()["access_token"]

    def test_token_from_login_works(self, client: TestClient) -> None:
        client.post("/api/v1/auth/register", json=VALID)
        token = client.post("/api/v1/auth/login", json=VALID).json()["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == VALID["email"]

    def test_unknown_email_and_wrong_password_are_indistinguishable(
        self, client: TestClient
    ) -> None:
        """Διαφορετικά μηνύματα θα επέτρεπαν απαρίθμηση λογαριασμών."""
        client.post("/api/v1/auth/register", json=VALID)

        wrong_password = client.post(
            "/api/v1/auth/login", json={**VALID, "password": "λάθος-κωδικός"}
        )
        unknown_email = client.post(
            "/api/v1/auth/login",
            json={"email": "κανείς@example.com", "password": "λάθος-κωδικός"},
        )

        assert wrong_password.status_code == unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()


class TestRoleGuard:
    def test_passenger_cannot_open_dashboard(
        self, client: TestClient, make_user, auth_headers
    ) -> None:
        response = client.get("/api/v1/admin/dashboard", headers=auth_headers(make_user()))
        assert response.status_code == 403

    def test_operator_can_open_dashboard(self, client: TestClient, make_user, auth_headers) -> None:
        operator = make_user(role=UserRole.OPERATOR)
        response = client.get("/api/v1/admin/dashboard", headers=auth_headers(operator))
        assert response.status_code == 200

    def test_anonymous_cannot_open_dashboard(self, client: TestClient) -> None:
        assert client.get("/api/v1/admin/dashboard").status_code == 401
