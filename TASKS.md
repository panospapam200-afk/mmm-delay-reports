# TASKS.md

Τρέχουσα λίστα εργασιών. Ό,τι δεν είναι εδώ, δεν δουλεύεται τώρα.

## Αμέσως επόμενα

1. **Email στον καθηγητή** για επίσημη ανάθεση του θέματος.
2. Ενεργοποίηση branch protection στο `main` με required checks· **screenshot**.
3. Merge του `feat/data-model` μέσω PR· **screenshot** του PR με πράσινα checks.

## Ολοκληρωμένα feature branches

- `fix/ci-image-name` — κανονικοποίηση ονόματος Docker image
- `feat/data-model` — μοντέλα, migrations, seed, υπηρεσία κατάστασης γραμμής

## Επόμενο feature branch: `feat/auth`

- [ ] Hashing κωδικών με passlib/bcrypt
- [ ] `POST /api/v1/auth/register`, `POST /api/v1/auth/login`
- [ ] Έκδοση και επαλήθευση JWT· εξάρτηση `current_user`
- [ ] Έλεγχος ρόλου για τα endpoints του χειριστή

## Μετά
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
