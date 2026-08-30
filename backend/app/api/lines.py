"""Endpoints ανάγνωσης: κατάλογος γραμμών και κατάσταση γραμμής.

**Δεν απαιτούν σύνδεση.** Απόφαση από τη User Journey Α: ο περιστασιακός
επιβάτης που θέλει απλώς να δει αν αργεί το λεωφορείο δεν πρέπει να συναντήσει
οθόνη εγγραφής — θα κλείσει την εφαρμογή. Η *υποβολή* απαιτεί λογαριασμό, η
*ανάγνωση* όχι.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.aggregation import LineAssessment
from app.deps import DbSession
from app.models import Line, utcnow
from app.schemas import LineDetailResponse, LineResponse, LineStatusResponse
from app.services import line_status

router = APIRouter(prefix="/api/v1/lines", tags=["lines"])


def to_status_response(assessment: LineAssessment) -> LineStatusResponse:
    return LineStatusResponse(
        status=assessment.status,
        label=assessment.status.label_el,
        estimated_delay=assessment.estimated_delay,
        confidence=assessment.confidence,
        sample_size=assessment.sample_size,
        discarded_as_outliers=assessment.discarded_as_outliers,
    )


def _detail(line: Line, session: DbSession) -> LineDetailResponse:
    assessment = line_status.assess(session, line.id, utcnow())
    return LineDetailResponse(
        id=line.id,
        code=line.code,
        name=line.name,
        mode=line.mode,
        current_status=to_status_response(assessment),
        stops=line.stops,
    )


@router.get("", response_model=list[LineResponse])
def list_lines(session: DbSession) -> list[LineResponse]:
    """Όλες οι γραμμές με την τρέχουσα κατάστασή τους, χειρότερες πρώτα."""
    now = utcnow()
    return [
        LineResponse(
            id=line.id,
            code=line.code,
            name=line.name,
            mode=line.mode,
            current_status=to_status_response(assessment),
        )
        for line, assessment in line_status.assess_all_lines(session, now)
    ]


# ΠΡΟΣΟΧΗ ΣΤΗ ΣΕΙΡΑ: αυτή η διαδρομή δηλώνεται *πριν* από την `/{line_id}`.
# Το FastAPI ταιριάζει με τη σειρά δήλωσης· αν προηγούνταν η `/{line_id}`, το
# «by-code» θα προσπαθούσε να μετατραπεί σε ακέραιο και θα επέστρεφε 422.
@router.get("/by-code/{code}", response_model=LineDetailResponse)
def get_line_by_code(code: str, session: DbSession) -> LineDetailResponse:
    """Αναζήτηση με τον κωδικό που ξέρει ο επιβάτης («550», «Μ3»), όχι με id."""
    line = session.scalar(select(Line).where(Line.code == code))
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Η γραμμή δεν βρέθηκε.")
    return _detail(line, session)


@router.get("/{line_id}", response_model=LineDetailResponse)
def get_line(line_id: int, session: DbSession) -> LineDetailResponse:
    line = session.get(Line, line_id)
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Η γραμμή δεν βρέθηκε.")
    return _detail(line, session)
