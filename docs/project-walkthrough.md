# BloodLink: product and codebase walkthrough

A guide for stand-ups, demos and the viva. It covers what BloodLink does, what was built
each day, and a tour of the code, including one request traced end to end through the
files.

- **Live site:** <https://bloodlink-olive.vercel.app>
- **API docs:** <https://bloodlink-api-jh3u.onrender.com/api/v1/docs>

---

## 1. BloodLink in one minute

**The problem.** When a patient needs blood urgently, Nigerian hospitals still search by
phone and WhatsApp. Appeals reach people with the wrong blood group, people who gave last
month, and people across the city. Nobody tracks who promised to come.

**What BloodLink does.**

1. A **verified hospital** raises a request: blood group, component, units, urgency,
   deadline.
2. BloodLink finds donors who are **compatible, eligible today, available, consenting and
   nearby**, ranks them nearest first, and **texts them**, each donor once at most.
3. **Donors pledge.** Each pledge takes one unit. The request **closes itself** when the
   last unit is taken, even if two donors press the button at the same moment.
4. The hospital records **donated** or **did not attend**. A donation starts the donor's
   waiting period immediately.
5. The hospital sees its **performance**: share of requests met, median time to fulfil,
   no-show rate.

**Who pays.** Hospitals and blood banks pay; donors never do. Pilot hospitals use it free
while prices are set with them.

**The three hard parts.**

1. **No overbooking under concurrency:** row locks, proven by racing threads.
2. **Medical rules come from data:** compatibility and waiting periods are database tables,
   not `if` statements.
3. **Correct distance search:** haversine distance with a bounding-box prefilter, nearest
   first.

---

## 2. The three users and what each can do

| User | Can do | Main screens |
|---|---|---|
| **Donor** | Register; set blood group and location; see eligibility per component; pause alerts; see "Requests near you"; pledge or cancel; see history | `/donor`, `/donor/profile` |
| **Hospital staff** | Register the hospital; after verification, raise and close requests; see the map and ranked anonymous matches; text donors; see pledged donors' contacts; record outcomes; see performance figures | `/hospital`, `/hospital/requests`, `/hospital/requests/new`, `/hospital/requests/[id]` |
| **Administrator** | Review hospitals: verify, or reject with a reason | `/admin`, `/admin/hospitals/[id]` |

Public pages: `/` (landing), `/login`, `/register` (`?as=hospital` or `?as=donor` skips
the account-type question).

---

## 3. What was built, day by day

Each day is a Git branch, merged to `main` and tagged `day-1` to `day-5`.

### Day 1: foundation (2 to 4 October)
- Repository, Docker PostgreSQL, settings, database session, health checks.
- All 11 tables, the first migration, and the seed for the compatibility chart and
  component types.
- Next.js app with Tailwind and shadcn/ui; typed API client.
- **Concurrency spike:** two simultaneous pledges for the last unit were both accepted
  without a row lock, and exactly one with it. This decided the pledge design.

*Stand-up line:* "Foundation is in: schema, migrations, reference data, and a spike that
proves the locking approach."

### Day 2: accounts, profiles and verification (4 to 7 October)
- **Auth:** registration, sign-in and sign-out; argon2 hashing; JWT in an httpOnly cookie;
  15-character password policy; sign-in rate limiting; role guards.
- Donor profiles and the **eligibility rules module**.
- Hospital registration and the **admin verification queue**, with an audit log.
- Design system, and the screens for all three roles.

*Stand-up line:* "All three roles can sign up and use their dashboards; hospitals must be
verified by an admin before they can request blood."

### Day 3: requests and matching (8 to 9 October)
- Request lifecycle: open, fulfilled, closed, expired. Expiry is applied when requests are
  read, so no scheduler is needed.
- **Distance** (haversine and bounding box) and the **matching engine**.
- Request screens: form, list, and a detail page with ranked anonymous matches.

*Stand-up line:* "Hospitals can raise requests and see compatible, eligible donors nearest
first."

### Day 4: pledges, alerts and map (9 October)
- **Concurrency-safe pledges:** donor lock, then request lock, then a 409 when full.
  Cancellation and outcomes; a donation updates the donor's last donation date.
- Donor dashboard: "Requests near you" and pledge history. Hospital page: pledged donors
  with **Donated** / **Did not attend**.
- **SMS alerts, at most once per donor**, through a console sender or Termii.
- **Leaflet map**, with donor positions rounded to about 1 km.
- **Demo seed:** five fictional hospitals and 28 donors in Lagos, Abuja and Enugu.

