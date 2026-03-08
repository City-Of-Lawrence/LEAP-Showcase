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

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = SECRET_KEY


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
            ip_address            TEXT
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
            rsvp_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def search_address(street):
    pattern = f"%{street.strip().upper()}%"
    return outreach_db().execute(
        """SELECT DISTINCT Account_Number, Service_Address, Service_Unit,
                  Vision_ID, Resident_Status, Owner_Name
           FROM Outreach_Master_Unified
           WHERE UPPER(Service_Address) LIKE ?
           ORDER BY Service_Address, Service_Unit LIMIT 10""",
        (pattern,)
    ).fetchall()

def has_prior_registration(account_number):
    row = upin_db().execute(
        "SELECT COUNT(*) FROM registrations WHERE account_number=?",
        (account_number,)
    ).fetchone()
    return row[0] > 0

def get_upcoming_events(limit=2):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = upin_db().execute(
        """SELECT e.*,
                  (SELECT COUNT(*) FROM event_rsvps r WHERE r.event_id=e.event_id) AS rsvp_count
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

def add_event_rsvp(event_id, account_number, upin=""):
    cur = upin_db().execute(
        "INSERT INTO event_rsvps (event_id, account_number, upin) VALUES (?,?,?)",
        (event_id, account_number, upin)
    )
    upin_db().commit()
    return cur.lastrowid

def save_registration(data):
    cur = upin_db().execute(
        """INSERT INTO registrations (
            account_number, upin_used, normalized_address, service_unit,
            role, intent, unit_count_reported, unit_count_known,
            unit_count_flag, mass_save_enrolled, needs_callback,
            event_rsvp_id, contact_name, contact_phone, contact_email, ip_address
        ) VALUES (
            :account_number, :upin_used, :normalized_address, :service_unit,
            :role, :intent, :unit_count_reported, :unit_count_known,
            :unit_count_flag, :mass_save_enrolled, :needs_callback,
            :event_rsvp_id, :contact_name, :contact_phone, :contact_email, :ip_address
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
            message="No UPIN found. Use your QR code or "
                    "<a href='/'>enter your address here</a>."), 400
    row = lookup_by_upin(upin_plain)
    if not row:
        return render_template("error.html",
            message="This UPIN is not valid. Please contact City Hall."), 404

    account_number = row["account_number"]
    prop = lookup_property(account_number)
    session["account_number"]     = account_number
    session["normalized_address"] = row["normalized_address"] or (
                                        prop["normalized_address"] if prop else "")
    session["entry_path"]         = "qr"
    session["upin_used"]          = "qr"
    session["upin_plain"]         = upin_plain
    session["is_repeat_visit"]    = has_prior_registration(account_number)
    session.pop("service_unit", None)
    return render_template("confirm_address.html",
                           address=session["normalized_address"],
                           account_number=account_number, prop=prop)

@app.route("/address-search", methods=["GET", "POST"])
def address_search():
    results, query = [], ""
    if request.method == "POST":
        query = request.form.get("street", "").strip()
        if query:
            results = search_address(query)
    return render_template("address_search.html", results=results, query=query)

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
        session.clear()
        return redirect(url_for("address_search"))
    return redirect(url_for("select_role"))

@app.route("/role", methods=["GET", "POST"])
def select_role():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        if role not in dict(ROLES):
            return render_template("role.html", roles=ROLES, error="Please select a role.")
        session["role"] = role
        if role == "landlord":
            return redirect(url_for("landlord_units"))
        return redirect(url_for("select_intent"))
    return render_template("role.html", roles=ROLES)


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
                                   error="Please enter a valid number.")
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

@app.route("/landlord/events", methods=["GET", "POST"])
def landlord_events():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    n = int(get_setting("events_to_show", "2"))
    events = get_upcoming_events(limit=n)
    events_display = [{
        "event_id":   e["event_id"],
        "name":       e["name"],
        "event_date": e["event_date"],
        "event_time": e["event_time"],
        "location":   e["location"],
        "capacity":   e["capacity"],
        "rsvp_count": e["rsvp_count"],
        "spots_left": e["capacity"] - e["rsvp_count"],
        "wards":      get_event_wards(e["event_id"]),
    } for e in events]

    if request.method == "POST":
        event_id_str = request.form.get("event_id", "").strip()
        if event_id_str:
            rsvp_id = add_event_rsvp(int(event_id_str),
                                     session["account_number"],
                                     session.get("upin_plain", ""))
            session["event_rsvp_id"] = rsvp_id
            session["intent"]        = "event"
        else:
            session["intent"]        = request.form.get("intent", "enroll")
        return redirect(url_for("contact_info"))

    return render_template("landlord_events.html",
                           events=events_display,
                           address=session.get("normalized_address"))

@app.route("/intent", methods=["GET", "POST"])
def select_intent():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.method == "POST":
        intent = request.form.get("intent", "").strip()
        if intent not in dict(INTENTS):
            return render_template("intent.html", intents=INTENTS,
                                   error="Please select an option.")
        session["intent"] = intent
        return redirect(url_for("contact_info"))
    return render_template("intent.html", intents=INTENTS)

@app.route("/contact", methods=["GET", "POST"])
def contact_info():
    if not session.get("account_number"):
        return redirect(url_for("index"))
    if request.method == "POST":
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
        """SELECT id, registered_at, normalized_address, service_unit,
                  role, intent, upin_used, unit_count_flag,
                  mass_save_enrolled, needs_callback,
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
                  (SELECT COUNT(*) FROM event_rsvps r WHERE r.event_id=e.event_id) AS rsvp_count
           FROM events e ORDER BY e.event_date, e.event_time"""
    ).fetchall()
    events_display = [dict(e) | {"wards": get_event_wards(e["event_id"]),
                                  "is_past": e["event_date"] < today}
                      for e in events]
    return render_template("admin_events.html", events=events_display)

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
