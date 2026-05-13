# LEAP UX Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** End-to-end UX audit of every public + admin route in `lean_app` at nine viewport widths (320 / 360 / 375 / 414 / 768 / 1024 / 1280 / 1440 / 1920), with fixes shipped in four ordered units (responsive correctness, visual polish, accessibility, copy + functional bugs).

**Architecture:** Two phases. Phase 1 is discovery — drive the local Flask app with Playwright MCP across every route × every width, write findings into a tracked markdown doc with severity and category tags. After a user-review gate, Phases 2–5 each pick up the findings tagged for their category, fix them on a short-lived feature branch, and merge to `master` via `--no-ff` under Anil's 2026-05-07 UI/UX carve-out.

**Tech Stack:** Flask 3.x, Jinja2 templates, inline CSS in `templates/base.html` (no external stylesheet — verified 2026-05-10), SQLite via `upinmgmt_render.sqlite` demo data, Playwright MCP for browser automation. Local Flask runs via `venv/Scripts/python.exe app.py` in background. No JS framework — vanilla `<script>` blocks in templates.

---

## File Structure

**Created:**

| Path | Responsibility |
|------|----------------|
| `LEAP_UX_Audit_Findings.md` | Working artifact tracked in git. One section per route. Each finding: Description, Where (file:line), Viewport(s), Category (responsive / polish / a11y / copy-bugs), Severity (S0 / S1 / S2), Status (open / fixed-in-unit-N / deferred / intentional). |
| `.audit-screenshots/` | Gitignored working dir for Playwright screenshots. Filename pattern `<route-with-slashes-as-dashes>__<width>.png`. |

**Modified:**

| Path | Likely changes |
|------|----------------|
| `.gitignore` | Add `.audit-screenshots/` entry |
| `templates/base.html` | Heaviest changes in Phase 2 (responsive) and Phase 3 (visual polish) — header CSS, breakpoint rules, focus indicators, button/input base styles. Already 464 lines; will keep additions focused. |
| `templates/*.html` (most of ~40) | Per-template fixes across all four units — added `<label>` elements, alt text, fixed overflow, typo fixes, etc. Driven by findings doc. |

---

## Phase 0 — Setup

### Task 0.1: Verify environment is ready

**Files:** none

- [ ] **Step 1: Confirm Flask venv is usable**

Run: `cd "C:/Users/amel.perez/Projects/City of Lawrence/lean_app" && venv/Scripts/python.exe -c "import flask; print(flask.__version__)"`
Expected: Flask version prints (e.g. `3.0.x`). If error, do NOT `pip install` — Sophos blocks native deps and pip is currently broken in this venv (per CLAUDE.md). Ask user how to proceed.

- [ ] **Step 2: Confirm Playwright MCP is responsive**

Run: invoke `mcp__playwright__browser_navigate` against `about:blank` and confirm no error. If error, surface to user; do not proceed.

- [ ] **Step 3: Read demo test UPINs**

Run Read on `lean_app/Test UPINS.txt`. Note at least three UPINs and which states they exercise (e.g. renter, landlord, returning). Save the list inline in the audit findings doc's preamble so resuming sessions don't have to re-discover them.

### Task 0.2: Start local Flask in background

**Files:** none

- [ ] **Step 1: Kill any stale Flask process on port 5000**

Run: `powershell -Command "Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"`
Expected: no output (no process), or process killed silently.

- [ ] **Step 2: Start Flask in background**

Run (Bash, run_in_background=true): `cd "C:/Users/amel.perez/Projects/City of Lawrence/lean_app" && venv/Scripts/python.exe app.py`
Capture the background shell ID for later teardown.

- [ ] **Step 3: Verify Flask is serving**

Run: `powershell -Command "Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/ | Select-Object -ExpandProperty StatusCode"`
Expected: `200`. If 5xx, read the background shell output to diagnose.

### Task 0.3: Add screenshots dir to gitignore

