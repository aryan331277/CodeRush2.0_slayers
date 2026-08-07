# UI Design — Self-Evolving Autonomous Research Agent (PS AE-02)
### Codename: **Ledger** — a mission control for governed research

---

## 0. Design thesis

The hardest part of AE-02 isn't the agent — it's trust. The judges are scoring "injection resistance," "rollback tests," and "human interventions" as first-class metrics, not afterthoughts. So the UI's job is to make **governance visible at all times**, not buried in a settings tab. A researcher should be able to glance at the screen and know: *what is the agent doing right now, what did it just read, did anything try to manipulate it, and what am I being asked to approve.*

Everything below is built around one idea: **the pipeline is the navigation, and the safety layer is the pipeline.** We don't have a separate "Trust Center" page you visit occasionally — the spine that lets you move between stages *is* the audit trail.

**Reference points, deliberately not copied:** Apple's Human Interface clarity (restraint, one accent, generous whitespace), Bloomberg Terminal / oscilloscope instrumentation (data density where it earns its place), and a physical lab notebook (the paper-toned reading surfaces for anything the researcher has to actually read and judge). Not a SaaS dashboard template, not a chat bubble app.

---

## 1. Token system

### 1.1 Color

Avoid the two AI-default palettes (warm cream + terracotta serif; near-black + neon accent). This product lives half in a control room, half in a reading room — so the palette splits deliberately into a **console mode** (dark, for monitoring/execution) and a **document mode** (light, paper-toned, for anything the researcher must read closely and judge — literature, drafts, the final paper). This split is not decorative; it's a signal to the researcher's eye about which cognitive mode they're in: *watching* vs *reading*.

| Token | Hex | Use |
|---|---|---|
| `ink-900` | `#14171C` | Console base background (warm graphite, not pure black) |
| `ink-800` | `#1B1F26` | Console panel / rail surface |
| `ink-700` | `#242A33` | Elevated console cards, hovered rows |
| `paper-100` | `#F6F4EE` | Document-mode background (literature, drafts, paper preview) |
| `paper-50` | `#FCFBF8` | Document-mode elevated card / editor surface |
| `line-mid` | `#3A414D` (dark) / `#DEDACD` (paper) | Hairline borders per mode |
| `ink-text` | `#E7E9EE` | Primary text on console |
| `paper-text` | `#22201B` | Primary text on paper |
| `muted` | `#8A93A3` (dark) / `#8B8578` (paper) | Secondary text, timestamps, metadata |
| `trace-blue` | `#5B84D6` | Primary accent — live agent activity, running states, links |
| `flag-amber` | `#D98E2F` | Safety flags — injection detected, awaiting approval, warnings |
| `signal-green` | `#4C9A72` | Verified / approved / passed benchmark |
| `signal-red` | `#C05B4D` | Blocked, rollback, failed |
| `provenance-violet` | `#7C7FA6` | Source/citation tags, evidence-graph edges |

Only **one** accent (`trace-blue`) is used for "the agent is doing something." Amber, green, red are reserved *exclusively* for safety/state semantics and never used decoratively — so the moment a researcher sees amber, it means something, every time.

### 1.2 Typography — three roles, not two

| Role | Face | Where |
|---|---|---|
| **UI / Display** | *General Sans* (or Inter as fallback) | Nav, buttons, headings, panel chrome |
| **Data / Trace** | *IBM Plex Mono* | Logs, code, pseudocode, terminal output, timestamps, hashes, version tags |
| **Reading** | *Source Serif 4* | Literature excerpts, draft prose, the generated paper itself |

The serif only appears in document-mode surfaces. Its presence is itself a signal: "you are reading something the agent produced or found, not operating the system." Type scale: 12 / 13 / 15 / 18 / 24 / 32px, with the mono face always set 1px smaller than adjacent sans text at the same visual weight (mono reads larger optically).

### 1.3 Spacing, radius, motion

