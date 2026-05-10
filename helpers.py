"""
helpers.py -- LEAP Portal
Shared helper functions used by both public and admin routes.

Outreach DB migration note (April 2026):
  Source changed from LEAPMailings_clean.sqlite / Outreach_Master_Unified
  to lawrence_energy.sqlite / mailing_addresses.
  SQL aliases preserve column names consumed downstream -- no Python changes
  below the query layer were needed.
  Residential/commercial filtering by tariff deferred: Lawrence housing stock
  includes residential units billed under G-1 (mixed-use buildings), so
  filtering would silently exclude legitimate residents. All addresses shown;
  user selects their unit. Revisit post-pilot if UX feedback warrants it.
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
      2. SELECT the single row where upin_hmac matches -- O(1) indexed lookup.
      3. Verify Argon2 on that one row only as a second-factor integrity check.

    Falls back to the legacy full-table Argon2 scan ONLY if UPIN_HMAC_KEY is
    not set -- keeps the app working during the migration window.
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
    Step 1 -- find distinct street names matching input.
    Returns list of matching street name strings.
    Role determines which DB(s) to query.

    Outreach DB: queries mailing_addresses.street_name directly (pre-parsed
    column -- cleaner than splitting full_address as was done with
    Outreach_Master_Unified.Service_Address).
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
        # Always query outreach DB in parallel -- not a fallback
        rows = outreach_db().execute(
            """SELECT DISTINCT street_name FROM mailing_addresses
               WHERE UPPER(street_name) LIKE ?
               ORDER BY street_name LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            if r["street_name"]:
                streets.add(r["street_name"].strip())

    elif role == "renter":
        rows = outreach_db().execute(
            """SELECT DISTINCT street_name FROM mailing_addresses
               WHERE UPPER(street_name) LIKE ?
               ORDER BY street_name LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            if r["street_name"]:
                streets.add(r["street_name"].strip())

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
            """SELECT DISTINCT street_name FROM mailing_addresses
               WHERE UPPER(street_name) LIKE ?
               ORDER BY street_name LIMIT 200""",
            (pattern,)
        ).fetchall()
        for r in rows:
            if r["street_name"]:
                streets.add(r["street_name"].strip())
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

    Outreach DB: ~800 distinct street names from 55,206 rows -- SQLite returns
    this in microseconds. No optimisation needed.
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
            """SELECT DISTINCT street_name FROM mailing_addresses
               ORDER BY street_name"""
        ).fetchall()
        for r in rows:
            if r["street_name"]:
                streets.add(r["street_name"].strip())

    elif role == "renter":
        rows = outreach_db().execute(
            """SELECT DISTINCT street_name FROM mailing_addresses
               ORDER BY street_name"""
        ).fetchall()
        for r in rows:
            if r["street_name"]:
                streets.add(r["street_name"].strip())

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
            """SELECT DISTINCT street_name FROM mailing_addresses
               ORDER BY street_name"""
        ).fetchall()
        for r in rows:
            if r["street_name"]:
                streets.add(r["street_name"].strip())
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
    Step 2 -- return all addresses on a confirmed street name.
    Each result is a dict with: account_number, display_address, service_unit, source

    Outreach DB: queries mailing_addresses with SQL aliases that preserve the
    column names (Service_Address, Service_Unit, Account_Number) consumed by
    the Python code below each query -- no changes needed to deduplication
    keys or result dict construction.

    street_name is pre-parsed in mailing_addresses, so we match on the
    street_name column directly rather than a LIKE pattern on full_address.
    street_number LIKE is used to allow partial number matches if needed, but
    an exact street_name match is sufficient for the address picker flow.
    """
    # Pattern for master DB (normalized_address = "123 BROADWAY ST")
    master_pattern = f"% {street_name.strip().upper()}%"
    results = []
    seen = set()

    if role in ("landlord",):
        rows = master_db().execute(
            """SELECT account_number, normalized_address, '' AS service_unit
               FROM Assessment_L_Parcels
               WHERE UPPER(normalized_address) LIKE ?
               ORDER BY normalized_address LIMIT 200""",
            (master_pattern,)
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
        # Always query outreach DB in parallel -- not a fallback
        rows = outreach_db().execute(
            """SELECT DISTINCT
                   account_number  AS Account_Number,
                   full_address    AS Service_Address,
                   unit            AS Service_Unit
               FROM mailing_addresses
               WHERE UPPER(street_name) = UPPER(?)
               ORDER BY full_address, unit LIMIT 500""",
            (street_name.strip(),)
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
            (master_pattern,)
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
            """SELECT
                   full_address    AS Service_Address,
                   unit            AS Service_Unit,
                   account_number  AS Account_Number
               FROM mailing_addresses
               WHERE UPPER(street_name) = UPPER(?)
               GROUP BY full_address, unit
               ORDER BY full_address, unit LIMIT 500""",
            (street_name.strip(),)
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

    else:  # others -- both DBs, outreach first
        rows = outreach_db().execute(
            """SELECT
                   full_address    AS Service_Address,
                   unit            AS Service_Unit,
                   account_number  AS Account_Number
               FROM mailing_addresses
               WHERE UPPER(street_name) = UPPER(?)
               GROUP BY full_address, unit
               ORDER BY full_address, unit LIMIT 500""",
            (street_name.strip(),)
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
            (master_pattern,)
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
    """Normalise service_unit then INSERT a registration row. Returns new row id.

    If the caller did not pass inviting_event_id, fall back to the session
    key set by the QR-landing routes (index / register_qr / renter_login).
    Lets attribution flow from the QR scan through to the persisted record
    without requiring every call site to thread the value explicitly.
    """
    if data.get("service_unit"):
        data["service_unit"] = normalize_unit(data["service_unit"])
    if "inviting_event_id" not in data:
        from flask import session
        data["inviting_event_id"] = session.get("inviting_event_id")
    cur = upin_db().execute(
        """INSERT INTO registrations (
            account_number, upin_used, normalized_address, service_unit,
            role, intent, unit_count_reported, unit_count_known,
            unit_count_flag, mass_save_enrolled, needs_callback,
            event_rsvp_id, contact_name, contact_phone, contact_email,
            ip_address, pending_upin, reported_fuel, inviting_event_id
        ) VALUES (
            :account_number, :upin_used, :normalized_address, :service_unit,
            :role, :intent, :unit_count_reported, :unit_count_known,
            :unit_count_flag, :mass_save_enrolled, :needs_callback,
            :event_rsvp_id, :contact_name, :contact_phone, :contact_email,
            :ip_address, :pending_upin, :reported_fuel, :inviting_event_id
        )""",
        data
    )
    upin_db().commit()
    return cur.lastrowid


# ------------------------------------------------------------------
# Audience filtering
# ------------------------------------------------------------------

# Maps each role to the set of audience values that role may see.
# 'general' events are visible to all roles.
_ROLE_AUDIENCES = {
    "renter":           {"residential", "general"},
    "owner_occupant":   {"residential", "general"},
    "landlord":         {"residential", "multi_unit", "general"},
    "property_manager": {"residential", "multi_unit", "general"},
    "small_business":   {"small_business", "general"},
}

def _audiences_for_role(role: str) -> list:
    """Return list of audience values the given role may see."""
    return list(_ROLE_AUDIENCES.get(role, {"residential", "general"}))


# ------------------------------------------------------------------
# Event helpers
# ------------------------------------------------------------------

def get_upcoming_events(role: str = "", limit: int = 2):
    """
    Return upcoming active events filtered by audience for the given role.

    Audience mapping:
      renter, owner_occupant  -> residential + general
      landlord                -> residential + multi_unit + general
      property_manager        -> residential + multi_unit + general
      small_business          -> small_business + general
      (unknown/empty)         -> residential + general (safe default)

    lra and lec are not yet routed -- no role sees them currently.
    """
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    audiences = _audiences_for_role(role)

    placeholders = ",".join("?" * len(audiences))
    rows = upin_db().execute(
        f"""SELECT e.*,
                  (SELECT COUNT(*) FROM event_rsvps r
                   WHERE r.event_id=e.event_id AND r.cancelled_at IS NULL) AS rsvp_count
           FROM events e
           WHERE e.status='active'
             AND e.event_date >= ?
             AND e.audience IN ({placeholders})
           ORDER BY e.event_date, e.event_time""",
        [today] + audiences
    ).fetchall()
    # Defensive: capacity should always be set (NOT NULL DEFAULT 50 in schema), but
    # legacy rows imported from an earlier schema may have NULL — treat as full so
    # the event doesn't surface to residents until capacity is corrected by staff.
    available = [r for r in rows if (r["rsvp_count"] or 0) < (r["capacity"] or 0)]
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
       This prevents cross-unit contamination for unit UPINs -- a UPIN match
       alone is not sufficient when multiple units share the same account_number.
    2. Fall through to account_number + service_unit lookup -- handles the case
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


# ------------------------------------------------------------------
# Save Progress (Roadmap §2 PR-A2)
# ------------------------------------------------------------------
# Opaque tokens that let a resident pause mid-funnel and resume from a
# resume link emailed to them. Storage is partial_registrations
# (created in schema.py:ensure_schema). Tokens default to a 7-day TTL.

import json
import secrets
from datetime import timedelta

PARTIAL_TOKEN_TTL_DAYS = 7


def _serialize_session_state(state) -> str:
    """JSON-encode the session dict, stripping non-funnel keys.

    Flask's session is a SecureCookieSession; iterating it yields the
    same data as a dict. We drop our own bookkeeping keys (lang,
    _partial_token) so the snapshot is just the funnel state -- restore
    pulls them back into a fresh session without polluting it.
    """
    skip = {"lang", "_partial_token", "admin_logged_in"}
    plain = {k: v for k, v in state.items() if k not in skip}
    return json.dumps(plain, default=str)


def create_partial_token(contact_email: str, contact_phone: str,
                         session_state, last_step: str,
                         ttl_days: int = PARTIAL_TOKEN_TTL_DAYS) -> str:
    """Create a partial_registrations row, return the token.

    contact_email is required (the resume link is emailed there).
    last_step is the relative URL the /resume route redirects to.
    """
    token   = secrets.token_urlsafe(24)
    payload = _serialize_session_state(session_state)
    expires = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat(
        sep=" ", timespec="seconds"
    )
    upin_db().execute(
        "INSERT INTO partial_registrations "
        "(token, contact_email, contact_phone, session_state, last_step, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (token, contact_email, contact_phone or "", payload, last_step, expires),
    )
    upin_db().commit()
    return token


def update_partial_state(token: str, session_state, last_step: str) -> bool:
    """Refresh the snapshot for an existing token. No-op if token unknown."""
    payload = _serialize_session_state(session_state)
    cur = upin_db().execute(
        "UPDATE partial_registrations "
        "SET session_state = ?, last_step = ? WHERE token = ?",
        (payload, last_step, token),
    )
    upin_db().commit()
    return cur.rowcount > 0


def restore_partial(token: str):
    """Fetch and decode a partial. Returns (state_dict, last_step) or None.

    Also opportunistically purges any expired rows so the table doesn't
    grow without bound -- callers don't need a separate cleanup job.
    """
    upin_db().execute(
        "DELETE FROM partial_registrations WHERE expires_at < ?",
        (datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds"),),
    )
    upin_db().commit()
    row = upin_db().execute(
        "SELECT session_state, last_step FROM partial_registrations WHERE token = ?",
        (token,),
    ).fetchone()
    if not row:
        return None
    try:
        state = json.loads(row["session_state"])
    except (ValueError, TypeError):
        return None
    return state, row["last_step"]


def delete_partial(token: str) -> None:
    """Remove a partial -- called when registration completes."""
    upin_db().execute(
        "DELETE FROM partial_registrations WHERE token = ?", (token,)
    )
    upin_db().commit()
