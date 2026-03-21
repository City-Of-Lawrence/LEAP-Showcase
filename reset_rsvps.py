"""
reset_rsvps.py — Wipe RSVP and registration records for demo reset
Run in Render shell: python3 reset_rsvps.py

Options:
  (no args)   Wipe event_rsvps only
  --full      Wipe event_rsvps AND registrations

Leaves UPINs, events, and event_wards intact.
"""
import sqlite3, os, sys

DB_PATH = os.environ.get("DB_UPIN", "/data/upinmgmt.sqlite")
FULL = "--full" in sys.argv

if not os.path.exists(DB_PATH):
    print(f"ERROR: DB not found at {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)

rsvp_count = conn.execute("SELECT COUNT(*) FROM event_rsvps").fetchone()[0]
reg_count  = conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]

print(f"Current RSVPs:         {rsvp_count}")
print(f"Current registrations: {reg_count}")
print()

if FULL:
    print("Mode: FULL RESET — wiping event_rsvps AND registrations")
else:
    print("Mode: RSVPs only — wiping event_rsvps, keeping registrations")
    print("Tip: run with --full to also wipe registrations")

print()
confirm = input("Proceed? (yes/no): ").strip().lower()
if confirm != "yes":
    print("Aborted.")
    conn.close()
    sys.exit(0)

conn.execute("DELETE FROM event_rsvps")
print(f"Wiped {rsvp_count} RSVP records.")

if FULL:
    conn.execute("DELETE FROM registrations")
    print(f"Wiped {reg_count} registration records.")

conn.commit()
print()
print("Done. UPINs, events, and event_wards are untouched.")
conn.close()
