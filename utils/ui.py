"""
utils/ui.py

UI primitives and navigation for the Carbon Registry Streamlit app.

Design goals:
- One consistent sidebar across all pages
- Single shared CSS theme (assets/style.css)
- Safe navigation via st.switch_page

Important Streamlit rule:
- st.set_page_config(...) must be the *first Streamlit call* in each page.
  Therefore: every page should call setup_page(...) as its first Streamlit call.
"""

from __future__ import annotations

import streamlit as st
from utils.load_css import load_css


APP_TITLE = "Carbon Registry"
APP_ICON = "🌍"
APP_VERSION = "v1.0 (foundation beta)"
APP_TAGLINE = "Boundaries → Assumptions → Calculators → Evidence"


NAV_ITEMS = [
    {

        "label": "🧱 Carbon Foundations",
        "desc": "The thinking layer: boundaries, baselines, assumptions, evidence, MRV maturity.",
        "button": "Open Foundations",
        "page": "pages/0_Foundations.py",
        "badge": "Core",
    },

        "label": "⚖️ Carbon Registry",
        "desc": "Create projects, log activities, and capture boundaries + assumptions.",
        "button": "Open Carbon Registry",
        "page": "pages/1_Registry.py",
        "badge": "Core",
    },
    {
        "label": "📊 Scope 1 / 2 / 3 Calculator",
        "desc": "Baseline estimates across scopes with transparent factors + assumptions.",
        "button": "Open Scope Calculator",
        "page": "pages/2_Scope_Calculator.py",
        "badge": "Core",
    },
    {
        "label": "📘 Methodology Tools",
        "desc": "Worked examples (demo style): VM0038, AM0124, VMR0007.",
        "button": "Open Methodology Examples",
        "page": "pages/3_Methodologies.py",
        "badge": "Beta",
    },
]


def safe_switch_page(page_path: str) -> None:
    """Navigate to a Streamlit page path safely."""
    try:
        st.switch_page(page_path)
    except Exception as e:
        st.error("Navigation failed: page not found or renamed.")
        st.caption(f"Expected file: {page_path}")
        st.caption(f"Details: {e}")


def render_sidebar(active_label: str | None = None) -> None:
    """Standard sidebar used on all pages."""
    with st.sidebar:
        st.markdown(f"## {APP_ICON} {APP_TITLE}")
        st.caption(APP_VERSION)
        st.divider()

        st.markdown("### Navigation")
        for i, item in enumerate(NAV_ITEMS):
            label = item["label"]
            shown = f"{label} ✅" if (active_label and active_label == label) else label
            if st.button(shown, key=f"di_nav_{i}", use_container_width=True):
                safe_switch_page(item["page"])

        st.divider()

        with st.expander("How to use (fast)"):
            st.write("1) Define **boundaries** for a project.")
            st.write("2) Record **assumptions + data sources**.")
            st.write("3) Run **calculator demos** with transparent factors.")
            st.write("4) Export notes/results for review.")

        with st.expander("Disclaimer"):
            st.write(
                "Beta tool for learning/analysis — not audit-ready. "
                "Validate inputs/results against the applicable standard/methodology and verified datasets."
            )


def render_hero(title: str, subtitle_html: str, tagline: str = APP_TAGLINE) -> None:
    """Consistent hero block used across pages."""
    st.markdown(
        f"""
<div class="glass-box" style="padding: 26px 26px 14px 26px; margin-bottom: 16px;">
<h1 style="margin:0; color:#86ffcf; text-shadow:0 0 10px #39ff9f;">{title}</h1>
<p style="font-size:18px; margin-top:10px; color:#b3ffdd;">{subtitle_html}</p>
<p style="font-size:14px; margin-top:10px; color:#b3ffdd; opacity:0.85;">
Suggested flow: <b>{tagline}</b>
</p>
</div>
""",
        unsafe_allow_html=True,
    )


def setup_page(
    page_title: str,
    page_icon: str = APP_ICON,
    layout: str = "wide",
    *,
    active_label: str | None = None,
) -> None:
    """Page bootstrap.

    Must be called as the FIRST Streamlit call in every page.
    """
    st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
    load_css()
    render_sidebar(active_label=active_label)
