"""
routes/public.py — LEAP Portal
All resident-facing routes. Registered as Blueprint "public".
"""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session
)
from datetime import datetime, timezone

from schema import upin_db
from helpers import (
    get_lang, get_setting,
    lookup_by_upin, lookup_property,
    search_streets_by_role, search_addresses_on_street,
    normalize_unit, has_prior_registration,
    get_prior_registration_summary, save_registration,
    get_upcoming_events, get_event_wards,
    add_event_rsvp, get_existing_rsvps, cancel_event_rsvp,
)
from translations import t, get_roles, get_intents, get_landlord_intents

public = Blueprint("public", __name__)

# Read from app config at runtime — set by app.py
def _masssave_url():
    from flask import current_app
    return current_app.config["MASSSAVE_URL"]

def _unit_count_multiplier():
    from flask import current_app
    return current_app.config["UNIT_COUNT_CONFIRM_MULTIPLIER"]

def _strip_unit_suffix(address: str) -> str:
    """Remove trailing unit suffix (e.g. ', Unit 1' or ' Unit 1') from display address.
    Prevents double-unit display when outreach DB address already contains unit info."""
    import re
    return re.sub(r'[,\s]+[Uu]nit\s+\S+\s*$', '', address).strip()


# ------------------------------------------------------------------
# Language toggle
# ------------------------------------------------------------------

@public.route("/lang/<lang>")
def set_language(lang):
    if lang in ("en", "es"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("public.index"))


# ------------------------------------------------------------------
# Index
# ------------------------------------------------------------------

@public.route("/")
def index():
    return render_template("index.html")


# ------------------------------------------------------------------
# QR / UPIN entry points
# ------------------------------------------------------------------

@public.route("/register")
def register_qr():
    upin_plain = request.args.get("upin", "").strip().upper()
    if not upin_plain:
        return render_template("error.html",
            message=t("error_upin_missing", get_lang())), 400
    row = lookup_by_upin(upin_plain)
    if not row:
        return render_template("error.html",
            message=t("error_upin_invalid", get_lang())), 404

    if row["upin_type"] == "unit":
        return _complete_renter_upin_login(upin_plain, row)

    account_number = row["account_number"]
    prop  = lookup_property(account_number)
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

    if prior:
        session["prior_role"]       = prior["role"] or ""
        session["prior_visit_date"] = prior["registered_at"][:10] if prior["registered_at"] else ""
        return redirect(url_for("public.welcome_back"))

    return render_template("confirm_address.html",
                           address=session["normalized_address"],
                           account_number=account_number, prop=prop)


def _complete_renter_upin_login(upin_plain, row):
    """Shared session setup and redirect for both QR scan and typed renter UPIN paths."""
    account_number  = row["account_number"]
    service_unit    = row["service_unit"] or ""
    normalized_addr = _strip_unit_suffix(row["normalized_address"] or "")

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

    # Zombie graduation
    norm_unit = normalize_unit(service_unit) if service_unit else ""
    zombie = upin_db().execute(
        """SELECT id, contact_name, contact_phone, contact_email
           FROM registrations
           WHERE normalized_address = ?
             AND service_unit = ?
             AND pending_upin = 'yes'
           ORDER BY registered_at DESC LIMIT 1""",
        (normalized_addr, norm_unit)
    ).fetchone()
    if zombie:
        upin_db().execute(
            "UPDATE registrations SET pending_upin='graduated' WHERE id=?",
            (zombie["id"],)
        )
        upin_db().commit()
        if zombie["contact_name"]:
            session["zombie_contact_name"]  = zombie["contact_name"]
        if zombie["contact_phone"]:
            session["zombie_contact_phone"] = zombie["contact_phone"]
        if zombie["contact_email"]:
            session["zombie_contact_email"] = zombie["contact_email"]
        session["graduated_zombie"] = True

    if prior:
        session["prior_role"]       = prior["role"] or ""
        session["prior_visit_date"] = (
            prior["registered_at"][:10] if prior["registered_at"] else ""
        )
        return redirect(url_for("public.welcome_back"))

    return redirect(url_for("public.welcome"))


