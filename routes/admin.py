"""
routes/admin.py — LEAP Portal
All admin routes. Registered as Blueprint "admin" with url_prefix="/admin".
"""

import io
import csv
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, abort, send_file, Response, current_app
)

from schema import upin_db, DB_UPIN
from helpers import admin_required, get_setting, get_event_wards

admin = Blueprint("admin", __name__, url_prefix="/admin")

# ------------------------------------------------------------------
# Tables owned by lean_app — the only tables touched by export/import.
# upin, upinInfo, audit_event are UPINmgmt-owned — never touched here.
# ------------------------------------------------------------------
LEAN_APP_TABLES = ["registrations", "events", "event_wards", "event_rsvps", "settings"]


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

@admin.route("/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == current_app.config["ADMIN_PASSWORD"]:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.admin_dashboard"))
        error = "Incorrect password."
    return render_template("admin_login.html", error=error)

@admin.route("/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.admin_login"))


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@admin.route("")
@admin_required
def admin_dashboard():
    rows = upin_db().execute(
        """SELECT id, registered_at, normalized_address, service_unit,
                  role, intent, upin_used, unit_count_flag,
                  mass_save_enrolled, needs_callback, pending_upin,
                  contact_name, contact_phone, contact_email, reported_fuel
           FROM registrations ORDER BY registered_at DESC LIMIT 200"""
    ).fetchall()
    total     = upin_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    flags     = upin_db().execute(
        "SELECT COUNT(*) FROM registrations WHERE unit_count_flag IN ('soft_flag','confirmed_flag')"
    ).fetchone()[0]
    callbacks = upin_db().execute(
        "SELECT COUNT(*) FROM registrations WHERE needs_callback='yes'"
    ).fetchone()[0]
    zombies   = upin_db().execute(
        "SELECT COUNT(*) FROM registrations WHERE pending_upin='yes'"
    ).fetchone()[0]
    return render_template("admin.html", rows=rows, total=total,
                           flags=flags, callbacks=callbacks, zombies=zombies,
                           events_to_show=get_setting("events_to_show", "2"))


# ------------------------------------------------------------------
# Outreach view (Roadmap Area 4 -- Operational Sustainability)
# ------------------------------------------------------------------

# Threshold-dropdown options surfaced in the page header. Days ints.
OUTREACH_THRESHOLD_CHOICES = [1, 3, 7, 14]


