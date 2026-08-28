# Frontend Architecture

Source: [`apps/dashboard/`](../../apps/dashboard/)
Run with: `npm run dev` (see below)
Tests: `npx vitest run`

## What this is

A product UI over the backend's typed, read-only research API
(`docs/architecture/backend.md`). It renders only what the API returns —
no hardcoded merchants, risk scores, exposure, liquidity, or SHAP
drivers — and preserves the backend's observed/modeled/derived
provenance distinction all the way to the screen.

```
backend API (FastAPI, http://127.0.0.1:8010)
        │
        ▼
apps/dashboard/src/api/          typed fetch client + endpoint functions
        │
        ▼
apps/dashboard/src/hooks/         useAsync-based data hooks, per resource
        │
        ▼
apps/dashboard/src/context/       MerchantContext (selected merchant + list)
        │
        ▼
apps/dashboard/src/components/    presentational components (layout, common, overview, simulator)
        │
        ▼
apps/dashboard/src/pages/         OverviewPage / SimulatorPage compose hooks + components
```

## Stack

**React 19 + Vite 8 + TypeScript 6 + Tailwind CSS v4.** No frontend
stack existed in the pre-existing empty `apps/dashboard` scaffold, so
this was chosen for a fast, typed, low-ceremony SPA — a good fit for a
data-dense internal dashboard, not a marketing site. **recharts** for
the trajectory chart (a maintained, typed React charting library rather
than hand-rolled SVG). **oxlint** (ships with Vite's `react-ts`
template) for linting. **Vitest + @testing-library/react + jsdom** for
tests, since it shares Vite's config/transform pipeline and needs no
separate bundler setup.

**react-router-dom** for real page routing across the six enabled
screens (`/` Overview, `/risk` Risk, `/explainability` Explainability,
`/simulator` Simulator, `/incident-response` Incident Response,
`/evidence` Evidence) — added once a second real screen (the What-If
Simulator, see `docs/architecture/simulator.md`) existed; before that,
one screen didn't justify a router.

## Directory layout

```
apps/dashboard/src/
  api/
    types.ts        TypeScript interfaces mirroring every backend Pydantic schema
    client.ts        typed fetch wrapper: query building, ApiError / ApiUnavailableError
    endpoints.ts      one function per backend endpoint
  hooks/
    useAsync.ts       generic stale-request-safe async hook (request-id guard)
    useMerchants.ts, useMerchantProfile.ts, useObservations.ts,
    useRisk.ts, useExplanation.ts        thin wrappers around useAsync + an endpoint
    useRiskTrend.ts    derives a real 7-day-prior comparison via a second /risk call
    useSimulationControls.ts   useAsync wrapper around GET .../simulation/controls
    useSimulation.ts   imperative (button-triggered) POST .../simulation, not auto-run
    useInterventions.ts   useAsync wrapper around GET .../interventions
    useInterventionMemory.ts   useAsync wrapper around GET .../interventions/memory, exposes refetch()
    useRecordIntervention.ts   imperative POST .../interventions/memory
  context/
    MerchantContext.tsx   selected merchant + full merchant list, app-wide
  lib/
    format.ts          number/date/percent formatting (no currency symbol — see below)
    provenance.ts        observed/modeled/derived labels + colors, driver-direction styling
    chartUtils.ts         trailing moving average (display-only smoothing of real data)
    simulationRequest.ts  builds the simulation POST body from slider state (changed controls only)
  components/
    layout/            Sidebar, Header, AppShell, icons.tsx, navigation.ts (shared NAV_ITEMS)
    common/             ProvenanceTag, LoadingState, ErrorState, EmptyState, MetricCard, MerchantSelector
    overview/            RiskSummary (embeds ConfidenceBadge), ExposureCard, LiquidityCard, TrajectoryChart, RiskDrivers
    simulator/           SimulatorIntro, ControlSlider, ControlsPanel, SimulationResult
    incidents/           IncidentModeIntro, IncidentList, IncidentHeader, CaseSummaryCard, EvidenceChecklist, ResponsePreparation
    interventions/       InterventionIntelligence, InterventionRow, RiskMemoryPanel, RecordSimulationInMemory — see docs/architecture/intervention_intelligence.md
    assistant/           AssistantPanel, SuggestedPrompts, AssistantAnswer — see docs/architecture/ai_orchestrator.md
  pages/
    OverviewPage.tsx           composes the above for the Overview screen
    RiskPage.tsx                composes the above for the Risk screen
    ExplainabilityPage.tsx       composes the above for the Explainability screen
    SimulatorPage.tsx           composes the above for the Simulator screen
    IncidentResponsePage.tsx     composes the above for the Incident Response screen
    EvidencePage.tsx            composes the above for the Evidence screen
  test/
    setup.ts, fixtures.ts, noHardcodedData.test.ts
```

