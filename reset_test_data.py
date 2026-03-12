"""
reset_test_data.py — LEAP demo reset utility
=============================================
Wipes transactional data from upinmgmt.sqlite for a clean demo start.

What gets CLEARED (default / full reset):
    event_rsvps     — all RSVPs, including cancelled ones
    registrations   — all visitor registrations
    audit_event     — full audit trail
    event_wards     — event-to-ward assignments
    events          — ALL events, including cancelled ones  ← the new part

What is PRESERVED (always):
    upin            — property UPINs (QR codes embed these; wiping breaks QR)
    settings        — admin configuration

Optional flag:
    --keep-events   Wipe only registrations/RSVPs; leave events intact.
                    Useful when you want to re-test RSVP flows against
                    events you already built.

Usage:
    python reset_test_data.py               # full demo reset
    python reset_test_data.py --keep-events # registrations only
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "upinmgmt.sqlite")

# Child tables must come before parent tables to avoid FK constraint errors.
FULL_RESET_TABLES = [
    "event_rsvps",
    "registrations",
    "audit_event",
    "event_wards",
    "events",
]

REGISTRATIONS_ONLY_TABLES = [
    "event_rsvps",
    "registrations",
    "audit_event",
]


def ensure_schema(con):
    """Apply any missing schema columns without dropping data."""
    cols = [row[1] for row in con.execute("PRAGMA table_info(event_rsvps)")]
    if "service_unit" not in cols:
        con.execute("ALTER TABLE event_rsvps ADD COLUMN service_unit TEXT")
        con.commit()
        print("  Schema updated: added event_rsvps.service_unit")
    else:
        print("  Schema OK: event_rsvps.service_unit present")


def show_counts(con, tables):
    print("\n  Current row counts:")
    for t in tables:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"    {t:<20} {n:>6} rows")
        except Exception:
            print(f"    {t:<20}  (table not found — will skip)")


def reset_tables(con, tables):
    print()
    cleared = []
    for t in tables:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            con.execute(f"DELETE FROM {t}")
            print(f"  Cleared  {t:<20} ({count} rows deleted)")
            cleared.append(t)
        except Exception as e:
            print(f"  SKIPPED  {t:<20} ({e})")

    if cleared:
        placeholders = ",".join("?" * len(cleared))
        con.execute(
            f"UPDATE sqlite_sequence SET seq = 0 WHERE name IN ({placeholders})",
            cleared,
        )
    con.commit()


def main():
    keep_events = "--keep-events" in sys.argv
    tables = REGISTRATIONS_ONLY_TABLES if keep_events else FULL_RESET_TABLES
    mode = (
        "registrations/RSVPs only  (events preserved)"
        if keep_events
        else "FULL DEMO RESET  (events + registrations + RSVPs)"
    )

    print(f"\n{'='*60}")
    print(f"  LEAP Demo Reset Utility")
    print(f"  Mode : {mode}")
    print(f"  DB   : {DB_PATH}")
    print(f"{'='*60}")

    if not os.path.exists(DB_PATH):
        print(f"\nERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(con)
        show_counts(con, tables)

        print(f"\n  Tables to be cleared:")
        for t in tables:
            print(f"    - {t}")
        print()

        confirm = input("  Type YES to confirm deletion: ").strip()
        if confirm != "YES":
            print("  Aborted — nothing changed.")
            return

        reset_tables(con, tables)

        print(f"\n{'='*60}")
        print("  Done — database is clean for demo.")
        if not keep_events:
            print("  Next: create your demo events in the Admin panel,")
            print("        then restart app.py.")
        else:
            print("  Next: restart app.py to begin fresh testing.")
        print(f"{'='*60}\n")

    except Exception as e:
        con.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()
