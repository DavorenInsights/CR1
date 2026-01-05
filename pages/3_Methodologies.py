from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Tuple, Dict, Any

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from utils.ui import setup_page, render_hero

# IMPORTANT: first Streamlit call in this file
setup_page(
    page_title="Carbon Registry • Methodologies",
    page_icon="📘",
    layout="wide",
    active_label="📘 Methodology Tools",
)

render_hero(
    title="📘 Methodology Tools",
    subtitle_html="Worked examples (demo style) with transparent inputs, outputs, and saving into the emissions ledger.",
)

# ------------------------------------------------------------
# DB (SQLite) — Cloud-safe
# ------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "carbon_registry.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@st.cache_resource
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
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
    # projects table should already exist from Registry page, but we guard anyway
    db_exec(
        """
    CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY,
        project_code TEXT,
        project_name TEXT,
        status TEXT DEFAULT 'active',
        updated_at TEXT
    );
    """
    )

    # A simple emissions ledger for methodology saves
    db_exec(
        """
    CREATE TABLE IF NOT EXISTS emissions (
        emission_id TEXT PRIMARY KEY,
        project_id TEXT,
        methodology TEXT,
        record_date TEXT,
        quantity_tco2e REAL,
        notes TEXT,
        inputs_json TEXT,
        outputs_json TEXT,
        created_at TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE SET NULL
    );
    """
    )


def list_projects() -> pd.DataFrame:
    df = db_query(
        """
        SELECT project_id, project_code, project_name, status, updated_at
        FROM projects
        WHERE COALESCE(status,'active') != 'archived'
        ORDER BY updated_at DESC
    """
    )
    if df.empty:
        return df
    df["project_code"] = df["project_code"].fillna("")
    df["project_name"] = df["project_name"].fillna("")
    df["label"] = df["project_code"] + " — " + df["project_name"]
    df.loc[df["label"].str.strip() == "—", "label"] = df["project_id"]
    return df


