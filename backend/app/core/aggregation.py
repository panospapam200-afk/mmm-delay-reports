"""Μηχανή συνάθροισης αναφορών καθυστέρησης.

Ο πυρήνας του συστήματος. Δέχεται τις ακατέργαστες αναφορές των επιβατών για
μία γραμμή και επιστρέφει μία εκτίμηση καθυστέρησης μαζί με ρητό βαθμό
εμπιστοσύνης.

Ο αγωγός επεξεργασίας έχει έξι στάδια:

1. **Χρονικό παράθυρο** — κρατάμε μόνο αναφορές των τελευταίων ``window``
   λεπτών· οι παλαιότερες περιγράφουν άλλο δρομολόγιο.
2. **Μία φωνή ανά χρήστη** — αν ο ίδιος χρήστης έστειλε πολλές αναφορές,
   μετράει μόνο η πιο πρόσφατη.
3. **Ελάχιστο πλήθος** — κάτω από ``min_reports`` δεν δηλώνουμε κατάσταση.
4. **Απόρριψη ακραίων τιμών** — φίλτρο MAD (Median Absolute Deviation), που
   αντέχει σε ακραίες τιμές πολύ καλύτερα από φίλτρο τυπικής απόκλισης.
5. **Στάθμιση** — εκθετική απόσβεση ως προς την ηλικία της αναφοράς, επί τον
   βαθμό αξιοπιστίας του συντάκτη.
6. **Σταθμισμένη διάμεσος + εμπιστοσύνη** — η διάμεσος (όχι ο μέσος όρος)
   γιατί παραμένει ανθεκτική σε ό,τι ξέφυγε από το στάδιο 4.

Καμία εξάρτηση από βάση δεδομένων ή HTTP: το ``now`` περνάει πάντα ως όρισμα,
ώστε τα tests να είναι απολύτως ντετερμινιστικά.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.status import LineStatus, classify

__all__ = [
    "DelayReport",
    "LineAssessment",
    "DEFAULT_WINDOW",
    "DEFAULT_MIN_REPORTS",
    "RECENCY_HALF_LIFE",
    "MAD_THRESHOLD",
    "LOW_CONFIDENCE_THRESHOLD",
    "assess_line",
    "weighted_median",
]

DEFAULT_WINDOW = timedelta(minutes=30)
DEFAULT_MIN_REPORTS = 2

# Χρόνος υποδιπλασιασμού της βαρύτητας μιας αναφοράς λόγω παλαιότητας.
RECENCY_HALF_LIFE = timedelta(minutes=10)

# Πόσες τυπικές αποκλίσεις (κατά MAD) μακριά από τη διάμεσο θεωρείται ακραία τιμή.
MAD_THRESHOLD = 3.5

# Σταθερά μετατροπής MAD σε συνεπή εκτιμήτρια τυπικής απόκλισης για κανονική κατανομή.
_MAD_SCALE = 1.4826

# Κάτω από αυτό το επίπεδο εμπιστοσύνης δεν δηλώνουμε κατάσταση στον χρήστη,
# ακόμη κι αν υπάρχει αριθμητική εκτίμηση.
LOW_CONFIDENCE_THRESHOLD = 0.20

# Παράμετρος εξομάλυνσης: πόσες αναφορές χρειάζονται για "μισή" εμπιστοσύνη ως προς το πλήθος.
_SAMPLE_SATURATION = 3.0

# Διασπορά (σε λεπτά) που μειώνει στο μισό τον όρο συμφωνίας.
_SPREAD_TOLERANCE = 5.0


@dataclass(frozen=True)
class DelayReport:
    """Μία αναφορά επιβάτη, όπως φτάνει στη μηχανή συνάθροισης."""

    id: int
    line_id: int
    author_id: int
    delay_minutes: float
    created_at: datetime
    author_reliability: float = 1.0


@dataclass(frozen=True)
class LineAssessment:
    """Το αποτέλεσμα της συνάθροισης για μία γραμμή."""

    status: LineStatus
    estimated_delay: float | None
    confidence: float
    sample_size: int
    discarded_as_outliers: int = 0
    used_report_ids: tuple[int, ...] = field(default_factory=tuple)

    @property
    def is_actionable(self) -> bool:
        """True όταν η εκτίμηση είναι αρκετά αξιόπιστη για να εμφανιστεί ως κατάσταση."""
        return self.status is not LineStatus.UNKNOWN


_UNKNOWN = LineAssessment(
    status=LineStatus.UNKNOWN,
    estimated_delay=None,
    confidence=0.0,
    sample_size=0,
)


def _median(values: list[float]) -> float:
    """Απλή διάμεσος. Προϋποθέτει μη κενή λίστα."""
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def weighted_median(values: list[float], weights: list[float]) -> float:
    """Σταθμισμένη διάμεσος: η τιμή όπου το σωρευτικό βάρος περνά το μισό του συνόλου.

    Όταν το σωρευτικό βάρος πέφτει *ακριβώς* στο μισό, επιστρέφεται ο μέσος
    όρος των δύο γειτονικών τιμών — ίδια σύμβαση με τη μη σταθμισμένη διάμεσο.

    :raises ValueError: για κενή είσοδο, ασύμβατα μήκη ή μη θετικό συνολικό βάρος.
    """
    if not values:
        raise ValueError("Η σταθμισμένη διάμεσος απαιτεί τουλάχιστον μία τιμή")
    if len(values) != len(weights):
        raise ValueError("Τιμές και βάρη πρέπει να έχουν ίδιο μήκος")
    if any(w < 0 for w in weights):
        raise ValueError("Τα βάρη δεν μπορεί να είναι αρνητικά")

    total = sum(weights)
    if total <= 0:
        raise ValueError("Το συνολικό βάρος πρέπει να είναι θετικό")

    pairs = sorted(zip(values, weights, strict=True), key=lambda pair: pair[0])
    half = total / 2
    cumulative = 0.0

    for index, (value, weight) in enumerate(pairs):
        cumulative += weight
        if math.isclose(cumulative, half, rel_tol=1e-9, abs_tol=1e-12):
            # Ακριβώς στο μισό: μεσολαβούμε με την επόμενη διακριτή τιμή.
            if index + 1 < len(pairs):
                return (value + pairs[index + 1][0]) / 2
            return value  # pragma: no cover - αδύνατο: θα σήμαινε συνολικό βάρος 0
        if cumulative > half:
            return value

    return pairs[-1][0]  # pragma: no cover - δίχτυ ασφαλείας για σφάλματα κινητής υποδιαστολής


def _recency_weight(age: timedelta) -> float:
    """Εκθετική απόσβεση: βαρύτητα 1.0 στο τώρα, 0.5 μετά από ένα ημιπερίοδο."""
    half_lives = age.total_seconds() / RECENCY_HALF_LIFE.total_seconds()
    return 0.5**half_lives


def _drop_outliers(reports: list[DelayReport]) -> tuple[list[DelayReport], int]:
    """Φίλτρο MAD. Επιστρέφει (αναφορές που κρατήθηκαν, πλήθος που απορρίφθηκε)."""
    if len(reports) < 3:
        # Με δύο αναφορές δεν υπάρχει έννοια "ακραίας τιμής" — η μία θα ήταν
        # πάντα το 100% της απόκλισης της άλλης.
        return reports, 0

    values = [r.delay_minutes for r in reports]
    center = _median(values)
    deviations = [abs(v - center) for v in values]
    mad = _median(deviations)

    if mad == 0:
        # Πλήρης ομοφωνία στη διάμεσο· κάθε απόκλιση είναι ύποπτη, αλλά χωρίς
        # κλίμακα δεν μπορούμε να την ποσοτικοποιήσουμε. Κρατάμε τα πάντα και
        # αφήνουμε τη σταθμισμένη διάμεσο να τα απορροφήσει.
        return reports, 0

    scale = _MAD_SCALE * mad
    kept = [r for r in reports if abs(r.delay_minutes - center) / scale <= MAD_THRESHOLD]
    return kept, len(reports) - len(kept)


def _latest_per_author(reports: list[DelayReport]) -> list[DelayReport]:
    """Μία φωνή ανά χρήστη: κρατάμε την πιο πρόσφατη αναφορά καθενός."""
    newest: dict[int, DelayReport] = {}
    for report in reports:
        current = newest.get(report.author_id)
        if current is None or report.created_at > current.created_at:
            newest[report.author_id] = report
        elif report.created_at == current.created_at and report.id > current.id:
            # Ντετερμινιστικό tie-break σε ισοπαλία χρόνου.
            newest[report.author_id] = report
    return list(newest.values())


def _confidence(kept: list[DelayReport], estimate: float) -> float:
    """Εμπιστοσύνη ως γινόμενο δύο όρων: πλήθος δείγματος επί συμφωνία."""
    n = len(kept)
    size_term = n / (n + _SAMPLE_SATURATION)

    deviations = [abs(r.delay_minutes - estimate) for r in kept]
    spread = _median(deviations)
    agreement_term = 1 / (1 + spread / _SPREAD_TOLERANCE)

    return round(min(1.0, size_term * agreement_term), 4)


def assess_line(
    reports: list[DelayReport],
    now: datetime,
    *,
    window: timedelta = DEFAULT_WINDOW,
    min_reports: int = DEFAULT_MIN_REPORTS,
) -> LineAssessment:
    """Συνθέτει αναφορές μιας γραμμής σε μία εκτίμηση κατάστασης.

    :param reports: οι αναφορές της γραμμής (δεν χρειάζεται να είναι ταξινομημένες).
    :param now: η στιγμή αναφοράς — περνάει ρητά ώστε τα tests να είναι ντετερμινιστικά.
    :param window: πόσο πίσω κοιτάμε.
    :param min_reports: ελάχιστο πλήθος διακριτών χρηστών για να δηλώσουμε κατάσταση.
    """
    if min_reports < 1:
        raise ValueError("Το min_reports πρέπει να είναι τουλάχιστον 1")

    # 1. Χρονικό παράθυρο. Αναφορές με μελλοντική ημερομηνία απορρίπτονται ως
    #    αλλοιωμένα δεδομένα — δεν τις εμπιστευόμαστε.
    fresh = [r for r in reports if timedelta(0) <= now - r.created_at <= window]
    if not fresh:
        return _UNKNOWN

    # 2. Μία φωνή ανά χρήστη.
    deduplicated = _latest_per_author(fresh)

    # 3. Ελάχιστο πλήθος.
    if len(deduplicated) < min_reports:
        return LineAssessment(
            status=LineStatus.UNKNOWN,
            estimated_delay=None,
            confidence=0.0,
            sample_size=len(deduplicated),
        )

    # 4. Απόρριψη ακραίων τιμών.
    kept, discarded = _drop_outliers(deduplicated)

    # 5. Στάθμιση: φρεσκάδα επί αξιοπιστία συντάκτη.
    weights = [_recency_weight(now - r.created_at) * max(0.0, r.author_reliability) for r in kept]

    if sum(weights) <= 0:
        # Όλοι οι συντάκτες έχουν μηδενική αξιοπιστία: δεδομένα χωρίς αξία.
        return LineAssessment(
            status=LineStatus.UNKNOWN,
            estimated_delay=None,
            confidence=0.0,
            sample_size=len(kept),
            discarded_as_outliers=discarded,
        )

    # 6. Σταθμισμένη διάμεσος και εμπιστοσύνη.
    estimate = weighted_median([r.delay_minutes for r in kept], weights)
    confidence = _confidence(kept, estimate)

    status = classify(estimate)
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        # Υπάρχει αριθμός, αλλά οι αναφορές διαφωνούν τόσο ώστε να μην είναι
        # έντιμο να τον παρουσιάσουμε ως κατάσταση γραμμής.
        status = LineStatus.UNKNOWN

    return LineAssessment(
        status=status,
        estimated_delay=round(estimate, 2),
        confidence=confidence,
        sample_size=len(kept),
        discarded_as_outliers=discarded,
        used_report_ids=tuple(sorted(r.id for r in kept)),
    )
