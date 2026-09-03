# PLAN.md

Πλάνο εκτέλεσης. Ενημερώθηκε στο τέλος κάθε φάσης.

**Προθεσμία: Πέμπτη 24/09/2026 23:55.** Στόχος υποβολής: **Τετάρτη 23/09**.

## Φάσεις

| Φάση | Περίοδος | Στόχος | Κατάσταση |
|---|---|---|---|
| 0 | 26/08 – 28/08 | Ανάλυση, repo, planning files, σκελετός CI | ✅ Ολοκληρώθηκε |
| 1 | 28/08 | Πυρήνας λογικής, unit tests, πράσινο pipeline | ✅ Ολοκληρώθηκε |
| 2 | 28/08 – 30/08 | Μοντέλο δεδομένων, migrations, REST API | ✅ Ολοκληρώθηκε |
| 3 | 30/08 – 03/09 | Docker, CD, deployment στο Render, screenshots | ✅ Ολοκληρώθηκε |
| 4 | 03/09 | Συγγραφή ενιαίου παραδοτέου | ✅ Ολοκληρώθηκε |

Οι φάσεις ολοκληρώθηκαν νωρίτερα από το αρχικό χρονοδιάγραμμα. Ο χρόνος που
περίσσεψε επενδύθηκε σε ποιότητα ελέγχων και τεκμηρίωσης αντί για επέκταση του
εύρους — βλ. §11.1 του παραδοτέου.

## Φάση 0 — Ανάλυση και στήσιμο ✅

- [x] `CLAUDE.md` με τους κανόνες του έργου
- [x] `PLAN.md`, `docs/ARCHITECTURE.md`, `TASKS.md`, `docs/agent-log.md`
- [x] CATWOE και Θεμελιακός Ορισμός → `docs/01-catwoe.md`
- [x] User Stories με κριτήρια αποδοχής → `docs/02-user-stories.md`
- [x] User Journeys → `docs/03-user-journeys.md`
- [x] Σκελετός backend, workflow CI, Dockerfile, docker-compose

## Φάση 1 — Πυρήνας ✅

- [x] `app/core/status.py` — ταξινόμηση κατάστασης
- [x] `app/core/aggregation.py` — μηχανή συνάθροισης
- [x] `app/core/ratelimit.py` — περιορισμός ρυθμού
- [x] `app/core/reliability.py` — βαθμός αξιοπιστίας
- [x] `/health` endpoint και smoke test
- [x] Push στο GitHub, πρώτο πράσινο run μετά από διόρθωση
- [x] Branch protection στο `main` με required checks

## Φάση 2 — Δεδομένα και API ✅

- [x] Μοντέλα SQLAlchemy και Alembic migration `0001_initial`
- [x] Test απόκλισης μοντέλων και migrations
- [x] `app/services/line_status.py` — γέφυρα βάσης και πυρήνα
- [x] `app/seed.py` — ιδεμπόσταστο seed με υπαρκτές γραμμές
- [x] Authentication με JWT, ρόλοι `PASSENGER` / `OPERATOR`
- [x] `POST /api/v1/reports` με έλεγχο ρυθμού → US-01, US-02
- [x] `GET /api/v1/lines` και `/lines/{id}` → US-04, US-05
- [x] `POST /api/v1/reports/{id}/confirm` → US-03
- [x] `GET /api/v1/admin/dashboard` με έλεγχο ρόλου → US-08
- [x] Integration tests με `TestClient`

## Φάση 3 — Παράδοση ✅

- [x] Multi-stage `Dockerfile` και `docker-compose.yml` για τοπικό staging
- [x] Push image στο GHCR με ετικέτες `sha-` και έκδοσης
- [x] `render.yaml` (Infrastructure as Code)
- [x] Υπηρεσία στο Render + PostgreSQL· `RENDER_DEPLOY_HOOK` ως secret
- [x] Κανονικοποίηση URL PostgreSQL — σφάλμα ορατό μόνο στην παραγωγή
- [x] Φόρτωση δεδομένων αναφοράς κατά την εκκίνηση του container
- [x] Ζωντανή εφαρμογή σε δημόσια διεύθυνση
- [x] Συλλογή αποδεικτικών στιγμιότυπων

## Φάση 4 — Συγγραφή ✅

- [x] Σύνθεση του ενιαίου παραδοτέου με τα δέκα σημεία της εκφώνησης
- [x] Ενσωμάτωση δώδεκα στιγμιότυπων με λεζάντες
- [x] Έλεγχος: κάθε ισχυρισμός τεκμηριώνεται με στιγμιότυπο ή commit
- [ ] Υποβολή

## Τι δεν έγινε, σκόπιμα

- Γραφική διεπαφή χρήστη — βλ. `docs/ARCHITECTURE.md` και §11.1 του παραδοτέου
- Ζωντανή σύνδεση σε GTFS, ειδοποιήσεις push, χάρτες
- Caching εκτιμήσεων — καταγράφεται ως γνωστός περιορισμός
