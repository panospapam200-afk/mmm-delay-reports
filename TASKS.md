# TASKS.md

Τρέχουσα λίστα εργασιών. Ό,τι δεν είναι εδώ, δεν δουλεύεται τώρα.

## Αμέσως επόμενα

1. **Email στον καθηγητή** για επίσημη ανάθεση του θέματος.
2. Ενεργοποίηση branch protection στο `main` με required checks· **screenshot**.
3. Merge του `feat/data-model` μέσω PR· **screenshot** του PR με πράσινα checks.

## Ολοκληρωμένα feature branches

- `fix/ci-image-name` — κανονικοποίηση ονόματος Docker image
- `feat/data-model` — μοντέλα, migrations, seed, υπηρεσία κατάστασης γραμμής
- `feat/auth-and-api` — JWT, ρόλοι, endpoints γραμμών/αναφορών/dashboard

## Επόμενο feature branch: `feat/frontend-shell`

- [ ] Vite + React + TypeScript, κλήσεις στο API
- [ ] Λίστα γραμμών με χρωματική ένδειξη κατάστασης και βαθμό εμπιστοσύνης
- [ ] Φόρμα υποβολής αναφοράς, χειρισμός του 429
- [ ] Οθόνη χειριστή
- [ ] Vitest για τα κρίσιμα components

## Μετά

- Multi-stage Dockerfile που χτίζει και σερβίρει το frontend
- Υπηρεσία στο Render, `RENDER_DEPLOY_HOOK` και `JWT_SECRET` ως secrets
- Συλλογή screenshots για τα σημεία 9 και 10

## Σκόπιμα εκτός εύρους

- Push notifications
- Χάρτες και γεωγραφική οπτικοποίηση
- Ζωντανή σύνδεση σε GTFS / τηλεματική
- Mobile εφαρμογή
- Caching επιπέδου παραγωγής

*Καθεμία από αυτές θα ήταν ωραία. Καμία δεν βαθμολογείται.*