*Stand-up line:* "The full loop works: request, alert, pledge, donation, and it can't be
overbooked, proven by tests that fail when the lock is removed."

### Day 5: ship (9 to 10 October)
- Hospital **performance figures**.
- The **hospital-first landing page** with the pricing story.
- **Deployment:** Neon, Render and Vercel. The site forwards `/api/v1` so the cookie stays
  first-party.
- README, engineering log, deployment guide, and a test of every recipient group against
  the published chart.

*Stand-up line:* "BloodLink is live with demo data; README and log are written; research is
the remaining item."

### Day 6: polish (11 October)
- Sign-up skips the account-type question when the button already said it ("Register your
  hospital", "Become a donor"), with a **Change** link.
- Landing page **photo carousel**: accessible, pauses on hover or focus, respects reduced
  motion.
- Product ideas and clinical research: see [`docs/product-ideas.md`](product-ideas.md).

### Day 7: standby donors and screening outcomes (21 October)
- **Standby list:** once every unit is pledged, donors can wait in reserve. A freed unit
  (cancelled, did not attend, deferred) goes automatically to the longest-waiting standby
  donor, who is texted. The rest are released when the request is met, closed or expired.
- **Deferred at screening:** staff pick a reason; the donor is paused for that reason's
  period. A positive infection screen is permanent and never revealed to the donor in the
  app.
- Pledge states are now: pledged, standby, donated, no-show, deferred, cancelled, released.

*Stand-up line:* "A pledge isn't a unit of blood, so BloodLink now keeps a standby reserve
that fills a gap automatically, still without overbooking, and records why a donor was
turned away without ever exposing a test result."

---

## 4. Architecture

```
Browser ──> Vercel (Next.js site) ──/api/v1/*──> Render (FastAPI, Docker) ──> Neon (PostgreSQL)
                                                        └──> Termii SMS (when configured)
```

**Rule of the codebase:** routes validate input and delegate, **services hold the business
rules**, and models only describe tables. If you want to know what BloodLink *decides*, read
`backend/app/services/`.

---

## 5. Codebase tour

### Backend (`backend/app/`)

| Folder | What lives there | Files to know |
|---|---|---|
| `core/` | Settings, security, password policy, rate limiting | `config.py` (every setting, validated at start-up), `security.py` (hashing, tokens) |
| `models/` | One file per table (SQLModel) | `blood_request.py`, `pledge.py`, `donor.py`, `blood_compatibility.py`, `component_type.py` |
| `schemas/` | Request and response shapes (Pydantic) | `request.py`, `pledge.py` |
| `services/` | **The business rules** | see below |
| `api/routes/` | HTTP endpoints, one file per area | `requests.py`, `pledges.py`, `donors.py` |
| `api/deps.py` | Who is signed in, role checks, "verified hospital" | `StaffUser`, `DonorUser`, `VerifiedHospital` |
| `db/` | Session, reference seed, demo seed | `seed.py`, `demo_seed.py` |
| `data/` | The compatibility chart and component intervals as constants, loaded into the tables | `reference_data.py` |

**The services, the heart of the system:**

| Service | Decides |
|---|---|
| `eligibility.py` | Can this donor give this component today? A pure function: no database, no clock. |
| `distance.py` | Haversine distance, the bounding box, positions rounded to about 1 km |
| `matching.py` | Which donors match a request (`find_matches`); which requests a donor can answer (`find_requests_for_donor`) |
| `requests.py` | Raising, listing, closing and expiring requests |
| `pledges.py` | Pledging under row locks, cancelling, recording outcomes |
| `notifications.py` | Alerting matched donors at most once (`INSERT ... ON CONFLICT DO NOTHING`) |
| `sms.py` | The console and Termii senders, and which one is active |
| `stats.py` | Fulfilment rate, median time to fulfil, no-show rate |
| `audit.py` | Writing audit entries in the same transaction as the change |

### Frontend (`frontend/`)

| Folder | What lives there |
|---|---|
| `pages/` | One file per screen (Pages Router). `pages/hospital/requests/[id].tsx` is the richest. |
| `components/requests/` | Request form, badges, progress, match list, alert panel, pledge list |
| `components/donor/` | Eligibility card, open-request card, pledge history, hospital contact |
| `components/map/` | `RequestMap` (Leaflet, browser only) and `MapPanel` (loads it) |
| `components/landing/` | Product preview, pricing, photo carousel |
| `lib/api.ts` | The only place that calls the API: cookies, JSON, readable errors |
| `lib/use-resource.ts` | Load-on-mount hook used by every screen |
| `context/AuthContext.tsx` and `components/RouteGuard.tsx` | Who is signed in, and which pages each role may open |
| `next.config.ts` | Forwards `/api/v1` to Render in production |

---

## 6. One request, traced through the code

**Scenario:** Lagoon Specialist Hospital needs 2 units of O- whole blood, and a donor
pledges.

1. **The form.** Staff fill `components/requests/RequestForm.tsx`, which sends
   `POST /api/v1/requests`.
2. **The route.** `api/routes/requests.py::raise_request`:
   - `VerifiedHospital` (in `deps.py`) refuses unverified hospitals with 403;
   - `RequestCreate` (in `schemas/request.py`) checks the deadline is 5 minutes to 30 days
     away.
3. **The service.** `services/requests.py::create_request` stores the request and an audit
   entry in one transaction, and enforces the 25-open-requests limit.
4. **Alerts.** After the response is sent, `notifications.py::alert_in_background` runs
   `find_matches`, claims each donor's notification row, and sends one SMS each.
5. **Matching.** `services/matching.py::find_matches`:
   1. reads the compatible donor groups from the `blood_compatibility` table (for O-, only
      O-);
   2. filters available, consenting, active donors with no unresolved pledge, inside the
      bounding box;
   3. computes the exact haversine distance and drops anyone beyond the radius;
   4. runs `evaluate_eligibility` for the component;
   5. sorts nearest first.
6. **The hospital's page.** `pages/hospital/requests/[id].tsx` shows the map, the matches
   (`GET .../matches`), the alerts and the pledges.
7. **The donor pledges.** On `/donor`, `OpenRequestCard` sends
   `POST /requests/{id}/pledges`. `services/pledges.py::create_pledge`:
   1. locks the donor row, then the request row;
   2. checks the request is open, the donor is compatible and eligible, and has no other
      active pledge;
   3. counts the taken units; if the request is full, raises `RequestFullError`, which
      becomes 409;
   4. inserts the pledge; if it took the last unit, sets the request to **fulfilled**;
   5. writes an audit entry and commits.
8. **Donated.** Staff press **Donated**, which calls `resolve_pledge`. In one transaction it
   sets the pledge to `donated`, creates the `donations` row, and moves the donor's
   `last_donation_date` forward, so `evaluate_eligibility` now reports the waiting period.

---

## 7. Tests: where the proof is

338 backend tests run against a real PostgreSQL database.

| Proves | File |
|---|---|
| No overbooking under concurrency (fails without the lock) | `tests/test_pledge_concurrency.py` |
| Each recipient group matches exactly the published chart | `tests/test_matching.py` |
| Eligibility boundaries, deferrals, interval changes in data | `tests/test_eligibility.py` |
| Distances, bounding box, ordering | `tests/test_distance.py` |
| Alerts at most once, even concurrently | `tests/test_notifications.py` |
| Pledge lifecycle, privacy, ownership | `tests/test_pledges_api.py` |
| Standby reserve under concurrency, promotion, release, deferral privacy | `tests/test_standby_and_screening.py` |
| Hospital figures | `tests/test_stats_api.py` |
| Demo data is complete and safe | `tests/test_demo_seed.py` |

Run them with: `cd backend && uv run pytest`

---

## 8. Likely viva questions, with short answers

- **"What stops two donors taking the last unit?"** A transaction that locks the request
  row with `SELECT ... FOR UPDATE` before counting pledges. The second transaction waits,
  then counts the committed truth and gets 409. The tests release racing threads together
  and fail if the lock is removed.
- **"Why not just a unique constraint?"** A unique constraint stops one donor pledging
  twice; it cannot stop *different* donors exceeding `units_needed`. That needs the count
  and the insert to happen under one lock.
- **"How would you change a waiting period?"** Edit the row in `component_types`. No code
  changes; a test proves this.
- **"Why haversine and not PostGIS?"** A demo-scale donor pool fits a bounding box plus
  exact distance on the remaining rows. PostGIS is on the roadmap for scale.
- **"How do you protect donors' privacy?"** Hospitals see matches anonymously; contact
  details appear only after the donor pledges and disappear if they cancel. Map positions
  are rounded to about 1 km, and phone numbers are masked in logs.
- **"What happens if the alert job runs twice?"** Nothing new is sent. Each donor is claimed
  by `INSERT ... ON CONFLICT DO NOTHING` on a unique (request, donor, channel) constraint
  before sending.
- **"What if nobody runs the expiry job?"** Requests are expired whenever they are read, so
  every screen is correct without a scheduler.
- **"Why does the site forward API calls?"** It keeps the session cookie first-party.
  Third-party cookies are blocked by Safari.
