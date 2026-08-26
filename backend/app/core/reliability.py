"""Βαθμός αξιοπιστίας χρήστη με βάση το ιστορικό επιβεβαιώσεων/διαψεύσεων.

Ο βαθμός χρησιμοποιείται ως πολλαπλασιαστής βαρύτητας στη μηχανή συνάθροισης:
οι αναφορές χρηστών που έχουν επανειλημμένα επιβεβαιωθεί μετρούν περισσότερο,
των χρηστών που έχουν διαψευστεί λιγότερο.
"""

from __future__ import annotations

__all__ = [
    "MIN_WEIGHT",
    "MAX_WEIGHT",
    "NEUTRAL_WEIGHT",
    "compute_reliability",
    "is_suspected_spammer",
]

MIN_WEIGHT = 0.25
MAX_WEIGHT = 1.75
NEUTRAL_WEIGHT = 1.0

# Κατώφλι κάτω από το οποίο ο χρήστης θεωρείται ύποπτος για κακόβουλη χρήση.
SPAMMER_WEIGHT_THRESHOLD = 0.5
SPAMMER_MIN_EVIDENCE = 5


def compute_reliability(confirmations: int, disputes: int) -> float:
    """Επιστρέφει πολλαπλασιαστή βαρύτητας στο διάστημα ``[0.25, 1.75]``.

    Χρησιμοποιείται εξομάλυνση Laplace ``(c + 1) / (c + d + 2)`` ώστε:

    * ο νέος χρήστης χωρίς ιστορικό να ξεκινά ουδέτερος (βαρύτητα ``1.0``)·
    * μία μεμονωμένη διάψευση να μην εκμηδενίζει τη φωνή του χρήστη·
    * η ακρότητα του βαθμού να απαιτεί συσσωρευμένα στοιχεία.

    :raises ValueError: αν δοθούν αρνητικά πλήθη.
    """
    if confirmations < 0 or disputes < 0:
        raise ValueError("Τα πλήθη επιβεβαιώσεων και διαψεύσεων δεν μπορεί να είναι αρνητικά")

    smoothed_ratio = (confirmations + 1) / (confirmations + disputes + 2)
    # Γραμμική απεικόνιση του (0, 1) στο [MIN_WEIGHT, MAX_WEIGHT] ώστε
    # το ουδέτερο 0.5 να αντιστοιχεί ακριβώς στο NEUTRAL_WEIGHT.
    weight = MIN_WEIGHT + smoothed_ratio * (MAX_WEIGHT - MIN_WEIGHT)
    return round(weight, 4)


def is_suspected_spammer(confirmations: int, disputes: int) -> bool:
    """Σημαία για moderation: αρκετά στοιχεία *και* χαμηλή αξιοπιστία."""
    if confirmations + disputes < SPAMMER_MIN_EVIDENCE:
        return False
    return compute_reliability(confirmations, disputes) < SPAMMER_WEIGHT_THRESHOLD
