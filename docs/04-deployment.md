# 4. Continuous Delivery και Deployment

> Παραδοτέο, σημείο 10.

## Πώς πακετάρεται η εφαρμογή

Multi-stage `Dockerfile`:

1. **builder** — δημιουργεί virtualenv και εγκαθιστά τις εξαρτήσεις.
2. **runtime** — αντιγράφει *μόνο* το virtualenv, τον κώδικα και τα migrations.
   Τα εργαλεία μεταγλώττισης δεν καταλήγουν στην τελική εικόνα.

Η εφαρμογή τρέχει ως χρήστης `appuser` (uid 10001), **ποτέ ως root**. Η εικόνα
φέρει `HEALTHCHECK` και εκκινεί με:

```
alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Τρία στάδια σε σειρά, καθένα προϋπόθεση του επόμενου: το σχήμα φτάνει στην
έκδοση που περιμένει ο κώδικας, τα δεδομένα αναφοράς υπάρχουν, και τότε
δέχεται αιτήματα ο server. **Αν οποιοδήποτε αποτύχει, το container δεν
ξεκινά** — προτιμότερο από εφαρμογή που τρέχει πάνω σε λάθος σχήμα ή χωρίς
γραμμές.

### Γιατί το seed γίνεται εδώ και όχι με το χέρι

Η δωρεάν βαθμίδα του Render **δεν παρέχει πρόσβαση σε shell**. Δεν υπάρχει
τρόπος να συνδεθεί κανείς στο container για να φορτώσει τα αρχικά δεδομένα.
Ο περιορισμός αποδείχθηκε χρήσιμος: ανάγκασε το bootstrap των δεδομένων
αναφοράς να γίνει μέρος της **αυτοματοποιημένης** διαδικασίας εκκίνησης αντί
για χειροκίνητο βήμα που κάποιος θα ξεχνούσε. Είναι ακίνδυνο σε κάθε
επανεκκίνηση, γιατί η `seed()` είναι ιδεμπόσταστη.

## Πώς παραδίδεται

| Στάδιο | Τι συμβαίνει | Πότε |
|---|---|---|
| Build | Docker image, push στο GHCR με ετικέτες `sha-<commit>` και `v<έκδοση>` | Μόνο σε push στο `main` |
| Smoke test | Το image τρέχει και ερωτάται το `/health` μέσω του digest του | Αμέσως μετά το build |
| Deploy | Κλήση deploy hook του Render | Μόνο από το `main` |

**Η διάκριση Delivery / Deployment:** σε Pull Request τρέχουν μόνο τα στάδια
lint και test. Ο κώδικας είναι *παραδοτέος* (Continuous Delivery) αλλά δεν
*παραδίδεται* αυτόματα. Μόνο μετά το merge στο `main` χτίζεται εικόνα και
γίνεται deployment (Continuous Deployment). Η γραμμή αυτή είναι σχεδιαστική
απόφαση, όχι παράλειψη.

## Περιβάλλον παραγωγής: Render

Η υποδομή περιγράφεται στο `render.yaml` (Infrastructure as Code) αντί να
στηθεί με κλικ:

- **Web service** από το `Dockerfile`, δωρεάν βαθμίδα, `healthCheckPath: /health`
- **PostgreSQL** δωρεάν βαθμίδα· το `DATABASE_URL` περνά αυτόματα στην υπηρεσία
- **`JWT_SECRET`** παράγεται από το Render (`generateValue: true`) και δεν
  υπάρχει πουθενά στο repository
- **`autoDeploy: false`** — το deployment το ενεργοποιεί το pipeline μέσω hook,
  ώστε να μη γίνεται deploy κώδικας που δεν πέρασε από τα tests

### Ένα σφάλμα που εμφανίζεται μόνο στην παραγωγή

Το Render δίνει URL της μορφής `postgres://...`, ενώ το SQLAlchemy 2 απαιτεί
ρητό οδηγό (`postgresql+psycopg://...`). Χωρίς μετατροπή η εφαρμογή σκάει στην
εκκίνηση με `Can't load plugin: sqlalchemy.dialects:postgres`.

Το σφάλμα **δεν θα φαινόταν ποτέ** τοπικά ή στα tests, γιατί εκεί τρέχει
SQLite. Η μετατροπή γίνεται στο `app/config.py` και καλύπτεται από tests στο
`tests/test_config.py` — δηλαδή ένα σφάλμα παραγωγής μετατράπηκε σε κάτι που
ένα unit test μπορεί να πιάσει.

## Τοπικό εξομοιωμένο περιβάλλον (Local Staging)

```bash
docker compose up --build
curl http://localhost:8000/health
```

Το `docker-compose.yml` σηκώνει την **ίδια εικόνα** που παράγει το pipeline,
μαζί με PostgreSQL — όχι μια «παρόμοια» τοπική εγκατάσταση.

## Βήματα στήσιμου (μία φορά)

1. Render → **New → Blueprint** → επιλογή του repository → Apply
2. Στην υπηρεσία: **Settings → Deploy Hook** → αντιγραφή του URL
3. GitHub → **Settings → Secrets and variables → Actions → New repository secret**
   → όνομα `RENDER_DEPLOY_HOOK`, τιμή το URL
4. Προαιρετικά: μεταβλητή `RENDER_SERVICE_URL` με τη δημόσια διεύθυνση, ώστε να
   εμφανίζεται στο περιβάλλον `production` του GitHub

Μέχρι να οριστεί το secret, το στάδιο 4 του pipeline καταγράφει προειδοποίηση
και τερματίζει κανονικά — δεν κοκκινίζει το build για μια ρύθμιση που λείπει.
