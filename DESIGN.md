# Design System: Jarvis 2.0 Sci-Fi HUD Dashboard

## 1. Visual Theme & Atmosphere
A high-density, asymmetric tactical cockpit interface inspired by sci-fi holographic head-up displays (HUDs). The design features micro-borders, glowing telemetry overlays, and real-time interactive widgets. The mood is highly technical and precise, but polished with premium, ultra-fine typography and spring-physics active states.

*   **Density:** Cockpit Dense (9/10) — high information density, tabular diagnostic stats, and clear telemetry blocks.
*   **Variance:** Offset Asymmetric (8/10) — grid layout with offset sidebar panels, detailed diagnostic overlays, and a prominent center HUD widget.
*   **Motion:** Kinetic (8/10) — perpetual pulsar rings, rotating loader status indicators, and micro-animations animating via hardware-accelerated transforms.

---

## 2. Color Palette & Roles
*   **Canvas Black:** `#030712` (Primary deep-space background)
*   **Pure Surface:** `#0b0f19` (Glassmorphic cards, widgets, and sidebars)
*   **Hologram Cyan:** `#06b6d4` (Primary accent color for active recording states, waveforms, and highlight outlines)
*   **Laser Amber:** `#f59e0b` (Secondary accent for warning/processing states)
*   **Pulsar Rose:** `#f43f5e` (Alert states, active voice logging, and system terminations)
*   **Diagnostic Slate:** `#1f2937` (Subtle 1px panel boundaries and visual grids)
*   **Telemetry Grey:** `#9ca3af` (Secondary text, descriptions, and metric labels)
*   **Holographic Ink:** `#f9fafb` (Primary text and high-contrast numbers)

---

## 3. Typography Rules
*   **Display & Headers:** `Satoshi` or `Geist` — Track-tight, controlled scale, uppercase with letter-spacing (`tracking-widest`).
*   **Body & Descriptions:** `Geist` — Standard text, 65ch max-width, secondary telemetry color.
*   **Mono & Metrics:** `JetBrains Mono` — Bounded numerical arrays, diagnostic stats, log readouts, and timestamps to prevent layout-shifting.
*   **Banned Fonts:** `Inter` is strictly BANNED. Serif fonts are strictly BANNED.

---

## 4. Component Stylings
*   **HUD Controls:** Rounded corners of `0.75rem` (12px). 1px solid borders in `Diagnostic Slate`. Flat layout with no heavy gradients.
*   **Pulsar Button:** Circular mic trigger with multi-layered glowing shadow rings in `Hologram Cyan` or `Pulsar Rose`.
*   **Telemetry Cards:** Backdrop blur (`backdrop-blur-md`) with semi-transparent fills (`bg-[#0b0f19]/80`). Custom glowing borders in `Hologram Cyan` on active state.
*   **System Status indicators:** Dot indicators with infinite pulse loops.
*   **Skeletal Loaders:** Pulsing grid lines matching layout dimensions. No generic spinning wheels.

---

## 5. Layout Principles
*   **Grid HUD Structure:** 12-column grid layout with nested border-top split columns and asymmetric sidebars.
*   **Negative Space:** Micro-padding (`p-2` to `p-4`) to accommodate rich technical readouts.
*   **Full-height HUD Canvas:** Container height constrained using `min-h-[100dvh]` to fit viewport perfectly.

---

## 6. Motion & Interaction
*   **Pulsar Rings:** Infinite scale/opacity loop for active microphone levels.
*   **Staggered Loading:** Diagnostic cards waterfall-fade into view when loading history.
*   **Hardware Acceleration:** All animations restricted to `transform` and `opacity` properties to prevent CPU layout reflows.

---

## 7. Anti-Patterns (Banned AI Tells)
*   No emojis anywhere in labels or buttons.
*   No pure black (`#000000`) for surfaces or canvases.
*   No oversaturated neon gradients or purple glows.
*   No generic card layouts.
*   No fake placeholder values — use real metrics or clear `[diagnostic]` labels.
