"""Dashboard χειριστή φορέα (US-08). Απαιτεί ρόλο ``OPERATOR``."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.aggregation import DEFAULT_WINDOW
from app.deps import DbSession, OperatorUser
from app.models import Report, utcnow
from app.schemas import DashboardLine, DashboardResponse
from app.services import line_status

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(session: DbSession, _operator: OperatorUser) -> DashboardResponse:
    """Κατάταξη γραμμών κατά ένταση προβλήματος.

    Το ``sample_size`` μετρά **διακριτούς χρήστες**, όχι αναφορές — αλλιώς ένας
    χρήστης με δέκα υποβολές θα έμοιαζε με δέκα ανθρώπους που συμφωνούν
    (βλ. User Journey Β, στάδιο 2).
    """
    now = utcnow()

    total_reports = session.scalar(
        select(func.count(Report.id)).where(Report.created_at >= now - DEFAULT_WINDOW)
    )

    return DashboardResponse(
        generated_at=now,
        total_reports_in_window=total_reports or 0,
        lines=[
            DashboardLine(
                code=line.code,
                name=line.name,
                mode=line.mode,
                status=assessment.status,
                label=assessment.status.label_el,
                estimated_delay=assessment.estimated_delay,
                confidence=assessment.confidence,
                sample_size=assessment.sample_size,
            )
            for line, assessment in line_status.assess_all_lines(session, now)
        ],
    )
