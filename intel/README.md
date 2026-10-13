# Sector intel briefs

`briefs.json` holds Claude's weekly sector intel briefs, newest first. The Intel
page renders it; Claude's scheduled tasks are the only writers.

This is decision support, not advice: no buy/sell calls, no price targets.
Each section gives the evidence, first- and second-order effects, an evidence
lean, the factual price levels that matter, and what would flip the read.

## Rules for the weekly task

- One brief per run, prepended to `briefs`. Never edit a previous brief except
  its `result` fields (monthly task only).
- Cover all six themes when there is something real to say: `AI & tech`,
  `SG equities`, `COE & cars`, `Energy`, `Staples`, `Macro`. Energy and Staples
  get a global and an SG read. Skip a theme with one line in `quiet` rather than pad.
- Separate `evidence` (things you can point to: filings, official data, prices)
  from `consensus` (what the market or commentators broadly believe, repeated
  rather than verified). Norman wants that split explicit.
- `levels` are facts from price data: last close, recent support/resistance,
  52-week range. `your_band` only if Norman's own framework states one.
- `benchmark` is the instrument the lean is scored against; record its price at
  publish so the 3-month check is mechanical.

## Section schema (`briefs[].sections[]`)

| field | type |
|---|---|
| `theme` | one of the six themes |
| `region` | `Global` / `SG` |
| `headline` | one line |
| `what_happened` | list of `{text, source}` (source = URL) |
| `first_order` | string — direct impact on this sector |
| `second_order` | list of `{sector, effect, direction}` — direction `up` / `down` / `mixed` |
| `lean` | `bullish` / `bearish` / `mixed` |
| `strength` | `weak` / `moderate` / `strong` |
| `evidence` | list of strings |
| `consensus` | list of strings |
| `levels` | list of `{name, ticker, last, support, resistance, low_52w, high_52w, your_band}` (numbers or null) |
| `flip_if` | string — what would change the read |
| `benchmark` | `{name, ticker, price_at_publish}` |
| `check_on` | `YYYY-MM-DD`, publish date + 91 days |
| `result` | null until checked, then `{price_at_check, return_pct, verdict, source}` — verdict `right` / `wrong` / `flat` / `unscored` |

Scoring: a bullish lean is `right` if the benchmark returns more than +2% by
`check_on`, `wrong` if below −2%, `flat` in between; bearish is the mirror;
`mixed` is `unscored`. Absolute return, not relative to the market — crude, and
labelled as such on the page.

Brief-level fields: `date` (`YYYY-MM-DD`), `summary` (3–5 lines: the week's
biggest cross-sector story), `quiet` (list of themes with nothing scoreable).
