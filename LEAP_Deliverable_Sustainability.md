# LEAP Deliverable scope — Operational Sustainability (UX Roadmap Area 4)

Implementation spec. Anchored in [LEAP_UX_Roadmap.md](LEAP_UX_Roadmap.md) §4, "Advocate Capacity Management." Four shape-determining decisions made by Amel 2026-05-08 (rationale inline below); remaining tunables are listed at the end. PR will be opened for Anil's review.

## Problem

As registration volume grows, the Energy Advocate (Amel) becomes a serial bottleneck for the funnel's most valuable transition: registered → enrolled with Mass Save. The handoff cliff (Area 1) shipped polished copy, partnership lockup, and safety-net contact in `12162c2` + `fc188df`, but the *signal* that a specific resident hit the cliff and never crossed it is still trapped in `registrations` rows nobody is auditing day-to-day. Without a surfacing mechanism, outreach is reactive — Amel hears about stalls only when residents call back themselves, which is exactly the wrong selection bias.

The roadmap proposes:

> Build a dashboard that alerts the Advocate to "at-risk" users (those who started but did not complete the handoff). This allows the Advocate to perform proactive outreach rather than reactive support.

## What's already there (don't rebuild)

The signals exist in `registrations` (`schema.py:132–155`); the existing admin dashboard (`/admin`, `routes/admin.py:53–76` → `templates/admin.html`) shows the raw rows but doesn't filter or age them.

| Field | Current use | Useful for at-risk? |
|---|---|---|
| `registered_at` | sort key | **yes** — drives aging |
| `intent` | `enroll` / `event` / `assistance` / `enrolled_update` / `done` | **yes** — `enroll` + `event` are the at-risk intents |
| `mass_save_enrolled` | column displayed | **yes** — null/empty after `enroll` intent = stalled |
| `needs_callback` | counted in summary, displayed | **yes** — explicit ask |
| `pending_upin` | "zombie" queue | tangentially — different bottleneck (no UPIN minted yet) |
| `inviting_event_id` | new in `3d50ffe` | **yes** — per-campaign rollup |
| `contact_phone`, `contact_email`, `contact_name` | displayed | **yes** — outreach channels |
| `event_rsvp_id` | linked RSVP | maybe — RSVPed-but-no-show is a future at-risk signal |

What's **not** there:
- Per-record outreach state (when last contacted, by whom, with what result).
- Aging-based visual treatment.
- A view that pre-filters to "needs outreach now" instead of showing all 200 most-recent rows.

## In scope

A **"Needs Outreach" view** that surfaces the subset of registrations actively at risk, with aging, click-to-contact affordances, an outcome-capturing "Mark contacted" workflow, and a per-campaign rollup.

- New admin route: `/admin/outreach` (sub-page, `@admin_required`).
- New template: `templates/admin_outreach.html`.
- New nav entry "Outreach" in `admin.html`'s top button row, alongside Events / Settings.
- **Schema (decision 1 — comprehensive):** new `outreach_log` table, one row per contact attempt. Captures full history per registration so Amel can see "I called this resident on the 3rd, they said they'd enroll; called again on the 10th, no answer." Columns: `id PK`, `registration_id FK → registrations.id`, `contacted_at TIMESTAMP`, `contacted_by TEXT` (who logged it; default 'admin' for v1), `channel TEXT` (`call` / `email` / `whatsapp` / `other`), `outcome TEXT` (`reached` / `unreachable` / `enrolled` / `not_interested`), `notes TEXT NULL`. Idempotent `CREATE TABLE IF NOT EXISTS` migration in `ensure_schema` matching the pattern at `schema.py:131–155`.
- **"Current status" of a registration** is derived from the most recent row in `outreach_log` for that registration_id (joined `MAX(contacted_at)` subquery). No denormalized "current outreach state" column on `registrations` — single source of truth lives in the log.
- Default at-risk filter: `intent IN ('enroll','event') AND (mass_save_enrolled IS NULL OR mass_save_enrolled='') AND registered_at < datetime('now','-{threshold} days')` — OR `needs_callback='yes'` regardless of age. Rows whose latest `outreach_log.outcome` is `enrolled` or `unreachable` are excluded from the default view; `reached` and `not_interested` re-surface after the threshold ages forward (the resident may need a follow-up).
- **Threshold UI (decision 4):** the default `{threshold}` is **3 days**, persisted in `settings` (key `outreach_at_risk_days`, reusing `get_setting`/`set_setting` already used for `events_to_show` at `admin.py:76`). The page header includes a small dropdown (`1 / 3 / 7 / 14 days`) that updates the setting via a tiny POST handler and reloads the page. Persistent default + immediate-feedback override in one control.
- Aging row colors driven by days-since-`registered_at`: yellow at threshold, orange at 2× threshold, red at 4× threshold (so colors auto-scale with the setting — no separate config). Matches the Bootstrap-ish conventions already present in `admin.html`'s `.tag` styles.
- Per-row affordances: `tel:`, `mailto:`, `https://wa.me/` links (WhatsApp number reused from `done.html:125`); a small **"Mark contacted" button (decision 2 — modal)** that opens a lightweight modal asking `outcome` (`reached` / `unreachable` / `enrolled` / `not_interested`), `channel` (`call` / `email` / `whatsapp` / `other`), and an optional `notes` textarea. Submitting POSTs to `/admin/outreach/log` which inserts into `outreach_log` and redirects back. Plain HTML/JS modal (no new framework) — opens via a `<dialog>` element with form-method="dialog" fallback for older browsers.
- Header summary: `X needs outreach now · Y reached awaiting enrollment · Z enrolled · W unreachable`.
- **Per-campaign rollup (decision 3 — included in v1):** bottom-of-page section `GROUP BY inviting_event_id` showing per event: invited (count of registrations with that `inviting_event_id`), registered (same count, surfaced for clarity), at-risk now (current default filter applied to the slice), reached (any `outreach_log` outcome of `reached`/`enrolled`), enrolled (`mass_save_enrolled='yes'` OR latest outcome `enrolled`). Rows with `inviting_event_id IS NULL` group into an "Organic / no campaign" bucket. Skipped only if no registrations yet have `inviting_event_id` set (graceful empty state).

