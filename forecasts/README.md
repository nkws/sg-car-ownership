# Forecast ledger

`ledger.json` is the single source of truth for the Forecasts page — Claude's
scored intel feed. Claude's scheduled tasks edit it with ordinary git commits to
`main`; the dashboard reads it, and commits Norman's optional edits back through
the GitHub API (needs `github_token` in Streamlit secrets).

## Rules

- **Claude does the forecasting.** The weekly scan gathers evidence and appends
  rows with `status: active` and its own `claude_p`. Norman does not need to act.
- Norman may optionally log `your_p` (scored alongside Claude) or dismiss a row
  (`status: rejected`). Scheduled tasks never touch `your_p`, never revive a
  rejected row, and never delete rows.
- The monthly task sets `status: resolved` + `outcome` + `outcome_source` +
  `resolved_on` on `active` rows whose `resolve_by` has passed. Claude is scored
  against `crowd_p` (prediction markets) — that comparison is the point.
- A question must resolve unambiguously from a public source by `resolve_by`.
  "AI will be big" is not a forecast; "Nvidia reports FY27 Q3 data-centre revenue
  above US$60bn" is.
- `proposed` is a legacy status, treated the same as `active`.

## Row schema

| field | type | who writes it |
|---|---|---|
| `id` | string, `YYYYMMDD-slug` | Claude |
| `status` | `active` / `resolved` / `rejected` | Claude (active, resolved), Norman (rejected) |
| `theme` | `AI & tech` / `SG equities` / `COE & cars` / `Energy` / `Staples` / `Macro` | Claude |
| `question` | string, yes/no | Claude, Norman may edit |
| `resolution` | string — exact rule and source that decides it | Claude |
| `resolve_by` | `YYYY-MM-DD` | Claude |
| `claude_p` | 0–1, Claude's own estimate | Claude |
| `crowd_p` | 0–1 or null | Claude |
| `crowd_source` | string or null (Metaculus / Polymarket / Kalshi URL) | Claude |
| `indicators` | list of strings — leading indicators behind it | Claude |
| `rationale` | string — base rate first, then the update | Claude |
| `your_p` | 0–1 or null | **Norman only, optional** |
| `your_note` | string or null | Norman |
| `created` | `YYYY-MM-DD` | Claude |
| `accepted` | `YYYY-MM-DD` or null | dashboard (date Norman logged his number) |
| `outcome` | true / false / null | Claude (monthly) |
| `outcome_source` | URL or null | Claude (monthly) |
| `resolved_on` | `YYYY-MM-DD` or null | Claude (monthly) |
