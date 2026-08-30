"""Σημείο εισόδου της εφαρμογής FastAPI."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import __version__
from app.api import admin, auth, lines, reports

app = FastAPI(
    title="Σύστημα Αναφοράς Καθυστερήσεων ΜΜΜ",
    description=(
        "Crowdsourced αναφορές καθυστερήσεων σε γραμμές μέσων μαζικής μεταφοράς, "
        "με αλγοριθμική στάθμιση ως προς φρεσκάδα, συμφωνία και αξιοπιστία συντάκτη.\n\n"
        "**Η ανάγνωση δεν απαιτεί σύνδεση· η υποβολή απαιτεί.**"
    ),
    version=__version__,
)

# Το frontend σερβίρεται από το ίδιο container στην παραγωγή, αλλά κατά την
# ανάπτυξη τρέχει σε δική του θύρα (Vite, 5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(lines.router)
app.include_router(reports.router)
app.include_router(admin.router)


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Έλεγχος ζωτικότητας — τον καλεί το Render και το smoke test του pipeline."""
    return HealthResponse(status="ok", version=__version__)
