# Σύστημα Αναφοράς Καθυστερήσεων ΜΜΜ

Crowdsourced σύστημα αναφοράς καθυστερήσεων σε γραμμές μέσων μαζικής μεταφοράς.
Οι επιβάτες υποβάλλουν αναφορές από τη στάση· το σύστημα τις σταθμίζει ως προς
φρεσκάδα, συμφωνία και αξιοπιστία του συντάκτη, και παράγει εκτίμηση κατάστασης
ανά γραμμή **με ρητό βαθμό εμπιστοσύνης**.

Ατομική εργασία στο μάθημα «Μεθοδολογίες Πληροφοριακών Συστημάτων».

## Γρήγορη εκκίνηση

```bash
cd backend
pip install -e ".[dev]"
pytest --cov=app --cov-report=term-missing
uvicorn app.main:app --reload
```

Τοπικό εξομοιωμένο περιβάλλον με PostgreSQL:

```bash
docker compose up --build
curl http://localhost:8000/health
```

## Τεκμηρίωση

| Αρχείο | Περιεχόμενο |
|---|---|
| [`docs/01-catwoe.md`](docs/01-catwoe.md) | Ανάλυση CATWOE και Θεμελιακός Ορισμός |
| [`docs/02-user-stories.md`](docs/02-user-stories.md) | User Stories με κριτήρια αποδοχής |
| [`docs/03-user-journeys.md`](docs/03-user-journeys.md) | User Journeys ανά ρόλο |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Αρχιτεκτονική, στοίβα, απορριφθείσες εναλλακτικές |
| [`docs/agent-log.md`](docs/agent-log.md) | Ημερολόγιο ανάπτυξης με coding agents |
| [`PLAN.md`](PLAN.md) | Φάσεις και χρονοδιάγραμμα |
| [`CLAUDE.md`](CLAUDE.md) | Κανόνες για coding agents |

## Αρχιτεκτονική με μία πρόταση

Ο πυρήνας της επιχειρησιακής λογικής (`backend/app/core/`) δεν γνωρίζει ότι
υπάρχει HTTP ή βάση δεδομένων — δέχεται δομές δεδομένων, επιστρέφει δομές
δεδομένων, και ο χρόνος περνάει πάντα ως όρισμα. Γι' αυτό όλο το test suite
τρέχει σε λιγότερο από ένα δευτερόλεπτο μέσα στο pipeline.

## Πώς αντιμετωπίζεται ο θόρυβος

| Πρόβλημα | Μηχανισμός |
|---|---|
| Παλιές αναφορές | Χρονικό παράθυρο 30 λεπτών με εκθετική απόσβεση (ημιπερίοδος 10΄) |
| Ένας χρήστης, πολλές αναφορές | Μία φωνή ανά χρήστη — μετράει η πιο πρόσφατη |
| Υπερβολικές τιμές | Φίλτρο MAD, ανθεκτικό σε ακραίες τιμές |
| Κακόβουλοι χρήστες | Βαθμός αξιοπιστίας με εξομάλυνση Laplace + περιορισμός ρυθμού |
| Αντιφατικά δεδομένα | Επιστροφή `UNKNOWN` αντί για παραπλανητικό μέσο όρο |

## CI/CD

```
Pull Request →  ① Lint  →  ② Tests (Python 3.11 & 3.12, κάλυψη ≥ 90%)
main         →  ① Lint  →  ② Tests  →  ③ Docker build + push (GHCR)  →  ④ Deploy (Render)
```

Branching: trunk-based με βραχύβια feature branches. Commits κατά Conventional
Commits. Εκδόσεις με semantic versioning tags.

## Κατάσταση

- ✅ Πυρήνας επιχειρησιακής λογικής, 68 unit tests, 100% κάλυψη
- ✅ CI/CD workflow, Dockerfile, τοπικό staging
- 🟡 API endpoints και βάση δεδομένων
- ⬜ React frontend
- ⬜ Deployment στο Render
