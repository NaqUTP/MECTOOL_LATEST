# streamlit_app.py
# MEC TOOL – final version with MDR.csv integration, average weightage, and full page implementations
# Author: Ahmad Naquib Syahmee Masror
# Date: 2026‑03‑09

import io
import re
import json
import warnings
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore", category=UserWarning)

# AG Grid & Plotly
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
except Exception:
    st.error("Missing streamlit-aggrid. Install: pip install streamlit-aggrid")
    st.stop()
try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:
    st.error("Missing plotly. Install: pip install plotly")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Page config – must be first Streamlit command
st.set_page_config(page_title="MEC TOOL", layout="wide")

# ──────────────────────────────────────────────────────────────────────────────
# Constants
HOURS_PER_MONTH = 176.0
N_MONTHS = 6  # fixed project duration
USD_SCHEDULES = {"schedule b", "b", "schedule d", "d"}
B_D_CATEGORY_FALLBACK = [
    "America (North/South/Canada/Australia)",
    "Middle East/Africa", "Europe", "Asia", "Japan", "Others"
]
AC_CATEGORIES = ["Malaysian", "Regional", "Expatriate"]

UNIT_TYPES = ["Minimum", "Maximum", "Normalise", "AKER", "DAR", "MMC", "TUAH", "PRW", "PUSB"]

THIRD_PARTY_CATEGORIES = ["Third Party Services"]
NON_LABOUR_CATEGORIES = ["Non-Labour Cost"]

# Discipline definitions (used for fallback only)
DISCIPLINE_ROW_COUNTS = {
    "General": 9, "Process": 5, "Mechanical Static": 5, "Mechanical Rotating": 5,
    "Mechanical Piping": 5, "Instrument and Control": 5, "Telecommunication": 5,
    "Electrical": 5, "Structural": 5, "Pipeline": 5, "Technical Safety": 5,
    "Material Corrosion Inspection": 5, "HSE": 5
}

DEFAULT_PERSONNEL = {
    "General": ["Project Manager", "Engineering Manager", "Project Engineer",
                "Lead Naval Architecture Engineer", "Planning/Scheduling Engineer",
                "Lead Cost Estimator", "Cost Controller", "General/Clerk Secretary",
                "Document Controller"],
    "Process": ["Lead Engineer Process", "Senior Engineer Process", "Engineer Process", "Drafting", "Designer"],
    "Mechanical Static": ["Lead Engineer Mechanical Static", "Senior Engineer Mechanical Static",
                          "Engineer Mechanical Static", "Drafting", "Designer"],
    "Mechanical Rotating": ["Lead Engineer Mechanical Rotating", "Senior Engineer Mechanical Rotating",
                            "Engineer Mechanical Rotating", "Drafting", "Designer"],
    "Mechanical Piping": ["Lead Engineer Piping", "Senior Engineer Piping", "Engineer Piping", "Drafting", "Designer"],
    "Instrument and Control": ["Lead Engineer Instrument", "Senior Engineer Instrument",
                               "Engineer Instrument", "Drafting", "Designer"],
    "Telecommunication": ["Lead Engineer Telecommunication", "Senior Engineer Telecommunication",
                          "Engineer Telecommunication", "Drafting", "Designer"],
    "Electrical": ["Lead Engineer Electrical", "Senior Engineer Electrical", "Engineer Electrical", "Drafting", "Designer"],
    "Structural": ["Lead Engineer C&S", "Senior Engineer C&S", "Engineer C&S", "Designer", "Drafting"],
    "Pipeline": ["Lead Engineer Pipeline", "Senior Engineer Pipeline", "Engineer Pipeline", "Drafting", "Designer"],
    "Technical Safety": ["Lead Engineer HSE", "Senior Engineer HSE", "Engineer HSE", "Designer", "Drafting"],
    "Material Corrosion Inspection": ["Lead Engineer MCI", "Senior Engineer MCI", "Engineer MCI", "Designer", "Drafting"],
    "HSE": ["Lead Engineer HSE", "Senior Engineer HSE", "Engineer HSE", "Designer", "Drafting"]
}

DISCIPLINE_COLORS = {
    "General": "FFF3E0", "Process": "E3F2FD", "Mechanical Static": "F3E5F5",
    "Mechanical Rotating": "E8F5E9", "Mechanical Piping": "FFEBEE",
    "Instrument and Control": "EDE7F6", "Telecommunication": "E0F7FA",
    "Electrical": "FCE4EC", "Structural": "F1F8E9", "Pipeline": "FFFDE7",
    "Technical Safety": "E8EAF6", "Material Corrosion Inspection": "E0F2F1",
    "HSE": "FFF8E1"
}

DISCIPLINE_SWATCH = {
    "General": "🟧", "Process": "🟦", "Mechanical Static": "🟪",
    "Mechanical Rotating": "🟩", "Mechanical Piping": "🟥",
    "Instrument and Control": "🟫", "Telecommunication": "🟦",
    "Electrical": "🟪", "Structural": "🟩", "Pipeline": "🟨",
    "Technical Safety": "⬛", "Material Corrosion Inspection": "🟩", "HSE": "🟧"
}

PAGES = {
    "MAIN": "🏠 Main",
    "TABLE": "👥 Personnel",
    "THIRD_PARTY": "💰 Third Party",
    "NON_LABOUR": "🏭 Non‑Labour",
    "LOADING": "📅 Loading",
    "TOTALS": "📊 Totals",
    "SUMMARY": "📈 Dashboard",
    "COMPARE": "🔄 Compare"
}

# Session keys
GRID_KEY = "grid_df"
THIRD_PARTY_KEY = "third_party_df"
NON_LABOUR_KEY = "non_labour_df"
MONTHLY_LOADING_KEY = "monthly_loading_df"
SAVED_PROJECTS_KEY = "saved_projects"

# ──────────────────────────────────────────────────────────────────────────────
# Session state initialisation
def init_session_state():
    if "page" not in st.session_state:
        st.session_state["page"] = "MAIN"
    if "theme_choice" not in st.session_state:
        st.session_state["theme_choice"] = "Emerald"
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False

    for proj in ["project_title", "cost_engineer", "tp_specialist"]:
        if proj not in st.session_state:
            st.session_state[proj] = ""
    if "project_date" not in st.session_state:
        st.session_state["project_date"] = None
    if "type_of_package" not in st.session_state:
        st.session_state["type_of_package"] = "U1"
    if "type_of_schedule" not in st.session_state:
        st.session_state["type_of_schedule"] = "Schedule A"
    if "rate_source" not in st.session_state:
        st.session_state["rate_source"] = "MEC.csv"

    for df_key in [GRID_KEY, THIRD_PARTY_KEY, NON_LABOUR_KEY, MONTHLY_LOADING_KEY]:
        if df_key not in st.session_state:
            st.session_state[df_key] = pd.DataFrame()
    if SAVED_PROJECTS_KEY not in st.session_state:
        st.session_state[SAVED_PROJECTS_KEY] = []

    # CSV data
    for k in ["mec_df", "schedule_opts", "personnel_list", "rate_types", "mec_data_loaded",
              "mdr_df", "mdr_data_loaded"]:
        if k not in st.session_state:
            if "df" in k:
                st.session_state[k] = pd.DataFrame()
            elif "list" in k:
                st.session_state[k] = []
            else:
                st.session_state[k] = False

init_session_state()

# ──────────────────────────────────────────────────────────────────────────────
# Theme & UI styling
THEMES = {
    "Emerald": {"brand1": "#10B981", "brand2": "#34D399", "muted": "#0d6a57"},
    "Purple": {"brand1": "#7C3AED", "brand2": "#A78BFA", "muted": "#4c2b9a"}
}

with st.sidebar:
    st.subheader("Appearance")
    theme_choice = st.radio("Theme", list(THEMES.keys()),
                            index=list(THEMES.keys()).index(st.session_state["theme_choice"]))
    dark_mode = st.toggle("🌙 Dark mode", value=st.session_state["dark_mode"])
    st.session_state["theme_choice"] = theme_choice
    st.session_state["dark_mode"] = dark_mode

