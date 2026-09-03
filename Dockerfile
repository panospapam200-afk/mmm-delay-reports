# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Στάδιο 1 — builder: εγκατάσταση εξαρτήσεων σε απομονωμένο virtualenv.
# Χωρίζεται από το runtime ώστε τα εργαλεία μεταγλώττισης να μην καταλήγουν
# στην τελική εικόνα.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install .

# ---------------------------------------------------------------------------
# Στάδιο 2 — runtime: μόνο ο διερμηνέας, το venv και ο κώδικας.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Η εφαρμογή δεν τρέχει ως root.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app \
    && chown appuser:appuser /app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser backend/app ./app
# Τα migrations ταξιδεύουν μαζί με τον κώδικα: το image πρέπει να μπορεί να
# ανεβάσει μόνο του το σχήμα της βάσης στην έκδοση που περιμένει ο κώδικας.
COPY --chown=appuser:appuser backend/migrations ./migrations
COPY --chown=appuser:appuser backend/alembic.ini ./alembic.ini

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# Τρία στάδια με τη σειρά, και το καθένα πρέπει να πετύχει για να συνεχίσει το
# επόμενο:
#
#   1. migrations  — το σχήμα φτάνει στην έκδοση που περιμένει ο κώδικας
#   2. seed        — τα δεδομένα αναφοράς (γραμμές, στάσεις) υπάρχουν
#   3. server      — η εφαρμογή δέχεται αιτήματα
#
# Το βήμα 2 γίνεται εδώ και όχι με το χέρι, επειδή η δωρεάν βαθμίδα του Render
# δεν παρέχει πρόσβαση σε shell. Είναι ακίνδυνο σε κάθε επανεκκίνηση, γιατί η
# seed() είναι ιδεμπόσταστη.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
