"""Intel — Claude's weekly sector intel brief.

Read-only. Claude's Monday task writes intel/briefs.json; the monthly task
scores each evidence lean against its benchmark's 3-month return.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from intel import scoring as S

st.set_page_config(page_title="Intel", page_icon="🛰️", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 2rem; }
  [data-testid="stMetric"] {
      background: var(--secondary-background-color);
      border-radius: 8px; padding: 1rem;
  }
  .meta { font-size: 0.82rem; opacity: 0.75; }
  .lean { display:inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
          font-size: 0.8rem; font-weight: 600; }
  .lean-bullish { background: rgba(76,175,80,0.18); color: #2e7d32; }
  .lean-bearish { background: rgba(239,83,80,0.18); color: #c62828; }
  .lean-mixed   { background: rgba(255,202,40,0.22); color: #8d6e00; }
  @media (prefers-color-scheme: dark) {
    .lean-bullish { color: #81c784; } .lean-bearish { color: #ef9a9a; } .lean-mixed { color: #ffe082; }
  }
</style>
""", unsafe_allow_html=True)

ARROW = {"up": "▲", "down": "▼", "mixed": "◆"}

briefs = S.load()

st.markdown("## Intel")
st.caption("Claude's weekly sector brief: evidence, knock-on effects, which way the evidence "
           "leans, and the price levels that matter. Decision support, not advice. "
           "New brief every Monday.")

if not briefs:
    st.info("The first brief is being compiled. It'll appear here shortly.")
    st.stop()

tab_brief, tab_record = st.tabs(["This week", "Track record"])


def _fmt(v):
    if v is None:
        return "—"
    return f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)


with tab_brief:
    dates = [b["date"] for b in briefs]
    pick = st.selectbox("Brief", dates, index=0, label_visibility="collapsed",
                        format_func=lambda d: f"Week of {d}" + ("  (latest)" if d == dates[0] else ""))
    brief = next(b for b in briefs if b["date"] == pick)

    if brief.get("summary"):
        with st.container(border=True):
            st.markdown("**The week in one read**")
            st.write(brief["summary"])

    sections = brief.get("sections", [])
    themes = list(dict.fromkeys(s["theme"] for s in sections))
    chosen = st.pills("Theme", themes, selection_mode="multi", default=themes,
                      label_visibility="collapsed") or themes

    for s in [s for s in sections if s["theme"] in chosen]:
        with st.container(border=True):
            lean = s.get("lean", "mixed")
            st.markdown(
                f"<span class='lean lean-{lean}'>{lean.upper()} · {s.get('strength','')}</span>"
                f" &nbsp;<span class='meta'>{s['theme']} · {s.get('region','')}</span>",
                unsafe_allow_html=True)
            st.markdown(f"**{s['headline']}**")
            st.write(s.get("first_order", ""))

            if s.get("second_order"):
                st.markdown("**Knock-on effects**")
                for k in s["second_order"]:
                    st.markdown(f"- {ARROW.get(k.get('direction'), '◆')} **{k['sector']}**: {k['effect']}")

            if s.get("levels"):
                st.markdown("**Levels that matter**")
                st.dataframe(pd.DataFrame([{
                    "Instrument": f"{l['name']} ({l.get('ticker','')})",
                    "Last": _fmt(l.get("last")),
                    "Support": _fmt(l.get("support")),
                    "Resistance": _fmt(l.get("resistance")),
                    "52w range": f"{_fmt(l.get('low_52w'))} – {_fmt(l.get('high_52w'))}",
                    "Your band": _fmt(l.get("your_band")),
                } for l in s["levels"]]), hide_index=True, width="stretch")

            if s.get("flip_if"):
                st.markdown(f"**What would flip this read:** {s['flip_if']}")

            with st.expander("Evidence vs consensus, and sources"):
                if s.get("evidence"):
                    st.markdown("**Evidence** (can be pointed to)")
                    for e in s["evidence"]:
                        st.markdown(f"- {e}")
                if s.get("consensus"):
                    st.markdown("**Consensus** (widely believed, not verified here)")
                    for c in s["consensus"]:
                        st.markdown(f"- {c}")
                if s.get("what_happened"):
                    st.markdown("**What happened**")
                    for w in s["what_happened"]:
                        src = f" — [source]({w['source']})" if w.get("source") else ""
                        st.markdown(f"- {w['text']}{src}")
                b = s.get("benchmark") or {}
                if b:
                    st.caption(f"Scored against {b.get('name')} ({b.get('ticker')}) from "
                               f"{_fmt(b.get('price_at_publish'))}, checked {s.get('check_on')}.")

    if brief.get("quiet"):
        st.caption("Nothing worth a read this week: " + ", ".join(brief["quiet"]))


with tab_record:
    rows = S.scored_sections(briefs)
    hr = S.hit_rate(rows)
    c1, c2 = st.columns(2)
    c1.metric("Lean hit rate", f"{hr[0]:.0%}" if hr else "—",
              help="Right ÷ (right + wrong). Flat moves within ±2% are excluded.")
    c2.metric("Leans checked", hr[1] if hr else 0)
    st.caption("Each bullish/bearish lean is checked against its benchmark's absolute return "
               "after 3 months. Crude by design. A coin flip scores about 50%, so until there are "
               "~20 checked leans clearly above that, treat the leans as unproven.")
    if rows:
        df = pd.DataFrame([{
            "Brief": r["date"], "Theme": r["theme"], "Region": r.get("region"),
            "Lean": r["lean"], "Benchmark": (r.get("benchmark") or {}).get("ticker"),
            "3-mo return": f"{r['result']['return_pct']:+.1f}%",
            "Verdict": r["result"]["verdict"],
        } for r in rows])
        st.dataframe(df, hide_index=True, width="stretch")
        by_theme = (df[df["Verdict"].isin(["right", "wrong"])]
                    .groupby("Theme")["Verdict"].apply(lambda v: (v == "right").mean()))
        if not by_theme.empty:
            st.markdown("**Hit rate by theme**")
            st.bar_chart(by_theme)
    else:
        st.write("First leans get checked about 3 months after they're published.")
