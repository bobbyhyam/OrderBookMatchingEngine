---
name: file-audit-issues
description: File GitHub issues for the problems found by a security audit, security review, correctness review, or code review run earlier in this session. Use when the user asks to create, file, open, or raise GitHub issues for audit or review findings.
---

# File GitHub issues from audit findings

Turn the validated findings from the audit or review in this session into GitHub issues that a human can triage. Filing is not fixing: do not change any files.

## 1. Collect the findings

- Use the findings already produced in this session. If the audit wrote a report file, read it for exact evidence and reproductions.
- If this session contains no audit or review, ask the user for the report path. Do not run a new audit.
- File only validated findings with severity Critical, High, or Medium. List Low and informational findings in the final table as not filed.
- Merge findings that share a root cause or a single fix into one issue. Examples: a market order that rests with a null price and the dashboard crash it causes; non-finite prices and unbounded batch sizes on the same request models.

## 2. Target the right repository

- Derive `owner/repo` from `git remote get-url origin` and pass `--repo owner/repo` to every `gh` command. Never file on an upstream or parent repository.
- Run `gh issue list --repo owner/repo --state all --limit 200 --json number,title,labels,body`.
- Skip any finding already tracked by an existing issue with the same root cause or the same evidence location, even if another audit filed it. Report it as "already tracked in #N". Do not edit or comment on existing issues.

## 3. Write each issue

Title: `[High] <plain description of the problem>` or `[Medium] <...>`. Map Critical to High.

Labels, using only these existing labels (never create labels):

- `security` when an attacker or another user can exploit it (injection, XSS, missing authentication, CORS, denial of service, data exposure). Otherwise `correctness` (wrong prices, fills, lifecycle, or display).
- `severity:high` for Critical and High, `severity:medium` for Medium.
- Never add `droid-fix`. A human decides what gets fixed.

Body, with these sections in this order:

- **Summary**: one or two sentences.
- **Impact**: the consequence for a trading firm (money, market integrity, trader trust, availability).
- **Evidence**: `path/to/file.py:start-end` for each location.
- **Reproduction**: the exact request bodies, commands, or UI steps from the audit.
- **Acceptance criteria**: testable checkboxes, including a regression test. End with `Files the fix may change: ...`.
- **Out of scope**: what the fix must not change, including files owned by other issues.
- **Source**: the audit and finding ID (for example `Security audit SEC-02` or `Correctness review finding 3`).

Write each body to a temporary file and use `gh issue create --body-file`.

## 4. Repository-specific rules

- Scope each fix to one area so separate fixes do not edit the same files. Typical areas: dashboard escaping in `src/order_matching/api/static/ui.js` and `api.js`; order lifecycle in `matching_engine.py` and `order.py`; request validation in `api/models/requests.py`. If two issues must touch the same file, say so in both issues' Out of scope sections and name the other issue.
- Price or size precision (rounding, tick size): the acceptance criteria must state that the tick size policy is pending maintainer input, and Droid must not start until the maintainer has edited the issue with the policy.
- Authentication, authorization, or CORS: state in the Summary that this is an architecture decision for the team, not an automated fix.
- Vulnerable locked dependencies: one combined issue listing package, advisory, and fixed version.

## 5. Limits and order

- File at most 5 new issues per request, highest severity first, so issue numbers follow priority. List the rest as "not filed (over limit)" and offer to file them.

## 6. Report

Print a table with issue number (or "not filed"), title, labels, and source finding. Include the skipped duplicates and why each was skipped.
