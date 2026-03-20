"""
app.py  –  LEAP City of Lawrence Registration Portal
Flask prototype  |  March 2026
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, g, abort
)
import sqlite3
import os
import functools
from datetime import datetime, timezone
from translations import t, get_roles, get_intents, get_landlord_intents

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
DB_UPIN     = os.environ.get("DB_UPIN",     os.path.join(BASE_DIR, "upinmgmt.sqlite"))
DB_MASTER   = os.environ.get("DB_MASTER",   os.path.join(BASE_DIR, "lawrence_master.sqlite"))
DB_OUTREACH = os.environ.get("DB_OUTREACH", os.path.join(BASE_DIR, "LEAPMailings_clean.sqlite"))

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "leapadmin2026")
SECRET_KEY     = os.environ.get("SECRET_KEY",     "dev-secret-change-in-prod")
MASSSAVE_URL   = "https://www.masssave.com/community-first/lawrence"
UNIT_COUNT_CONFIRM_MULTIPLIER = 2

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = SECRET_KEY


def get_lang():
    """Return current language from session, default English."""
    return session.get("lang", "en")

@app.context_processor
def inject_globals():
    """Make t() and lang available in every template automatically."""
    lang = get_lang()
    return {
        "t":    lambda key: t(key, lang),
        "lang": lang,
        "now":  datetime.now(timezone.utc),
    }

@app.route("/lang/<lang>")
def set_language(lang):
    """Switch language and return to previous page."""
    if lang in ("en", "es"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------

def get_db(path):
    attr = f"_db_{os.path.basename(path)}"
    if not hasattr(g, attr):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        setattr(g, attr, conn)
    return getattr(g, attr)

@app.teardown_appcontext
def close_dbs(exc):
    for attr in list(vars(g)):
        if attr.startswith("_db_"):
            getattr(g, attr).close()

def upin_db():     return get_db(DB_UPIN)
def master_db():   return get_db(DB_MASTER)
def outreach_db(): return get_db(DB_OUTREACH)


# ------------------------------------------------------------------
# Schema
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
            pending_upin          TEXT
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


def ensure_schema():
    """
    Safe schema creation for gunicorn / Render startup.
    Uses CREATE TABLE IF NOT EXISTS — never drops existing data.
    Called once at app startup via @app.before_request guard.
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
            pending_upin          TEXT
        )
    """)
    # Migration guard — adds pending_upin to existing databases without a full reset
    try:
        cur.execute("ALTER TABLE registrations ADD COLUMN pending_upin TEXT")
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


# Run ensure_schema once at startup (works under both gunicorn and python app.py)
_schema_ready = False

@app.before_request
def startup_schema():
    global _schema_ready
    if not _schema_ready:
        ensure_schema()
        _schema_ready = True


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def get_setting(key, default=""):
    row = upin_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default

def lookup_by_upin(upin_plain):
    from argon2 import PasswordHasher, exceptions
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
        # Extract street names (everything after the first token = house number)
        for r in rows:
            parts = r["normalized_address"].split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].strip())
        # Fallback to outreach DB if nothing found
        if not streets:
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

    else:  # owner_occupant, property_manager, small_business — try both
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
        # Also check master DB
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
        # Fallback
        if not results:
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

def normalize_unit(unit: str) -> str:
    """Strip common prefix words so 'APT 323' and '323' compare equal."""
    import re
    return re.sub(r'^(APT|UNIT|STE|SUITE|#)\s*', '', unit.strip().upper())

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

def save_registration(data):
    # Normalize service_unit before storing so lookups always match
    if data.get("service_unit"):
        data["service_unit"] = normalize_unit(data["service_unit"])
    cur = upin_db().execute(
        """INSERT INTO registrations (
            account_number, upin_used, normalized_address, service_unit,
            role, intent, unit_count_reported, unit_count_known,
            unit_count_flag, mass_save_enrolled, needs_callback,
            event_rsvp_id, contact_name, contact_phone, contact_email,
            ip_address, pending_upin
        ) VALUES (
            :account_number, :upin_used, :normalized_address, :service_unit,
            :role, :intent, :unit_count_reported, :unit_count_known,
            :unit_count_flag, :mass_save_enrolled, :needs_callback,
            :event_rsvp_id, :contact_name, :contact_phone, :contact_email,
            :ip_address, :pending_upin
        )""",
        data
    )
    upin_db().commit()
    return cur.lastrowid

def admin_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ------------------------------------------------------------------
# PUBLIC ROUTES
# ------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register")
def register_qr():
    upin_plain = request.args.get("upin", "").strip().upper()
    if not upin_plain:
        return render_template("error.html",
            message=t("error_upin_missing", get_lang())), 400
    row = lookup_by_upin(upin_plain)
    if not row:
        return render_template("error.html",
            message=t("error_upin_invalid", get_lang())), 404

    # Unit UPINs belong to renters — hand off to renter login flow
    if row["upin_type"] == "unit":
        return _complete_renter_upin_login(upin_plain, row)

    # Property UPINs — landlord flow
    account_number = row["account_number"]
    prop = lookup_property(account_number)
    prior = get_prior_registration_summary(account_number)

    session["account_number"]     = account_number
    session["normalized_address"] = row["normalized_address"] or (
                                        prop["normalized_address"] if prop else "")
    session["entry_path"]         = "qr"
    session["upin_used"]          = "qr"
    session["upin_plain"]         = upin_plain
    session["upin_role"]          = "landlord"
    session["is_repeat_visit"]    = prior is not None
    session.pop("service_unit", None)

    # Returning visitor — skip full intake, go to welcome-back shortcut
    if prior:
        session["prior_role"]      = prior["role"] or ""
        session["prior_visit_date"] = prior["registered_at"][:10] if prior["registered_at"] else ""
        return redirect(url_for("welcome_back"))

    return render_template("confirm_address.html",
                           address=session["normalized_address"],
                           account_number=account_number, prop=prop)

def _complete_renter_upin_login(upin_plain, row):
    """Shared session setup and redirect for both QR scan and typed renter UPIN paths."""
    account_number  = row["account_number"]
    service_unit    = row["service_unit"] or ""
    normalized_addr = row["normalized_address"] or ""

    prior = get_prior_registration_summary(account_number, service_unit)

    session["account_number"]     = account_number
    session["service_unit"]       = service_unit
    session["normalized_address"] = normalized_addr
    session["role"]               = "renter"
    session["entry_path"]         = "upin"
    session["upin_used"]          = "upin"
    session["upin_plain"]         = upin_plain
    session["upin_role"]          = "renter"
    session["is_repeat_visit"]    = prior is not None

    if prior:
        session["prior_role"]       = prior["role"] or ""
        session["prior_visit_date"] = (
            prior["registered_at"][:10] if prior["registered_at"] else ""
        )
        return redirect(url_for("welcome_back"))

    return redirect(url_for("event_select"))


@app.route("/renter/login", methods=["GET", "POST"])
def renter_login():
    """
    Renter UPIN entry point.
    GET  with ?upin= — QR scan path: auto-validates and enters flow immediately.
    GET  without     — shows UPIN entry form for manual typing.
    POST             — validates UPIN typed into form.
    'No UPIN' link   — redirects to /renter/start (street path fallback).
    """
    error = None

    # QR scan path: UPIN arrives as GET query param — auto-validate, skip form
    upin_from_qr = request.args.get("upin", "").strip().upper()
    if request.method == "GET" and upin_from_qr:
        row = lookup_by_upin(upin_from_qr)
        if not row or row["upin_type"] != "unit":
            return render_template("renter_login.html",
                                   error=t("error_upin_invalid", get_lang()))
        return _complete_renter_upin_login(upin_from_qr, row)

    # Typed entry path: UPIN submitted via POST form
    if request.method == "POST":
        upin_plain = request.form.get("upin", "").strip().upper()
        lang = get_lang()
        if not upin_plain:
            error = t("error_upin_missing", lang)
        else:
            row = lookup_by_upin(upin_plain)
            if not row or row["upin_type"] != "unit":
                error = t("error_upin_invalid", lang)
            else:
                return _complete_renter_upin_login(upin_plain, row)

    return render_template("renter_login.html", error=error)


@app.route("/welcome-back", methods=["GET", "POST"])
def welcome_back():
    """Returning visitor via QR — confirm role then go to short action menu."""
    if not session.get("account_number"):
        return redirect(url_for("index"))

    upin_role  = session.get("upin_role", "")
    upin_plain = session.get("upin_plain", "")

    existing_rsvps = get_existing_rsvps(upin_plain,
                                        account_number=session.get("account_number", ""),
                                        service_unit=session.get("service_unit", ""))
    active_rsvps = []
    if existing_rsvps:
        rows = upin_db().execute(
            """SELECT r.id, r.event_id, e.name, e.event_date, e.event_time, e.location
               FROM event_rsvps r JOIN events e ON r.event_id = e.event_id
               WHERE r.id IN ({})
                 AND e.status = 'active' AND e.event_date >= date('now')
               ORDER BY e.event_date, e.event_time""".format(
                ",".join("?" * len(existing_rsvps))
            ),
            list(existing_rsvps.values())
        ).fetchall()
        active_rsvps = [dict(r) for r in rows]

    if request.method == "POST":
        role = upin_role if upin_role else request.form.get("role", "").strip()
        lang = get_lang()
        if not upin_role and role not in dict(get_roles(lang)):
            return render_template("welcome_back.html",
                                   roles=get_roles(lang),
                                   upin_role=upin_role,
                                   address=session.get("normalized_address"),
                                   prior_role=session.get("prior_role", ""),
                                   prior_visit_date=session.get("prior_visit_date", ""),
                                   active_rsvps=active_rsvps,
                                   error=t("error_select_role", lang))
        session["role"] = role
        if role == "landlord":
            return redirect(url_for("landlord_events"))
        return redirect(url_for("event_select"))

    return render_template("welcome_back.html",
                           roles=get_roles(get_lang()),
                           upin_role=upin_role,
                           address=session.get("normalized_address"),
                           prior_role=session.get("prior_role", ""),
                           prior_visit_date=session.get("prior_visit_date", ""),
                           active_rsvps=active_rsvps)


@app.route("/renter/start")
def renter_start():
    """
    Street-path entry for renters who have no UPIN.
    Linked from /renter/login 'no UPIN' fallback.
    Pre-sets role=renter and skips the role selection screen.
    """
    session["role"]            = "renter"
    session["entry_path"]      = "generic"
    session["upin_used"]       = "manual"
    session["is_repeat_visit"] = False
    return redirect(url_for("address_street"))


@app.route("/start", methods=["GET", "POST"])
def start_generic():
    """Generic path step 1 — role selection before address search."""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        lang = get_lang()
        if role not in dict(get_roles(lang)):
            return render_template("start_generic.html", roles=get_roles(lang),
                                   error=t("error_select_role", lang))
        session["role"]            = role
        session["entry_path"]      = "generic"
        session["upin_used"]       = "manual"
        session["is_repeat_visit"] = False
        return redirect(url_for("address_street"))
    return render_template("start_generic.html", roles=get_roles(get_lang()))


@app.route("/address/street", methods=["GET", "POST"])
def address_street():
    """Generic path step 2 — enter street name only."""
    if not session.get("role"):
        return redirect(url_for("start_generic"))
    error = None
    if request.method == "POST":
        street_input = request.form.get("street_name", "").strip()
        if any(c.isdigit() for c in street_input):
            error = t("error_street_name_only", get_lang())
        elif not street_input:
            error = t("error_street_required", get_lang())
        else:
            role    = session.get("role", "renter")
            streets = search_streets_by_role(street_input, role)
            if not streets:
                lang = get_lang()
                role = session.get("role", "renter")
                # Landlords and property managers → EA path (assessment DB mismatch)
                # All others → manual address confirmation → zombie path
                if role in ("landlord", "property_manager"):
                    return render_template("address_street.html",
                        role=dict(get_roles(lang)).get(role, ""),
                        error=t("error_street_not_found", lang)
                              + " <a href='/address/not-found'>"
                              + t("error_street_not_found_link", lang) + "</a>.")
                # Renter / owner_occupant / small_business → confirm screen
                session["street_not_found_input"] = street_input
                return redirect(url_for("address_not_found_confirm"))
            if len(streets) == 1:
                session["street_name"] = streets[0]
                return redirect(url_for("address_pick"))
            return render_template("address_street.html",
                                   role=dict(get_roles(get_lang())).get(role, ""),
                                   streets=streets, query=street_input)
    return render_template("address_street.html",
                           role=dict(get_roles(get_lang())).get(session.get("role", ""), ""),
                           error=error)


@app.route("/address/confirm-street", methods=["POST"])
def address_confirm_street():
    """User picked from multiple matching street names."""
    if not session.get("role"):
        return redirect(url_for("start_generic"))
    street = request.form.get("street_name", "").strip()
    if not street:
        return redirect(url_for("address_street"))
    session["street_name"] = street
    return redirect(url_for("address_pick"))


@app.route("/address/pick", methods=["GET", "POST"])
def address_pick():
    """Generic path step 3 — pick specific address from dropdown."""
    if not session.get("role") or not session.get("street_name"):
        return redirect(url_for("address_street"))
    role        = session["role"]
    street_name = session["street_name"]
    addresses   = search_addresses_on_street(street_name, role)

    if request.method == "POST":
        account_number  = request.form.get("account_number", "").strip()
        service_unit    = request.form.get("service_unit", "").strip()
        display_address = request.form.get("display_address", "").strip()

        # Manual free-text entry (non-landlord path)
        if account_number == "MANUAL":
            manual_address = request.form.get("manual_address", "").strip()
            manual_unit    = request.form.get("manual_unit", "").strip()
            if not manual_address:
                return render_template("address_pick.html", addresses=addresses,
                                       street_name=street_name,
                                       role=dict(get_roles(get_lang())).get(role, ""),
                                       error=t("error_enter_address", get_lang()))
            display_address = manual_address
            if manual_unit:
                display_address += f" Unit {manual_unit}"
                service_unit = manual_unit
            session["account_number"]     = "MANUAL"
            session["normalized_address"] = display_address
            session["service_unit"]       = service_unit
            session["is_repeat_visit"]    = False
            # MANUAL renters have no UPIN — save registration immediately and
            # send to zombie holding so they don't fill out screens they can't complete
            if session.get("role") == "renter":
                save_registration({
                    "account_number":      "MANUAL",
                    "upin_used":           "manual",
                    "normalized_address":  display_address,
                    "service_unit":        normalize_unit(service_unit) if service_unit else "",
                    "role":                "renter",
                    "intent":              "pending",
                    "unit_count_reported": None,
                    "unit_count_known":    None,
                    "unit_count_flag":     None,
                    "mass_save_enrolled":  None,
                    "needs_callback":      None,
                    "event_rsvp_id":       None,
                    "contact_name":        "",
                    "contact_phone":       "",
                    "contact_email":       "",
                    "ip_address":          request.remote_addr,
                    "pending_upin":        "yes",
                })
                lang = session.get("lang", "en")
                session.clear()
                session["lang"] = lang
                return redirect(url_for("zombie_holding"))
            return redirect(url_for("select_intent"))

        if not account_number:
            return render_template("address_pick.html", addresses=addresses,
                                   street_name=street_name,
                                   role=dict(get_roles(get_lang())).get(role, ""),
                                   error=t("error_select_address", get_lang()))
        prop = lookup_property(account_number)
        session["account_number"]     = account_number
        session["normalized_address"] = display_address or (
                                            prop["normalized_address"] if prop else account_number)
        session["service_unit"]       = service_unit
        session["is_repeat_visit"]    = has_prior_registration(account_number, service_unit)

        if session["is_repeat_visit"]:
            prior = get_prior_registration_summary(account_number, service_unit)
            if prior:
                session["prior_role"]       = prior["role"] or ""
                session["prior_visit_date"] = prior["registered_at"][:10] if prior["registered_at"] else ""
            return redirect(url_for("welcome_back"))

        # Landlord gets unit count step; others go to intent
        if role == "landlord":
            return redirect(url_for("landlord_units"))
        return redirect(url_for("select_intent"))

    return render_template("address_pick.html", addresses=addresses,
                           street_name=street_name,
                           role=dict(get_roles(get_lang())).get(role, ""),
                           error=None)


@app.route("/address/not-found")
def address_not_found():
    return render_template("address_not_found.html")


@app.route("/address/not-found-confirm", methods=["GET", "POST"])
def address_not_found_confirm():
    """
    Confirmation screen for renters/owner-occupants/small businesses whose
    street was not found. They enter their full address; on confirm we save
    a zombie registration and redirect to the holding screen.
    """
    if not session.get("role"):
        return redirect(url_for("start_generic"))

    if request.method == "POST":
        manual_address = request.form.get("manual_address", "").strip()
        manual_unit    = request.form.get("manual_unit", "").strip()
        if not manual_address:
            return render_template("address_not_found_confirm.html",
                                   prefill_address="",
                                   error=t("error_enter_address", get_lang()))
        display_address = manual_address
        if manual_unit:
            display_address += f" Unit {manual_unit}"

        save_registration({
            "account_number":      "NOT_FOUND",
            "upin_used":           "manual",
            "normalized_address":  display_address,
            "service_unit":        normalize_unit(manual_unit) if manual_unit else "",
            "role":                session.get("role", "renter"),
            "intent":              "pending",
            "unit_count_reported": None,
            "unit_count_known":    None,
            "unit_count_flag":     None,
            "mass_save_enrolled":  None,
            "needs_callback":      None,
            "event_rsvp_id":       None,
            "contact_name":        "",
            "contact_phone":       "",
            "contact_email":       "",
            "ip_address":          request.remote_addr,
            "pending_upin":        "yes",
        })
        lang = session.get("lang", "en")
        session.clear()
        session["lang"] = lang
        return redirect(url_for("zombie_holding"))

    # GET — prefill with what they typed on the street screen
    prefill = session.get("street_not_found_input", "")
    return render_template("address_not_found_confirm.html",
                           prefill_address=prefill)


@app.route("/address-search", methods=["GET", "POST"])
def address_search():
    """Legacy route — redirect to new flow."""
    return redirect(url_for("start_generic"))

@app.route("/select-address")
def select_address():
    account_number = request.args.get("acct", "").strip()
    service_unit   = request.args.get("unit", "").strip()
    if not account_number:
        return redirect(url_for("address_search"))
    prop = lookup_property(account_number)
    outreach_row = outreach_db().execute(
        "SELECT Service_Address FROM Outreach_Master_Unified WHERE Account_Number=? LIMIT 1",
        (account_number,)
    ).fetchone()
    address = (prop["normalized_address"] if prop
               else (outreach_row["Service_Address"] if outreach_row else account_number))
    session.update({
        "account_number": account_number,
        "normalized_address": address,
        "service_unit": service_unit,
        "entry_path": "generic",
        "upin_used": "manual",
        "is_repeat_visit": False,
    })
    return render_template("confirm_address.html",
                           address=address, service_unit=service_unit,
                           account_number=account_number, prop=prop)

@app.route("/confirm-address", methods=["POST"])
def confirm_address():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.form.get("confirmed") != "yes":
        lang = session.get("lang", "en")
        session.clear()
        session["lang"] = lang
        return redirect(url_for("address_search"))
    # If role already locked by UPIN, skip role selection entirely
    if session.get("upin_role"):
        session["role"] = session["upin_role"]
        return redirect(url_for("landlord_units"))
    return redirect(url_for("select_role"))

@app.route("/role", methods=["GET", "POST"])
def select_role():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        lang = get_lang()
        if role not in dict(get_roles(lang)):
            return render_template("role.html", roles=get_roles(lang),
                                   error=t("error_select_role", lang))
        session["role"] = role
        if role == "landlord":
            return redirect(url_for("landlord_units"))
        return redirect(url_for("select_intent"))
    return render_template("role.html", roles=get_roles(get_lang()))


# ------------------------------------------------------------------
# LANDLORD FLOW
# ------------------------------------------------------------------

@app.route("/landlord/units", methods=["GET", "POST"])
def landlord_units():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    prop = lookup_property(session["account_number"])
    known_units = int(prop["total_occupancy"]) if prop and prop["total_occupancy"] else 0

    if request.method == "POST":
        try:
            reported = int(request.form.get("unit_count", "0").strip())
        except ValueError:
            return render_template("landlord_units.html", known_units=known_units,
                                   error=t("error_valid_number", get_lang()))
        session["unit_count_reported"] = reported
        session["unit_count_known"]    = known_units
        if known_units > 0 and reported > known_units * UNIT_COUNT_CONFIRM_MULTIPLIER:
            session["unit_count_flag"] = "pending_confirm"
            return redirect(url_for("landlord_units_confirm"))
        elif known_units > 0 and reported != known_units:
            session["unit_count_flag"] = "soft_flag"
        else:
            session["unit_count_flag"] = "ok"
        next_step = "landlord_repeat" if session.get("is_repeat_visit") else "landlord_events"
        return redirect(url_for(next_step))

    return render_template("landlord_units.html", known_units=known_units)

@app.route("/landlord/units/confirm", methods=["GET", "POST"])
def landlord_units_confirm():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.method == "POST":
        if request.form.get("confirmed") == "yes":
            session["unit_count_flag"] = "confirmed_flag"
        else:
            session["unit_count_reported"] = session.get("unit_count_known", 0)
            session["unit_count_flag"]     = "ok"
        next_step = "landlord_repeat" if session.get("is_repeat_visit") else "landlord_events"
        return redirect(url_for(next_step))
    return render_template("landlord_units_confirm.html",
                           reported=session.get("unit_count_reported"),
                           known=session.get("unit_count_known"))

@app.route("/landlord/returning", methods=["GET", "POST"])
def landlord_repeat():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.method == "POST":
        session["mass_save_enrolled"] = request.form.get("enrolled", "no")
        session["needs_callback"]     = request.form.get("callback", "no")
        return redirect(url_for("landlord_events"))
    return render_template("landlord_repeat.html",
                           address=session.get("normalized_address"))

def get_existing_rsvps(upin_plain, account_number="", service_unit=""):
    """Return dict of {event_id: rsvp_row_id} for active (non-cancelled) RSVPs.

    Lookup priority:
      1. upin_plain  — UPIN/landlord path
      2. account_number + service_unit — street-path renter fallback
    """
    if upin_plain:
        rows = upin_db().execute(
            "SELECT id, event_id FROM event_rsvps WHERE upin=? AND cancelled_at IS NULL",
            (upin_plain,)
        ).fetchall()
        return {r["event_id"]: r["id"] for r in rows}
    if account_number:
        norm = normalize_unit(service_unit) if service_unit else ""
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

@app.route("/landlord/events", methods=["GET", "POST"])
def landlord_events():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    n = int(get_setting("events_to_show", "2"))
    events = get_upcoming_events(limit=n)
    account_number = session["account_number"]
    upin_plain = session.get("upin_plain", "")
    existing_rsvps = get_existing_rsvps(upin_plain,
                                        account_number=account_number,
                                        service_unit=session.get("service_unit", ""))
    already_enrolled = session.get("mass_save_enrolled") == "yes"

    events_display = [{
        "event_id":      e["event_id"],
        "name":          e["name"],
        "event_date":    e["event_date"],
        "event_time":    e["event_time"],
        "location":      e["location"],
        "capacity":      e["capacity"],
        "rsvp_count":    e["rsvp_count"],
        "spots_left":    e["capacity"] - e["rsvp_count"],
        "wards":         get_event_wards(e["event_id"]),
        "already_rsvpd": e["event_id"] in existing_rsvps,
        "rsvp_id":       existing_rsvps.get(e["event_id"]),
    } for e in events]

    if request.method == "POST":
        event_id_str = request.form.get("event_id", "").strip()
        if event_id_str:
            event_id_int = int(event_id_str)
            if event_id_int not in existing_rsvps:
                rsvp_id = add_event_rsvp(event_id_int, account_number, upin_plain,
                                         session.get("service_unit", ""))
                session["event_rsvp_id"] = rsvp_id
            else:
                session["event_rsvp_id"] = event_id_int
        else:
            # "Skip" chosen — cancel any existing RSVPs for upcoming events
            for event in events_display:
                if event["already_rsvpd"]:
                    cancel_event_rsvp(upin_plain, event["event_id"])
            session["no_events_notify"] = not bool(events_display)
        return redirect(url_for("landlord_intent"))

    return render_template("landlord_events.html",
                           events=events_display,
                           already_enrolled=already_enrolled,
                           is_repeat_visit=session.get("is_repeat_visit", False),
                           address=session.get("normalized_address"))


@app.route("/landlord/intent", methods=["GET", "POST"])
def landlord_intent():
    """Landlord-specific intent page — simplified choices."""
    if not session.get("account_number"):
        return redirect(url_for("index"))
    lang = get_lang()
    intents = get_landlord_intents(lang)
    if request.method == "POST":
        intent = request.form.get("intent", "").strip()
        if intent not in dict(intents):
            return render_template("intent.html", intents=intents,
                                   error=t("error_select_option", lang))
        session["intent"] = intent
        return redirect(url_for("contact_info"))
    return render_template("intent.html", intents=intents)

@app.route("/events/select", methods=["GET", "POST"])
def event_select():
    """Shared event selection for all non-landlord roles."""
    if not session.get("account_number"):
        return redirect(url_for("index"))

    # Zombie gate: street-path renter with no UPIN cannot RSVP
    if session.get("role") == "renter" and not session.get("upin_plain"):
        return redirect(url_for("zombie_holding"))

    n = int(get_setting("events_to_show", "2"))
    events = get_upcoming_events(limit=n)
    account_number = session["account_number"]
    existing_rsvps = get_existing_rsvps(session.get("upin_plain", ""),
                                        account_number=account_number,
                                        service_unit=session.get("service_unit", ""))
    events_display = [{
        "event_id":      e["event_id"],
        "name":          e["name"],
        "event_date":    e["event_date"],
        "event_time":    e["event_time"],
        "location":      e["location"],
        "capacity":      e["capacity"],
        "rsvp_count":    e["rsvp_count"],
        "spots_left":    e["capacity"] - e["rsvp_count"],
        "wards":         get_event_wards(e["event_id"]),
        "already_rsvpd": e["event_id"] in existing_rsvps,
        "rsvp_id":       existing_rsvps.get(e["event_id"]),
    } for e in events]

    if request.method == "POST":
        event_id_str = request.form.get("event_id", "").strip()
        if event_id_str:
            event_id_int = int(event_id_str)
            if event_id_int not in existing_rsvps:
                rsvp_id = add_event_rsvp(event_id_int,
                                         account_number,
                                         session.get("upin_plain", ""),
                                         session.get("service_unit", ""))
                session["event_rsvp_id"] = rsvp_id
            else:
                # Already RSVP'd — store the actual row id, not the event id
                session["event_rsvp_id"] = existing_rsvps[event_id_int]
        if not event_id_str:
            session["no_events_notify"] = True
        return redirect(url_for("contact_info"))

    return render_template("event_select.html",
                           events=events_display,
                           is_repeat_visit=session.get("is_repeat_visit", False),
                           role=dict(get_roles(get_lang())).get(session.get("role", ""), ""),
                           address=session.get("normalized_address"),
                           service_unit=session.get("service_unit", ""))


@app.route("/intent", methods=["GET", "POST"])
def select_intent():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.method == "POST":
        intent = request.form.get("intent", "").strip()
        lang = get_lang()
        if intent not in dict(get_intents(lang)):
            return render_template("intent.html", intents=get_intents(lang),
                                   error=t("error_select_option", lang))
        session["intent"] = intent
        if intent == "event":
            n = int(get_setting("events_to_show", "2"))
            session["no_events_notify"] = len(get_upcoming_events(limit=n)) == 0
            return redirect(url_for("event_select"))
        return redirect(url_for("contact_info"))
    return render_template("intent.html", intents=get_intents(get_lang()))

@app.route("/contact", methods=["GET", "POST"])
def contact_info():
    # Special case: address-not-found path — no session required
    if request.method == "POST" and request.form.get("_path") == "not_found":
        street_note = request.form.get("street_note", "").strip()
        save_registration({
            "account_number":      "NOT_FOUND",
            "upin_used":           "manual",
            "normalized_address":  street_note,
            "service_unit":        "",
            "role":                "unknown",
            "intent":              "assistance",
            "unit_count_reported": None,
            "unit_count_known":    None,
            "unit_count_flag":     None,
            "mass_save_enrolled":  None,
            "needs_callback":      "yes",
            "event_rsvp_id":       None,
            "contact_name":        request.form.get("contact_name", "").strip(),
            "contact_phone":       request.form.get("contact_phone", "").strip(),
            "contact_email":       request.form.get("contact_email", "").strip(),
            "ip_address":          request.remote_addr,
        })
        return redirect(url_for("done"))

    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.method == "POST":
        # Zombie detection: street-path renter with no UPIN
        is_zombie = (
            session.get("role") == "renter"
            and not session.get("upin_plain")
        )
        save_registration({
            "account_number":      session["account_number"],
            "upin_used":           session.get("upin_used", "manual"),
            "normalized_address":  session.get("normalized_address", ""),
            "service_unit":        session.get("service_unit", ""),
            "role":                session.get("role", ""),
            "intent":              session.get("intent", ""),
            "unit_count_reported": session.get("unit_count_reported"),
            "unit_count_known":    session.get("unit_count_known"),
            "unit_count_flag":     session.get("unit_count_flag"),
            "mass_save_enrolled":  session.get("mass_save_enrolled"),
            "needs_callback":      session.get("needs_callback"),
            "event_rsvp_id":       session.get("event_rsvp_id"),
            "contact_name":        request.form.get("contact_name", "").strip(),
            "contact_phone":       request.form.get("contact_phone", "").strip(),
            "contact_email":       request.form.get("contact_email", "").strip(),
            "ip_address":          request.remote_addr,
            "pending_upin":        "yes" if is_zombie else None,
        })
        lang = session.get("lang", "en")
        intent = session.get("intent")
        session.clear()
        session["lang"] = lang
        if is_zombie:
            return redirect(url_for("zombie_holding"))
        if intent == "enroll":
            return redirect(MASSSAVE_URL)
        return redirect(url_for("done"))

    # Pre-fill contact fields from most recent registration if returning visitor
    prior_contact = {}
    if session.get("is_repeat_visit"):
        prior = upin_db().execute(
            """SELECT contact_name, contact_phone, contact_email
               FROM registrations
               WHERE account_number = ?
                 AND (contact_name != '' OR contact_phone != '' OR contact_email != '')
               ORDER BY registered_at DESC LIMIT 1""",
            (session["account_number"],)
        ).fetchone()
        if prior:
            prior_contact = {
                "name":  prior["contact_name"]  or "",
                "phone": prior["contact_phone"] or "",
                "email": prior["contact_email"] or "",
            }

    return render_template("contact.html",
                           address=session.get("normalized_address"),
                           service_unit=session.get("service_unit", ""),
                           role=dict(get_roles(get_lang())).get(session.get("role", ""), ""),
                           intent=session.get("intent", ""),
                           event_rsvp_id=session.get("event_rsvp_id"),
                           no_events_notify=session.get("no_events_notify", False),
                           prior_contact=prior_contact)

@app.route("/done")
def done():
    upin_plain  = session.get("upin_plain", "")
    is_zombie   = request.args.get("zombie") == "1"
    active_rsvps = []
    if upin_plain:
        rows = upin_db().execute(
            """SELECT r.id, r.event_id, e.name, e.event_date, e.event_time, e.location
               FROM event_rsvps r JOIN events e ON r.event_id = e.event_id
               WHERE r.upin = ? AND r.cancelled_at IS NULL
                 AND e.status = 'active' AND e.event_date >= date('now')
               ORDER BY e.event_date, e.event_time""",
            (upin_plain,)
        ).fetchall()
        active_rsvps = [dict(r) for r in rows]
    return render_template("done.html", masssave_url=MASSSAVE_URL,
                           active_rsvps=active_rsvps,
                           is_zombie=is_zombie)


@app.route("/renter/pending")
def zombie_holding():
    """
    Holding screen for street-path renters who have no UPIN yet (Zombies).
    Shown after contact_info is saved. Session is already cleared at this point —
    the page is purely informational, no session data required.
    """
    return render_template("zombie_holding.html")


@app.route("/rsvp/<int:rsvp_id>/cancel", methods=["POST"])
def rsvp_cancel(rsvp_id):
    """Self-service RSVP cancellation. Returns to 'next' param or done page."""
    upin_plain     = session.get("upin_plain", "")
    account_number = session.get("account_number", "")

    if upin_plain:
        upin_db().execute(
            """UPDATE event_rsvps SET cancelled_at = CURRENT_TIMESTAMP
               WHERE id = ? AND upin = ? AND cancelled_at IS NULL""",
            (rsvp_id, upin_plain)
        )
    elif account_number:
        upin_db().execute(
            """UPDATE event_rsvps SET cancelled_at = CURRENT_TIMESTAMP
               WHERE id = ? AND account_number = ? AND cancelled_at IS NULL""",
            (rsvp_id, account_number)
        )
    else:
        # Session was cleared (street-path renter on done page) —
        # cancel by id alone. The id was rendered to this user moments
        # ago so it is sufficiently scoped; no auth token available.
        upin_db().execute(
            """UPDATE event_rsvps SET cancelled_at = CURRENT_TIMESTAMP
               WHERE id = ? AND cancelled_at IS NULL""",
            (rsvp_id,)
        )

    upin_db().commit()
    next_page = request.form.get("next", "done")
    safe_destinations = {"done", "welcome_back", "landlord_events", "event_select"}
    if next_page not in safe_destinations:
        next_page = "done"
    return redirect(url_for(next_page))


# ------------------------------------------------------------------
# ADMIN ROUTES
# ------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Incorrect password."
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    rows = upin_db().execute(
        """SELECT id, registered_at, normalized_address, service_unit,
                  role, intent, upin_used, unit_count_flag,
                  mass_save_enrolled, needs_callback, pending_upin,
                  contact_name, contact_phone, contact_email
           FROM registrations ORDER BY registered_at DESC LIMIT 200"""
    ).fetchall()
    total     = upin_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    flags     = upin_db().execute(
        "SELECT COUNT(*) FROM registrations WHERE unit_count_flag IN ('soft_flag','confirmed_flag')"
    ).fetchone()[0]
    callbacks = upin_db().execute(
        "SELECT COUNT(*) FROM registrations WHERE needs_callback='yes'"
    ).fetchone()[0]
    return render_template("admin.html", rows=rows, total=total,
                           flags=flags, callbacks=callbacks,
                           events_to_show=get_setting("events_to_show", "2"))

@app.route("/admin/events")
@admin_required
def admin_events():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = upin_db().execute(
        """SELECT e.*,
                  (SELECT COUNT(*) FROM event_rsvps r
                   WHERE r.event_id=e.event_id AND r.cancelled_at IS NULL) AS rsvp_count
           FROM events e ORDER BY e.event_date, e.event_time"""
    ).fetchall()
    events_display = [dict(e) | {"wards": get_event_wards(e["event_id"]),
                                  "is_past": e["event_date"] < today}
                      for e in events]
    import_result = session.pop("import_result", None)
    return render_template("admin_events.html", events=events_display,
                           import_result=import_result)

@app.route("/admin/events/new", methods=["GET", "POST"])
@admin_required
def admin_event_new():
    if request.method == "POST":
        cur = upin_db().execute(
            "INSERT INTO events (name,event_date,event_time,location,capacity) VALUES (?,?,?,?,?)",
            (request.form["name"], request.form["event_date"],
             request.form["event_time"], request.form["location"],
             int(request.form.get("capacity", 50) or 50))
        )
        for ward in request.form.getlist("wards"):
            upin_db().execute(
                "INSERT INTO event_wards (event_id,ward) VALUES (?,?)",
                (cur.lastrowid, ward.strip())
            )
        upin_db().commit()
        return redirect(url_for("admin_events"))
    return render_template("admin_event_form.html", event=None, wards=[])

@app.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_event_edit(event_id):
    event = upin_db().execute(
        "SELECT * FROM events WHERE event_id=?", (event_id,)
    ).fetchone()
    if not event:
        abort(404)
    existing_wards = get_event_wards(event_id)
    if request.method == "POST":
        upin_db().execute(
            "UPDATE events SET name=?,event_date=?,event_time=?,location=?,capacity=? WHERE event_id=?",
            (request.form["name"], request.form["event_date"],
             request.form["event_time"], request.form["location"],
             int(request.form.get("capacity", 50) or 50), event_id)
        )
        upin_db().execute("DELETE FROM event_wards WHERE event_id=?", (event_id,))
        for ward in request.form.getlist("wards"):
            upin_db().execute(
                "INSERT INTO event_wards (event_id,ward) VALUES (?,?)",
                (event_id, ward.strip())
            )
        upin_db().commit()
        return redirect(url_for("admin_events"))
    return render_template("admin_event_form.html", event=event, wards=existing_wards)

@app.route("/admin/events/<int:event_id>/cancel", methods=["POST"])
@admin_required
def admin_event_cancel(event_id):
    upin_db().execute("UPDATE events SET status='cancelled' WHERE event_id=?", (event_id,))
    upin_db().commit()
    return redirect(url_for("admin_events"))


@app.route("/admin/events/<int:event_id>/attendees")
@admin_required
def admin_event_attendees(event_id):
    """Show all RSVPs for a specific event with contact details."""
    event = upin_db().execute(
        "SELECT * FROM events WHERE event_id=?", (event_id,)
    ).fetchone()
    if not event:
        abort(404)

    # Join RSVPs to registrations — LEFT JOIN so RSVPs without a registration row still appear
    rows = upin_db().execute(
        """SELECT rv.id          AS rsvp_id,
                  rv.account_number,
                  rv.upin,
                  rv.service_unit,
                  rv.rsvp_at,
                  rv.cancelled_at,
                  r.contact_name,
                  r.contact_phone,
                  r.contact_email,
                  r.normalized_address
           FROM event_rsvps rv
           LEFT JOIN registrations r ON r.account_number = rv.account_number
           WHERE rv.event_id = ?
           ORDER BY rv.cancelled_at NULLS FIRST, rv.rsvp_at""",
        (event_id,)
    ).fetchall()

    attendees = [dict(r) for r in rows]

    # Flag accounts with 2+ cancellations across ALL events — Energy Advocate signal
    # Only check accounts that appear in this event's list
    account_numbers = list({a["account_number"] for a in attendees
                            if a["account_number"] and a["cancelled_at"]})
    ea_flags = set()
    for acct in account_numbers:
        count = upin_db().execute(
            """SELECT COUNT(*) FROM event_rsvps
               WHERE account_number=? AND cancelled_at IS NOT NULL""",
            (acct,)
        ).fetchone()[0]
        if count >= 2:
            ea_flags.add(acct)

    active_count    = sum(1 for a in attendees if not a["cancelled_at"])
    cancelled_count = sum(1 for a in attendees if a["cancelled_at"])
    wards           = get_event_wards(event_id)

    return render_template("admin_event_attendees.html",
                           event=dict(event),
                           wards=wards,
                           attendees=attendees,
                           active_count=active_count,
                           cancelled_count=cancelled_count,
                           ea_flags=ea_flags)


@app.route("/admin/events/export")
@admin_required
def admin_events_export():
    """Export all events to Excel workbook for backup."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from flask import send_file

    events = upin_db().execute(
        "SELECT * FROM events ORDER BY event_date, event_time"
    ).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Events"

    # Header row
    headers = ["event_id", "name", "event_date", "event_time",
               "location", "capacity", "status", "wards"]
    header_fill = PatternFill("solid", start_color="1A3A5C")
    header_font = Font(bold=True, color="FFFFFF", name="Arial")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # Column widths
    widths = [10, 35, 12, 10, 35, 10, 10, 20]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = w

    # Data rows
    for row_num, e in enumerate(events, 2):
        wards = ", ".join(get_event_wards(e["event_id"]))
        ws.cell(row=row_num, column=1, value=e["event_id"])
        ws.cell(row=row_num, column=2, value=e["name"])
        ws.cell(row=row_num, column=3, value=e["event_date"])
        ws.cell(row=row_num, column=4, value=e["event_time"])
        ws.cell(row=row_num, column=5, value=e["location"])
        ws.cell(row=row_num, column=6, value=e["capacity"])
        ws.cell(row=row_num, column=7, value=e["status"])
        ws.cell(row=row_num, column=8, value=wards)
        # Alternate row shading
        if row_num % 2 == 0:
            fill = PatternFill("solid", start_color="EEF2F7")
            for col in range(1, 9):
                ws.cell(row=row_num, column=col).fill = fill

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"LEAP_events_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/admin/events/import", methods=["POST"])
@admin_required
def admin_events_import():
    """Import events from uploaded Excel file. Skips events already present."""
    import io
    from openpyxl import load_workbook

    f = request.files.get("events_file")
    if not f or not f.filename.endswith(".xlsx"):
        return redirect(url_for("admin_events"))

    wb = load_workbook(io.BytesIO(f.read()), data_only=True)
    ws = wb.active

    # Build set of existing events for duplicate detection
    # Match key: (name, event_date, event_time, location) — all lowercase stripped
    existing = upin_db().execute(
        "SELECT name, event_date, event_time, location FROM events"
    ).fetchall()
    existing_keys = {
        (r["name"].strip().lower(), r["event_date"].strip(),
         r["event_time"].strip(), r["location"].strip().lower())
        for r in existing
    }

    imported = 0
    skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        # Columns: event_id, name, event_date, event_time, location, capacity, status, wards
        if not row[1]:   # name required
            continue
        name     = str(row[1]).strip()
        edate    = str(row[2]).strip() if row[2] else ""
        etime    = str(row[3]).strip() if row[3] else ""
        location = str(row[4]).strip() if row[4] else ""
        capacity = int(row[5]) if row[5] else 50
        status   = str(row[6]).strip() if row[6] in ("active", "cancelled") else "active"
        wards_str = str(row[7]).strip() if row[7] else ""

        key = (name.lower(), edate, etime, location.lower())
        if key in existing_keys:
            skipped += 1
            continue

        cur = upin_db().execute(
            "INSERT INTO events (name, event_date, event_time, location, capacity, status) "
            "VALUES (?,?,?,?,?,?)",
            (name, edate, etime, location, capacity, status)
        )
        new_id = cur.lastrowid
        for ward in [w.strip() for w in wards_str.split(",") if w.strip()]:
            upin_db().execute(
                "INSERT INTO event_wards (event_id, ward) VALUES (?,?)", (new_id, ward)
            )
        existing_keys.add(key)
        imported += 1

    upin_db().commit()
    # Pass counts back via session flash
    session["import_result"] = f"Imported {imported} event(s), skipped {skipped} duplicate(s)."
    return redirect(url_for("admin_events"))

@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        try:
            n = max(1, int(request.form.get("events_to_show", "2")))
        except ValueError:
            n = 2
        upin_db().execute(
            "INSERT OR REPLACE INTO settings (key,value) VALUES ('events_to_show',?)", (str(n),)
        )
        upin_db().commit()
        return redirect(url_for("admin_settings"))
    return render_template("admin_settings.html",
                           events_to_show=get_setting("events_to_show", "2"))

# ------------------------------------------------------------------
if __name__ == "__main__":
    init_schema()
    app.run(debug=True, port=5000)
