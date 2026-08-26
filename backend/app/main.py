"""Σημείο εισόδου της εφαρμογής FastAPI.

Στη Φάση 1 περιέχει μόνο τα endpoints υγείας και έκδοσης, ώστε το Docker image
να είναι εκτελέσιμο και το pipeline να μπορεί να κάνει smoke test το container.
Τα endpoints αναφορών προστίθενται στη Φάση 2.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from app import __version__

app = FastAPI(
    title="Σύστημα Αναφοράς Καθυστερήσεων ΜΜΜ",
    description=(
        "Crowdsourced αναφορές καθυστερήσεων σε γραμμές μέσων μαζικής μεταφοράς, "
        "με αλγοριθμική στάθμιση ως προς φρεσκάδα, συμφωνία και αξιοπιστία συντάκτη."
    ),
    version=__version__,
)


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Έλεγχος ζωτικότητας — τον καλεί το Render και το smoke test του pipeline."""
    return HealthResponse(status="ok", version=__version__)
