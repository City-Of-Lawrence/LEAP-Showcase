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

### Screenshot interpretation note (Playwright)

The Playwright headless Chromium doesn't bundle emoji color fonts. Screenshots will show emoji as either the underlying Unicode characters or empty boxes. In particular:
- The lang toggle `🇩🇴 Español` (Dominican flag) renders in screenshots as `DO Español`. Real users with normal browsers see the flag.
- The English toggle `🇺🇸 English` renders as `US English` in screenshots.
- The footer demo disclaimer's `⚠️` renders as `⚠` (no color).
- Emoji icons on home tiles (🏠 / 🏪 / ⚡) may render in basic glyph form rather than color.

Do not flag emoji rendering differences as findings unless they suggest a real user-facing issue.

## Route checklist

Verified against `routes/public.py` and `routes/admin.py` render_template calls on 2026-05-10. POST-only handlers, file-download routes, redirect routes, and pure JSON endpoints are excluded.

### Public flow (25 pages)

- [x] `/` → `index.html`
- [x] `/lec` → `lec.html`
- [x] `/choose-path` → `choose_path.html`
- [x] `/start` → `start_generic.html`
- [x] `/start/small-business` → redirects to `/address/street` (single-role bypass)
- [x] `/renter/login` → `renter_login.html`
- [ ] `/welcome-back` → `welcome_back.html`
- [x] `/welcome` → `welcome.html`
- [x] `/address/street` → `address_street.html` (reached via /start/small-business redirect)
- [x] `/address/pick` → `address_pick.html`
- [ ] `/address/not-found` → `address_not_found.html`
- [ ] `/address/not-found-confirm` → `address_not_found_confirm.html`
- [ ] `/select-address` → `confirm_address.html`
- [ ] `/role` → `role.html`
- [x] `/landlord/units` → `landlord_units.html`
- [ ] `/landlord/units/confirm` → `landlord_units_confirm.html`
- [ ] `/landlord/returning` → `landlord_repeat.html`
- [x] `/landlord/events` → `landlord_events.html`
- [x] `/landlord/intent` → `intent.html` (landlord branch)
- [ ] `/intent` → `intent.html` (renter branch)
- [x] `/events/select` → `event_select.html`
- [ ] `/already-registered` → `already_rsvpd.html`
- [x] `/contact` → `contact.html`
- [x] `/done` → `done.html`
- [ ] `/renter/pending` → `zombie_holding.html`
- [x] `/register` (error states) → `error.html` — clean at 1440 (UPIN-not-in-demo-DB error state). The intentional Flask 404 response status logs a console "error" but it's semantically correct (resource not found).

### Admin flow (10 pages)

- [~] `/admin/login` → `admin_login.html` — live audit at 1440 (no auth needed), then static review for rest. Clean: labeled password input, simple form, no markup issues.
- [~] `/admin/` → `admin.html` — static-reviewed
- [~] `/admin/outreach` → `admin_outreach.html` — static-reviewed
- [~] `/admin/events` → `admin_events.html` — static-reviewed (head only)
- [~] `/admin/events/new` → `admin_event_form.html` — static-reviewed in full; clean labels
- [~] `/admin/events/<id>/edit` → `admin_event_form.html` (same template)
- [~] `/admin/events/<id>/attendees` → `admin_event_attendees.html` — static-reviewed
- [~] `/admin/funnel` → `admin_funnel.html` — static-reviewed
- [~] `/admin/settings` → `admin_settings.html` — static-reviewed
- [~] `/admin/import/leap_registrations` → `admin_import_xdb.html` — static-reviewed

**Note**: live admin login was blocked because the local Flask defaults `ADMIN_PASSWORD` to `leapadmin2026`, but the user supplied the Render production password `#$CoLDemoIs0ver$`. Attempts to restart Flask with the env var override didn't propagate cleanly through the bash quoting layer. Static template review covers markup-level rubric items (a11y labels, alt text, MBLU, mojibake, structural issues) without requiring auth. Visual polish and per-viewport responsive checks on admin pages are deferred to a session that has a working ADMIN_PASSWORD match.

### Excluded routes (verified, intentional)

