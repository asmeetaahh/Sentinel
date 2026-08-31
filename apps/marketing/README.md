# Sentinel — Marketing

A separate, standalone frontend from [`apps/dashboard`](../dashboard) (the
Sentinel product itself). This app is Sentinel's cinematic marketing
experience — it does not call the backend API and shares no component code
with the dashboard, only the brand identity (logo, Manrope, the indigo/
violet accent).

**Current status: foundation only.** No marketing sections exist yet — see
`src/App.tsx` for the infrastructure smoke test currently rendered in their
place, and `src/sections/` (empty) for where they will live.

## Stack

React 19, Vite, TypeScript, Tailwind CSS v4, Three.js, `@react-three/fiber`
+ `@react-three/drei`, GSAP (+ ScrollTrigger), Lenis (smooth scroll),
`lucide-react`.

## Structure

```
src/
  sections/     Page-level sections (Problem, Blind Spot, Sentinel,
                Intelligence Loop, Business Value, Differentiation,
                Technical Credibility, Research Lab, Future, CTA) — empty,
                built in later tasks.
  scenes/       Three.js / @react-three/fiber scenes, one per file. Used
                selectively — only where spatial/interactive visualization
                genuinely helps (risk trajectories, the intelligence loop,
                the transaction- vs. merchant-level gap, the Research Lab),
                not on every section.
  components/   Shared UI (non-3D) components.
  hooks/        Reusable hooks (e.g. the Lenis smooth-scroll hook).
  lib/          Small config/setup modules (e.g. GSAP plugin registration).
  assets/       Fonts and images.
```

## Local development

```bash
npm install
npm run dev      # http://localhost:5173 (or next free port)

npm run build     # tsc -b && vite build
npm run preview
npm run lint
```
