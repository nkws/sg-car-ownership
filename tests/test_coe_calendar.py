"""Tests for the COE bidding calendar helpers."""

from datetime import date

from app_pages.coe_calendar import next_bidding_round, buying_window_status


def test_next_round_is_a_future_monday():
    nxt = next_bidding_round(today=date(2026, 6, 16))  # a Tuesday
    assert nxt["date"] >= date(2026, 6, 16)
    assert nxt["date"].weekday() == 0  # Monday
    assert nxt["days_until"] >= 0


def test_next_round_wraps_month_end():
    # Late June → next exercise should be the following month's 1st Monday.
    nxt = next_bidding_round(today=date(2026, 6, 30))
    assert nxt["date"] > date(2026, 6, 30)


def test_window_before_open():
    s = buying_window_status(today=date(2026, 6, 16))
    assert s["state"] == "before"
    assert s["days"] > 0


def test_window_open():
    s = buying_window_status(today=date(2026, 8, 1))
    assert s["state"] == "open"


def test_window_after_close():
    s = buying_window_status(today=date(2026, 12, 31))
    assert s["state"] == "after"
