"""
routes/admin.py — LEAP Portal
All admin routes. Registered as Blueprint "admin" with url_prefix="/admin".
"""

import io
import csv
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, abort, send_file, Response
)

from schema import upin_db
from helpers import admin_required, get_setting, get_event_wards

admin = Blueprint("admin", __name__, url_prefix="/admin")


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

@admin.route("/login", methods=["GET", "POST"])
def admin_login():
    from flask import current_app
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
    return render_template("admin_events.html", events=events_display,
                           import_result=import_result)

@admin.route("/events/new", methods=["GET", "POST"])
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
               "location", "capacity", "status", "wards"]
    header_fill = PatternFill("solid", start_color="1A3A5C")
    header_font = Font(bold=True, color="FFFFFF", name="Arial")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    widths = [10, 35, 12, 10, 35, 10, 10, 20]
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
        ws.cell(row=row_num, column=8, value=wards)
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
