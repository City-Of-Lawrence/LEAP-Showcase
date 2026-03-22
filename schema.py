"""
schema.py — LEAP Portal
Database connection management and schema initialisation.
"""

import sqlite3
import os
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_UPIN     = os.environ.get("DB_UPIN",     os.path.join(BASE_DIR, "upinmgmt.sqlite"))
DB_MASTER   = os.environ.get("DB_MASTER",   os.path.join(BASE_DIR, "lawrence_master.sqlite"))
DB_OUTREACH = os.environ.get("DB_OUTREACH", os.path.join(BASE_DIR, "LEAPMailings_clean.sqlite"))


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
# Schema — destructive (dev only, called from __main__)
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
            reported_fuel         TEXT
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
# Schema — safe (production, called at app startup)
# ------------------------------------------------------------------

def ensure_schema():
    """
    Safe schema creation for gunicorn / Render startup.
    Uses CREATE TABLE IF NOT EXISTS — never drops existing data.
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
            reported_fuel         TEXT
        )
    """)
    # Migration guards — add new columns to existing databases without a full reset
    for col_sql in [
        "ALTER TABLE registrations ADD COLUMN pending_upin TEXT",
        "ALTER TABLE registrations ADD COLUMN reported_fuel TEXT",
    ]:
        try:
            cur.execute(col_sql)
            conn.commit()
        except Exception:
            pass  # Column already exists — safe to ignore

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
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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
    conn.commit()
    conn.close()
