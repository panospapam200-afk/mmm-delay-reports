"""Ταξινόμηση της εκτιμώμενης καθυστέρησης σε κατάσταση γραμμής.

Καθαρό module: καμία εξάρτηση από βάση δεδομένων, HTTP ή ρολόι συστήματος.
Αυτό είναι σκόπιμο — επιτρέπει ντετερμινιστικά unit tests χιλιοστών του
δευτερολέπτου μέσα στο CI pipeline.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["LineStatus", "MINOR_THRESHOLD_MINUTES", "SEVERE_THRESHOLD_MINUTES", "classify"]


class LineStatus(StrEnum):
    """Η κατάσταση μιας γραμμής όπως παρουσιάζεται στον επιβάτη."""

    UNKNOWN = "UNKNOWN"  # Ανεπαρκή ή αντιφατικά δεδομένα
    NORMAL = "NORMAL"  # Κανονική λειτουργία
    MINOR = "MINOR"  # Μικρή καθυστέρηση
    SEVERE = "SEVERE"  # Σοβαρή καθυστέρηση

    @property
    def label_el(self) -> str:
        return {
            LineStatus.UNKNOWN: "Άγνωστο",
            LineStatus.NORMAL: "Κανονικά",
            LineStatus.MINOR: "Μικρή καθυστέρηση",
            LineStatus.SEVERE: "Σοβαρή καθυστέρηση",
        }[self]


# Όρια σε λεπτά. Ορίζονται ως σταθερές module-level ώστε τα tests να ελέγχουν
# τις οριακές τιμές χωρίς να επαναλαμβάνουν "μαγικούς αριθμούς".
MINOR_THRESHOLD_MINUTES = 5.0
SEVERE_THRESHOLD_MINUTES = 15.0


def classify(delay_minutes: float | None) -> LineStatus:
    """Μετατρέπει λεπτά καθυστέρησης σε :class:`LineStatus`.

    Τα όρια είναι κλειστά από κάτω και ανοιχτά από πάνω:

    * ``delay < 5``            -> ``NORMAL``
    * ``5 <= delay < 15``      -> ``MINOR``
    * ``delay >= 15``          -> ``SEVERE``
    * ``None``                 -> ``UNKNOWN``

    Αρνητικές τιμές (όχημα που πέρασε νωρίτερα από το δρομολόγιο) θεωρούνται
    κανονική λειτουργία — δεν είναι σφάλμα εισόδου.
    """
    if delay_minutes is None:
        return LineStatus.UNKNOWN
    if delay_minutes < MINOR_THRESHOLD_MINUTES:
        return LineStatus.NORMAL
    if delay_minutes < SEVERE_THRESHOLD_MINUTES:
        return LineStatus.MINOR
    return LineStatus.SEVERE
