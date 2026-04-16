"""Shared data contract for analyst / thought-leader profiles.

This is the shape the Macro → Thought Leaders pipeline will populate.
All analysts (Bremmer and future additions) conform to Analyst.
"""

from __future__ import annotations

from typing import Literal, TypedDict


FrameworkStatus = Literal["active", "watch", "dormant"]
SignalCategory = Literal[
    "geopolitical",
    "economic",
    "technology",
    "security",
    "energy",
    "other",
]


class Framework(TypedDict):
    name: str
    status: FrameworkStatus
    signal: str
    note: str


class Signal(TypedDict):
    name: str
    severity: int  # 0-10, how consequential if it plays out
    velocity: int  # 0-10, how fast it's evolving
    category: SignalCategory


class RecentItem(TypedDict):
    title: str
    source: str
    url: str
    published: str  # ISO date (YYYY-MM-DD)
    summary: str


class Analyst(TypedDict):
    id: str
    name: str
    focus_area: str
    bio: str
    last_updated: str  # ISO date
    latest_content: str  # prose synthesis of the last week
    recent_items: list[RecentItem]
    frameworks: list[Framework]
    signals: list[Signal]
