# BloodLink

**When a hospital needs O-negative tonight, find donors who can actually give.**

A verified hospital raises an urgent blood request. BloodLink finds donors who are
compatible, eligible today and nearby, texts them nearest first, and tracks every pledge
through to a confirmed donation. The request closes itself the moment enough units are
pledged, even when two donors answer at the same instant.

Hospitals and blood banks are the paying customers. Donors always use BloodLink free.

| | |
|---|---|
| **Live site** | <https://bloodlink-olive.vercel.app> |
| **API documentation** | <https://bloodlink-api-jh3u.onrender.com/api/v1/docs> |
| **Specification** | [`BloodLink_project_spec.md`](BloodLink_project_spec.md) |
| **Research** | [`RESEARCH.md`](RESEARCH.md) |
| **Engineering log** | [`LOG.md`](LOG.md) |

> The API runs on a free plan that sleeps after 15 minutes without traffic. If the site is
> slow to sign in, open the [API health check](https://bloodlink-api-jh3u.onrender.com/api/v1/health)
> and wait up to a minute for `"status":"ok"`.

### Demonstration accounts

The live site is loaded with fictional hospitals and donors in Lagos, Abuja and Enugu. All
accounts end in `@bloodlink.example` and share one password, which is not published here:
ask the project owner.

| Role | Sign in as | Try this |
|---|---|---|
| Hospital staff (verified, Lagos) | `staff.lagos@bloodlink.example` | Open the critical O- request: map, matches, pledged donors, **Donated** |
| Donor (O-, Lagos) | `donor07@bloodlink.example` | "Requests near you", pledge, see directions |
| Administrator | `admin@bloodlink.example` | Review the hospital waiting for verification |
| Hospital staff (pending) | `staff.pending@bloodlink.example` | See what an unverified hospital can and cannot do |

---

## The problem (with evidence)

When a patient needs blood urgently, finding it still depends on who the staff can reach.
Hospitals phone blood banks, relatives and WhatsApp groups one by one. Appeals reach people
who are the wrong blood group, gave too recently or live across the city. Promises made in
a chat are not tracked, so nobody knows who is actually coming.

The planning research pointed to these claims. Each one is being checked against its
original source, with the citation recorded in [`RESEARCH.md`](RESEARCH.md); until then
they are stated here as claims, not facts.

| Claim | Source being checked |
|---|---|
| Nigeria needs roughly 1.8 million pints of blood a year and still struggles to recruit voluntary donors | WHO Africa statement (2021), reported by Nigeria Health Watch |
| Nigeria has one of the lowest rates of voluntary unpaid donation in Africa | *The Guardian* (Nigeria), "Blood for those who need it" |
| Commercial blood banks work in silos, so hospitals lose time searching for blood | MIT Solve, LifeBank "Frontlines of Health" entry |
| Postpartum haemorrhage and road traffic injuries drive constant demand | Prime Progress, feature on J Blood Match |

The interviews with people who handle blood requests (section 1 of `RESEARCH.md`) are the
evidence this product stands on. They are what the pricing and the next priorities will be
set from.

## What it does

1. **A hospital registers, and an administrator verifies it.** Only verified hospitals can
   raise requests, so every alert a donor receives is real.
2. **The hospital raises a request:** blood group, component (whole blood, platelets,
   plasma), units, urgency, deadline.
3. **BloodLink matches donors** who are compatible, eligible today, available, agreed to be
   contacted and within the radius, ranked nearest first. Matching donors are texted, and
   each donor at most once per request.
4. **Donors pledge.** Each pledge takes one unit. The pledge that takes the last unit
   fulfils the request. Donors can cancel, which frees the unit.
5. **The hospital records each outcome:** donated or did not attend. A donation starts the
   donor's waiting period at once.
6. **The hospital sees its performance:** share of requests met, median time to fulfil,
   no-show rate.

Requests past their deadline expire automatically, and every sensitive action is written to
an append-only audit log.

---

## The hard part

Three problems had to be right, not just working. Each is explained here and proven with
tests that run against a real PostgreSQL database.

### 1. No overbooking, even under concurrency

**The risk.** A request needs one more unit. Two donors press "pledge" at the same moment.
Both transactions count the existing pledges, both see one unit free, both insert. The
hospital is promised a donor it does not need, and the second donor travels for nothing.

**The fix.** Pledging is one transaction in
[`app/services/pledges.py`](backend/app/services/pledges.py):

1. lock the donor's row (`SELECT ... FOR UPDATE`), so one donor cannot pledge to two
   requests at once;
2. lock the request's row, so competing pledges for it take turns;
3. under the locks, check the request is open and before its deadline, that the donor is
   compatible and eligible, and count the units already taken;
4. refuse with `409 Conflict` if none are left; otherwise insert the pledge and, if it took
   the last unit, mark the request **fulfilled**.

The second transaction waits at the lock until the first commits, then counts again and
sees the truth. Locks are always taken in the same order (donor, then request), so two
transactions can never wait on each other forever. A unique constraint on
(request, donor) is the last line of defence against a double submission.

**The proof** ([`tests/test_pledge_concurrency.py`](backend/tests/test_pledge_concurrency.py)).
Threads with their own database connections are held at a barrier and released together:

| Scenario | Result with the lock | Result with the lock removed |
|---|---|---|
| 2 donors race for the last unit | 1 accepted, 1 refused | 2 accepted (overbooked) |
| 10 donors race for 3 units | exactly 3 accepted | 9 accepted |
| 1 donor submits twice at once | 1 pledge | crash on the unique constraint |

The "lock removed" column was measured by deleting the `with_for_update()` calls and
re-running the tests, which then fail. The original 50-line experiment is in
[`spikes/concurrent_pledge_spike.py`](spikes/concurrent_pledge_spike.py):
with the lock, two simultaneous pledges for one unit give `[accepted, rejected]`; without
it, `[accepted, accepted]`.

### 2. Rules come from data, not `if` statements

Who may give to whom, and how long a donor must wait between donations, are medical rules.
They change, and they must be reviewable by someone who does not read code.

- **Compatibility** comes from the `blood_compatibility` table (27 recipient and donor
  pairs, seeded from the red-cell chart). Matching asks the table which donor groups a
  patient can receive; there is no chain of `if` statements anywhere.
- **Waiting periods** live in `component_types`, per component and per sex. Age and weight
  limits live in configuration.
- **Eligibility** ([`app/services/eligibility.py`](backend/app/services/eligibility.py)) is a
  pure function: it takes the donor, the rules, the deferrals and the date, and touches no
  database and no clock, so every boundary can be tested exactly. The donor's dashboard,
  matching and pledging all use this one function, so they can never disagree.

**Tests** ([`tests/test_matching.py`](backend/tests/test_matching.py),
[`tests/test_eligibility.py`](backend/tests/test_eligibility.py)):
- each of the eight recipient groups matches exactly the donor groups in the published
  chart, checked against a copy of the chart typed out separately from the seed data;
- a donor one day inside the waiting period is excluded, and on the boundary day included;
- changing an interval in `component_types` changes the result with no code change;
- an active deferral excludes an otherwise eligible donor.

> The waiting periods and the age and weight limits are working placeholders. They are to
> be replaced with the national transfusion service and WHO figures cited in `RESEARCH.md`
> before BloodLink is used for anything beyond demonstration.

### 3. Correct distance search, nearest first

- Distance is the haversine great-circle formula
  ([`app/services/distance.py`](backend/app/services/distance.py)).
- The database first discards donors outside a bounding box around the hospital, a cheap
  indexed filter. The exact distance is then worked out only for the few that remain, and
  anyone outside the circle is dropped. The box is calculated so that it always contains
  the whole circle, including near the poles.

**Tests** ([`tests/test_distance.py`](backend/tests/test_distance.py)):
- Lagos to Abuja is about 530 km, within tolerance;
- 72 points exactly on a circle all fall inside its bounding box, at three latitudes;
- donors outside the radius are excluded;
- results are ordered nearest first.

### Also hard: alerts that are never sent twice

An alert job that runs twice, or a hospital that clicks twice, must not text a donor twice
at 2 AM about the same emergency. The service claims each donor with
`INSERT ... ON CONFLICT DO NOTHING` against a unique (request, donor, channel) constraint,
and only the run that made the claim sends the message. Four alert runs started at the same
instant text each of five donors exactly once
([`tests/test_notifications.py`](backend/tests/test_notifications.py)).

---

## Why this design (with sources)

| Decision | Why |
|---|---|
| **Only verified hospitals can raise requests** | Chat-based matching services have no verification, so donors cannot tell a real emergency from a scam. Verification is what makes an alert worth answering. |
| **Contact details are revealed only after a donor pledges** | Hospitals see matched donors anonymously (blood group, area, distance). A donor's name and phone number are shared with one hospital, only by the donor's own action. |
| **Donor positions on the map are rounded to about 1 km** | Enough to see where help is clustered, not enough to find a home. Exact coordinates never leave the server. |
| **No payment for blood** | WHO's principle of voluntary, unpaid donation. Hospitals pay for the coordination service, never for blood. |
| **Rules as data** | Compatibility and waiting periods can be checked and corrected by clinical staff without a code change (see the hard part above). |
| **Expiry checked when requests are read** | Requests past their deadline are expired whenever they are read, and a sweep command does the same for every hospital. Correctness never depends on a scheduler running on time. |
| **Alerts go out at most once** | Missing one alert after a crash is safer than texting a donor twice. A message left in the "queued" state is not retried automatically. |
| **Termii, with a console fallback** | Termii is a Nigerian SMS gateway, but it has no sandbox: every message is real and paid for. The API records alerts without sending them until a sender ID is approved, and tests can never send a real message. |
| **The site forwards API calls** | The browser only ever talks to the site's own address, so the session cookie is first-party. Calling the API's address directly would make it a third-party cookie, which Safari blocks. |
| **The platform coordinates; it does not screen** | Donor-facing text says final eligibility is decided by clinical staff at the donation site. |

The cited sources behind these decisions (donor eligibility guidance, the red-cell
compatibility chart, Nigerian blood-supply figures and the Nigeria Data Protection Act 2023
for health data) are recorded in [`RESEARCH.md`](RESEARCH.md) section 3, each with the
sentence on how it changed the design.

## Who pays

| Customer | What they get | Model |
|---|---|---|
| **Private hospitals** (first: Lagos and Abuja) | Urgent requests, matching, alerts, pledge tracking, performance figures | Free pilot for three months, in exchange for anonymised fulfilment data. Then a monthly subscription priced by request volume. |
| **Blood banks and hospital groups** | Several sites, donor drives, reporting | Annual agreement |
| **Employers, universities, HMOs** | Sponsored donor drives and impact reports | Per drive or sponsorship |
| **Governments and NGOs** | Demand and fulfilment dashboards | Licence |
| **Donors** | Everything they need to give | **Always free** |

Prices are being set with the pilot hospitals, from what finding blood costs them today
(staff time, blood bank fees, failed requests). They are not guessed. Private hospitals
come first because public hospitals have longer buying cycles.

### Competitors

| | What it does | What it misses |
|---|---|---|
| **LifeBank** | Blood bank inventory and delivery to hospitals | Bulk logistics, not live donor fulfilment for an urgent case |
| **J Blood Match** | Free donor and recipient matching over chat bots | No hospital verification; the donation is arranged off-platform and never tracked |
| **WhatsApp groups and phone trees** | What hospitals use today | No eligibility check, no tracking, no record |

BloodLink is the closed loop between them: verified requests, enforced eligibility, tracked
donations.

---

## Architecture

```
Browser ──> Vercel: Next.js site ──(/api/v1/* forwarded)──> Render: FastAPI ──> Neon: PostgreSQL
                                                                 │
                                                                 └──> Termii (SMS), when configured
```

| Layer | Technology |
|---|---|
| Web | Next.js (Pages Router), TypeScript, Tailwind CSS, shadcn/ui, Leaflet with OpenStreetMap |
| API | FastAPI, SQLModel, Pydantic, Alembic, argon2 password hashing, JWT in an httpOnly cookie |
| Database | PostgreSQL (Docker locally, Neon in production) |
| Tooling | `uv`, `ruff`, `pytest`, ESLint, `tsc` |

Code is layered: routes validate input and delegate, services hold the business rules,
models only describe tables. The data model (11 tables, UUID keys, constrained statuses) is
drawn in [`docs/erd.md`](docs/erd.md).

### API

All routes are under `/api/v1`; every one is documented at
[`/api/v1/docs`](https://bloodlink-api-jh3u.onrender.com/api/v1/docs).

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Donors | `GET`/`PUT /donors/me`, `PATCH /donors/me/availability`, `GET /donors/me/eligibility`, `GET /donors/me/requests`, `GET /donors/me/pledges` |
| Hospitals | `POST /hospitals`, `GET`/`PUT /hospitals/me` |
| Admin | `GET /admin/hospitals`, `GET /admin/hospitals/{id}`, `POST /admin/hospitals/{id}/verify`, `POST /admin/hospitals/{id}/reject` |
| Requests | `POST`/`GET /requests`, `GET /requests/{id}`, `POST /requests/{id}/close`, `GET /requests/{id}/matches`, `GET`/`POST /requests/{id}/alerts` |
| Pledges | `POST`/`GET /requests/{id}/pledges`, `DELETE /pledges/{id}`, `POST /pledges/{id}/donated`, `POST /pledges/{id}/no-show` |
| Other | `GET /components`, `GET /stats/hospital`, `GET /health`, `GET /health/ready` |

Every protected route checks the caller's role and ownership. Another hospital's request,
or another donor's pledge, is reported as not found, so its existence is never revealed.

---

## Running it locally

Needs Docker Desktop, [`uv`](https://docs.astral.sh/uv/), Node.js LTS and Git Bash.

```bash
# Environment file: then edit the database password and the secret key
cp .env.example .env

# PostgreSQL in Docker, on host port 5433
docker compose up -d db
```

**API**, from `backend`:

```bash
uv sync
uv run alembic upgrade head             # create the tables
uv run python -m scripts.seed           # compatibility chart and component types
uv run python -m scripts.seed_demo      # optional: demo hospitals, donors and accounts
uv run uvicorn app.main:app --reload    # http://localhost:8000/api/v1/docs
```

`seed_demo` needs `DEMO_PASSWORD` in `.env` (see `.env.example`). It prints the demo
accounts and changes nothing if run again.

**Web app**, from `frontend`:

```bash
npm install
npm run dev                             # http://localhost:3000
```

**Other commands**, from `backend`:

```bash
uv run python -m scripts.create_admin --email you@example.com --name "Your Name"
uv run python -m scripts.expire_requests   # expire overdue requests for every hospital
```

pgAdmin 4 can connect to `localhost:5433` with the credentials in `.env`.

### Tests and checks

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npx tsc --noEmit && npx eslint .
```

The backend has 316 tests. Those that need the database run against a separate
`bloodlink_test` database in the same container, so development data is never touched. If
PostgreSQL is not running they are skipped with a message, not failed. Every test is forced
onto the console SMS sender, so no test can send a real message.

### Text messages

By default (`SMS_PROVIDER=console`) alerts are recorded and written to the API log without
being sent. To send real messages through Termii, set `SMS_PROVIDER=termii`,
`TERMII_API_KEY`, `TERMII_BASE_URL` and an approved `TERMII_SENDER_ID`. If any is missing or
the sender ID is malformed, the API stays on the console sender and logs a warning.

## Deployment

Neon for PostgreSQL, Render for the API (Docker, Frankfurt region), Vercel for the site.
Every merge to `main` redeploys both. The API's container updates the schema and reference
data on every start, so no manual step is needed. Step-by-step instructions are in
[`docs/deployment.md`](docs/deployment.md).

## Project layout

```
backend/
  app/
    api/routes/    one module per area (auth, donors, hospitals, admin, requests, pledges, ...)
    core/          settings, security, password policy, rate limiting
    models/        one module per table
    schemas/       request and response models
    services/      business rules: eligibility, matching, pledges, notifications, stats
    db/            session, reference seed, demonstration seed
  alembic/         migrations
  scripts/         seed, seed_demo, create_admin, expire_requests
  tests/
frontend/
  pages/           Pages Router screens for donors, hospitals and administrators
  components/      UI building blocks, forms, map, request and pledge components
  lib/             API client, formatting, routing helpers
spikes/            the concurrency experiment
docs/              data model and deployment guide
```

## Safety and compliance

- **No payment for blood**, following the WHO voluntary unpaid donation principle.
- **Health and location data** is sensitive personal data under the Nigeria Data Protection
  Act 2023. BloodLink asks for explicit consent to be contacted, stores only what matching
  needs, shares contact details only after a pledge, and keeps phone numbers and tokens out
  of logs. A data protection impact assessment and advice from a qualified professional are
  needed before real use.
- **Not medical screening:** final eligibility is always decided by clinical staff at the
  donation site.
- **Security:** argon2 password hashing, a 15-character minimum password following NIST SP
  800-63B-4, httpOnly session cookies, sign-in rate limiting, and an append-only audit log
  of verifications, request changes and pledge outcomes.

## What comes next

Notification waves that widen the radius after a timeout; a donor reliability score; quiet
hours; WhatsApp and USSD alerts; partner blood bank stock checked before donors are asked;
Paystack billing; and a multilingual offline app (English, Pidgin, Yoruba, Hausa, Igbo).
The schema is designed so that none of these needs existing data to be rewritten.
