"""Σχήματα αιτημάτων και αποκρίσεων (Pydantic).

Ξεχωριστά από τα μοντέλα ORM με σκοπό: το σχήμα του API δεν είναι το σχήμα της
βάσης. Το ``password_hash`` δεν πρέπει να μπορεί να διαρρεύσει σε απόκριση
επειδή κάποιος πρόσθεσε ένα πεδίο στο μοντέλο.

Το FastAPI παράγει από αυτά αυτόματα το OpenAPI schema, το οποίο
χρησιμοποιείται ως τεκμηρίωση API στο παραδοτέο.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.status import LineStatus
from app.models import (
    MAX_DELAY_MINUTES,
    MIN_DELAY_MINUTES,
    ReportCategory,
    TransportMode,
    UserRole,
)

# ----------------------------------------------------------------- λογαριασμοί


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72, description="Τουλάχιστον 8 χαρακτήρες")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    reliability: float = Field(description="Πολλαπλασιαστής βαρύτητας, υπολογισμένος")


# --------------------------------------------------------------------- γραμμές


class StopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: int


class LineStatusResponse(BaseModel):
    """Η κατάσταση μιας γραμμής όπως τη βλέπει ο επιβάτης.

    Το ``confidence`` **δεν** είναι εσωτερική μετρική: εμφανίζεται δίπλα στην
    εκτίμηση. Χωρίς αυτό ο χρήστης δεν έχει τρόπο να κρίνει αν να εμπιστευτεί
    τον αριθμό (βλ. User Journey Α, στάδιο 3).
    """

    status: LineStatus
    label: str = Field(description="Ετικέτα κατάστασης στα ελληνικά")
    estimated_delay: float | None = Field(description="Εκτιμώμενη καθυστέρηση σε λεπτά")
    confidence: float = Field(ge=0.0, le=1.0)
    sample_size: int = Field(description="Πλήθος **διακριτών** χρηστών που συνεισέφεραν")
    discarded_as_outliers: int


class LineResponse(BaseModel):
    id: int
    code: str
    name: str
    mode: TransportMode
    current_status: LineStatusResponse


class LineDetailResponse(LineResponse):
    stops: list[StopResponse]


# --------------------------------------------------------------------- αναφορές


class CreateReportRequest(BaseModel):
    line_id: int
    delay_minutes: float = Field(ge=MIN_DELAY_MINUTES, le=MAX_DELAY_MINUTES)
    category: ReportCategory = ReportCategory.DELAY
    stop_id: int | None = None
    note: str | None = Field(default=None, max_length=280)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_id: int
    author_id: int
    delay_minutes: float
    category: ReportCategory
    note: str | None
    created_at: datetime


class ConfirmRequest(BaseModel):
    agrees: bool = Field(description="True = επιβεβαιώνω, False = διαψεύδω")


class ConfirmResponse(BaseModel):
    report_id: int
    agrees: bool
    author_reliability: float = Field(description="Ο νέος βαθμός του συντάκτη της αναφοράς")


# ------------------------------------------------------------------- dashboard


class DashboardLine(BaseModel):
    code: str
    name: str
    mode: TransportMode
    status: LineStatus
    label: str
    estimated_delay: float | None
    confidence: float
    sample_size: int


class DashboardResponse(BaseModel):
    generated_at: datetime
    total_reports_in_window: int
    lines: list[DashboardLine]