PALETTE = THEMES[st.session_state["theme_choice"]]
BRAND1, BRAND2, MUTED = PALETTE["brand1"], PALETTE["brand2"], PALETTE["muted"]

def apply_theme(dark, brand1, brand2, muted):
    surface = "#0B0F14" if dark else "#FFFFFF"
    surface_alt = "#111827" if dark else "#F9FAFB"
    text = "#E5E7EB" if dark else "#111827"
    text_muted = "#9CA3AF" if dark else "#4B5563"
    st.markdown(f"""
    <style>
      :root {{
        --brand1: {brand1};
        --brand2: {brand2};
        --muted: {muted};
        --surface: {surface};
        --surface-alt: {surface_alt};
        --text: {text};
        --text-muted: {text_muted};
      }}
      .stApp {{ background: var(--surface); color: var(--text); }}
      .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: var(--text); }}
      .stCaption, p, label {{ color: var(--text-muted); }}
      div[data-testid="metric-container"] label p {{ color: var(--text-muted) !important; }}
      div[data-testid="metric-container"] div {{ color: var(--text) !important; }}
      .stButton button {{
        border: 1px solid var(--brand1);
        color: #fff; background: var(--brand1);
      }}
      .stButton button:hover {{
        filter: brightness(0.95);
      }}
      .stDataFrame, .st-emotion-cache-oco5fk {{ background: var(--surface-alt); }}
      .metric-card {{
        background: var(--surface-alt);
        border-radius: 10px;
        padding: 1.5rem;
        border-left: 4px solid var(--brand1);
        margin-bottom: 1rem;
      }}
      .metric-card h3 {{
        color: var(--text-muted);
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
      }}
      .metric-card .value {{
        color: var(--text);
        font-size: 1.8rem;
        font-weight: 700;
      }}
      .summary-card {{
        background: var(--surface-alt);
        border-radius: 10px;
        padding: 1.5rem;
        border-top: 3px solid var(--brand2);
        margin-bottom: 1.5rem;
      }}
      .comparison-badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
      }}
      .comparison-badge.up {{
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
      }}
      .comparison-badge.down {{
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
      }}
      .comparison-badge.neutral {{
        background: rgba(156, 163, 175, 0.15);
        color: #9CA3AF;
      }}
      div.stButton > button[kind="secondary"] {{
        background: transparent;
        color: var(--text);
        border: 1px solid var(--text-muted);
      }}
      div.stButton > button[kind="secondary"]:hover {{
        border-color: var(--brand1);
        color: var(--brand1);
      }}
    </style>
    """, unsafe_allow_html=True)

apply_theme(st.session_state["dark_mode"], BRAND1, BRAND2, MUTED)

# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
NBSP = "\xa0"
_num = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

def _to_float_safe(val):
    if pd.isna(val):
        return 0.0
    s = str(val).replace(",", "").replace(NBSP, " ").strip()
    s = re.sub(r"(usd|myr|rm|\$|,)", " ", s, flags=re.I)
    m = _num.search(s)
    return float(m.group(0)) if m else 0.0

def _canon(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace(NBSP, " ").strip().lower())

def _canon_sched_tag(s: str) -> str:
    t = _canon(s)
    m = re.search(r"(?:schedule\s*)?([abcd])$", t)
    return m.group(1) if m else t

def get_col(df: pd.DataFrame, name: str) -> pd.Series:
    if df.empty:
        return pd.Series([])
    if name in df.columns:
        return df[name]
    name_lower = name.lower()
    for col in df.columns:
        if col.lower() == name_lower or name_lower in col.lower():
            return df[col]
    return pd.Series([None] * len(df))

def is_usd(schedule: str) -> bool:
    return _canon(schedule) in USD_SCHEDULES or _canon_sched_tag(schedule) in {"b", "d"}

def currency_for(schedule: str) -> str:
    return "USD" if is_usd(schedule) else "MYR"

def build_category_options(schedule: str, mec_df) -> List[str]:
    if mec_df is not None and not mec_df.empty:
        df = mec_df.copy()
        if "SCHEDULES" in df.columns and schedule:
            sched_col = get_col(df, "SCHEDULES")
            if not sched_col.empty:
                df = df[sched_col.astype(str).str.contains(schedule, case=False, na=False)]
        if "CATEGORY" in df.columns:
            cats = get_col(df, "CATEGORY").dropna().astype(str).str.strip().unique().tolist()
            cats = [c for c in cats if c and c.lower() != 'nan']
            if cats:
                return sorted(cats)
    return B_D_CATEGORY_FALLBACK if is_usd(schedule) else AC_CATEGORIES

# ──────────────────────────────────────────────────────────────────────────────
# Grid initialisation (using MDR.csv)
def initialize_default_grids():
    """Create personnel grid from MDR.csv if available, else fallback to defaults with zero hours."""
    tmp_schedule = st.session_state["type_of_schedule"]
    categories = build_category_options(tmp_schedule, st.session_state.get("mec_df", pd.DataFrame()))
    if not categories:
        categories = B_D_CATEGORY_FALLBACK if is_usd(tmp_schedule) else AC_CATEGORIES

    mdr_df = st.session_state.get("mdr_df", pd.DataFrame())
    rows = []

    if not mdr_df.empty and all(c in mdr_df.columns for c in ["DISCIPLINE", "PERSONNEL", "Total (Hours)"]):
        # Use MDR data
        for _, row in mdr_df.iterrows():
            disc = str(row["DISCIPLINE"]).strip()
            pers = str(row["PERSONNEL"]).strip()
            try:
                total_hrs = float(row["Total (Hours)"])
            except:
                total_hrs = 0.0
            weightage = total_hrs / HOURS_PER_MONTH
            rows.append({
                "Swatch": DISCIPLINE_SWATCH.get(disc, "⬜"),
                "Discipline": disc,
                "Personnel": pers,
                "Category": categories[0] if categories else "",
                "Type of Unit Rate": "Normalise",
                "Total Hours": total_hrs,
                "Weightage (FTE)": weightage
            })
    else:
        # Fallback: create default personnel with zero hours
        for disc, count in DISCIPLINE_ROW_COUNTS.items():
            defaults = DEFAULT_PERSONNEL.get(disc, [])
            for i in range(count):
                pers = defaults[i] if i < len(defaults) else ""
                rows.append({
                    "Swatch": DISCIPLINE_SWATCH.get(disc, "⬜"),
                    "Discipline": disc,
                    "Personnel": pers,
                    "Category": categories[0] if categories else "",
                    "Type of Unit Rate": "Normalise",
                    "Total Hours": 0.0,
                    "Weightage (FTE)": 0.0
                })
    st.session_state[GRID_KEY] = pd.DataFrame(rows)

def reset_grid():
    initialize_default_grids()

# ──────────────────────────────────────────────────────────────────────────────
# Reset all project data (keeps saved projects)
def reset_all():
    st.session_state["project_title"] = ""
    st.session_state["cost_engineer"] = ""
    st.session_state["tp_specialist"] = ""
    st.session_state["project_date"] = None
    st.session_state["type_of_package"] = "U1"
    if st.session_state.get("schedule_opts"):
        st.session_state["type_of_schedule"] = st.session_state["schedule_opts"][0]
    else:
        st.session_state["type_of_schedule"] = "Schedule A"

    initialize_default_grids()

    # Reset third party & non‑labour
    st.session_state[THIRD_PARTY_KEY] = pd.DataFrame([{"Category": "Third Party Services", "Description": "",
                                                        "Basis": "Percentage of Labour Cost", "Percentage": 0.0,
                                                        "Fixed Amount": 0.0, "Remarks": ""}])
    st.session_state[NON_LABOUR_KEY] = pd.DataFrame([{"Category": "Non-Labour Cost", "Description": "",
                                                       "Basis": "Percentage of Labour Cost", "Percentage": 0.0,
                                                       "Fixed Amount": 0.0, "Remarks": ""}])
    months = [f"Month {i+1:02d}" for i in range(12)]  # keep 12 for loading, but note project duration is 6 months
    st.session_state[MONTHLY_LOADING_KEY] = pd.DataFrame({
        "Month": months,
        "Loading Factor (%)": [100.0]*12,
        "Weightage Distribution": [100.0/12]*12
    })

    st.session_state["page"] = "MAIN"
    st.success("Project reset. Saved projects preserved.")

