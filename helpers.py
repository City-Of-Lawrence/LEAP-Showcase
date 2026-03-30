"""
helpers.py — LEAP Portal
Shared helper functions used by both public and admin routes.
"""

import re
import functools
from datetime import datetime, timezone
from flask import session, redirect, url_for
from schema import upin_db, master_db, outreach_db
from translations import t, get_roles


# ------------------------------------------------------------------
# Language
# ------------------------------------------------------------------

def get_lang():
    """Return current language from session, default English."""
    return session.get("lang", "en")


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

def get_setting(key, default=""):
    row = upin_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


# ------------------------------------------------------------------
# UPIN & property lookups
# ------------------------------------------------------------------

def lookup_by_upin(upin_plain):
    """
    Fast UPIN lookup using HMAC index column.

    Strategy:
      1. Compute HMAC-SHA256 of the submitted plaintext UPIN.
      2. SELECT the single row where upin_hmac matches — O(1) indexed lookup.
      3. Verify Argon2 on that one row only as a second-factor integrity check.

    Falls back to the legacy full-table Argon2 scan ONLY if UPIN_HMAC_KEY is
    not set — keeps the app working during the migration window.
    """
    import os, hmac, hashlib
    from argon2 import PasswordHasher, exceptions

    hmac_key = os.environ.get("UPIN_HMAC_KEY", "").encode()

    if hmac_key:
        # Fast path: HMAC index lookup
        digest = hmac.new(hmac_key, upin_plain.encode(), hashlib.sha256).hexdigest()
        row = upin_db().execute(
            "SELECT * FROM upin WHERE upin_hmac=? AND status='active'",
            (digest,)
        ).fetchone()
        if not row:
            return None
        # Argon2 integrity check on the single matched row
        ph = PasswordHasher()
        try:
            ph.verify(row["upin_hash"], upin_plain)
            return row
        except Exception:
            return None

    # Slow fallback: full table scan (pre-migration only)
    ph = PasswordHasher()
    for row in upin_db().execute("SELECT * FROM upin WHERE status='active'"):
        try:
            ph.verify(row["upin_hash"], upin_plain)
            return row
        except exceptions.VerifyMismatchError:
            continue
        except Exception:
            continue
    return None

def lookup_property(account_number):
    return master_db().execute(
        """SELECT account_number, normalized_address, heating_fuel_description,
                  primary_land_use_code_description, total_occupancy,
                  vision_id, lean_eligibility, owner_1_name
           FROM Assessment_L_Parcels WHERE account_number=? LIMIT 1""",
        (account_number,)
    ).fetchone()


# ------------------------------------------------------------------
# Address search
# ------------------------------------------------------------------

