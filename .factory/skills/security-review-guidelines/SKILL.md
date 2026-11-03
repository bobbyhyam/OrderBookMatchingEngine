---
name: security-review-guidelines
description: Repository-specific security review rules for the order matching engine.
---

Treat this repository as an internal trading system used by traders on a shared dashboard.

- Any API field rendered into the dashboard without escaping (`innerHTML`, inline `onclick`, HTML attributes) is High: it lets one trader run script in every other trader's browser.
- State-changing endpoints (`/place`, `/match`, `/reset`, `DELETE /orders/{id}`) without authentication are Critical in a production context.
- Silent loss of monetary precision (rounding prices or sizes without rejecting the request) must be reported as a correctness and integrity finding.
- Unbounded request sizes or field lengths on order endpoints are Medium (denial of service).
- Do not report findings in `benchmark.sh`, `docs_src/`, or `openspec/`.