def save_emission(
    project_id: str,
    methodology: str,
    quantity_tco2e: float,
    record_date: str,
    notes: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
) -> str:
    emission_id = str(uuid.uuid4())
    db_exec(
        """
        INSERT INTO emissions (
            emission_id, project_id, methodology, record_date,
            quantity_tco2e, notes, inputs_json, outputs_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            emission_id,
            project_id,
            methodology,
            record_date,
            float(quantity_tco2e),
            notes,
            json.dumps(inputs, ensure_ascii=False),
            json.dumps(outputs, ensure_ascii=False),
            now_iso(),
        ),
    )
    return emission_id


def render_save_panel(
    methodology: str,
    quantity_tco2e: float,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    notes_default: str = "",
):
    st.divider()
    with st.expander("💾 Save this result to Emissions Ledger", expanded=False):
        projects = list_projects()
        if projects.empty:
            st.warning(
                "No projects found yet. Go to **Carbon Registry** page and create a project first."
            )
            return

        pick = st.selectbox(
            "Select project",
            projects["label"].tolist(),
            index=0,
            key=f"{methodology}_project_pick",
        )
        project_id = projects.loc[projects["label"] == pick, "project_id"].iloc[0]

        c1, c2 = st.columns(2)
        with c1:
            rec_date = st.date_input(
                "Record date", value=date.today(), key=f"{methodology}_rec_date"
            )
        with c2:
            st.metric("Quantity (tCO₂e)", f"{quantity_tco2e:,.4f}")

        notes = st.text_area(
            "Notes",
            value=notes_default,
            height=100,
            key=f"{methodology}_notes",
        )

        if st.button("Save to ledger", type="primary", key=f"{methodology}_save_btn"):
            eid = save_emission(
                project_id=project_id,
                methodology=methodology,
                quantity_tco2e=float(quantity_tco2e),
                record_date=str(rec_date),
                notes=notes,
                inputs=inputs,
                outputs=outputs,
            )
            st.success(f"Saved ✅ Emission ID: {eid}")


# ------------------------------------------------------------
# Methodology 1: VM0038 (EV Charging) demo-style
# ------------------------------------------------------------
FUEL_EF = {
    "Petrol": 2.31,
    "Diesel": 2.68,
    "LPG": 1.51,
    "Other": None,
}  # kg CO2e/L (demo defaults)
WTT_EF = {"Petrol": 0.52, "Diesel": 0.58, "LPG": 0.21}  # kg CO2e/L (demo defaults)
FUEL_ENERGY_MJ = {
    "Petrol": 34.2,
    "Diesel": 38.6,
    "LPG": 26.8,
    "Other": 0.0,
}  # MJ/L
RENEWABLE_EF = 0.0  # kg CO2e/kWh (assumed)


def vm0038_ev():
    st.subheader("⚡ VM0038 (demo-style) — EV Charging")

    with st.expander("📘 Overview", expanded=False):
        st.markdown(
            """
This is a **VM0038-style demonstration**:
- Baseline: ICE fuel avoided (litres/year) × (EF + optional WTT)
- Project: EV charging electricity (kWh/year) × grid EF, adjusted for renewable fraction and charging efficiency
- Optional grid decarbonisation over time

**Important:** Default factors are placeholders for demo use. Replace with vetted datasets for real analysis.
            """
        )

    mode = st.radio(
        "Input method", ["Fuel avoided (baseline)", "Charger fleet (derive kWh)"], horizontal=True
    )

    left, right = st.columns([1.1, 0.9])

    with left:
        grid_ef = st.number_input(
            "Grid emission factor (kg CO₂e/kWh)",
            min_value=0.0,
            value=0.95,
            step=0.01,
            key="vm0038_grid_ef",
        )
        renewable_frac = st.slider(
            "Renewable fraction (%)", 0, 100, 0, key="vm0038_ren_frac"
        )
        include_wtt = st.checkbox(
            "Include well-to-tank (WTT) for baseline", value=True, key="vm0038_wtt"
        )
        annual_decarb = st.slider(
            "Annual grid decarbonisation (%)", 0, 20, 0, key="vm0038_decarb"
        )
        years = st.number_input(
            "Crediting period (years)", min_value=1, value=7, step=1, key="vm0038_years"
        )

    if mode == "Fuel avoided (baseline)":
        with right:
            fuel_type = st.selectbox(
                "ICE fuel type", list(FUEL_EF.keys()), index=1, key="vm0038_fuel"
            )
            litres_year = st.number_input(
                "Fuel avoided (litres/year)",
                min_value=0.0,
                value=25000.0,
                step=500.0,
                key="vm0038_litres",
            )
            if fuel_type == "Other":
                ef_tail = st.number_input(
                    "Tailpipe EF (kg CO₂e/L)",
                    min_value=0.0,
                    value=2.50,
                    step=0.01,
                    key="vm0038_other_ef",
                )
                ef_wtt = st.number_input(
                    "WTT EF (kg CO₂e/L)",
                    min_value=0.0,
                    value=0.50,
                    step=0.01,
                    key="vm0038_other_wtt",
                )
            else:
                ef_tail = float(FUEL_EF[fuel_type])
                ef_wtt = float(WTT_EF.get(fuel_type, 0.0))

            baseline_kg = float(litres_year) * (ef_tail + (ef_wtt if include_wtt else 0.0))

            # Project electricity from energy equivalence (demo approach)
            mj = float(litres_year) * float(FUEL_ENERGY_MJ.get(fuel_type, 0.0))
            # assume 1 kWh = 3.6 MJ
            kwh_year = mj / 3.6 if mj > 0 else 0.0

            charge_eff = st.slider(
                "Charging efficiency (%)", 70, 100, 90, key="vm0038_eff"
            )
            kwh_delivered = kwh_year / (charge_eff / 100.0) if charge_eff > 0 else 0.0

    else:
        with right:
            st.markdown("**Charger fleet**")
            a1, a2, a3, a4 = st.columns(4)
            with a1:
                n_chargers = st.number_input(
                    "Chargers", min_value=1, value=4, step=1, key="vm0038_n"
                )
            with a2:
                sessions_per_day = st.number_input(
                    "Sessions/charger/day",
                    min_value=0.0,
                    value=4.0,
                    step=0.5,
                    key="vm0038_spd",
                )
            with a3:
                kwh_per_session = st.number_input(
                    "kWh/session", min_value=0.0, value=20.0, step=0.5, key="vm0038_kps"
                )
            with a4:
                operating_days = st.number_input(
                    "Operating days/year", min_value=0, value=300, step=1, key="vm0038_days"
                )

            kwh_year = float(n_chargers) * sessions_per_day * kwh_per_session * float(operating_days)
            st.info(f"Derived annual electricity: **{kwh_year:,.1f} kWh/year**")
            charge_eff = st.slider("Charging efficiency (%)", 70, 100, 90, key="vm0038_eff2")
            kwh_delivered = kwh_year / (charge_eff / 100.0) if charge_eff > 0 else 0.0

            # Baseline fuel avoided derived from kWh equivalence (demo)
            # assume 2.5 kWh/L avoided (placeholder)
            litres_year = kwh_year / 2.5 if kwh_year > 0 else 0.0
            fuel_type = st.selectbox(
                "ICE fuel type (for baseline)",
                list(FUEL_EF.keys()),
                index=1,
                key="vm0038_fuel2",
            )
            if fuel_type == "Other":
                ef_tail = st.number_input(
                    "Tailpipe EF (kg CO₂e/L)", min_value=0.0, value=2.50, step=0.01, key="vm0038_other_ef2"
                )
                ef_wtt = st.number_input(
                    "WTT EF (kg CO₂e/L)", min_value=0.0, value=0.50, step=0.01, key="vm0038_other_wtt2"
                )
            else:
                ef_tail = float(FUEL_EF[fuel_type])
                ef_wtt = float(WTT_EF.get(fuel_type, 0.0))
            baseline_kg = float(litres_year) * (ef_tail + (ef_wtt if include_wtt else 0.0))

    # Project emissions with renewables + decarb
    ren_frac = float(renewable_frac) / 100.0
    eff_grid_ef = float(grid_ef) * (1.0 - ren_frac) + float(RENEWABLE_EF) * ren_frac
    project_kg_year0 = float(kwh_delivered) * eff_grid_ef

    # Apply decarbonisation over years
    series = []
    total_baseline = 0.0
    total_project = 0.0
    total_er = 0.0

    for y in range(1, int(years) + 1):
        grid_factor = (1.0 - float(annual_decarb) / 100.0) ** (y - 1)
        proj_y = project_kg_year0 * grid_factor
        base_y = baseline_kg
        er_y = max(base_y - proj_y, 0.0)

        total_baseline += base_y
        total_project += proj_y
        total_er += er_y

        series.append(
            {
                "Year": y,
                "Baseline (tCO2e)": base_y / 1000.0,
                "Project (tCO2e)": proj_y / 1000.0,
                "ER (tCO2e)": er_y / 1000.0,
            }
        )

    df = pd.DataFrame(series)

    c1, c2, c3 = st.columns(3)
    c1.metric("Baseline (tCO₂e)", f"{total_baseline/1000.0:,.3f}")
    c2.metric("Project (tCO₂e)", f"{total_project/1000.0:,.3f}")
    c3.metric("Emission Reductions (tCO₂e)", f"{total_er/1000.0:,.3f}")

    chart = (
        alt.Chart(df.melt("Year"))
        .mark_line(point=True)
        .encode(x="Year:O", y="value:Q", color="variable:N")
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)

    st.dataframe(df, use_container_width=True)

    inputs = {
        "mode": mode,
        "grid_ef_kg_per_kwh": float(grid_ef),
        "renewable_fraction_pct": float(renewable_frac),
        "include_wtt": bool(include_wtt),
        "annual_grid_decarbonisation_pct": float(annual_decarb),
        "years": int(years),
        "fuel_type": fuel_type,
        "fuel_avoided_litres_year": float(litres_year),
        "kwh_year": float(kwh_year),
        "charging_eff_pct": float(charge_eff),
        "kwh_delivered": float(kwh_delivered),
        "baseline_kg": float(baseline_kg),
    }

    outputs = {
        "total_baseline_tco2e": float(total_baseline / 1000.0),
        "total_project_tco2e": float(total_project / 1000.0),
        "total_er_tco2e": float(total_er / 1000.0),
        "yearly_table": series,
    }

    render_save_panel(
        methodology="VM0038",
        quantity_tco2e=float(total_er / 1000.0),
        inputs=inputs,
        outputs=outputs,
        notes_default="VM0038 demo-style ER calculation (replace factors with vetted datasets).",
    )


# ------------------------------------------------------------
# Methodology 2: AM0124 (Hydrogen) demo-style
# ------------------------------------------------------------
def am0124_hydrogen_app():
    st.subheader("🧪 AM0124 (demo-style) — Hydrogen via Electrolysis")

    with st.expander("📘 Overview", expanded=False):
        st.markdown(
            """
Demo framing for **AM0124-style** logic:
- Baseline: grid electricity supplying the same service (or fossil H2 route) — simplified
- Project: electricity used for electrolysis × grid EF, minus renewable share

This is not a formal applicability check; it's a structured example for transparent inputs/outputs.
            """
        )

    col1, col2 = st.columns(2)

    with col1:
        h2_tons = st.number_input("Hydrogen produced (tons/year)", min_value=0.0, value=120.0, step=5.0)
        kwh_per_kg = st.number_input("Electrolyser energy intensity (kWh/kg H2)", min_value=0.0, value=55.0, step=0.5)
        grid_ef = st.number_input("Grid EF (kg CO₂e/kWh)", min_value=0.0, value=0.95, step=0.01)
        renewable_frac = st.slider("Renewable fraction (%)", 0, 100, 0)

    with col2:
        baseline_mode = st.selectbox(
            "Baseline assumption (demo)",
            ["Grid electricity equivalent", "Grey H2 (SMR) equivalent"],
            index=0,
        )
        if baseline_mode == "Grey H2 (SMR) equivalent":
            smr_kg_per_kg = st.number_input(
                "SMR EF (kg CO₂e/kg H2) [demo]",
                min_value=0.0,
                value=9.5,
                step=0.1,
            )
        else:
            smr_kg_per_kg = 0.0

        leakage_pct = st.slider("H2 leakage (%) [demo placeholder]", 0.0, 5.0, 0.0, 0.1)
        years = st.number_input("Crediting period (years)", min_value=1, value=7, step=1)

    # Derived energy use
    h2_kg = float(h2_tons) * 1000.0
    elec_kwh = h2_kg * float(kwh_per_kg)

    ren_frac = float(renewable_frac) / 100.0
    proj_kg = elec_kwh * float(grid_ef) * (1.0 - ren_frac)

    # Baseline
    if baseline_mode == "Grey H2 (SMR) equivalent":
        base_kg = h2_kg * float(smr_kg_per_kg)
    else:
        # assume baseline would be same electricity with no renewables (demo)
        base_kg = elec_kwh * float(grid_ef)

    # Leakage penalty (demo)
    leak_penalty = base_kg * (float(leakage_pct) / 100.0)

    # ER per year
    er_kg_y = max(base_kg - proj_kg - leak_penalty, 0.0)

    # Over years
    total_base = base_kg * float(years)
    total_proj = proj_kg * float(years)
    total_pen = leak_penalty * float(years)
    total_er = er_kg_y * float(years)

    c1, c2, c3 = st.columns(3)
    c1.metric("Baseline (tCO₂e)", f"{total_base/1000.0:,.3f}")
    c2.metric("Project (tCO₂e)", f"{total_proj/1000.0:,.3f}")
    c3.metric("ER (tCO₂e)", f"{total_er/1000.0:,.3f}")

    df = pd.DataFrame(
        {
            "Metric": ["H2 produced (kg)", "Electricity (kWh)", "Leakage penalty (tCO2e/yr)", "ER (tCO2e/yr)"],
            "Value": [h2_kg, elec_kwh, leak_penalty / 1000.0, er_kg_y / 1000.0],
        }
    )
    st.dataframe(df, use_container_width=True)

    inputs = {
        "h2_tons_year": float(h2_tons),
        "kwh_per_kg": float(kwh_per_kg),
        "elec_kwh_year": float(elec_kwh),
        "grid_ef_kg_per_kwh": float(grid_ef),
        "renewable_fraction_pct": float(renewable_frac),
        "baseline_mode": baseline_mode,
        "smr_ef_kg_per_kg": float(smr_kg_per_kg),
        "leakage_pct": float(leakage_pct),
        "years": int(years),
    }
    outputs = {
        "baseline_tco2e_total": float(total_base / 1000.0),
        "project_tco2e_total": float(total_proj / 1000.0),
        "penalty_tco2e_total": float(total_pen / 1000.0),
        "er_tco2e_total": float(total_er / 1000.0),
        "er_tco2e_per_year": float(er_kg_y / 1000.0),
    }

    render_save_panel(
        methodology="AM0124",
        quantity_tco2e=float(total_er / 1000.0),
        inputs=inputs,
        outputs=outputs,
        notes_default="AM0124 demo-style ER calculation (replace assumptions/factors with vetted datasets).",
    )


# ------------------------------------------------------------
# Methodology 3: VMR0007 (Waste recovery / recycling) demo-style
# ------------------------------------------------------------
def vmr0007_app():
    st.subheader("♻️ VMR0007 (demo-style) — Waste Recovery & Recycling")

    with st.expander("📘 Overview", expanded=False):
        st.markdown(
            """
Demo framing for **VMR0007-style** logic:
- Baseline: landfill disposal with methane emissions (simplified proxy)
- Project: recycling + residue handling + transport/energy emissions (simplified proxy)

Replace all defaults with your verified method inputs and GHG parameters for real analysis.
            """
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        material = st.selectbox("Material", ["Plastic", "Paper", "Glass", "Metal"], index=0)
        tons = st.number_input("Waste processed (tons/year)", min_value=0.0, value=500.0, step=10.0)
        contamination = st.slider("Contamination (%)", 0.0, 50.0, 10.0, 1.0)

    with col2:
        landfill_ef = st.number_input(
            "Landfill EF (tCO₂e/ton) [demo]",
            min_value=0.0,
            value=1.20,
            step=0.05,
        )
        recycle_ef = st.number_input(
            "Recycling process emissions (tCO₂e/ton) [demo]",
            min_value=0.0,
            value=0.15,
            step=0.01,
        )

    with col3:
        transport_km = st.number_input("Transport distance (km) [demo]", min_value=0.0, value=80.0, step=5.0)
        transport_ef = st.number_input("Transport EF (tCO₂e/ton-km) [demo]", min_value=0.0, value=0.00012, step=0.00001, format="%.5f")
        energy_tco2e = st.number_input("Other energy emissions (tCO₂e/year) [demo]", min_value=0.0, value=5.0, step=0.5)

    clean_tons = float(tons) * (1.0 - float(contamination) / 100.0)
    residue_tons = float(tons) - clean_tons

    baseline = float(tons) * float(landfill_ef)
    project_recycling = clean_tons * float(recycle_ef)
    project_residue = residue_tons * float(landfill_ef)  # residue still landfilled (demo)
    project_transport = float(tons) * float(transport_km) * float(transport_ef)
    project_energy = float(energy_tco2e)

    project_total = project_recycling + project_residue + project_transport + project_energy
    er = max(baseline - project_total, 0.0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Baseline (tCO₂e)", f"{baseline:,.3f}")
    c2.metric("Project (tCO₂e)", f"{project_total:,.3f}")
    c3.metric("ER (tCO₂e)", f"{er:,.3f}")

    st.dataframe(
        pd.DataFrame(
            {
                "Component": [
                    "Clean tons recycled",
                    "Residue tons",
                    "Recycling emissions",
                    "Residue landfill emissions",
                    "Transport emissions",
                    "Energy emissions",
                ],
                "Value": [
                    clean_tons,
                    residue_tons,
                    project_recycling,
                    project_residue,
                    project_transport,
                    project_energy,
                ],
            }
        ),
        use_container_width=True,
    )

    inputs = {
        "material": material,
        "tons": float(tons),
        "contamination_pct": float(contamination),
        "landfill_ef_tco2e_per_ton": float(landfill_ef),
        "recycle_ef_tco2e_per_ton": float(recycle_ef),
        "transport_km": float(transport_km),
        "transport_ef_tco2e_per_ton_km": float(transport_ef),
        "energy_tco2e_year": float(energy_tco2e),
    }
    outputs = {
        "clean_tons": float(clean_tons),
        "residue_tons": float(residue_tons),
        "baseline_tco2e": float(baseline),
        "project_tco2e": float(project_total),
        "er_tco2e": float(er),
        "breakdown": {
            "recycling": float(project_recycling),
            "residue_landfill": float(project_residue),
            "transport": float(project_transport),
            "energy": float(project_energy),
        },
    }

    render_save_panel(
        methodology="VMR0007",
        quantity_tco2e=float(er),
        inputs=inputs,
        outputs=outputs,
        notes_default="VMR0007 demo-style ER calculation (replace assumptions/factors with vetted datasets).",
    )


# ------------------------------------------------------------
# Page selection / router
# ------------------------------------------------------------
ensure_schema()

st.markdown("### Choose a demo methodology")
choice = st.selectbox(
    "Methodology calculator",
    [
        "VM0038 — EV Charging",
        "AM0124 — Hydrogen (Electrolysis)",
        "VMR0007 — Waste Recovery & Recycling",
    ],
    index=0,
)

st.divider()

if choice.startswith("VM0038"):
    vm0038_ev()
elif choice.startswith("AM0124"):
    am0124_hydrogen_app()
else:
    vmr0007_app()

st.divider()
st.caption(
    "Launch note: These are demo-style reference implementations. "
    "They prove structure + data flow + audit-ready saving, not official crediting."
)