def search_streets_by_role(street_name: str, role: str):
    """
    Step 1 — find distinct street names matching input.
    Returns list of matching street name strings.
    Role determines which DB(s) to query.
    """
    pattern = f"%{street_name.strip().upper()}%"
    streets = set()

    if role == "landlord":
        rows = master_db().execute(
            """SELECT DISTINCT normalized_address FROM Assessment_L_Parcels
               WHERE UPPER(normalized_address) LIKE ?
               ORDER BY normalized_address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            parts = r["normalized_address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())
        # Always query outreach DB in parallel — not a fallback
        rows = outreach_db().execute(
            """SELECT DISTINCT Service_Address FROM Outreach_Master_Unified
               WHERE UPPER(Service_Address) LIKE ?
               ORDER BY Service_Address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            parts = r["Service_Address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())

    elif role == "renter":
        rows = outreach_db().execute(
            """SELECT DISTINCT Service_Address FROM Outreach_Master_Unified
               WHERE UPPER(Service_Address) LIKE ?
               ORDER BY Service_Address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            parts = r["Service_Address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())

    elif role == "owner_occupant":
        # Master DB only -- owner-occupants are single-family homeowners,
        # not in the rental outreach DB
        rows = master_db().execute(
            """SELECT DISTINCT normalized_address FROM Assessment_L_Parcels
               WHERE UPPER(normalized_address) LIKE ?
               ORDER BY normalized_address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            parts = r["normalized_address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())

    else:  # property_manager, small_business -- both DBs
        rows = outreach_db().execute(
            """SELECT DISTINCT Service_Address FROM Outreach_Master_Unified
               WHERE UPPER(Service_Address) LIKE ?
               ORDER BY Service_Address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            parts = r["Service_Address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())
        rows = master_db().execute(
            """SELECT DISTINCT normalized_address FROM Assessment_L_Parcels
               WHERE UPPER(normalized_address) LIKE ?
               ORDER BY normalized_address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            parts = r["normalized_address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())

    return sorted(streets)


def get_all_streets_by_role(role: str):
    """
    Returns the full sorted list of distinct street names for the given role.
    Used to populate the live filter on the street search screen.
    Same DB logic as search_streets_by_role but with no filter pattern.
    """
    streets = set()

    if role == "landlord":
        rows = master_db().execute(
            """SELECT DISTINCT normalized_address FROM Assessment_L_Parcels
               ORDER BY normalized_address"""
        ).fetchall()
        for r in rows:
            parts = r["normalized_address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())
        rows = outreach_db().execute(
            """SELECT DISTINCT Service_Address FROM Outreach_Master_Unified
               ORDER BY Service_Address"""
        ).fetchall()
        for r in rows:
            parts = r["Service_Address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())

    elif role == "renter":
        rows = outreach_db().execute(
            """SELECT DISTINCT Service_Address FROM Outreach_Master_Unified
               ORDER BY Service_Address"""
        ).fetchall()
        for r in rows:
            parts = r["Service_Address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())

    elif role == "owner_occupant":
        # Master DB only -- owner-occupants are single-family homeowners
        rows = master_db().execute(
            """SELECT DISTINCT normalized_address FROM Assessment_L_Parcels
               ORDER BY normalized_address"""
        ).fetchall()
        for r in rows:
            parts = r["normalized_address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())

    else:  # property_manager, small_business
        rows = outreach_db().execute(
            """SELECT DISTINCT Service_Address FROM Outreach_Master_Unified
               ORDER BY Service_Address"""
        ).fetchall()
        for r in rows:
            parts = r["Service_Address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())
        rows = master_db().execute(
            """SELECT DISTINCT normalized_address FROM Assessment_L_Parcels
               ORDER BY normalized_address"""
        ).fetchall()
        for r in rows:
            parts = r["normalized_address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())

    return sorted(streets)


def search_addresses_on_street(street_name: str, role: str):
    """
    Step 2 — return all addresses on a confirmed street name.
    Each result is a dict with: account_number, display_address, service_unit, source
    """
    pattern = f"% {street_name.strip().upper()}%"
    results = []
    seen = set()

    if role in ("landlord",):
        rows = master_db().execute(
            """SELECT account_number, normalized_address, '' AS service_unit
               FROM Assessment_L_Parcels
               WHERE UPPER(normalized_address) LIKE ?
               ORDER BY normalized_address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            key = r["account_number"]
            if key not in seen:
                seen.add(key)
                results.append({
                    "account_number":  r["account_number"],
                    "display_address": r["normalized_address"],
                    "service_unit":    r["service_unit"] or "",
                    "source":          "master",
                })
        # Always query outreach DB in parallel — not a fallback
        rows = outreach_db().execute(
            """SELECT DISTINCT Account_Number, Service_Address, Service_Unit
               FROM Outreach_Master_Unified
               WHERE UPPER(Service_Address) LIKE ?
               ORDER BY Service_Address, Service_Unit LIMIT 500""",
            (pattern,)
        ).fetchall()
        for r in rows:
            key = r["Account_Number"]
            if key not in seen:
                seen.add(key)
                addr = r["Service_Address"]
                if r["Service_Unit"]:
                    addr += f" Unit {r['Service_Unit']}"
                results.append({
                    "account_number":  r["Account_Number"],
                    "display_address": addr,
                    "service_unit":    r["Service_Unit"] or "",
                    "source":          "outreach",
                })

    elif role == "owner_occupant":
        # Master DB only, whole-building addresses only -- no unit rows.
        # Owner-occupants live in single-family homes; unit-level rows
        # from the outreach DB are rental units and do not apply.
        rows = master_db().execute(
            """SELECT account_number, normalized_address
               FROM Assessment_L_Parcels
               WHERE UPPER(normalized_address) LIKE ?
               ORDER BY normalized_address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            key = r["account_number"]
            if key not in seen:
                seen.add(key)
                results.append({
                    "account_number":  r["account_number"],
                    "display_address": r["normalized_address"],
                    "service_unit":    "",
                    "source":          "master",
                })

    elif role == "renter":
        rows = outreach_db().execute(
            """SELECT Service_Address, Service_Unit, Account_Number
               FROM Outreach_Master_Unified
               WHERE UPPER(Service_Address) LIKE ?
               GROUP BY Service_Address, Service_Unit
               ORDER BY Service_Address, Service_Unit LIMIT 500""",
            (pattern,)
        ).fetchall()
        for r in rows:
            key = f"{r['Service_Address']}|{r['Service_Unit']}"
            if key not in seen:
                seen.add(key)
                addr = r["Service_Address"]
                if r["Service_Unit"]:
                    addr += f" Unit {r['Service_Unit']}"
                results.append({
                    "account_number":  r["Account_Number"],
                    "display_address": addr,
                    "service_unit":    r["Service_Unit"] or "",
                    "source":          "outreach",
                })

    else:  # others — both DBs, outreach first
        rows = outreach_db().execute(
            """SELECT Service_Address, Service_Unit, Account_Number
               FROM Outreach_Master_Unified
               WHERE UPPER(Service_Address) LIKE ?
               GROUP BY Service_Address, Service_Unit
               ORDER BY Service_Address, Service_Unit LIMIT 500""",
            (pattern,)
        ).fetchall()
        for r in rows:
            key = f"{r['Service_Address']}|{r['Service_Unit']}"
            if key not in seen:
                seen.add(key)
                addr = r["Service_Address"]
                if r["Service_Unit"]:
                    addr += f" Unit {r['Service_Unit']}"
                results.append({
                    "account_number":  r["Account_Number"],
                    "display_address": addr,
                    "service_unit":    r["Service_Unit"] or "",
                    "source":          "outreach",
                })
        rows = master_db().execute(
            """SELECT account_number, normalized_address
               FROM Assessment_L_Parcels
               WHERE UPPER(normalized_address) LIKE ?
               ORDER BY normalized_address LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            key = r["account_number"]
            if key not in seen:
                seen.add(key)
                results.append({
                    "account_number":  r["account_number"],
                    "display_address": r["normalized_address"],
                    "service_unit":    "",
                    "source":          "master",
                })

    return results


# ------------------------------------------------------------------
# Unit normalisation
# ------------------------------------------------------------------

def normalize_unit(unit: str) -> str:
    """Strip common prefix words so 'APT 323' and '323' compare equal."""
    return re.sub(r'^(APT|UNIT|STE|SUITE|#)\s*', '', unit.strip().upper())


# ------------------------------------------------------------------
# Registration helpers
# ------------------------------------------------------------------

def has_prior_registration(account_number, service_unit=""):
    """Return True if this specific unit (or property for landlords) has registered before."""
    norm = normalize_unit(service_unit) if service_unit else ""
    if norm:
        row = upin_db().execute(
            "SELECT COUNT(*) FROM registrations WHERE account_number=? AND service_unit=?",
            (account_number, norm)
        ).fetchone()
    else:
        row = upin_db().execute(
            "SELECT COUNT(*) FROM registrations WHERE account_number=? AND (service_unit IS NULL OR service_unit='')",
            (account_number,)
        ).fetchone()
    return row[0] > 0

def get_prior_registration_summary(account_number, service_unit=""):
    """Return role and date of most recent registration for this unit/property."""
    norm = normalize_unit(service_unit) if service_unit else ""
    if norm:
        return upin_db().execute(
            """SELECT role, registered_at FROM registrations
               WHERE account_number=? AND service_unit=?
               ORDER BY registered_at DESC LIMIT 1""",
            (account_number, norm)
        ).fetchone()
    else:
        return upin_db().execute(
            """SELECT role, registered_at FROM registrations
               WHERE account_number=? AND (service_unit IS NULL OR service_unit='')
               ORDER BY registered_at DESC LIMIT 1""",
            (account_number,)
        ).fetchone()

def save_registration(data):
    """Normalise service_unit then INSERT a registration row. Returns new row id."""
    if data.get("service_unit"):
        data["service_unit"] = normalize_unit(data["service_unit"])
    cur = upin_db().execute(
        """INSERT INTO registrations (
            account_number, upin_used, normalized_address, service_unit,
            role, intent, unit_count_reported, unit_count_known,
            unit_count_flag, mass_save_enrolled, needs_callback,
            event_rsvp_id, contact_name, contact_phone, contact_email,
            ip_address, pending_upin, reported_fuel
        ) VALUES (
            :account_number, :upin_used, :normalized_address, :service_unit,
            :role, :intent, :unit_count_reported, :unit_count_known,
            :unit_count_flag, :mass_save_enrolled, :needs_callback,
            :event_rsvp_id, :contact_name, :contact_phone, :contact_email,
            :ip_address, :pending_upin, :reported_fuel
        )""",
        data
    )
    upin_db().commit()
    return cur.lastrowid


# ------------------------------------------------------------------
# Event helpers
# ------------------------------------------------------------------

def get_upcoming_events(limit=2):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = upin_db().execute(
        """SELECT e.*,
                  (SELECT COUNT(*) FROM event_rsvps r
                   WHERE r.event_id=e.event_id AND r.cancelled_at IS NULL) AS rsvp_count
           FROM events e
           WHERE e.status='active' AND e.event_date >= ?
           ORDER BY e.event_date, e.event_time""",
        (today,)
    ).fetchall()
    available = [r for r in rows if r["rsvp_count"] < r["capacity"]]
    return available[:limit]

def get_event_wards(event_id):
    rows = upin_db().execute(
        "SELECT ward FROM event_wards WHERE event_id=?", (event_id,)
    ).fetchall()
    return [r["ward"] for r in rows]

def add_event_rsvp(event_id, account_number, upin="", service_unit=""):
    cur = upin_db().execute(
        "INSERT INTO event_rsvps (event_id, account_number, upin, service_unit) VALUES (?,?,?,?)",
        (event_id, account_number, upin, normalize_unit(service_unit) if service_unit else "")
    )
    upin_db().commit()
    return cur.lastrowid

def get_existing_rsvps(upin_plain, account_number="", service_unit=""):
    """Return dict of {event_id: rsvp_row_id} for active (non-cancelled) RSVPs.

    Strategy:
    1. Query by UPIN if present, also filtering by service_unit when available.
       This prevents cross-unit contamination for unit UPINs — a UPIN match
       alone is not sufficient when multiple units share the same account_number.
    2. Fall through to account_number + service_unit lookup — handles the case
       where a prior RSVP was saved before UPIN was issued.
    """
    norm = normalize_unit(service_unit) if service_unit else ""
    if upin_plain:
        if norm:
            rows = upin_db().execute(
                "SELECT id, event_id FROM event_rsvps WHERE upin=? AND service_unit=? AND cancelled_at IS NULL",
                (upin_plain, norm)
            ).fetchall()
        else:
            rows = upin_db().execute(
                "SELECT id, event_id FROM event_rsvps WHERE upin=? AND cancelled_at IS NULL",
                (upin_plain,)
            ).fetchall()
        if rows:
            return {r["event_id"]: r["id"] for r in rows}
    if account_number:
        rows = upin_db().execute(
            "SELECT id, event_id FROM event_rsvps WHERE account_number=? AND service_unit=? AND cancelled_at IS NULL",
            (account_number, norm)
        ).fetchall()
        return {r["event_id"]: r["id"] for r in rows}
    return {}

def cancel_event_rsvp(upin_plain, event_id):
    """Soft-cancel an existing RSVP by setting cancelled_at timestamp."""
    if not upin_plain:
        return
    upin_db().execute(
        """UPDATE event_rsvps SET cancelled_at=CURRENT_TIMESTAMP
           WHERE upin=? AND event_id=? AND cancelled_at IS NULL""",
        (upin_plain, event_id)
    )
    upin_db().commit()


# ------------------------------------------------------------------
# Auth decorator
# ------------------------------------------------------------------

def admin_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.admin_login"))
        return f(*args, **kwargs)
    return decorated