@admin.route("/outreach", methods=["GET", "POST"])
@admin_required
def admin_outreach():
    """At-risk advocate workflow.

    Surfaces the subset of registrations that registered with intent to
    enroll (or attend an event leading to enrollment), did not complete
    Mass Save enrollment, and have aged past the configurable
    ``outreach_at_risk_days`` threshold -- plus anyone with
    ``needs_callback='yes'`` regardless of age.

    Rows whose latest ``outreach_log.outcome`` is ``enrolled`` or
    ``unreachable`` drop out of the default view. ``reached`` and
    ``not_interested`` re-surface once the registration ages forward of
    its previous contact, so the Advocate gets a follow-up reminder.
    """
    # POST: threshold-dropdown change. The Mark-contacted modal posts to
    # /outreach/log instead, so the only POST that lands here is the
    # threshold setter.
    if request.method == "POST":
        try:
            n = int(request.form.get("outreach_at_risk_days", "3"))
            if n not in OUTREACH_THRESHOLD_CHOICES:
                n = 3
        except ValueError:
            n = 3
        upin_db().execute(
            "INSERT OR REPLACE INTO settings (key,value) VALUES "
            "('outreach_at_risk_days',?)",
            (str(n),),
        )
        upin_db().commit()
        return redirect(url_for("admin.admin_outreach"))

    threshold_days = int(get_setting("outreach_at_risk_days", "3"))

    # The latest outreach_log row per registration -- joined left so
    # never-contacted registrations show up with NULL latest_outcome.
    # Index idx_outreach_log_registration makes this O(log n).
    latest_outreach_join = (
        "LEFT JOIN ("
        "  SELECT o.registration_id, o.outcome, o.contacted_at "
        "  FROM outreach_log o "
        "  WHERE o.contacted_at = ("
        "    SELECT MAX(contacted_at) FROM outreach_log "
        "    WHERE registration_id = o.registration_id"
        "  )"
        ") lo ON lo.registration_id = r.id"
    )

    # At-risk filter as documented above. Parameter for threshold uses
    # SQLite's datetime modifier syntax so the days value plugs in.
    threshold_modifier = f"-{threshold_days} days"

    rows = upin_db().execute(
        f"""SELECT r.id, r.registered_at, r.normalized_address, r.service_unit,
                   r.role, r.intent, r.mass_save_enrolled, r.needs_callback,
                   r.contact_name, r.contact_phone, r.contact_email,
                   r.inviting_event_id,
                   lo.outcome      AS latest_outcome,
                   lo.contacted_at AS latest_contact_at,
                   CAST(julianday('now') - julianday(r.registered_at) AS INTEGER)
                       AS age_days
            FROM registrations r
            {latest_outreach_join}
            WHERE COALESCE(lo.outcome,'') NOT IN ('enrolled','unreachable')
              AND (
                r.needs_callback = 'yes'
                OR (
                  r.intent IN ('enroll','event')
                  AND COALESCE(r.mass_save_enrolled,'') = ''
                  AND r.registered_at < datetime('now', ?)
                )
              )
            ORDER BY r.registered_at ASC""",
        (threshold_modifier,),
    ).fetchall()

    # Header summary tiles, scoped to enroll/event funnel intent.
    summary = upin_db().execute(
        f"""SELECT
              SUM(CASE WHEN COALESCE(lo.outcome,'') = 'reached'
                        AND COALESCE(r.mass_save_enrolled,'') = ''
                       THEN 1 ELSE 0 END) AS reached_in_flight,
              SUM(CASE WHEN COALESCE(lo.outcome,'') = 'enrolled'
                        OR  r.mass_save_enrolled = 'yes'
                       THEN 1 ELSE 0 END) AS enrolled,
              SUM(CASE WHEN COALESCE(lo.outcome,'') = 'unreachable'
                       THEN 1 ELSE 0 END) AS unreachable
            FROM registrations r
            {latest_outreach_join}
            WHERE r.intent IN ('enroll','event')"""
    ).fetchone()

    return render_template(
        "admin_outreach.html",
        rows=rows,
        threshold_days=threshold_days,
        threshold_choices=OUTREACH_THRESHOLD_CHOICES,
        needs_outreach=len(rows),
        reached_in_flight=summary["reached_in_flight"] or 0,
        enrolled=summary["enrolled"] or 0,
        unreachable=summary["unreachable"] or 0,
    )


@admin.route("/outreach/log", methods=["POST"])
@admin_required
def admin_outreach_log():
    """Insert a row into outreach_log (Mark-contacted modal target)."""
    try:
        registration_id = int(request.form["registration_id"])
    except (KeyError, ValueError):
        abort(400)

    channel = request.form.get("channel", "")
    outcome = request.form.get("outcome", "")
    notes   = (request.form.get("notes") or "").strip() or None

    if channel not in ("call", "email", "whatsapp", "other"):
        abort(400)
    if outcome not in ("reached", "unreachable", "enrolled", "not_interested"):
        abort(400)

    upin_db().execute(
        "INSERT INTO outreach_log "
        "(registration_id, contacted_by, channel, outcome, notes) "
        "VALUES (?, 'admin', ?, ?, ?)",
        (registration_id, channel, outcome, notes),
    )
    upin_db().commit()
    return redirect(url_for("admin.admin_outreach"))


# ------------------------------------------------------------------
# Zombie queue export
# ------------------------------------------------------------------

