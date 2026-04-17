"""Mock data for Steve Eisman — placeholder until the real pipeline runs.

Replace this module wholesale when the ingestion / synthesis pipeline
lands. Keep the `EISMAN: Analyst` export name stable.
"""

from models.analyst import Analyst


EISMAN: Analyst = {
    "id": "eisman",
    "name": "Steve Eisman",
    "focus_area": "Bank balance sheets & financial-sector fragility",
    "bio": (
        "Senior portfolio manager at Neuberger Berman. Best known for his "
        "pre-2008 short on subprime mortgage lenders, dramatized in The "
        "Big Short. Frequent CNBC, Bloomberg, and Odd Lots commentator on "
        "US bank capitalisation, regional-bank health, commercial real "
        "estate refinancing, and systemic credit risk. Explicit about "
        "distinguishing 'stress' from 'crisis' in bank-sector narratives."
    ),
    "last_updated": "2026-04-15",
    "latest_content": (
        "Eisman this week keeps hammering two points: the 2026 commercial "
        "real estate refinancing wall is real and mechanically rate-"
        "sensitive, but it is not a 2008. His frame is that CRE stress "
        "works its way through regional bank earnings as a multi-quarter "
        "grind rather than a single credit event, and that the large "
        "US banks have absorbed the worst of their HTM unrealized losses "
        "already. Secondary theme: he is notably more worried about "
        "private credit than about listed banks — he argues mark-to-"
        "model valuations there have never been truly stress-tested. "
        "Tertiary: pushback on the Basel III endgame rollback narrative; "
        "thinks the rollback is marginal and that bank capital is "
        "structurally higher than any pre-GFC comparison implies."
    ),
    "recent_items": [
        {
            "title": "CNBC Fast Money: the CRE wall is a grind, not a crash",
            "source": "CNBC",
            "url": "https://www.cnbc.com/",
            "published": "2026-04-14",
            "summary": (
                "Frames 2026 CRE refinancing as a three-year drag on "
                "regional bank EPS rather than a discrete credit event. "
                "Names no specific short."
            ),
        },
        {
            "title": "Odd Lots: What's actually in private credit books?",
            "source": "Bloomberg Odd Lots (podcast)",
            "url": "https://www.bloomberg.com/podcasts/odd_lots",
            "published": "2026-04-12",
            "summary": (
                "Argues private credit is the current cycle's analogue to "
                "pre-2008 CDO tranches — not in structure, but in the "
                "untested nature of its stress-scenario valuations."
            ),
        },
        {
            "title": "Bloomberg TV: Not another 2008",
            "source": "Bloomberg TV",
            "url": "https://www.bloomberg.com/",
            "published": "2026-04-10",
            "summary": (
                "Explicit pushback on bank-apocalypse framing. Cites "
                "Tier-1 capital ratios, LCR, and post-GFC stress-test "
                "history as the main counterweights."
            ),
        },
        {
            "title": "Neuberger Berman Q2 outlook: regional banks",
            "source": "Neuberger Berman (letter)",
            "url": "https://www.nb.com/",
            "published": "2026-04-08",
            "summary": (
                "Selective long/short on US regionals: constructive on "
                "banks with low CRE / high deposit beta discipline, "
                "negative on those with concentrated office exposure."
            ),
        },
        {
            "title": "The Compound: Basel III endgame rollback is overstated",
            "source": "The Compound (podcast)",
            "url": "https://www.thecompoundnews.com/",
            "published": "2026-04-06",
            "summary": (
                "Argues the political narrative on capital-rule rollback "
                "is louder than the economic one; bank balance sheets are "
                "already operating well above binding minima."
            ),
        },
    ],
    "frameworks": [
        {
            "name": "Forensic balance sheet",
            "status": "active",
            "signal": "Core frame",
            "note": (
                "HTM unrealized losses, deposit beta, CRE concentration — "
                "his running scorecard for distinguishing stress from "
                "crisis at individual banks."
            ),
        },
        {
            "name": "Stress vs. crisis",
            "status": "active",
            "signal": "Central this week",
            "note": (
                "Argues the market repeatedly mis-labels a multi-quarter "
                "earnings grind as a systemic event; his most-invoked "
                "frame in current appearances."
            ),
        },
        {
            "name": "Private credit opacity",
            "status": "active",
            "signal": "Escalating",
            "note": (
                "Pivoted from public-bank focus to private-credit marks as "
                "the cycle's highest-risk blind spot."
            ),
        },
        {
            "name": "Not another 2008",
            "status": "active",
            "signal": "Reinforced",
            "note": (
                "Explicit pushback on bank-apocalypse narratives; cites "
                "post-GFC capital structure as the core counterpoint."
            ),
        },
    ],
    "signals": [
        {
            "name": "CRE refinancing wall 2026",
            "severity": 8,
            "velocity": 7,
            "category": "economic",
        },
        {
            "name": "Private credit mark-to-model opacity",
            "severity": 8,
            "velocity": 6,
            "category": "economic",
        },
        {
            "name": "Regional bank HTM unrealized losses",
            "severity": 5,
            "velocity": 3,
            "category": "economic",
        },
        {
            "name": "Deposit beta discipline divergence",
            "severity": 5,
            "velocity": 5,
            "category": "economic",
        },
        {
            "name": "Consumer credit card delinquencies",
            "severity": 6,
            "velocity": 6,
            "category": "economic",
        },
        {
            "name": "Basel III endgame rollback",
            "severity": 4,
            "velocity": 4,
            "category": "economic",
        },
        {
            "name": "Office-CRE concentrated-bank stress",
            "severity": 7,
            "velocity": 6,
            "category": "economic",
        },
    ],
}
