# LEAP Portal — Technical Design Document
## lean_app (Blueprint architecture)
### City of Lawrence · Community First Partnership

*Prepared: March 19, 2026 · Updated: March 21, 2026*
*Author: Anil Geo, Advisor to the Mayor for Energy, Environment & Sustainability*
*Companion document: UPINmgmt_Technical_Context.md*

---

## 1. Purpose and Scope

The LEAP Portal (`lean_app`) is the public-facing web application for the City of Lawrence's Community First Partnership energy efficiency outreach program. It provides a bilingual (English/Spanish) digital registration portal that connects Lawrence residents — renters, landlords, owner-occupants, small businesses, and property managers — with Mass Save no-cost energy efficiency upgrades.

This document covers the architecture, data flows, registration paths, and design decisions for `lean_app`. It is a companion to `UPINmgmt_Technical_Context.md`, which covers the offline UPIN management system.

**What this system does:**
- Accepts resident registrations via UPIN (QR code or typed) or street address search
- Routes residents through role-appropriate registration flows
- Manages City information session RSVPs
- Provides an admin panel for City staff to manage events and view registrations
- Captures zombie registrations (street-path renters without UPINs) for letter issuance

**What this system does NOT do:**
- Enroll residents in Mass Save (that happens at masssave.com)
- Generate or manage UPINs (that is UPINmgmt's job)
- Track contractor assignments or installation status

---

## 2. Technology Stack

| Component | Technology |
|---|---|
| Web framework | Flask (Python) |
| Database | SQLite (3 databases) |
| Hosting | Render (free tier, auto-deploy from GitHub) |
| Session management | Flask server-side sessions (cookie-based) |
| Password hashing | Argon2 (for UPIN verification) |
| Translations | Custom `translations.py` (EN + Dominican Spanish) |
| Excel export/import | openpyxl |
| Code architecture | Flask Blueprints (`public`, `admin`) |
| Version control | GitHub (`EnergizeCoL/lean_app`, master branch) |
| Start command | `gunicorn app:app` (Render dashboard + Procfile) |

---

## 3. Code Architecture

As of March 21, 2026 the codebase uses Flask Blueprints. `app.py` is ~80 lines.

| File | Purpose |
|---|---|
| `app.py` | App creation, config, blueprint registration, DB teardown, schema startup |
| `schema.py` | DB connection helpers (`upin_db`, `master_db`, `outreach_db`), `ensure_schema()`, `init_schema()` |
| `helpers.py` | All shared helper functions (lookups, search, registration, events) |
| `routes/public.py` | Blueprint `"public"` — all resident-facing routes |
| `routes/admin.py` | Blueprint `"admin"`, `url_prefix="/admin"` — all admin routes |
| `routes/__init__.py` | Package marker |
| `translations.py` | EN/ES string dictionary |
| `templates/` | Jinja2 HTML templates |
| `static/` | CSS, images |

### URL naming convention
All `url_for()` calls use blueprint-prefixed endpoint names:
- Resident routes: `url_for("public.index")`, `url_for("public.event_select")`, etc.
- Admin routes: `url_for("admin.admin_dashboard")`, `url_for("admin.admin_events")`, etc.
- Static files: `url_for("static", filename=...)` — no prefix

### Config values
Passed via `app.config` dict:
- `app.config["ADMIN_PASSWORD"]` — read from `ADMIN_PASSWORD` env var
- `app.config["MASSSAVE_URL"]` — Mass Save CFP landing page URL
- `app.config["UNIT_COUNT_CONFIRM_MULTIPLIER"]` — threshold for unit count flag (default: 2)

---

## 4. Database Architecture

The app connects to three SQLite databases at runtime. All are stored on a persistent Render disk at `/data/`.

### 4.1 upinmgmt.sqlite (`DB_UPIN`)
The primary operational database. Owned by this app for read/write of registrations, events, and RSVPs. UPINs are read-only from this app's perspective — they are generated and managed by the UPINmgmt offline system.

**Tables (owned by lean_app):**

**`registrations`** — Every portal registration regardless of path
```
id                  INTEGER PRIMARY KEY
account_number      TEXT NOT NULL        -- MBLU, 'MANUAL', or 'NOT_FOUND'
upin_used           TEXT                 -- 'qr', 'upin', or 'manual'
normalized_address  TEXT
service_unit        TEXT                 -- normalized via normalize_unit()
role                TEXT
intent              TEXT
unit_count_reported INTEGER
unit_count_known    INTEGER
unit_count_flag     TEXT                 -- 'ok', 'soft_flag', 'confirmed_flag'
mass_save_enrolled  TEXT                 -- 'yes' or 'no' (returning visitor only)
needs_callback      TEXT                 -- 'yes' or null
event_rsvp_id       INTEGER
contact_name        TEXT
contact_phone       TEXT
contact_email       TEXT
registered_at       TIMESTAMP
ip_address          TEXT
pending_upin        TEXT                 -- 'yes' = zombie, 'graduated' = returned with UPIN
```

**`events`** — City information sessions
```
event_id    INTEGER PRIMARY KEY
name        TEXT
event_date  TEXT
event_time  TEXT
location    TEXT
capacity    INTEGER DEFAULT 50
status      TEXT    -- 'active' or 'cancelled'
created_at  TIMESTAMP
```

**`event_wards`** — Ward assignments for events (many-to-many)
```
id        INTEGER PRIMARY KEY
event_id  INTEGER REFERENCES events
ward      TEXT
```

**`event_rsvps`** — Resident RSVPs for events
```
id             INTEGER PRIMARY KEY
event_id       INTEGER REFERENCES events
account_number TEXT
upin           TEXT
service_unit   TEXT
rsvp_at        TIMESTAMP
cancelled_at   TIMESTAMP    -- NULL = active, set = soft-cancelled
```

**`settings`** — Portal configuration key-value store
```
key   TEXT PRIMARY KEY
value TEXT
```
Current keys: `events_to_show` (default: 2)

**Tables (owned by UPINmgmt, read-only from lean_app):**

**`upin`** — All issued UPINs
```
id                  INTEGER PRIMARY KEY
upin_hash           TEXT     -- Argon2 hash; plain text never stored
account_number      TEXT
normalized_address  TEXT
service_unit        TEXT
upin_type           TEXT     -- 'property' (landlord) or 'unit' (renter)
role                TEXT
status              TEXT     -- 'active' or 'revoked'
```

### 4.2 lawrence_master.sqlite (`DB_MASTER`)
Read-only. Contains Lawrence property assessment data from the City Assessor's office.

**Key table: `Assessment_L_Parcels`**
- `account_number` — MBLU format, primary join key
- `normalized_address` — standardized street address
- `total_occupancy` — number of units (used for landlord unit count verification)
- `heating_fuel_description` — fuel type
- `lean_eligibility` — LEAN program eligibility flag
- `owner_1_name` — property owner name
- `vision_id` — secondary ID from Vision Government Solutions CAMA

### 4.3 LEAPMailings_clean.sqlite (`DB_OUTREACH`)
Read-only. Contains National Grid outreach data — ratepayer service addresses and unit information. Sanitized version of the raw outreach data (duplicates removed).

**Key table: `Outreach_Master_Unified`**
- `Account_Number` — geocoded MBLU (may differ from assessment MBLU for some rows)
- `Service_Address` — ratepayer service address
- `Service_Unit` — unit number (inconsistent format — see normalize_unit())
- `Resident_Status` — 'Potential Renter', 'Potential Renter (Multi-Unit)', etc.

---

## 5. UPIN Architecture

UPINs are the primary identifier for properties and units. They are generated offline by UPINmgmt and never created by this app.

### 5.1 UPIN Types
| Type | Identifies | Used by |
|---|---|---|
| `property` | A parcel (building) | Landlords |
| `unit` | A specific unit within a parcel | Renters |

### 5.2 UPIN Lookup
`lookup_by_upin(upin_plain)` iterates all active UPINs and uses Argon2 to verify the hash. Plain-text UPINs are never stored — only the hash exists in the database.

### 5.3 Entry Points
- **Home page UPIN box** → `/register` → checks `upin_type` → routes to landlord or renter flow
- **QR code scan** → `/register?upin=XXXX` → same routing
- **Renter login page** → `/renter/login` → only accepts `upin_type='unit'`

---

## 6. Registration Flows

### 6.1 Entry Paths

```
Home page
  ├── UPIN / QR code
  │     ├── upin_type='property' → Landlord flow
  │     └── upin_type='unit'    → Renter UPIN flow
  │
  └── "Find My Address" (street search)
        ├── Role = Landlord/Property Manager → Landlord street flow
        └── Role = Renter/Other → Renter street flow
                                    ├── Address found → Renter street flow
                                    └── Address not found → Confirm screen → Zombie
```

### 6.2 Landlord Flow (UPIN path)
```
/register → confirm_address → landlord_units → [landlord_units_confirm?]
         → [landlord_repeat? if returning] → landlord_events → landlord_intent
         → contact → done
```

### 6.3 Landlord Flow (street path)
```
/start → address_street → address_pick → landlord_units → landlord_events
       → landlord_intent → contact → done
```

### 6.4 Renter Flow (UPIN path — full citizen)
```
/renter/login → event_select [with address banner] → contact → done
```

### 6.5 Renter Flow (street path — zombie)
```
/renter/start → address_street
  ├── Street found → address_pick
  │     ├── Address in dropdown → [session set] → select_intent → event_select
  │     │     └── RSVP gate: no upin_plain → redirect to zombie_holding
  │     └── "My address isn't listed" (MANUAL) → zombie saved → zombie_holding
  │
  └── Street not found → address_not_found_confirm → zombie saved → zombie_holding
```

### 6.6 Zombie Flow
```
zombie_holding
  ├── "Go to Mass Save Now" → masssave.com (new tab)
  └── "Got It" → /done?zombie=1 (subtitle hidden)

Later: resident receives letter → returns with UPIN → graduates to full citizen
```

### 6.7 Returning Visitor Flow
```
Any UPIN entry → has_prior_registration() = True
  → welcome_back → [action menu]
    ├── Landlord → landlord_events
    └── Renter   → event_select
```

---

## 7. Zombie State

### 7.1 Definition
A **Zombie** is a street-path renter who has completed portal registration but has no UPIN yet. They exist in the database but cannot RSVP for events until they receive a City letter with their UPIN.

### 7.2 Zombie Registration Records
All zombie registrations share these characteristics:
- `pending_upin = 'yes'`
- `intent = 'pending'` (no intent collected)
- `account_number` = `'MANUAL'` (address in DB but not listed) or `'NOT_FOUND'` (street not found)
- No contact info collected for MANUAL path (session cleared before contact screen)

### 7.3 Zombie States
| Value | Meaning |
|---|---|
| `NULL` | Normal registration — full citizen |
| `'yes'` | Zombie — awaiting letter |
| `'graduated'` | Was zombie, returned with UPIN and graduated |

### 7.4 RSVP Gate
`event_select` checks: `if role == 'renter' and not upin_plain → redirect to zombie_holding`

### 7.5 Graduation ✅ (built March 20, 2026)
When a zombie returns with their UPIN, `_complete_renter_upin_login()`:
1. Queries registrations for matching `normalized_address` + `service_unit` where `pending_upin='yes'`
2. Updates that row: `pending_upin='graduated'`
3. Carries forward contact info from zombie record into session keys (`zombie_contact_name/phone/email`)
4. Sets `session["graduated_zombie"] = True`
5. `event_select` shows a green "Welcome back!" banner for graduated zombies
6. `contact_info` pre-fills from zombie contact data if no repeat-visit record exists

---

## 8. Admin Panel

### 8.1 Routes
| Route | Purpose |
|---|---|
| `/admin` | Registrations dashboard — 200 most recent |
| `/admin/export/zombies` | CSV export of all `pending_upin='yes'` rows for UPINmgmt CLI option 15 Path B |
| `/admin/events` | Event management — create, edit, cancel |
| `/admin/events/<id>/attendees` | Per-event RSVP list with EA flag |
| `/admin/settings` | Portal configuration |
| `/admin/events/export` | Excel export of all events |
| `/admin/events/import` | Excel import of events |

### 8.2 Admin Dashboard Columns
`#` · `Date/Time` · `Address` · `Unit` · `Role` · `Intent` · `Path` · `Unit Flag` · `Mass Save: Enrolled?` · `Pending UPIN` · `Callback` · `Name` · `Phone` · `Email`

### 8.3 Energy Advocate Flag
On the attendee list page: if any registrant has 2+ cancelled RSVPs across ALL events, a yellow EA banner appears and that registrant gets an EA badge. Signal: repeated cancellations may indicate a barrier to participation that needs human follow-up.

### 8.4 Pending UPIN Badges
- `⏳ Awaiting` — amber badge for `pending_upin='yes'`. Identifies zombies needing letter issuance via UPINmgmt CLI option 15 Path B.
- `✓ Graduated` — green badge for `pending_upin='graduated'`. Zombie has returned with UPIN.
- Dashboard stats line shows zombie count. Amber `⬇ Export Zombie Queue (N)` button appears when count > 0.

---

## 9. Translation System

All resident-facing strings are stored in `translations.py` as a dict of `{key: {en: ..., es: ...}}`. Spanish is Dominican Spanish register (usted forms throughout).

```python
t(key, lang)          # Returns translated string, falls back to English
get_roles(lang)       # Returns role list for role selection screen
get_intents(lang)     # Returns intent list for intent screen
get_landlord_intents(lang)  # Simplified intent list for landlord flow
```

`inject_globals()` context processor makes `t()` and `lang` available in every template automatically. Admin templates are English-only (staff-facing).

---

## 10. Session Architecture

Flask sessions (cookie-based) carry registration state between screens. Key session variables:

| Key | Set by | Used by |
|---|---|---|
| `account_number` | address_pick, register_qr, renter_login | All routes |
| `normalized_address` | address_pick, register_qr | confirm, contact, event_select |
| `service_unit` | address_pick, renter_login | contact, event_select, save_registration |
| `role` | start_generic, renter_start, select_role | All routes |
| `upin_plain` | register_qr, renter_login | RSVP gate, event lookup |
| `upin_role` | register_qr | welcome_back, confirm_address |
| `upin_used` | All entry points | save_registration |
| `entry_path` | All entry points | save_registration |
| `intent` | select_intent, landlord_intent | contact, done |
| `is_repeat_visit` | address_pick, register_qr | welcome_back routing |
| `event_rsvp_id` | event_select, landlord_events | contact, save_registration |
| `pending_upin` | NOT in session — DB only | admin dashboard |
| `lang` | set_language | All templates via inject_globals |
| `admin_logged_in` | admin_login | admin_required decorator |
| `graduated_zombie` | `_complete_renter_upin_login()` | event_select banner, contact pre-fill |
| `zombie_contact_name` | `_complete_renter_upin_login()` | contact pre-fill carry-forward |
| `zombie_contact_phone` | `_complete_renter_upin_login()` | contact pre-fill carry-forward |
| `zombie_contact_email` | `_complete_renter_upin_login()` | contact pre-fill carry-forward |

**Session clearing:** `session.clear()` is called after `contact_info` POST (after save_registration). `lang` is preserved across the clear. `upin_plain` is NOT preserved (fixed March 11 — was causing session bleed between visitors).

---

## 11. Key Helper Functions

| Function | Purpose |
|---|---|
| `lookup_by_upin(upin_plain)` | Argon2 hash verification against all active UPINs |
| `lookup_property(account_number)` | Assessment DB parcel lookup |
| `search_streets_by_role(street, role)` | Street name search — role determines which DB(s) |
| `search_addresses_on_street(street, role)` | Address list for a confirmed street |
| `normalize_unit(unit)` | Strips APT/UNIT/STE/SUITE/# prefixes for consistent comparison |
| `has_prior_registration(acct, unit)` | Returns True if this unit has registered before |
| `get_prior_registration_summary(acct, unit)` | Returns role + date of last registration |
| `save_registration(data)` | Inserts registration row — normalizes service_unit |
| `add_event_rsvp(event_id, acct, upin, unit)` | Inserts RSVP row |
| `cancel_event_rsvp(upin, event_id)` | Soft-cancels RSVP (sets cancelled_at) |
| `get_upcoming_events(limit)` | Returns active future events with available capacity |
| `get_existing_rsvps(upin, acct, unit)` | Returns dict of {event_id: rsvp_id} for active RSVPs |
| `get_event_wards(event_id)` | Returns ward list for an event |
| `get_setting(key, default)` | Reads from settings table |

---

## 12. Schema Migration Strategy

`ensure_schema()` uses `CREATE TABLE IF NOT EXISTS` — safe for production, never drops data. New columns are added via `ALTER TABLE` guards:

```python
try:
    cur.execute("ALTER TABLE registrations ADD COLUMN new_col TEXT")
    conn.commit()
except Exception:
    pass  # Column already exists — safe to ignore
```

`init_schema()` uses `DROP TABLE IF EXISTS` — destructive, development only, called only when running `python app.py` directly (never under gunicorn/Render).

---

## 13. Known Gaps and Deferred Work

| Item | Priority | Notes |
|---|---|---|
| ~~Admin zombie queue export~~ | ✅ Done | CSV download at `/admin/export/zombies` |
| ~~Zombie graduation~~ | ✅ Done | Built March 20 — graduated badge, contact carry-forward |
| Landlord street search — both DBs in parallel | Medium | Currently outreach DB is fallback only — next session |
| Render cold start latency | Medium | Free tier spins down after 15 min inactivity |
| Stakeholder emails | When ready | Drafts complete, need phone number |
| Event attendance tracking | Low | Check-in mechanism not yet designed |
| Notifications (email/SMS) | Low | Requires Twilio/SendGrid integration |
| Admin password → environment variable | Before production | Currently has default fallback |

---

## 14. Design Principles

1. **Never block a resident.** No dead ends. Every path has a forward exit.
2. **Collect only what is necessary.** No income, SSN, utility account numbers.
3. **Protect what matters.** LEAN eligibility, parcel data, assessment info never shown to public.
4. **Postal address = proof of residency.** Post office validates, not City staff.
5. **UPIN is a property/unit identifier, not a person identifier.** Program goal is properties, not individuals.
6. **Admin panel is English-only.** Staff-facing — no translation overhead needed.
7. **Session is ephemeral.** Registration state lives in session only until `contact_info` POST. After that, everything is in the database.

---

*City of Lawrence, Massachusetts · LEAP Portal · Pro bono development*
*Anil Geo, Advisor to the Mayor for Energy, Environment & Sustainability*
*Design document prepared March 19, 2026 · Updated March 21, 2026*
