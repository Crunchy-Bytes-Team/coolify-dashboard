# Product

## Register

product

## Users

Operators of Coolify installations use this dashboard to understand server and application CPU and RAM trends. The interface is simple and legible, resembling a system utility.

## Product Purpose

Read existing Sentinel metrics over authenticated HTTPS, retain them in SQLite, and make server load and individual application consumption easy to compare. Docker Compose runs the dashboard and collection on a workstation or private server. Collection does not use SSH and can catch up after reconnecting within Sentinel's available history.

## Brand Personality

Essential, legible, practical. Italian and English interface, familiar controls, clear units and timestamps. Respect the browser's language initially and keep an explicit language selector with a saved preference.

## Anti-references

Avoid dense Grafana-style controls, ornamental marketing layouts, fake live readings, and green health indicators for missing data. No additional anti-references were requested.

## Design Principles

- Show data freshness beside every reading.
- Keep server totals distinct from container consumption.
- Display unavailable samples as gaps, never zeroes.
- Keep credentials and infrastructure configuration outside browser responses.
- Explain the next setup step when a gateway is not yet connected.

## Accessibility & Inclusion

Support keyboard navigation, good contrast, and status text that does not depend on color. Use semantic HTML, visible focus, reduced motion support, and chart summaries in text.