- 8px base grid. Panel padding 24px, card padding 16px, row padding 8–12px.
- Radius: 6px for controls, 10px for cards, 0px for the spine (it's a rule, not a card) — small, consistent, never pill-shaped. Nothing about this product should look bouncy.
- Motion budget is small and purposeful: 150ms ease-out for hover/press, 220ms for panel transitions, a single **orchestrated** page-load sequence for the initial dashboard (spine draws in top-to-bottom, ~600ms, once — never repeats). No idle ambient animation anywhere except the two explicitly-designed live indicators (§5). Reduced-motion setting collapses all of this to instant state changes.

---

## 2. App shell (persists across every page)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ⌘  Ledger        Project: "NSE Regime Alpha — v3"      ● Sandbox: live  │  ← top bar, 48px
├───────────┬────────────────────────────────────────────┬─────────────────┤
│           │                                            │                 │
│  SPINE    │              CANVAS                        │   CONTEXT PANE  │
│  (left)   │        (dynamic per stage)                 │     (right)     │
│  240px    │              flex-1                         │      340px      │
│           │                                            │                 │
├───────────┴────────────────────────────────────────────┴─────────────────┤
│  Session 04f2a1 · 3 approvals pending · last checkpoint 2 min ago         │  ← status bar, 32px
└──────────────────────────────────────────────────────────────────────────┘
```

- **Left = Spine.** Fixed. Vertical timeline of all 16 pipeline stages (grouped, see §3). This is navigation *and* the audit trail — see §5.1.
- **Center = Canvas.** The only region that changes meaningfully page to page. Console-mode (dark) for retrieval/execution stages, document-mode (paper) for drafting/paper stages.
- **Right = Context Pane.** Always answers "why is the agent doing this / what is it looking at right now." Tabs: **Reasoning** · **Sources** · **Safety Log**. Persists its tab selection across stages so a researcher tracking the injection log doesn't lose their place when they click to a new stage.
- **Status bar.** Always-visible sandbox state, pending human gates, last checkpoint — the one thing that must never require a click to discover.

---

## 3. The Spine — signature element, part 1

The spine is a single vertical rule with 16 nodes, grouped into five bands matching the pipeline's real logical structure (this grouping is informative, not decorative — it's how the researcher chunks a 16-step process into something scannable):

```
● Input                     (1)
─────────────────────────────
○ Research                  (2 Research · 3 Idea Surfacing)
  🛡 firewall active
─────────────────────────────
✓ Human Gate — Idea          (4)
● Formulation                (5 Draft · 6 Pseudocode)
✓ Human Gate — Pseudocode    (7)
○ Code                       (8 Codegen)
✓ Human Gate — Code          (9)
─────────────────────────────
◐ Execution                  (10 Run · 11 Check)
  🔒 sandboxed · no egress
↻ Rerun v2                   (12, if looping)
✓ Human Gate — Architecture  (13, if triggered)
─────────────────────────────
□ Output                     (14 Paper · 16 Non-code branch)
∞ Memory                     (15)
```

**Node states** (shape + color, never color alone — colorblind-safe):
- `○` hollow = not yet reached
- `◐` half-fill, pulsing `trace-blue` = running now (the *only* looping animation in the product — a slow 2s breathe, not a spinner)
- `✓` filled `signal-green` = human-approved gate, passed
- `✋` filled `flag-amber` = **awaiting your approval right now** — this node also appears as a persistent chip in the top bar until resolved, so it's never possible to miss
- `⚠` `flag-amber` outline = injection attempt logged at this stage (see §5.2)
- `↺` `signal-red` outline = rollback occurred here

**Hover behavior on any node:** a tooltip card slides out (paper-toned, 220ms) showing stage name, one-line description pulled straight from the problem statement's own language, timestamp if completed, and — critically — *what evidence a judge would want to see here* (e.g. hovering "Human Gate — Pseudocode" shows "Approved by you, 14:02. Diff from generated version: 2 lines."). This turns the spine into a self-documenting demo trail, which directly serves the MVD checklist (cited report, evidence map, action trace).

Clicking a completed node doesn't just navigate — it reopens that stage's canvas **as it was**, read-only, with a small "Return to live" button. This matters for a research tool: researchers need to go back and check what the agent knew when it made a decision.

---

## 4. Pages, mapped to pipeline stages

Rather than 16 literal pages, the canvas has **8 dynamic views**, because several pipeline steps share one working surface (this mirrors how a researcher actually thinks about the work, not how the backend chunks it).

### 4.1 Home / Project Dashboard
Console-mode. Grid of project cards (not a table — each card shows a miniature static spine so you can tell project state at a glance without opening it). Top-right: "New Investigation" — opens the dual-mode prompt input.

**New Investigation modal:** a single toggle, `Quick` / `Guided`. Quick is one text field, generous, placeholder in the agent's own future voice ("What do you want to know, and what may I use to find out?"). Guided expands into structured fields (question, source policies, tool permissions, budget, stop conditions) — directly matches "Core inputs" from the brief. The toggle itself is the whole point: it should feel like flipping one switch, not picking between two separate forms.

### 4.2 Research & Idea Surfacing (stages 2–3)
Console-mode, three-column *within* the canvas (this is the one page allowed to subdivide further, because retrieval is inherently parallel):
- Left sub-column: live query stream — each sub-agent's search-in-progress, monospace, ticker-style but not noisy (fades in, holds, no scroll-jitter).
- Center: **3D Evidence Graph** (three.js) — see §5.3, the signature 3D moment.
- Right sub-column: "Surfaced" feed — implementable ideas and contradictions found, each as a small card you can pin to compare later.

Every retrieved passage, wherever it's shown, carries a small provenance chip (`violet`, monospace: source · timestamp · confidence) — hovering it expands to full citation + a one-line "why this is trusted" (domain reputation, recency, cross-corroboration count).

### 4.3 Idea Selection (stage 4 — Human Gate)
Document-mode. Three cards side by side: *Follow suggested* / *Modify* / *Design your own*, each showing the idea's one-paragraph framing in serif. This is the first hard approval gate — the primary action button is deliberately the only saturated-color button on the page (`trace-blue`, filled; every other button on this screen is outline-only), so the eye can't miss where the decision actually happens.

### 4.4 Formulation (stages 5–6)
Split document/console: left half is the drafted idea in serif prose with an inline, auto-generated concept-lineage strip above it (MoE → Transformers → Efficient LLMs → Edge LLMs, rendered as a simple horizontal chain of pills, each clickable to its source). Right half is the generated pseudocode in mono, syntax-colored with restraint (two colors max: `trace-blue` for control flow, `muted` for comments).

### 4.5 Code Review (stages 7–9)
Console-mode, full-width diff view. Pseudocode → generated code shown as a real diff (additions `signal-green`-tinted background at 8% opacity, never full-saturation highlighter). Approve / Request changes buttons pinned bottom-right, always in view regardless of scroll — a human gate should never require scrolling to find the decision.

### 4.6 Execution (stages 10–13) — the console's home turf
This is the most "control room" page in the product:
- **Sandbox status bar** (own strip, not buried in the global status bar): container ID, network policy (`no egress` / `allowlist: 3 domains`), resource quota bar, session TTL countdown.
- **Live terminal**, mono, real streaming output, auto-scroll with a "jump to latest" affordance the moment you scroll up.
- **Audit log** as a slide-in drawer from the right context pane — every command run, timestamped, collapsible.
- **Result check** renders as a simple pass/fail banner, not a modal — pass routes to 4.7, fail routes into a **Rerun ledger**: a horizontal strip of version chips (`v1 v2 v3…`), each with its scorecard on hover, so a researcher can compare rerun attempts without leaving the page.
- If architecture change is required: a **full-width interrupt banner** (the one place we allow a non-node-based modal), amber, stating plainly "This fix changes the model architecture. Approve to continue, or reject to keep the current version." Rejecting is a first-class button, not a small "cancel" link — the product should never make "no" feel like the lesser option.
- If rollback triggers automatically: a red banner explains *why* in plain language ("v3 scored 0.61 vs v2's 0.74 on held-out tasks — reverted to v2") — errors state facts, never apologize.

### 4.7 Paper (stage 14) + Non-programming branch (stage 16)
Full document-mode, the calmest page in the app. LaTeX-rendered preview, serif, generous margins, looks like an actual paper — because it's the deliverable a judge will scrutinize most closely. Section-by-section outline in the left canvas rail (Intro / Lit Review / Methodology / Results / References), each section's citations hoverable inline (superscript numbers → provenance chip). A visible toggle for methodology style (defensive / vague / etc.) sits above the preview, not hidden in a menu.

The non-programming branch (theorem reasoning, physical-lab flags) renders as a distinct "Analysis" tab on this same page rather than a separate page — a flagged callout box, `flag-amber` outline, reading plainly: "This method requires physical lab validation and cannot be verified by the agent alone."

### 4.8 Memory & Safety Center
Two tabs on one page, because they're the same trust surface:
- **Long-term memory:** a decaying timeline — older runs visually fade (lower opacity, smaller type) rather than disappear, so the expiry rule is *seen*, not just logged.
- **Safety Center:** the full injection-attempt log (source, payload summary — never the raw payload rendered as if it were legitimate content, always framed in a clearly-marked quarantine card), approval history, rollback history. This page is what a judge opens to verify the injection-resistance and rollback-test criteria in under thirty seconds.

---

## 5. The two live/3D moments (spend the motion budget here, nowhere else)

### 5.1 Spine pulse
Already described in §3 — the only recurring animation, a slow breathing glow on the currently-running node. Deliberately restrained: this is what stops the console from feeling static without making it feel busy.

### 5.2 Injection flag micro-interaction
When a sub-agent hits an injected instruction inside scraped content, the relevant provenance chip briefly gets a one-time `flag-amber` outline pulse (not looping) and a small shield-slash icon appears — hovering it shows the exact instruction that was found and ignored, framed inside a quarantine card with a clear border ("Detected inside source, not executed"). This is the demo moment for MVD requirement #2 — it needs to be unmistakable on a projector from the back of a room, which is why it's the one place besides the spine that gets any motion at all.

### 5.3 Three.js Evidence Graph — signature element, part 2
Center of the Research page (§4.2). A restrained, low-poly force-directed graph: nodes = sources/claims, edges = supports / contradicts / cites. Rendered in console palette only — `ink-800` background, nodes in `provenance-violet`, edges in `muted`, contradictions rendered as a `flag-amber` edge (not a separate legend color — consistency with the rest of the system). Slow ambient auto-rotation (0.05 rad/s, pauses on hover/drag), no bloom, no particles, no neon — this should look like an instrument reading, not a screensaver. Clicking a node opens its provenance chip in the right pane. This is the one "wow" moment of the product, and it earns that role because it's also functionally the clearest way to see contradiction-tracking, which is an explicit scoring criterion.

Everywhere else, resist the temptation to add 3D — a pipeline status page, an approval gate, and a paper preview all work better flat. Three.js should read as *load-bearing*, used exactly once, not sprinkled in as texture.

---

## 6. Approval-gate pattern (used identically at every human gate)

Consistency here is what makes the product feel governed rather than merely permissioned:

1. Primary action is always the single saturated `trace-blue` button, left-aligned.
2. Reject/modify is always an outline button, same size, same row — never smaller, never gray-and-hidden.
3. A one-line plain-language summary of *what approving actually does* sits directly above the buttons ("Approving generates real code from this pseudocode and does not run it yet").
4. Every gate, once resolved, becomes a permanent, clickable entry in the spine tooltip and the Safety Center — nothing about a human decision is ever ephemeral.

---

## 7. Empty & error states

- Empty dashboard: "No investigations yet. Give the agent a question — it does the rest, with you approving every irreversible step." (Invitation to act, not decoration.)
- Failed execution: states the metric and the delta, never "Something went wrong."
- Blocked self-proposed skill (hard-mode extension): a distinct `signal-red` card in the Safety Center, permanent, reading "Agent proposed [action] outside its permitted scope. Blocked automatically." — this is a feature to display proudly, not an error to soften.

---

## 8. Accessibility & responsiveness floor

- All state communicated by shape + label in addition to color (spine glyphs above).
- Visible keyboard focus rings in `trace-blue`, 2px offset, on every interactive element including spine nodes.
- Context pane collapses to a bottom sheet under 1024px; spine collapses to icon-only rail with tap-to-expand under 768px. Canvas is the last thing to compress.
- `prefers-reduced-motion` removes the spine pulse and graph auto-rotation entirely — both fall back to a static state that still reads correctly (a solid dot instead of a pulse, a fixed graph layout instead of rotation).

---

## 9. What this deliberately avoids

- No chat-bubble transcript as the primary interface — the researcher's relationship to this tool is *supervising a process*, not *chatting with an assistant*, and the layout should say that immediately.
- No warm-cream-and-terracotta or near-black-plus-neon defaults (see §1.1's console/paper split instead).
- No decorative 3D, no particle backgrounds, no gradient mesh hero — the one 3D element is functional and appears exactly once.
- No approval buried in a dropdown, toast, or secondary menu — every human gate is full-width and impossible to scroll past unnoticed.
