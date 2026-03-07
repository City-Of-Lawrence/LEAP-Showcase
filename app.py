"""
app.py  –  LEAP City of Lawrence Registration Portal
Flask prototype  |  April 2026

Entry paths:
  QR path   : GET /register?upin=<plaintext_upin>
                → address confirmation → role → intent → contact → done
  Generic   : GET /  → address lookup → role → intent → contact → done
  Admin     : GET /admin  (password protected)
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, g, abort
)
import sqlite3
import os
import functools

# Ensure Flask finds templates and databases relative to this file,
# not relative to whatever directory the user runs python from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
DB_UPIN     = os.environ.get("DB_UPIN",     os.path.join(BASE_DIR, "upinmgmt.sqlite"))
DB_MASTER   = os.environ.get("DB_MASTER",   os.path.join(BASE_DIR, "lawrence_master.sqlite"))
DB_OUTREACH = os.environ.get("DB_OUTREACH", os.path.join(BASE_DIR, "LEAPMailings_clean.sqlite"))

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "leapadmin2026")  # change before deploy

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

MASSSAVE_URL = "https://www.masssave.com/community-first/lawrence"

ROLES = [
    ("renter",           "Renter"),
    ("owner_occupant",   "Owner-Occupant"),
    ("landlord",         "Landlord"),
    ("property_manager", "Property Manager"),
    ("small_business",   "Small Business"),
]

INTENTS = [
    ("enroll",     "I want to enroll in Mass Save now"),
    ("event",      "I want to attend a City information event"),
    ("assistance", "I need help understanding the program"),
]

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = SECRET_KEY


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------

def get_db(path):
    """Return a cached sqlite3 connection for the current request."""
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


def upin_db():   return get_db(DB_UPIN)
def master_db(): return get_db(DB_MASTER)
def outreach_db(): return get_db(DB_OUTREACH)


def ensure_registrations_table():
    """Create registrations table in upinmgmt.sqlite if it doesn't exist."""
    conn = sqlite3.connect(DB_UPIN)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number   TEXT NOT NULL,
            upin_used        TEXT,          -- 'qr' or 'manual'
            normalized_address TEXT,
            service_unit     TEXT,
            role             TEXT,
            intent           TEXT,
            contact_name     TEXT,
            contact_phone    TEXT,
            contact_email    TEXT,
            registered_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address       TEXT
        )
    """)
    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# UPIN lookup (reads upinmgmt.sqlite)
# ------------------------------------------------------------------

def lookup_by_upin(upin_plain: str):
    """
    Validate a plaintext UPIN against all active rows.
    Returns the matching upin row (sqlite3.Row) or None.
    Uses argon2 verify — safe even with many rows because
    the outreach batch is small (hundreds, not millions).
    """
    from argon2 import PasswordHasher, exceptions
    ph = PasswordHasher()

    cur = upin_db().execute(
        "SELECT * FROM upin WHERE status = 'active'"
    )
    for row in cur:
        try:
            ph.verify(row["upin_hash"], upin_plain)
            return row          # match found
        except exceptions.VerifyMismatchError:
            continue
        except Exception:
            continue
    return None


def lookup_property(account_number: str):
    """Fetch parcel details from lawrence_master.sqlite."""
    return master_db().execute(
        """
        SELECT account_number,
               normalized_address,
               heating_fuel_description,
               primary_land_use_code_description,
               total_occupancy,
               vision_id,
               lean_eligibility,
               owner_1_name
        FROM   Assessment_L_Parcels
        WHERE  account_number = ?
        LIMIT  1
        """,
        (account_number,)
    ).fetchone()


# ------------------------------------------------------------------
# Address lookup (reads LEAPMailings_clean.sqlite)
# ------------------------------------------------------------------

def search_address(street: str):
    """
    Fuzzy-ish address search: returns up to 10 matching rows
    from Outreach_Master_Unified for the typed street string.
    """
    pattern = f"%{street.strip().upper()}%"
    return outreach_db().execute(
        """
        SELECT DISTINCT
               Account_Number,
               Service_Address,
               Service_Unit,
               Vision_ID,
               Resident_Status,
               Owner_Name
        FROM   Outreach_Master_Unified
        WHERE  UPPER(Service_Address) LIKE ?
        ORDER  BY Service_Address, Service_Unit
        LIMIT  10
        """,
        (pattern,)
    ).fetchall()


# ------------------------------------------------------------------
# Registration save
# ------------------------------------------------------------------

def save_registration(data: dict):
    upin_db().execute(
        """
        INSERT INTO registrations
            (account_number, upin_used, normalized_address,
             service_unit, role, intent,
             contact_name, contact_phone, contact_email, ip_address)
        VALUES
            (:account_number, :upin_used, :normalized_address,
             :service_unit, :role, :intent,
             :contact_name, :contact_phone, :contact_email, :ip_address)
        """,
        data
    )
    upin_db().commit()


# ------------------------------------------------------------------
# Admin auth decorator
# ------------------------------------------------------------------

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
    """Landing page — generic (cold) path."""
    return render_template("index.html")


@app.route("/register")
def register_qr():
    """
    QR path entry point.
    Expects ?upin=<plaintext_upin>
    Validates UPIN, then redirects into the shared flow.
    """
    upin_plain = request.args.get("upin", "").strip().upper()
    if not upin_plain:
        return render_template("error.html",
            message="No UPIN found in this link. Please use the QR code from your letter, "
                    "or <a href='/'>enter your address here</a>."), 400

    row = lookup_by_upin(upin_plain)
    if not row:
        return render_template("error.html",
            message="This UPIN is not valid or has already been used. "
                    "Please contact City Hall for assistance."), 404

    account_number = row["account_number"]
    prop = lookup_property(account_number)

    # Store in session so downstream steps don't re-query
    session["account_number"]     = account_number
    session["normalized_address"] = row["normalized_address"] or (prop["normalized_address"] if prop else "")
    session["entry_path"]         = "qr"
    session["upin_used"]          = "qr"
    session.pop("service_unit", None)

    return render_template(
        "confirm_address.html",
        address=session["normalized_address"],
        account_number=account_number,
        prop=prop,
    )


@app.route("/address-search", methods=["GET", "POST"])
def address_search():
    """Generic path — step 1: search for address."""
    results = []
    query = ""
    if request.method == "POST":
        query = request.form.get("street", "").strip()
        if query:
            results = search_address(query)
    return render_template("address_search.html", results=results, query=query)


@app.route("/select-address")
def select_address():
    """
    User clicked a specific address from search results.
    Stores selection in session, shows confirmation.
    """
    account_number = request.args.get("acct", "").strip()
    service_unit   = request.args.get("unit", "").strip()

    if not account_number:
        return redirect(url_for("address_search"))

    prop = lookup_property(account_number)

    # Fall back to outreach address if master DB has no record
    outreach_row = outreach_db().execute(
        "SELECT Service_Address, Service_Unit FROM Outreach_Master_Unified "
        "WHERE Account_Number = ? LIMIT 1",
        (account_number,)
    ).fetchone()

    address = (prop["normalized_address"] if prop
               else (outreach_row["Service_Address"] if outreach_row else account_number))

    session["account_number"]     = account_number
    session["normalized_address"] = address
    session["service_unit"]       = service_unit
    session["entry_path"]         = "generic"
    session["upin_used"]          = "manual"

    return render_template(
        "confirm_address.html",
        address=address,
        service_unit=service_unit,
        account_number=account_number,
        prop=prop,
    )


@app.route("/confirm-address", methods=["POST"])
def confirm_address():
    """Address confirmed — proceed to role selection."""
    if not session.get("account_number"):
        return redirect(url_for("index"))
    # If user said 'not my address', send back to search
    if request.form.get("confirmed") != "yes":
        session.clear()
        return redirect(url_for("address_search"))
    return redirect(url_for("select_role"))


@app.route("/role", methods=["GET", "POST"])
def select_role():
    """Step 2 — role selection."""
    if not session.get("account_number"):
        return redirect(url_for("index"))

    if request.method == "POST":
        role = request.form.get("role", "").strip()
        if role not in dict(ROLES):
            return render_template("role.html", roles=ROLES, error="Please select a role.")
        session["role"] = role
        return redirect(url_for("select_intent"))

    return render_template("role.html", roles=ROLES)


@app.route("/intent", methods=["GET", "POST"])
def select_intent():
    """Step 3 — intent selection."""
    if not session.get("account_number"):
        return redirect(url_for("index"))

    if request.method == "POST":
        intent = request.form.get("intent", "").strip()
        if intent not in dict(INTENTS):
            return render_template("intent.html", intents=INTENTS, error="Please select an option.")
        session["intent"] = intent
        return redirect(url_for("contact_info"))

    return render_template("intent.html", intents=INTENTS)


@app.route("/contact", methods=["GET", "POST"])
def contact_info():
    """Step 4 — optional contact info, then save registration."""
    if not session.get("account_number"):
        return redirect(url_for("index"))

    if request.method == "POST":
        contact_name  = request.form.get("contact_name", "").strip()
        contact_phone = request.form.get("contact_phone", "").strip()
        contact_email = request.form.get("contact_email", "").strip()

        save_registration({
            "account_number":     session["account_number"],
            "upin_used":          session.get("upin_used", "manual"),
            "normalized_address": session.get("normalized_address", ""),
            "service_unit":       session.get("service_unit", ""),
            "role":               session.get("role", ""),
            "intent":             session.get("intent", ""),
            "contact_name":       contact_name,
            "contact_phone":      contact_phone,
            "contact_email":      contact_email,
            "ip_address":         request.remote_addr,
        })

        intent = session.get("intent")
        session.clear()

        if intent == "enroll":
            return redirect(MASSSAVE_URL)
        return redirect(url_for("done"))

    return render_template("contact.html",
                           address=session.get("normalized_address"),
                           role=dict(ROLES).get(session.get("role", ""), ""))


@app.route("/done")
def done():
    return render_template("done.html", masssave_url=MASSSAVE_URL)


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
        """
        SELECT id, registered_at, normalized_address, service_unit,
               role, intent, upin_used,
               contact_name, contact_phone, contact_email
        FROM   registrations
        ORDER  BY registered_at DESC
        LIMIT  200
        """
    ).fetchall()
    total = upin_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    return render_template("admin.html", rows=rows, total=total)


# ------------------------------------------------------------------
# Run
# ------------------------------------------------------------------

if __name__ == "__main__":
    ensure_registrations_table()
    app.run(debug=True, port=5000)
