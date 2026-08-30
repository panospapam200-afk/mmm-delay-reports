# PLAN.md

Πλάνο εκτέλεσης. Ενημερώνεται στο τέλος κάθε φάσης.

**Προθεσμία: Πέμπτη 24/09/2026 23:55.** Στόχος υποβολής: **Τετάρτη 23/09**.

## Φάσεις

| Φάση | Περίοδος | Στόχος | Κατάσταση |
|---|---|---|---|
| 0 | 26/08 – 31/08 | Ανάλυση, repo, planning files, σκελετός CI | ✅ Ολοκληρώθηκε |
| 1 | 01/09 – 07/09 | Πυρήνας λογικής, unit tests, πράσινο pipeline | ✅ Ολοκληρώθηκε νωρίτερα |
| 2 | 08/09 – 14/09 | API endpoints, βάση, React frontend | 🟡 Σε εξέλιξη |
| 3 | 15/09 – 20/09 | Docker, CD, deployment στο Render, screenshots | ⬜ |
| 4 | 21/09 – 23/09 | Συγγραφή ενιαίου παραδοτέου | ⬜ |

## Φάση 0 — Ανάλυση και στήσιμο ✅

- [x] `CLAUDE.md` με τους κανόνες του έργου
- [x] `PLAN.md`, `docs/ARCHITECTURE.md`, `TASKS.md`, `docs/agent-log.md`
- [x] CATWOE και Θεμελιακός Ορισμός → `docs/01-catwoe.md`
- [x] User Stories με κριτήρια αποδοχής → `docs/02-user-stories.md`
- [x] User Journeys → `docs/03-user-journeys.md`
- [x] Σκελετός backend, workflow CI, Dockerfile, docker-compose
- [ ] **Επίσημη ανάθεση θέματος από τον καθηγητή** ← μπλοκάρει τα πάντα

## Φάση 1 — Πυρήνας ✅

- [x] `app/core/status.py` — ταξινόμηση κατάστασης
- [x] `app/core/aggregation.py` — μηχανή συνάθροισης
- [x] `app/core/ratelimit.py` — περιορισμός ρυθμού
- [x] `app/core/reliability.py` — βαθμός αξιοπιστίας
- [x] 68 unit tests, 100% κάλυψη πυρήνα
- [x] `/health` endpoint και smoke test
- [x] Push στο GitHub, πρώτο πράσινο run (μετά από διόρθωση) → **screenshot**
- [ ] Branch protection στο `main` με required checks → **screenshot**
- [x] Μοντέλα SQLAlchemy και πρώτο Alembic migration

## Φάση 2 — API και frontend 🟡

- [x] Μοντέλα, migrations, seed δεδομένα, υπηρεσία κατάστασης γραμμής
- [x] Authentication με JWT, ρόλοι `passenger` / `operator`
- [x] `POST /api/v1/reports` με έλεγχο ρυθμού → US-01, US-02
- [x] `GET /api/v1/lines` και `/lines/{id}` → US-04, US-05
- [x] `POST /api/v1/reports/{id}/confirm` → US-03
- [x] `GET /api/v1/admin/dashboard` με έλεγχο ρόλου → US-08
- [x] Integration tests με `TestClient` (149 tests συνολικά)
- [ ] React: λίστα γραμμών, φόρμα αναφοράς, dashboard χειριστή
- [ ] Vitest για τα κρίσιμα components

## Φάση 3 — Παράδοση ⬜

- [x] `render.yaml` (Infrastructure as Code) και τεκμηρίωση deployment
- [ ] Multi-stage Dockerfile με το build του frontend
- [ ] Push image στο GHCR με ετικέτες `sha-` και `v`
- [ ] Υπηρεσία στο Render + `RENDER_DEPLOY_HOOK` secret
- [ ] Τοπικό staging με `docker compose up` → **screenshot**
- [ ] Ζωντανή εφαρμογή σε δημόσιο URL → **screenshot**
- [ ] Ένα αποτυχημένο run που διορθώθηκε → **screenshot**

## Φάση 4 — Συγγραφή ⬜

- [ ] Σύνθεση των δέκα σημείων με τη σειρά της εκφώνησης
- [ ] Ενσωμάτωση screenshots με λεζάντες
- [ ] Έλεγχος: κάθε ισχυρισμός τεκμηριώνεται με screenshot ή commit
- [ ] Υποβολή

## Κίνδυνοι

| Κίνδυνος | Αντιμετώπιση |
|---|---|
| Καθυστέρηση στην ανάθεση θέματος | Η Φάση 0 δεν εξαρτάται από αυτήν· email σήμερα |
| Το free tier του Render «κοιμάται» | Τα screenshots τραβιούνται αμέσως μετά το deploy |
| Το frontend τρώει τον χρόνο της Φάσης 2 | Ελάχιστη διεπαφή· η βαθμολογία είναι στο pipeline |
| Screenshots αφημένα για το τέλος | Λίστα στο `PLAN.md`· τραβιούνται στη φάση τους |