**Files:** Modify `lean_app/.gitignore`

- [ ] **Step 1: Append entry to gitignore**

Edit `.gitignore` — append at end of file:
```
# UX audit working dir (Playwright screenshots — local-only)
.audit-screenshots/
```

- [ ] **Step 2: Verify dir is ignored**

Run: `cd "C:/Users/amel.perez/Projects/City of Lawrence/lean_app" && mkdir -p .audit-screenshots && touch .audit-screenshots/.keep && git check-ignore .audit-screenshots/.keep`
Expected output: `.audit-screenshots/.keep` (means it IS ignored — `git check-ignore` prints the path when it matches).

- [ ] **Step 3: Commit gitignore change**

This is a tiny config commit, not UI/UX. Use a regular branch + merge.
```bash
git checkout -b amel/audit-gitignore
git add .gitignore
git commit -m "Ignore .audit-screenshots/ working dir

The UX audit (LEAP_UX_Audit_Design.md) generates per-route per-viewport
screenshots locally for review. They're working artifacts, not source."
git checkout master
git merge --no-ff amel/audit-gitignore -m "Merge branch 'amel/audit-gitignore'"
git branch -d amel/audit-gitignore
```

### Task 0.4: Create findings doc scaffold

**Files:** Create `lean_app/LEAP_UX_Audit_Findings.md`

- [ ] **Step 1: Write scaffold with route checklist**

```markdown
# LEAP UX Audit — Findings

**Audit date:** 2026-05-10 (in progress)
**Spec:** `LEAP_UX_Audit_Design.md`

## Session state

**Test UPINs in use:**
- [fill from Test UPINS.txt during audit]

**Admin login:** re-supplied per session, never logged.

## Route checklist

Public flow:
- [ ] `/` (index)
- [ ] `/welcome`
- [ ] `/welcome_back`
- [ ] `/address/search`
- [ ] `/address/street`
- [ ] `/address/pick`
- [ ] `/address/not-found`
- [ ] `/address/not-found-confirm`
- [ ] `/address/confirm`
- [ ] `/role`
- [ ] `/intent`
- [ ] `/choose-path`
- [ ] `/landlord/events`
- [ ] `/landlord/repeat`
- [ ] `/landlord/units`
- [ ] `/landlord/units-confirm`
- [ ] `/renter/login`
- [ ] `/returning-action`
- [ ] `/event/select`
- [ ] `/already-rsvpd`
- [ ] `/zombie-holding`
- [ ] `/contact`
- [ ] `/how-can-we-help`
- [ ] `/done`
- [ ] `/error`
- [ ] `/lec`
- [ ] `/start-generic`
- [ ] `/save-progress` (the resume-token form)

Admin:
- [ ] `/admin/login`
- [ ] `/admin/`
- [ ] `/admin/events`
- [ ] `/admin/events/<id>` (PATCH-page form)
- [ ] `/admin/event/new` or equivalent
- [ ] `/admin/event/<id>/attendees`
- [ ] `/admin/funnel`
- [ ] `/admin/outreach`
- [ ] `/admin/settings`
- [ ] `/admin/import-xdb`

## Findings

(Findings appear here as the audit progresses, grouped by route.)
```

- [ ] **Step 2: Verify routes match `routes/` files**

Run Grep for `@bp.route` or `@app.route` in `lean_app/routes/public.py` and `lean_app/routes/admin.py`. Update the checklist if URL paths don't match (template name doesn't always equal URL). Do NOT guess — verify.

### Task 0.5: Re-read §10 invariants

**Files:** none

- [ ] **Step 1: Read UPINmgmt §10**

Run Read on `C:/Users/amel.perez/Projects/City of Lawrence/LEAP-UPIN-Mgmt/UPINmgmt_Technical_Context.md`, locate §10. Note any UI-relevant invariants (e.g., specific text that must remain, flows that must not be skippable). Save a short summary to the findings doc's preamble as `## §10 UI-relevant invariants` so fix decisions can reference them quickly.

