# Design

## Scene and theme

A developer checks infrastructure on the same Mac used for daytime work, with the dashboard beside other native applications. A quiet light surface and system typography make brief checks legible; follow the system dark preference for evening use.

## Palette

Restrained, lightly green-tinted neutral surfaces. A muted green accent marks selection and fresh data; amber and red always accompany text. CPU uses green, memory uses blue with explicit labels.

## Typography

System sans-serif. Body 14px, labels 12px, section titles 20px, page title 30px. Tabular numerals for readings. No remote font dependency.

## Layout and components

A compact header, server navigation, a chronological detail workspace with two charts, and an application table. Minimal full borders and generous whitespace. Filter controls remain native and labelled. Collapse to a single column on narrow screens. No nested cards or decorative animation.

## States

Distinct unconfigured, loading, collecting, fresh, stale, unavailable, and error states. Explicit last sample times and historical ranges. Zero only represents a collected zero. No simulated production data.

## Server sidebar

Use two native exclusive accordions, “Server” expanded and “Progetti” collapsed on initial load. Group project resources with their server names and direct links to the existing detail view. Preserve the user's accordion state during refreshes.

Show CPU and host RAM as percentages. RAM uses the total from the same Sentinel sample; keep byte units in charts and application tables. Highlight fresh server readings in orange at CPU or RAM ≥ 80%, with the text “Utilizzo elevato”. Keep the selected state distinguishable and never flag stale or unavailable readings as current high usage. The tooltip retains used/total memory in byte units.

## Alarms

A collapsible panel holds global server thresholds, optional resource rules, browser/audio activation and a test action. Default thresholds are 80% for server CPU/RAM over 30 seconds, repeating every 5 minutes. Resource memory thresholds use MiB. Daily quiet hours default to 00:00–06:00 in the browser's local timezone, with configurable times and a manual override. Quiet hours silence both delivery channels while retaining the visual status. Clearly disclose permissions, page-open requirements and background timing limitations.

## Language

Use a native language select in the header with the autonyms Italiano and English.
Switch static and dynamic labels, accessible names, notifications, dates and numbers
without reloading the page or resetting input drafts. Keep infrastructure names and
time zones unchanged. Follow the browser language on first visit, falling back to
English, and persist explicit choices separately from alert settings.
