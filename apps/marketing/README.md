# Sentinel — Marketing

A separate, standalone frontend from [`apps/dashboard`](../dashboard) (the
Sentinel product itself). This app is Sentinel's cinematic marketing site —
it does not call the backend API and shares no component code with the
dashboard, only the brand identity (logo, Manrope, the indigo/violet
accent).

**Live**: https://sentinel-marketing-suzb.onrender.com/

The homepage is a scroll-driven narrative built with GSAP ScrollTrigger and
layered CSS/SVG composition — no 3D engine, no canvas, no meshes. It
currently renders the hero and four scroll sections (00–04, ending at
"That's why we built Sentinel"), with resource links to the GitHub
repository, the research documentation, the live product, and the demo
video.

## Stack

React 19, Vite, TypeScript, Tailwind CSS v4, GSAP (+ ScrollTrigger), Lenis
(smooth scroll), `lucide-react`.

## Structure

```
src/
  sections/     Page-level sections. Hero, MoneyMovesSection,
                SignalEmergence, TrajectorySection, and ExplainSection are
                rendered on the homepage today (see App.tsx). The
                remaining files (ProductSection, SimulateSection,
                StabilizeSection, ResponseSection, BusinessValueSection,
                TechnicalCredibilitySection, ResearchLabSection) are
                completed, previously-built sections kept on disk for
                possible reuse — not currently imported or rendered.
  scenes/       HeroScene — the hero's layered CSS/SVG visual (orbital
                field, signal markers, intelligence core).
  components/   Shared UI and visual-device components (Nav, CtaButton,
                RiskDivergence, RiskTrajectory, ProductTrajectory,
                SimulationTrajectory, SignalMarkers, OrbitalField,
                IntelligenceCore, MoneyFlowField, SmoothScrollProvider).
  hooks/        Reusable hooks (Lenis smooth-scroll, parallax, viewport
                breakpoints, reduced-motion).
  lib/          Small config/setup modules (GSAP plugin registration,
                orbital-field geometry).
  assets/       Fonts, images, and design-reference material.
```

## Local development

```bash
npm install
npm run dev      # http://localhost:5173 (or next free port)

npm run build     # tsc -b && vite build
npm run preview
npm run lint
```
