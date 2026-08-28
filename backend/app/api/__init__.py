"""HTTP layer — FastAPI routers.

Οι routers μεταφράζουν HTTP σε κλήσεις υπηρεσιών και πίσω. Δεν περιέχουν
επιχειρησιακή λογική: κάθε απόφαση για το *τι* σημαίνουν τα δεδομένα ανήκει στο
``app/core/``.
"""

from app.api import admin, auth, lines, reports

__all__ = ["admin", "auth", "lines", "reports"]