@admin.route("/export/zombies")
@admin_required
def admin_export_zombies():
    """Export all pending zombie registrations as CSV for UPINmgmt CLI option 15 Path B."""
    rows = upin_db().execute(
        """SELECT id, registered_at, normalized_address, service_unit,
                  role, account_number, contact_name, contact_phone, contact_email
           FROM registrations
           WHERE pending_upin = 'yes'
           ORDER BY registered_at"""
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "registered_at", "normalized_address", "service_unit",
                     "role", "account_number", "contact_name", "contact_phone", "contact_email"])
    for r in rows:
        writer.writerow([
            r["id"], r["registered_at"], r["normalized_address"] or "",
            r["service_unit"] or "", r["role"] or "", r["account_number"] or "",
            r["contact_name"] or "", r["contact_phone"] or "", r["contact_email"] or "",
        ])

    filename = f"LEAP_zombie_queue_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ------------------------------------------------------------------
# XDB export — full lean_app data snapshot
# ------------------------------------------------------------------

@admin.route("/export/leap_registrations")
@admin_required
def admin_export_xdb():
    """
    Export all lean_app-owned tables to a single SQLite file (.xdb).

    Tables exported: registrations, events, event_wards, event_rsvps, settings.
    Tables NOT touched: upin, upinInfo, audit_event (UPINmgmt-owned — sacred).

    The .xdb file is the interchange format between lean_app and UPINmgmt.
    Drop it in UPINmgmt/EventInfo/ on the city workstation for Option 19.
    It is also the restore artifact — import it back via /admin/import/leap_registrations.
    """
    src_path = DB_UPIN

    # Build the export in memory as a fresh SQLite DB
    # containing only the lean_app-owned tables.
    export_conn = sqlite3.connect(":memory:")
    export_conn.row_factory = sqlite3.Row

    src_conn = sqlite3.connect(src_path)
    src_conn.row_factory = sqlite3.Row

    try:
        for table in LEAN_APP_TABLES:
            # Copy schema from source
            schema_row = src_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            ).fetchone()
            if not schema_row:
                continue  # table doesn't exist yet — skip gracefully
            export_conn.execute(schema_row["sql"])

            # Copy all rows
            rows = src_conn.execute(f"SELECT * FROM {table}").fetchall()
            if rows:
                cols   = rows[0].keys()
                params = ", ".join(["?"] * len(cols))
                export_conn.executemany(
                    f"INSERT INTO {table} VALUES ({params})",
                    [tuple(r) for r in rows]
                )

        export_conn.commit()

        # Serialize to bytes
        buf = io.BytesIO()
        for chunk in export_conn.iterdump():
            pass  # iterdump is for SQL text — use backup API instead

        # Use SQLite backup API to write to bytes buffer via a temp file
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xdb")
        os.close(tmp_fd)
        try:
            dest_conn = sqlite3.connect(tmp_path)
            export_conn.backup(dest_conn)
            dest_conn.close()
            with open(tmp_path, "rb") as f:
                buf = io.BytesIO(f.read())
        finally:
            os.unlink(tmp_path)

    finally:
        src_conn.close()
        export_conn.close()

    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="leap_registrations.xdb",
        mimetype="application/octet-stream",
    )


# ------------------------------------------------------------------
# XDB import / restore — two-step: upload → confirm → execute
# ------------------------------------------------------------------

def _count_tables_in_xdb(path):
    """
    Open an .xdb file and return a dict of {table_name: row_count}
    for all lean_app-owned tables found in the file.
    Returns None if the file is not valid SQLite.
    """
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        # Quick sanity check — valid SQLite files have sqlite_master
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    except sqlite3.DatabaseError:
        return None

    counts = {}
    for table in LEAN_APP_TABLES:
        try:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = None  # table missing in uploaded file
    conn.close()
    return counts


def _count_current_tables():
    """Return {table_name: row_count} for live lean_app tables."""
    counts = {}
    for table in LEAN_APP_TABLES:
        try:
            counts[table] = upin_db().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = 0
    return counts


