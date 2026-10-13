"""Forecasts — Claude's scored intel feed.

Claude gathers evidence weekly and publishes dated, scoreable forecasts with its
own probability (scheduled tasks editing forecasts/ledger.json); a monthly task
resolves them. Norman reads. Adding his own number or dismissing a forecast is
optional. Claude is scored against the prediction-market crowd, so the page
shows whether its intel is worth trusting.
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
  .fc-p { font-size: 1.6rem; font-weight: 600; line-height: 1.1; }
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
        except Exception as e:
            st.warning(f"Couldn't read the ledger from GitHub ({e}); showing the deployed copy.")
    return L.load_local()


def apply(fid: str, changes: dict, message: str) -> None:
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
active = [f for f in fc if f.get("status") in ("active", "proposed")]
resolved = [f for f in fc if f.get("status") == "resolved"]


def _pct(p):
    return "—" if p is None else f"{p:.0%}"


# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("## Forecasts")
st.caption("Claude's intel, as dated probabilities that get scored. New ones arrive every "
           "Monday; outcomes are checked on the 1st. Brier: 0 is perfect, 0.25 is a coin flip.")

cl_b = L.mean_brier(fc, "claude_p")
cl_vs_crowd = L.head_to_head(fc, "claude_p", "crowd_p")
new_this_week = [f for f in active
                 if (date.today() - date.fromisoformat(f["created"])).days <= 7]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Open forecasts", len(active),
          delta=f"{len(new_this_week)} new this week" if new_this_week else None,
          delta_color="off")
m2.metric("Resolved", len(resolved))
m3.metric("Claude's Brier", f"{cl_b:.3f}" if cl_b is not None else "—")
if cl_vs_crowd:
    c, cr, n = cl_vs_crowd
    m4.metric("Claude vs crowd", f"{c:.3f} vs {cr:.3f}",
              delta=f"{'beating' if c < cr else 'trailing'} on {n}",
              delta_color="normal" if c < cr else "inverse")
else:
    m4.metric("Claude vs crowd", "—",
              help="Fills in once forecasts that had a market price resolve")

if len(resolved) < 20:
    st.caption(f"Track record so far: {len(resolved)} resolved. Treat Claude's numbers as "
               "unproven until ~20 have resolved and it holds up against the crowd.")

tab_feed, tab_score = st.tabs(["Intel feed", "Track record"])


# ─── Intel feed ──────────────────────────────────────────────────────────────

with tab_feed:
    themes = sorted({f.get("theme", "Other") for f in active})
    pick = st.pills("Theme", themes, selection_mode="multi", default=themes,
                    label_visibility="collapsed") if themes else []
    shown = [f for f in active if f.get("theme", "Other") in (pick or themes)]

    if not shown:
        st.write("No open forecasts. The Monday scan adds new ones.")

    for f in sorted(shown, key=lambda x: x["resolve_by"]):
        late = date.fromisoformat(f["resolve_by"]) < date.today()
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"**{f['question']}**")
                crowd = (f" · crowd {_pct(f['crowd_p'])}" if f.get("crowd_p") is not None else "")
                mine = (f" · you {_pct(f['your_p'])}" if f.get("your_p") is not None else "")
                st.markdown(
                    f"<div class='fc-meta'>{f.get('theme','')} · resolves by {f['resolve_by']}"
                    f"{' ⚠ awaiting resolution' if late else ''}{crowd}{mine}</div>",
                    unsafe_allow_html=True)
            with right:
                st.markdown(f"<div class='fc-p'>{_pct(f.get('claude_p'))}</div>"
                            "<div class='fc-meta'>Claude</div>", unsafe_allow_html=True)

            with st.expander("Evidence and reasoning"):
                st.write(f.get("rationale", ""))
                if f.get("indicators"):
                    st.markdown("**Indicators**")
                    for i in f["indicators"]:
                        st.markdown(f"- {i}")
                st.markdown(f"**Resolves:** {f.get('resolution','')}")
                if f.get("crowd_source"):
                    st.markdown(f"[Market price]({f['crowd_source']})")

                st.divider()
                st.caption("Optional: disagree with Claude? Log your own number and it gets scored too.")
                p = st.slider("Your probability", 1, 99,
                              int(round((f.get("your_p") or f.get("claude_p") or 0.5) * 100)),
                              format="%d%%", key=f"p_{f['id']}")
                a, d, _ = st.columns([1, 1, 3])
                if a.button("Log my number", key=f"a_{f['id']}"):
                    apply(f["id"], {"your_p": p / 100, "status": "active",
                                    "accepted": date.today().isoformat()},
                          f"Log Norman's {p}% on {f['id']}")
                    st.rerun()
                if d.button("Not useful", key=f"r_{f['id']}"):
                    apply(f["id"], {"status": "rejected"}, f"Dismiss forecast {f['id']}")
                    st.rerun()

    if not TOKEN and active:
        st.caption("🔒 Logging a number or dismissing won't save on the cloud deployment until "
                   "`github_token` is in Streamlit secrets. Reading works without it.")


# ─── Track record ────────────────────────────────────────────────────────────

with tab_score:
    cal = L.calibration(fc, "claude_p")
    if not cal:
        st.write("Nothing resolved yet. The first outcomes are checked on the 1st of next month.")
    else:
        st.markdown("**Is Claude calibrated?**")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                                 line=dict(dash="dot", color="gray")))
        fig.add_trace(go.Scatter(
            x=[c["said"] for c in cal], y=[c["happened"] for c in cal],
            mode="markers+text", text=[f"n={c['n']}" for c in cal],
            textposition="top center", marker=dict(size=[8 + 3 * c["n"] for c in cal])))
        fig.update_layout(template="streamlit", height=360, showlegend=False,
                          xaxis=dict(title="Claude said", tickformat=".0%", range=[0, 1]),
                          yaxis=dict(title="It happened", tickformat=".0%", range=[0, 1]),
                          margin=dict(t=20, b=40, l=60, r=20))
        st.plotly_chart(fig, width="stretch")
        st.caption("Below the line: overconfident. Above: underconfident.")

        you_vs = L.head_to_head(fc, "your_p", "claude_p")
        if you_vs:
            y, c, n = you_vs
            st.caption(f"Where you logged your own number ({n}): you {y:.3f} vs Claude {c:.3f}.")

        st.dataframe(pd.DataFrame([{
            "Resolved": f.get("resolved_on"),
            "Question": f["question"],
            "Outcome": "Yes" if f.get("outcome") else "No",
            "Claude": _pct(f.get("claude_p")),
            "Claude Brier": f"{L.brier(f['claude_p'], f['outcome']):.3f}" if f.get("claude_p") is not None else "—",
            "Crowd": _pct(f.get("crowd_p")),
            "You": _pct(f.get("your_p")),
            "Source": f.get("outcome_source"),
        } for f in sorted(resolved, key=lambda x: x.get("resolved_on") or "", reverse=True)]),
            hide_index=True, width="stretch",
            column_config={"Source": st.column_config.LinkColumn("Source")})
