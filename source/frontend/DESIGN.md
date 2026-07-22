<!-- DESIGN SYSTEM -->
---
version: alpha
name: Atlassian
description: "An enterprise software suite built on the Atlassian Design System with a distinctive blue (#0052CC / #0065FF) family across a white and light-gray canvas. The visual language is enterprise-serious but not corporate-cold. Used here for the On-Premises OMR operator console: dense, trust-first product UI (not a marketing/landing page)."

colors:
  primary: "#0052CC"
  on-primary: "#ffffff"
  primary-hover: "#0747A6"
  secondary: "#0065FF"
  ink: "#172B4D"
  ink-muted: "#6B778C"
  canvas: "#ffffff"
  surface-1: "#F4F5F7"
  surface-2: "#EBECF0"
  border: "#DFE1E6"
  success: "#00875A"
  warning: "#FF8B00"
  danger: "#DE350B"
  discovery: "#6554C0"

typography:
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5

spacing:
  base: 8px
  scale: [2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80]

radius:
  sm: 3px
  md: 4px
  lg: 8px
  pill: 9999px

shadows:
  card: "0 1px 1px rgba(9,30,66,0.25), 0 0 0 1px rgba(9,30,66,0.08)"
  elevated: "0 4px 8px -2px rgba(9,30,66,0.25), 0 0 0 1px rgba(9,30,66,0.08)"
  overlay: "0 8px 16px -4px rgba(9,30,66,0.25), 0 0 0 1px rgba(9,30,66,0.06)"

motion:
  duration-fast: 100ms
  duration-base: 200ms
  easing: cubic-bezier(0.23, 1, 0.32, 1)
---

## 1. Visual Theme & Atmosphere
White canvas, blue headers, color-coded status lozenges, dense information hierarchy. Unapologetically utilitarian. Optimized for operators who use it all day at an exam-processing desk.

## 2. Color System
- Primary #0052CC — primary buttons, active states, focus ring
- Interactive #0065FF — hover/focus, links
- Navy ink #172B4D — signature text color (dark navy, not true black)
- Muted #6B778C — secondary labels, metadata
- Surfaces #F4F5F7 / #EBECF0 — low-contrast surface differentiation
- Semantic: Success #00875A, Warning #FF8B00, Danger #DE350B, Discovery #6554C0

## 3. Typography
System fonts at 14px (below the conventional 16px) for data density. On Windows this resolves to Segoe UI. Navy ink over pure black reduces harshness during all-day use.

## 4. Components & Patterns
- Lozenge: pill-shaped status badge colored by status category; never rely on color alone, always show the text label.
- Two-layer card shadow: `rgba(9,30,66,0.25) + rgba(9,30,66,0.08)` for elevation.
- Inline, compact tables for lists.
- Forms: label above input, helper text optional, error text below.

## 5. Spacing & Layout
Dense. 8px base scale (down to 2px for micro-adjustments). Left-aligned content. Contained max-width for readability.

### Spacing utilities
CSS classes map to the scale: `.mt-4` = 8px, `.mb-6` = 16px, `.gap-4` = 8px, etc. Prefer utilities over inline `style` margins.

### Page hierarchy
- **Page title:** 20px / 600 weight (`page-title`)
- **Page subtitle:** 14px muted (`page-subtitle`)
- **Helper text:** 12px `#5E6C84` (`text-helper`) — improved contrast vs body-muted for labels

### Panel rhythm
- Standard panel padding: `16px 20px` (`--ads-panel-padding`)
- Max content width: `1080px` (`--ads-content-max`)

## 6. Table UX standards
- Toolbar: search left, filters center, count right (`TableToolbar`)
- Row actions: `Button variant="subtle"` for View/Review; `Button variant="danger-link"` for delete
- Pagination: always below table; page sizes 25 / 50 / 100
- Empty filtered state: inline in table body when possible

## 7. Action system
- **Primary / default / subtle / danger:** `Button` component
- **Text links:** `Button variant="link"` (replaces legacy `.link-btn`)
- **Destructive text:** `Button variant="danger-link"`

## 8. Tabs
Unified `Tabs` component with variants: `default` (page tabs), `toolbar` (table sub-tabs), `filter` (chip filters).

## 9. Motion & Interaction
Functional and quick (100-200ms). No delight animation. Honor `prefers-reduced-motion`.

## Accessibility
- Primary #0052CC on #ffffff: 6.8:1 (AAA).
- Text #172B4D on #ffffff: 18.8:1.
- Muted #6B778C on #ffffff: 4.8:1 (AA, no headroom below 14px).
- Touch targets 44x44px minimum; focus indicator 2px #0052CC, 2px offset.
- Never rely on lozenge color alone; always include the text label.

<!-- END DESIGN SYSTEM -->
