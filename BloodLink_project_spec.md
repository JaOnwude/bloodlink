# BloodLink: project specification

**Owner:** Onwude James Uchenna
**Programme:** Fullstack bootcamp capstone (startup MVP), chosen option 2 of 0-4
**Build window:** 5 days (the brief allows 10; the schedule below compresses it)
**Product direction:** hospital-facing SaaS (hospitals and blood banks pay) built on top of a free donor network (the supply side)

> **For AI coding agents (opencode, GitHub Copilot, Claude Code, etc.):** read sections 0 and 12 before writing any code. Treat this file as the source of truth. If something here conflicts with a request in the terminal, ask the human before deviating.

---

## 0. Agent operating rules

1. **Stack is fixed.** Next.js **Pages Router** (not App Router), TypeScript, Tailwind, shadcn/ui; FastAPI; PostgreSQL; SQLModel; Alembic; Docker Compose; Vercel (web) and Render (API).
2. **Python tooling is `uv`.** Never use `pip install` or `python -m venv` directly. Use `uv add`, `uv sync`, `uv run`.
3. **Shell is Git Bash on Windows.** Write commands for bash (forward slashes, `export`, `&&`), never PowerShell syntax.
4. **Comments are elaborate and professional.** Every module opens with a docstring explaining its purpose and how it fits the system. Every public function, class and endpoint has a docstring covering behaviour, parameters, return values, errors and edge cases. Explain *why*, not only *what*.
5. **Never mention project days, schedules or "TODO for later" milestones in code or comments** (no "day 1", "week 2", "phase 3"). Describe what the code does and, where useful, what it is designed to support, in neutral terms such as "this table is designed so that component types can be added without a migration of existing rows".
6. **Small, meaningful commits** using Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`). One logical change per commit. Run tests before committing.
7. **Rules live in data.** Blood compatibility and donor eligibility must come from database tables and configuration, never from long `if` chains.
8. **Security by default.** Hash passwords (argon2 or bcrypt), validate all input with Pydantic, enforce role and ownership checks on every protected route, never log personal data or tokens, keep secrets in `.env` (never committed).
9. **Tests are part of the feature.** A feature is not finished until its tests pass. Minimum 15 tests overall; the hard part has at least three dedicated tests (section 7).
10. **Do not invent facts.** Medical thresholds (donation intervals, age, weight) must be set from the cited NBTS/WHO sources in `RESEARCH.md`. Until verified, mark any default as a placeholder in config and in the docstring.

---

## 1. The product

**BloodLink: when a hospital needs O-negative tonight, find willing donors who can actually give.**

A verified hospital posts an urgent request (blood group, units, component, deadline, location). BloodLink finds donors who are compatible, eligible (enough time since their last donation, available, within range) and nearby, ranks them by distance, and notifies them. Donors pledge. The hospital confirms each donation or records a no-show. The request closes automatically the moment enough units are pledged, even if two donors accept at the same instant.

**Positioning.** Existing Nigerian products solve half of the problem: LifeBank is strong on blood bank inventory and delivery; J Blood Match connects donors and recipients over chat bots but leaves the donation itself off-platform. BloodLink is a **trusted, closed-loop emergency layer**: only verified hospitals can raise requests, eligibility is enforced by the system, and every pledge is tracked through to a confirmed donation.

**Customer model.** Hospitals and blood banks are the paying customers. Donors always use it free. The donor network exists to make hospital requests succeed, which is what hospitals pay for.

---

## 2. The problem (with evidence)

Claims below come from secondary sources found during planning. **They must be re-checked and cited properly in `RESEARCH.md`** before being used in the README.

| Claim | Source to verify |
|---|---|
| Nigeria needs roughly 1.8 million pints of blood a year (WHO Africa, 2021 statement) and still struggles with voluntary donor recruitment | sjai.nigeriahealthwatch.com article on AI-linked blood donors |
| Nigeria has one of the lowest rates of voluntary unpaid donation in Africa | guardian.ng, "Blood for those who need it" |
| Commercial blood banks operate in silos, so hospitals waste time searching for blood | MIT Solve / LifeBank "Frontlines of Health" entry |
| Postpartum haemorrhage and road traffic injuries drive constant demand | primeprogressng.com, J Blood Match feature |
| LifeBank: B2B, hospitals are the direct customers; served 600+ hospitals with 150+ blood banks | aljazeera.com, 2022 feature on LifeBank |

---

## 3. Market and competitors

| Competitor | What it does | What it misses |
|---|---|---|
| **LifeBank** (Nigeria, Kenya) | Hospital ordering and delivery of blood, cold-chain logistics, inventory discovery across blood banks, SmartBag traceability and LabX | Not a donor-first emergency alert system; bulk logistics rather than live donor fulfilment |
| **J Blood Match** (Jela's Development Initiatives) | Free donor/recipient matching through Telegram and Messenger bots, enforces roughly a three-to-four-month gap | No hospital verification; once matched, the donation is arranged off-platform and not tracked |
| **iDon8 and MIT Solve entries** | "Uber-style" nearby donor finding, appointment and inventory apps | Early-stage, little public evidence of hospital adoption |
| **Enterprise blood bank software** (for example SCC SoftDonor and SoftRecruit) | Regulated donor eligibility, testing, inventory, recruitment campaigns, appointment scheduling, donor portals | Built for large regulated blood services; heavy, expensive, not designed for urgent hospital-initiated requests |

`RESEARCH.md` must add two competitors or workarounds with real prices (for example a hospital's WhatsApp group or a phone-call process) gathered from interviews.

---

## 4. Users and roles

| Role | Can do |
|---|---|
| **Donor** | Register, set blood group and location, toggle availability, see eligibility date, receive alerts, pledge to a request, cancel a pledge, view donation history |
| **Hospital staff** | Belong to one hospital; once the hospital is verified, create and manage requests, see matched donors and pledges, confirm donated or no-show |
| **Admin** | Review and approve or reject hospital verification, view platform metrics, manage compatibility data, deactivate abusive accounts |

Ownership rules: a donor only sees and changes their own profile and pledges; hospital staff only see their own hospital's requests and pledges; only admins can verify hospitals.

---

## 5. Scope

### 5.1 MVP (build in the five-day window)

- Auth with the three roles, JWT in an httpOnly cookie, ownership checks.
- Hospital verification (pending, verified, rejected) with an admin approval screen.
- Audit log for every sensitive action, confirmed donation history, donor deferrals, and component types with per-component intervals.
- Donor profile: blood group, location, last donation date, availability toggle.
- Blood requests with lifecycle **Open → Fulfilled → Closed / Expired**.
- Matching engine (compatibility from a table, eligibility from config, distance from Haversine, sorted nearest first).
- Pledges with concurrency-safe unit limits; hospital marks donated or no-show; the donor's last donation date updates.
- Notifications to matched donors through the Termii sandbox (SMS) and a notification log that prevents duplicate alerts.
- Leaflet map showing the hospital and candidate donors.
- Landing page that pitches hospitals first (problem, who it is for, pricing story) and recruits donors second.
- Seed script with realistic Nigerian demo data (Lagos, Abuja, Enugu hospitals and donors).
- Deployed on Vercel and Render; main journey works end to end on the deployed URL.

### 5.2 Product roadmap (design for it now, build it after the capstone)

**Trust and safety:** donor health questionnaire with deferral reasons and expiry; immutable audit log; abuse detection and rate limiting; transport reimbursement option (never payment for blood).
**Smarter matching:** notification waves (nearest donors first, widen radius after a timeout); donor reliability score; quiet hours; component types (whole blood, platelets, plasma) with their own intervals; rare-group (Rh-negative) flags; inventory-first waterfall (check partner blood bank stock, then donors).
**Reach:** WhatsApp and USSD alerts; voice-call fallback for critical requests; multilingual offline PWA (English, Pidgin, Yoruba, Hausa, Igbo); Telegram bot.
**Donor retention:** eligibility countdown reminders, digital donor card, appointments, employer and university drive management, optional partner rewards.
**B2B platform:** multi-tenant organisations and staff roles; blood bank stock listings with expiry and reservation; dashboards (time to fulfil, no-show rate, demand by group); Paystack billing; public API and webhooks; regulator reports.
**Scale and standards:** PostGIS; background job queue with idempotent notifications; observability; field-level encryption of personal data; ISBT 128 and FHIR alignment where relevant; demand forecasting.

---

## 6. Data model

Design rules for every table: UUID primary keys, `created_at` and `updated_at` timestamps, status columns as constrained enums or check constraints, foreign keys with sensible `ON DELETE` behaviour, indexes on every column used for filtering.

### 6.1 Core tables (11)

The tutor has approved going beyond the brief's 5-7 table guideline, so the schema below is the one to build. Every table must still be explainable at the viva.

**users**
`id`, `email` (unique), `password_hash`, `role` (donor | hospital_staff | admin), `full_name`, `phone`, `is_active`, timestamps.

**hospitals**
`id`, `name`, `address`, `city`, `state`, `latitude`, `longitude`, `registration_number`, `contact_phone`, `verification_status` (pending | verified | rejected), `verified_at`, `rejection_reason`, timestamps. The reviewing admin is recorded in `audit_log`. Staff users link to a hospital (a `hospital_id` column on staff profiles or a small link; keep it simple: nullable `hospital_id` on `users` for staff).

**donors**
`id`, `user_id` (unique FK), `blood_group` (A+, A-, B+, B-, AB+, AB-, O+, O-), `date_of_birth`, `weight_kg`, `sex`, `latitude`, `longitude`, `city`, `last_donation_date` (nullable), `is_available`, `consent_to_contact`, timestamps.

**blood_compatibility** (rules as data)
`id`, `recipient_group`, `donor_group`, unique pair. Seeded from the red-cell compatibility chart:

| Recipient | Compatible donor groups |
|---|---|
| O- | O- |
| O+ | O+, O- |
| A- | A-, O- |
| A+ | A+, A-, O+, O- |
| B- | B-, O- |
| B+ | B+, B-, O+, O- |
| AB- | AB-, A-, B-, O- |
| AB+ | all eight groups |

**blood_requests**
`id`, `hospital_id`, `created_by` (user id), `recipient_group`, `units_needed`, `urgency` (critical | urgent | routine), `deadline`, `notes`, `status` (open | fulfilled | closed | expired), `fulfilled_at`, timestamps. `component_type_id` (FK to `component_types`) records what is needed (whole blood, platelets, plasma).

**pledges**
`id`, `request_id`, `donor_id`, `status` (pledged | donated | no_show | cancelled), `pledged_at`, `resolved_at`, `resolved_by`, timestamps. Unique constraint on (`request_id`, `donor_id`) so a donor cannot pledge twice to the same request.

**notifications**
`id`, `request_id`, `donor_id`, `channel` (sms for now), `status` (queued | sent | failed), `provider_message_id`, `sent_at`, timestamps. Unique constraint on (`request_id`, `donor_id`, `channel`) so the same alert is never sent twice, even if the job runs twice.

**component_types** (rules as data)
`id`, `code` (whole_blood | platelets | plasma), `name`, `min_interval_days_male`, `min_interval_days_female`, `is_active`. Donation intervals live here, per component. **Seeded values are placeholders until the NBTS/WHO figures are verified in `RESEARCH.md`.**

**donations** (confirmed donation history)
`id`, `pledge_id` (unique FK), `donor_id`, `hospital_id`, `component_type_id`, `units`, `donated_at`, `confirmed_by` (user id), timestamps. Created in the same transaction that marks a pledge as donated. `donors.last_donation_date` is a cached value updated in that transaction.

**donor_deferrals** (temporary or permanent ineligibility)
`id`, `donor_id`, `reason`, `deferred_until` (nullable for permanent), `recorded_by`, `created_at`. The eligibility module treats an active deferral as ineligible.

**audit_log** (append-only)
`id`, `actor_user_id` (nullable), `action`, `entity_type`, `entity_id`, `before` (JSON), `after` (JSON), `ip_address`, `created_at`. Written for verification decisions, request lifecycle changes, pledge resolutions and account deactivations. Never updated or deleted by application code.

### 6.2 Configuration (not tables)

Age limits, minimum weight, search radius defaults and token lifetimes live in application configuration loaded from environment variables. **Defaults are placeholders until the NBTS/WHO figures are verified in `RESEARCH.md`.**

### 6.3 Designed-for-later tables (do not build yet)

`donor_health_screenings`, `blood_bank_inventory`, `organisations`/`memberships`, `donation_appointments`, `drives`, `subscriptions`/`invoices`, `api_keys`/`webhooks`. The core schema must not block any of them (UUID keys, enums, timestamps, no hard-coded assumptions about a single hospital per user beyond the nullable `hospital_id`).

---

## 7. The hard part (explained at a whiteboard, proven with tests)

### 7.1 Rules from data, not `if` statements
- Compatible donor groups come from `blood_compatibility`.
- Eligibility (component interval since last donation, age, weight, availability, consent, active deferrals) is evaluated by a small rules module driven by `component_types` and configuration.
- **Tests:** (a) every recipient group returns exactly the donor groups in the table above; (b) a donor inside the interval is excluded and one on the boundary date is included; (c) changing a component's interval in `component_types` changes the result with no code change; (d) an active deferral excludes an otherwise eligible donor.

### 7.2 No overbooking, even under concurrency
- Pledging runs in a single transaction that locks the request row (`SELECT ... FOR UPDATE`), counts pledges with status `pledged` or `donated`, rejects with `409 Conflict` if the count already equals `units_needed`, inserts the pledge otherwise, and flips the request to `fulfilled` when the last unit is taken.
- **Tests:** (a) sequential pledges stop at `units_needed`; (b) two concurrent pledges for the last unit produce exactly one success and one 409; (c) a donor cannot pledge twice to the same request.

### 7.3 Correct distance search
- Haversine distance computed in SQL (or a tested helper), filter by radius, sort nearest first.
- **Tests:** (a) known city-pair distances within tolerance (for example Lagos to Abuja); (b) donors outside the radius are excluded; (c) ordering is nearest first.

---

## 8. API surface (FastAPI, prefix `/api/v1`)

| Method and path | Role | Purpose |
|---|---|---|
| `POST /auth/register` | public | Register donor or hospital staff |
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | any | Session handling |
| `GET/PUT /donors/me` | donor | View and update profile, toggle availability |
| `GET /donors/me/eligibility` | donor | Next eligible date and reasons |
| `GET /donors/me/pledges` | donor | History |
| `POST /hospitals` | staff | Register hospital (starts as pending) |
| `GET /hospitals/me` | staff | Own hospital and verification status |
| `GET /admin/hospitals?status=pending`, `POST /admin/hospitals/{id}/verify` and `/reject` | admin | Verification queue |
| `POST /requests` | verified staff | Create request, triggers matching and notifications |
| `GET /requests`, `GET /requests/{id}` | staff (own), donor (matched, open) | List and detail |
| `POST /requests/{id}/close` | staff | Close early |
| `GET /requests/{id}/matches` | staff | Ranked candidate donors with distance |
| `POST /requests/{id}/pledges` | donor | Pledge (concurrency-safe) |
| `DELETE /pledges/{id}` | donor | Cancel |
| `POST /pledges/{id}/donated`, `POST /pledges/{id}/no-show` | staff | Resolve, updates donor's last donation date |
| `GET /stats/hospital` | staff | Time to fulfil, fulfilment rate, no-show rate |
| `GET /health` | public | Liveness |

Standards: consistent error body, correct status codes, pagination on list endpoints, OpenAPI docs with descriptions on every route.

---

## 9. Frontend (Next.js Pages Router)

```
pages/
  _app.tsx            global layout, auth provider, toasts
  index.tsx           landing page (hospital-first pitch, pricing story, donor sign-up call to action)
  login.tsx
  register.tsx
  donor/index.tsx     dashboard: eligibility, open matching requests, history
  donor/profile.tsx
  hospital/index.tsx  dashboard: requests, stats
  hospital/requests/new.tsx
  hospital/requests/[id].tsx   matches, pledges, map, resolve donations
  admin/index.tsx     verification queue and metrics
