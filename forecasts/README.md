# Forecast ledger

`ledger.json` is the single source of truth for the Forecasts page. Claude's
scheduled tasks edit it with ordinary git commits to `main`; the dashboard reads
it and commits Norman's accept/reject/probability edits back through the GitHub
API (needs `github_token` in Streamlit secrets).

## Rules

- **Only Norman sets `your_p`, accepts, or rejects.** Scheduled tasks never touch
  `your_p`, never change `status` from `proposed`, and never delete rows.
- Scheduled tasks may: append `proposed` rows (weekly scan), and set
  `status: resolved` + `outcome` + `outcome_source` + `resolved_on` on `active`
  rows whose `resolve_by` has passed (monthly scoring).
- A question must resolve unambiguously from a public source by `resolve_by`.
  "AI will be big" is not a forecast; "Nvidia reports FY27 Q3 data-centre revenue
  above US$60bn" is.

## Row schema

| field | type | who writes it |
|---|---|---|
| `id` | string, `YYYYMMDD-slug` | Claude |
| `status` | `proposed` / `active` / `resolved` / `rejected` | Claude (proposed, resolved), Norman (active, rejected) |
| `theme` | `AI & tech` / `SG equities` / `COE & cars` / `Energy` / `Staples` / `Macro` | Claude |
| `question` | string, yes/no | Claude, Norman may edit |
| `resolution` | string — exact rule and source that decides it | Claude |
| `resolve_by` | `YYYY-MM-DD` | Claude |
| `claude_p` | 0–1, Claude's own estimate | Claude |
| `crowd_p` | 0–1 or null | Claude |
| `crowd_source` | string or null (Metaculus / Polymarket / Kalshi URL) | Claude |
| `indicators` | list of strings — leading indicators behind it | Claude |
| `rationale` | string — base rate first, then the update | Claude |
| `your_p` | 0–1 or null | **Norman only** |
| `your_note` | string or null | Norman |
| `created` | `YYYY-MM-DD` | Claude |
| `accepted` | `YYYY-MM-DD` or null | dashboard |
| `outcome` | true / false / null | Claude (monthly) |
| `outcome_source` | URL or null | Claude (monthly) |
| `resolved_on` | `YYYY-MM-DD` or null | Claude (monthly) |
