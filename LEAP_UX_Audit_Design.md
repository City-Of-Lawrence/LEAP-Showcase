# LEAP UX Audit — Design

**Date:** 2026-05-10
**Owner:** Amel Perez
**Status:** Spec — awaiting user review before plan

## Problem

The LEAP resident portal (`lean_app`, live at `lean-app.onrender.com`) has shipped the four Roadmap areas (§1 Handoff Cliff, §2 Engagement & Retention, §3 Clarity, §4 Sustainability) plus a mobile polish pass. Each shipped on its own focused PR. There has not been a single end-to-end pass that exercises **every public route at every realistic viewport width** and judges the result holistically against a consistent rubric.

This is a city-of-Lawrence platform. Public mistakes — a clipped button on a 360px Android, a missing input label on the address picker, a contrast failure on the consent text — are magnified by the audience (residents who may already be skeptical of city tech) and by the city's reputational stake.

## Goals

1. **Catch every UX regression and inconsistency** that a resident, council member, or accessibility tester would notice across every page and every realistic viewport width.
2. **Fix what's clearly wrong**, in scoped PRs Anil can review independently by concern.
3. **Document what's intentional but looks wrong** so it doesn't get re-audited in a future pass.
4. **Respect prior work.** Roadmap §1–§4 design decisions stand. UPIN-Mgmt §10's 34 invariants stand. Where a finding conflicts with a settled decision, surface it as a question, not a fix.

## Non-goals

- Redesigning the visual language. The LEAP/City brand and `base.html` foundation define the design system; this audit refines, doesn't replace.
- "Bold" design choices. The aesthetic target is competent civic design (gov.uk / USDS-style), not editorial flair.
- Backend or data-model changes. Findings that require schema/route changes get flagged for follow-up, not fixed in these PRs.
- Production-data verification. Demo data on the local instance is the substrate.
- Touching `An_notes.txt`, gitignore audit, DNS, or other open loops unrelated to UX.

## Scope

**All templates in `lean_app/templates/`** — public flow plus admin pages. ~40 templates.

**Public flow** (~30 templates): `index`, `welcome`, `welcome_back`, `address_search`, `address_street`, `address_pick`, `address_not_found`, `address_not_found_confirm`, `confirm_address`, `role`, `intent`, `choose_path`, `landlord_events`, `landlord_repeat`, `landlord_units`, `landlord_units_confirm`, `renter_login`, `returning_action`, `event_select`, `already_rsvpd`, `zombie_holding`, `contact`, `how_can_we_help`, `done`, `error`, `lec`, `start_generic`, `base`.

**Admin flow**: `admin_login`, `admin`, `admin_events`, `admin_events_PATCH`, `admin_event_form`, `admin_event_attendees`, `admin_funnel`, `admin_outreach`, `admin_settings`, `admin_import_xdb`.

**Skipped:** none. If a template can't be reached with demo data (e.g., specific zombie states), it gets a static template review as fallback and is flagged in the findings doc.

## Viewports

Nine widths, each tested at the page's natural height (no fixed mobile height — let content drive):

| Width | Why |
|------:|-----|
| 320px | Galaxy Fold cover screen, oldest realistic mobile |
| 360px | Most common Android |
| 375px | iPhone SE / mini |
| 414px | iPhone Plus / Pro Max |
| 768px | iPad portrait, tablet boundary |
| 1024px | iPad landscape, small laptop |
| 1280px | Common desktop |
| 1440px | Standard developer/office monitor |
| 1920px | Full HD desktop |

## Rubric

Four categories. Findings tagged by category in the working findings doc and split into four PRs in this order.

### 1. Responsive correctness *(PR #1)*

- No horizontal scroll at any viewport
- No clipped or truncated text on buttons, headers, labels, or content
- No content overflowing card/section boundaries
- Touch targets ≥ 44×44px on viewports ≤ 768px (WCAG 2.5.5 / Apple HIG)
- Forms remain functional and visible (no fields off-screen, labels stay attached)
- Images scale; no fixed-pixel widths that break at small viewports
- Viewport meta tag present and correct
- Breakpoints behave (no awkward intermediate widths where the layout collapses)

### 2. Visual polish & consistency *(PR #2)*