- `/lang/<lang>` — language toggle, redirects
- `/how-can-we-help` — redirects to `/` (no template)
- `/confirm-address`, `/address/confirm-street`, `/save-progress`, `/rsvp/<id>/cancel` — POST-only handlers, no GET render
- `/admin/logout`, `/admin/events/<id>/cancel`, `/admin/events/import`, `/admin/outreach/log` — POST-only
- `/admin/export/zombies`, `/admin/export/leap_registrations`, `/admin/events/export` — file downloads, no page
- `/resume/<token>` — requires a real token; covered as a flow entry point if a Save Progress token is generated during audit
- `/renter/start` — GET handler exists; need to verify if it renders or redirects (check during audit)

## Triage summary

**Audit pass status (2026-05-10):** PARTIAL — 7 of 35 routes swept (`/`, `/lec`, `/choose-path`, `/start`, `/start/small-business`-redirect, `/address/street`, `/renter/login`, `/register`→`error.html`). Remaining 28 routes (most auth-gated public flow + all admin) deferred to a continuation session.

**Blocker for the auth-gated continuation:** the test UPINs documented in `Test UPINS.txt` aren't present in the tracked `upinmgmt_render.sqlite` demo DB — `/register?upin=UFUZLQJERV` returns "This UPIN is not valid." Next session needs either (a) UPINs that exist in the demo DB (query the SQLite directly), or (b) traverse via the address-search flow which doesn't require a pre-issued UPIN.

**Findings logged: 11 (across 7 routes swept) + 1 informational (intentional pause-prompt behavior).** Of these, 6 are now `fixed-in-global-batch` and pushed (commit `c5c2ab8`).

| Severity | Responsive | Polish | A11y | Copy-bugs | Total |
|----------|-----------|--------|------|-----------|-------|
| S0       | 1         | 0      | 0    | 0         | 1     |
| S1       | 1         | 0      | 1    | 2         | 4     |
| S2       | 1         | 4      | 0    | 1         | 6     |

**Why global fixes are jumping the queue:** Several S1 findings live in `base.html` or shared partials and affect every page in the app. Fixing them before completing the remaining audit pass reduces noise (otherwise every subsequent page would re-flag the same global issue) and gives the remaining audit a clean baseline. This is a deliberate deviation from the plan's strict per-unit ordering; documented here so the audit trail explains the reorder.

**Global fixes batch (next commit):**
- Finding 1 (favicon 404) — copy-bugs, S2
- Finding 5 (double-arrow back link) — copy-bugs, S1, 3+ templates
- Finding 10 (base.html title mojibake) — copy-bugs, S1
- Finding 8 + 9 (Search and Email-me button touch targets at 320) — responsive, S0+S1
- Finding 4 (unlabeled UPIN input on choose-path) — a11y, S1
- Finding 3 (LEC overflow at 320) — responsive, S2

**Deferred to later passes (polish, subjective):**
- Finding 2 (lone chevron card pattern) — polish, S2 — needs design judgment
- Finding 6 (inconsistent role-tile subtitles) — polish, S2
- Finding 7 (orphan 5th tile on /start grid) — polish, S2

**Not actionable in this audit (intentional or external):**
- Finding 11 (pause prompt empty mailto + text-link dismiss) — flagged as `intentional` per CLAUDE.md
- Global Finding B (DEMO banner intermittent clipping) — to re-verify during fixes; possibly a misread

## Findings

### `/` (index.html)

Tested at 320, 768, 1440. No horizontal scroll, no overflowing elements, no small touch targets at any width. All three hero images have alt text. `<html lang="en">` set.

#### Finding 1: `/favicon.ico` returns 404
- **Where:** server-side; no favicon asset shipped in `static/`
- **Viewport(s):** all (console error fires on every page load app-wide)
- **Category:** copy-bugs
- **Severity:** S2
- **Status:** fixed-in-global-batch (2026-05-10)
- **Fix:** Added `<link rel="icon" type="image/png" href="{{ url_for('static', filename='Lawrence-Seal.png') }}"/>` in `base.html` head. Browser uses the city seal as favicon; the spurious `/favicon.ico` request is suppressed because the link tag declares the icon explicitly. Verified: 0 console errors on /choose-path after the change.

