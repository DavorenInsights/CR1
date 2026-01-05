"""
utils/load_css.py

Robust CSS loader for Streamlit multipage apps.

Key guarantees:
- Works regardless of current working directory.
- Avoids stacking CSS multiple times in the same session.
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st


def _css_path() -> Path:
    # utils/ is one level below project root
    return Path(__file__).resolve().parents[1] / "assets" / "style.css"


def load_css(force: bool = False) -> None:
    """Inject the shared CSS into the app.

    Parameters
    ----------
    force:
        If True, re-inject CSS even if it has been injected already in this session.
    """
    if not force and st.session_state.get("_di_css_loaded"):
        return

    path = _css_path()
    if not path.exists():
        st.warning("⚠️ style.css not found. Expected: assets/style.css")
        st.caption(str(path))
        return

    st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    st.session_state["_di_css_loaded"] = True
