# LEAP Web App — Todo / Deferred Features

## In Progress
- [ ] No-QR generic path improvements (address fallback, Energy Advocate follow-up)

## Fixed — Session 2026-03-19
- [x] Zombie state — holding screen, pending_upin flag, RSVP gate, admin badge (commit 528b1e4)
      Street-path renters with no UPIN → "Watch for a Letter" screen. Cannot RSVP.
      MANUAL address entry → zombie registration saved immediately at address_pick.
      Admin dashboard shows ⏳ Awaiting badge for pending_upin='yes' registrations.
- [x] Zombie state — street-not-found path by role (commit 0d9410d)
      Renter/owner_occupant/small_business: confirmation screen → zombie → holding screen.
      Landlord/property_manager: existing EA path unchanged.
      Postal address = proof of residency. Post office validates, not EA.
- [x] Zombie wording — step 3 corrected, Mass Save nudge added (commit 10f4d08)
      Step 3 no longer implies Mass Save requires UPIN.
      New nudge box: "You can enroll with Mass Save right now — no code needed."
      Done page subtitle hidden for zombie visitors (?zombie=1 query param).
- [x] Home page UPIN routing — unit UPINs now route to renter flow (commit 32ae818)
      register_qr() checks upin_type: 'unit' → renter login, 'property' → landlord.
- [x] Renter address confirmation — "Mailing address on file" banner on event_select
- [x] Unit number shown on contact page address card
- [x] Full smoke test — all portal paths tested and passing (March 19, 2026)

## Fixed — Session 2026-03-18
- [x] Demo branding — LEAP name, DEMO SITE banner (orange), red footer disclaimer (commit aa28534)
- [x] Admin column rename: 'Enrolled' → 'Mass Save: Enrolled?' (commit a315be7)
- [x] Event attendee list — see Admin section

## Fixed — Session 2026-03-11 (evening)
- [x] upin_plain session bleed — landlord UPIN was preserved through session.clear()
      after contact submission, leaking into next visitor's session in same browser.
      Caused street-path renters to inherit landlord's RSVP badge incorrectly.
      Fix: removed upin_plain preservation (done page no longer needs it).
- [x] Service_Unit normalization — Outreach_Master_Unified contains inconsistent unit
      formats for the same physical unit (e.g. 'APT 323' and '323' for same unit).
      normalize_unit() helper strips APT/UNIT/STE/SUITE/# prefixes before comparison
      and storage. Applied in: search_addresses_on_street (all 3 branches), address_pick
      session storage, has_prior_registration, get_prior_registration_summary.

## Testing Required — Session 2026-03-11
- [ ] Already-enrolled landlord card — verify subtitle changes to "already enrolled" text
- [ ] Already-enrolled landlord + existing RSVP — verify "skip" cancels reservation in DB
      (`cancelled_at` should be set on the `event_rsvps` row, not deleted)
- [ ] Already-enrolled landlord + no RSVP — verify "skip" label stays as "No thanks, skip the events"
- [ ] UPIN entry first-time — confirm role selection screen is skipped entirely,
      goes directly to landlord_units
- [ ] UPIN entry returning — confirm welcome_back shows only landlord option, no other roles
- [ ] RSVP isolation — renter RSVPs at a property should NOT block landlord RSVP
      for same event (now scoped by upin_plain, not account_number)
- [ ] ⚠️ DB schema change — `event_rsvps` has new `cancelled_at` column.
      Must re-run `init_db()` or drop/recreate `upinmgmt.sqlite` before testing.
      Any existing test RSVPs will be lost — acceptable for prototype.

## Landlord Path
- [x] Unit count verification against assessment data
- [x] Repeat visit detection via UPIN
- [x] Returning visitor shortcut flow (welcome-back → action menu)
- [x] Event RSVP with capacity tracking
- [ ] Landlord street address search — query LEAPMailings_clean.sqlite (Outreach_Master_Unified)
      IN PARALLEL with lawrence_master.sqlite (Assessment_L_Parcels), not as fallback.
      Current behavior: outreach DB only queried if master DB returns nothing.
      Correct behavior: both DBs queried simultaneously, results merged and deduplicated.
      Affects: search_streets_by_role() and search_addresses_on_street() landlord branch.
