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

# Πρώτα μόνο το pyproject: αν δεν αλλάξουν οι εξαρτήσεις, το Docker
# επαναχρησιμοποιεί αυτό το layer από την cache.
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
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser backend/app ./app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# Το Render περνά τη θύρα μέσω της μεταβλητής PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