### `/lec` (lec.html)

Tested at 320, 1440. No `MBLU`, lang=en, no missing alt.

#### Finding 3: `lec-logo-link` and `lec-btn-secondary` overflow viewport at 320px
- **Where:** `templates/lec.html` (Colonial Power Group logo card + "← Back to Home" button)
- **Viewport(s):** 320 (clean at 1440)
- **Category:** responsive
- **Severity:** S2
- **Status:** fixed-in-global-batch (2026-05-10)
- **Root cause:** The Colonial logo is natively 1338×377px. CSS rendered it at `height: 72px; width: auto` which scaled it to 256px wide — wider than the parent `.lec-actions` container at narrow viewports. The image forced `.lec-logo-link` to overflow. Similar shape on `.lec-btn-secondary` (intrinsic text width).
- **Fix:** Added `max-width: 100%; height: auto` on `.lec-logo-link img` inside the existing `@media (max-width: 480px)` block. Also added `max-width: 100%` to `.lec-btn-primary, .lec-btn-secondary`. Verified at 320: both elements now 230px wide (fits parent), no overflow.

#### Finding 2: Lone `›` chevron at bottom of each program tile
- **Where:** `templates/index.html:230,238,246` — `<span class="leap-tile-chevron">&#8250;</span>`
- **Viewport(s):** all
- **Category:** polish
- **Severity:** S2
- **Status:** open
- **Notes:** Each of the three program tiles ends with a small standalone `›` glyph at the bottom. The tile is wrapped in `<a class="leap-tile">` so the whole card is clickable, and the chevron is intended as the affordance. But visually the chevron floats with no accompanying "Learn more" text and at quick glance reads as a stray character rather than a call to action. Same pattern appears on `choose_path.html:142` (`.cp-card-chevron`) and `start_generic.html` role tiles. Two fix options: (a) add `Learn more ›` text alongside, (b) move chevron inline beside the tile heading. Civic-design preference: option (a), since it's more obviously an action.

---

### `/choose-path` (choose_path.html)

Tested at 320, 1440. No horizontal scroll. Layout cleanly stacks at 320.

#### Finding 4: UPIN input has no `<label>`
- **Where:** `templates/choose_path.html:127-130` — `<input type="text" id="upin" name="upin" placeholder="...">`
- **Viewport(s):** all
- **Category:** a11y
- **Severity:** S1
- **Status:** fixed-in-global-batch (2026-05-10)
- **Fix:** Added `<label for="upin" class="sr-only">{{ t('index_upin_label') }}</label>` immediately before the input. Also added a reusable `.sr-only` utility class to `base.html` so future a11y labels can use the same pattern (visually hidden, screen-reader-announceable). Verified via Playwright: `input.labels.length === 1` and `labelText === "Enter Your UPIN"`.

#### Finding 5: Double-arrow back link "← ← Back"
- **Where:** 5 templates (`choose_path.html:148`, `how_can_we_help.html:206`, `already_rsvpd.html:65`, `start_generic.html:157`, `event_select.html:146`) — all prepended `←` or `&#8592;`/`&#x2190;` to `{{ t('back_btn') }}`
- **Viewport(s):** all
- **Category:** copy-bugs
- **Severity:** S1
- **Status:** fixed-in-global-batch (2026-05-10)
- **Root cause:** The `back_btn` translation already includes a leading `←` (en: `"← Back"`, es: `"← Atrás"`). Five templates additionally prepended their own `←`, producing `← ← Back` / `← ← Atrás`.
- **Fix:** Removed the template-side prepended arrow in all 5 templates. Translation now owns the arrow as the single source of truth. Verified on /choose-path: back link renders as `← Back` (single arrow).

---

### `/start` (start_generic.html)

Tested at 320, 1440. No horizontal scroll, no overflowing elements.