- [ ] Property Manager path — differentiated from landlord
- [ ] Property UPIN role scope — currently hardcoded to "landlord" in session
      at QR entry (`register_qr()` sets `session["upin_role"] = "landlord"`).
      When Property Manager path is implemented, UPIN record in `upinmgmt.sqlite`
      will need a `role` column so the correct role can be read at scan time
      rather than assumed. `welcome_back()` already enforces whatever role is
      stored in `session["upin_role"]` — the template hides all other role
      choices when this is set, preventing a landlord UPIN from being used to
      enter as a renter.
- [ ] Owner-Occupant role — currently offered to all users on role selection screen.
      Should only be presented when the property is a single-family home.
      For multi-unit properties, a landlord living in one unit is still a landlord
      (owner-occupied multi-family) — offering "Owner-Occupant" creates ambiguity.
      Fix: check `total_occupancy` from `Assessment_L_Parcels` at role selection time;
      suppress Owner-Occupant option when `total_occupancy > 1`.
      Requires account_number to be known before role selection — currently true
      for UPIN path but NOT for street-address path (role is chosen before address).
      May need to reorder street-address flow: address first → then role.
- [ ] Landlord mailing address — for landlords entering via street address, the
      National Grid billing address (mailing address) is unknown. UPIN holders
      already have their mailing address in the National Grid outreach record.
      For street-address landlords, consider adding a mailing address field to
      the contact page, or a separate step after address confirmation.
      Needed for: invitation letters, enrollment follow-up, program correspondence.

## Event Attendance Tracking (NEW — deferred)
- [ ] Admin UI to mark an event as "occurred"
- [ ] Check-in mechanism for attendees at the event
  - Option A: Staff scans attendee QR at door
  - Option B: Attendee scans a room QR code to self-check-in
  - Option C: Staff manually enters UPIN or name
- [ ] `event_attendance` table: event_id, account_number, upin, checked_in_at, checked_in_by
- [ ] Admin report: per-event attendance vs RSVP count vs capacity
- [ ] Dashboard stat: total attendees across all events
- [ ] Follow-up flag: attended but not yet enrolled → Energy Advocate queue

## Notifications (deferred — requires email/SMS integration)
- [ ] Notify RSVPs when event is cancelled or rescheduled
- [ ] Notify contact-list users when new event is scheduled
- [ ] Enrollment confirmation nudge 2 weeks after event attendance
- [ ] Consider: Twilio for SMS, SendGrid or SES for email

## Contact Page Enhancements
- [ ] Add optional "What would you like us to call you?" name field to contact page.
      Resident chooses what to share — first name, nickname, full name, or nothing.
      Warm and respectful — aligns with portal design principle of asking only what
      is necessary. Store in contact_name column (already exists in registrations table).
      Pre-fill on return visit like phone and email.

## Renter Street-Path — Zombie State (Design Decision March 18, 2026)
- [x] "Watch for your letter" screen — commit 528b1e4
- [x] pending_upin flag in registrations table — commit 528b1e4
- [x] UPIN gate on RSVP — Zombies cannot RSVP — commit 528b1e4
- [x] Street-not-found → confirmation screen → zombie path (renters) — commit TBD
- [ ] Admin export of Zombie registrations — feeds UPINmgmt CLI option 15 Path B queue
- [ ] Graduation event — when Zombie returns with UPIN, system recognizes them and
      creates a full registration record, optionally linking to original Zombie record
- [ ] Unmatched visitors (NOT_FOUND / MANUAL address) → SELF_REPORTED path → EA resolves
      address before letter can be sent (existing UPINmgmt option 16 flow)

Key design principle: Legitimate postal address (no PO boxes) in Lawrence = proof of
residency. The UPIN in the letter IS the property/unit identifier — not a person ID.

## Other Incomplete Flows
- [ ] Renter path — no tailored guidance yet
- [ ] Owner-occupant path — same as renter currently
- [ ] Small business path — needs separate guidance
- [ ] Property manager path — needs differentiation from landlord
- [ ] Lost UPIN / invalid QR — no self-service recovery
- [x] Unit-UPIN generation — 457 unit-UPINs seeded on Render (March 18 2026)
      QR/UPIN path is primary identifier for renters. Generic address path remains
      as fallback (Zombie state) for residents without a letter.

