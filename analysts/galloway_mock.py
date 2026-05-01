"""Data module for Scott Galloway.

Bio, framework tracker, top signals, and the prose synthesis are
hand-curated below. `recent_items` is overlaid from the No Mercy /
No Malice RSS feed when reachable; if the feed is down, the static
fallback list below is used so the dashboard always renders.
"""

from collectors.galloway_rss import fetch_galloway_items
from models.analyst import Analyst


_FALLBACK_RECENT_ITEMS = [
    {
        "title": "The AI capex circle is starting to bite its own tail",
        "source": "No Mercy / No Malice (newsletter)",
        "url": "https://www.profgalloway.com/",
        "published": "2026-04-12",
        "summary": (
            "Argues hyperscaler–frontier-lab vendor financing has the "
            "structural shape of late-1999 telecom, even if the "
            "underlying tech is real."
        ),
    },
    {
        "title": "Pivot: Tesla's demand problem is finally legible",
        "source": "Pivot (podcast)",
        "url": "https://www.voxmedia.com/podcasts/pivot",
        "published": "2026-04-11",
        "summary": (
            "With Kara Swisher. Lease residuals, not delivery numbers, "
            "are the cleanest read on Tesla demand; residuals are down "
            "materially YoY."
        ),
    },
    {
        "title": "The Prof G Pod: Why the 'young men' story won't go away",
        "source": "The Prof G Pod",
        "url": "https://www.profgmedia.com/",
        "published": "2026-04-09",
        "summary": (
            "Revisits his under-30-male thesis with updated 2026 data "
            "on enrolment, homeownership, and overdose mortality."
        ),
    },
    {
        "title": "Keynote: The Algebra of Wealth, 2026 edition",
        "source": "SXSW",
        "url": "https://www.sxsw.com/",
        "published": "2026-04-07",
        "summary": (
            "Updated 'stoicism + focus + time + diversification' talk "
            "with a sharper section on AI-era human capital strategy."
        ),
    },
    {
        "title": "No Mercy / No Malice: Ozempic is a retail story, not a pharma story",
        "source": "No Mercy / No Malice (newsletter)",
        "url": "https://www.profgalloway.com/",
        "published": "2026-04-05",
        "summary": (
            "Frames GLP-1 adoption as a demand-side shock to packaged "
            "food, fast-casual, and even airline margins."
        ),
    },
]


_FALLBACK_LAST_UPDATED = "2026-04-14"


def _resolve_recent_items() -> list:
    live = fetch_galloway_items(limit=5)
    return live if live else _FALLBACK_RECENT_ITEMS


def _last_updated_from(items: list) -> str:
    if items and items[0].get("published"):
        return items[0]["published"]
    return _FALLBACK_LAST_UPDATED


def refresh_galloway() -> None:
    """Re-pull recent items from the RSS source and update GALLOWAY in place.

    The page script (Streamlit re-runs it on every interaction) calls this so
    the in-memory analyst dict tracks the on-disk feed cache. The fetch itself
    is gated by the 6-hour TTL in `collectors.galloway_rss`.
    """
    items = _resolve_recent_items()
    GALLOWAY["recent_items"] = items
    GALLOWAY["last_updated"] = _last_updated_from(items)


GALLOWAY: Analyst = {
    "id": "galloway",
    "name": "Scott Galloway",
    "focus_area": "Tech, media, and young-male malaise",
    "bio": (
        "Professor of marketing at NYU Stern. Co-host of Pivot (with Kara "
        "Swisher) and host of The Prof G Pod. Writes the No Mercy / No "
        "Malice newsletter. Known for business frameworks around Big Tech "
        "(The Four, T-Algorithm) and a growing body of work on economic "
        "and relational outcomes for young American men."
    ),
    "last_updated": _FALLBACK_LAST_UPDATED,
    "latest_content": (
        "Galloway's dominant theme this week is that the AI capex cycle is "
        "starting to look like late-stage dotcom in two specific ways: "
        "circular vendor financing among hyperscalers and frontier labs, "
        "and the share of S&P 500 capex now concentrated in six names. He "
        "is not calling a top but flags that the marginal AI dollar is "
        "increasingly funded by the same balance sheets receiving it. "
        "Secondary theme: his long-running 'young men' thesis is tightening "
        "around three data points — the male-female college enrolment gap "
        "widening again, a further drop in under-30 homeownership, and "
        "deaths of despair re-accelerating. He argues the policy response "
        "is still aimed at the wrong cohort. Tertiary: Tesla demand unwind "
        "is now visible in lease residuals, not just deliveries."
    ),
    "recent_items": _FALLBACK_RECENT_ITEMS,
    "frameworks": [
        {
            "name": "The Four / T-Algorithm",
            "status": "active",
            "signal": "Concentration deepening",
            "note": (
                "Mag-7 share of S&P capex and buybacks at new highs; his "
                "framework for what makes a trillion-dollar company "
                "increasingly describes a closed set."
            ),
        },
        {
            "name": "Algebra of Wealth",
            "status": "active",
            "signal": "Reinforced",
            "note": (
                "SXSW keynote re-centred on focus + time; argues AI makes "
                "the 'stoicism' term more valuable, not less."
            ),
        },
        {
            "name": "Young men crisis",
            "status": "active",
            "signal": "Strengthening",
            "note": (
                "2026 data on enrolment, housing, and mortality all moved "
                "the wrong way; becoming his most-cited frame."
            ),
        },
        {
            "name": "Rundle thesis",
            "status": "watch",
            "signal": "Saturation",
            "note": (
                "Subscription-bundle model hitting churn ceiling across "
                "streaming; less prominent in his recent content."
            ),
        },
    ],
    "signals": [
        {
            "name": "AI capex circular financing",
            "severity": 8,
            "velocity": 8,
            "category": "economic",
        },
        {
            "name": "Young-male economic detachment",
            "severity": 7,
            "velocity": 5,
            "category": "economic",
        },
        {
            "name": "Tesla demand unwind (lease residuals)",
            "severity": 6,
            "velocity": 7,
            "category": "economic",
        },
        {
            "name": "US university ROI collapse",
            "severity": 7,
            "velocity": 4,
            "category": "economic",
        },
        {
            "name": "GLP-1 reshaping retail / food",
            "severity": 5,
            "velocity": 7,
            "category": "economic",
        },
        {
            "name": "Mag-7 S&P concentration",
            "severity": 7,
            "velocity": 5,
            "category": "economic",
        },
        {
            "name": "Streaming churn ceiling",
            "severity": 4,
            "velocity": 5,
            "category": "technology",
        },
    ],
}


refresh_galloway()