components/           UI building blocks (shadcn/ui), map, forms, tables
lib/api.ts            typed API client (fetch wrapper, error handling)
context/AuthContext.tsx
```

Use `getServerSideProps` only where server data is needed up front; use client-side fetching for dashboards. Guard routes by role. Responsive layout, accessible forms, loading and error states everywhere.

---

## 10. Repository layout

```
bloodlink/
  README.md  LOG.md  RESEARCH.md  AGENTS.md (copy of section 0 and 12)
  docker-compose.yml  .env.example  .gitignore
  backend/
    pyproject.toml (uv)  alembic.ini  alembic/
    app/
      main.py
      core/        config.py  security.py  eligibility.py
      db/          session.py  base.py
      models/      one module per table
      schemas/     Pydantic request/response models
      api/         deps.py  routes/ (auth, donors, hospitals, requests, pledges, admin, stats)
      services/    matching.py  pledges.py  notifications.py  distance.py
    scripts/       seed.py
    tests/
  frontend/        (Next.js, Pages Router)
  spikes/          concurrent_pledge_spike.py (<= 50 lines)
  docs/            erd.md, api.md, decisions.md
```

---

## 11. Environment and tooling

- **Python:** `uv init`, `uv add fastapi "uvicorn[standard]" sqlmodel alembic psycopg[binary] pydantic-settings "pyjwt" argon2-cffi httpx`, dev: `uv add --dev pytest pytest-asyncio ruff mypy`. Run with `uv run ...`.
- **Database:** Docker Compose runs PostgreSQL; map the host port to **5433** to avoid clashing with any local PostgreSQL. Connect pgAdmin4 to `localhost:5433` with the credentials in `.env`.
- **Frontend:** Node LTS, `npx create-next-app@latest frontend --typescript --tailwind --eslint --no-app --src-dir=false`, then initialise shadcn/ui.
- **Quality gates:** `ruff` and `mypy` on the backend, ESLint and `tsc --noEmit` on the frontend, `pytest` before each commit.
- **Shell:** Git Bash on Windows.
- **Integrations:** Termii sandbox (SMS), Leaflet and OpenStreetMap, Paystack test mode reserved for later billing.

---

## 12. Engineering conventions

- **Layering:** routes validate and delegate; services hold business logic; models only describe persistence. No business rules in route handlers.
- **Transactions:** one transaction per use case; pledging and resolving donations are transactional.
- **Idempotency:** notification sending checks and records the notification row inside the same transaction as the decision to send.
- **Time:** store UTC, convert at the edges. Deadlines and expiry are evaluated in UTC.
- **Expiry:** requests past their deadline are treated as expired when read, and a sweep command persists the status, so correctness never depends on a scheduler.
- **Privacy:** donors' exact coordinates and phone numbers are never shown to other donors. Hospital staff see a donor's contact details only after that donor pledges.
- **Errors:** domain exceptions mapped to HTTP errors in one place.
- **Docs:** README sections *The problem (with evidence)*, *The hard part*, *Why this design (with sources)*, *Who pays*; `LOG.md` updated daily.

---

## 13. Five-day plan

| Day | Focus | Deliverables | Example commits |
|---|---|---|---|
| 1 | Foundation and research start | Repo, Docker Compose, `.env.example`, FastAPI skeleton, settings, DB session, SQLModel models, first Alembic migration, compatibility seed, health check test, Pages Router app with Tailwind and shadcn/ui, API client, `RESEARCH.md` template, concurrency spike | `chore: scaffold repo`, `feat(api): add settings and database session`, `feat(db): add core models`, `feat(db): add initial migration`, `feat(seed): add compatibility rules`, `feat(web): scaffold pages router app`, `docs: add research template` |
| 2 | Auth, roles, profiles | Registration, login, JWT cookie, role guards, donor and hospital profile endpoints and screens, admin verification flow | `feat(auth): ...`, `feat(donors): ...`, `feat(admin): ...`, `test: ...` |
| 3 | Requests and matching | Request lifecycle, eligibility rules module, distance helper, matching service, matches endpoint, first three hard-part tests | `feat(requests): ...`, `feat(matching): ...`, `test(matching): ...` |
| 4 | Pledges and integration | Concurrency-safe pledges, resolve donated or no-show, Termii notifications with dedupe, Leaflet map, hospital and donor screens wired up | `feat(pledges): ...`, `feat(notify): ...`, `feat(web): ...` |
| 5 | Ship | Landing page and pricing story, seed with realistic data, deploy to Vercel and Render, 15+ tests passing, README and `LOG.md`, viva preparation | `feat(web): landing page`, `chore(deploy): ...`, `docs: readme` |

The research interviews run in parallel from day 1 and must be signed off before feature code beyond scaffolding is submitted.

---

## 14. The research gate

No feature code is accepted until `RESEARCH.md` is signed off.

1. **User evidence:** two conversations with real people in the domain (for example a blood bank worker or lab scientist, and a hospital administrator or nurse). Record role, date, questions asked, what surprised you, and one checkable artefact each (a photo of a request ledger, a screenshot of a WhatsApp appeal group, a redacted form).
2. **Market:** two competitors or workarounds with what they charge and what they miss (use section 3 as a starting point; add real prices from interviews).
3. **Three cited sources**, each with one sentence on how it changes the design: (a) NBTS/WHO donor eligibility (interval, age, weight), (b) red-cell compatibility chart, (c) a Nigerian blood supply statistic, or the Nigeria Data Protection Act 2023 for health data handling.
4. **Technical spike (<= 50 lines) in `/spikes`:** two concurrent pledge attempts against PostgreSQL for the last unit; exactly one must succeed.
5. **Three design decisions**, each pointing to a finding above (for example: eligibility interval is configuration; hospital verification is mandatory; contact details are revealed only after a pledge).

Suggested interview questions: How do you find blood today when a patient needs it urgently? How long does it take and who do you call? How many requests go unfilled and why? What would make you trust an app for this? What would you pay for monthly, and who approves that spend?

---

## 15. Who pays

- **Hospitals:** subscription tiers by request volume (prices to be set from interviews, not guessed).
- **Blood banks:** SaaS for donor drives and, later, inventory.
- **Employers, universities, HMOs:** sponsored drives and adherence/impact reports.
- **Governments and NGOs:** analytics dashboards.
- **Donors:** always free.

Start with private hospitals and blood banks in Lagos and Abuja; public hospitals have longer sales cycles. Early pilots may be free in exchange for fulfilment data.

---

## 16. Compliance and safety

- No payment for blood (WHO voluntary unpaid donation principle); transport reimbursement is acceptable.
- Health and location data is sensitive personal data. Collect explicit consent to be contacted, minimise what is stored, and plan a data protection impact assessment. Confirm obligations under the Nigeria Data Protection Act 2023 with a qualified professional.
- The platform matches and coordinates; it does not perform medical screening. Donor-facing text must say final eligibility is decided by clinical staff at the donation site.
- Rate-limit authentication and request creation; log administrative actions.

---

## 17. Marking (100)

| Part | Marks |
|---|---|
| Research (evidence real and specific, market, sources used in design, spike) | 15 |
| Working product, deployed, main journey end to end | 30 |
| Hard part: code 8, tests 7, explained 5 | 20 |
| Product quality (landing page, usable UI, sensible pricing story) | 10 |
| Code quality and tests | 10 |
| Viva (own code plus two research questions) | 15 |

---

## 18. Definition of done

- [ ] `RESEARCH.md` complete and signed off
- [ ] Hospital registers, is verified by admin, posts a request
- [ ] Matching returns compatible, eligible donors nearest first
- [ ] Donor receives an alert (sandbox), pledges, and cannot overbook the request
- [ ] Hospital confirms donation or no-show; donor's last donation date updates
- [ ] Request becomes fulfilled automatically and expired when the deadline passes
- [ ] 15+ tests pass, including the three hard-part groups
- [ ] Deployed URL works end to end with seeded demo data
- [ ] Landing page, README sections, and `LOG.md` complete
- [ ] I can explain every line of the hard part on a whiteboard
