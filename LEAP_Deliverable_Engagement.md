# LEAP Deliverable scope — Engagement & Retention (UX Roadmap Area 2)

Pre-implementation sketch. Anchored in [LEAP_UX_Roadmap.md](LEAP_UX_Roadmap.md) §2. Heaviest of the four roadmap areas — three distinct sub-features that almost certainly split into multiple PRs. **This is the design-only doc; walk it through with Anil before any branch is created.**

## Problem

The funnel between "resident landed on the LEAP portal" and "resident completed Mass Save enrollment" leaks at every transition the system can't see:

- **Drop-off is invisible.** A user who reaches the address picker and bails leaves no record — `registrations` rows are only inserted at `/contact` POST (`routes/public.py:864`, `:890`), so anyone who quits earlier never appears in the admin dashboard or the new outreach view. The Advocate can't proactively reach drop-offs because they're not in the dataset.
- **The system is silent after registration.** A resident who finishes `/contact` lands on `/done`, sees the bridge to Mass Save, and then nothing — no SMS, no email, no confirmation that the City actually has them. If they get cold feet on the Mass Save form ten minutes later, there's no breadcrumb back. The "black hole" feeling the roadmap names is exactly this gap.
- **Browser-close = restart.** All form state lives in Flask session. Close the tab between `/role` and `/contact`, lose everything. No way to resume.

These are three distinct workstreams hidden inside one roadmap bullet:

1. **Drop-off analytics + "Need Help?" pause prompt** — observability into the funnel + a runtime nudge.
2. **Save Progress** — persistable, resumable form state.
3. **Automated First Touch** — confirmation email/SMS on `/contact` submit so the silence never starts.

Their scope, risk, and infrastructure shape are different enough that they should ship as separate PRs in a deliberate order.

## What's already there

Almost nothing. This area is unusual in that prior LEAP work didn't lay foundation for it — most of the build is net-new.

| Capability | Current state |
|---|---|
| Email send | None. `requirements.txt` has no SMTP/email library. |
| SMS send | None. No Twilio or equivalent. |
| Analytics | None. No PostHog/Plausible/Mixpanel/GA. No server-side event log. |
| Background jobs | None. No Celery, RQ, Huey, APScheduler. |
| Form state | Flask session only — server-side cookie, lost on browser close. |
| Per-step DB write | None. Only `/contact` POST writes a `registrations` row. |
| Contact channels at point of capture | `contact_email` + `contact_phone` are captured at `/contact` (`routes/public.py:903–905`), already in the schema. |

The good news: the data we need for First Touch (email + phone) is already collected at the right step. The bad news: everything else (send infrastructure, partial-form persistence, analytics) is greenfield.

## In scope (split across three sequential PRs)

### PR-A1: Automated First Touch (recommended first)

**What:** After a successful `/contact` POST, the portal sends an immediate confirmation email and/or SMS to the contact info the resident just provided. Sets expectations: "We have you. The City of Lawrence Energy Advocate will follow up within X days. If you haven't heard from us by [date], call (978) 315-9255."

**Why first:**
- Highest user-facing impact per line of code — eliminates the "black hole" silence the roadmap names.
- Doesn't require persisting partial state or instrumenting events.
- Provider choice (email/SMS) is the only real open question; everything else falls out.
- Fits the existing post-`save_registration()` flow at `routes/public.py:903`.

**Implementation shape:**
- Add a `mailer.py` module (or inline in `helpers.py`) that wraps the chosen provider's SDK.
- Hook a single function call after `save_registration()` returns. Don't block the redirect — fire and log; if send fails, write a row to a new `outreach_log`-style table marking it pending so the Advocate can manually follow up. (We already have `outreach_log` from PR `amel/outreach-dashboard` once that lands — reuse it as a sink.)
- One translation key pair per channel for the message body (EN + ES), styled minimally.
- New env vars for provider credentials (`MAILER_API_KEY`, `MAILER_FROM_ADDRESS`, optionally `SMS_API_KEY`).

### PR-A2: Save Progress (medium scope)

**What:** Resident provides email or phone early in the funnel (probably right after `/role` selection). System emails/SMSes them a resume link with an opaque token. Closing the tab no longer loses progress; clicking the link from a later session restores their step.

**Why second, not first:**
- Depends on PR-A1's email/SMS infrastructure — no point implementing send twice.
- Adds a `partial_registrations` table (or extends `registrations` with a `is_complete` flag and writes earlier).
- Has a UX cost — adds an extra contact-info prompt early. Worth it for retention but should ship after First Touch validates the send pipeline.

**Implementation shape:**
- New table: `partial_registrations(token, contact_email, contact_phone, session_state JSON, last_step, created_at, expires_at)`.
- New early step in the funnel (probably after `/role`) that asks "Want a resume link in case you need to come back?" — opt-in, not required.
- New route: `/resume/<token>` that loads the saved state into session and routes to `last_step`.
- Token expiry policy (probably 7 days) and cleanup job (cron-style) — but no real background-job framework needed; a `DELETE FROM partial_registrations WHERE expires_at < datetime('now')` on each request is fine.

### PR-A3: Drop-off Analytics + "Need Help?" pause prompt (heaviest)

**What:** Two separate things bundled because they share infrastructure:

- **Server-side funnel event log.** New `funnel_events` table. Each route transition writes a row (`session_id`, `from_step`, `to_step`, `timestamp`, `user_agent`, optional `partial_registration_token` if PR-A2 landed). Admin gets a new view showing per-step drop-off percentages and a list of orphaned sessions (started, never reached `/contact`).
- **Client-side pause prompt.** JS that detects user inactivity on a form (no input/scroll for 30s), surfaces a modal: "Need help? Talk to an Advocate." Uses the same `tel:` / `mailto:` / `wa.me/` affordances from the outreach dashboard. No persistence needed — purely a UX nudge.

**Why last:**
- Highest implementation complexity (new event log, new admin dashboard view, JS for the pause prompt, careful instrumentation across every route).
- Lowest immediate user-facing impact — the Advocate gets visibility, but no resident gets help directly from the funnel events alone (the outreach dashboard is where action happens, and it already covers completed registrations).
- Easier to get right after PR-A2's `partial_registrations` ships, because at-risk sessions then have actual identity to attach to.

## Out of scope (explicitly)

- **Account system / login.** Save Progress uses opaque resume tokens, not accounts. The portal stays no-account by design.
- **Real-time analytics dashboards.** PR-A3 ships static views with the existing admin pattern. No streaming, no charts framework.
- **Multi-channel orchestration.** First Touch fires once after `save_registration()`. No drip campaigns, no scheduled follow-ups beyond what the outreach dashboard already prompts manually.
- **A/B testing of copy variants.** All copy ships as a single translation key per channel.
- **Internationalization beyond EN/ES.** Existing portal convention.
- **Unsubscribe management.** First Touch is transactional (confirmation of an action the user just took), not marketing — CAN-SPAM and TCPA carve-outs apply. If marketing-style outreach later, that's a separate scoping exercise.
- **In-flow "Save and finish later" button.** PR-A2's resume link is offered up front, not as a mid-flow rescue. Adding mid-flow saves doubles the UX surface for marginal lift; defer.

## Decisions Anil needs to make

These shape the implementation; defaults below ship if no answer.

1. **Email provider.** Default recommendation: **SendGrid** (free tier 100 emails/day, simple API, well-documented). Alternatives: Mailgun, AWS SES (cheapest but more setup), Postmark (best deliverability, paid). The City may have an existing relationship with a vendor — check.
2. **SMS — yes or no?** Adds a Twilio dependency (~$0.0079/SMS US) and TCPA compliance considerations. If "no" for v1, ship First Touch as email-only and revisit SMS later. If "yes," need Twilio account + an explicit opt-in checkbox on the contact form. **Recommendation: defer SMS to v2** unless Anil has a specific reason it's required from day one — email alone covers the silence problem and ships faster.
3. **First-touch send mode.** Synchronous (block the response, slow the redirect) or fire-and-forget (use `threading.Thread` or APScheduler in-process)? Recommend fire-and-forget with a 5-second timeout; if send fails, log to `outreach_log` so the Advocate sees it manually.
4. **Resume-token expiry.** 7 days is the proposed default. Long enough that a resident who got distracted has time; short enough that stale tokens don't accumulate. Adjust?
5. **Save Progress prompt placement.** "Want a resume link?" right after `/role` (one extra step) or not until after `/intent` (closer to the end, but more pre-investment to lose)? Right after `/role` is the higher-leverage placement because that's where most drop-off currently happens.
6. **Analytics event-log scope.** Just route transitions, or also explicit user actions (clicked a tile, picked an address suggestion, submitted with errors)? Start with route transitions; expand in a follow-up if a real question can't be answered without finer events.
7. **Pause-prompt threshold.** 30 seconds of inactivity? 60 seconds? Inactivity triggers a "Need help?" modal — too aggressive feels intrusive; too lenient and it never fires. Recommend 45s on form pages, never on read-only pages.

## Phasing recommendation

| Order | PR | Estimated logic-only LOC | Risk |
|---|---|---|---|
| 1 | A1 — Automated First Touch (email-only) | ~200–250 | Low — single integration point, single new module |
| 2 | A2 — Save Progress with resume tokens | ~350–450 | Medium — new table, new route, new prompt step in funnel |
| 3 | A3 — Drop-off analytics + pause prompt | ~500–700 | High — instrumentation across every route, new admin view, client-side JS for pause |

Each PR ships independently and adds value alone. If only A1 ships, the silence problem is fixed. If only A1+A2 ship, drop-off is reduced even without measurement. A3 measures the impact of A1+A2 retroactively, which is the right order — measure after a known-good baseline rather than before.

## Test plan (sketch — full plan per PR)

- **A1:** confirmation email arrives within 30s of `/contact` submit on a real address. EN + ES bodies render. Failed-send case writes a row to `outreach_log` with channel='email', outcome='unreachable'. Existing flow unaffected if email send infra is unreachable (redirect still happens, registration still saves).
- **A2:** clicking a resume link from a different browser session restores the saved step and prefills prior fields. Token expiry blocks resumption with a friendly error. Cleanup query removes expired rows.
- **A3:** funnel event log captures every route transition during a manual walkthrough. Admin view shows correct drop-off percentages. Pause prompt fires after the configured threshold and dismisses cleanly without blocking submit.

## Followups (separate scoping if requested)

- Marketing-style outreach (drip campaigns, batch emails by inviting_event_id, etc.) — this is operational outreach, not engagement-retention. Different deliverable.
- A/B testing infrastructure for copy variants.
- Real-time admin dashboard (websocket/SSE).
- SMS-based outreach if email-only A1 leaves coverage gaps.
- Multi-language expansion beyond EN/ES.