@public.route("/renter/login", methods=["GET", "POST"])
def renter_login():
    error = None
    upin_from_qr = request.args.get("upin", "").strip().upper()
    if request.method == "GET" and upin_from_qr:
        row = lookup_by_upin(upin_from_qr)
        if not row or row["upin_type"] != "unit":
            return render_template("renter_login.html",
                                   error=t("error_upin_invalid", get_lang()))
        return _complete_renter_upin_login(upin_from_qr, row)

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


# ------------------------------------------------------------------
# Welcome back (returning visitor)
# ------------------------------------------------------------------

@public.route("/welcome-back", methods=["GET", "POST"])
def welcome_back():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))

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
            return redirect(url_for("public.landlord_events"))
        return redirect(url_for("public.event_select"))

    return render_template("welcome_back.html",
                           roles=get_roles(get_lang()),
                           upin_role=upin_role,
                           address=session.get("normalized_address"),
                           prior_role=session.get("prior_role", ""),
                           prior_visit_date=session.get("prior_visit_date", ""),
                           active_rsvps=active_rsvps)


# ------------------------------------------------------------------
# Street-address path
# ------------------------------------------------------------------

@public.route("/renter/start")
def renter_start():
    session["role"]            = "renter"
    session["entry_path"]      = "generic"
    session["upin_used"]       = "manual"
    session["is_repeat_visit"] = False
    return redirect(url_for("public.address_street"))


@public.route("/start", methods=["GET", "POST"])
def start_generic():
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
        return redirect(url_for("public.address_street"))
    return render_template("start_generic.html", roles=get_roles(get_lang()))


@public.route("/address/street", methods=["GET", "POST"])
def address_street():
    if not session.get("role"):
        return redirect(url_for("public.start_generic"))
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
                if role in ("landlord", "property_manager"):
                    return render_template("address_street.html",
                        role=dict(get_roles(lang)).get(role, ""),
                        error=t("error_street_not_found", lang)
                              + " <a href='/address/not-found'>"
                              + t("error_street_not_found_link", lang) + "</a>.")
                session["street_not_found_input"] = street_input
                return redirect(url_for("public.address_not_found_confirm"))
            if len(streets) == 1:
                session["street_name"] = streets[0]
                return redirect(url_for("public.address_pick"))
            return render_template("address_street.html",
                                   role=dict(get_roles(get_lang())).get(role, ""),
                                   streets=streets, query=street_input)
    return render_template("address_street.html",
                           role=dict(get_roles(get_lang())).get(session.get("role", ""), ""),
                           error=error)


@public.route("/address/confirm-street", methods=["POST"])
def address_confirm_street():
    if not session.get("role"):
        return redirect(url_for("public.start_generic"))
    street = request.form.get("street_name", "").strip()
    if not street:
        return redirect(url_for("public.address_street"))
    session["street_name"] = street
    return redirect(url_for("public.address_pick"))


@public.route("/address/pick", methods=["GET", "POST"])
def address_pick():
    if not session.get("role") or not session.get("street_name"):
        return redirect(url_for("public.address_street"))
    role        = session["role"]
    street_name = session["street_name"]
    addresses   = search_addresses_on_street(street_name, role)

    if request.method == "POST":
        account_number  = request.form.get("account_number", "").strip()
        service_unit    = request.form.get("service_unit", "").strip()
        display_address = request.form.get("display_address", "").strip()

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
                return redirect(url_for("public.zombie_holding"))
            return redirect(url_for("public.select_intent"))

        if not account_number:
            return render_template("address_pick.html", addresses=addresses,
                                   street_name=street_name,
                                   role=dict(get_roles(get_lang())).get(role, ""),
                                   error=t("error_select_address", get_lang()))
        prop = lookup_property(account_number)
        session["account_number"]     = account_number
        session["normalized_address"] = _strip_unit_suffix(display_address or (
                                            prop["normalized_address"] if prop else account_number))
        session["service_unit"]       = service_unit
        session["is_repeat_visit"]    = has_prior_registration(account_number, service_unit)

        if session["is_repeat_visit"]:
            prior = get_prior_registration_summary(account_number, service_unit)
            if prior:
                session["prior_role"]       = prior["role"] or ""
                session["prior_visit_date"] = prior["registered_at"][:10] if prior["registered_at"] else ""
            return redirect(url_for("public.welcome_back"))

        if role == "landlord":
            return redirect(url_for("public.landlord_units"))
        return redirect(url_for("public.welcome"))

    return render_template("address_pick.html", addresses=addresses,
                           street_name=street_name,
                           role=dict(get_roles(get_lang())).get(role, ""),
                           error=None)