Components are presentational; data fetching lives in hooks; hooks call
`api/endpoints.ts`, never `fetch` directly. This keeps the API contract
in one place and makes components testable with mocked hook data.

## API integration

- **Base URL**: `VITE_API_BASE_URL` (see `.env.example`), read once in
  `api/client.ts`. Defaults to `http://127.0.0.1:8000` if unset.
- **Typed responses**: every backend schema in `backend/api/schemas/`
  has a matching interface in `api/types.ts`, kept in sync by hand
  (there is no live codegen step — out of scope for this task's size).
- **Errors**: `ApiError` (non-2xx HTTP response, carries `status` +
  `detail` from the backend's error body) and `ApiUnavailableError`
  (network/fetch failure — backend down or unreachable) are distinct
  types, so `ErrorState` can show a different message for "backend
  said no" vs. "backend isn't there."
- **Staleness guard**: `useAsync` tags each request with an
  incrementing id and only commits a response if it's still the latest
  request for that hook instance — switching merchants quickly can't
  let an older, slower response overwrite a newer one.

## Application shell

`AppShell` = `Sidebar` (branding, merchant context, nav) + `Header`
(current page title + selected merchant's archetype/tier +
`MerchantSelector`) + a scrollable `<main>` routed by `react-router-dom`.
Both `Sidebar` and `Header` read the same `NAV_ITEMS` list
(`components/layout/navigation.ts`) — the sidebar to render links, the
header to look up the active route's label — so the page title can never
drift out of sync with the current route. All six nav items —
**Overview**, **Risk**, **Explainability**, **Simulator**, **Incident
Response**, and **Evidence** — are enabled; there is no disabled or
"Soon" placeholder screen. There is deliberately no "Settings" entry:
no settings/preferences functionality exists anywhere in the backend
(no user accounts, no configurable state), so a disabled "Settings —
Soon" placeholder would be a dead promise rather than a real product
surface. There is also no separate "AI" nav item — the assistant
(`docs/architecture/ai_orchestrator.md`) is embedded directly on the
Overview, Simulator, and Incident Response screens instead, since no
existing placeholder for a standalone AI screen exists.

## Overview screen

`OverviewPage` fetches the selected merchant's profile first (to get
`latest_observed_snapshot.as_of_date`), then risk, explanation, and
observations in parallel. Each section owns its own loading/error state
independently — a failed `/explanation` call shows an inline error in
the Risk Drivers card without blocking the rest of the page.

- **RiskSummary** — risk state badge (Normal/Elevated) with a
  `ProvenanceTag("modeled")`, the 30-day modeled probability as a
  secondary stat (not a giant hero number), a real 7-day trend via
  `useRiskTrend`, the flag threshold, a compact **Confidence** badge
  (High/Medium/Limited, via `ConfidenceBadge` — see
  `docs/architecture/confidence_data_quality.md`; rendered only when
  `risk.data_quality` is present, since the Incident Response page's
  reused `RiskSummary` doesn't carry one), and a disclaimer that this is a
  synthetic-benchmark output, not a validated real-world probability.
- **ExposureCard** — `exposure.estimate` (tagged `derived`) as the
  primary figure, with its trailing-average methodology spelled out;
  `exposure.retrospective_actual` (tagged `observed`) shown smaller and
  only when available, explicitly labeled "benchmark only."
- **LiquidityCard** — `available_liquidity` (`observed`) and a
  `liquidity_stress` gauge (`derived`) anchored at ratio = 1.0 (exposure
  estimate equals available liquidity) — a mathematically self-evident
  reference point, not an invented severity threshold.
- **TrajectoryChart** — a `recharts` composed chart of real daily
  observations: GMV as an area (left axis) and 7-day moving averages of
  chargeback/refund rate as lines (right axis). The moving average is a
  client-side display smoothing of real values, captioned as such — not
  a new data source, and never implying observations are predictions.
- **RiskDrivers** — real SHAP output from `/explanation`: feature name
  (mechanically humanized, not LLM-generated), group, value, a
  magnitude bar, and non-causal direction language ("Contributing to
  modeled risk" / "Reducing modeled risk"), plus the backend's
  causality disclaimer footer. Shows an explicit empty state if a
  merchant has no drivers rather than fabricating any.
- **InterventionIntelligence** — the deterministic, ranked recommendation
  list from `/merchants/{id}/interventions` (priority badge, optional
  "Verified SHAP driver" badge, reason, expandable "Why this matters,"
  "Test in Simulator" deep link, "Acknowledge" action), or the honest
  empty state when nothing clears the relevance bar. See
  `docs/architecture/intervention_intelligence.md` for the full rules.
- **RiskMemoryPanel** — this merchant's Risk Memory records, newest
  first, each showing action status and an always-present "Outcome: Not
  observed" badge — or its own honest empty state when nothing has been
  recorded.
- **AssistantPanel** — embedded at the bottom of the screen; see
  "Assistant panel" below.

## Simulator screen

See `docs/architecture/simulator.md` for the full design rationale
(control selection, why sibling features aren't cascade-updated, the
exposure-scaling formula). In brief: `SimulatorPage` loads the three
controls' bounds/baseline via `useSimulationControls`, renders a slider
per control (`ControlSlider`, with a tick mark at the observed baseline),
and only includes a control in the POST body if its value differs from
baseline (`lib/simulationRequest.ts`) — "Run simulation" stays disabled
until at least one control has actually moved. `SimulationResult` shows a
prominent "MODELED IMPACT" badge, a risk-state comparison, a
current/simulated/change table, the changed controls, and the API's own
disclaimer text verbatim (never re-worded or LLM-generated). "Reset to
observed values" restores every slider to baseline and clears any prior
result; switching merchants (via the same shared `MerchantContext`) does
the same automatically. `AssistantPanel` is embedded below the result,
receiving the currently-run simulation (reconstructed from the result via
`lib/simulationRequest.ts:simulationRequestFromResult`, never a raw client
number the backend has to trust) so the assistant can explain it. When
arrived at via an Intervention Intelligence "Test in Simulator" link
(`/simulator?control=<control_id>`, read via `useSearchParams()`), the
matching `ControlSlider` gets a visual ring highlight
(`highlightedControlId`) — a UI affordance only, every control stays
independently editable. After a simulation touches exactly the one
control a currently-active recommendation names,
`RecordSimulationInMemory` offers to record that modeled result in Risk
Memory (`action_status: "simulated"`) — omitted for a multi-control
simulation or one with no matching recommendation, since there is no
single `intervention_id` to attach it to.

## Incident Response screen

See `docs/architecture/incident_response.md` for the full design. In
brief: `IncidentResponsePage` stacks a single-column layout — `IncidentList`
renders as a compact, horizontally-wrapping incident switcher across the
top (not a left-hand rail), and the full-width content below it starts
with `IncidentHeader` for the selected incident, followed by the
**same** `RiskSummary`/`ExposureCard`/`LiquidityCard`/`RiskDrivers`
components from `components/overview/` (via a thin
`IncidentDetail -> RiskResponse` type adapter, not a reimplementation),
then `CaseSummaryCard`, `EvidenceChecklist`, `ResponsePreparation`, and
`AssistantPanel` (with the selected incident threaded in as context).
`ResponsePreparation` and
`AssistantPanel` are both keyed by the incident id so switching incidents
resets their local state — an early bug caught here during live
verification was two sibling elements keyed with the *same* string
(`data.incident_id`) instead of two distinct ones, which produces a silent
React "duplicate key" warning even though only one instance of each was
rendered.

## Assistant panel

`components/assistant/AssistantPanel.tsx`, embedded on Overview, Simulator,
and Incident Response with page-appropriate suggested prompts and context
(`merchantId` always; `asOfDate` on Overview/Simulator; `incidentId` on
Incident Response; `simulation` on Simulator only, and only once a result
exists). States: suggested prompts + free-form input, loading, answer
(provenance-tag row, collapsible limitations/disclaimer, follow-up chips),
a distinct "Provider unavailable" error (mapped from the API's 503 via
`ErrorState.tsx`'s now-exported `describeError`), and a generic error
state. The response's `provider` field is always rendered — a prominent
amber "MOCK PROVIDER — not a real AI response" badge whenever it's
`"mock"` — so mock and real output can never be visually confused. See
`docs/architecture/ai_orchestrator.md` for the full backend design this
panel is a thin client for.

## Backend endpoints consumed

`/health`, `/merchants`, `/merchants/{id}`, `/merchants/{id}/observations`,
`/merchants/{id}/risk`, `/merchants/{id}/explanation`,
`/merchants/{id}/simulation/controls`, `/merchants/{id}/simulation`,
`/merchants/{id}/incidents`, `/incidents/{id}`,
`/merchants/{id}/interventions`, `/merchants/{id}/interventions/memory`
(GET and POST), `/merchants/{id}/assistant`.
(`/metadata`, `/merchants/{id}/features`, and `/incidents/{id}/evidence`
are typed in `api/types.ts` for completeness but not yet called from any
screen.)

## Design system

Defined mostly through consistent Tailwind usage rather than a separate
tokens file:

- **Typography**: Manrope (UI), JetBrains Mono (numeric/tabular figures),
  loaded via Google Fonts in `index.css`.
- **Surfaces**: near-black dark theme cards and page background, thin
  low-contrast borders, restrained shadows and a subtle purple/indigo
  accent glow on active/selected elements — no excessive gradients, no
  glassmorphism.
- **Color semantics**: slate = observed, indigo = modeled, teal =
  derived (`lib/provenance.ts`); red = elevated risk / negative driver,
  emerald/teal = normal risk / positive driver. Intervention priority
  reuses the existing amber/slate `PRIORITY_STYLE` (no red for "high"),
  and Risk Memory's `ACTION_STATUS_STYLE`/`OUTCOME_STATUS_STYLE` are
  deliberately muted — "not observed" is styled as a calm fact, never a
  warning. Colors are never reused for unrelated meanings.
- **Focus states**: a visible `:focus-visible` ring is defined globally
  in `index.css` and never removed, for keyboard accessibility.

## Accessibility

Semantic landmarks (`<main>`, `<nav>`), a native `<select>` for the
merchant picker (full keyboard support for free), disabled nav items
marked `aria-disabled`, chart data accompanied by text captions (not
chart-only information), and sufficient color contrast on all status
badges.

## Responsive behavior

Desktop/laptop is the primary target (a risk-analyst tool, used at a
desk). The layout uses flex/grid with `min-w-0`/wrapping so it degrades
reasonably on a tablet-width viewport; no dedicated mobile navigation
or touch-specific affordances were built, per the task's scope.

## No fake data

`src/test/noHardcodedData.test.ts` scans every `.ts`/`.tsx` file under
`components/`, `pages/`, `context/`, and `hooks/` for a literal
merchant-id pattern or an import of the test-only fixtures file, and
fails the suite if either appears outside `src/test/`. Mock data
(`src/test/fixtures.ts`) is shaped exactly like real backend responses
and used only in tests.

## Local development

```bash
# backend (from repo root, once artifacts are built — see docs/architecture/backend.md)
.venv/bin/python scripts/run_backend.py --port 8010

# frontend (from apps/dashboard/)
cp .env.example .env        # sets VITE_API_BASE_URL=http://127.0.0.1:8010
npm install
npm run dev                  # http://localhost:5173 (or next free port)

# checks
npx vitest run
npx tsc -b --noEmit
npm run lint
npm run build
```

## Limitations

- **No codegen**: `api/types.ts` is hand-maintained against the backend
  schemas; a backend response-shape change requires a matching manual
  edit here.
- **Six screens**: Overview, Risk, Explainability, Simulator, Incident
  Response, and Evidence are all implemented and enabled; there are no
  inert placeholder screens.
- **Bundle size**: the production build is ~650 KB (~192 KB gzipped),
  mostly `recharts`; acceptable for this tool's size, but would want
  code-splitting before adding more chart-heavy screens.
- **This is a UI over a synthetic-benchmark research prototype** — see
  `docs/architecture/backend.md`'s limitations for what the underlying
  model/data can and cannot claim; the frontend does not add any
  additional predictive claims of its own.