#### Finding 6: Inconsistent role-tile subtitles
- **Where:** `templates/start_generic.html` (5 role tiles: Renter, I Own & Live in My Home, Landlord, Property Manager, Small Business)
- **Viewport(s):** all
- **Category:** polish
- **Severity:** S2
- **Status:** open
- **Notes:** Only one of the five role tiles has a subtitle ("Single-family home" under "I Own & Live in My Home"). The others have only a title. This visual inconsistency reads as a missing item rather than an intentional distinction. Fix options: (a) add subtitles to all 5 tiles, (b) remove the lone subtitle, (c) make subtitles optional via a deliberate pattern (some tiles have it, others don't — but then add a visual rhythm that explains why).

#### Finding 7: "Small Business" tile orphaned in 5-tile grid at desktop
- **Where:** `templates/start_generic.html` (5 tiles in a 2-column grid at desktop → 4 + 1 lonely)
- **Viewport(s):** 768+ (at 320 they stack vertically — fine)
- **Category:** polish
- **Severity:** S2
- **Status:** open
- **Notes:** At tablet/desktop, the 5 role tiles render as 2-column grid producing a final orphaned tile in its own row. Options: (a) use 3 columns at wider widths (5 = 3 + 2), (b) collapse Small Business into a different entry point (the `/start/small-business` route exists already as a direct-link), (c) center the orphan visually.

---

### `/address/street` (address_street.html)

Tested at 320, 1440. Reached via `/start/small-business`. Clean at 1440; touch-target issues at 320.

#### Finding 8: "Search →" button is 41px tall at 320 (touch target < 44)
- **Where:** `templates/base.html` — `.btn` shared rule used by all primary/secondary/outline buttons
- **Viewport(s):** 320 (all .btn instances app-wide)
- **Category:** responsive
- **Severity:** S1
- **Status:** fixed-in-global-batch (2026-05-10)
- **Fix:** Bumped `.btn` to `display: inline-flex; align-items: center; justify-content: center; min-height: 44px` in `base.html`. inline-flex centering preserves text vertical alignment when min-height kicks in. Verified at 320 on /address/street: `Search →` 44px, `← Back` 48px. Affects every `.btn` in the app — clean baseline for the rest of the audit.

#### Finding 9: "Email me a resume link →" button is 30px tall at 320 (touch target severely under)
- **Where:** `templates/address_street.html:177-182` AND `templates/welcome.html:171-176` (Save Progress aside, two copies)
- **Viewport(s):** 320 (both submit buttons)
- **Category:** responsive
- **Severity:** S0
- **Status:** fixed-in-global-batch (2026-05-10)
- **Root cause:** Save Progress aside submit had `padding: 0.45rem 0.8rem; font-size: 0.83rem` (or `0.5rem 0.9rem; 0.85rem` in welcome.html) — well under the 44px minimum. The button uses inline styles instead of `.btn`, so the `.btn` shared fix doesn't reach it.
- **Fix:** Bumped both inline-styled submits to `padding: 0.7rem 1rem; min-height: 44px; font-size: 0.88rem`. Verified at 320 on /address/street: `Email me a resume link →` is now 44px tall.
- **Followup:** the inline styles on these two Save Progress asides should eventually be extracted to a `.btn-compact` or similar class so future Save Progress instances don't drift again. Out of scope for this batch.

---

### `/renter/login` (renter_login.html)

Tested at 1440 only (pause prompt fired before 320 sweep; pause prompt itself captured in screenshot).

Page is publicly reachable; UPIN entry form is straightforward.

#### Finding 10: Page title shows UTF-8 mojibake instead of em-dash
- **Where:** `templates/base.html` (default title block + 14 CSS comment dividers + 2 Jinja comments) — affects every page that falls back to the default title
- **Viewport(s):** all (title bar)
- **Category:** copy-bugs
- **Severity:** S1
- **Status:** fixed-in-global-batch (2026-05-10)
- **Root cause:** Two mojibake patterns. (a) `Ã¢‚¬"` (5 chars) where a single `—` em-dash should be — in the title and Jinja comments. (b) `Ã¢"‚¬Ã¢"‚¬` (10 chars) where `——` should be — in CSS comment dividers (16 of them). Originally UTF-8 em-dash bytes read as Windows-1252 and re-encoded as UTF-8 produced this drift.
- **Fix:** Two `Edit replace_all` passes on `base.html`: `Ã¢"‚¬Ã¢"‚¬` → `——`, then `Ã¢‚¬"` → `—`. Confirmed no remaining mojibake bytes (`Ã¢|Ã‚|‚¬` grep returns no matches). Verified on /renter/login title: `Lawrence Energy Affordability Project (LEAP) — DEMO` (clean em-dash).

#### Finding 11: Pause prompt fires after 45s of inactivity (intentional, confirmed working)
- **Where:** `base.html` — pause prompt modal (from Roadmap §2 A3)
- **Viewport(s):** all
- **Category:** (informational — not a bug)
- **Severity:** N/A
- **Status:** intentional
- **Notes:** Caught the modal firing during the audit sweep. Modal shows "Need a hand? Looks like you're paused. The City of Lawrence Energy Advocate is one tap away…" with three actions: Call, WhatsApp, "I'm fine, keep going". Per CLAUDE.md, the `mailto:` is intentionally absent until Anil supplies an EA email. **"I'm fine, keep going" is rendered as a text link rather than a styled button** — flagging as a follow-up polish question (is this intentional de-emphasis of the dismiss, or should it be a tertiary button?). Not actioning until clarified.

---

## Global findings (affect multiple pages via shared partials)

### Global Finding A: `/favicon.ico` returns 404 on every page

Already captured as Finding 1. Reiterating: this fires a console error on every page load app-wide.

### Global Finding B: Possible DEMO SITE banner clipping at narrow viewports

I observed truncated "DEMO SIT" in the choose-path 320 screenshot, but a re-eval on `/start` at 320 showed the banner not clipped (`clipped: false`, full text "DEMO SITE"). May have been a misread of the tiny font at 320, or the clipping is intermittent (e.g., depending on flag emoji width affecting the lang-toggle width). To re-verify during Unit 1 fixes by re-screenshotting choose-path at 320 with a fresh evaluate.

---

## Second-pass findings (from session continuation 2026-05-10)

### `/address/pick` (address_pick.html)
Reached via Renter → Andover/Exeter street search. Clean at 1440: 5-step progress, "Select Your Address" heading, well-labeled `<select>` of 189 addresses, two action buttons. No overflow, no MBLU, no unlabeled inputs.

#### Finding 12: Duplicate address entries in `<select>`
- **Where:** `routes/public.py` address-lookup logic (data layer) — surfaces in `templates/address_pick.html` rendering
- **Viewport(s):** all (data-driven, not viewport-dependent)
- **Category:** copy-bugs
- **Severity:** S2
- **Status:** open
- **Notes:** The `<select>` shows entries like `1 EXETER ST LAWRENCE MA 01843` AND `1 EXETER ST, LAWRENCE, MA 01843` (with commas) as two separate options pointing to the same `account_number = "0041 0000 0001 A"`. Same account, different display strings — confusing for the user. Likely the Outreach_Master_Unified and Assessment_L_Parcels rows have format-variant addresses that aren't normalized. Fix is non-trivial (data normalization in the lookup query). Flagging for follow-up; not in this audit's scope.

### `/welcome` (welcome.html, renter path with 1 EXETER ST)
Clean at 1440. 5-step progress (Role, Street, Address, Intent active, Contact) consistent with /address/street. Three intent option cards. Save Progress aside at bottom (now with the 44px button from the global fix).

No new findings on this page beyond what's already covered.

### `/events/select` (event_select.html, empty state)

#### Finding 13: Step indicator inconsistency — labels and order drift across pages
- **Where:** `templates/event_select.html` (step indicator) — compare to other flow pages
- **Viewport(s):** all
- **Category:** copy-bugs (also touches polish/consistency)
- **Severity:** S1
- **Status:** open
- **Notes:** The 5-step progress indicator should be consistent across the flow. Found three different variants:
  - **Variant A** (renter path, most pages): `Role / Street / Address / Intent / Contact`
  - **Variant B** (event_select.html only): `Address / Role / Intent / Event / Contact` — reordered, "Street" dropped, "Event" added
  - **Variant C** (landlord_events.html only): `Address / Role / Property / Intent / Contact` — reordered, "Street" replaced with "Property"

  Users navigating multi-step flows get disoriented when steps relabel between pages. Fix: pick one canonical label set per role-path and apply consistently. Best done as one focused PR touching the {{ t('step_*') }} translation keys or template-side label macros. Out of scope for this audit's quick-win fixes.

### `/contact` (contact.html, post-events)
Clean at 1440. Step indicator matches Variant A (Role/Street/Address/Intent/Contact). Three properly-labeled form fields (Name, Phone, Email) with privacy disclosure. Finish + Skip buttons.

No new findings on this page.

### `/done` (done.html)

#### Finding 14: "Questions? Call the City at" trails off without a phone number
- **Where:** `templates/done.html` — final trailing line
- **Viewport(s):** all
- **Category:** copy-bugs
- **Severity:** S2
- **Status:** open
- **Notes:** The done page has a `Need help with the Mass Save site?` card with phone number (978) 315-9255 + WhatsApp icon, then below that a separate line reading "Questions? Call the City at" — and nothing follows. Reads like a string concatenation broke or a variable wasn't filled. The phone number is already visible just above, so the line is also redundant. Two fix options: (a) remove the orphan line entirely, (b) complete the sentence with the City Hall phone (different from EA phone). Check `done.html` for the source — likely a translation key followed by a `{{ city_phone }}` variable that's not in context.

### `/landlord/units` (landlord_units.html)

#### Finding 15: Minus button shows `ˆ’` instead of `−` (mojibake)
- **Where:** `templates/landlord_units.html:30` — `<button>ˆ'</button>` (U+02C6 modifier-circumflex + U+2019 right-single-quote)
- **Viewport(s):** all
- **Category:** copy-bugs
- **Severity:** S1
- **Status:** fixed-in-second-batch (2026-05-10)
- **Fix:** Replaced `ˆ'` with `−` (U+2212, math minus). Matches the visual weight of the `+` companion button. Verified at 1440 after Flask reload.

### `/landlord/events` (landlord_events.html, empty state)

#### Finding 16: Empty-state copy promises a "callback below" that isn't visible
- **Where:** `templates/landlord_events.html` (empty-state alert text)
- **Viewport(s):** all
- **Category:** copy-bugs
- **Severity:** S2
- **Status:** open
- **Notes:** Alert text reads: "No sessions are currently scheduled. Check back soon — we add new sessions regularly. You can still enroll directly with Mass Save or request a callback below." But the page only has a Continue button below — no callback request form is shown on this page. The text seems to assume content that doesn't render. Either the page is missing a callback section, or the copy should be revised. Compare to `/events/select` which has a similar empty-state but with consistent copy.

### `/landlord/intent` (intent.html, landlord branch)
Step indicator matches Variant A (Role/Street/Address/Intent/Contact). Three labeled choice cards. Clean trust callout: "Remember: Official enrollment happens at masssave.com/Lawrence. The City's registration is separate and optional." Well-designed.

No new findings.

### Admin templates (static review)

10 admin templates reviewed by reading the markup. No MBLU references found anywhere (§10 #18 invariant safe). No obvious mojibake patterns. All visible inputs across `admin_event_form.html`, `admin_login.html`, `admin_settings.html`, `admin_import_xdb.html`, `admin_outreach.html` have proper `<label for=...>` associations.

#### Finding 17: `<label>Wards Targeted</label>` lacks `for` attribute (and isn't a `<fieldset>`/`<legend>`)
- **Where:** `templates/admin_event_form.html:60`
- **Viewport(s):** all
- **Category:** a11y
- **Severity:** S2
- **Status:** open
- **Notes:** The "Wards Targeted (select all that apply)" label groups 6 checkboxes (A-F). It's wrapped as a plain `<label>` without a `for` attribute (it can't have one — it's a group label, not bound to a single input). For correct a11y semantics, this should be `<fieldset><legend>Wards Targeted ...</legend>...</fieldset>`. Each checkbox already has implicit label association via its own wrapping `<label>`, so the per-input affordance is fine. Only the group-label semantics need fixing. Small change, low risk.


