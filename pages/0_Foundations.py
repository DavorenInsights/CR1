# pages/0_Foundations.py
from __future__ import annotations

import streamlit as st
from utils.ui import setup_page, render_hero

# IMPORTANT: first Streamlit call
setup_page(
    page_title="Carbon Registry • Foundations",
    page_icon="🧱",
    layout="wide",
    active_label="🧱 Carbon Foundations",
)

render_hero(
    title="🧱 Carbon Foundations",
    subtitle_html=(
        "This page teaches the <b>thinking layer</b>: boundaries, baselines, assumptions, evidence, and integrity. "
        "No magic numbers — just transparent reasoning."
    ),
)

# --- Main content ---
st.markdown("## 1) Boundaries (what’s in / out)")
st.markdown(
    """
A boundary is the *system definition*. Two people can get different answers because they are describing different systems.

**Checklist**
- What assets/activities are included?
- What is explicitly excluded (and why)?
- What time window applies (and why)?
- Who owns/control vs who influences?
"""
)

st.markdown("## 2) Baselines (what would happen otherwise)")
st.markdown(
    """
A baseline is a *counterfactual story* with rules.

**Key idea:** A baseline is not a guess — it must be justified using a standard/methodology logic:
- historical performance,
- common practice,
- regulatory baseline,
- grid-average baseline,
- technology benchmark, etc.
"""
)

st.markdown("## 3) Assumptions (your real ‘inputs’)")
st.markdown(
    """
Assumptions are not weaknesses — they’re the *truth layer*.

Good practice:
- write them plainly
- tag them as **High impact / Medium / Low**
- link each to evidence or a future evidence requirement
"""
)

st.markdown("## 4) Emission factors (EFs) are context, not constants")
st.markdown(
    """
EFs change with:
- geography,
- year/version,
- market vs location basis (Scope 2),
- supplier vs generic datasets (Scope 3),
- method (LCA vs inventory vs hybrid).

Rule: if you can’t cite it, you can’t defend it.
"""
)

st.markdown("## 5) Uncertainty (how confident is your number?)")
st.markdown(
    """
Uncertainty is not optional in serious work.  
It’s how you communicate confidence and MRV readiness.

Examples of uncertainty sources:
- metering gaps,
- proxies,
- missing invoices,
- EF mismatch,
- sampling error,
- model structure.
"""
)

st.markdown("## 6) Common integrity failures (what you should watch for)")
st.markdown(
    """
- Double counting (same reduction claimed twice)
- Boundary creep (quietly expanding what’s counted)
- Baseline inflation (choosing the most favorable counterfactual)
- EF cherry-picking (selecting convenient factors)
- Missing leakage or rebound effects
"""
)

st.divider()

st.markdown("## Quick self-check (MRV maturity screening)")
st.caption("This is not an audit. It’s a fast maturity indicator for internal decision-making.")

c1, c2, c3 = st.columns(3)
with c1:
    boundary = st.slider("Boundary clarity", 0, 5, 3)
    baseline = st.slider("Baseline justification", 0, 5, 3)
with c2:
    assumptions = st.slider("Assumptions documented", 0, 5, 3)
    ef_trace = st.slider("EF traceability (cited)", 0, 5, 2)
with c3:
    data_quality = st.slider("Data quality (metering/invoices)", 0, 5, 3)
    uncertainty = st.slider("Uncertainty expressed", 0, 5, 2)

score = boundary + baseline + assumptions + ef_trace + data_quality + uncertainty
pct = (score / 30.0) * 100.0

st.metric("MRV Readiness (screening)", f"{pct:.0f}%")

if pct < 50:
    st.warning("Early-stage. Treat outputs as rough screening. Focus on boundaries, assumptions, and EF sourcing.")
elif pct < 75:
    st.info("Intermediate. Good for internal decisions and early stakeholder conversations. Tighten traceability.")
else:
    st.success("Strong. Approaching audit-ready structure (still verify against the standard/methodology).")

st.caption("Tip: Use the Registry page to store your boundaries, assumptions, data sources, and evidence checklist.")
