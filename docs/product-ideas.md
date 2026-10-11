# BloodLink: product ideas, clinical realities and business model

What a hospital's blood bank and wards actually deal with, what BloodLink should build next
because of it, how private individuals can take part within the law, and how the business
makes money in the long run.

> Written from published sources and standard transfusion practice. It is not clinical
> advice. Every clinical rule here should be confirmed with the hospital's own blood bank
> and haematologists before it goes into the product.

---

## 1. Five clinical realities the product must respect

### 1.1 A pledge is not a unit of blood
Every donation is screened for HIV, hepatitis B and C, and syphilis before it can be used,
and donors are also turned away on the day for low haemoglobin, blood pressure or recent
illness. In one eleven-year study at a Calabar teaching hospital, **15% of prospective
donors carried at least one infection** (HBV 4.1%, HCV 3.6%, syphilis 3.1%, HIV 4.2%)
([Calabar study, PMC5964952](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5964952/)).

**Consequence:** a request for 2 units that stops at exactly 2 pledges will often end with
1 usable unit. Experienced blood bank staff over-recruit for this reason.

### 1.2 Self-reported blood groups are unreliable
Many people state a group that was never laboratory-confirmed. The blood bank always groups
and cross-matches, but a wrong group in a profile wastes a trip and a cross-match.

