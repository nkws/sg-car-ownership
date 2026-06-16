"""Decision Hurdle Index (DHI).

A forward-looking companion to the Financial Stress Index. Where the FSI asks
*"how financially hard is car ownership right now?"*, the DHI asks the question
the user actually faces: *"how high is the bar to confidently buy a car NOW?"*

It is a 0-100 composite (higher = harder to pull the trigger today) built from
four interpretable hurdles, offset by an urgency factor that captures the
opportunity cost of waiting:

    DHI = w_af·affordability + w_tm·timing + w_co·commitment + w_po·policy
          − w_ur·urgency        (clamped to 0-100)

Every sub-hurdle is a pure function returning (score, reason) so the UI can
show *which* hurdle is binding, and so the logic is unit-testable without a
database or Streamlit. The orchestration layer (verdict panel) gathers the raw
inputs — premium, reversal state, profile — and passes primitives in here.

Heuristic only — not financial advice.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict

from config import DHI_WEIGHTS, DHI_BANDS, POLICY_CLIFFS, EV_INCENTIVES


# Reversal states from models/coe_reversal.py, ranked worst (price fall most
# likely) to calm. A likely reversal RAISES the timing hurdle: waiting pays.
_REVERSAL_RANK = {"NO DATA": 0, "STABLE": 0, "WATCH": 1, "POSSIBLE": 2,
                  "LIKELY": 3, "CONFIRMED": 4}
_REVERSAL_TIMING = {0: 35, 1: 55, 2: 70, 3: 85, 4: 95}

Recommendation = str  # "Wait" | "Caution" | "Proceed with caution"


class Hurdle(TypedDict):
    label: str
    score: float        # 0-100
    reason: str


class DecisionScore(TypedDict):
    dhi: float                  # 0-100 composite (higher = harder to buy now)
    band: Recommendation        # Wait / Caution / Proceed with caution
    hurdles: list[Hurdle]       # the four positive hurdles
    urgency: Hurdle             # the offsetting urgency factor
    binding: str                # label of the largest positive hurdle


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _parse(d) -> date:
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


# ── Sub-hurdles ──────────────────────────────────────────────────────────────

def affordability_hurdle(stress_ratio: float, fsi_score: float) -> Hurdle:
    """Personal stress-tested cost-to-income blended with the macro FSI.

    Ratio 10% of income → ~0; 50% → ~100. Blended 70/30 personal/macro.
    """
    ratio_score = _clamp((stress_ratio - 0.10) / (0.50 - 0.10) * 100)
    score = round(0.70 * ratio_score + 0.30 * _clamp(fsi_score), 1)
    reason = (f"Stress-tested cost is {stress_ratio:.0%} of income "
              f"(macro FSI {fsi_score:.0f}/100)")
    return Hurdle(label="Affordability", score=score, reason=reason)


def timing_hurdle(premium: float, avg_premium: float, reversal_state: str,
                  correction_pct: float = 0.0) -> Hurdle:
    """Are prices elevated AND is a reversal likely (so waiting pays)?

    Blends premium-vs-average level with the reversal signal. A heavy
    correction already booked pulls the hurdle back down (good entry).
    """
    if avg_premium and avg_premium > 0:
        level = _clamp(50 + (premium / avg_premium - 1) * 100)
    else:
        level = 50.0
    rev = _REVERSAL_TIMING[_REVERSAL_RANK.get(reversal_state, 0)]
    raw = 0.5 * level + 0.5 * rev
    # If the market has already corrected hard, today is a better entry.
    raw -= _clamp(correction_pct, 0, 30) * 0.5
    score = round(_clamp(raw), 1)
    if rev >= 70:
        reason = f"Reversal {reversal_state}: premiums likely to ease — waiting may pay"
    elif level >= 65:
        reason = f"Premiums {premium / avg_premium - 1:+.0%} vs average — historically elevated"
    else:
        reason = "Premiums near or below average; timing roughly neutral"
    return Hurdle(label="Timing", score=score, reason=reason)


def commitment_hurdle(downpayment: float, monthly_income: float,
                      tenure_years: int) -> Hurdle:
    """Liquidity drain (40% downpayment) and lock-in (loan tenure + 10-yr COE)."""
    months = downpayment / max(monthly_income, 1)
    # 2 months of income → ~0; 12 months → ~100.
    liquidity = _clamp((months - 2) / (12 - 2) * 100)
    tenure_adj = (tenure_years - 6) * 5  # 5y → -5, 7y → +5
    score = round(_clamp(liquidity + tenure_adj), 1)
    reason = (f"40% downpayment ≈ {months:.1f} months of income; "
              f"{tenure_years}-yr loan + 10-yr COE lock-in")
    return Hurdle(label="Commitment", score=score, reason=reason)


def policy_hurdle(today: date | None = None, thesis_stale: bool = False) -> Hurdle:
    """Uncertainty from imminent policy cliffs and a stale market thesis."""
    today = today or date.today()
    score = 35.0
    reasons = ["baseline policy uncertainty"]

    days_to_sunset = (_parse(POLICY_CLIFFS["eeai_sunset"]) - today).days
    if 0 <= days_to_sunset <= 180:
        score += 15
        reasons = ["EEAI rebate change within 6 months"]

    days_to_vgr = (_parse(POLICY_CLIFFS["vgr_review"]) - today).days
    if 0 <= days_to_vgr <= 365:
        score += 10
        reasons.append("vehicle-growth-rate review pending")

    if thesis_stale:
        score += 20
        reasons.append("market thesis overdue for review")

    return Hurdle(label="Policy uncertainty", score=round(_clamp(score), 1),
                  reason="; ".join(reasons))


def urgency_offset(today: date | None = None, is_ev: bool = False) -> Hurdle:
    """Opportunity cost of waiting — SUBTRACTED from the composite.

    Two act-now pulls: an EV buyer losing the EEAI rebate at the Jan-2027 cliff,
    and being inside the thesis's buying window. Higher = more reason to move.
    """
    today = today or date.today()
    score = 10.0
    reasons = ["no pressing reason to rush"]

    if is_ev:
        days_to_sunset = (_parse(EV_INCENTIVES["eeai_sunset"]) - today).days
        if 0 <= days_to_sunset <= 365:
            # 365 days out → ~30; at the cliff → ~95.
            score = max(score, _clamp(95 - (days_to_sunset / 365) * 65))
            reasons = [f"EEAI ${EV_INCENTIVES['eeai_current']:,} rebate ends in "
                       f"{days_to_sunset} days"]

    win_open = _parse(POLICY_CLIFFS["buying_window_open"])
    win_close = _parse(POLICY_CLIFFS["buying_window_close"])
    if win_open <= today <= win_close:
        score = max(score, 55)
        reasons.append("inside the thesis buying window")

    return Hurdle(label="Urgency (waiting cost)", score=round(_clamp(score), 1),
                  reason="; ".join(reasons))


# ── Composite ────────────────────────────────────────────────────────────────

def compute_dhi(
    *,
    affordability: Hurdle,
    timing: Hurdle,
    commitment: Hurdle,
    policy: Hurdle,
    urgency: Hurdle,
    weights: dict | None = None,
    bands: dict | None = None,
) -> DecisionScore:
    """Combine the four hurdles minus urgency into a 0-100 DHI and a band."""
    w = weights or DHI_WEIGHTS
    b = bands or DHI_BANDS

    hurdles = [affordability, timing, commitment, policy]
    positive = (
        w["affordability"] * affordability["score"]
        + w["timing"] * timing["score"]
        + w["commitment"] * commitment["score"]
        + w["policy"] * policy["score"]
    )
    dhi = round(_clamp(positive - w["urgency"] * urgency["score"]), 1)

    if dhi <= b["proceed_below"]:
        band: Recommendation = "Proceed with caution"
    elif dhi >= b["wait_above"]:
        band = "Wait"
    else:
        band = "Caution"

    binding = max(hurdles, key=lambda h: h["score"])["label"]

    return DecisionScore(
        dhi=dhi, band=band, hurdles=hurdles, urgency=urgency, binding=binding,
    )


def build_decision_score(
    *,
    stress_ratio: float,
    fsi_score: float,
    premium: float,
    avg_premium: float,
    reversal_state: str,
    correction_pct: float,
    downpayment: float,
    monthly_income: float,
    tenure_years: int,
    is_ev: bool,
    thesis_stale: bool = False,
    today: date | None = None,
    weights: dict | None = None,
    bands: dict | None = None,
) -> DecisionScore:
    """Convenience orchestrator: assemble every hurdle from raw inputs."""
    return compute_dhi(
        affordability=affordability_hurdle(stress_ratio, fsi_score),
        timing=timing_hurdle(premium, avg_premium, reversal_state, correction_pct),
        commitment=commitment_hurdle(downpayment, monthly_income, tenure_years),
        policy=policy_hurdle(today, thesis_stale),
        urgency=urgency_offset(today, is_ev),
        weights=weights,
        bands=bands,
    )
