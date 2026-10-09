# Engineering log

A dated record of what was built, what was learned, and what is blocked. Entries follow the
five-day plan in the specification; the work ran from 2 to 9 October 2026, and each day's
work is tagged in Git (`day-1` to `day-5`).

---

## 2026-10-02 · Day 1: foundation

**Built:**
- Repository, Docker Compose PostgreSQL on port 5433, `.env.example`.
- FastAPI skeleton with validated settings, the database session, and health and readiness
  endpoints.
- All 11 SQLModel tables and the first Alembic migration.
- Reference data: the red-cell compatibility chart and component types, with a seed
  command.
- Next.js Pages Router app with Tailwind and shadcn/ui.
- ERD, research template, this log, and the concurrency spike.

**Learned:**
- **The spike decided the core design.** Without `SELECT ... FOR UPDATE`, two simultaneous
  pledges for the last unit were both accepted; with it, exactly one. The pledge service has
  to lock the request row before counting.
- **Statuses as constrained strings.** Storing them as strings guarded by `CHECK`
  constraints, rather than native PostgreSQL enums, means adding a status later only
  replaces a constraint.
- **Line endings matter on Windows.** Enforcing LF in `.gitattributes` stops scripts and
  Docker files breaking on Linux hosts.

**Blocked / questions:** Interviews for `RESEARCH.md` not yet arranged.

**Next:** Authentication and roles.

---

## 2026-10-04 · Day 1 to 2: web client foundations and authentication

**Built:**
- Typed API client, authentication context and role-based route guard.
- Password hashing (argon2) and signed access tokens in an httpOnly cookie.
- Password policy, sign-in rate limiter, and register, login, logout and current-user
  endpoints.
- A separate PostgreSQL test database, and a command to create administrators.

**Learned:**
- **Passwords.** NIST SP 800-63B-4 favours length (15 characters when the password is the
  only factor) over composition rules.
- **Unicode.** Passwords are normalised before hashing, so the same password typed on
  different keyboards still matches.
- **Tests need the real database.** Row locks and unique constraints only behave correctly
  on PostgreSQL, so the tests run against a dedicated `_test` database instead of SQLite.

**Blocked / questions:** None.

**Next:** Donor and hospital profiles, admin verification.

---

## 2026-10-05 · Day 2: profiles, eligibility and verification

**Built:**
- **Eligibility rules module:** waiting period per component and sex, age, weight and
  deferrals.
- Donor profile and eligibility endpoints, and hospital registration.
- The admin review queue with verify and reject, and an audit log of every decision.

**Learned:**
- **Eligibility is a pure function.** It takes values and a date, no database and no clock,
  which makes the boundary days testable exactly: the day the waiting period ends counts as
  eligible.
- **Verification is one dependency.** A "verified hospital" dependency puts the trust gate
  in one place instead of in every route.

**Blocked / questions:** The waiting periods, age and weight limits are placeholders until
the national transfusion service and WHO figures are cited.

**Next:** Design system and screens.

---

## 2026-10-06 · Day 2: design system and screens

**Built:**
- Design tokens, typography, layout and motion components, and a design system reference
  page.
- Sign-in and register pages.
- Donor dashboard (eligibility card, profile, alerts switch) and donor profile form, with a
  shared location picker.
- Hospital registration form and dashboard, with verification badge and steps.

**Learned:**
- **Safe return addresses.** After sign-in, a requested page is only followed if it is a
  path on this site, which prevents open redirects.
- **Show reasons, not a verdict.** Showing donors why they cannot give, and from which date
  they can, is more useful than a yes or no.

**Blocked / questions:** None.

**Next:** Admin screens.

---

## 2026-10-07 · Day 2: administrator screens

**Built:**
- Admin review queue and hospital review pages with the decision panel.
- A check for which pages each role may open.

**Learned:**
- **A stale return address.** One left over from a different account could send a donor
  towards an admin page after signing in. Return addresses are now checked against the new
  account's role, and dropped after a deliberate sign-out.

**Blocked / questions:** None.

**Next:** Blood requests and matching.

---

## 2026-10-08 · Day 3: requests and matching

**Built:**
- **Requests:** endpoints with the lifecycle (open, fulfilled, closed, expired). Expiry is
  applied whenever requests are read, plus a sweep command.
- **Distance:** a haversine helper with a bounding box.
- **Matching:** compatible, eligible, available, consenting and nearby donors, nearest first.
- Tests for the lifecycle, ownership, compatibility, distance and eligibility.

**Learned:**
- **Rounding made a test fail.** A test built its point with a rounded figure for kilometres
  per degree and landed a fraction outside the box. Checking it showed the box's east-west
  width shortcut was slightly too narrow, so the exact formula is used now.
- **Expiry without a scheduler.** Expiring overdue requests when they are read keeps every
  screen correct even if the scheduled sweep never runs.

**Blocked / questions:** None.

**Next:** Request screens, then pledges.

---

## 2026-10-09 · Days 3 to 5: pledges, alerts, map, demo data, landing page and deployment

**Built:**
- **Request screens:** form, list and detail with ranked anonymous matches, and a public
  component list.
- **Pledges:** concurrency-safe, with a donor lock then a request lock. Cancellation,
  donated and no-show outcomes, and the donor's "requests near you" and pledge history.
- **SMS alerts,** at most once per donor per request, through a console sender or Termii.
- **Leaflet map** with donor positions rounded to about a kilometre.
- **Demo seed:** five fictional hospitals and 28 donors in Lagos, Abuja and Enugu.
- **Hospital figures:** requests met, median time to fulfil, no-show rate.
- **Landing page:** hospital-first, with the pricing story.
- **Deployed:** Neon (database), Render (API) and Vercel (site).

**Learned:**
- **A concurrency test that passed for the wrong reason.** Three of its four threads were
  crashing on a shared database object, so only one run happened. The test now fails if any
  thread raises, and a test is only trusted after watching it fail without the protection.
  Removing the row lock made all three pledge race tests fail, as they should.
- **Termii has no sandbox.** Every message is real and paid for, and a sender ID must be
  approved first. The promotional route does not reach Do-Not-Disturb numbers and is blocked
  on MTN between 8 PM and 8 AM, which is exactly when emergencies happen, so the
  transactional (DND) route is needed. Alerts fall back to a console sender until then.
- **Third-party cookies.** With the site on Vercel and the API on Render, the session cookie
  would have been third-party and blocked by Safari. Forwarding `/api/v1` through the site
  keeps it first-party.
- **No shell on Render's free plan.** Migrations and reference data therefore run on every
  container start; both are safe to repeat.
- **Privacy on the map.** Rounding positions to two decimal places (about 1.1 km) shows
  where donors are clustered without revealing homes.
- **Measures that a whiteboard can hold.** The median time to fulfil resists one slow
  request, and rates are left empty rather than shown as 0% when there is nothing to
  measure yet.

**Blocked / questions:**
- `RESEARCH.md`: the two interviews, competitor prices and cited sources are still to be
  done and signed off. They are needed for the evidence in the README, for real prices,
  and to replace the placeholder eligibility figures.
- The Termii sender ID is awaiting approval, and the DND route must be requested from
  Termii support.
- The Render API sleeps when idle; wake it before demonstrations.

**Next:** Complete `RESEARCH.md`, replace the eligibility placeholders with cited figures,
add cited statistics to the landing page and README, and prepare for the viva.