@admin.route("/import/leap_registrations", methods=["GET", "POST"])
@admin_required
def admin_import_xdb():
    """
    Two-step import/restore from .xdb file.

    GET  — show upload form
    POST (step=upload)   — validate file, save to session staging area,
                           show confirmation screen with current vs incoming counts
    POST (step=confirm)  — backup current DB, execute full replace of lean_app tables
    POST (step=cancel)   — clean up staged file, redirect to dashboard
    """
    step = request.form.get("step", "upload") if request.method == "POST" else "upload"

    # ---- GET: show upload form ----
    if request.method == "GET":
        return render_template("admin_import_xdb.html",
                               step="upload", error=None)

    # ---- POST step=cancel ----
    if step == "cancel":
        staged = session.pop("xdb_staged_path", None)
        if staged and os.path.exists(staged):
            os.unlink(staged)
        return redirect(url_for("admin.admin_dashboard"))

    # ---- POST step=upload: validate and stage ----
    if step == "upload":
        f = request.files.get("xdb_file")

        if not f or not f.filename:
            return render_template("admin_import_xdb.html",
                                   step="upload",
                                   error="No file selected.")

        if not (f.filename.endswith(".xdb") or f.filename.endswith(".xdbk")):
            return render_template("admin_import_xdb.html",
                                   step="upload",
                                   error="Invalid file type. Please upload a .xdb file.")

        # Save to a temp file for validation and staging
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xdb")
        os.close(tmp_fd)
        f.save(tmp_path)

        # Validate: is it valid SQLite with expected tables?
        incoming_counts = _count_tables_in_xdb(tmp_path)
        if incoming_counts is None:
            os.unlink(tmp_path)
            return render_template("admin_import_xdb.html",
                                   step="upload",
                                   error="Invalid file: not a valid SQLite database.")

        missing = [t for t, c in incoming_counts.items() if c is None]
        if missing:
            os.unlink(tmp_path)
            return render_template("admin_import_xdb.html",
                                   step="upload",
                                   error=f"Invalid file: missing table(s): {', '.join(missing)}")

        # Stage path in session for confirm step
        # Clean up any previously staged file first
        old_staged = session.pop("xdb_staged_path", None)
        if old_staged and os.path.exists(old_staged):
            os.unlink(old_staged)
        session["xdb_staged_path"] = tmp_path

        current_counts  = _count_current_tables()

        return render_template("admin_import_xdb.html",
                               step="confirm",
                               current_counts=current_counts,
                               incoming_counts=incoming_counts,
                               tables=LEAN_APP_TABLES,
                               error=None)

    # ---- POST step=confirm: backup then replace ----
    if step == "confirm":
        staged_path = session.pop("xdb_staged_path", None)

        if not staged_path or not os.path.exists(staged_path):
            return render_template("admin_import_xdb.html",
                                   step="upload",
                                   error="Session expired or staged file missing. Please upload again.")

        # --- Step 1: Backup current DB to /data/backups/ ---
        backup_dir = os.path.join(os.path.dirname(DB_UPIN), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_filename = datetime.now().strftime("%Y%m%d_%H%M") + ".xdbk"
        backup_path     = os.path.join(backup_dir, backup_filename)

        try:
            src_conn  = sqlite3.connect(DB_UPIN)
            dest_conn = sqlite3.connect(backup_path)
            # Backup only the lean_app tables — not upin/upinInfo/audit_event
            # We do this by building a fresh DB with just those tables
            dest_conn.close()
            # Full file backup is safer — easier to restore from console.
            # upin/upinInfo/audit_event are included in the .xdbk but
            # the restore step below only replaces lean_app tables,
            # so the backup having them is harmless and actually useful
            # for full disaster recovery.
            dest_conn = sqlite3.connect(backup_path)
            src_conn.backup(dest_conn)
            dest_conn.close()
            src_conn.close()
        except Exception as e:
            os.unlink(staged_path)
            return render_template("admin_import_xdb.html",
                                   step="upload",
                                   error=f"Backup failed — restore aborted. Error: {e}")

        # --- Step 2: Replace lean_app tables only ---
        try:
            incoming_conn = sqlite3.connect(staged_path)
            incoming_conn.row_factory = sqlite3.Row
            live_conn     = sqlite3.connect(DB_UPIN)

            for table in LEAN_APP_TABLES:
                # Drop and recreate from incoming schema
                schema_row = incoming_conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                ).fetchone()
                if not schema_row:
                    continue

                live_conn.execute(f"DROP TABLE IF EXISTS {table}")
                live_conn.execute(schema_row["sql"])

                rows = incoming_conn.execute(f"SELECT * FROM {table}").fetchall()
                if rows:
                    cols   = rows[0].keys()
                    params = ", ".join(["?"] * len(cols))
                    live_conn.executemany(
                        f"INSERT INTO {table} VALUES ({params})",
                        [tuple(r) for r in rows]
                    )

            live_conn.commit()
            live_conn.close()
            incoming_conn.close()

        except Exception as e:
            # Backup already made — operator can restore manually via console
            return render_template("admin_import_xdb.html",
                                   step="upload",
                                   error=(
                                       f"Restore failed mid-way. Error: {e} — "
                                       f"Backup saved as backups/{backup_filename} "
                                       f"— restore via Render console if needed."
                                   ))
        finally:
            os.unlink(staged_path)

        session["import_xdb_result"] = (
            f"Restore complete. Previous data backed up as backups/{backup_filename}."
        )
        return redirect(url_for("admin.admin_dashboard"))

    # Fallback
    return redirect(url_for("admin.admin_import_xdb"))


