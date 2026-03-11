"""
reset_test_data.py — LEAP test data reset utility
Clears all registration and RSVP data from upinmgmt.sqlite.
Leaves upin, events, event_wards, and settings tables untouched.

Usage:
    python reset_test_data.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "upinmgmt.sqlite")

TABLES_TO_CLEAR = [
    "registrations",
    "event_rsvps",
    "audit_event",
]

def ensure_schema(con):
    """Apply any missing schema changes without dropping data."""
    # event_rsvps.service_unit — added for street-path renter RSVP dedup
    cols = [row[1] for row in con.execute("PRAGMA table_info(event_rsvps)")]
    if "service_unit" not in cols:
        con.execute("ALTER TABLE event_rsvps ADD COLUMN service_unit TEXT")
        con.commit()
        print("  Schema updated: added event_rsvps.service_unit")
    else:
        print("  Schema OK: event_rsvps.service_unit already present")

def reset():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    confirm = input("This will DELETE all registrations and RSVPs. Type YES to confirm: ").strip()
    if confirm != "YES":
        print("Aborted.")
        return

    con = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(con)
        print()
        for table in TABLES_TO_CLEAR:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            con.execute(f"DELETE FROM {table}")
            print(f"  Cleared {table} ({count} rows deleted)")

        # Reset auto-increment counters
        con.execute(
            "UPDATE sqlite_sequence SET seq=0 WHERE name IN (?,?,?)",
            TABLES_TO_CLEAR
        )
        con.commit()
        print("\nDone — test data cleared, ID counters reset to 0.")
        print("Restart app.py to begin fresh testing.")
    except Exception as e:
        con.rollback()
        print(f"ERROR: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    reset()
