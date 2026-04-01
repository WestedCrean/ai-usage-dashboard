# Frontend Styling Research: Neumorphism + Frosted Glass

## Design Philosophy

The dashboard uses a **hybrid** approach:
- **Neumorphism** for base UI surfaces (stat cards, buttons, inputs) on solid backgrounds
- **Glassmorphism (frosted glass)** for overlay elements (filter panels, modals, dropdowns)

This combination gives depth and tactility to primary content while making contextual overlays feel light and non-intrusive.

---

## Color Palette

```
Background:   #f0f4f8  (soft blue-gray base — matches both styles)
Surface:      #e8edf5  (cards on solid bg)
Text/Dark:    #1a2942  (primary text)
Text/Mid:     #4a5f7f  (secondary text)
Text/Muted:   #7a8fb5  (labels, captions)

Accent Indigo:  #6366f1
Accent Purple:  #8b5cf6
Accent Emerald: #10b981  (success / positive delta)
Accent Amber:   #f59e0b  (warning)
Accent Rose:    #ef4444  (danger / negative delta)

Neo shadow light: #ffffff
Neo shadow dark:  #a8b9d1
```

---

## Neumorphism

### Concept
Elements appear to extrude from or press into the background. The key is two `box-shadow` layers from the same base hue — one lighter (top-left highlight) and one darker (bottom-right shadow).

### Key CSS
```css
/* Raised card */
.neo-card {
  background: #e8edf5;
  border-radius: 20px;
  box-shadow:
    -5px -5px 12px #ffffff,
     5px  5px 12px #a8b9d1;
}

/* Inset input */
.neo-input {
  background: #e8edf5;
  border-radius: 12px;
  border: none;
  box-shadow:
    inset -3px -3px 7px #ffffff,
    inset  3px  3px 7px #a8b9d1;
}

/* Active / pressed button */
.neo-btn:active {
  box-shadow:
    inset -2px -2px 5px #ffffff,
    inset  2px  2px 5px #a8b9d1;
}
```

### Tailwind Custom Shadows
```js
// tailwind.config.js
boxShadow: {
  'neo':        '-5px -5px 12px #fff, 5px 5px 12px #a8b9d1',
  'neo-sm':     '-3px -3px 7px #fff, 3px 3px 7px #a8b9d1',
  'neo-inset':  'inset -3px -3px 7px #fff, inset 3px 3px 7px #a8b9d1',
  'neo-press':  'inset -2px -2px 5px #fff, inset 2px 2px 5px #a8b9d1',
}
```

### Accessibility
- Use `prefers-contrast: more` to deepen shadow values
- Ensure text meets WCAG AA (4.5:1) — dark text on light neo surfaces is safe
- Keep `transition: box-shadow 150ms ease` for interactive states

---

## Glassmorphism (Frosted Glass)

### Concept
Elements appear as translucent frosted glass panels layered over a colourful or blurred background. Requires a visually interesting backdrop.

### Key CSS
```css
.glass-card {
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);  /* Safari */
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 16px;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.12),
    inset 1px 1px 0 rgba(255, 255, 255, 0.28);
}
```

### Fallback (browsers without backdrop-filter)
```css
@supports not (backdrop-filter: blur(1px)) {
  .glass-card {
    background: rgba(240, 244, 248, 0.92);
  }
}
```

### Browser Support
| Browser       | Support       |
|---------------|---------------|
| Chrome 76+    | Full          |
| Firefox 103+  | Full          |
| Safari 9+     | Full (prefixed)|
| Edge 79+      | Full          |
| IE 11         | None (fallback)|

---

## Combining Both — Usage Map

| Element              | Style          | Why                                        |
|----------------------|----------------|--------------------------------------------|
| Stat cards           | Neumorphic     | Tactile, prominent, on solid bg            |
| Chart containers     | Neumorphic     | Consistent primary content area            |
| Buttons (primary)    | Neumorphic     | Clear interactive affordance               |
| Form inputs          | Neo inset      | Recessed = "fill me in"                    |
| Filter side panel    | Glass          | Slides over content, needs to feel light   |
| Modals               | Glass          | Overlay context, blurs background          |
| Dropdown menus       | Glass          | Floating, non-disruptive                   |
| Nav/header           | Glass          | Sticky, needs to show content underneath   |
| Tooltips             | Glass          | Tiny floating overlays                     |

---

## Background Gradient (makes glass pop)

```css
body {
  background: linear-gradient(135deg,
    #667eea 0%,    /* indigo */
    #764ba2 40%,   /* purple */
    #f093fb 100%   /* soft pink */
  );
  min-height: 100vh;
}

/* Or, for the main dashboard area behind neumorphic content: */
.dashboard-bg {
  background: #f0f4f8;
}
```

For the dashboard: use the soft `#f0f4f8` body + neumorphic cards for main content, then activate the gradient + glass effect only for modals/sidepanels by using a backdrop overlay.

---

## Tech Stack Decisions

| Decision           | Choice           | Reason                                    |
|--------------------|------------------|-------------------------------------------|
| Framework          | React 18 + Vite  | Fast DX, HMR, small bundles               |
| Styling            | Tailwind CSS v3  | Utility-first, treeshaken, easy custom    |
| Charts             | Recharts         | React-native, composable, Tailwind-friendly|
| Data fetching      | TanStack Query   | Caching, loading states, error handling   |
| Icons              | Lucide React     | Consistent, lightweight                   |
| Date handling      | date-fns         | Lightweight, modular                      |

---

## Component Architecture

```
src/
  components/
    ui/               ← primitives (Button, Card, Badge, Input, Select)
    layout/           ← Header, Sidebar, Layout
    dashboard/        ← StatCard, ChartCard, FilterPanel
    charts/           ← UsageLineChart, CostBarChart, ModelPieChart
  hooks/
    useUsage.js       ← TanStack Query hooks for /api/v1/usage
    useModels.js
    useProjects.js
    useFilters.js
  pages/
    DashboardPage.jsx
  lib/
    api.js            ← fetch wrapper for backend
    formatters.js     ← number/currency/date formatting
```

---

## Key Tailwind Classes Reference

```
Neumorphic card:    rounded-2xl bg-[#e8edf5] shadow-neo p-6
Neumorphic btn:     rounded-full shadow-neo active:shadow-neo-press transition-shadow
Inset input:        rounded-xl shadow-neo-inset bg-[#e8edf5] px-4 py-2.5

Glass card:         rounded-2xl bg-white/[0.14] backdrop-blur-xl border border-white/20 shadow-glass
Glass btn:          rounded-xl bg-white/20 backdrop-blur-md border border-white/30 hover:bg-white/25
Glass input:        rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white
```
