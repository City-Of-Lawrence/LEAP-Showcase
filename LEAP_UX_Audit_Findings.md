# LEAP UX Audit — Findings

**Audit date:** 2026-05-10 (in progress)
**Spec:** `LEAP_UX_Audit_Design.md`
**Plan:** `LEAP_UX_Audit_Plan.md`

## Session state

### Test UPINs in use

From `Test UPINS.txt`:

| UPIN | Account / role | Notes |
|------|----------------|-------|
| `UFUZLQJERV` | acct `0102 0000 0030 A` | property-owner UPIN |
| `2KZT3TYH3W` | acct `0241 0002 0002 A` | property-owner UPIN |
| `6UEKWH4K8D` | acct `0157 0000 0081 A` | property-owner UPIN |
| `AU9GB9JL68` | acct `0079 0000 0080 A` | LEAN-eligible (OIL) |
| `HRUMEHM4RQ` | acct `0049 0000 0018 A` | LMF-eligible (ELECTRIC) |
| `C88972UNSG` | acct `0157 0000 0081 A`, renter | unit-UPIN |
| `VP3EJP2PK8` | acct `0079 0000 0080 A`, renter | unit-UPIN |
| `CD8NHDHB4T` | SELF_REPORTED, renter, `15 No Name Fake Rd Fake 2B` | unit-UPIN |
| `V65YQBVMVP` | SELF_REPORTED, landlord, `15 No Name Fake Rd` | unit-UPIN |

### Admin login

Demo admin password supplied per-session by Amel. Never logged, screenshotted, committed, or memorized. Re-share for any new session.

### §10 UI-relevant invariants (from `UPINmgmt_Technical_Context.md`)

Only one §10 rule directly impacts user-facing text:

- **#18 — Never use "MBLU" in user-facing text. Always `account_number`.** Audit each rendered page (and any visible form labels) for stray "MBLU" strings; replace with `account_number` (or the translated equivalent).

Other §10 rules are backend/data-model invariants and do not affect this audit.

### Intentional gaps (from `CLAUDE.md`)

Do not "fix" these — they're intentional:

- **Empty `mailto:` on the pause prompt** in `base.html`. Waiting on Anil to supply an Energy Advocate email. Translation key `pause_prompt_email_label` is already in place for one-line wire-up later.
- **`admin_events_PATCH.html`** template is not referenced in any `render_template(...)` call as of 2026-05-10 — likely dead code from a prior iteration. Flag for cleanup, do not audit.

## Route checklist

Verified against `routes/public.py` and `routes/admin.py` render_template calls on 2026-05-10. POST-only handlers, file-download routes, redirect routes, and pure JSON endpoints are excluded.

### Public flow (25 pages)

- [ ] `/` → `index.html`
- [ ] `/lec` → `lec.html`
- [ ] `/choose-path` → `choose_path.html`
- [ ] `/start` → `start_generic.html`
- [ ] `/start/small-business` → `start_generic.html` (alt entry)
- [ ] `/renter/login` → `renter_login.html`
- [ ] `/welcome-back` → `welcome_back.html`
- [ ] `/welcome` → `welcome.html`
- [ ] `/address/street` → `address_street.html`
- [ ] `/address/pick` → `address_pick.html`
- [ ] `/address/not-found` → `address_not_found.html`
- [ ] `/address/not-found-confirm` → `address_not_found_confirm.html`
- [ ] `/select-address` → `confirm_address.html`
- [ ] `/role` → `role.html`
- [ ] `/landlord/units` → `landlord_units.html`
- [ ] `/landlord/units/confirm` → `landlord_units_confirm.html`
- [ ] `/landlord/returning` → `landlord_repeat.html`
- [ ] `/landlord/events` → `landlord_events.html`
- [ ] `/landlord/intent` → `intent.html` (landlord branch)
- [ ] `/intent` → `intent.html` (renter branch)
- [ ] `/events/select` → `event_select.html`
- [ ] `/already-registered` → `already_rsvpd.html`
- [ ] `/contact` → `contact.html`
- [ ] `/done` → `done.html`
- [ ] `/renter/pending` → `zombie_holding.html`
- [ ] `/register` (error states) → `error.html`

### Admin flow (10 pages)

- [ ] `/admin/login` → `admin_login.html`
- [ ] `/admin/` → `admin.html`
- [ ] `/admin/outreach` → `admin_outreach.html`
- [ ] `/admin/events` → `admin_events.html`
- [ ] `/admin/events/new` → `admin_event_form.html`
- [ ] `/admin/events/<id>/edit` → `admin_event_form.html`
- [ ] `/admin/events/<id>/attendees` → `admin_event_attendees.html`
- [ ] `/admin/funnel` → `admin_funnel.html`
- [ ] `/admin/settings` → `admin_settings.html`
- [ ] `/admin/import/leap_registrations` → `admin_import_xdb.html`

### Excluded routes (verified, intentional)

- `/lang/<lang>` — language toggle, redirects
- `/how-can-we-help` — redirects to `/` (no template)
- `/confirm-address`, `/address/confirm-street`, `/save-progress`, `/rsvp/<id>/cancel` — POST-only handlers, no GET render
- `/admin/logout`, `/admin/events/<id>/cancel`, `/admin/events/import`, `/admin/outreach/log` — POST-only
- `/admin/export/zombies`, `/admin/export/leap_registrations`, `/admin/events/export` — file downloads, no page
- `/resume/<token>` — requires a real token; covered as a flow entry point if a Save Progress token is generated during audit
- `/renter/start` — GET handler exists; need to verify if it renders or redirects (check during audit)

## Triage summary

(Populated after Phase 1 audit pass completes.)

## Findings

(Appear here as the audit progresses, grouped by route.)