## Admin
- [x] Event attendee list — /admin/events/<id>/attendees (commit a315be7, March 18 2026)
      Shows all RSVPs per event with contact details. Cancelled rows struck through.
      Energy Advocate flag: yellow banner + EA badge for 2+ cancellations across all events.
- [ ] Export registrations to CSV
- [ ] Filter registrations by role / flag / date range
- [ ] Callback queue view (needs_callback=yes, sorted by date)
- [ ] Change admin password via UI

## Infrastructure
- [x] Spanish language support (Dominican Spanish, static translation via translations.py)
- [x] Deploy to Render — LIVE at https://lean-app.onrender.com (commit aa28534, March 18 2026)
      498 UPINs seeded (41 property + 457 unit). Auto-deploy from GitHub master branch.
- [x] Letter printing (Option 19) — when built, print plain URL as hyperlink below QR code.
      UPINinQRlookup.py demonstrates the Fernet decrypt → pyzbar decode round trip.
      Useful for PA/AIE/Mayor review packets and residents without smartphones.
- [x] Demo QR handout PDF — generate_qr_handout.py built March 15, 2026.
      4x4 grid (16 per page), sequential numbering #1–#498, reference index at end.
      Output: qr_handout_LEAP_demo.pdf (16.5 MB, 498 QR codes + 17 index pages).
      Push to UPINmgmt git repo.
- [ ] QR handout visual enhancements (deferred):
      - City seal center overlay missing (cairosvg not available on Windows)
      - Fuel-type dot colors missing (Gas=black, Oil=brown, Electric=blue)
      - Blue border frame missing on renter QRs
      - Investigate: Inkscape CLI for SVG→PNG, or render seal directly in reportlab
- [ ] Pre-deployment: resolve handling of dash-prefix account_numbers in
      LEAPMailings_clean.sqlite before using production data on hosted portal.
      These rows (~864) have no matching parcel in Assessment_L_Parcels —
      lookup_property() returns None silently for them. Resolution paths:
        1. Re-run spatial join with relaxed tolerance (nearest centroid within N meters)
        2. Assessment dept MBLU crosswalk for State-to-City MBLU drift cases
      Demo databases deliberately exclude all dash-prefix account_numbers.
      See Known Data Quality Issues section for full detail.
- [x] Demo databases — create_demo_dbs.py rebuilt March 15, 2026.
      Now produces TWO sets: UPINmgmtDB/ (full) and leap_appDB/ (scrubbed).
      Schema corrected: owner_1_name and lean_eligibility added to Assessment_L_Parcels.
      42 parcels (41 residential + 1 commercial), 457 renter units.
      lean_eligibility: 10 LEAN, 12 LMF, 19 NULL. All integrity checks pass.
- [x] Update qr_render.py to encode City portal URL with upin_plain — FIXED March 15, 2026.
      Property: https://lean-app.onrender.com/register?upin={upin_plain}
      Unit:     https://lean-app.onrender.com/renter/login?upin={upin_plain}
      Verified end-to-end: Fernet decrypt → token → QR → pyzbar decode round trip.
- [ ] Move admin password to environment variable before any sharing
      ADMIN_PASSWORD already reads from env in app.py — just set it in Render dashboard.
- [x] Remote git repository (GitHub — private repo at github.com/EnergizeCoL/lean_app)
- [ ] Backwards-compatible schema migrations (post-deploy)
- [ ] .gitignore audit — confirm production SQLite files excluded before first push
- [ ] Set Render environment variables: SECRET_KEY, FLASK_ENV, ADMIN_PASSWORD, DB_UPIN
- [ ] translations.py — add 6 renter login keys (see Session Notes)
- [ ] sanitize_upin_for_render.py — run to produce upinmgmt_render.sqlite before push
- [ ] 200-renter QR handout PDF — after deploy confirmed working

## Known Data Quality Issues