@public.route("/address/not-found")
def address_not_found():
    return render_template("address_not_found.html")


@public.route("/address/not-found-confirm", methods=["GET", "POST"])
def address_not_found_confirm():
    if not session.get("role"):
        return redirect(url_for("public.start_generic"))

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
        return redirect(url_for("public.zombie_holding"))

    prefill = session.get("street_not_found_input", "")
    return render_template("address_not_found_confirm.html", prefill_address=prefill)


# Legacy redirects
@public.route("/address-search", methods=["GET", "POST"])
def address_search():
    return redirect(url_for("public.start_generic"))

@public.route("/select-address")
def select_address():
    from schema import outreach_db
    account_number = request.args.get("acct", "").strip()
    service_unit   = request.args.get("unit", "").strip()
    if not account_number:
        return redirect(url_for("public.address_search"))
    prop = lookup_property(account_number)
    outreach_row = outreach_db().execute(
        "SELECT Service_Address FROM Outreach_Master_Unified WHERE Account_Number=? LIMIT 1",
        (account_number,)
    ).fetchone()
    address = (prop["normalized_address"] if prop
               else (outreach_row["Service_Address"] if outreach_row else account_number))
    session.update({
        "account_number":     account_number,
        "normalized_address": address,
        "service_unit":       service_unit,
        "entry_path":         "generic",
        "upin_used":          "manual",
        "is_repeat_visit":    False,
    })
    return render_template("confirm_address.html",
                           address=address, service_unit=service_unit,
                           account_number=account_number, prop=prop)


@public.route("/confirm-address", methods=["POST"])
def confirm_address():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
    if request.form.get("confirmed") != "yes":
        lang = session.get("lang", "en")
        session.clear()
        session["lang"] = lang
        return redirect(url_for("public.address_search"))
    if session.get("upin_role"):
        session["role"] = session["upin_role"]
        return redirect(url_for("public.landlord_units"))
    return redirect(url_for("public.select_role"))


@public.route("/role", methods=["GET", "POST"])
def select_role():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        lang = get_lang()
        if role not in dict(get_roles(lang)):
            return render_template("role.html", roles=get_roles(lang),
                                   error=t("error_select_role", lang))
        session["role"] = role
        if role == "landlord":
            return redirect(url_for("public.landlord_units"))
        return redirect(url_for("public.select_intent"))
    return render_template("role.html", roles=get_roles(get_lang()))


# ------------------------------------------------------------------
# Landlord flow
# ------------------------------------------------------------------

@public.route("/landlord/units", methods=["GET", "POST"])
def landlord_units():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
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
        multiplier = _unit_count_multiplier()
        if known_units > 0 and reported > known_units * multiplier:
            session["unit_count_flag"] = "pending_confirm"
            return redirect(url_for("public.landlord_units_confirm"))
        elif known_units > 0 and reported != known_units:
            session["unit_count_flag"] = "soft_flag"
        else:
            session["unit_count_flag"] = "ok"
        next_step = "public.landlord_repeat" if session.get("is_repeat_visit") else "public.landlord_events"
        return redirect(url_for(next_step))

    return render_template("landlord_units.html", known_units=known_units)


