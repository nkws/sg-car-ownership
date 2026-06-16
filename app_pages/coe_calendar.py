"""COE bidding calendar helpers.

LTA runs two COE bidding exercises a month: the 1st and 3rd Mondays, each
closing the following Wednesday. These helpers compute the next exercise and
the distance to the thesis buying window so the Home page can show live
countdowns. Pure date math — no I/O.
"""

from __future__ import annotations

from datetime import date, timedelta

from config import POLICY_CLIFFS


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th (1-based) given weekday of a month. weekday: Mon=0 … Sun=6."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + (n - 1) * 7)


def next_bidding_round(today: date | None = None) -> dict:
    """Return the next bidding exercise: {date, label, days_until}.

    Exercises open on the 1st and 3rd Mondays of each month.
    """
    today = today or date.today()
    candidates: list[date] = []
    # This month and next, to handle month-end wrap.
    for delta in (0, 1):
        y = today.year + (today.month - 1 + delta) // 12
        m = (today.month - 1 + delta) % 12 + 1
        candidates.append(_nth_weekday(y, m, 0, 1))  # 1st Monday
        candidates.append(_nth_weekday(y, m, 0, 3))  # 3rd Monday

    upcoming = sorted(d for d in candidates if d >= today)
    nxt = upcoming[0]
    which = "Round 1" if nxt == _nth_weekday(nxt.year, nxt.month, 0, 1) else "Round 2"
    return {
        "date": nxt,
        "label": f"{nxt.strftime('%b %Y')} {which}",
        "days_until": (nxt - today).days,
    }


def buying_window_status(today: date | None = None) -> dict:
    """Where today sits relative to the thesis buying window.

    Returns {state, days, open, close} where state is one of
    'before' | 'open' | 'after' and ``days`` is days until open (before) or
    until close (open).
    """
    today = today or date.today()
    open_d = date.fromisoformat(POLICY_CLIFFS["buying_window_open"])
    close_d = date.fromisoformat(POLICY_CLIFFS["buying_window_close"])

    if today < open_d:
        state, days = "before", (open_d - today).days
    elif today <= close_d:
        state, days = "open", (close_d - today).days
    else:
        state, days = "after", (today - close_d).days
    return {"state": state, "days": days, "open": open_d, "close": close_d}
