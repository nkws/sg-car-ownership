"""Collector for Scott Galloway's No Mercy / No Malice newsletter (RSS).

Pulls recent posts from profgalloway.com and shapes them into the
RecentItem contract used on the Macro / Thought Leaders page.

Caches the parsed result to data/galloway_feed.json so the dashboard
doesn't hit the feed on every render and so the page stays usable when
the feed is down. Falls back to stale cache (or empty list) on error.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

from config import DATA_DIR

FEED_URL = "https://www.profgalloway.com/feed/"
CACHE_PATH: Path = DATA_DIR / "galloway_feed.json"
SOURCE_LABEL = "No Mercy / No Malice (newsletter)"
DEFAULT_TTL_HOURS = 6
SUMMARY_MAX_CHARS = 280
HTTP_TIMEOUT = 20

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _to_iso_date(rfc822: str | None) -> str:
    if not rfc822:
        return ""
    try:
        return parsedate_to_datetime(rfc822).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _trim(text: str, limit: int = SUMMARY_MAX_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _parse_feed(xml_bytes: bytes, limit: int) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel") if root.tag.lower() == "rss" else root
    if channel is None:
        return []

    items = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        # WordPress feeds put a long body in <content:encoded>; <description>
        # is the excerpt. Prefer the excerpt for the card summary.
        desc = item.findtext("description") or ""

        items.append({
            "title": title,
            "source": SOURCE_LABEL,
            "url": link,
            "published": _to_iso_date(pub),
            "summary": _trim(_strip_html(desc)),
        })
        if len(items) >= limit:
            break
    return items


def _read_cache() -> dict | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(items: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    CACHE_PATH.write_text(json.dumps(payload, indent=2))


def _cache_is_fresh(cache: dict, ttl_hours: int) -> bool:
    ts = cache.get("fetched_at")
    if not ts:
        return False
    try:
        fetched_at = datetime.fromisoformat(ts)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - fetched_at < timedelta(hours=ttl_hours)


def fetch_galloway_items(
    limit: int = 5,
    ttl_hours: int = DEFAULT_TTL_HOURS,
    force: bool = False,
) -> list[dict]:
    """Return up to `limit` recent Galloway posts as RecentItem dicts.

    Serves from disk cache if fresh; otherwise fetches the feed, parses,
    and rewrites the cache. On network or parse failure, returns the
    stale cache if available, else an empty list.
    """
    cache = _read_cache()
    if cache and not force and _cache_is_fresh(cache, ttl_hours):
        return cache.get("items", [])[:limit]

    try:
        resp = requests.get(FEED_URL, timeout=HTTP_TIMEOUT,
                            headers={"User-Agent": "sg-car-ownership/0.1"})
        resp.raise_for_status()
        items = _parse_feed(resp.content, limit)
        if items:
            _write_cache(items)
            return items
    except (requests.RequestException, ET.ParseError) as e:
        print(f"Galloway RSS fetch failed: {e}")

    if cache:
        return cache.get("items", [])[:limit]
    return []


def run() -> int:
    """Pipeline entry point — refresh the cache and report item count."""
    print("=== Galloway RSS Collector ===")
    items = fetch_galloway_items(force=True)
    print(f"Fetched {len(items)} Galloway items")
    return len(items)


if __name__ == "__main__":
    run()