@public.route("/landlord/units/confirm", methods=["GET", "POST"])
def landlord_units_confirm():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
    if request.method == "POST":
        if request.form.get("confirmed") == "yes":
            session["unit_count_flag"] = "confirmed_flag"
        else:
            session["unit_count_reported"] = session.get("unit_count_known", 0)
            session["unit_count_flag"]     = "ok"
        next_step = "public.landlord_repeat" if session.get("is_repeat_visit") else "public.landlord_events"
        return redirect(url_for(next_step))
    return render_template("landlord_units_confirm.html",
                           reported=session.get("unit_count_reported"),
                           known=session.get("unit_count_known"))


@public.route("/landlord/returning", methods=["GET", "POST"])
def landlord_repeat():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
    if request.method == "POST":
        session["mass_save_enrolled"] = request.form.get("enrolled", "no")
        session["needs_callback"]     = request.form.get("callback", "no")
        return redirect(url_for("public.landlord_events"))
    return render_template("landlord_repeat.html",
                           address=session.get("normalized_address"))


@public.route("/landlord/events", methods=["GET", "POST"])
def landlord_events():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
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
                session["event_rsvp_id"] = existing_rsvps[event_id_int]
        else:
            for event in events_display:
                if event["already_rsvpd"]:
                    cancel_event_rsvp(upin_plain, event["event_id"])
            session["no_events_notify"] = not bool(events_display)
        return redirect(url_for("public.landlord_intent"))

    return render_template("landlord_events.html",
                           events=events_display,
                           already_enrolled=already_enrolled,
                           is_repeat_visit=session.get("is_repeat_visit", False),
                           address=session.get("normalized_address"))


@public.route("/landlord/intent", methods=["GET", "POST"])
def landlord_intent():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
    lang = get_lang()
    intents = get_landlord_intents(lang)
    if request.method == "POST":
        intent = request.form.get("intent", "").strip()
        if intent not in dict(intents):
            return render_template("intent.html", intents=intents,
                                   error=t("error_select_option", lang))
        session["intent"] = intent
        return redirect(url_for("public.contact_info"))
    return render_template("intent.html", intents=intents)


# ------------------------------------------------------------------
# Shared renter / non-landlord flow
# ------------------------------------------------------------------

@public.route("/events/select", methods=["GET", "POST"])
def event_select():
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
    if session.get("role") == "renter" and not session.get("upin_plain"):
        return redirect(url_for("public.zombie_holding"))

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
                # Already registered — store correct rsvp_id and show confirmation
                session["event_rsvp_id"] = existing_rsvps[event_id_int]
                return redirect(url_for("public.already_rsvpd"))
        if not event_id_str:
            session["no_events_notify"] = True
        return redirect(url_for("public.contact_info"))

    graduated_zombie = session.get("graduated_zombie", False)
    zombie_has_contact = bool(
        session.get("zombie_contact_name") or
        session.get("zombie_contact_phone") or
        session.get("zombie_contact_email")
    )
    return render_template("event_select.html",
                           events=events_display,
                           is_repeat_visit=session.get("is_repeat_visit", False),
                           role=dict(get_roles(get_lang())).get(session.get("role", ""), ""),
                           address=session.get("normalized_address"),
                           service_unit=session.get("service_unit", ""),
                           graduated_zombie=graduated_zombie,
                           zombie_has_contact=zombie_has_contact)


