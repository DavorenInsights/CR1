# pages/0_Foundations.py
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

import pandas as pd
import streamlit as st

from utils.ui import setup_page, render_hero


# ----------------------------
# Page bootstrap (must be first Streamlit call)
# ----------------------------
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
        "It also provides an <b>MRV Readiness</b> screening score you can save per project."
    ),
)


# ----------------------------
# DB (same DB as your other pages)
# ----------------------------
DB_PATH = Path("data/carbon_registry.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

@st.cache_resource
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def db_exec(query: str, params: Tuple = ()) -> None:
    conn = get_conn()
    conn.execute(query, params)
    conn.commit()

def db_query(query: str, params: Tuple = ()) -> pd.DataFrame:
    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    return pd.DataFrame([dict(r) for r in rows])

def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def ensure_schema() -> None:
    # Projects table already exists from Registry page, but we guard anyway
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            project_code TEXT,
            project_name TEXT,
            status TEXT,
            updated_at TEXT
        );
        """
    )

    # NEW: MRV score history table
    db_exec(
        """
        CREATE TABLE IF NOT EXISTS mrv_scores (
            mrv_id TEXT PRIMARY KEY,
            project_id TEXT,
            score_pct REAL NOT NULL,
            boundary INTEGER NOT NULL,
            baseline INTEGER NOT NULL,
            assumptions INTEGER NOT NULL,
            ef_trace INTEGER NOT NULL,
            data_quality INTEGER NOT NULL,
            uncertainty INTEGER NOT NULL,
            narrative TEXT,
            meta_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE SET NULL
        );
        """
    )

ensure_schema()


# ----------------------------
# Helpers
# ----------------------------
def list_projects() -> pd.DataFrame:
    try:
        df = db_query(
            """
            SELECT project_id, project_code, project_name, status, updated_at
            FROM projects
            ORDER BY COALESCE(updated_at,'') DESC
            """
        )
        if df.empty:
            return df
        df["project_code"] = df["project_code"].fillna("")
        df["project_name"] = df["project_name"].fillna("")
        df["label"] = df["project_code"] + " — " + df["project_name"]
        df.loc[df["label"].str.strip() == "—", "label"] = df["project_id"]
        return df
    except Exception:
        return pd.DataFrame(columns=["project_id", "project_code", "project_name", "status", "updated_at", "label"])

def build_narrative(score_pct: float, dims: Dict[str, int]) -> str:
    # Identify strengths / weaknesses
    sorted_dims = sorted(dims.items(), key=lambda kv: kv[1])
    weakest = sorted_dims[:2]
    strongest = sorted_dims[-2:]

    weak_txt = ", ".join([f"{k.replace('_',' ').title()} ({v}/5)" for k, v in weakest])
    strong_txt = ", ".join([f"{k.replace('_',' ').title()} ({v}/5)" for k, v in strongest])

    if score_pct < 50:
        stage = "Early-stage (screening only)"
        advice = "Focus on clarifying boundaries, documenting assumptions, and recording factor sources."
    elif score_pct < 75:
        stage = "Intermediate (decision-support)"
        advice = "Tighten evidence traceability and quantify uncertainty for critical inputs."
    else:
        stage = "Strong (approaching audit-ready structure)"
        advice = "Maintain traceability and align fully to the chosen standard/methodology for audit defensibility."

    return (
        f"### Carbon Integrity Narrative\n"
        f"- **MRV Readiness (screening):** {score_pct:.0f}%\n"
        f"- **Maturity stage:** {stage}\n"
        f"- **Strongest areas:** {strong_txt}\n"
        f"- **Weakest areas:** {weak_txt}\n"
        f"- **Recommendation:** {advice}\n"
        f"\n"
        f"> Note: This score is a structured clarity check, not an audit outcome.\n"
    )

def save_mrv(project_id: str, score_pct: float, dims: Dict[str, int], narrative: str, meta: Optional[Dict[str, Any]] = None) -> str:
    mrv_id = str(uuid.uuid4())
    db_exec(
        """
        INSERT INTO mrv_scores (
            mrv_id, project_id, score_pct,
            boundary, baseline, assumptions, ef_trace, data_quality, uncertainty,
            narrative, meta_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mrv_id,
            project_id,
            float(score_pct),
            int(dims["boundary"]),
            int(dims["baseline"]),
            int(dims["assumptions"]),
            int(dims["ef_trace"]),
            int(dims["data_quality"]),
            int(dims["uncertainty"]),
            narrative,
            json.dumps(meta or {}, ensure_ascii=False),
            now_iso(),
        ),
    )
    return mrv_id