---

## Phase 1 — Audit pass

This phase visits every route at every viewport and populates findings. It is one long loop. There's no automated test; the "verification" is the populated findings doc.

### Task 1.1: Audit one route (template — repeat per route in checklist)

**Goal:** For one route, capture screenshots + a11y snapshots at all 9 widths and record findings.

**Files:** Modify `lean_app/LEAP_UX_Audit_Findings.md` (append/update findings under the route's section)

For ROUTE in the checklist (in checklist order):

- [ ] **Step 1: Navigate to ROUTE at first width (320px)**

Set viewport: `mcp__playwright__browser_resize` to 320 × 720
Navigate: `mcp__playwright__browser_navigate` to `http://127.0.0.1:5000{ROUTE}`
For auth-gated public routes: walk in via the prior route (e.g., visit `/welcome` and use a Test UPIN) before navigating to the target. For admin routes: log in via `/admin/login` once per session.

- [ ] **Step 2: Capture screenshot**

Run: `mcp__playwright__browser_take_screenshot` with `fullPage: true`, save to `.audit-screenshots/{ROUTE-as-dashes}__320.png`.

- [ ] **Step 3: Capture a11y snapshot + console**

Run: `mcp__playwright__browser_snapshot` (a11y tree) and `mcp__playwright__browser_console_messages`. Note any console errors or warnings in the findings doc under the route.

- [ ] **Step 4: Spot-check the rubric**

Use `mcp__playwright__browser_evaluate` to verify:
- `document.documentElement.scrollWidth <= window.innerWidth` (no horizontal overflow). If false, record an [S1 responsive] finding.
- For buttons/links visible in viewport: `getBoundingClientRect()` width AND height ≥ 44 at viewports ≤ 768. If any fail, record [S1 responsive].
- `document.documentElement.lang` is set. If empty, [S2 a11y].

- [ ] **Step 5: Repeat for remaining widths**

Resize to 360, 375, 414, 768, 1024, 1280, 1440, 1920 in order. For each: screenshot, snapshot, console, spot-check. Reuse the same navigation; resizing in Playwright triggers reflow without re-nav.

- [ ] **Step 6: Visual review of screenshots**

Open the 9 screenshots in a row mentally. For each, scan against the four-category rubric. Record every issue into the findings doc with this template:

```markdown
### {ROUTE}

#### Finding {N}: {short description}
- **Where:** `templates/{file}.html:{line}` (or "computed style on `selector`")
- **Viewport(s):** 320, 360, 375 (or "all", or "≤768", etc.)
- **Category:** responsive | polish | a11y | copy-bugs
- **Severity:** S0 | S1 | S2
- **Status:** open
- **Notes:** {what's wrong, why it matters, any candidate fix sketch}
```

Multiple findings per route is normal. No findings is also valid — note "No issues found" under the route header.

- [ ] **Step 7: Mark route checked**

In the route checklist at top of findings doc, change `- [ ]` to `- [x]` for ROUTE.

- [ ] **Step 8: Commit progress**

After every 5 routes (or end of work session, whichever comes first), commit the findings doc on the current audit branch (if any) or directly to a new `amel/audit-findings-wip` branch:

```bash
git checkout -B amel/audit-findings-wip
git add LEAP_UX_Audit_Findings.md
git commit -m "wip: audit findings through {last-route-checked}"
```

This branch is local-only WIP; do not merge to master yet. The findings doc gets its first merge as part of Unit 1.

### Task 1.2: Audit pass complete — review and triage findings

**Files:** `lean_app/LEAP_UX_Audit_Findings.md`

- [ ] **Step 1: Verify all routes marked checked**

Open findings doc; confirm every `- [ ]` in the route checklist is now `- [x]`. If any route was unreachable with demo data, the entry should be `- [~] unreachable — static review only` with a note explaining why.

- [ ] **Step 2: Count findings by category and severity**

Run a grep over the findings doc to count each `**Category:** X` and `**Severity:** Y`. Add a summary block at the top of the findings doc:

```markdown
## Triage summary

Total findings: {N}
By category: responsive: {a}, polish: {b}, a11y: {c}, copy-bugs: {d}
By severity: S0 (blocker): {x}, S1 (noticeable): {y}, S2 (polish): {z}
```

- [ ] **Step 3: Flag findings that conflict with §10 invariants or known-intentional gaps**

For each finding, cross-check against:
- The §10 UI-relevant invariants summary in the doc preamble
- The intentional gaps in `CLAUDE.md` (e.g., empty `mailto:` on pause prompt)

For any conflict, flip Status to `intentional` and add a `**Conflict:**` line referencing the rule.

- [ ] **Step 4: USER REVIEW GATE — pause here**

Present the populated findings doc to the user. Surface:
- Total counts
- Any S0 findings (these may want fast-tracking outside the four-unit order)
- Any finding where category/disposition was ambiguous

Wait for user to confirm: triage looks right, S0s handled (if any), and to proceed with Unit 1. Do not start Phase 2 without this confirmation.

---

## Phase 2 — Unit 1: Responsive correctness

For every finding in the doc with `**Category:** responsive` and `**Status:** open`, apply the fix workflow below. Tasks here are templated because the concrete fix list comes from Phase 1.

### Task 2.1: Branch off latest master

**Files:** none

- [ ] **Step 1: Confirm master is clean**

Run: `cd "C:/Users/amel.perez/Projects/City of Lawrence/lean_app" && git status && git log --oneline -1`
Expected: working tree clean (or only the WIP audit-findings branch); tip is the latest merge commit.

- [ ] **Step 2: Create unit branch**

Run: `git checkout -B amel/audit-responsive master`

- [ ] **Step 3: Merge WIP findings into this branch**

If `amel/audit-findings-wip` exists, replay its findings-doc commits onto `amel/audit-responsive`:
```bash
# Range syntax: ^first-wip-commit^..last-wip-commit gives the full inclusive range
git cherry-pick {first-wip-commit}^..{last-wip-commit}
# -D not -d: cherry-pick doesn't mark the source as merged
git branch -D amel/audit-findings-wip
```
The findings doc now lives on the unit branch. After Unit 1's merge to master, the doc is on master too — Units 2-4 just branch off master and the doc travels naturally.

### Task 2.2: Fix one responsive finding (template — repeat per finding)

For FINDING in findings doc where `Category: responsive` and `Status: open`:

- [ ] **Step 1: Reproduce the issue**

Resize Playwright to the affected viewport, navigate to the affected route, capture a "before" screenshot to `.audit-screenshots/{route}__{width}__before.png`. Confirm the issue is still present (the audit may be a day old; reality is source of truth).

- [ ] **Step 2: Apply the minimal fix**

Use Edit on the file:line referenced in the finding. Show the exact diff in this step. Fix scope: only the issue described. Do not chain in adjacent improvements (those have their own findings).

- [ ] **Step 3: Verify the fix**

Reload the page in Playwright (browser_navigate to same URL). Capture an "after" screenshot. Confirm: issue is gone, AND no new visual regression. Run the original spot-check (e.g., re-run the `scrollWidth <= innerWidth` check).

- [ ] **Step 4: Cross-check adjacent viewports**

If the fix touches CSS in `base.html` or shared selectors, re-screenshot the same route at the two adjacent widths (e.g., fix was at 375 → re-check 360 and 414) to make sure the fix didn't break something else.

- [ ] **Step 5: Update findings doc**

Flip the finding's `Status: open` to `Status: fixed-in-unit-1`. If the fix surfaced a new related issue, append a new finding entry.

- [ ] **Step 6: Commit**

```bash
git add {touched files} LEAP_UX_Audit_Findings.md
git commit -m "Fix {one-sentence description of the responsive issue}

{Why this is a problem; why the fix is correct; any tradeoff.}"
```

Imperative subject, why-not-what in body, no Claude attribution. One commit per logical fix (a single finding usually maps to one commit; one finding affecting 3 templates may be one commit if the change is unified, or 3 commits if independent).

### Task 2.3: Pre-merge local smoke

**Files:** none

- [ ] **Step 1: Run touched flows end-to-end in Playwright**

For each template touched in Unit 1, walk the flow it sits in at 375px AND 1440px. Watch for: console errors, broken navigation, unexpected layout shifts. Capture screenshots only if something surprises you — otherwise visual scan is enough.

- [ ] **Step 2: Findings/diff cross-check**

Confirm the findings doc and the code diff agree:
```bash
# Every file touched in the diff should appear in at least one fixed-in-unit-1 finding
git diff master --name-only amel/audit-responsive | grep -v LEAP_UX_Audit_Findings.md
```
For each file in that list, grep the findings doc for an entry whose `Where:` references it AND has `Status: fixed-in-unit-1`. If a file is touched but no finding references it, the change is undocumented — either add the finding retroactively or revert the change.

Also confirm no finding lost its trail: grep findings doc for `Status: fixed-in-unit-1` and verify each one's `Where:` file shows in the diff.

- [ ] **Step 3: Diff size check**

Run: `git diff master --stat amel/audit-responsive` and `git diff master amel/audit-responsive | wc -l`.
If logic-diff (templates + CSS, excluding findings-doc lines) exceeds 500 lines, flag to user before proceeding. If > 700, propose splitting into `amel/audit-responsive-public` and `amel/audit-responsive-admin`.

- [ ] **Step 4: Rebase intermediate WIP commits into logical units**

Run: `git rebase -i master` and squash any `wip:` commits into the substantive commits they belong to. Final history should be one commit per logical fix.

### Task 2.4: Merge Unit 1 to master

**Files:** none

- [ ] **Step 1: Merge with `--no-ff`**

```bash
git checkout master
git merge --no-ff amel/audit-responsive -m "Merge branch 'amel/audit-responsive' — UX audit unit 1: responsive correctness

Problem: full-app sweep had not been done end-to-end across the realistic
viewport range (320–1920px). Audit pass found {N} responsive issues across
{M} templates.

Solution: per-finding fixes documented in LEAP_UX_Audit_Findings.md
(status flipped from open to fixed-in-unit-1). Touched: {list of templates}.
Most changes consolidated in templates/base.html breakpoint blocks.

Tradeoffs: {anything surprising — e.g., dropped a flex-row layout in favor
of stack at narrow widths, accepted slightly more vertical space}.

Followups: {anything deferred to a later unit or out of scope}.

Test plan: local Flask + Playwright at 375 and 1440 across every touched
flow; before/after screenshots in .audit-screenshots/ for spot-check."
```

- [ ] **Step 2: Verify merge clean**

Run: `git status && git log --oneline -5`
Expected: clean working tree; merge commit is tip; unit-1 commits visible in history.

- [ ] **Step 3: Delete unit branch**

Run: `git branch -d amel/audit-responsive`

- [ ] **Step 4: Push master**

Run: `git push origin master`
Render auto-deploys; expect a 502 for ~60s. Do not push another unit during the deploy window — finish smoke-testing the deployed unit first.

- [ ] **Step 5: Verify Render deploy**

After ~90s: `powershell -Command "Invoke-WebRequest -UseBasicParsing https://lean-app.onrender.com/ | Select-Object -ExpandProperty StatusCode"`
Expected: 200. If 5xx for > 3 minutes, check Render logs (out of band).

---

## Phase 3 — Unit 2: Visual polish & consistency

Same shape as Phase 2, but for findings with `Category: polish`.

### Task 3.1: Branch off latest master

- [ ] **Step 1:** `git checkout -B amel/audit-visual-polish master`

### Task 3.2: Fix one polish finding (template — repeat per finding)

Identical shape to Task 2.2, with these differences:
- Findings filtered: `Category: polish` and `Status: open`
- Status flip: `Status: fixed-in-unit-2`
- Cross-check adjacent viewports is less critical (polish is usually width-agnostic) but still smoke at 375 and 1440 after each commit

### Task 3.3: Pre-merge local smoke

Identical to Task 2.3. Diff size threshold: 500 logic LOC.

### Task 3.4: Merge Unit 2 to master

Identical to Task 2.4. Merge commit template:

```
Merge branch 'amel/audit-visual-polish' — UX audit unit 2: visual polish

Problem: {N} polish/consistency findings from the audit (button style drift,
spacing inconsistencies, weak focus/hover states, etc.).

Solution: per-finding fixes; most consolidated into base.html shared rules.

Tradeoffs: {e.g., normalized button style means three templates lost a
slightly-distinct hover state — judged not worth the inconsistency}.

Followups: {anything punted}.

Test plan: local Flask + Playwright walkthrough; visual diff of touched
pages against the before-screenshots in .audit-screenshots/.
```

---

## Phase 4 — Unit 3: Accessibility

Same shape, `Category: a11y`.

### Task 4.1: Branch off latest master

- [ ] **Step 1:** `git checkout -B amel/audit-a11y master`

### Task 4.2: Fix one a11y finding (template — repeat per finding)

Identical to Task 2.2, with these category-specific spot-checks per finding:
- Labels: confirm `<input>` has either `<label for>`, an `aria-label`, or `aria-labelledby` pointing to a real id. Verify in Playwright via `browser_evaluate`: `document.querySelector('{selector}').labels?.length || document.querySelector('{selector}').ariaLabel || document.querySelector('{selector}').getAttribute('aria-labelledby')` is truthy.
- Alt text: `document.querySelector('img').alt !== undefined` and (for non-decorative) `.alt.length > 0`.
- Contrast: spot-check via `getComputedStyle({el}).color` and `.backgroundColor`; eyeball against WCAG ratio (4.5:1 normal, 3:1 large). For borderline cases, use a contrast-checker mental model or note as `[NEEDS_CONTRAST_VERIFY]` and skip rather than guess.
- Focus indicator: tab into the element via `mcp__playwright__browser_press_key` Tab, then `getComputedStyle(document.activeElement, ':focus-visible')`; outline or box-shadow must be ≥ 2px and have ≥ 3:1 contrast with surroundings.
- Semantic HTML: confirm `<button>` not `<div onclick>` etc. via grep over the touched template.
- `lang` attribute: confirm `<html lang>` is set (likely `en`; with translation system in play, may need to be set dynamically — check `translations.py` and `base.html`).

Status flip: `Status: fixed-in-unit-3`.

### Task 4.3: Pre-merge local smoke

Identical to 2.3 PLUS a keyboard-only pass: tab through every touched flow at 1440px. Every interactive element must be reachable and visibly focused.

### Task 4.4: Merge Unit 3 to master

Identical shape. Merge commit template:

```
Merge branch 'amel/audit-a11y' — UX audit unit 3: accessibility

Problem: {N} a11y findings (missing labels/alt, contrast, focus, semantic
HTML, lang attribute, etc.).

Solution: per-finding fixes; baseline focus indicator added in base.html;
{any global changes}.

Tradeoffs: {e.g., added aria-live region for funnel-event toasts —
slight markup overhead, screen-reader-relevant}.

Followups: full WCAG audit (this pass is the obvious-issues sweep, not a
formal conformance audit).

Test plan: local Flask + Playwright at 1440; keyboard-only tab through
every touched flow; spot-contrast checks on changed colors.
```

---

## Phase 5 — Unit 4: Copy clarity + functional UI bugs

Same shape, `Category: copy-bugs`.

### Task 5.1: Branch off latest master

- [ ] **Step 1:** `git checkout -B amel/audit-copy-bugs master`

### Task 5.2: Fix one copy-bugs finding (template — repeat per finding)

Identical to Task 2.2, with these category-specific spot-checks per finding:
- Typos & terminology: use a re-read pass after each edit; check the translation file (`translations.py`) for the same key — fix BOTH languages or surface as a translation followup.
- Broken links / dead buttons: confirm in Playwright that the link resolves (200 or 3xx to an in-app route) and the button does the documented thing. Do not "fix" a link that points to an intentional dead-end (e.g., the empty `mailto:` per CLAUDE.md).
- Console errors: re-load the route and confirm console is clean. Some warnings (e.g., favicon 404 if no favicon exists) may need a real asset, not a code fix.
- Missing assets: check `static/` for the referenced file; if absent, surface to user — sourcing or generating new assets is out of scope for this audit.

Status flip: `Status: fixed-in-unit-4`.

### Task 5.3: Pre-merge local smoke

Identical to 2.3 PLUS check that the findings doc is now fully resolved: every finding has Status `fixed-in-unit-{N}`, `deferred`, or `intentional`. No `open` findings remain. If any do, decide: fix now in Unit 4 (if in scope), or convert to `deferred` with a justification in the Notes field.

### Task 5.4: Merge Unit 4 to master

Identical shape. Merge commit template:

```
Merge branch 'amel/audit-copy-bugs' — UX audit unit 4: copy + functional bugs

Problem: {N} copy/terminology/functional findings (typos, inconsistent
labels, dead links, console errors, missing assets, etc.).

Solution: per-finding fixes; terminology consolidated for {term1}, {term2};
{any global changes}.

Tradeoffs: {e.g., chose 'unit number' over 'apartment number' for
consistency with landlord_units_confirm.html — surfaces in 4 templates}.

Followups: {missing-asset items deferred; translation gaps surfaced
separately}.

Test plan: local Flask + Playwright walk through every touched flow with
console open; visual diff of touched pages.
```

### Task 5.5: Final findings-doc state

**Files:** `lean_app/LEAP_UX_Audit_Findings.md`

- [ ] **Step 1: Update findings doc preamble with completion summary**

Add at top:
```markdown
## Audit complete

**Completed:** {YYYY-MM-DD}
**Units shipped:** 4 (`amel/audit-responsive`, `amel/audit-visual-polish`, `amel/audit-a11y`, `amel/audit-copy-bugs` — all merged to master)
**Resolution counts:** fixed: {x}, deferred: {y}, intentional: {z}
```

- [ ] **Step 2: Commit the summary update**

This is on a tiny throwaway branch since Unit 4 already merged:
```bash
git checkout -b amel/audit-final-summary
git add LEAP_UX_Audit_Findings.md
git commit -m "Mark LEAP UX audit complete"
git checkout master
git merge --no-ff amel/audit-final-summary -m "Merge branch 'amel/audit-final-summary'"
git branch -d amel/audit-final-summary
git push origin master
```

- [ ] **Step 3: Tear down**

Stop the background Flask process. Delete `.audit-screenshots/` (or leave it; gitignored either way).

---

## Self-review checklist

Engineers executing this plan should also check:
- The spec at `LEAP_UX_Audit_Design.md` for any constraint or risk not reflected in their current task
- §10 invariants before any structural change
- CLAUDE.md "intentional gaps" before "fixing" something that looks broken but isn't

## Out of scope (do not attempt in these units)

- Backend / route-logic / schema changes
- Asset creation (logos, photos, icons not already in `static/`)
- Translation gaps (surface to user instead — separate workstream)
- DNS / Render config
- The `An_notes.txt` GitHub PAT (separate security issue, flagged to Anil)
- The Lawrence Showcase fork strategy
