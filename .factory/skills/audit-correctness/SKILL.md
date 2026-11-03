---
name: audit-correctness
description: Correctness audit of the order matching engine, REST API, and dashboard for bugs that would matter in a production trading system. Use when the user asks for a correctness audit, correctness review, or a review for trading bugs.
---

# Correctness audit

Review the matching engine and REST API in this repository for correctness bugs that would matter in a production trading system: price and size precision, the order lifecycle (market orders, partial fills, expiry, cancellation), and how the dashboard (`src/order_matching/api/static`) handles edge-case data returned by the API.

Validate every finding by reproducing it with the FastAPI TestClient (`uv run python`). Do not change any files in the repository.

For each validated finding report:

- a severity (High or Medium)
- the file and line
- the exact reproduction (request bodies or UI steps)
- the observed versus expected behaviour
- a suggested fix

Finish with a summary table. Output only the report, in Markdown.
