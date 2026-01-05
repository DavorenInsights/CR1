"""
Carbon_registry.py

Landing page (home hub) for the Carbon Registry Streamlit app.

Fixes:
- Uses shared setup_page() so Streamlit config + CSS + sidebar are consistent.
- No embedded CSS here (single source of truth: assets/style.css)
- Navigation paths are correct and shared across pages
"""

from __future__ import annotations

import streamlit as st
from utils.ui import APP_TITLE, APP_ICON, APP_VERSION, NAV_ITEMS, setup_page, render_hero, safe_switch_page

# MUST be first Streamlit call
setup_page(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

render_hero(
    title=f"{APP_ICON} {APP_TITLE}",
    subtitle_html=(
        "A transparent workspace for <b>boundaries</b>, <b>assumptions</b>, activity logs, and calculator demos."
        f"<br/><span style='opacity:0.85;'>Version: {APP_VERSION}</span>"
    ),
)

cols = st.columns(3)
for idx, item in enumerate(NAV_ITEMS):
    with cols[idx % 3]:
        st.markdown(
            f"""
<div class="card">
<div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
<h3 style="margin:0; color:#86ffcf;">{item['label']}</h3>
<span class="pill-badge">{item['badge']}</span>
</div>
<p style="margin-top:10px; color:#b3ffdd;">{item['desc']}</p>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button(item["button"], key=f"home_btn_{idx}", use_container_width=True):
            safe_switch_page(item["page"])

st.divider()
st.caption(
    "Disclaimer: Beta tool for learning and analysis — not audit-ready. "
    "Validate inputs/results against the applicable standard/methodology and verified datasets."
)
st.caption(f"{APP_TITLE} • {APP_VERSION}")

)
st.caption(f"{APP_TITLE} • {APP_VERSION}")
