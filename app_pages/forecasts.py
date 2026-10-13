"""Forecasts — scored prediction ledger.

Claude proposes forecasts weekly and resolves them monthly (scheduled tasks
editing forecasts/ledger.json). Norman accepts, rejects, and sets his own
probability here. Only his number is scored as "you".
"""

import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from forecasts import ledger as L

st.set_page_config(page_title="Forecasts", page_icon="🎯", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 2rem; }
  [data-testid="stMetric"] {
      background: var(--secondary-background-color);
      border-radius: 8px; padding: 1rem;
  }
  .fc-meta { font-size: 0.82rem; opacity: 0.75; }
</style>
""", unsafe_allow_html=True)


# ─── Storage ─────────────────────────────────────────────────────────────────

def _token() -> str | None:
    try:
        return st.secrets.get("github_token")
    except Exception:
        return None


TOKEN = _token()


def load() -> dict:
    if TOKEN:
        try:
            data, sha = L.load_remote(TOKEN)
            st.session_state["ledger_sha"] = sha
            return data
        except Exception as e:  # fall back so the page still renders
            st.warning(f"Couldn't read the ledger from GitHub ({e}); showing the deployed copy.")
    return L.load_local()


def apply(fid: str, changes: dict, message: str) -> None:
    """Re-read, change one row, write back. Retries once on a commit conflict."""
    for attempt in range(2):
        data = load()
        row = next((f for f in data["forecasts"] if f["id"] == fid), None)
        if row is None:
            st.error("That forecast no longer exists in the ledger.")
            return
        row.update(changes)
        if not TOKEN:
            L.save_local(data)
            return
        try:
            L.save_remote(data, st.session_state["ledger_sha"], TOKEN, message)
            return
        except Exception:
            if attempt == 1:
                raise


ledger = load()
fc = ledger.get("forecasts", [])
by_status = {s: [f for f in fc if f.get("status") == s] for s in L.STATUSES}


# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("## Forecasts")
st.caption("Explicit, dated, scored. Claude proposes weekly and resolves monthly; "
           "only your probability counts as yours. Brier: 0 is perfect, 0.25 is a coin flip.")

if not TOKEN:
    st.info("Read-only on the cloud deployment until a `github_token` is added to "
            "Streamlit secrets — edits made here would be lost on the next restart.",
            icon="🔒")

you_b = L.mean_brier(fc)
vs_claude = L.head_to_head(fc, "claude_p")
vs_crowd = L.head_to_head(fc, "crowd_p")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Awaiting your review", len(by_status["proposed"]))
m2.metric("Open", len(by_status["active"]),
          delta=f"{len(L.overdue(fc))} overdue" if L.overdue(fc) else None,
          delta_color="off")
m3.metric("Your Brier", f"{you_b:.3f}" if you_b is not None else "—",
          help=f"Across {len(L.scored(fc))} resolved forecasts")
if vs_crowd:
    you, crowd, n = vs_crowd
    m4.metric("You vs crowd", f"{you:.3f} vs {crowd:.3f}",
              delta=f"{'ahead' if you < crowd else 'behind'} on {n}",
              delta_color="normal" if you < crowd else "inverse")
elif vs_claude:
    you, cl, n = vs_claude
    m4.metric("You vs Claude", f"{you:.3f} vs {cl:.3f}",
              delta=f"{'ahead' if you < cl else 'behind'} on {n}",
              delta_color="normal" if you < cl else "inverse")
else:
    m4.metric("You vs crowd", "—", help="Needs resolved forecasts that had a crowd number")


tab_review, tab_open, tab_score = st.tabs([
    f"Review ({len(by_status['proposed'])})",
    f"Open ({len(by_status['active'])})",
    "Scorecard",
])


def _pct(p):
    return "—" if p is None else f"{p:.0%}"


# ─── Review ──────────────────────────────────────────────────────────────────

with tab_review:
    if not by_status["proposed"]:
        st.write("Nothing to review. The weekly scan adds proposals here.")
    for f in sorted(by_status["proposed"], key=lambda x: x["resolve_by"]):
        with st.container(border=True):
            st.markdown(f"**{f['question']}**")
            st.markdown(
                f"<div class='fc-meta'>{f.get('theme','')} · resolves by {f['resolve_by']} · "
                f"Claude {_pct(f.get('claude_p'))} · crowd {_pct(f.get('crowd_p'))}</div>",
                unsafe_allow_html=True)
            with st.expander("Why, and how it resolves"):
                st.write(f.get("rationale", ""))
                if f.get("indicators"):
                    st.markdown("**Indicators:** " + "; ".join(f["indicators"]))
                st.markdown(f"**Resolves:** {f.get('resolution','')}")
                if f.get("crowd_source"):
                    st.markdown(f"[Crowd forecast]({f['crowd_source']})")

            # Deliberately no default from Claude's number: anchoring defeats the point.
            p = st.slider("Your probability", 1, 99, 50, format="%d%%",
                          key=f"p_{f['id']}")
            note = st.text_input("Your reasoning (optional)", key=f"n_{f['id']}")
            a, r, _ = st.columns([1, 1, 4])
            if a.button("Accept", key=f"a_{f['id']}", type="primary"):
                apply(f["id"], {"status": "active", "your_p": p / 100,
                                "your_note": note or None,
                                "accepted": date.today().isoformat()},
                      f"Accept forecast {f['id']} at {p}%")
                st.rerun()
            if r.button("Reject", key=f"r_{f['id']}"):
                apply(f["id"], {"status": "rejected", "your_note": note or None},
                      f"Reject forecast {f['id']}")
                st.rerun()


# ─── Open ────────────────────────────────────────────────────────────────────

with tab_open:
    if not by_status["active"]:
        st.write("No open forecasts yet.")
    else:
        late = {f["id"] for f in L.overdue(fc)}
        df = pd.DataFrame([{
            "Resolves by": f["resolve_by"] + ("  ⚠ overdue" if f["id"] in late else ""),
            "Question": f["question"],
            "Theme": f.get("theme"),
            "You": _pct(f.get("your_p")),
            "Claude": _pct(f.get("claude_p")),
            "Crowd": _pct(f.get("crowd_p")),
        } for f in sorted(by_status["active"], key=lambda x: x["resolve_by"])])
        st.dataframe(df, hide_index=True, width="stretch")
        st.caption("Overdue items get resolved by the monthly scoring run.")


# ─── Scorecard ───────────────────────────────────────────────────────────────

with tab_score:
    cal = L.calibration(fc)
    if not cal:
        st.write("No resolved forecasts yet. Calibration needs roughly 20 before it means much.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect",
                                 line=dict(dash="dot", color="gray")))
        fig.add_trace(go.Scatter(
            x=[c["said"] for c in cal], y=[c["happened"] for c in cal],
            mode="markers+text", name="You",
            text=[f"n={c['n']}" for c in cal], textposition="top center",
            marker=dict(size=[8 + 3 * c["n"] for c in cal])))
        fig.update_layout(template="streamlit", height=380,
                          xaxis=dict(title="You said", tickformat=".0%", range=[0, 1]),
                          yaxis=dict(title="It happened", tickformat=".0%", range=[0, 1]),
                          margin=dict(t=20, b=40, l=60, r=20), showlegend=False)
        st.plotly_chart(fig, width="stretch")
        st.caption("Points below the line: overconfident. Above: underconfident.")

        res = sorted(by_status["resolved"], key=lambda x: x.get("resolved_on") or "", reverse=True)
        st.dataframe(pd.DataFrame([{
            "Resolved": f.get("resolved_on"),
            "Question": f["question"],
            "Outcome": "Yes" if f.get("outcome") else "No",
            "You": _pct(f.get("your_p")),
            "Your Brier": f"{L.brier(f['your_p'], f['outcome']):.3f}" if f.get("your_p") is not None else "—",
            "Crowd": _pct(f.get("crowd_p")),
            "Source": f.get("outcome_source"),
        } for f in res]), hide_index=True, width="stretch",
            column_config={"Source": st.column_config.LinkColumn("Source")})
