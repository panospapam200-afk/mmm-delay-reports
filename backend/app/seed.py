"""Αρχικά δεδομένα γραμμών και στάσεων.

⚠️ **Τα δεδομένα είναι ενδεικτικά.** Χρησιμοποιούνται υπαρκτοί κωδικοί γραμμών
του δικτύου της Αθήνας ώστε η εφαρμογή να είναι αναγνωρίσιμη, αλλά οι στάσεις
είναι δείγμα και όχι πλήρης, επικυρωμένη διαδρομή. Σε πραγματική λειτουργία η
πηγή θα ήταν το GTFS feed του φορέα — καταγράφεται ως γνωστός περιορισμός στο
``docs/ARCHITECTURE.md``.

Η συνάρτηση ``seed()`` είναι **ιδεμπόσταστη** (idempotent): εκτελείται όσες
φορές θέλει κανείς χωρίς να δημιουργεί διπλοεγγραφές. Αυτό είναι απαραίτητο
γιατί καλείται κατά την εκκίνηση του container, που μπορεί να ξαναγίνει
οποιαδήποτε στιγμή.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Line, Stop, TransportMode

__all__ = ["SEED_LINES", "seed"]


@dataclass(frozen=True)
class LineSeed:
    code: str
    name: str
    mode: TransportMode
    stops: tuple[str, ...]


SEED_LINES: tuple[LineSeed, ...] = (
    LineSeed(
        code="Μ1",
        name="Πειραιάς – Κηφισιά",
        mode=TransportMode.METRO,
        stops=("Πειραιάς", "Φάληρο", "Μοναστηράκι", "Ομόνοια", "Αττική", "Κηφισιά"),
    ),
    LineSeed(
        code="Μ2",
        name="Ελληνικό – Ανθούπολη",
        mode=TransportMode.METRO,
        stops=("Ελληνικό", "Δάφνη", "Συγγρού-Φιξ", "Ομόνοια", "Αττική", "Ανθούπολη"),
    ),
    LineSeed(
        code="Μ3",
        name="Δημοτικό Θέατρο – Αεροδρόμιο",
        mode=TransportMode.METRO,
        stops=("Δημοτικό Θέατρο", "Σύνταγμα", "Αμπελόκηποι", "Δουκίσσης Πλακεντίας", "Αεροδρόμιο"),
    ),
    LineSeed(
        code="Τ6",
        name="Σύνταγμα – Ασκληπιείο Βούλας",
        mode=TransportMode.TRAM,
        stops=("Σύνταγμα", "Ζάππειο", "Νέο Φάληρο", "Γλυφάδα", "Ασκληπιείο Βούλας"),
    ),
    LineSeed(
        code="040",
        name="Πειραιάς – Σύνταγμα",
        mode=TransportMode.BUS,
        stops=("Πειραιάς", "Καλλιθέα", "Συγγρού", "Σύνταγμα"),
    ),
    LineSeed(
        code="550",
        name="Κηφισιά – Παλαιό Φάληρο",
        mode=TransportMode.BUS,
        stops=("Κηφισιά", "Αμπελόκηποι", "Ακαδημία", "Παλαιό Φάληρο"),
    ),
    LineSeed(
        code="Χ95",
        name="Σύνταγμα – Αεροδρόμιο (express)",
        mode=TransportMode.BUS,
        stops=("Σύνταγμα", "Κατεχάκη", "Σταυρός", "Αεροδρόμιο"),
    ),
    LineSeed(
        code="Α1",
        name="Πειραιάς – Βούλα",
        mode=TransportMode.BUS,
        stops=("Πειραιάς", "Νέο Φάληρο", "Άλιμος", "Γλυφάδα", "Βούλα"),
    ),
    LineSeed(
        code="11",
        name="Άνω Πατήσια – Νέα Ελβετία",
        mode=TransportMode.TROLLEY,
        stops=("Άνω Πατήσια", "Ομόνοια", "Σύνταγμα", "Νέα Ελβετία"),
    ),
    LineSeed(
        code="Π1",
        name="Πειραιάς – Άνω Λιόσια (Προαστιακός)",
        mode=TransportMode.SUBURBAN,
        stops=("Πειραιάς", "Λεύκα", "Άνω Λιόσια"),
    ),
)


def seed(session: Session) -> int:
    """Εισάγει όσες γραμμές λείπουν. Επιστρέφει πόσες προστέθηκαν."""
    existing = set(session.scalars(select(Line.code)))
    added = 0

    for entry in SEED_LINES:
        if entry.code in existing:
            continue
        line = Line(code=entry.code, name=entry.name, mode=entry.mode)
        line.stops = [
            Stop(name=stop_name, position=position)
            for position, stop_name in enumerate(entry.stops)
        ]
        session.add(line)
        added += 1

    session.commit()
    return added