## Out of scope (explicitly)

- Push notifications, SMS, email send. The dashboard surfaces who needs outreach; the actual call/text is manual via the `tel:` / `wa.me` / `mailto:` links. Automated outreach is Roadmap Area 2.
- Drop-off mid-form (resident bailed before submit) — that's Area 2's "Save Progress" / exit analytics work, requires partial-form persistence we don't have.
- Bulk actions (multi-select + mark contacted).
- Charts on the per-campaign rollup. The rollup ships as a numeric table; charts come later if Amel wants them.
- Export. Existing `.xdb` export at `/admin/export/leap_registrations` already covers data exfil; the new `outreach_log` table will round-trip with it via the existing `admin_import_xdb` flow (since `ensure_schema` creates the table).
- New auth/RBAC. Reuse `@admin_required` exactly as the rest of the admin panel does.

## Implementation choice

**Option A — sub-page at `/admin/outreach`.** The main `/admin` dashboard stays unchanged as a "raw firehose"; the outreach view is a focused tool. Doesn't touch the existing dashboard's query (which is already doing a lot), keeps the mental model clean (main page = browse, outreach page = act), and is easier to evolve independently. Trade-off accepted: one extra nav button on the admin top bar.

(Considered and rejected: a filter tab on `/admin` — conflates browse and act, makes per-row action buttons harder to add cleanly. And inline columns on `/admin` only — defeats the roadmap's "alert" goal because Amel would still have to scan 200 rows to find the at-risk ones.)

## Decisions made (2026-05-08, Amel)

1. **Schema model:** separate `outreach_log` table — multi-touch history captured per registration. Defeats the "did I lie to my dashboard?" failure mode by making the contact record the ground truth, not a stamp.
2. **"Mark contacted" UX:** modal capturing `outcome` + `channel` + optional `notes`. Slightly slower per row, but the dashboard tells the truth.
3. **Per-campaign rollup:** included in v1.
4. **At-risk threshold:** 3-day default, **with an in-page UI control to adjust** (1 / 3 / 7 / 14 days dropdown in the page header, persisted via `settings` so it sticks across sessions). Aging colors auto-scale to the threshold so no separate knob.

## Tunables — open for Anil's review on the PR

These don't fork the implementation; defaults below ship if Anil says nothing.

- **Outreach affordances per row.** `tel:` + `mailto:` + WhatsApp `wa.me/19783159255` (the public safety-net number reused from `done.html:125`). If the WhatsApp number shouldn't be reused for outbound advocate outreach (e.g., it's a one-direction inbound number), I'll drop the WhatsApp link or swap to a different number Anil provides.
- **Modal channel + outcome enums.** Channel: `call` / `email` / `whatsapp` / `other`. Outcome: `reached` / `unreachable` / `enrolled` / `not_interested`. Easy to add a fifth value either way.
- **Admin EN-only vs translated.** The existing admin panel is English-only (no `t()` calls in `admin.html`). Following that convention; if Anil wants the outreach view bilingual, easy two-key addition.
- **`needs_callback='yes'`** auto-promotes to at-risk regardless of age. (Confirmed by Amel as the default; flagged here so Anil sees the choice.)

## Test plan (sketch)

- Schema migration runs idempotently on a fresh DB and on a DB with existing registrations (no data loss).
- `/admin/outreach` requires admin login; redirects to `/admin/login` when unauth.
- Default filter excludes rows with `outreach_status IN ('contacted','enrolled','unreachable')` and rows newer than 3 days *unless* they have `needs_callback='yes'`.
- Aging colors: a row with `registered_at` 5 days ago renders yellow; 9 days renders orange; 20 days renders red.
- "Mark contacted" round-trip: click button → `last_contacted_at` is set, `outreach_status='contacted'`, row drops out of the default filter on refresh.
- `tel:`, `mailto:`, `wa.me` links render correctly with phone numbers properly formatted (existing data may have spaces/dashes — strip in the template).
- Per-campaign rollup correctly counts `at-risk` per `inviting_event_id`; rows with `inviting_event_id IS NULL` group into an "Organic / no campaign" bucket.
- EN + ES both render (admin panel today is English-only — confirm with Anil whether to translate or leave EN-only for v1).
- Mobile viewport (admin is rarely used on mobile but should at least be functional).

## Followups (separate PRs, not this one)

- Roadmap Area 2 (Engagement & Retention) — drop-off analytics, Save Progress, automated First Touch SMS/email.
- Free-text notes per registration (escalate to a separate `outreach_log` table if Anil prefers multi-touch tracking).
- Per-campaign performance charts (build on top of the `inviting_event_id` rollup once we have a few real campaigns of data).
- Email digest to Amel summarizing what's at-risk each morning (depends on having an SMTP path — also Area 2 territory).
