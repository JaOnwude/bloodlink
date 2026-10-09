# Research

No feature work is accepted until this document is complete and signed off.

## 1. User evidence

### Conversation 1
- Role / organisation:
- Date:
- Questions asked:
- What surprised me:
- Checkable artefact (attach or link):

### Conversation 2
- Role / organisation:
- Date:
- Questions asked:
- What surprised me:
- Checkable artefact (attach or link):

Suggested questions: How do you find blood today when a patient needs it urgently? Who do
you call and how long does it take? How often does a request go unfilled, and why? What
would make you trust an app for this? What would you pay for each month, and who approves
that spend?

## 2. Market

| Competitor or workaround | What it charges | What it misses |
|---|---|---|
| | | |
| | | |

## 3. Cited sources

| Source | Key fact | How it changes the design |
|---|---|---|
| Donor eligibility (national transfusion service / WHO): interval, age, weight | | Replaces the placeholder intervals seeded in the component types |
| Red-cell compatibility chart | | Confirms the seeded compatibility rules |
| A Nigerian blood-supply statistic, or data protection law for health data | | |

## 4. Technical spike

`spikes/concurrent_pledge_spike.py`, run on 2026-10-09 against PostgreSQL 16: two
transactions pledge for the last remaining unit at the same instant.

- Result with the row lock (`SELECT ... FOR UPDATE`): `[accepted, rejected]`, exactly one
  succeeds.
- Result without the lock: `[accepted, accepted]`, the request is overbooked.

This is why the pledge service locks the request row before counting pledges.

## 5. Design decisions

1. Decision:  Finding it rests on:
2. Decision:  Finding it rests on:
3. Decision:  Finding it rests on:

## Sign-off

Reviewer: ____________  Date: ____________