# ----------------------------
# Teaching content (short + punchy)
# ----------------------------
st.markdown("## What this page is for")
st.write(
    "Before any calculator: define the **system**, defend the **baseline**, write your **assumptions**, cite your **factors**, "
    "and express **uncertainty**. That’s how you build carbon integrity."
)

with st.expander("📌 Key Concepts (quick)", expanded=False):
    st.markdown(
        """
### 1) Boundaries (what’s in / out)
A boundary is your system definition. Different boundaries → different “truth”.

### 2) Baselines (what would happen otherwise)
A baseline is a counterfactual story with rules (methodology logic).

### 3) Assumptions (your real inputs)
Assumptions are not weaknesses — they are your transparency layer.

### 4) Emission Factors (EFs)
EFs are contextual: geography, year, dataset, Scope 2 basis choice.

### 5) Uncertainty
Uncertainty is how you communicate confidence and MRV readiness.

### 6) Integrity failures to watch
Double counting, baseline inflation, boundary creep, EF cherry-picking.
        """
    )


# ----------------------------
# MRV readiness check + save
# ----------------------------
st.divider()
st.markdown("## MRV Readiness (screening-level)")
st.caption("A holistic clarity test. Save it per project and track improvement over time.")

projects = list_projects()
if projects.empty:
    st.warning("No projects found yet. Create a project in **⚖️ Carbon Registry** first.")
else:
    active_pid = st.session_state.get("active_project_id")
    options = projects["project_id"].tolist()
    default_idx = options.index(active_pid) if active_pid in options else 0

    project_id = st.selectbox(
        "Select project for MRV scoring",
        options=options,
        index=default_idx,
        format_func=lambda pid: projects.loc[projects.project_id == pid, "label"].values[0],
    )

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

    dims = {
        "boundary": boundary,
        "baseline": baseline,
        "assumptions": assumptions,
        "ef_trace": ef_trace,
        "data_quality": data_quality,
        "uncertainty": uncertainty,
    }

    narrative = build_narrative(pct, dims)
    st.markdown(narrative)

    notes = st.text_area(
        "Optional notes (what’s missing, what evidence you still need, caveats)",
        height=90,
        placeholder="Example: EF source not yet confirmed; invoices missing for Q3; baseline choice needs methodology justification...",
    )

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("💾 Save MRV Score to Project", use_container_width=True):
            mrv_id = save_mrv(
                project_id=project_id,
                score_pct=pct,
                dims=dims,
                narrative=narrative,
                meta={"notes": notes.strip() or None, "saved_on": str(date.today())},
            )
            st.success(f"Saved ✅ MRV ID: {mrv_id}")

    with colB:
        report_text = (
            f"# MRV Readiness Snapshot\n\n"
            f"- Project: {projects.loc[projects.project_id == project_id, 'label'].values[0]}\n"
            f"- Date: {date.today()}\n\n"
            f"{narrative}\n\n"
            f"### Notes\n{notes.strip() or '-'}\n"
        )
        st.download_button(
            "⬇️ Download Narrative (Markdown)",
            data=report_text.encode("utf-8"),
            file_name="mrv_readiness_snapshot.md",
            mime="text/markdown",
            use_container_width=True,
        )