### 1.3 Most blood in Nigeria still comes from paid donors, and paying is illegal
The National Health Act 2014 prohibits buying or selling blood, yet the National Blood
Service Commission estimates that about **90% of the roughly 1.23 million units collected
each year come from paid commercial donors**
([NAN report](https://nannews.ng/desperate-measures-dark-truth-behind-nigerias-blood-trade/)).

**Consequence:** BloodLink's voluntary, tracked donor pool is a public-health good, not just
a product. That opens doors to government, NGO and NBSC partnerships, and rules out any
feature that pays donors.

### 1.4 Emergencies cluster in a few clinical situations
- **Postpartum haemorrhage.** Nigeria accounted for almost 75,000 of about 260,000 maternal
  deaths worldwide in 2023, about 29%. Haemorrhage is the leading direct cause in hospital
  studies ([AllAfrica, E-MOTIVE data](https://allafrica.com/stories/202510300165.html)).
  Anaemia before delivery makes it worse
  ([WOMAN-2 report](https://allafrica.com/stories/202604230114.html)).
- **Sickle cell disease.** Nigeria carries the world's highest burden. Estimates range from
  about 91,000 to 150,000 affected births a year
  ([Africa Check](https://africacheck.org/reports/weighing-nigerias-sickle-cell-burden-is-it-the-worlds-highest/)).
  Many patients need transfusions again and again.
- **Road traffic injuries, surgery and cancer care,** where platelets matter.

### 1.5 Blood does not keep
Red cells keep for roughly 5 to 6 weeks in a fridge; **platelets keep only about 5 days**,
at room temperature. Units expire on shelves in one hospital while another hospital
searches.

---

## 2. Ideas to build, in order of value

Effort: **S** = about a day, **M** = 2 to 4 days, **L** = a week or more.

### A. Standby donors, because a pledge is not a unit (S): build first
- A request gets **standby places** (for example 50% extra, set by the hospital). Once the
  units are pledged, further donors can pledge as **standby**: "You may be called if a
  donor cannot give."
- When a pledged donor is deferred at screening or does not attend, the **nearest standby
  donor is promoted** and texted at once.
- **Implementation:**
  - `blood_requests.standby_units`;
  - a new pledge status `standby`;
  - `create_pledge` allows standby once full;
  - `resolve_pledge(no_show or deferred)` promotes the oldest standby under the same row
    lock.
- **Viva value:** it shows you understand that screening rejects donors, a real clinical
  nuance.

### B. Screening outcomes, recorded confidentially (S)
- A third outcome next to **Donated** and **Did not attend**: **Deferred at screening**,
  with a reason *category* (low haemoglobin, blood pressure, recent illness, positive
  infection screen).
- It creates a `donor_deferrals` row with the right length; a positive infection screen
  gives a permanent deferral. The donor sees "Please contact the hospital about your
  screening" with the hospital's number, never the result itself, and other hospitals
  never see the reason.
- This is health data under the Nigeria Data Protection Act 2023: store the category only,
  restrict who can read it, and audit every access.

### C. Laboratory-confirmed blood group (S)
- When staff confirm a donation, they tick "blood group confirmed by our lab". The donor's
  profile gets `blood_group_verified_at` and a **Verified group** badge.
- Matching ranks verified donors first. The hospital page shows "group confirmed" next to
  each match.

### D. Alert waves that widen over time (S to M)
- Critical requests text the nearest donors first. If too few pledge within 15 minutes, the
  radius widens (10 km, then 25 km, then 50 km) and the next wave goes out. Routine requests
  respect quiet hours (no texts from 10 PM to 6 AM).
- **Implementation:** the existing `POST /requests/{id}/alerts?radius_km=` already texts
  only newly matched donors. Add a sweep command that each run widens any request still
  short after its wave interval.

### E. Family requests and share links, which bring in private individuals (M)
Families are the people most motivated to find donors, and hospitals already ask them to
bring "replacement donors". Today that happens on WhatsApp, untracked.

- A **relative can start a request** for a patient: hospital, ward, blood group, units, and
  the hospital's request form number.
- The hospital's blood bank sees it in a **"Confirm family requests"** queue and confirms it
  with one click. Only then is it a live request; this keeps the "verified only" promise.
- The family gets a **share link** for WhatsApp, such as "Help Mama Ngozi at Lagoon
  Specialist, O+, 2 units by Thursday". Friends who open it register as donors and pledge.
  Every new donor stays in the pool for future emergencies.
- **Growth loop:** each emergency recruits new voluntary donors, which directly counters
  paid donation.
- **Implementation:**
  - a new role `family`, or anonymous requests verified by phone;
  - `blood_requests.origin` (`hospital` or `family`) and `confirmed_by`;
  - a public page `/r/{code}` showing the request without patient identity;
  - register with `?pledge={code}`.

### F. Maternity standby circles (M): high clinical impact
- At an antenatal visit, the clinic registers the expected delivery date and the mother's
  blood group (with her consent). BloodLink finds **two or three compatible, eligible donors
  who agree to be on standby** in the weeks around the due date.
- If haemorrhage starts, the ward presses one button and the standby donors are texted
  first, with no search.
- **Why it matters:** postpartum haemorrhage kills within hours; a pre-arranged circle cuts
  the search to minutes.
- **Implementation:** a planned request with a window (`window_start`, `window_end`),
  pledges as `standby` (idea A), and a one-tap "activate" that turns it into a critical
  request.

### G. Recurring transfusions for sickle cell and thalassaemia (M)
- Patients who need blood every few weeks get a **recurring request** and a small **donor
  circle** that rotates, so no donor is asked inside their waiting period.
- Later, add **extended red-cell phenotype matching** to reduce antibody formation in
  frequently transfused patients, a known clinical problem.

### H. Donor health perks that are legal (S to M)
- Many Nigerians value knowing their **genotype and blood group**. After a confirmed
  donation, show the lab-confirmed group (idea C) and the haemoglobin. Partner labs can
  offer free genotype testing to regular donors.
- Add a digital donor card, the "next eligible date" countdown, milestones (3, 5, 10
  donations), and certificates for employers and universities.
- **Transport reimbursement** (a fixed, modest amount) is acceptable; cash or anything that
  looks like payment for blood is not.

### I. Platelet and rare-group registry (S)
- Flags for **apheresis-willing donors** and **rare groups** (Rh-negative, and later rarer
  phenotypes). Hospitals can search the registry directly for oncology, dengue or Lassa
  fever cases.

### J. Reach beyond smartphones (M to L)
- **WhatsApp** messages and replies ("Reply YES to pledge").
- **USSD** for feature phones (`*xxx#` to check eligibility or pledge).
- A **voice call** fallback for critical requests, in English, Pidgin, Yoruba, Hausa and
  Igbo.

### K. Blood bank stock exchange, before asking donors (L)
- Partner blood banks list screened units with their expiry dates. A hospital's request
  first checks **stock nearby**, then donors.
- **Near-expiry alerts** move units to where they will be used before they are wasted
  (platelets especially).
- **Legal note:** blood cannot be sold. Blood banks charge **processing fees** (screening,
  storage). Any fee BloodLink touches must be a processing or logistics fee, structured with
  legal advice.

### L. Integration with the national platform (M)
The NBSA has launched a digital blood management platform
([NAN](https://nannews.ng/nbsa-inaugurates-digital-blood-management-platform/)). Position
BloodLink as the **emergency donor layer that feeds it**: offer an API or export of
confirmed donations, rather than competing with it.

---

## 3. Can private individuals pay?

**Not for blood.** Buying or selling blood is prohibited by the National Health Act 2014,
and paid donation is what makes blood unsafe (higher infection rates among paid donors are
the reason WHO promotes voluntary unpaid donation). Blood is also only ever transfused in a
hospital after a cross-match, so an individual cannot simply "receive blood" through an app.

**What individuals can do, and what can be charged:**

| Option | Who pays | Allowed? |
|---|---|---|
| A family starts a request; the hospital confirms it (idea E) | Nobody: **free for families**, always | Yes, and it should stay free in emergencies |
| Donor transport reimbursement, passed through to the donor | The family or the hospital; BloodLink keeps a small processing fee | Yes, if modest and fixed, as expense reimbursement |
| **BloodLink Care** plans for chronic patients (sickle cell, thalassaemia): recurring scheduling, donor circle, reminders (idea G) | The family, an HMO or the hospital | Yes: it pays for coordination, not blood |
| **Maternity standby** sold as an add-on to antenatal care (idea F) | The HMO or the hospital (best), or the family | Yes: the same principle |
| Paying a donor, or "priority" for a fee in an emergency | n/a | **No.** Illegal and unethical, and it would destroy trust. |

**Recommendation:** keep every emergency free for patients and families. Earn from
institutions (hospitals, HMOs, employers, government). Charge families only for optional,
planned coordination services, and offer those through HMOs wherever possible.

---

## 4. Making money in the long run

| Stream | Customer | How it is priced | When |
|---|---|---|---|
| **Hospital subscription** | Private hospitals | Monthly, by request volume; free pilot first | Now |
| **Network licence** | Blood banks, hospital groups, state ministries | Annual, per site | Year 1 |
| **HMO and insurer contracts** | HMOs | Per member per month for maternity standby and chronic-care plans; they save on complications and longer stays | Year 1 to 2 |
| **Corporate donor drives** | Banks, telcos, oil and gas, universities (CSR) | Per drive or a yearly sponsorship, with an impact report | Year 1 |
| **Stock exchange and logistics** | Blood banks and couriers | Processing and logistics fee per transfer (legal advice first) | Year 2 |
| **Data and dashboards** | NBSC/NBSA, state governments, NGOs and donors (Gates, Global Fund, USAID-type programmes) | Licence or grant: anonymised demand, shortages and fulfilment by LGA | Year 2 |
| **API** | Hospital management and lab system vendors | Per hospital or per call | Year 2 |
| **Partner perks** | Labs and brands sponsoring non-cash donor perks (idea H) | Sponsorship | Year 2 |

**What keeps costs down:**
- Text messages are the main running cost, so waves (idea D) send fewer messages per
  fulfilled request.
- WhatsApp and push notifications are cheaper than SMS for routine traffic.
- Free-tier hosting for the pilot.

**The moat:**
- a large, **verified, tracked voluntary donor pool**, with lab-confirmed groups and
  donation histories;
- years of fulfilment data that no chat bot or WhatsApp group has.

**The key figure to sell with:** median time to fulfil, before and after BloodLink. It is
already on the hospital dashboard.

---

## 5. Suggested build order from here

1. **A. Standby donors** and **B. Screening outcomes.** Small, and they make the clinical
   story credible at the viva.
2. **C. Verified blood group.** Small, and it improves matching quality.
3. **E. Family requests and share links.** This is how private individuals join, and the
   growth loop.
4. **D. Alert waves.** Fewer SMS per request, faster fulfilment.
5. **F. Maternity standby** and **G. Recurring transfusions:** the HMO revenue story.
6. Then J (WhatsApp and USSD), K (stock exchange) and L (national platform).

---

## 6. Is the pilot offer on the landing page fixed?

Today the pricing tiers ("Pilot: free for three months", "Open now") are written in
`frontend/components/landing/Pricing.tsx`, so they change only when the code changes and is
redeployed. That is fine for a capstone, but the offer should change over time: the pilot
fills up, prices are agreed, offers end.

Options, simplest first:

1. **One settings file** (`frontend/lib/pricing.ts`) holding the tiers, prices and an
   `openUntil` date. The "Open now" badge hides itself after that date, and prices are
   edited in one place. *(S)*
2. **Admin-managed plans:** a `plans` table and an admin screen to edit tiers, prices and
   the pilot's open or closed state, with no redeploy. *(M)*
3. Later, **Paystack billing** reads the same `plans` table, so what the page shows is
   exactly what is charged. *(L)*
