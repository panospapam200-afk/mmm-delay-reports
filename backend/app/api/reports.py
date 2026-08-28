"""Endpoints υποβολής αναφοράς και ψήφου επιβεβαίωσης/διάψευσης."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, DbSession
from app.models import Confirmation, Line, Report, Stop, utcnow
from app.schemas import ConfirmRequest, ConfirmResponse, CreateReportRequest, ReportResponse
from app.services import line_status

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: CreateReportRequest,
    session: DbSession,
    user: CurrentUser,
    response: Response,
) -> Report:
    """Υποβολή αναφοράς καθυστέρησης (US-01, US-02)."""
    now = utcnow()

    line = session.get(Line, payload.line_id)
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Η γραμμή δεν βρέθηκε.")

    if payload.stop_id is not None:
        stop = session.get(Stop, payload.stop_id)
        if stop is None or stop.line_id != line.id:
            # Σκόπιμα ο αριθμός και όχι η σταθερά: το Starlette μετονόμασε το
            # HTTP_422_UNPROCESSABLE_ENTITY σε ..._CONTENT και η παλιά ονομασία
            # παράγει προειδοποίηση απόσυρσης. Ο κωδικός 422 δεν αλλάζει.
            raise HTTPException(
                status_code=422,
                detail="Η στάση δεν ανήκει σε αυτή τη γραμμή.",
            )

    decision = line_status.check_submission_allowed(session, user.id, line.id, now)
    if not decision.allowed:
        # Το πρότυπο HTTP ορίζει την κεφαλίδα Retry-After γι' αυτόν ακριβώς τον
        # σκοπό· ο πελάτης δεν χρειάζεται να μαντέψει πότε να ξαναδοκιμάσει.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Έχεις ήδη αναφέρει αυτή τη γραμμή πρόσφατα. "
                f"Δοκίμασε ξανά σε {decision.retry_after_seconds // 60 + 1} λεπτά."
            ),
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    report = Report(
        line_id=line.id,
        author_id=user.id,
        stop_id=payload.stop_id,
        delay_minutes=payload.delay_minutes,
        category=payload.category,
        note=payload.note,
        created_at=now,
    )
    session.add(report)
    session.commit()
    session.refresh(report)

    response.headers["Location"] = f"/api/v1/reports/{report.id}"
    return report


@router.post("/{report_id}/confirm", response_model=ConfirmResponse)
def confirm_report(
    report_id: int,
    payload: ConfirmRequest,
    session: DbSession,
    user: CurrentUser,
) -> ConfirmResponse:
    """Επιβεβαίωση ή διάψευση αναφοράς άλλου χρήστη (US-03).

    Η ψήφος ενημερώνει τα σωρευτικά πλήθη του **συντάκτη**, από τα οποία
    προκύπτει ο βαθμός αξιοπιστίας του στην επόμενη συνάθροιση.
    """
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Η αναφορά δεν βρέθηκε.")

    if report.author_id == user.id:
        # Χωρίς αυτόν τον έλεγχο, ο καθένας θα ανέβαζε τον βαθμό αξιοπιστίας
        # του επιβεβαιώνοντας τις ίδιες του τις αναφορές.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Δεν μπορείς να ψηφίσεις τη δική σου αναφορά.",
        )

    # Ο συντάκτης διαβάζεται *πριν* προστεθεί η ψήφος. Αν γινόταν μετά, η
    # τεμπέλικη φόρτωση της σχέσης θα πυροδοτούσε autoflush και η παραβίαση του
    # περιορισμού μοναδικότητας θα σκάγαμε εκτός του try/except παρακάτω — με
    # αποτέλεσμα 500 αντί για 409.
    author = report.author

    session.add(Confirmation(report_id=report.id, user_id=user.id, agrees=payload.agrees))

    if payload.agrees:
        author.confirmations_received += 1
    else:
        author.disputes_received += 1

    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        # Ο περιορισμός μοναδικότητας της βάσης είναι η πραγματική δικλείδα:
        # ένας έλεγχος μόνο στην εφαρμογή θα έσπαγε σε ταυτόχρονα αιτήματα.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Έχεις ήδη ψηφίσει αυτή την αναφορά.",
        ) from error

    session.refresh(author)
    return ConfirmResponse(
        report_id=report.id, agrees=payload.agrees, author_reliability=author.reliability
    )