# ------------------------------------------------------------------
# Events management
# ------------------------------------------------------------------

@admin.route("/events")
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
    import_xdb_result = session.pop("import_xdb_result", None)
    return render_template("admin_events.html", events=events_display,
                           import_result=import_result,
                           import_xdb_result=import_xdb_result)

@admin.route("/events/new", methods=["GET", "POST"])
@admin_required
def admin_event_new():
    if request.method == "POST":
        audience = request.form.get("audience", "residential").strip()
        cur = upin_db().execute(
            "INSERT INTO events (name,event_date,event_time,location,capacity,audience) VALUES (?,?,?,?,?,?)",
            (request.form["name"], request.form["event_date"],
             request.form["event_time"], request.form["location"],
             int(request.form.get("capacity", 50) or 50),
             audience)
        )
        for ward in request.form.getlist("wards"):
            upin_db().execute(
                "INSERT INTO event_wards (event_id,ward) VALUES (?,?)",
                (cur.lastrowid, ward.strip())
            )
        upin_db().commit()
        return redirect(url_for("admin.admin_events"))
    return render_template("admin_event_form.html", event=None, wards=[])

@admin.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_event_edit(event_id):
    event = upin_db().execute(
        "SELECT * FROM events WHERE event_id=?", (event_id,)
    ).fetchone()
    if not event:
        abort(404)
    existing_wards = get_event_wards(event_id)
    if request.method == "POST":
        audience = request.form.get("audience", "residential").strip()
        upin_db().execute(
            "UPDATE events SET name=?,event_date=?,event_time=?,location=?,capacity=?,audience=? WHERE event_id=?",
            (request.form["name"], request.form["event_date"],
             request.form["event_time"], request.form["location"],
             int(request.form.get("capacity", 50) or 50),
             audience, event_id)
        )
        upin_db().execute("DELETE FROM event_wards WHERE event_id=?", (event_id,))
        for ward in request.form.getlist("wards"):
            upin_db().execute(
                "INSERT INTO event_wards (event_id,ward) VALUES (?,?)",
                (event_id, ward.strip())
            )
        upin_db().commit()
        return redirect(url_for("admin.admin_events"))
    return render_template("admin_event_form.html", event=event, wards=existing_wards)

@admin.route("/events/<int:event_id>/cancel", methods=["POST"])
@admin_required
def admin_event_cancel(event_id):
    upin_db().execute("UPDATE events SET status='cancelled' WHERE event_id=?", (event_id,))
    upin_db().commit()
    return redirect(url_for("admin.admin_events"))

