# LEAP Deliverable scope — Clarity & Content (UX Roadmap Area 3)

Pre-implementation sketch. Walk through with Anil at next sync before any code, per his "workflow design precedes coding" rule. Anchored in [LEAP_UX_Roadmap.md](LEAP_UX_Roadmap.md) §3, "The 'One-Sentence' Rule."

## Problem

The portal surfaces two energy programs whose value props sound similar to a non-expert: **Mass Save** (efficiency — use less energy) and **Lawrence Energy Choice / LEC** (supply — pay less for the energy you use). They are complementary, not alternatives. A resident skimming the program tiles can't tell them apart at a glance and may pick one when both apply, or bounce because the choice feels confusing.

The roadmap proposes a one-sentence contrast under (or attached to) the program cards:

> *"Efficiency helps you use less energy; Lawrence Energy Choice helps you pay less for the energy you use. Most families benefit from both."*

## Where program tiles currently live

- `templates/index.html:184–214` — three `.leap-tile` cards (Energy Upgrades, Small Business, Lower My Bills).
- `templates/how_can_we_help.html:173–201` — three `.help-tile` cards (Mass Save, LEC, Small Business).

Existing copy (`translations.py:229–248`):
- `help_masssave_body`: "No-cost home energy improvements through Mass Save® programs — insulation, heat pumps, thermostats, and more."
- `help_aggregation_body`: "Lawrence Energy Choice (**LEC**) is a state-approved City program that pools residents' buying power for competitive electricity rates."

Both bodies are descriptive but never draw the **efficiency vs supply** contrast.

## In scope

- Add a single mechanism — chosen from §"Implementation options" below — that delivers the one-sentence contrast.
- Both EN and ES translation keys.
- Apply to both `index.html` and `how_can_we_help.html` (same conceptual confusion exists on both pages).
- Keep existing tile bodies untouched unless the chosen mechanism explicitly replaces them.

## Out of scope

- Mass Save / LEC marketing copy revisions beyond the one-sentence contrast.
- Visual redesign of the tiles themselves (icons, layout).
- Translations for Areas 2 and 4 of the roadmap.
- Tooltips on the Small Business tile (no efficiency-vs-supply confusion there).

## Implementation options (pick one with Anil)

### A. FAQ block below the tiles

Single block under all three tiles on each page. Heading: "Which one is for me?" Body: the contrast sentence + an at-a-glance comparison.

- **Pros:** Single new translation key per page, no new CSS interaction. Most accessible — no hover/tap discovery cost. Reads like an editorial answer to the question users are asking themselves.
- **Cons:** Easy to scroll past. Visually disconnected from the tiles it's clarifying.

### B. Per-tile info disclosure (ⓘ icon → tooltip / `<details>`)

Small ⓘ icon on the Mass Save and LEC tiles. Click/tap reveals one sentence framed for that program: *"Mass Save = use less energy. Pairs with LEC, which lowers what you pay for it."*

- **Pros:** Discovery in context of the tile being read. Native `<details>`/`<summary>` keeps it accessible without JS.
- **Cons:** Two strings (one per program) to keep parallel. More CSS work. Mobile tap target needs care.

### C. Inline contrast sentence appended to each tile body

Add one short sentence to `help_masssave_body` and `help_aggregation_body`: *"… Pairs with LEC for lower supply rates."* / *"… Pairs with Mass Save to use less energy."*

- **Pros:** Zero new mechanism, zero new CSS. Smallest diff.
- **Cons:** Lengthens the tile bodies (they're already approaching the soft limit on mobile). Risks telegraph copy: every tile gestures at every other tile.

**Recommendation to walk through:** **Option A (FAQ block)**. Lowest implementation cost, single translation key pair per language, doesn't fight the existing tile copy. If Anil prefers the "answer in context" feel of a tooltip, fall back to B.

## Open questions for Anil

1. **Mechanism:** A, B, or C above?
2. **Both pages or one?** `index.html` is first-impression; `how_can_we_help.html` is intentional path-pick. The confusion exists on both, but landing-page real estate is tighter — maybe FAQ block lives only on `how_can_we_help.html` and `index.html` keeps its existing copy?
3. **"Most families benefit from both" framing** — does this match LEAP's program-eligibility messaging? If a household is over the LEAN income threshold but still eligible for LEC, the "both" framing is correct. If there's a documented "you'll only qualify for one" bucket, the framing needs softening.
4. **Spanish translation source** — translate in-house or route through the same channel that produced the existing ES strings (Ana Lopez review, per `99b4925`)?

## Test plan (sketch)

- Manual visual check on both pages, EN and ES, on desktop + mobile viewport.
- Lighthouse accessibility pass (no regressions); for Option B specifically, keyboard navigation into the disclosure.
- No automated test additions for v1 — the existing app has no UI test harness; adding one is its own deliverable.

## Followups (separate PRs, not this one)

- Roadmap Area 2 (Engagement & Retention) — drop-off analytics, Save Progress, automated First Touch.
- Roadmap Area 4 (Operational Sustainability) — Advocate dashboard for at-risk users.
- Existing tile-body length audit on mobile if Option C is chosen.
