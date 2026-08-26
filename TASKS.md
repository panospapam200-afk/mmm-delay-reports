# TASKS.md

Τρέχουσα λίστα εργασιών. Ό,τι δεν είναι εδώ, δεν δουλεύεται τώρα.

## Αμέσως επόμενα

1. **Email στον καθηγητή** για επίσημη ανάθεση του θέματος.
2. `git init` και πρώτο commit· δημιουργία repo στο GitHub.
3. Ενεργοποίηση branch protection στο `main`:
   *Settings → Branches → Add rule → Require status checks* (`lint`, `test`).
4. Push· επιβεβαίωση ότι το pipeline είναι πράσινο· **screenshot**.

## Επόμενο feature branch: `feat/data-model`

- [ ] `app/models.py` — User, Line, Stop, Report, Confirmation
- [ ] `app/db.py` — session factory, SQLite στα tests
- [ ] Πρώτο Alembic migration
- [ ] `app/seed.py` — υπαρκτές γραμμές και στάσεις

## Μετά

- `feat/auth` — εγγραφή, σύνδεση, JWT, ρόλοι
- `feat/reports-api` — υποβολή αναφοράς με έλεγχο ρυθμού
- `feat/status-api` — endpoint κατάστασης γραμμής
- `feat/frontend-shell` — Vite, routing, κλήσεις API
- `feat/operator-dashboard` — οθόνη χειριστή

## Σκόπιμα εκτός εύρους

- Push notifications
- Χάρτες και γεωγραφική οπτικοποίηση
- Ζωντανή σύνδεση σε GTFS / τηλεματική
- Mobile εφαρμογή
- Caching επιπέδου παραγωγής

*Καθεμία από αυτές θα ήταν ωραία. Καμία δεν βαθμολογείται.*