@admin.route("/events/<int:event_id>/attendees")
@admin_required
def admin_event_attendees(event_id):
    event = upin_db().execute(
        "SELECT * FROM events WHERE event_id=?", (event_id,)
    ).fetchone()
    if not event:
        abort(404)

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

    account_numbers = list({a["account_number"] for a in attendees
                            if a["account_number"] and a["cancelled_at"]})
    ea_flags = set()
    for acct in account_numbers:
        count = upin_db().execute(
            "SELECT COUNT(*) FROM event_rsvps WHERE account_number=? AND cancelled_at IS NOT NULL",
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

@admin.route("/events/export")
@admin_required
def admin_events_export():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    events = upin_db().execute(
        "SELECT * FROM events ORDER BY event_date, event_time"
    ).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Events"

    headers = ["event_id", "name", "event_date", "event_time",
               "location", "capacity", "status", "audience", "wards"]
    header_fill = PatternFill("solid", start_color="1A3A5C")
    header_font = Font(bold=True, color="FFFFFF", name="Arial")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    widths = [10, 35, 12, 10, 35, 10, 10, 18, 20]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = w

    for row_num, e in enumerate(events, 2):
        wards = ", ".join(get_event_wards(e["event_id"]))
        ws.cell(row=row_num, column=1, value=e["event_id"])
        ws.cell(row=row_num, column=2, value=e["name"])
        ws.cell(row=row_num, column=3, value=e["event_date"])
        ws.cell(row=row_num, column=4, value=e["event_time"])
        ws.cell(row=row_num, column=5, value=e["location"])
        ws.cell(row=row_num, column=6, value=e["capacity"])
        ws.cell(row=row_num, column=7, value=e["status"])
        ws.cell(row=row_num, column=8, value=e["audience"] if "audience" in e.keys() else "residential")
        ws.cell(row=row_num, column=9, value=wards)
        if row_num % 2 == 0:
            fill = PatternFill("solid", start_color="EEF2F7")
            for col in range(1, 10):
                ws.cell(row=row_num, column=col).fill = fill

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"LEAP_events_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@admin.route("/events/import", methods=["POST"])
@admin_required
def admin_events_import():
    from openpyxl import load_workbook

    f = request.files.get("events_file")
    if not f or not f.filename.endswith(".xlsx"):
        return redirect(url_for("admin.admin_events"))

    wb = load_workbook(io.BytesIO(f.read()), data_only=True)
    ws = wb.active

    existing = upin_db().execute(
        "SELECT name, event_date, event_time, location FROM events"
    ).fetchall()
    existing_keys = {
        (r["name"].strip().lower(), r["event_date"].strip(),
         r["event_time"].strip(), r["location"].strip().lower())
        for r in existing
    }

    imported = 0
    skipped  = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[1]:
            continue
        name      = str(row[1]).strip()
        edate     = str(row[2]).strip() if row[2] else ""
        etime     = str(row[3]).strip() if row[3] else ""
        location  = str(row[4]).strip() if row[4] else ""
        capacity  = int(row[5]) if row[5] else 50
        status    = str(row[6]).strip() if row[6] in ("active", "cancelled") else "active"
        # audience column added -- default to 'residential' for older exports without it
        _aud_raw  = str(row[7]).strip() if len(row) > 7 and row[7] else "residential"
        audience  = _aud_raw if _aud_raw in (
            "residential", "general", "small_business", "multi_unit", "lra", "lec"
        ) else "residential"
        wards_str = str(row[8]).strip() if len(row) > 8 and row[8] else ""

        key = (name.lower(), edate, etime, location.lower())
        if key in existing_keys:
            skipped += 1
            continue

        cur = upin_db().execute(
            "INSERT INTO events (name, event_date, event_time, location, capacity, status, audience) "
            "VALUES (?,?,?,?,?,?,?)",
            (name, edate, etime, location, capacity, status, audience)
        )
        new_id = cur.lastrowid
        for ward in [w.strip() for w in wards_str.split(",") if w.strip()]:
            upin_db().execute(
                "INSERT INTO event_wards (event_id, ward) VALUES (?,?)", (new_id, ward)
            )
        existing_keys.add(key)
        imported += 1

    upin_db().commit()
    session["import_result"] = f"Imported {imported} event(s), skipped {skipped} duplicate(s)."
    return redirect(url_for("admin.admin_events"))


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

@admin.route("/settings", methods=["GET", "POST"])
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
        return redirect(url_for("admin.admin_settings"))
    return render_template("admin_settings.html",
                           events_to_show=get_setting("events_to_show", "2"))