@public.route("/welcome", methods=["GET", "POST"])
def welcome():
    """
    Combined greeting + intent selection screen for all non-landlord paths.
    Replaces select_intent. Shows confirmed address and three action choices.
    """
    if not session.get("account_number"):
        return redirect(url_for("public.index"))

    if request.method == "POST":
        choice = request.form.get("choice", "").strip()
        reported_fuel = request.form.get("reported_fuel", "").strip()
        # Store correction only if resident changed it from the on-file value
        assessed_fuel = session.get("assessed_fuel", "")
        if reported_fuel and reported_fuel != assessed_fuel:
            session["reported_fuel"] = reported_fuel
        else:
            session.pop("reported_fuel", None)

        if choice == "event":
            session["intent"] = "event"
            n = int(get_setting("events_to_show", "2"))
            session["no_events_notify"] = len(get_upcoming_events(limit=n)) == 0
            return redirect(url_for("public.event_select"))
        elif choice == "assistance":
            session["intent"] = "assistance"
            session["needs_callback"] = "yes"
            return redirect(url_for("public.contact_info"))
        elif choice == "enroll":
            session["intent"] = "enroll"
            return redirect(url_for("public.contact_info"))
        # Fallback — unknown choice, re-render
        return redirect(url_for("public.welcome"))

    # Fetch assessed fuel from master DB for display
    from helpers import lookup_property
    assessed_fuel = ""
    account_number = session.get("account_number", "")
    if account_number and account_number not in ("MANUAL", "NOT_FOUND"):
        prop = lookup_property(account_number)
        if prop and prop["heating_fuel_description"]:
            assessed_fuel = prop["heating_fuel_description"]
    session["assessed_fuel"] = assessed_fuel

    return render_template("welcome.html",
                           address=session.get("normalized_address"),
                           service_unit=session.get("service_unit", ""),
                           assessed_fuel=assessed_fuel)


@public.route("/already-registered")
def already_rsvpd():
    """
    Shown when a visitor submits an event they are already registered for.
    No new slot is consumed. Offers Keep or Cancel.
    """
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
    rsvp_id    = session.get("event_rsvp_id")
    upin_plain = session.get("upin_plain", "")

    event = None
    if rsvp_id:
        row = upin_db().execute(
            """SELECT e.name, e.event_date, e.event_time, e.location
               FROM event_rsvps r JOIN events e ON r.event_id = e.event_id
               WHERE r.id = ?""",
            (rsvp_id,)
        ).fetchone()
        if row:
            event = dict(row)

    return render_template("already_rsvpd.html",
                           event=event,
                           rsvp_id=rsvp_id,
                           upin_plain=upin_plain)


@public.route("/intent", methods=["GET", "POST"])
def select_intent():
    # select_intent is superseded by the welcome screen for all non-landlord paths.
    # Redirect gracefully so any bookmarked or back-navigated link still works.
    if not session.get("account_number"):
        return redirect(url_for("public.index"))
    role = session.get("role", "")
    if role == "landlord":
        return redirect(url_for("public.landlord_intent"))
    return redirect(url_for("public.welcome"))


@public.route("/contact", methods=["GET", "POST"])
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
            "pending_upin":        None,
        })
        return redirect(url_for("public.done"))

    if not session.get("account_number"):
        return redirect(url_for("public.index"))

    if request.method == "POST":
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
            "reported_fuel":       session.get("reported_fuel"),
        })
        lang   = session.get("lang", "en")
        intent = session.get("intent")
        session.clear()
        session["lang"] = lang
        if is_zombie:
            return redirect(url_for("public.zombie_holding"))
        if intent == "enroll":
            return redirect(_masssave_url())
        return redirect(url_for("public.done"))

    # Pre-fill contact fields
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
    if session.get("graduated_zombie") and not prior_contact:
        prior_contact = {
            "name":  session.get("zombie_contact_name",  ""),
            "phone": session.get("zombie_contact_phone", ""),
            "email": session.get("zombie_contact_email", ""),
        }

    return render_template("contact.html",
                           address=session.get("normalized_address"),
                           service_unit=session.get("service_unit", ""),
                           role=dict(get_roles(get_lang())).get(session.get("role", ""), ""),
                           intent=session.get("intent", ""),
                           event_rsvp_id=session.get("event_rsvp_id"),
                           no_events_notify=session.get("no_events_notify", False),
                           prior_contact=prior_contact)


@public.route("/done")
def done():
    upin_plain   = session.get("upin_plain", "")
    is_zombie    = request.args.get("zombie") == "1"
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
    return render_template("done.html", masssave_url=_masssave_url(),
                           active_rsvps=active_rsvps,
                           is_zombie=is_zombie)


@public.route("/renter/pending")
def zombie_holding():
    return render_template("zombie_holding.html")


@public.route("/rsvp/<int:rsvp_id>/cancel", methods=["POST"])
def rsvp_cancel(rsvp_id):
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
    return redirect(url_for(f"public.{next_page}"))