# ──────────────────────────────────────────────────────────────────────────────
# CSV loaders
@st.cache_data(show_spinner=False, ttl=600)
def load_mec_csv(file_obj):
    try:
        file_obj.seek(0)
        df = pd.read_csv(file_obj)
        df.columns = [str(col).strip() for col in df.columns]
        rename = {}
        for col in df.columns:
            low = col.lower().strip()
            if 'project' in low and 'description' not in low:
                rename[col] = 'PROJECT'
            elif 'project description' in low:
                rename[col] = 'PROJECT DESCRIPTION'
            elif 'schedule' in low and 'description' not in low:
                rename[col] = 'SCHEDULES'
            elif 'schedule description' in low:
                rename[col] = 'SCHEDULES DESCRIPTION'
            elif 'category' in low:
                rename[col] = 'CATEGORY'
            elif 'personnel' in low:
                rename[col] = 'PERSONNEL'
            elif 'type of rate' in low:
                rename[col] = 'TYPE OF RATE'
            elif 'unit rate' in low:
                rename[col] = 'UNIT RATE'
            elif 'package' in low:
                rename[col] = 'PACKAGE'
        df = df.rename(columns=rename)
        return df
    except Exception as e:
        st.warning(f"Error reading MEC.csv: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=600)
def load_mdr_csv(file_obj):
    """Load MDR.csv – must contain DISCIPLINE, PERSONNEL, Month 1 ... Month 6, Total (Hours)."""
    try:
        file_obj.seek(0)
        df = pd.read_csv(file_obj)
        df.columns = [str(col).strip() for col in df.columns]

        # Expected columns: DISCIPLINE, PERSONNEL, Month 1, Month 2, ..., Month 6, Total (Hours)
        if "Total (Hours)" not in df.columns:
            st.warning("MDR.csv must contain a 'Total (Hours)' column.")
            return pd.DataFrame()
        if "DISCIPLINE" not in df.columns:
            st.warning("MDR.csv must contain a 'DISCIPLINE' column.")
            return pd.DataFrame()
        if "PERSONNEL" not in df.columns:
            st.warning("MDR.csv must contain a 'PERSONNEL' column.")
            return pd.DataFrame()

        # Keep only needed columns
        df = df[["DISCIPLINE", "PERSONNEL", "Total (Hours)"]].copy()
        df["Total (Hours)"] = pd.to_numeric(df["Total (Hours)"], errors="coerce").fillna(0)
        df = df.dropna(subset=["DISCIPLINE", "PERSONNEL"])
        df["DISCIPLINE"] = df["DISCIPLINE"].astype(str).str.strip()
        df["PERSONNEL"] = df["PERSONNEL"].astype(str).str.strip()
        return df
    except Exception as e:
        st.warning(f"Error reading MDR.csv: {e}")
        return pd.DataFrame()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar file uploads
with st.sidebar:
    st.subheader("📁 Upload MEC.csv")
    st.caption("Rates & schedules")
    mec_file = st.file_uploader("MEC.csv", type=["csv"], key="mec_uploader")
    if mec_file is not None:
        st.success("✅ MEC.csv uploaded")
        if st.button("Load MEC Data", use_container_width=True):
            st.session_state["mec_data_loaded"] = False
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("MEC.csv required")
        st.stop()

    st.subheader("📁 Upload MDR.csv")
    st.caption("Personnel hours (DISCIPLINE, PERSONNEL, Month 1‑6, Total (Hours))")
    mdr_file = st.file_uploader("MDR.csv", type=["csv"], key="mdr_uploader")
    if mdr_file is not None:
        st.success("✅ MDR.csv uploaded")
        if st.button("Load MDR Data", use_container_width=True):
            st.session_state["mdr_data_loaded"] = False
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("MDR.csv optional – using default personnel (zero hours).")

# Load MEC.csv
if mec_file is not None and not st.session_state["mec_data_loaded"]:
    with st.spinner("Loading MEC.csv..."):
        mec_df = load_mec_csv(mec_file)
        if mec_df.empty:
            st.error("Failed to load MEC.csv")
            st.stop()
        # Extract schedules
        schedule_opts = []
        if "SCHEDULES" in mec_df.columns:
            s = get_col(mec_df, "SCHEDULES").dropna().astype(str).str.strip()
            schedule_opts = sorted([v for v in s.unique() if v and v.lower() != 'nan'])
        # Personnel list (for dropdown)
        personnel_list = []
        if "PERSONNEL" in mec_df.columns:
            personnel_list.extend(get_col(mec_df, "PERSONNEL").dropna().astype(str).tolist())
        for plist in DEFAULT_PERSONNEL.values():
            personnel_list.extend(plist)
        personnel_list = sorted(set(p for p in personnel_list if p and p.lower() != 'nan'))
        # Rate types
        rate_types = []
        if "TYPE OF RATE" in mec_df.columns:
            rate_types.extend(get_col(mec_df, "TYPE OF RATE").dropna().astype(str).str.strip().unique().tolist())
        for r in UNIT_TYPES:
            if r not in rate_types:
                rate_types.append(r)
        rate_types = sorted(set(rate_types))

        st.session_state["mec_df"] = mec_df
        st.session_state["schedule_opts"] = schedule_opts
        st.session_state["personnel_list"] = personnel_list
        st.session_state["rate_types"] = rate_types
        st.session_state["mec_data_loaded"] = True
        if schedule_opts:
            st.session_state["type_of_schedule"] = schedule_opts[0]
        st.sidebar.write(f"✅ MEC.csv: {len(mec_df)} rows")
        st.sidebar.write(f"✅ {len(schedule_opts)} schedules")

        # After MEC loaded, initialise grids (if MDR also loaded later, we'll re‑init then)
        initialize_default_grids()
        st.rerun()

# Load MDR.csv
if mdr_file is not None and not st.session_state["mdr_data_loaded"]:
    with st.spinner("Loading MDR.csv..."):
        mdr_df = load_mdr_csv(mdr_file)
        st.session_state["mdr_df"] = mdr_df
        st.session_state["mdr_data_loaded"] = True
        st.sidebar.write(f"✅ MDR.csv: {len(mdr_df)} rows")
        # Re‑initialise grids to apply hours
        initialize_default_grids()
        st.rerun()

# Retrieve from session
mec_df = st.session_state.get("mec_df", pd.DataFrame())
schedule_opts = st.session_state.get("schedule_opts", [])
PERSONNEL_LIST = st.session_state.get("personnel_list", [])
RATE_TYPES = st.session_state.get("rate_types", UNIT_TYPES)
mdr_df = st.session_state.get("mdr_df", pd.DataFrame())

# Ensure grids exist
if st.session_state["mec_data_loaded"] and st.session_state[GRID_KEY].empty:
    initialize_default_grids()

# ──────────────────────────────────────────────────────────────────────────────
# Rate lookup (exact only)
def _canonical_col(df: pd.DataFrame, name: str) -> pd.Series:
    s = get_col(df, name)
    return s.astype(str).str.replace(NBSP, " ").str.strip().str.lower() if not s.empty else pd.Series([])

def _relaxed_match(df: pd.DataFrame, personnel: str, category: str, schedule: Optional[str],
                   rate_type: str, package: str) -> pd.DataFrame:
    if df.empty:
        return df
    m = df.copy()
    if "PACKAGE" in m.columns and package:
        pkg_s = _canonical_col(m, "PACKAGE")
        if not pkg_s.empty:
            pkg_target = package.lower().strip()
            m = m[pkg_s.str.contains(pkg_target, na=False)]
    if "PERSONNEL" in m.columns and personnel:
        pers_s = _canonical_col(m, "PERSONNEL")
        if not pers_s.empty:
            pers_target = personnel.lower().strip()
            exact = pers_s == pers_target
            if exact.any():
                m = m[exact]
            else:
                m = m[pers_s.str.contains(pers_target, na=False)]
    if "CATEGORY" in m.columns and category:
        cat_s = _canonical_col(m, "CATEGORY")
        if not cat_s.empty:
            cat_target = category.lower().strip()
            exact = cat_s == cat_target
            if exact.any():
                m = m[exact]
            else:
                m = m[cat_s.str.contains(cat_target, na=False)]
    if schedule and "SCHEDULES" in m.columns:
        sch_s = _canonical_col(m, "SCHEDULES")
        if not sch_s.empty:
            tag = _canon_sched_tag(schedule)
            m = m[sch_s.str.contains(tag, na=False)]
    if "TYPE OF RATE" in m.columns and rate_type:
        rate_s = _canonical_col(m, "TYPE OF RATE")
        if not rate_s.empty:
            rt = rate_type.lower().strip()
            exact = rate_s == rt
            if exact.any():
                m = m[exact]
            else:
                m = m[rate_s.str.contains(rt, na=False)]
    return m

def get_rate(mec_df: pd.DataFrame, personnel: str, category: str, unit_type: str,
             schedule: str, package: str) -> float:
    if mec_df.empty:
        return 0.0
    matches = _relaxed_match(mec_df, personnel, category, schedule, unit_type, package)
    if not matches.empty and "UNIT RATE" in matches.columns:
        val = get_col(matches, "UNIT RATE").iloc[0]
        return _to_float_safe(val)
    return 0.0

# ──────────────────────────────────────────────────────────────────────────────
# Calculations (no KPBI)
def calculate_labour_costs(grid_df: pd.DataFrame, currency: str, type_of_schedule: str,
                           type_of_package: str) -> pd.DataFrame:
    if grid_df.empty:
        return pd.DataFrame(columns=["Discipline", "Personnel", "Category", "Type of Unit Rate",
                                      f"Unit Rate ({currency})", "Total Hours", "Weightage (FTE)",
                                      f"Labour Cost ({currency})"])
    cache = {}
    def rate_for(row):
        key = (row["Personnel"], row["Category"], row["Type of Unit Rate"],
               type_of_schedule, type_of_package)
        if key in cache:
            return cache[key]
        val = get_rate(mec_df, key[0], key[1], key[2], key[3], key[4])
        cache[key] = val
        return val

    df = grid_df.copy()
    # Ensure numeric
    df["Total Hours"] = pd.to_numeric(df["Total Hours"], errors="coerce").fillna(0).astype(float)
    df["Weightage (FTE)"] = pd.to_numeric(df["Weightage (FTE)"], errors="coerce").fillna(0).astype(float)

    df[f"Unit Rate ({currency})"] = df.apply(rate_for, axis=1).astype(float)
    df[f"Labour Cost ({currency})"] = df["Total Hours"] * df[f"Unit Rate ({currency})"]
    return df[["Discipline", "Personnel", "Category", "Type of Unit Rate",
               f"Unit Rate ({currency})", "Total Hours", "Weightage (FTE)",
               f"Labour Cost ({currency})"]]

def calculate_third_party_costs(df: pd.DataFrame, total_labour: float, currency: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Category", "Description", "Basis", f"Cost ({currency})", "Remarks"])
    result = df.copy()
    result[f"Cost ({currency})"] = 0.0
    for idx, row in result.iterrows():
        basis = str(row["Basis"]).lower()
        if "percentage" in basis or "%" in basis:
            pct = float(row.get("Percentage", 0))
            result.loc[idx, f"Cost ({currency})"] = total_labour * (pct / 100.0)
        else:  # lump sum / fixed amount
            amt = float(row.get("Fixed Amount", 0))
            result.loc[idx, f"Cost ({currency})"] = amt
    return result[["Category", "Description", "Basis", f"Cost ({currency})", "Remarks"]]

def apply_monthly_loading(labour_df: pd.DataFrame, third_party_df: pd.DataFrame,
                          monthly_df: pd.DataFrame, currency: str) -> Dict:
    if monthly_df.empty:
        return {"monthly_labour": {}, "monthly_third_party": {}, "total_by_month": {}, "months": []}
    months = monthly_df["Month"].tolist()
    factors = monthly_df["Loading Factor (%)"].tolist()
    weights = monthly_df["Weightage Distribution"].tolist()
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0
    total_third = third_party_df[f"Cost ({currency})"].sum() if not third_party_df.empty else 0
    monthly_labour = {}
    monthly_third = {}
    total_by_month = {}
    for i, m in enumerate(months):
        factor = factors[i] / 100.0
        weight = weights[i] / 100.0
        monthly_labour[m] = total_labour * weight * factor
        monthly_third[m] = total_third * weight * factor
        total_by_month[m] = monthly_labour[m] + monthly_third[m]
    return {"monthly_labour": monthly_labour, "monthly_third_party": monthly_third,
            "total_by_month": total_by_month, "months": months}

def compute_totals(labour_df: pd.DataFrame, third_party_df: pd.DataFrame,
                   monthly_df: pd.DataFrame, currency: str) -> Dict:
    total_labour_exact = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0.0
    total_hours = labour_df["Total Hours"].sum() if not labour_df.empty else 0.0
    total_third = third_party_df[f"Cost ({currency})"].sum() if not third_party_df.empty else 0.0
    total_exact = total_labour_exact + total_third
    if not labour_df.empty:
        disc_totals = labour_df.groupby("Discipline", as_index=False).agg(
            Manhour=("Total Hours", "sum"),
            **{f"Labour Cost ({currency})": (f"Labour Cost ({currency})", "sum")}
        )
    else:
        disc_totals = pd.DataFrame(columns=["Discipline", "Manhour", f"Labour Cost ({currency})"])
    monthly = apply_monthly_loading(labour_df, third_party_df, monthly_df, currency)
    return {"total_hours": total_hours, "total_labour_exact": total_labour_exact,
            "total_third_party": total_third, "total_exact": total_exact,
            "discipline_totals": disc_totals, "monthly_breakdown": monthly}

# ──────────────────────────────────────────────────────────────────────────────
# Save / compare
def save_current_project():
    sched = st.session_state["type_of_schedule"]
    pkg = st.session_state["type_of_package"]
    curr = currency_for(sched)
    labour = calculate_labour_costs(st.session_state[GRID_KEY], curr, sched, pkg)
    total_lab = labour[f"Labour Cost ({curr})"].sum() if not labour.empty else 0.0
    combined = pd.concat([st.session_state[THIRD_PARTY_KEY], st.session_state.get(NON_LABOUR_KEY, pd.DataFrame())], ignore_index=True)
    third = calculate_third_party_costs(combined, total_lab, curr)
    totals = compute_totals(labour, third, st.session_state[MONTHLY_LOADING_KEY], curr)
    data = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "name": st.session_state["project_title"] or f"Project_{datetime.now():%Y%m%d_%H%M}",
        "timestamp": datetime.now().isoformat(),
        "project_title": st.session_state["project_title"],
        "type_of_schedule": sched,
        "type_of_package": pkg,
        "currency": curr,
        "total_hours": totals["total_hours"],
        "total_labour_exact": totals["total_labour_exact"],
        "total_third_party": totals["total_third_party"],
        "total_exact": totals["total_exact"],
        "discipline_totals": totals["discipline_totals"].to_dict("records") if not totals["discipline_totals"].empty else [],
        "labour_line_items": labour.to_dict("records"),
        "third_party_items": third.to_dict("records"),
        "personnel_count": len(st.session_state[GRID_KEY]),
        "disciplines_used": st.session_state[GRID_KEY]["Discipline"].nunique()
    }
    st.session_state[SAVED_PROJECTS_KEY].append(data)
    return data

def compare_projects(p1, p2):
    return {
        "hours_diff": p2["total_hours"] - p1["total_hours"],
        "hours_pct": ((p2["total_hours"] - p1["total_hours"]) / p1["total_hours"] * 100) if p1["total_hours"] else 0,
        "exact_cost_diff": p2["total_exact"] - p1["total_exact"],
        "exact_cost_pct": ((p2["total_exact"] - p1["total_exact"]) / p1["total_exact"] * 100) if p1["total_exact"] else 0,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Excel export with Summary format (including average weightage)
def to_excel_bytes(main_meta, totals, labour_df, third_party_df, monthly_df, currency):
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    # Title
    ws.merge_cells("B2:I3")
    ws["B2"] = "MAJOR ENGINEERING CONTRACT (MEC) TOOL FOR CE UPSTREAM"
    ws["B2"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["B2"].fill = PatternFill("solid", fgColor=BRAND1.replace("#",""))
    ws["B2"].alignment = Alignment(horizontal="center", vertical="center")

    # Project info
    row = 5
    for k, v in main_meta.iloc[0].items():
        ws[f"B{row}"] = k
        ws[f"C{row}"] = v
        row += 1

    # Summary table
    row += 2
    ws[f"B{row}"] = "Description"
    ws[f"C{row}"] = "Manhour"
    ws[f"D{row}"] = f"Total Price ({currency})"
    ws[f"B{row}"].font = ws[f"C{row}"].font = ws[f"D{row}"].font = Font(bold=True)
    row += 1

    # Labour Cost rows (disciplines)
    if not labour_df.empty:
        disc_sum = labour_df.groupby("Discipline").agg({"Total Hours": "sum", f"Labour Cost ({currency})": "sum"}).reset_index()
        for _, drow in disc_sum.iterrows():
            ws[f"B{row}"] = drow["Discipline"]
            ws[f"C{row}"] = drow["Total Hours"]
            ws[f"D{row}"] = drow[f"Labour Cost ({currency})"]
            row += 1

    # Third Party Services
    tp_cost = totals["total_third_party"]
    ws[f"B{row}"] = "B Third Party Services Cost(*)"
    ws[f"D{row}"] = tp_cost
    row += 1

    # Non‑Labour Cost
    non_labour_df = st.session_state.get(NON_LABOUR_KEY, pd.DataFrame())
    if not non_labour_df.empty:
        non_cost = calculate_third_party_costs(non_labour_df, totals["total_labour_exact"], currency)[f"Cost ({currency})"].sum()
        ws[f"B{row}"] = "C Non-Labour Cost"
        ws[f"D{row}"] = non_cost
        row += 1

    row += 1
    ws[f"B{row}"] = "Total Raw Bid Price (Base Scope)"
    ws[f"C{row}"] = totals["total_hours"]
    ws[f"D{row}"] = totals["total_exact"]
    ws[f"B{row}"].font = ws[f"C{row}"].font = ws[f"D{row}"].font = Font(bold=True)

    row += 2
    # Average Weightage per Month
    total_weightage = labour_df["Weightage (FTE)"].sum() if not labour_df.empty else 0
    avg_weight = total_weightage / N_MONTHS if N_MONTHS else 0
    ws[f"B{row}"] = f"Average Weightage per Month: {avg_weight:.2f}"
    row += 1
    ws[f"B{row}"] = f"RM/manhour: {currency} {totals['total_exact']/totals['total_hours'] if totals['total_hours'] else 0:,.2f}"

    # Optional: detailed labour sheet
    if not labour_df.empty:
        ws2 = wb.create_sheet("Labour Details")
        for c, col in enumerate(labour_df.columns, 1):
            ws2.cell(1, c, col)
        for r, row_data in labour_df.iterrows():
            for c, val in enumerate(row_data, 1):
                ws2.cell(r+2, c, val)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()

# ──────────────────────────────────────────────────────────────────────────────
# Navigation
def render_navigation():
    cols = st.columns(len(PAGES))
    for i, (key, label) in enumerate(PAGES.items()):
        with cols[i]:
            if st.button(label, key=f"nav_{key}", use_container_width=True,
                         type="primary" if st.session_state["page"] == key else "secondary"):
                st.session_state["page"] = key
                st.rerun()
    st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Page renderers
def render_main():
    st.markdown(f"<h1 style='color:{BRAND1}'>MEC TOOL</h1><p>Major Engineering Contract Tool</p>", unsafe_allow_html=True)
    if not mec_df.empty:
        st.caption(f"📁 MEC.csv: {len(mec_df)} rows")
    if not mdr_df.empty:
        st.caption(f"📁 MDR.csv: {len(mdr_df)} rows")

    col1, col2, col3 = st.columns([3,1,1])
    with col3:
        if st.button("🔄 New Project", use_container_width=True):
            reset_all()
            st.rerun()

    mp1, mp2 = st.columns(2)
    with mp1:
        st.session_state["project_title"] = st.text_input("Project Title", st.session_state["project_title"])
        st.session_state["cost_engineer"] = st.text_input("Cost Engineer", st.session_state["cost_engineer"])
        st.session_state["tp_specialist"] = st.text_input("TP/Specialist", st.session_state["tp_specialist"])
    with mp2:
        st.session_state["project_date"] = st.date_input("Date", st.session_state["project_date"])
        if schedule_opts:
            cur = st.session_state["type_of_schedule"]
            idx = schedule_opts.index(cur) if cur in schedule_opts else 0
            st.session_state["type_of_schedule"] = st.selectbox("Schedule", schedule_opts, index=idx)
        else:
            st.session_state["type_of_schedule"] = st.selectbox("Schedule", ["A","B","C","D"])
        st.session_state["type_of_package"] = st.selectbox("Package", ["U1","U2"],
            index=0 if st.session_state["type_of_package"]=="U1" else 1)

    st.info(f"📊 Package: {st.session_state['type_of_package']}")
    st.markdown(f"<div class='metric-card'><h3>Hours per Month</h3><div class='value'>{HOURS_PER_MONTH}</div></div>", unsafe_allow_html=True)

    b1,b2,b3 = st.columns(3)
    with b1:
        if st.button("👥 Personnel", use_container_width=True):
            st.session_state["page"] = "TABLE"
            st.rerun()
    with b2:
        if st.button("↺ Reset Grid", use_container_width=True):
            reset_grid()
            st.rerun()
    with b3:
        if st.button("💰 Third Party", use_container_width=True):
            st.session_state["page"] = "THIRD_PARTY"
            st.rerun()

def render_table():
    sched = st.session_state["type_of_schedule"]
    pkg = st.session_state["type_of_package"]
    curr = currency_for(sched)

    cats = build_category_options(sched, mec_df) or (B_D_CATEGORY_FALLBACK if is_usd(sched) else AC_CATEGORIES)

    df = st.session_state[GRID_KEY].copy()
    if df.empty:
        initialize_default_grids()
        df = st.session_state[GRID_KEY].copy()

    # Ensure Category is valid
    df["Category"] = df["Category"].where(df["Category"].isin(cats), cats[0] if cats else "")
    df["Swatch"] = df["Discipline"].map(DISCIPLINE_SWATCH).fillna("⬜")
    st.session_state[GRID_KEY] = df

    # Bulk actions (simplified)
    _, c_cat, c_type, _ = st.columns([1,2,2,1])
    with c_cat:
        st.selectbox("Category for ALL", cats, key="bulk_cat")
        if st.button("Apply Category", use_container_width=True):
            df["Category"] = st.session_state["bulk_cat"]
            st.session_state[GRID_KEY] = df
            st.rerun()
    with c_type:
        st.selectbox("Rate Type for ALL", RATE_TYPES or UNIT_TYPES, key="bulk_type")
        if st.button("Apply Rate", use_container_width=True):
            df["Type of Unit Rate"] = st.session_state["bulk_type"]
            st.session_state[GRID_KEY] = df
            st.rerun()

    # AG Grid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, sortable=True, filter=True)
    gb.configure_column("Swatch", pinned="left", width=70, editable=False)
    gb.configure_column("Discipline", pinned="left", width=190, editable=True,
                        cellEditor="agSelectCellEditor",
                        cellEditorParams={"values": list(DISCIPLINE_ROW_COUNTS.keys())})
    gb.configure_column("Personnel", width=260, editable=True,
                        cellEditor="agSelectCellEditor",
                        cellEditorParams={"values": PERSONNEL_LIST if PERSONNEL_LIST else ["Project Manager"]})
    gb.configure_column("Category", width=240, editable=True,
                        cellEditor="agSelectCellEditor", cellEditorParams={"values": cats})
    gb.configure_column("Type of Unit Rate", width=220, editable=True,
                        cellEditor="agSelectCellEditor",
                        cellEditorParams={"values": RATE_TYPES if RATE_TYPES else UNIT_TYPES})
    gb.configure_column("Total Hours", type=["numericColumn"], width=150, editable=False)
    gb.configure_column("Weightage (FTE)", type=["numericColumn"], width=150, editable=False)
    disc_bg = {k: f"#{v}" for k,v in DISCIPLINE_COLORS.items()}
    row_style = JsCode(f"""
        function(params) {{
            const map = {json.dumps(disc_bg)};
            return params.data ? {{backgroundColor: map[params.data.Discipline] || null}} : null;
        }}
    """)
    gb.configure_grid_options(getRowStyle=row_style)

    try:
        resp = AgGrid(df, gridOptions=gb.build(), height=500, update_on="value_changed",
                      allow_unsafe_jscode=True, theme="streamlit")
        st.session_state[GRID_KEY] = pd.DataFrame(resp["data"])
    except:
        st.warning("Grid update failed")

    b1,b2,b3 = st.columns(3)
    with b1:
        if st.button("➕ Add Row", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df.loc[len(df)] = {"Swatch": "⬜", "Discipline": list(DISCIPLINE_ROW_COUNTS.keys())[0],
                               "Personnel": PERSONNEL_LIST[0] if PERSONNEL_LIST else "",
                               "Category": cats[0] if cats else "", "Type of Unit Rate": "Normalise",
                               "Total Hours": 0.0, "Weightage (FTE)": 0.0}
            st.session_state[GRID_KEY] = df
            st.rerun()
    with b2:
        if st.button("↺ Reset", use_container_width=True):
            reset_grid()
            st.rerun()
    with b3:
        if st.button("📅 Next →", use_container_width=True):
            st.session_state["page"] = "LOADING"
            st.rerun()

    # Preview total
    labour = calculate_labour_costs(st.session_state[GRID_KEY], curr, sched, pkg)
    total = labour[f"Labour Cost ({curr})"].sum()
    st.markdown(f"<h3 style='color:{BRAND1}'>Total Labour: {curr} {total:,.2f}</h3>", unsafe_allow_html=True)

def render_totals():
    sched = st.session_state["type_of_schedule"]
    pkg = st.session_state["type_of_package"]
    curr = currency_for(sched)

    labour = calculate_labour_costs(st.session_state[GRID_KEY], curr, sched, pkg)
    total_lab = labour[f"Labour Cost ({curr})"].sum() if not labour.empty else 0.0
    combined = pd.concat([st.session_state[THIRD_PARTY_KEY], st.session_state.get(NON_LABOUR_KEY, pd.DataFrame())], ignore_index=True)
    third = calculate_third_party_costs(combined, total_lab, curr)
    totals = compute_totals(labour, third, st.session_state[MONTHLY_LOADING_KEY], curr)

    st.markdown(f"<div class='summary-card'><h2>Summary</h2><div>Manhours: {totals['total_hours']:,.0f}<br>Package: {pkg}</div></div>", unsafe_allow_html=True)
    st.metric("Total Exact", f"{curr} {totals['total_exact']:,.2f}")

    if not totals["discipline_totals"].empty:
        st.subheader("Labour by Discipline")
        st.dataframe(totals["discipline_totals"], use_container_width=True, hide_index=True)

    b1,b2,b3,b4 = st.columns(4)
    with b1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state["page"] = "LOADING"
            st.rerun()
    with b2:
        if st.button("💾 Save", use_container_width=True):
            save_current_project()
            st.success("Saved!")
            st.rerun()
    with b3:
        if st.button("📈 Dashboard", type="primary", use_container_width=True):
            st.session_state["page"] = "SUMMARY"
            st.rerun()
    with b4:
        if st.button("🔄 Compare", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            st.rerun()

def render_summary():
    sched = st.session_state["type_of_schedule"]
    pkg = st.session_state["type_of_package"]
    curr = currency_for(sched)

    meta = pd.DataFrame([{
        "Project Title": st.session_state["project_title"],
        "Date": str(st.session_state["project_date"]),
        "Cost Engineer": st.session_state["cost_engineer"],
        "TP/Specialist": st.session_state["tp_specialist"],
        "Schedule": sched,
        "Package": pkg,
        "Currency": curr,
        "Hours/Month": HOURS_PER_MONTH
    }])

    labour = calculate_labour_costs(st.session_state[GRID_KEY], curr, sched, pkg)
    total_lab = labour[f"Labour Cost ({curr})"].sum() if not labour.empty else 0.0
    combined = pd.concat([st.session_state[THIRD_PARTY_KEY], st.session_state.get(NON_LABOUR_KEY, pd.DataFrame())], ignore_index=True)
    third = calculate_third_party_costs(combined, total_lab, curr)
    totals = compute_totals(labour, third, st.session_state[MONTHLY_LOADING_KEY], curr)

    st.subheader("Project Information")
    st.dataframe(meta, use_container_width=True)

    st.subheader("Cost Summary")
    summary_rows = []
    if not labour.empty:
        disc_sum = labour.groupby("Discipline").agg({"Total Hours": "sum", f"Labour Cost ({curr})": "sum"}).reset_index()
        for _, row in disc_sum.iterrows():
            summary_rows.append({
                "Description": row["Discipline"],
                "Manhour": f"{row['Total Hours']:,.0f}",
                f"Total Price ({curr})": f"{row[f'Labour Cost ({curr})']:,.2f}"
            })
    tp_cost = third[f"Cost ({curr})"].sum() if not third.empty else 0.0
    summary_rows.append({
        "Description": "B Third Party Services Cost(*)",
        "Manhour": "",
        f"Total Price ({curr})": f"{tp_cost:,.2f}"
    })
    non_labour_df = st.session_state.get(NON_LABOUR_KEY, pd.DataFrame())
    if not non_labour_df.empty:
        non_cost = calculate_third_party_costs(non_labour_df, total_lab, curr)[f"Cost ({curr})"].sum()
        summary_rows.append({
            "Description": "C Non-Labour Cost",
            "Manhour": "",
            f"Total Price ({curr})": f"{non_cost:,.2f}"
        })
    summary_rows.append({
        "Description": "Total Raw Bid Price (Base Scope)",
        "Manhour": f"{totals['total_hours']:,.0f}",
        f"Total Price ({curr})": f"{totals['total_exact']:,.2f}"
    })

    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # Average Weightage per Month
    total_weightage = labour["Weightage (FTE)"].sum() if not labour.empty else 0
    avg_weight = total_weightage / N_MONTHS if N_MONTHS else 0
    st.metric("Average Weightage per Month", f"{avg_weight:.2f}")

    # RM/manhour
    if totals['total_hours']:
        st.metric("RM/manhour", f"{curr} {totals['total_exact']/totals['total_hours']:,.2f}")

    if st.button("📥 Download Excel Report", use_container_width=True):
        excel = to_excel_bytes(meta, totals, labour, third, st.session_state[MONTHLY_LOADING_KEY], curr)
        st.download_button("⬇️ Download", data=excel, file_name=f"MEC_{st.session_state['project_title'] or 'Output'}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    b1,b2,b3 = st.columns(3)
    with b1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state["page"] = "TOTALS"
            st.rerun()
    with b2:
        if st.button("💾 Save", use_container_width=True):
            save_current_project()
            st.success("Saved!")
            st.rerun()
    with b3:
        if st.button("🔄 Compare", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# Third Party page (full implementation)
def render_third_party():
    st.header("💰 Third Party Services")
    currency = currency_for(st.session_state["type_of_schedule"])

    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency,
                                       st.session_state["type_of_schedule"],
                                       st.session_state["type_of_package"])
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0

    st.info(f"Current Total Labour Cost: {currency} {total_labour:,.2f}")

    df = st.session_state[THIRD_PARTY_KEY].copy()
    if df.empty:
        df = pd.DataFrame([{"Category": "Third Party Services", "Description": "",
                            "Basis": "Percentage of Labour Cost", "Percentage": 0.0,
                            "Fixed Amount": 0.0, "Remarks": ""}])
        st.session_state[THIRD_PARTY_KEY] = df

    # Migrate old basis labels
    df["Basis"] = df["Basis"].replace({
        "% of Labour Cost": "Percentage of Labour Cost",
        "Fixed Amount": "LumpSum / Fixed Amount",
    })

    # Handle row removal
    remove_idx = st.session_state.pop("tp_remove_idx", None)
    if remove_idx is not None and remove_idx in df.index:
        df = df.drop(index=remove_idx).reset_index(drop=True)
        st.session_state[THIRD_PARTY_KEY] = df
        st.rerun()

    basis_options = ["Percentage of Labour Cost", "LumpSum / Fixed Amount"]

    for idx, row in df.iterrows():
        st.markdown(f"**Item {idx + 1}**")
        current_basis = row["Basis"] if row["Basis"] in basis_options else basis_options[0]
        is_lump = current_basis == "LumpSum / Fixed Amount"

        col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
        with col1:
            df.loc[idx, "Category"] = st.text_input(f"cat_{idx}", value=row["Category"], label_visibility="collapsed", disabled=True)
        with col2:
            df.loc[idx, "Description"] = st.text_input(f"desc_{idx}", value=row["Description"],
                                                        placeholder="Description", label_visibility="collapsed")
        with col3:
            df.loc[idx, "Basis"] = st.selectbox(f"basis_{idx}", basis_options,
                                                 index=basis_options.index(current_basis),
                                                 label_visibility="collapsed")
        with col4:
            if st.button("🗑️", key=f"tp_del_{idx}"):
                st.session_state["tp_remove_idx"] = idx
                st.rerun()

        if df.loc[idx, "Basis"] == "Percentage of Labour Cost":
            df.loc[idx, "Percentage"] = st.number_input(f"pct_{idx}", min_value=0.0, max_value=100.0,
                value=float(row.get("Percentage", 0.0)), step=0.1, format="%.1f", label_visibility="collapsed")
            df.loc[idx, "Fixed Amount"] = 0.0
        else:
            df.loc[idx, "Fixed Amount"] = st.number_input(f"amt_{idx}", min_value=0.0,
                value=float(row.get("Fixed Amount", 0.0)), step=100.0, format="%.2f", label_visibility="collapsed")
            df.loc[idx, "Percentage"] = 0.0

        st.markdown("---")

    st.session_state[THIRD_PARTY_KEY] = df

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Item", use_container_width=True):
            new = pd.DataFrame([{"Category": "Third Party Services", "Description": "",
                                 "Basis": "Percentage of Labour Cost", "Percentage": 0.0,
                                 "Fixed Amount": 0.0, "Remarks": ""}])
            st.session_state[THIRD_PARTY_KEY] = pd.concat([df, new], ignore_index=True)
            st.rerun()
    with col2:
        if st.button("🏭 Non-Labour →", use_container_width=True, type="primary"):
            st.session_state["page"] = "NON_LABOUR"
            st.rerun()

    if len(df) > 0:
        costs = calculate_third_party_costs(df, total_labour, currency)
        total = costs[f"Cost ({currency})"].sum()
        st.subheader("Calculated Costs")
        st.dataframe(costs, use_container_width=True)
        st.markdown(f"<h3 style='color:{BRAND1}'>Total: {currency} {total:,.2f}</h3>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Non-Labour page (full implementation)
def render_non_labour():
    st.header("🏭 Non-Labour Costs")
    currency = currency_for(st.session_state["type_of_schedule"])

    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency,
                                       st.session_state["type_of_schedule"],
                                       st.session_state["type_of_package"])
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0

    st.info(f"Current Total Labour Cost: {currency} {total_labour:,.2f}")

    df = st.session_state[NON_LABOUR_KEY].copy()
    if df.empty:
        df = pd.DataFrame([{"Category": "Non-Labour Cost", "Description": "",
                            "Basis": "Percentage of Labour Cost", "Percentage": 0.0,
                            "Fixed Amount": 0.0, "Remarks": ""}])
        st.session_state[NON_LABOUR_KEY] = df

    df["Basis"] = df["Basis"].replace({
        "% of Labour Cost": "Percentage of Labour Cost",
        "Fixed Amount": "LumpSum / Fixed Amount",
    })

    remove_idx = st.session_state.pop("nl_remove_idx", None)
    if remove_idx is not None and remove_idx in df.index:
        df = df.drop(index=remove_idx).reset_index(drop=True)
        st.session_state[NON_LABOUR_KEY] = df
        st.rerun()

    basis_options = ["Percentage of Labour Cost", "LumpSum / Fixed Amount"]

    for idx, row in df.iterrows():
        st.markdown(f"**Item {idx + 1}**")
        current_basis = row["Basis"] if row["Basis"] in basis_options else basis_options[0]

        col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
        with col1:
            df.loc[idx, "Category"] = st.text_input(f"nl_cat_{idx}", value=row["Category"], label_visibility="collapsed", disabled=True)
        with col2:
            df.loc[idx, "Description"] = st.text_input(f"nl_desc_{idx}", value=row["Description"],
                                                        placeholder="Description", label_visibility="collapsed")
        with col3:
            df.loc[idx, "Basis"] = st.selectbox(f"nl_basis_{idx}", basis_options,
                                                 index=basis_options.index(current_basis),
                                                 label_visibility="collapsed")
        with col4:
            if st.button("🗑️", key=f"nl_del_{idx}"):
                st.session_state["nl_remove_idx"] = idx
                st.rerun()

        if df.loc[idx, "Basis"] == "Percentage of Labour Cost":
            df.loc[idx, "Percentage"] = st.number_input(f"nl_pct_{idx}", min_value=0.0, max_value=100.0,
                value=float(row.get("Percentage", 0.0)), step=0.1, format="%.1f", label_visibility="collapsed")
            df.loc[idx, "Fixed Amount"] = 0.0
        else:
            df.loc[idx, "Fixed Amount"] = st.number_input(f"nl_amt_{idx}", min_value=0.0,
                value=float(row.get("Fixed Amount", 0.0)), step=100.0, format="%.2f", label_visibility="collapsed")
            df.loc[idx, "Percentage"] = 0.0

        st.markdown("---")

    st.session_state[NON_LABOUR_KEY] = df

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Item", use_container_width=True):
            new = pd.DataFrame([{"Category": "Non-Labour Cost", "Description": "",
                                 "Basis": "Percentage of Labour Cost", "Percentage": 0.0,
                                 "Fixed Amount": 0.0, "Remarks": ""}])
            st.session_state[NON_LABOUR_KEY] = pd.concat([df, new], ignore_index=True)
            st.rerun()
    with col2:
        if st.button("📅 Monthly Loading →", use_container_width=True, type="primary"):
            st.session_state["page"] = "LOADING"
            st.rerun()

    if len(df) > 0:
        costs = calculate_third_party_costs(df, total_labour, currency)
        total = costs[f"Cost ({currency})"].sum()
        st.subheader("Calculated Costs")
        st.dataframe(costs, use_container_width=True)
        st.markdown(f"<h3 style='color:{BRAND1}'>Total: {currency} {total:,.2f}</h3>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Monthly Loading page (full implementation)
def render_loading():
    st.header("📅 Monthly Loading")
    currency = currency_for(st.session_state["type_of_schedule"])

    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency,
                                       st.session_state["type_of_schedule"],
                                       st.session_state["type_of_package"])
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0

    combined = pd.concat([st.session_state[THIRD_PARTY_KEY], st.session_state.get(NON_LABOUR_KEY, pd.DataFrame())], ignore_index=True)
    third_party_df = calculate_third_party_costs(combined, total_labour, currency)

    df = st.session_state[MONTHLY_LOADING_KEY].copy()
    if df.empty:
        months = [f"Month {i+1:02d}" for i in range(12)]
        df = pd.DataFrame({
            "Month": months,
            "Loading Factor (%)": [100.0]*12,
            "Weightage Distribution": [100.0/12]*12
        })
        st.session_state[MONTHLY_LOADING_KEY] = df

    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        num = st.number_input("Number of Months", min_value=1, max_value=60, value=len(df), step=1)
    with col2:
        if st.button("Update", use_container_width=True) and num != len(df):
            months = [f"Month {i+1:02d}" for i in range(num)]
            if num > len(df):
                extra = pd.DataFrame({
                    "Month": months[len(df):],
                    "Loading Factor (%)": [100.0] * (num - len(df)),
                    "Weightage Distribution": [100.0/num] * (num - len(df))
                })
                df = pd.concat([df.iloc[:len(df)], extra], ignore_index=True)
            else:
                df = df.iloc[:num].reset_index(drop=True)
            df["Weightage Distribution"] = 100.0 / num
            st.session_state[MONTHLY_LOADING_KEY] = df
            st.rerun()
    with col3:
        st.info("Loading factors multiply monthly costs")

    for idx, row in df.iterrows():
        cols = st.columns(5)
        with cols[0]:
            st.write(f"**{row['Month']}**")
        with cols[1]:
            df.loc[idx, "Loading Factor (%)"] = st.number_input(f"load_{idx}", min_value=0.0, max_value=200.0,
                value=float(row["Loading Factor (%)"]), step=5.0, format="%.1f", label_visibility="collapsed")
        with cols[2]:
            df.loc[idx, "Weightage Distribution"] = st.number_input(f"w_{idx}", min_value=0.0, max_value=100.0,
                value=float(row["Weightage Distribution"]), step=0.1, format="%.1f", label_visibility="collapsed")
        with cols[3]:
            eff = (df.loc[idx, "Loading Factor (%)"] / 100) * (df.loc[idx, "Weightage Distribution"] / 100) * 100
            st.metric("Effective %", f"{eff:.1f}%")
        with cols[4]:
            cost = total_labour * (df.loc[idx, "Weightage Distribution"] / 100) * (df.loc[idx, "Loading Factor (%)"] / 100)
            st.write(f"{currency} {cost:,.0f}")

    if abs(df["Weightage Distribution"].sum() - 100) > 0.01:
        st.warning(f"Total weightage: {df['Weightage Distribution'].sum():.1f}% (should be 100%)")

    st.session_state[MONTHLY_LOADING_KEY] = df

    breakdown = apply_monthly_loading(labour_df, third_party_df, df, currency)
    preview = pd.DataFrame([{
        "Month": m,
        f"Labour ({currency})": breakdown["monthly_labour"].get(m, 0),
        f"Third Party ({currency})": breakdown["monthly_third_party"].get(m, 0),
        f"Total ({currency})": breakdown["total_by_month"].get(m, 0)
    } for m in breakdown["months"]])

    display = preview.copy()
    for col in display.columns[1:]:
        display[col] = display[col].apply(lambda x: f"{x:,.2f}")
    st.dataframe(display, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state["page"] = "NON_LABOUR"
            st.rerun()
    with col2:
        if st.button("📊 Totals", use_container_width=True, type="primary"):
            st.session_state["page"] = "TOTALS"
            st.rerun()
    with col3:
        if st.button("↺ Reset", use_container_width=True):
            months = [f"Month {i+1:02d}" for i in range(12)]
            default = pd.DataFrame({"Month": months, "Loading Factor (%)": [100.0]*12, "Weightage Distribution": [100.0/12]*12})
            st.session_state[MONTHLY_LOADING_KEY] = default
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# Compare Projects page (full implementation)
def render_compare():
    st.header("Project Comparison")

    saved = st.session_state.get(SAVED_PROJECTS_KEY, [])
    if not saved:
        st.info("No saved projects. Save from Totals or Summary page.")
        if st.button("⬅️ Back"):
            st.session_state["page"] = "SUMMARY"
            st.rerun()
        return

    display = [f"{p['name']} ({p['type_of_schedule']}, {p['type_of_package']}, {p['currency']})" for p in saved]

    col1, col2 = st.columns(2)
    with col1:
        i1 = st.selectbox("First Project", range(len(saved)), format_func=lambda i: display[i], key="c1")
    with col2:
        i2 = st.selectbox("Second Project", range(len(saved)), format_func=lambda i: display[i],
                         index=min(1, len(saved)-1), key="c2")

    if i1 == i2:
        st.warning("Select different projects")
    else:
        p1, p2 = saved[i1], saved[i2]
        comp = compare_projects(p1, p2)

        col1, col2, col3 = st.columns(3)
        with col1:
            badge = "up" if comp["hours_pct"] > 5 else "down" if comp["hours_pct"] < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Manhour Change</h3>
                    <div class="value">{comp['hours_diff']:+,.0f}</div>
                    <div><span class="comparison-badge {badge}">{comp['hours_pct']:+.1f}%</span></div>
                </div>
                """, unsafe_allow_html=True
            )
        with col2:
            badge = "up" if comp["exact_cost_pct"] > 5 else "down" if comp["exact_cost_pct"] < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Method A Change</h3>
                    <div class="value">{comp['exact_cost_diff']:+,.2f} {p2['currency']}</div>
                    <div><span class="comparison-badge {badge}">{comp['exact_cost_pct']:+.1f}%</span></div>
                </div>
                """, unsafe_allow_html=True
            )

    st.subheader("Manage Saved Projects")
    for i, p in enumerate(saved):
        cols = st.columns([3, 2, 2, 1])
        with cols[0]:
            st.write(f"**{p['name']}**")
            st.caption(f"{p['type_of_schedule']} • {p['type_of_package']} • {p['currency']}")
        with cols[1]:
            st.caption(f"Method A: {p['total_exact']:,.2f}")
        with cols[2]:
            st.caption(f"Saved: {datetime.fromisoformat(p['timestamp']).strftime('%Y-%m-%d %H:%M')}")
        with cols[3]:
            if st.button("🗑️", key=f"del_{i}"):
                saved.pop(i)
                st.session_state[SAVED_PROJECTS_KEY] = saved
                st.rerun()

    if st.button("Clear All", type="secondary"):
        st.session_state[SAVED_PROJECTS_KEY] = []
        st.rerun()

    if st.button("⬅️ Back to Summary"):
        st.session_state["page"] = "SUMMARY"
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# Main router
st.markdown(f"<h1 style='color:{BRAND1};text-align:center'>MEC TOOL</h1><p style='text-align:center'>Major Engineering Contract Tool</p>", unsafe_allow_html=True)
render_navigation()

page = st.session_state["page"]
if page == "MAIN":
    render_main()
elif page == "TABLE":
    render_table()
elif page == "THIRD_PARTY":
    render_third_party()
elif page == "NON_LABOUR":
    render_non_labour()
elif page == "LOADING":
    render_loading()
elif page == "TOTALS":
    render_totals()
elif page == "SUMMARY":
    render_summary()
elif page == "COMPARE":
    render_compare()
else:
    st.session_state["page"] = "MAIN"
    st.rerun()
