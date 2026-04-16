"""Mock data for Ian Bremmer — placeholder until the real pipeline runs.

Replace this module wholesale when the ingestion / synthesis pipeline
lands. Keep the `BREMMER: Analyst` export name stable.
"""

from models.analyst import Analyst


BREMMER: Analyst = {
    "id": "bremmer",
    "name": "Ian Bremmer",
    "focus_area": "Geopolitical risk",
    "bio": (
        "President of Eurasia Group and GZERO Media. Political scientist "
        "focused on global political risk, US–China competition, and the "
        "erosion of the post-war international order. Known for the G-Zero, "
        "Technopolar, and J-Curve frameworks."
    ),
    "last_updated": "2026-04-15",
    "latest_content": (
        "Bremmer's dominant frame this week is that the G-Zero world is "
        "accelerating, not plateauing. He argues the combination of a second "
        "Trump term's tariff posture, Europe's fragmented response to the "
        "Ukraine settlement, and the Gulf states' open hedging between "
        "Washington and Beijing marks a qualitative shift: allies are no "
        "longer just doubting US reliability, they are pricing it in. "
        "Secondary theme: the Technopolar thesis is tightening as frontier "
        "AI labs become de facto counterparties to states on export controls "
        "and compute allocation. He flags the US–UAE compute deal as the "
        "clearest recent marker. On the J-Curve, he is cautiously watching "
        "Turkey and Venezuela — both sitting at the unstable trough where "
        "partial opening can either tip into reform or into collapse."
    ),
    "recent_items": [
        {
            "title": "The G-Zero world, five years in: what we got right and wrong",
            "source": "GZERO World (podcast)",
            "url": "https://www.gzeromedia.com/",
            "published": "2026-04-14",
            "summary": (
                "Retrospective episode. Bremmer concedes the G-Zero framing "
                "underestimated how quickly middle powers would start hedging "
                "openly rather than choosing a bloc."
            ),
        },
        {
            "title": "Why the US–UAE compute deal is a Technopolar inflection point",
            "source": "Foreign Affairs",
            "url": "https://www.foreignaffairs.com/",
            "published": "2026-04-12",
            "summary": (
                "Argues that chip allocation is becoming the new sanctions "
                "regime, and that frontier AI labs are now first-class "
                "geopolitical actors rather than instruments of state power."
            ),
        },
        {
            "title": "Quick Take: Europe's Ukraine fatigue is structural, not political",
            "source": "Eurasia Group (note)",
            "url": "https://www.eurasiagroup.net/",
            "published": "2026-04-10",
            "summary": (
                "Short client note. Frames European reluctance on further "
                "Ukraine commitments as an industrial-base constraint rather "
                "than a coalition-politics one."
            ),
        },
        {
            "title": "Turkey on the J-Curve: reform window or collapse window?",
            "source": "Substack (Ian Bremmer)",
            "url": "https://ianbremmer.substack.com/",
            "published": "2026-04-08",
            "summary": (
                "Lira stabilisation has bought time but not trajectory. "
                "Calls the next six months the highest-variance period for "
                "Turkey since 2018."
            ),
        },
        {
            "title": "Top Risks 2026: Q2 check-in",
            "source": "GZERO Daily",
            "url": "https://www.gzeromedia.com/gzero-daily",
            "published": "2026-04-07",
            "summary": (
                "Mid-year update to the January Top Risks list. Rogue US, "
                "US–China breakdown, and ungoverned AI all revised upward; "
                "Middle East revised slightly down after Gulf détente moves."
            ),
        },
    ],
    "frameworks": [
        {
            "name": "G-Zero",
            "status": "active",
            "signal": "Strengthening",
            "note": (
                "Allies hedging openly; no coalition stepping into the "
                "leadership vacuum. Bremmer's most-invoked frame this week."
            ),
        },
        {
            "name": "Technopolar",
            "status": "active",
            "signal": "Strengthening",
            "note": (
                "Compute allocation treated as sanctions policy; AI labs "
                "behaving as sovereign-adjacent actors in US–UAE deal."
            ),
        },
        {
            "name": "J-Curve",
            "status": "watch",
            "signal": "Reactivated",
            "note": (
                "Turkey and Venezuela flagged as sitting at the unstable "
                "trough; not invoked in months prior."
            ),
        },
    ],
    "signals": [
        {
            "name": "US–China tech decoupling",
            "severity": 8,
            "velocity": 6,
            "category": "geopolitical",
        },
        {
            "name": "Frontier AI lab as geopolitical actor",
            "severity": 7,
            "velocity": 8,
            "category": "technology",
        },
        {
            "name": "European industrial-base strain on Ukraine",
            "severity": 6,
            "velocity": 4,
            "category": "security",
        },
        {
            "name": "Gulf states open hedging US vs China",
            "severity": 6,
            "velocity": 7,
            "category": "geopolitical",
        },
        {
            "name": "Turkey J-Curve instability",
            "severity": 5,
            "velocity": 6,
            "category": "economic",
        },
        {
            "name": "Taiwan strait miscalculation risk",
            "severity": 9,
            "velocity": 3,
            "category": "security",
        },
        {
            "name": "AI governance fragmentation",
            "severity": 6,
            "velocity": 7,
            "category": "technology",
        },
    ],
}