### LEAPMailings_clean.sqlite — Anomalous Account Numbers
- account_number is a DERIVED field (not National Grid data) — computed by:
  1. Geocoding ratepayer Service_Address to lat/long
  2. Spatial point-in-polygon lookup against Lawrence parcel boundaries
  3. Assigning matched parcel's MBLU as account_number (all-digit format)
- 864 rows out of 56,780 have account_number matching PRIV or - pattern
  indicating the spatial join failed or was ambiguous
- PRIV prefix — geocoded point likely valid but landed outside any parcel polygon
  (private street, common area, etc.)
- dash pattern — likely geocoding failure, address could not be resolved to coords
- These rows will not join to Assessment_L_Parcels in lawrence_master.sqlite
- Current app risk: lookup_property() returns None silently for these rows
- TODO: Re-run spatial lookup with relaxed tolerance:
  - Try nearest parcel centroid within N meters instead of strict point-in-polygon
  - PRIV rows likely resolvable this way
  - dash rows may need re-geocoding with better geocoder first
- PROTOTYPE DECISION: Register everyone regardless of address match status.
  All four account_number states (real MBLU, PRIV/dash derived, MANUAL,
  NOT_FOUND) flow through to done page. Parcel data resolution is a
  post-prototype data quality task, not a registration blocker.
- dash rows: Geocoding succeeded and spatial join to MassGIS State parcel
  layer succeeded, but State MBLU does not match City Assessment MBLU.
  Classic MassGIS vs. City Assessment MBLU drift — subdivisions, lot
  consolidations, or clerical inconsistency between the two sources.
  Fix: Assessment dept to provide State-to-City MBLU crosswalk table — deferred
- PRIV rows: Geocoding likely succeeded (NG billing addresses are valid
  deliverable addresses). Resolution pipeline:
  1. Geocode Service_Address → (lat, long)  [geopy/Nominatim or Census geocoder]
  2. Point-in-polygon lookup against Lawrence parcel boundary layer (MassGIS)
  3. Extract MBLU from matched parcel polygon
  4. Convert MassGIS MBLU format → City Assessment account_number format
  5. Join to Assessment_L_Parcels to confirm match
  Note: These are likely large multi-unit parcels on private streets where
  the parcel fronts a public street but units have internal private street
  addresses. Parcel polygon lookup should succeed even when street geocoding
  appears to reference a private road — the coordinates will still fall
  inside the correct parcel boundary.
  Tools needed: geopandas, shapely, geopy, MassGIS parcel shapefile for Lawrence
  This is a standalone data prep script, not an app change.
- Landlord path safe — lookup is against lawrence_master.sqlite directly

## Data Architecture Decisions (for documentation)

### Primary Property Identifier: account_number (MBLU format)
- MBLU assigned and managed by Registry of Deeds — most stable identifier
- Survives ownership changes, reassessments, CAMA vendor changes
- Aligns with legal record (deeds, liens, title searches)
- Vision_ID is application-internal to Vision Government Solutions CAMA
  system currently used by Lawrence — useful as secondary fallback only
- If Vision_ID lookup ever needed as fallback, it is present in both
  Outreach_Master_Unified and Assessment_L_Parcels for cross-reference

## Known Data Quality Issues — Service_Unit Format
- Outreach_Master_Unified contains inconsistent Service_Unit formats for the same
  physical unit within the same table (e.g. 'APT 323' and '323' for 106 Hawthorne Way).
- Root cause unknown — likely different import batches or NG billing system updates.
- Current fix: normalize_unit() strips prefixes before comparison and storage.
- Post-prototype: worth auditing Outreach_Master_Unified for extent of inconsistency
  and normalizing at the source DB level if widespread.

## Address Search UX
- Large complexes (e.g. Hawthorne Way — 172 units across 2 parcels) produce
  very long dropdowns. For prototype this is acceptable.
- Post-prototype: consider replacing dropdown with a searchable/filterable
  input (e.g. Select2 or a simple JS filter on the dropdown) when result
  count exceeds ~30 addresses
- Root cause: many renters share same Account_Number (MBLU) — multi-unit
  buildings on private streets. Query now uses GROUP BY Service_Address,
  Service_Unit to show individual units rather than collapsing to 2 parcels.
