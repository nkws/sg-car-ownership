"""Mock data for Michael Burry — placeholder until the real pipeline runs.

Replace this module wholesale when the ingestion / synthesis pipeline
lands. Keep the `BURRY: Analyst` export name stable.

Note: Burry's public footprint is unusually sparse — mostly SEC 13F
filings and brief, often-deleted @michaeljburry tweets. Expect
`recent_items` here to be shorter and more event-driven than for
analysts who publish continuous longform content.
"""

from models.analyst import Analyst


BURRY: Analyst = {
    "id": "burry",
    "name": "Michael Burry",
    "focus_area": "Contrarian macro & concentrated shorts",
    "bio": (
        "Founder of Scion Asset Management. Profiled in The Big Short for "
        "his pre-2008 short on subprime mortgage-backed securities. Posts "
        "cryptic, frequently-deleted market commentary on X under "
        "@michaeljburry. Public footprint is dominated by quarterly 13F "
        "filings and tactical short positions rather than longform views."
    ),
    "last_updated": "2026-04-15",
    "latest_content": (
        "Q1 2026 13F dropped this week and drives the read. Scion rotated "
        "further into selected Asia value names (raised BABA, initiated "
        "JD again) while adding put-spread exposure on the US "
        "semiconductor cycle. Net-net the book is more barbell than "
        "outright bearish: cheap Chinese cash-flow names on one side, "
        "defined-risk downside on AI-cycle beneficiaries on the other. "
        "His sparse X presence this week reinforced two long-running "
        "themes: passive-index flows distorting price discovery in the "
        "Mag-7, and 'circular' vendor financing in AI infrastructure. A "
        "deleted-but-screenshotted tweet flagged private-credit opacity "
        "as the cycle's likely accident site — less dramatic than 2008 "
        "mortgage bonds but, in his framing, similarly mis-rated."
    ),
    "recent_items": [
        {
            "title": "Scion Asset Management Q1 2026 13F",
            "source": "SEC EDGAR",
            "url": "https://www.sec.gov/cgi-bin/browse-edgar",
            "published": "2026-04-14",
            "summary": (
                "Added to BABA and JD; initiated puts on a US semi-cycle "
                "proxy basket; trimmed healthcare. Book small by AUM but "
                "concentrated."
            ),
        },
        {
            "title": "'Cassandra' — deleted tweet on passive flows",
            "source": "X / @michaeljburry",
            "url": "https://x.com/michaeljburry",
            "published": "2026-04-13",
            "summary": (
                "Reconstructed from screenshots: argued passive-index "
                "concentration in Mag-7 has reached the point where "
                "outflows become reflexive rather than fundamental."
            ),
        },
        {
            "title": "'The accident site' — deleted tweet on private credit",
            "source": "X / @michaeljburry",
            "url": "https://x.com/michaeljburry",
            "published": "2026-04-10",
            "summary": (
                "Flagged opacity in private-credit mark-to-model valuations "
                "as the structurally most likely site of the next credit "
                "event. No specific name cited."
            ),
        },
        {
            "title": "Scion short interest disclosure (13F derivatives)",
            "source": "SEC EDGAR",
            "url": "https://www.sec.gov/cgi-bin/browse-edgar",
            "published": "2026-04-14",
            "summary": (
                "Put-spread notional on US semi basket at highest level "
                "since 2021; paired with long exposure to Asia hardware "
                "suppliers."
            ),
        },
    ],
    "frameworks": [
        {
            "name": "Passive bubble",
            "status": "active",
            "signal": "Strengthening",
            "note": (
                "Argues index flows distort price discovery at the "
                "concentration levels now seen in Mag-7; explicitly "
                "reinvoked this week."
            ),
        },
        {
            "name": "Asia value rotation",
            "status": "active",
            "signal": "Reinforced",
            "note": (
                "Third consecutive 13F adding to BABA / JD / Tencent-"
                "adjacent names; frames as cash-flow-per-dollar mispricing."
            ),
        },
        {
            "name": "Concentrated short with cheap tails",
            "status": "active",
            "signal": "In use",
            "note": (
                "Put-spread structure on semi basket matches his historical "
                "pattern: pay for defined downside during cycle tops."
            ),
        },
        {
            "name": "Credit cycle exhaustion",
            "status": "watch",
            "signal": "Refocused on private credit",
            "note": (
                "Pivoted from public-market credit concerns to private-"
                "credit mark opacity as the likely fracture point."
            ),
        },
    ],
    "signals": [
        {
            "name": "AI capex circular financing",
            "severity": 8,
            "velocity": 7,
            "category": "economic",
        },
        {
            "name": "Passive-index concentration in Mag-7",
            "severity": 7,
            "velocity": 5,
            "category": "economic",
        },
        {
            "name": "Private credit mark-to-model opacity",
            "severity": 8,
            "velocity": 6,
            "category": "economic",
        },
        {
            "name": "US semiconductor cycle inventory build",
            "severity": 6,
            "velocity": 7,
            "category": "technology",
        },
        {
            "name": "Asia value re-rating (BABA / JD)",
            "severity": 5,
            "velocity": 6,
            "category": "economic",
        },
        {
            "name": "Consumer credit delinquency drift",
            "severity": 5,
            "velocity": 5,
            "category": "economic",
        },
    ],
}
