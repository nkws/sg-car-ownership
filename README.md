# Singapore Car Ownership — Affordability, COE & Decision Hurdle Index

A personal decision-support tool for one question: **when and whether should my
household buy a car in Singapore?** It pulls public data (LTA COE results, DOS
household income, MAS hire-purchase credit, HDB/URA carparks, CPF wages),
models the cost and stress of ownership, and turns it into a single buy / wait /
proceed call.

## What it does

- **Decision Hurdle Index (DHI)** — the headline score. Unlike a pure financial
  stress measure, it asks *how high is the bar to confidently buy now*, blending
  four hurdles (affordability, market timing, commitment/liquidity, policy
  uncertainty) offset by the **urgency** of waiting (e.g. the EEAI EV-rebate
  cliff). See `models/decision_index.py`.
- **Financial Stress Index (FSI)** — the macro financial-difficulty pillar that
  feeds the DHI's affordability hurdle (`models/fsi.py`).
- **Home briefing** — verdict, latest COE round vs the buy trigger, countdowns
  to the next bidding round and the buying window, thesis health, live alerts.
- **COE dashboard** — premium history, tipping-point detection, affordability
  segmentation, calculators (cost, 10-year waterfall, own-vs-ride-hail, EEAI
  cliff, renew-vs-buy, cost-of-waiting), stress tests, and the FSI backtester.
- **COE Outlook** — the structural "coming dip" thesis with a buying-window call
  and a self-auditing thesis-health panel.

## Setup

```bash
pip install -r requirements.txt
python3 run_pipeline.py        # fetch data → SQLite + data/fsi_signal.json
streamlit run app.py           # or ./start_dashboard.sh
```

The pipeline falls back to bundled/synthetic data when the live sources are
unreachable, so the app always renders.

## Daily alerts (optional)

`.github/workflows/daily-pipeline.yml` runs the pipeline daily and calls
`outputs/notify.py`, which messages you when something actionable changes (an
FSI alert appears, Cat A closes below the buy trigger, or the stress band
shifts). It only sends on a *change* from the last run.

To enable Telegram, set two repository secrets:

| Secret | Value |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | from @BotFather |
| `TELEGRAM_CHAT_ID` | your chat/channel id |

Without them, the notify step runs log-only (prints what it would send).

## Project layout

```
app.py                  Multi-page entry (Home · COE · COE Outlook)
dashboard.py            COE dashboard page (header + tabs)
app_pages/              Shared page modules
  home.py                 daily briefing
  coe_outlook.py          structural thesis page
  profile_state.py        sidebar profile (shared session state)
  data_access.py          cached SQLite/JSON loaders
  verdict_panel.py        DHI verdict panel (shared)
  coe_calendar.py         bidding-round / window date math
  styles.py               shared CSS
  sections/calculator.py  EEAI-cliff, renew-vs-buy, cost-of-waiting
models/                 decision_index, verdict, fsi, ratio_model, …
collectors/             data.gov.sg / LTA / DOS / MAS / CPF fetchers
analysis/               coe_market thesis, policy_radar
outputs/                notify.py (alerts), sheets.py (export)
tests/                  pytest unit tests for the pure logic
```

## Tests

```bash
python3 -m pytest
```

Covers the decision rule, DHI hurdles, flat-rate→EIR math, EV rebates, and the
bidding calendar.

---

*Heuristic tool, not financial advice.*
