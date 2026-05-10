"""
schema.py -- LEAP Portal
Database connection management and schema initialisation.
"""

import sqlite3
import os
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_UPIN     = os.environ.get("DB_UPIN",     os.path.join(BASE_DIR, "upinmgmt.sqlite"))
DB_MASTER   = os.environ.get("DB_MASTER",   os.path.join(BASE_DIR, "lawrence_master.sqlite"))
DB_OUTREACH = os.environ.get("DB_OUTREACH", os.path.join(BASE_DIR, "lawrence_energy.sqlite"))


# ------------------------------------------------------------------
# Connection helpers
# ------------------------------------------------------------------

def get_db(path):
    attr = f"_db_{os.path.basename(path)}"
    if not hasattr(g, attr):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        setattr(g, attr, conn)
    return getattr(g, attr)

def upin_db():     return get_db(DB_UPIN)
def master_db():   return get_db(DB_MASTER)
def outreach_db(): return get_db(DB_OUTREACH)


# ------------------------------------------------------------------
# Schema -- destructive (dev only, called from __main__)
# ------------------------------------------------------------------

def init_schema():
    conn = sqlite3.connect(DB_UPIN)
    cur  = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS registrations")
    cur.execute("""
        CREATE TABLE registrations (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number        TEXT NOT NULL,
            upin_used             TEXT,
            normalized_address    TEXT,
            service_unit          TEXT,
            role                  TEXT,
            intent                TEXT,
            unit_count_reported   INTEGER,
            unit_count_known      INTEGER,
            unit_count_flag       TEXT,
            mass_save_enrolled    TEXT,
            needs_callback        TEXT,
            event_rsvp_id         INTEGER,
            contact_name          TEXT,
            contact_phone         TEXT,
            contact_email         TEXT,
            registered_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address            TEXT,
            pending_upin          TEXT,
            reported_fuel         TEXT,
            inviting_event_id     INTEGER
        )
    """)

    cur.execute("DROP TABLE IF EXISTS event_wards")
    cur.execute("DROP TABLE IF EXISTS event_rsvps")
    cur.execute("DROP TABLE IF EXISTS events")
    cur.execute("DROP TABLE IF EXISTS settings")

    cur.execute("""
        CREATE TABLE events (
            event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            event_date  TEXT NOT NULL,
            event_time  TEXT NOT NULL,
            location    TEXT NOT NULL,
            capacity    INTEGER NOT NULL DEFAULT 50,
            status      TEXT NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','cancelled')),
            audience    TEXT NOT NULL DEFAULT 'residential',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE event_wards (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id  INTEGER NOT NULL REFERENCES events(event_id),
            ward      TEXT    NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE event_rsvps (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id       INTEGER NOT NULL REFERENCES events(event_id),
            account_number TEXT NOT NULL,
            upin           TEXT,
            service_unit   TEXT,
            rsvp_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cancelled_at   TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cur.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('events_to_show','2')")
    conn.commit()
    conn.close()
    print("Schema initialised.")


# ------------------------------------------------------------------
# Schema -- safe (production, called at app startup)
# ------------------------------------------------------------------

def ensure_schema():
    """
    Safe schema creation for gunicorn / Render startup.
    Uses CREATE TABLE IF NOT EXISTS -- never drops existing data.
    Called once at app startup via before_request guard.
    """
    conn = sqlite3.connect(DB_UPIN)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number        TEXT NOT NULL,
            upin_used             TEXT,
            normalized_address    TEXT,
            service_unit          TEXT,
            role                  TEXT,
            intent                TEXT,
            unit_count_reported   INTEGER,
            unit_count_known      INTEGER,
            unit_count_flag       TEXT,
            mass_save_enrolled    TEXT,
            needs_callback        TEXT,
            event_rsvp_id         INTEGER,
            contact_name          TEXT,
            contact_phone         TEXT,
            contact_email         TEXT,
            registered_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address            TEXT,
            pending_upin          TEXT,
            reported_fuel         TEXT,
            inviting_event_id     INTEGER
        )
    """)

    # Migration guards -- add new columns to existing databases without a full reset
    for col_sql in [
        "ALTER TABLE registrations ADD COLUMN pending_upin TEXT",
        "ALTER TABLE registrations ADD COLUMN reported_fuel TEXT",
        "ALTER TABLE registrations ADD COLUMN inviting_event_id INTEGER",
    ]:
        try:
            cur.execute(col_sql)
            conn.commit()
        except Exception:
            pass  # Column already exists -- safe to ignore

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            event_date  TEXT NOT NULL,
            event_time  TEXT NOT NULL,
            location    TEXT NOT NULL,
            capacity    INTEGER NOT NULL DEFAULT 50,
            status      TEXT NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','cancelled')),
            audience    TEXT NOT NULL DEFAULT 'residential',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration guard -- add audience column to existing events table
    try:
        cur.execute("ALTER TABLE events ADD COLUMN audience TEXT NOT NULL DEFAULT 'residential'")
        conn.commit()
    except Exception:
        pass  # Column already exists -- safe to ignore

    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_wards (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id  INTEGER NOT NULL REFERENCES events(event_id),
            ward      TEXT    NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_rsvps (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id       INTEGER NOT NULL REFERENCES events(event_id),
            account_number TEXT NOT NULL,
            upin           TEXT,
            service_unit   TEXT,
            rsvp_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cancelled_at   TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cur.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('events_to_show','2')")
    cur.execute("INSERT OR IGNORE INTO settings (key,value) VALUES ('outreach_at_risk_days','3')")

    # Multi-touch outreach record. One row per contact attempt against a
    # registration. The Advocate's "current outreach state" of any
    # registration is derived from this table's most-recent row for that
    # registration_id -- registrations.* is never updated by this flow.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS outreach_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id INTEGER NOT NULL REFERENCES registrations(id),
            contacted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            contacted_by    TEXT NOT NULL DEFAULT 'admin',
            channel         TEXT NOT NULL
                                CHECK(channel IN ('call','email','whatsapp','other')),
            outcome         TEXT NOT NULL
                                CHECK(outcome IN ('reached','unreachable','enrolled','not_interested')),
            notes           TEXT
        )
    """)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_outreach_log_registration "
        "ON outreach_log(registration_id, contacted_at DESC)"
    )

    # Save Progress (Roadmap §2 PR-A2). Holds an opaque token + the
    # snapshot of session state at the latest funnel step the resident
    # reached. /resume/<token> restores that snapshot so a resident who
    # got distracted can come back without restarting. The session_state
    # is JSON; it's the dict() of the Flask session at save time. Rows
    # expire on their own clock (default 7 days) and are purged
    # opportunistically on /resume hits -- no separate cleanup job.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS partial_registrations (
            token         TEXT PRIMARY KEY,
            contact_email TEXT NOT NULL,
            contact_phone TEXT,
            session_state TEXT NOT NULL,
            last_step     TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at    TIMESTAMP NOT NULL
        )
    """)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_partial_registrations_expires "
        "ON partial_registrations(expires_at)"
    )
    conn.commit()
    conn.close()