- Button styles consistent across pages (one primary, one secondary, one destructive — not five variants)
- Input/textarea/select styles consistent
- Card/section spacing rhythm consistent (likely 4/8/16/24px scale based on `base.html`)
- Typography hierarchy clear and consistent (h1/h2/h3/body sizes don't drift per template)
- Hover, focus, and active states present and visible
- Alignment: edges line up; nothing visually orphaned
- LEAP/City brand consistent (logo treatment, color usage, photo treatment)
- No AI-slop tells (generic Bootstrap-y cards, purple-gradient hero blocks, default system font stack, dropshadow-on-everything)

### 3. Accessibility *(PR #3)*

- `<label>` for every input, or `aria-label`/`aria-labelledby` when label is visual-only
- `alt` text on every meaningful image; `alt=""` on decorative
- WCAG AA color contrast: 4.5:1 for normal text, 3:1 for large text and UI components
- Visible focus indicators on every interactive element
- Keyboard reachable: every interactive element tab-able in a sensible order
- Semantic HTML: `<button>` not `<div onclick>`, `<nav>` for navigation, headings in order
- ARIA only where semantics don't carry the meaning (don't add ARIA for ARIA's sake)
- Form validation errors announced to screen readers (`aria-invalid`, `aria-describedby`, `role="alert"`)
- Language attribute on `<html>` (matters because the app has a translation system)

### 4. Copy clarity + functional UI bugs *(PR #4)*

- Typos and grammatical errors
- Inconsistent terminology (e.g., "unit number" vs. "apartment number" vs. "apt")
- Missing or unclear error messages
- Missing empty states
- Broken links
- Form validation that misfires (rejects valid input, accepts invalid)
- Dead buttons / `href="#"` placeholders
- JS console errors and warnings
- Missing assets (404s on images, fonts, CSS)
- Favicon presence and rendering

## Methodology

### Tooling

- **Playwright MCP** drives a real Chromium against the local Flask app
- **Local Flask** via `venv/Scripts/python.exe app.py` started in background, killed at end of session
- **Screenshots** saved to `lean_app/.audit-screenshots/` (gitignored — working dir only). Filename pattern: `<route>__<width>.png`
- **A11y tree** captured via Playwright `browser_snapshot` per page
- **Console errors** captured via `browser_console_messages` per page
- **Computed styles** spot-checked via `browser_evaluate` for contrast, focus rings, touch-target sizing
- **Manual a11y check**: keyboard-only navigation pass through each major flow

### Auth and demo data

- **Resident flow**: traverse with UPINs from `lean_app/Test UPINS.txt`
- **Admin flow**: log in with the demo password supplied for this session. Password is never written to disk, transcripts, screenshots, or commit messages. If a future session needs it, the user re-shares.
- **Demo DB**: `upinmgmt_render.sqlite` (Anil-managed demo data per CLAUDE.md, 2026-05-07)

### Per-page pass

For each route × each viewport (in ascending width):
1. Navigate
2. Wait for network idle
3. Screenshot full page
4. Snapshot accessibility tree
5. Capture console messages
6. Spot-check computed styles for the active rubric category
7. Record findings inline in the working findings doc, tagged with route, viewport, and rubric category

### Findings doc (working artifact)

- Path: `lean_app/LEAP_UX_Audit_Findings.md`
- Format: one section per route, subsections per finding with `[viewport]` and `[category]` tags
- **Lifecycle**: The full audit pass populates this doc *before* any fix lands. Each finding has a Status field (`open` / `fixed-in-PR#N` / `deferred` / `intentional`). PR #1 commits the populated findings doc and starts flipping responsive findings to `fixed-in-PR#1`. PRs #2–#4 each update their findings' Status. Final commit of PR #4 leaves every finding at `fixed-*`, `deferred`, or `intentional`.
- Each finding has: Description, Where (file:line), Viewport(s), Category, Severity (S0 blocker / S1 noticeable / S2 polish), Status

## Merge plan

Four units land on `master` in order under Anil's UI/UX carve-out (2026-05-07): UI/UX work merges directly to `master` without PR review. Each unit still gets its own short-lived feature branch so WIP commits don't deploy to Render, and merges in via `--no-ff` to preserve the unit boundary in history.

| # | Branch | Scope | Est. LOC |
|---|--------|-------|---------:|
| 1 | `amel/audit-responsive` | Viewport meta, breakpoints, overflow rules, touch-target sizing, layout primitives in `base.html` + per-template overrides | 300–600 |
| 2 | `amel/audit-visual-polish` | Component style consolidation, spacing/typography rhythm, hover/focus/active states, brand consistency | 300–500 |
| 3 | `amel/audit-a11y` | Labels, alt text, contrast, focus indicators, semantic markup, ARIA where warranted, lang attribute | 200–400 |
| 4 | `amel/audit-copy-bugs` | Typos, terminology consolidation, error/empty states, dead links, console errors, missing assets | 100–300 |

**Why this order:**
- Layout primitives belong in `base.html` and CSS foundations. Fixing them first means the next three passes don't fight a shifting layout.
- Polish sits on top of correct layout. Polishing first would mean re-tweaking once responsive lands.
- A11y often surfaces during the first two passes (missing labels become obvious when styling inputs), so unit #3 consolidates the rest.
- Copy and functional bugs last, when the visual layer is stable and discrepancies are easy to spot.

**Per-unit ritual** (per existing memory: `feedback_commit_pr_style.md`, modified to fit the carve-out):
- Branch first off latest `master`
- `wip:` prefix on intermediate commits; rebase into logical commits before merge
- Imperative subject lines; why-not-what in the body; no Claude attribution
- Local Flask run + manual smoke of affected flow before merge (`feedback_test_locally_before_push.md`)
- `git merge --no-ff` into `master` with a merge-commit subject summarizing the unit (e.g., `Merge branch 'amel/audit-responsive' — UX audit unit 1: responsive correctness`) and the Problem / Solution / Tradeoffs / Followups / Test Plan body in the merge message
- Push `master` after each unit merges; Render auto-deploys
- Diff size flagged at 500 LOC of merge diff, re-flagged at +200 (`feedback_pr_scope_check.md`). If a unit balloons, split as `amel/audit-<category>-public` and `amel/audit-<category>-admin` with separate merges.
- Delete feature branch after merge

## Constraints

- **§10 invariants** (`..\LEAP-UPIN-Mgmt\UPINmgmt_Technical_Context.md`): re-read before proposing any structural change. If a fix conflicts, flag as question — don't override.
- **Intentional gaps from CLAUDE.md**: the empty `mailto:` on the pause prompt stays empty until Anil supplies an Energy Advocate email. Other intentional deferrals get the same treatment — confirm before "fixing."
- **No backend/data-model changes** in these units.
- **UI/UX carve-out (Anil 2026-05-07)**: this audit is squarely UI/UX, so units merge directly to `master`. Local-test-before-push still required; Anil reviews after the fact via `git log`/GitHub.
- **Lawrence Showcase fork** (tag `v1.1-showcase-baseline`): purpose still unknown. Branches target current `master` unless Anil clarifies otherwise at next sync.

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Time: 9 widths × 40 pages × 4 categories is genuinely multi-session work | Commit and push WIP frequently; findings doc is the resumable state |
| Some routes need specific UPIN states demo data doesn't cover (`done`, `already_rsvpd`, `zombie_holding`) | Fall back to static template review; flag in findings doc |
| Visual polish is subjective | Match what `base.html` and the most-used pages establish; don't impose a new system. When in doubt, flag rather than rewrite |
| Audit reveals deep architectural issues (e.g., needs a CSS framework change) | Out of scope; flag as a follow-up project, don't try to land in these PRs |
| Sophos blocks Playwright's native deps | Playwright MCP runs out-of-process; not affected by Sophos's DllMain interception. Memory rule `feedback_sophos_native_python.md` is about Python-native deps, not the MCP server |
| Password leakage | Used inline only; never written to disk, screenshots, console logs, commits, or memory |

## Test plan

For each unit before merging to `master`:
1. Start Flask locally; smoke the touched routes on a real mobile width (375px) and a desktop width (1440px) via Playwright
2. Run the existing test suite if one exists (none currently in `lean_app/`; this audit doesn't add one)
3. Diff against `master`; verify no unintended template/CSS changes
4. Confirm findings-doc entries match the diff (every fix referenced; every flagged-as-intentional preserved)
5. Merge commit body has Problem / Solution / Tradeoffs / Followups / Test Plan

## Open questions

None at spec-approval time. If new questions arise during the audit (most likely: "is X an intentional design decision?"), they land in the findings doc as `[QUESTION]` and get answered before the corresponding PR opens.
