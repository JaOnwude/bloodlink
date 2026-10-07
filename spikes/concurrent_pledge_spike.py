"""Spike: prove two simultaneous pledges for the last unit cannot both succeed.

Run (database from docker compose must be up):
    SPIKE_LOCK=1 uv run --project backend python spikes/concurrent_pledge_spike.py   # expect 1 accepted
    SPIKE_LOCK=0 uv run --project backend python spikes/concurrent_pledge_spike.py   # expect 2 accepted (bug)
"""
import os
import sys
import threading

import psycopg

DSN = os.getenv("SPIKE_DSN", "postgresql://bloodlink:change-me@localhost:5433/bloodlink")
USE_LOCK = os.getenv("SPIKE_LOCK", "1") == "1"   # FOR UPDATE serialises competing pledges
results: list[str] = []
barrier = threading.Barrier(2)                    # both donors act at the same instant

def pledge(donor: int) -> None:
    with psycopg.connect(DSN) as conn, conn.transaction():
        barrier.wait()
        lock = " FOR UPDATE" if USE_LOCK else ""
        units = conn.execute(f"SELECT units_needed FROM spike_request WHERE id = 1{lock}").fetchone()[0]
        taken = conn.execute("SELECT count(*) FROM spike_pledge WHERE request_id = 1").fetchone()[0]
        conn.execute("SELECT pg_sleep(0.3)")      # widen the race window deliberately
        if taken >= units:
            results.append("rejected"); return
        conn.execute("INSERT INTO spike_pledge VALUES (1, %s)", (donor,))
        results.append("accepted")

with psycopg.connect(DSN, autocommit=True) as conn:
    conn.execute("DROP TABLE IF EXISTS spike_pledge, spike_request")
    conn.execute("CREATE TABLE spike_request (id int PRIMARY KEY, units_needed int)")
    conn.execute("CREATE TABLE spike_pledge (request_id int, donor int, UNIQUE (request_id, donor))")
    conn.execute("INSERT INTO spike_request VALUES (1, 1)")    # only ONE unit is needed

threads = [threading.Thread(target=pledge, args=(d,)) for d in (1, 2)]
[t.start() for t in threads]; [t.join() for t in threads]
with psycopg.connect(DSN, autocommit=True) as conn:
    conn.execute("DROP TABLE spike_pledge, spike_request")
print(f"lock={USE_LOCK} results={sorted(results)}")
sys.exit(0 if results.count("accepted") == (1 if USE_LOCK else 2) else 1)
