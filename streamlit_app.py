# streamlit_app.py
# MEC TOOL – Streamlit app (Single CSV version with KPBI rate from CSV)
# Author: Ahmad Naquib Syahmee Masror (Dev/Upstream)
# Date: 2025-10-29

import io
import os
import re
import json
import warnings
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import streamlit as st

# Silence harmless warnings
warnings.filterwarnings("ignore", category=UserWarning)

# AG Grid (with JsCode for custom JS)
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
except Exception:
    st.error(
        "Missing dependency streamlit-aggrid.\n\n"
        "Install first:\n\n"
        "py -m pip install streamlit-aggrid"
    )
    st.stop()

# Plotly for visuals
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except Exception:
    st.error(
        "Missing dependency plotly.\n\n"
        "Install first:\n\n"
        "py -m pip install plotly"
    )
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Page config - MUST BE FIRST STREAMLIT COMMAND
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="MEC TOOL", layout="wide")

# ──────────────────────────────────────────────────────────────────────────────
# Constants - Define these FIRST before any functions
# ──────────────────────────────────────────────────────────────────────────────
HOURS_PER_MONTH = 176.0
USD_SCHEDULES = {"schedule b", "b", "schedule d", "d"}

# Category fallbacks
B_D_CATEGORY_FALLBACK = [
    "America (North/South/Canada/Australia)",
    "Middle East/Africa",
    "Europe",
    "Asia",
    "Japan",
    "Others",
]
AC_CATEGORIES = ["Malaysian", "Regional", "Expatriate"]

# Rate types
UNIT_TYPES = [
    "Minimum", "Maximum", "Normalise", 
    "AKER", "DAR", "MMC", "TUAH", "PRW", "PUSB"
]

# Third Party Categories
THIRD_PARTY_CATEGORIES = [
    "Third Party Services",
    "Equipment Rental",
    "Software Licenses",
    "Travel & Accommodation",
    "Training",
    "Material Costs",
    "Subcontractor",
    "Other Direct Costs"
]

# Discipline configurations
DISCIPLINE_ROW_COUNTS = {
    "General": 9,
    "Process": 5,
    "Mechanical Static": 5,
    "Mechanical Rotating": 5,
    "Mechanical Piping": 5,
    "Instrument and Control": 5,
    "Telecommunication": 5,
    "Electrical": 5,
    "Structural": 5,
    "Pipeline": 5,
    "Technical Safety": 5,
    "Material Corrosion Inspection": 5,
    "HSE": 5,
}

DEFAULT_PERSONNEL = {
    "General": [
        "Project Manager",
        "Engineering Manager",
        "Project Engineer",
        "Lead Naval Architecture Engineer",
        "Planning/Scheduling Engineer",
        "Lead Cost Estimator",
        "Cost Controller",
        "General/Clerk Secretary",
        "Document Controller",
    ],
    "Process": ["Lead Engineer Process", "Senior Engineer Process", "Engineer Process", "Drafting", "Designer"],
    "Mechanical Static": [
        "Lead Engineer Mechanical Static",
        "Senior Engineer Mechanical Static",
        "Engineer Mechanical Static",
        "Drafting",
        "Designer",
    ],
    "Mechanical Rotating": [
        "Lead Engineer Mechanical Rotating",
        "Senior Engineer Mechanical Rotating",
        "Engineer Mechanical Rotating",
        "Drafting",
        "Designer",
    ],
    "Mechanical Piping": ["Lead Engineer Piping", "Senior Engineer Piping", "Engineer Piping", "Drafting", "Designer"],
    "Instrument and Control": [
        "Lead Engineer Instrument",
        "Senior Engineer Instrument",
        "Engineer Instrument",
        "Drafting",
        "Designer",
    ],
    "Telecommunication": [
        "Lead Engineer Telecommunication",
        "Senior Engineer Telecommunication",
        "Engineer Telecommunication",
        "Drafting",
        "Designer",
    ],
    "Electrical": ["Lead Engineer Electrical", "Senior Engineer Electrical", "Engineer Electrical", "Drafting", "Designer"],
    "Structural": ["Lead Engineer C&S", "Senior Engineer C&S", "Engineer C&S", "Designer", "Drafting"],
    "Pipeline": ["Lead Engineer Pipeline", "Senior Engineer Pipeline", "Engineer Pipeline", "Drafting", "Designer"],
    "Technical Safety": ["Lead Engineer HSE", "Senior Engineer HSE", "Engineer HSE", "Designer", "Drafting"],
    "Material Corrosion Inspection": ["Lead Engineer MCI", "Senior Engineer MCI", "Engineer MCI", "Designer", "Drafting"],
    "HSE": ["Lead Engineer HSE", "Senior Engineer HSE", "Engineer HSE", "Designer", "Drafting"],
}

DISCIPLINE_COLORS = {
    "General": "FFF3E0",
    "Process": "E3F2FD",
    "Mechanical Static": "F3E5F5",
    "Mechanical Rotating": "E8F5E9",
    "Mechanical Piping": "FFEBEE",
    "Instrument and Control": "EDE7F6",
    "Telecommunication": "E0F7FA",
    "Electrical": "FCE4EC",
    "Structural": "F1F8E9",
    "Pipeline": "FFFDE7",
    "Technical Safety": "E8EAF6",
    "Material Corrosion Inspection": "E0F2F1",
    "HSE": "FFF8E1",
}

DISCIPLINE_SWATCH = {
    "General": "🟧",
    "Process": "🟦",
    "Mechanical Static": "🟪",
    "Mechanical Rotating": "🟩",
    "Mechanical Piping": "🟥",
    "Instrument and Control": "🟫",
    "Telecommunication": "🟦",
    "Electrical": "🟪",
    "Structural": "🟩",
    "Pipeline": "🟨",
    "Technical Safety": "⬛",
    "Material Corrosion Inspection": "🟩",
    "HSE": "🟧",
}

# Navigation Pages
PAGES = {
    "MAIN": "🏠 Main Page",
    "TABLE": "👥 Personnel Table", 
    "THIRD_PARTY": "💰 Third Party & Non-Labour",
    "LOADING": "📅 Monthly Loading",
    "TOTALS": "📊 Totals & Line Items",
    "SUMMARY": "📈 Summary & Download",
    "COMPARE": "🔄 Compare Projects"
}

# Session state keys
GRID_KEY = "grid_df"
THIRD_PARTY_KEY = "third_party_df"
MONTHLY_LOADING_KEY = "monthly_loading_df"
SAVED_PROJECTS_KEY = "saved_projects"

# ──────────────────────────────────────────────────────────────────────────────
# Initialize session state FIRST before anything else
# ──────────────────────────────────────────────────────────────────────────────
def init_session_state():
    """Initialize all session state variables"""
    
    # Page state
    if "page" not in st.session_state:
        st.session_state["page"] = "MAIN"
    
    # Project info
    if "project_title" not in st.session_state:
        st.session_state["project_title"] = ""
    if "cost_engineer" not in st.session_state:
        st.session_state["cost_engineer"] = ""
    if "tp_specialist" not in st.session_state:
        st.session_state["tp_specialist"] = ""
    if "project_date" not in st.session_state:
        st.session_state["project_date"] = None
    if "type_of_package" not in st.session_state:
        st.session_state["type_of_package"] = "U1"
    if "type_of_schedule" not in st.session_state:
        st.session_state["type_of_schedule"] = "Schedule A"
    if "rate_source" not in st.session_state:
        st.session_state["rate_source"] = "MEC.csv"
    
    # DataFrames
    if GRID_KEY not in st.session_state:
        st.session_state[GRID_KEY] = pd.DataFrame()
    if THIRD_PARTY_KEY not in st.session_state:
        st.session_state[THIRD_PARTY_KEY] = pd.DataFrame()
    if MONTHLY_LOADING_KEY not in st.session_state:
        st.session_state[MONTHLY_LOADING_KEY] = pd.DataFrame()
    if SAVED_PROJECTS_KEY not in st.session_state:
        st.session_state[SAVED_PROJECTS_KEY] = []
    
    # CSV data
    if "mec_df" not in st.session_state:
        st.session_state["mec_df"] = pd.DataFrame()
    if "schedule_opts" not in st.session_state:
        st.session_state["schedule_opts"] = []
    if "personnel_list" not in st.session_state:
        st.session_state["personnel_list"] = []
    if "rate_types" not in st.session_state:
        st.session_state["rate_types"] = []
    if "mec_data_loaded" not in st.session_state:
        st.session_state["mec_data_loaded"] = False


# Initialize session state
init_session_state()

# ──────────────────────────────────────────────────────────────────────────────
# Theme Configuration
# ──────────────────────────────────────────────────────────────────────────────
THEMES = {
    "Emerald": {"brand1": "#10B981", "brand2": "#34D399", "muted": "#0d6a57"},
    "Purple": {"brand1": "#7C3AED", "brand2": "#A78BFA", "muted": "#4c2b9a"},
}
DEFAULT_THEME = "Emerald"

with st.sidebar:
    st.subheader("Appearance")
    theme_choice = st.radio("Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(DEFAULT_THEME))
    dark_mode = st.toggle("🌙 Dark mode", value=False, help="Switch to dark UI")

PALETTE = THEMES[theme_choice]
BRAND1, BRAND2, MUTED = PALETTE["brand1"], PALETTE["brand2"], PALETTE["muted"]


def apply_theme(dark: bool, brand1: str, brand2: str, muted: str) -> None:
    surface = "#0B0F14" if dark else "#FFFFFF"
    surface_alt = "#111827" if dark else "#F9FAFB"
    text = "#E5E7EB" if dark else "#111827"
    text_muted = "#9CA3AF" if dark else "#4B5563"

    st.markdown(
        f"""
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
      .stCaption, p, label, .st-emotion-cache-16idsys span {{ color: var(--text-muted); }}
      div[data-testid="metric-container"] label p {{ color: var(--text-muted) !important; }}
      div[data-testid="metric-container"] div {{ color: var(--text) !important; }}
      .stButton button {{
        border: 1px solid var(--brand1);
        color: #fff; background: var(--brand1);
      }}
      .stButton button:hover {{
        filter: brightness(0.95); box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand1) 30%, transparent);
      }}
      .stDataFrame, .st-emotion-cache-oco5fk, .st-emotion-cache-1k2qj1w {{
        background: var(--surface-alt);
      }}
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
        font-weight: 600;
      }}
      .metric-card .value {{
        color: var(--text);
        font-size: 1.8rem;
        font-weight: 700;
        line-height: 1.2;
      }}
      .metric-card .subvalue {{
        color: var(--brand1);
        font-size: 1rem;
        font-weight: 500;
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
        margin-bottom: 0.5rem;
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
    """,
        unsafe_allow_html=True,
    )


def do_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


apply_theme(dark_mode, BRAND1, BRAND2, MUTED)

# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────
NBSP = u"\xa0"
_num = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _to_float_safe(val: object) -> float:
    if pd.isna(val):
        return 0.0
    s = str(val).replace(",", "")
    s = s.replace(NBSP, " ").strip()
    s = re.sub(r"(usd|myr|rm|\$|,)", " ", s, flags=re.I)
    m = _num.search(s)
    return float(m.group(0)) if m else 0.0


def _canon(s: str) -> str:
    s = str(s or "").replace(NBSP, " ").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9\s]", "", s)
    return s


def _canon_sched_tag(s: str) -> str:
    t = _canon(s)
    m = re.search(r"(?:schedule\s*)?([abcd])$", t)
    return m.group(1) if m else t


def get_col(df: pd.DataFrame, name: str) -> pd.Series:
    """Safely get a column from dataframe"""
    if df.empty:
        return pd.Series([])
    if name in df.columns:
        return df[name]
    name_lower = name.lower()
    for col in df.columns:
        if col.lower() == name_lower:
            return df[col]
    for col in df.columns:
        if name_lower in col.lower():
            return df[col]
    return pd.Series([None] * len(df))


def is_usd(schedule: str) -> bool:
    return _canon(schedule) in USD_SCHEDULES or _canon_sched_tag(schedule) in {"b", "d"}


def currency_for(schedule: str) -> str:
    return "USD" if is_usd(schedule) else "MYR"


def build_category_options(schedule: str, mec_df) -> List[str]:
    """Build category options from MEC.csv"""
    if mec_df is not None and not mec_df.empty:
        df = mec_df.copy()
        if "SCHEDULES" in df.columns and schedule:
            sched_col = get_col(df, "SCHEDULES")
            if not sched_col.empty:
                df = df[sched_col.astype(str).str.contains(schedule, case=False, na=False)]
        if "CATEGORY" in df.columns:
            cats = (
                get_col(df, "CATEGORY")
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            cats = [c for c in cats if c and c.lower() != 'nan']
            if cats:
                return sorted(cats)
    return B_D_CATEGORY_FALLBACK if is_usd(schedule) else AC_CATEGORIES


# ──────────────────────────────────────────────────────────────────────────────
# Grid Initialization Functions
# ──────────────────────────────────────────────────────────────────────────────
def initialize_default_grids():
    """Initialize default grids after data is loaded"""
    tmp_schedule = st.session_state["type_of_schedule"]
    tmp_categories = build_category_options(tmp_schedule, st.session_state.get("mec_df", pd.DataFrame()))
    if not tmp_categories:
        tmp_categories = B_D_CATEGORY_FALLBACK if is_usd(tmp_schedule) else AC_CATEGORIES
    
    # Personnel Table
    rows = []
    for disc, count in DISCIPLINE_ROW_COUNTS.items():
        defaults = DEFAULT_PERSONNEL.get(disc, [])
        for i in range(count):
            personnel = defaults[i] if i < len(defaults) else (st.session_state.get("personnel_list", [""])[0] if st.session_state.get("personnel_list") else "")
            rows.append({
                "Swatch": DISCIPLINE_SWATCH.get(disc, "⬜"),
                "Discipline": disc,
                "Personnel": personnel,
                "Category": tmp_categories[0] if tmp_categories else "",
                "Type of Unit Rate": "Normalise",
                "Weightage (FTE)": 0.0,
                "Duration (months)": 1.0,
            })
    st.session_state[GRID_KEY] = pd.DataFrame(rows)
    
    # Third Party
    third_party_rows = []
    for category in THIRD_PARTY_CATEGORIES:
        third_party_rows.append({
            "Category": category,
            "Description": "",
            "Basis": "% of Labour Cost",
            "Percentage": 0.0,
            "Fixed Amount": 0.0,
            "Remarks": ""
        })
    st.session_state[THIRD_PARTY_KEY] = pd.DataFrame(third_party_rows)
    
    # Monthly Loading
    months = [f"Month {i+1:02d}" for i in range(12)]
    monthly_data = {
        "Month": months,
        "Loading Factor (%)": [100.0] * 12,
        "Weightage Distribution": [100.0/12] * 12
    }
    st.session_state[MONTHLY_LOADING_KEY] = pd.DataFrame(monthly_data)


def reset_grid():
    """Reset only the personnel grid to defaults"""
    tmp_schedule = st.session_state["type_of_schedule"]
    categories = build_category_options(tmp_schedule, st.session_state.get("mec_df", pd.DataFrame()))
    if not categories:
        categories = B_D_CATEGORY_FALLBACK if is_usd(tmp_schedule) else AC_CATEGORIES
    
    rows = []
    for disc, count in DISCIPLINE_ROW_COUNTS.items():
        defaults = DEFAULT_PERSONNEL.get(disc, [])
        for i in range(count):
            personnel = defaults[i] if i < len(defaults) else (st.session_state.get("personnel_list", [""])[0] if st.session_state.get("personnel_list") else "")
            rows.append({
                "Swatch": DISCIPLINE_SWATCH.get(disc, "⬜"),
                "Discipline": disc,
                "Personnel": personnel,
                "Category": categories[0] if categories else "",
                "Type of Unit Rate": "Normalise",
                "Weightage (FTE)": 0.0,
                "Duration (months)": 1.0,
            })
    st.session_state[GRID_KEY] = pd.DataFrame(rows)


def reset_all():
    """Reset all session state to default values but keep file data"""
    # Keep file-related data
    mec_df = st.session_state.get("mec_df", pd.DataFrame())
    schedule_opts = st.session_state.get("schedule_opts", [])
    personnel_list = st.session_state.get("personnel_list", [])
    rate_types = st.session_state.get("rate_types", [])
    data_loaded = st.session_state.get("mec_data_loaded", False)
    
    # Clear all session state except file data
    for key in list(st.session_state.keys()):
        if key not in ["mec_df", "schedule_opts", "personnel_list", "rate_types", "mec_data_loaded"]:
            del st.session_state[key]
    
    # Restore file data
    st.session_state["mec_df"] = mec_df
    st.session_state["schedule_opts"] = schedule_opts
    st.session_state["personnel_list"] = personnel_list
    st.session_state["rate_types"] = rate_types
    st.session_state["mec_data_loaded"] = data_loaded
    
    # Reset page
    st.session_state["page"] = "MAIN"
    
    # Reset project info
    st.session_state["project_title"] = ""
    st.session_state["cost_engineer"] = ""
    st.session_state["tp_specialist"] = ""
    st.session_state["project_date"] = None
    st.session_state["type_of_package"] = "U1"
    if schedule_opts:
        st.session_state["type_of_schedule"] = schedule_opts[0]
    else:
        st.session_state["type_of_schedule"] = "Schedule A"
    st.session_state["rate_source"] = "MEC.csv"
    
    # Reinitialize grids
    initialize_default_grids()


# ──────────────────────────────────────────────────────────────────────────────
# Load MEC.csv
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=600)
def load_mec_csv(file_obj):
    """Load MEC.csv with specific header format including KPBI UNIT RATE"""
    try:
        if file_obj is not None:
            file_obj.seek(0)
            df = pd.read_csv(file_obj)
            df.columns = [str(col).strip() for col in df.columns]
            
            rename_map = {}
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'project' in col_lower and 'description' not in col_lower:
                    rename_map[col] = 'PROJECT'
                elif 'project description' in col_lower:
                    rename_map[col] = 'PROJECT DESCRIPTION'
                elif 'schedule' in col_lower and 'description' not in col_lower:
                    rename_map[col] = 'SCHEDULES'
                elif 'schedule description' in col_lower:
                    rename_map[col] = 'SCHEDULES DESCRIPTION'
                elif 'category' in col_lower:
                    rename_map[col] = 'CATEGORY'
                elif 'personnel' in col_lower:
                    rename_map[col] = 'PERSONNEL'
                elif 'kpbi unit rate' in col_lower or 'kpbi' in col_lower:
                    rename_map[col] = 'KPBI UNIT RATE'
                elif 'type of rate' in col_lower:
                    rename_map[col] = 'TYPE OF RATE'
                elif 'unit rate' in col_lower:
                    rename_map[col] = 'UNIT RATE'
                elif 'package' in col_lower:
                    rename_map[col] = 'PACKAGE'
            
            df = df.rename(columns=rename_map)
            return df
    except Exception as e:
        st.warning(f"Error reading MEC.csv: {str(e)}")
        return pd.DataFrame()
    return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────────────
# File Upload Section
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("📁 Upload MEC.csv")
    st.caption("Upload the consolidated MEC.csv file")
    st.caption("Headers: PROJECT, PROJECT DESCRIPTION, SCHEDULES, SCHEDULES DESCRIPTION, CATEGORY, PERSONNEL, KPBI UNIT RATE, TYPE OF RATE, UNIT RATE, PACKAGE")
    
    mec_file = st.file_uploader(
        "MEC.csv",
        type=["csv"],
        key="mec_uploader"
    )
    
    if mec_file is not None:
        st.success("✅ MEC.csv uploaded!")
        if st.button("Load MEC Data", type="primary", use_container_width=True):
            st.session_state["mec_data_loaded"] = False
            st.cache_data.clear()
            do_rerun()
    else:
        st.warning("Please upload MEC.csv to continue.")
        st.stop()


# Load MEC data
if mec_file is not None and not st.session_state["mec_data_loaded"]:
    with st.spinner("Loading MEC.csv data..."):
        mec_df = load_mec_csv(mec_file)
        
        if mec_df.empty:
            st.error("Failed to load MEC.csv. Please check the file format.")
            st.stop()
        
        # Get schedule options
        schedule_opts = []
        if "SCHEDULES" in mec_df.columns:
            s = get_col(mec_df, "SCHEDULES").dropna().astype(str).str.strip()
            schedule_opts = sorted([v for v in s.unique().tolist() if v and v.lower() != 'nan'])

        # Get personnel list
        personnel_list = []
        if "PERSONNEL" in mec_df.columns:
            personnel_from_mec = get_col(mec_df, "PERSONNEL").dropna().astype(str).tolist()
            personnel_list.extend(personnel_from_mec)
        
        for _, plist in DEFAULT_PERSONNEL.items():
            personnel_list.extend(plist)
        
        personnel_list = [p for p in personnel_list if p and p.lower() != 'nan']
        personnel_list = sorted(set(personnel_list))

        # Get rate types
        rate_types = []
        if "TYPE OF RATE" in mec_df.columns:
            rate_from_mec = get_col(mec_df, "TYPE OF RATE").dropna().astype(str).str.strip().unique().tolist()
            rate_types.extend(rate_from_mec)
        
        for rate in UNIT_TYPES:
            if rate not in rate_types:
                rate_types.append(rate)
        
        rate_types = sorted(set(rate_types))
        
        # Store in session state
        st.session_state["mec_df"] = mec_df
        st.session_state["schedule_opts"] = schedule_opts
        st.session_state["personnel_list"] = personnel_list
        st.session_state["rate_types"] = rate_types
        st.session_state["mec_data_loaded"] = True
        
        if schedule_opts:
            st.session_state["type_of_schedule"] = schedule_opts[0]
        
        st.sidebar.write("📊 Loaded Data:")
        st.sidebar.write(f"✅ MEC.csv: {len(mec_df)} rows")
        st.sidebar.write(f"✅ {len(schedule_opts)} schedules found")
        st.sidebar.write(f"✅ KPBI UNIT RATE column found: {'KPBI UNIT RATE' in mec_df.columns}")
        
        # Now call initialize_default_grids after data is loaded
        initialize_default_grids()
        do_rerun()

# Get data from session state
mec_df = st.session_state.get("mec_df", pd.DataFrame())
schedule_opts = st.session_state.get("schedule_opts", [])
PERSONNEL_LIST = st.session_state.get("personnel_list", [])
RATE_TYPES = st.session_state.get("rate_types", UNIT_TYPES)

# Initialize grids if needed (after data is loaded and grids are empty)
if st.session_state["mec_data_loaded"] and st.session_state[GRID_KEY].empty:
    initialize_default_grids()

# ──────────────────────────────────────────────────────────────────────────────
# Rate Lookup Functions
# ──────────────────────────────────────────────────────────────────────────────
def _canonical_col(df: pd.DataFrame, name: str) -> pd.Series:
    s = get_col(df, name)
    if s.empty:
        return pd.Series([])
    return s.astype(str).str.replace(NBSP, " ").str.strip().str.lower()


def _relaxed_match(df: pd.DataFrame, personnel: str, category: str, schedule: Optional[str], 
                   rate_type: str, package: str) -> pd.DataFrame:
    """Find matching rows in dataframe with relaxed matching, including package filter"""
    if df.empty:
        return df
    
    m = df.copy()
    
    # Match package (U1 or U2)
    if "PACKAGE" in m.columns and package and str(package).strip():
        package_s = _canonical_col(m, "PACKAGE")
        if not package_s.empty:
            package_target = str(package).strip().lower()
            exact_match = package_s == package_target
            if exact_match.any():
                m = m[exact_match]
            else:
                contains_match = package_s.str.contains(package_target, na=False)
                if contains_match.any():
                    m = m[contains_match]
    
    # Match personnel
    if "PERSONNEL" in m.columns and personnel and str(personnel).strip():
        pers_s = _canonical_col(m, "PERSONNEL")
        if not pers_s.empty:
            pers_target = str(personnel).strip().lower()
            exact_match = pers_s == pers_target
            if exact_match.any():
                m = m[exact_match]
            else:
                contains_match = pers_s.str.contains(pers_target, na=False)
                if contains_match.any():
                    m = m[contains_match]
    
    # Match category
    if "CATEGORY" in m.columns and category and str(category).strip():
        cat_s = _canonical_col(m, "CATEGORY")
        if not cat_s.empty:
            cat_target = str(category).strip().lower()
            exact_match = cat_s == cat_target
            if exact_match.any():
                m = m[exact_match]
            else:
                contains_match = cat_s.str.contains(cat_target, na=False)
                if contains_match.any():
                    m = m[contains_match]
    
    # Match schedule
    if schedule and "SCHEDULES" in m.columns:
        sch_s = _canonical_col(m, "SCHEDULES")
        if not sch_s.empty:
            tag = _canon_sched_tag(schedule)
            contains_match = sch_s.str.contains(tag, na=False)
            if contains_match.any():
                m = m[contains_match]
    
    # Match rate type
    if "TYPE OF RATE" in m.columns and rate_type and str(rate_type).strip():
        rate_s = _canonical_col(m, "TYPE OF RATE")
        if not rate_s.empty:
            rate_target = str(rate_type).strip().lower()
            exact_match = rate_s == rate_target
            if exact_match.any():
                m = m[exact_match]
            else:
                contains_match = rate_s.str.contains(rate_target, na=False)
                if contains_match.any():
                    m = m[contains_match]

    return m


def get_rate(mec_df: pd.DataFrame, personnel: str, category: str, unit_type: str, 
             schedule: str, package: str) -> float:
    """Get rate from MEC.csv with package filter"""
    if mec_df is not None and not mec_df.empty:
        matches = _relaxed_match(mec_df, personnel, category, schedule, unit_type, package)
        if not matches.empty and "UNIT RATE" in matches.columns:
            rate_val = get_col(matches, "UNIT RATE").iloc[0]
            return _to_float_safe(rate_val)
    return 0.0


def get_kpbi_rate(mec_df: pd.DataFrame, personnel: str, category: str, 
                  schedule: str, package: str) -> float:
    """Get KPBI rate from MEC.csv for Method B"""
    if mec_df is not None and not mec_df.empty:
        # KPBI rate doesn't depend on rate type, just personnel, category, schedule, package
        matches = _relaxed_match(mec_df, personnel, category, schedule, "", package)
        if not matches.empty and "KPBI UNIT RATE" in matches.columns:
            kpbi_val = get_col(matches, "KPBI UNIT RATE").iloc[0]
            return _to_float_safe(kpbi_val)
    return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Calculation Functions
# ──────────────────────────────────────────────────────────────────────────────
def calculate_labour_costs(grid_df: pd.DataFrame, currency: str, type_of_schedule: str, 
                          type_of_package: str) -> pd.DataFrame:
    """Calculate labour costs from personnel table using MEC.csv with package filter"""
    if grid_df.empty:
        return pd.DataFrame(columns=[
            "Discipline", "Personnel", "Category", "Type of Unit Rate",
            f"Unit Rate ({currency})", "Weightage (FTE)", "Duration (months)",
            "Total Hours", f"Labour Cost ({currency})",
        ])

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
    for col in ["Weightage (FTE)", "Duration (months)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    df[f"Unit Rate ({currency})"] = df.apply(rate_for, axis=1).astype("float32")
    df["Total Hours"] = df["Weightage (FTE)"] * HOURS_PER_MONTH * df["Duration (months)"]
    df[f"Labour Cost ({currency})"] = df[f"Unit Rate ({currency})"] * df["Total Hours"]

    return df


def calculate_kpbi_labour_costs(grid_df: pd.DataFrame, currency: str, type_of_schedule: str, 
                               type_of_package: str) -> pd.DataFrame:
    """Calculate labour costs using KPBI rates from MEC.csv for Method B"""
    if grid_df.empty:
        return pd.DataFrame(columns=[
            "Discipline", "Personnel", "Category",
            f"KPBI Rate ({currency})", "Weightage (FTE)", "Duration (months)",
            "Total Hours", f"Labour Cost ({currency})",
        ])

    cache = {}

    def kpbi_rate_for(row):
        key = (row["Personnel"], row["Category"], type_of_schedule, type_of_package)
        if key in cache:
            return cache[key]
        val = get_kpbi_rate(mec_df, key[0], key[1], key[2], key[3])
        cache[key] = val
        return val

    df = grid_df.copy()
    for col in ["Weightage (FTE)", "Duration (months)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    df[f"KPBI Rate ({currency})"] = df.apply(kpbi_rate_for, axis=1).astype("float32")
    df["Total Hours"] = df["Weightage (FTE)"] * HOURS_PER_MONTH * df["Duration (months)"]
    df[f"Labour Cost ({currency})"] = df[f"KPBI Rate ({currency})"] * df["Total Hours"]

    return df[["Discipline", "Personnel", "Category", f"KPBI Rate ({currency})", 
               "Weightage (FTE)", "Duration (months)", "Total Hours", f"Labour Cost ({currency})"]]


def calculate_third_party_costs(df: pd.DataFrame, total_labour: float, currency: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Category", "Description", "Basis", f"Cost ({currency})", "Remarks"])
    
    result = df.copy()
    result[f"Cost ({currency})"] = 0.0
    
    for idx, row in result.iterrows():
        if row["Basis"] == "% of Labour Cost":
            result.loc[idx, f"Cost ({currency})"] = total_labour * (float(row["Percentage"]) / 100.0)
        else:
            result.loc[idx, f"Cost ({currency})"] = float(row["Fixed Amount"])
    
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
    
    for i, month in enumerate(months):
        factor = factors[i] / 100.0
        weight = weights[i] / 100.0
        monthly_labour[month] = total_labour * weight * factor
        monthly_third[month] = total_third * weight * factor
        total_by_month[month] = monthly_labour[month] + monthly_third[month]
    
    return {
        "monthly_labour": monthly_labour,
        "monthly_third_party": monthly_third,
        "total_by_month": total_by_month,
        "months": months
    }


def compute_totals(labour_df: pd.DataFrame, kpbi_labour_df: pd.DataFrame, third_party_df: pd.DataFrame, 
                  monthly_df: pd.DataFrame, currency: str) -> Dict:
    """Compute totals with Method A (Exact rates) and Method B (KPBI rates from CSV)"""
    total_labour_exact = float(labour_df[f"Labour Cost ({currency})"].sum()) if not labour_df.empty else 0.0
    total_hours = float(labour_df["Total Hours"].sum()) if not labour_df.empty else 0.0
    
    total_labour_kpbi = float(kpbi_labour_df[f"Labour Cost ({currency})"].sum()) if not kpbi_labour_df.empty else 0.0
    total_third_party = float(third_party_df[f"Cost ({currency})"].sum()) if not third_party_df.empty else 0.0
    
    total_exact = total_labour_exact + total_third_party
    total_kpbi = total_labour_kpbi + total_third_party
    
    if not labour_df.empty:
        discipline_totals = labour_df.groupby("Discipline", as_index=False).agg(
            Manhour=("Total Hours", "sum"),
            **{f"Labour Cost ({currency})": (f"Labour Cost ({currency})", "sum")},
        )
    else:
        discipline_totals = pd.DataFrame(columns=["Discipline", "Manhour", f"Labour Cost ({currency})"])
    
    monthly_breakdown = apply_monthly_loading(labour_df, third_party_df, monthly_df, currency)
    
    return {
        "total_hours": total_hours,
        "total_labour_exact": total_labour_exact,
        "total_labour_kpbi": total_labour_kpbi,
        "total_third_party": total_third_party,
        "total_exact": total_exact,
        "total_kpbi": total_kpbi,
        "discipline_totals": discipline_totals,
        "monthly_breakdown": monthly_breakdown
    }


# ──────────────────────────────────────────────────────────────────────────────
# Project Save/Load Functions
# ──────────────────────────────────────────────────────────────────────────────
def save_current_project():
    type_of_schedule = st.session_state["type_of_schedule"]
    type_of_package = st.session_state["type_of_package"]
    currency = currency_for(type_of_schedule)
    
    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, type_of_schedule, type_of_package)
    kpbi_labour_df = calculate_kpbi_labour_costs(st.session_state[GRID_KEY], currency, type_of_schedule, type_of_package)
    total_labour = float(labour_df[f"Labour Cost ({currency})"].sum()) if not labour_df.empty else 0.0
    third_party_df = calculate_third_party_costs(st.session_state[THIRD_PARTY_KEY], total_labour, currency)
    totals = compute_totals(labour_df, kpbi_labour_df, third_party_df, st.session_state[MONTHLY_LOADING_KEY], currency)
    
    project_data = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "name": st.session_state["project_title"] or f"Project_{datetime.now().strftime('%Y%m%d_%H%M')}",
        "timestamp": datetime.now().isoformat(),
        "project_title": st.session_state["project_title"],
        "type_of_schedule": type_of_schedule,
        "type_of_package": type_of_package,
        "currency": currency,
        "total_hours": totals["total_hours"],
        "total_labour_exact": totals["total_labour_exact"],
        "total_labour_kpbi": totals["total_labour_kpbi"],
        "total_third_party": totals["total_third_party"],
        "total_exact": totals["total_exact"],
        "total_kpbi": totals["total_kpbi"],
        "discipline_totals": totals["discipline_totals"].to_dict('records') if not totals["discipline_totals"].empty else [],
        "labour_line_items": labour_df.to_dict('records'),
        "kpbi_labour_line_items": kpbi_labour_df.to_dict('records'),
        "third_party_items": third_party_df.to_dict('records'),
        "personnel_count": len(st.session_state[GRID_KEY]),
        "disciplines_used": st.session_state[GRID_KEY]["Discipline"].nunique()
    }
    
    st.session_state[SAVED_PROJECTS_KEY].append(project_data)
    return project_data


def compare_projects(p1, p2):
    return {
        "hours_diff": p2["total_hours"] - p1["total_hours"],
        "hours_pct": ((p2["total_hours"] - p1["total_hours"]) / p1["total_hours"] * 100) if p1["total_hours"] > 0 else 0,
        "exact_cost_diff": p2["total_exact"] - p1["total_exact"],
        "exact_cost_pct": ((p2["total_exact"] - p1["total_exact"]) / p1["total_exact"] * 100) if p1["total_exact"] > 0 else 0,
        "kpbi_cost_diff": p2["total_kpbi"] - p1["total_kpbi"],
        "kpbi_cost_pct": ((p2["total_kpbi"] - p1["total_kpbi"]) / p1["total_kpbi"] * 100) if p1["total_kpbi"] > 0 else 0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Excel Export Function
# ──────────────────────────────────────────────────────────────────────────────
def to_excel_bytes(main_meta: pd.DataFrame, totals: dict, labour_df: pd.DataFrame, 
                   kpbi_labour_df: pd.DataFrame, third_party_df: pd.DataFrame, 
                   monthly_df: pd.DataFrame, schedule_label: str, currency: str):
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    wb = Workbook()
    BRAND_HEX = BRAND1.replace("#", "")
    LIGHT = "E6F9F7"
    WHITE = "FFFFFF"
    THIN = Side(style="thin", color="999999")

    # Main Page
    ws = wb.active
    ws.title = "Main Page"
    ws.merge_cells("B2:I3")
    ws["B2"].value = "MAJOR ENGINEERING CONTRACT (MEC) TOOL FOR CE UPSTREAM"
    
    # Add project info
    row = 5
    for col, value in main_meta.iloc[0].items():
        ws.cell(row=row, column=2, value=col)
        ws.cell(row=row, column=3, value=value)
        row += 1
    
    # Labour Costs Sheet (Method A)
    ws2 = wb.create_sheet("Labour Costs - Method A")
    for c, col in enumerate(labour_df.columns, 1):
        ws2.cell(row=1, column=c, value=col)
    for r, row in labour_df.iterrows():
        for c, value in enumerate(row, 1):
            ws2.cell(row=r+2, column=c, value=value)
    
    # Labour Costs Sheet (Method B - KPBI)
    ws2b = wb.create_sheet("Labour Costs - Method B (KPBI)")
    for c, col in enumerate(kpbi_labour_df.columns, 1):
        ws2b.cell(row=1, column=c, value=col)
    for r, row in kpbi_labour_df.iterrows():
        for c, value in enumerate(row, 1):
            ws2b.cell(row=r+2, column=c, value=value)
    
    # Third Party Sheet
    ws3 = wb.create_sheet("Third Party")
    for c, col in enumerate(third_party_df.columns, 1):
        ws3.cell(row=1, column=c, value=col)
    for r, row in third_party_df.iterrows():
        for c, value in enumerate(row, 1):
            ws3.cell(row=r+2, column=c, value=value)
    
    # Monthly Loading Sheet
    ws4 = wb.create_sheet("Monthly Loading")
    monthly_with_costs = monthly_df.copy()
    monthly_with_costs[f"Labour A ({currency})"] = [totals["monthly_breakdown"]["monthly_labour"].get(m, 0) for m in monthly_df["Month"]]
    monthly_with_costs[f"Third Party ({currency})"] = [totals["monthly_breakdown"]["monthly_third_party"].get(m, 0) for m in monthly_df["Month"]]
    monthly_with_costs[f"Total A ({currency})"] = [totals["monthly_breakdown"]["total_by_month"].get(m, 0) for m in monthly_df["Month"]]
    
    for c, col in enumerate(monthly_with_costs.columns, 1):
        ws4.cell(row=1, column=c, value=col)
    for r, row in monthly_with_costs.iterrows():
        for c, value in enumerate(row, 1):
            ws4.cell(row=r+2, column=c, value=value)
    
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Navigation Function
# ──────────────────────────────────────────────────────────────────────────────
def render_navigation():
    current_page = st.session_state["page"]
    cols = st.columns(len(PAGES))
    
    for idx, (page_key, page_label) in enumerate(PAGES.items()):
        with cols[idx]:
            if st.button(page_label, key=f"nav_{page_key}", use_container_width=True,
                        type="primary" if current_page == page_key else "secondary"):
                st.session_state["page"] = page_key
                do_rerun()
    
    st.markdown("---")


# ──────────────────────────────────────────────────────────────────────────────
# Page Renderers
# ──────────────────────────────────────────────────────────────────────────────
def render_main():
    st.markdown(
        f"""
        <h1 style="color: var(--brand1); margin-bottom: 0.5rem;">MEC TOOL</h1>
        <p style="color: var(--text-muted); font-size: 1.1rem; margin-bottom: 2rem;">
          Major Engineering Contract Tool for CE Upstream
        </p>
        """,
        unsafe_allow_html=True
    )
    
    if not mec_df.empty:
        st.caption(f"📁 Loaded: MEC.csv ({len(mec_df)} rows)")
        has_kpbi = "KPBI UNIT RATE" in mec_df.columns
        st.caption(f"✅ KPBI rates available: {has_kpbi}")

    st.markdown("<hr style='margin: 2rem 0;'/>", unsafe_allow_html=True)
    st.header("Main Page")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col3:
        if st.button("🔄 New Project", type="secondary", use_container_width=True):
            reset_all()
            st.success("Started new project!")
            do_rerun()

    mp1, mp2 = st.columns(2)
    with mp1:
        st.session_state["project_title"] = st.text_input("Project Title", value=st.session_state["project_title"])
        st.session_state["cost_engineer"] = st.text_input("Cost Engineer", value=st.session_state["cost_engineer"])
        st.session_state["tp_specialist"] = st.text_input("TP/Specialist", value=st.session_state["tp_specialist"])

    with mp2:
        st.session_state["project_date"] = st.date_input("Date", value=st.session_state["project_date"])
        
        # Schedule selection
        if schedule_opts:
            current = st.session_state["type_of_schedule"]
            if current not in schedule_opts:
                current = schedule_opts[0]
                st.session_state["type_of_schedule"] = current
            st.session_state["type_of_schedule"] = st.selectbox(
                "Type of Schedule", schedule_opts,
                index=schedule_opts.index(current) if current in schedule_opts else 0
            )
        else:
            st.session_state["type_of_schedule"] = st.selectbox(
                "Type of Schedule", ["Schedule A", "Schedule B", "Schedule C", "Schedule D"], index=0
            )
        
        # Package selection (U1/U2)
        st.session_state["type_of_package"] = st.selectbox(
            "Package Type",
            ["U1", "U2"],
            index=0 if st.session_state["type_of_package"] == "U1" else 1
        )

    st.info(f"📊 Rate Source: MEC.csv - Package: {st.session_state['type_of_package']}")
    
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Hours per Month (constant)</h3>
            <div class="value">{HOURS_PER_MONTH:,.0f} hrs</div>
            <div class="subvalue">Hours = Weightage × 176 × Duration</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➡️ Go to Personnel Table", use_container_width=True, type="primary"):
            st.session_state["page"] = "TABLE"
            do_rerun()
    with c2:
        if st.button("↺ Reset Grid to Defaults", use_container_width=True):
            reset_grid()
            st.success("Grid reset to defaults!")
            do_rerun()
    with c3:
        if st.button("💰 Third Party Costs", use_container_width=True):
            st.session_state["page"] = "THIRD_PARTY"
            do_rerun()


def render_table():
    type_of_schedule = st.session_state["type_of_schedule"]
    type_of_package = st.session_state["type_of_package"]
    currency = currency_for(type_of_schedule)

    categories = build_category_options(type_of_schedule, mec_df)
    if not categories:
        categories = B_D_CATEGORY_FALLBACK if is_usd(type_of_schedule) else AC_CATEGORIES

    st.header(f"Personnel Table — Currency: {currency} (Package: {type_of_package})")

    df = st.session_state[GRID_KEY].copy()
    if df.empty:
        initialize_default_grids()
        df = st.session_state[GRID_KEY].copy()
    
    if "Category" in df.columns and categories:
        df["Category"] = df["Category"].where(df["Category"].isin(categories), categories[0])
    df["Swatch"] = df["Discipline"].map(DISCIPLINE_SWATCH).fillna("⬜")
    st.session_state[GRID_KEY] = df

    # Bulk actions
    st.subheader("Bulk actions")
    c_w, c_cat, c_type, c_dur = st.columns(4)
    with c_w:
        new_w = st.number_input("Weightage for ALL", min_value=0.0, step=0.1, value=0.0, key="bulk_w")
        if st.button("Apply", key="apply_w", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df["Weightage (FTE)"] = float(st.session_state["bulk_w"])
            st.session_state[GRID_KEY] = df
            st.success("Applied!")
            do_rerun()
    with c_cat:
        new_cat = st.selectbox("Category for ALL", categories, key="bulk_cat")
        if st.button("Apply", key="apply_cat", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df["Category"] = st.session_state["bulk_cat"]
            st.session_state[GRID_KEY] = df
            st.success("Applied!")
            do_rerun()
    with c_type:
        new_type = st.selectbox("Rate Type for ALL", RATE_TYPES if RATE_TYPES else UNIT_TYPES, key="bulk_type")
        if st.button("Apply", key="apply_type", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df["Type of Unit Rate"] = st.session_state["bulk_type"]
            st.session_state[GRID_KEY] = df
            st.success("Applied!")
            do_rerun()
    with c_dur:
        new_dur = st.number_input("Duration for ALL", min_value=0, step=1, value=1, key="bulk_dur")
        if st.button("Apply", key="apply_dur", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df["Duration (months)"] = int(st.session_state["bulk_dur"])
            st.session_state[GRID_KEY] = df
            st.success("Applied!")
            do_rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➕ Add Row", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df.loc[len(df)] = {
                "Swatch": "⬜",
                "Discipline": list(DISCIPLINE_ROW_COUNTS.keys())[0],
                "Personnel": PERSONNEL_LIST[0] if PERSONNEL_LIST else "",
                "Category": categories[0] if categories else "",
                "Type of Unit Rate": "Normalise",
                "Weightage (FTE)": 0.0,
                "Duration (months)": 1.0,
            }
            st.session_state[GRID_KEY] = df
            do_rerun()
    with c2:
        if st.button("↺ Reset", use_container_width=True):
            reset_grid()
            do_rerun()
    with c3:
        if st.button("📅 Next", use_container_width=True):
            st.session_state["page"] = "LOADING"
            do_rerun()

    # AG Grid
    df = st.session_state[GRID_KEY].copy()
    for col in ["Weightage (FTE)", "Duration (months)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_grid_options(rowHeight=34, headerHeight=36)
    gb.configure_default_column(resizable=True, sortable=True, filter=True)

    gb.configure_column("Swatch", pinned="left", width=70, editable=False)
    gb.configure_column("Discipline", pinned="left", width=190, editable=True,
                       cellEditor="agSelectCellEditor",
                       cellEditorParams={"values": list(DISCIPLINE_ROW_COUNTS.keys())})
    gb.configure_column("Personnel", width=260, editable=True,
                       cellEditor="agSelectCellEditor",
                       cellEditorParams={"values": PERSONNEL_LIST if PERSONNEL_LIST else ["Project Manager"]})
    gb.configure_column("Category", width=240, editable=True,
                       cellEditor="agSelectCellEditor",
                       cellEditorParams={"values": categories})
    gb.configure_column("Type of Unit Rate", width=220, editable=True,
                       cellEditor="agSelectCellEditor",
                       cellEditorParams={"values": RATE_TYPES if RATE_TYPES else UNIT_TYPES})
    gb.configure_column("Weightage (FTE)", type=["numericColumn"], width=170, editable=True)
    gb.configure_column("Duration (months)", type=["numericColumn"], width=170, editable=True)

    disc_bg = {k: f"#{v}" for k, v in DISCIPLINE_COLORS.items()}
    row_style_js = JsCode(f"""
        function(params) {{
            const map = {json.dumps(disc_bg)};
            const disc = params?.data?.Discipline || "";
            return map[disc] ? {{ backgroundColor: map[disc] }} : null;
        }}
    """)
    gb.configure_grid_options(getRowStyle=row_style_js)

    try:
        resp = AgGrid(df, gridOptions=gb.build(), height=500, update_on="value_changed",
                     allow_unsafe_jscode=True, theme="streamlit")
        st.session_state[GRID_KEY] = pd.DataFrame(resp["data"])
    except:
        st.warning("Grid update failed. Please refresh.")

    # Preview
    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, type_of_schedule, type_of_package)
    total = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0
    
    if not labour_df.empty:
        with st.expander("Debug: View rates found"):
            st.dataframe(labour_df[["Discipline", "Personnel", "Category", "Type of Unit Rate", f"Unit Rate ({currency})"]])
    
    st.markdown(
        f"""
        <div style="background: var(--surface-alt); padding: 1rem; border-radius: 10px;">
            <h3 style="margin: 0; color: var(--brand1);">Total Labour Cost: {currency} {total:,.2f}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_third_party():
    st.header("💰 Third Party & Non-Labour Costs")
    currency = currency_for(st.session_state["type_of_schedule"])
    
    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, 
                                       st.session_state["type_of_schedule"],
                                       st.session_state["type_of_package"])
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0
    
    st.info(f"Current Total Labour Cost: {currency} {total_labour:,.2f}")
    
    df = st.session_state[THIRD_PARTY_KEY].copy()
    if df.empty:
        initialize_default_grids()
        df = st.session_state[THIRD_PARTY_KEY].copy()
    
    # Display editable rows
    for idx, row in df.iterrows():
        cols = st.columns([2, 3, 1.5, 1.5, 2])
        with cols[0]:
            df.loc[idx, "Category"] = st.selectbox(f"cat_{idx}", THIRD_PARTY_CATEGORIES,
                index=THIRD_PARTY_CATEGORIES.index(row["Category"]) if row["Category"] in THIRD_PARTY_CATEGORIES else 0,
                label_visibility="collapsed", key=f"cat_{idx}")
        with cols[1]:
            df.loc[idx, "Description"] = st.text_input(f"desc_{idx}", value=row["Description"],
                label_visibility="collapsed", key=f"desc_{idx}")
        with cols[2]:
            basis = ["% of Labour Cost", "Fixed Amount"]
            df.loc[idx, "Basis"] = st.selectbox(f"basis_{idx}", basis,
                index=basis.index(row["Basis"]) if row["Basis"] in basis else 0,
                label_visibility="collapsed", key=f"basis_{idx}")
        with cols[3]:
            if df.loc[idx, "Basis"] == "% of Labour Cost":
                df.loc[idx, "Percentage"] = st.number_input(f"pct_{idx}", min_value=0.0, max_value=100.0,
                    value=float(row["Percentage"]), step=0.1, format="%.1f", label_visibility="collapsed", key=f"pct_{idx}")
                df.loc[idx, "Fixed Amount"] = 0.0
            else:
                df.loc[idx, "Fixed Amount"] = st.number_input(f"amt_{idx}", min_value=0.0,
                    value=float(row["Fixed Amount"]), step=100.0, format="%.2f", label_visibility="collapsed", key=f"amt_{idx}")
                df.loc[idx, "Percentage"] = 0.0
        with cols[4]:
            df.loc[idx, "Remarks"] = st.text_input(f"rem_{idx}", value=row["Remarks"],
                label_visibility="collapsed", key=f"rem_{idx}")
    
    st.session_state[THIRD_PARTY_KEY] = df
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ Add Item", use_container_width=True):
            new = pd.DataFrame([{"Category": THIRD_PARTY_CATEGORIES[0], "Description": "", "Basis": "% of Labour Cost",
                               "Percentage": 0.0, "Fixed Amount": 0.0, "Remarks": ""}])
            st.session_state[THIRD_PARTY_KEY] = pd.concat([df, new], ignore_index=True)
            do_rerun()
    with col2:
        if st.button("🗑️ Remove Last", use_container_width=True) and len(df) > 0:
            st.session_state[THIRD_PARTY_KEY] = df.iloc[:-1].reset_index(drop=True)
            do_rerun()
    with col3:
        if st.button("📅 Next", use_container_width=True):
            st.session_state["page"] = "LOADING"
            do_rerun()
    
    if len(df) > 0:
        costs = calculate_third_party_costs(df, total_labour, currency)
        display = costs.copy()
        display[f"Cost ({currency})"] = display[f"Cost ({currency})"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(display, use_container_width=True)
        
        total = costs[f"Cost ({currency})"].sum()
        st.markdown(f"<h3 style='color: var(--brand1);'>Total: {currency} {total:,.2f}</h3>", unsafe_allow_html=True)


def render_loading():
    st.header("📅 Monthly Loading")
    currency = currency_for(st.session_state["type_of_schedule"])
    
    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, 
                                       st.session_state["type_of_schedule"],
                                       st.session_state["type_of_package"])
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0
    
    third_party_df = calculate_third_party_costs(st.session_state[THIRD_PARTY_KEY], total_labour, currency)
    
    df = st.session_state[MONTHLY_LOADING_KEY].copy()
    if df.empty:
        initialize_default_grids()
        df = st.session_state[MONTHLY_LOADING_KEY].copy()
    
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
            do_rerun()
    with col3:
        st.info("Loading factors multiply monthly costs")
    
    for idx, row in df.iterrows():
        cols = st.columns(5)
        with cols[0]:
            st.write(f"**{row['Month']}**")
        with cols[1]:
            df.loc[idx, "Loading Factor (%)"] = st.number_input(f"load_{idx}", min_value=0.0, max_value=200.0,
                value=float(row["Loading Factor (%)"]), step=5.0, format="%.1f", label_visibility="collapsed", key=f"load_{idx}")
        with cols[2]:
            df.loc[idx, "Weightage Distribution"] = st.number_input(f"w_{idx}", min_value=0.0, max_value=100.0,
                value=float(row["Weightage Distribution"]), step=0.1, format="%.1f", label_visibility="collapsed", key=f"w_{idx}")
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
            st.session_state["page"] = "THIRD_PARTY"
            do_rerun()
    with col2:
        if st.button("📊 Totals", use_container_width=True, type="primary"):
            st.session_state["page"] = "TOTALS"
            do_rerun()
    with col3:
        if st.button("↺ Reset", use_container_width=True):
            months = [f"Month {i+1:02d}" for i in range(12)]
            default = pd.DataFrame({"Month": months, "Loading Factor (%)": [100.0]*12, "Weightage Distribution": [100.0/12]*12})
            st.session_state[MONTHLY_LOADING_KEY] = default
            do_rerun()


def render_totals():
    schedule = st.session_state["type_of_schedule"]
    package = st.session_state["type_of_package"]
    currency = currency_for(schedule)

    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, schedule, package)
    kpbi_labour_df = calculate_kpbi_labour_costs(st.session_state[GRID_KEY], currency, schedule, package)
    total_labour = float(labour_df[f"Labour Cost ({currency})"].sum()) if not labour_df.empty else 0.0
    
    third_df = calculate_third_party_costs(st.session_state[THIRD_PARTY_KEY], total_labour, currency)
    totals = compute_totals(labour_df, kpbi_labour_df, third_df, st.session_state[MONTHLY_LOADING_KEY], currency)

    st.markdown(
        f"""
        <div class="summary-card">
            <h2 style="color: var(--brand1);">Project Summary</h2>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                <div><h3 style="color: var(--text-muted);">Total Manhours</h3>
                <div style="font-size: 2.2rem;">{totals['total_hours']:,.0f}</div></div>
                <div><h3 style="color: var(--text-muted);">Package</h3>
                <div style="font-size: 2.2rem;">{package}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>🔵 METHOD A — EXACT RATES</h3>
                <div class="value">{totals['total_exact']:,.2f} {currency}</div>
                <div class="subvalue">Labour: {totals['total_labour_exact']:,.2f}<br/>Third Party: {totals['total_third_party']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>🟢 METHOD B — KPBI RATES (from CSV)</h3>
                <div class="value">{totals['total_kpbi']:,.2f} {currency}</div>
                <div class="subvalue">Labour (KPBI): {totals['total_labour_kpbi']:,.2f}<br/>Third Party: {totals['total_third_party']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True
        )

    if not totals["discipline_totals"].empty:
        st.subheader("Labour Cost by Discipline (Method A)")
        st.dataframe(totals["discipline_totals"], use_container_width=True, hide_index=True)
        
        fig = px.bar(totals["discipline_totals"].sort_values(f"Labour Cost ({currency})"), 
                    y="Discipline", x=f"Labour Cost ({currency})", orientation='h', color="Discipline",
                    color_discrete_map={d: f"#{DISCIPLINE_COLORS.get(d, 'D1D5DB')}" for d in totals["discipline_totals"]["Discipline"]})
        fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    if not third_df.empty:
        st.subheader("Third Party Costs")
        display = third_df.copy()
        display[f"Cost ({currency})"] = display[f"Cost ({currency})"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(display, use_container_width=True, hide_index=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state["page"] = "LOADING"
            do_rerun()
    with col2:
        if st.button("💾 Save", use_container_width=True):
            p = save_current_project()
            st.success(f"Saved '{p['name']}'!")
            do_rerun()
    with col3:
        if st.button("📈 Summary", use_container_width=True, type="primary"):
            st.session_state["page"] = "SUMMARY"
            do_rerun()
    with col4:
        if st.button("🔄 Compare", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            do_rerun()


def render_summary():
    schedule = st.session_state["type_of_schedule"]
    package = st.session_state["type_of_package"]
    currency = currency_for(schedule)

    meta = pd.DataFrame([{
        "Project Title": st.session_state["project_title"],
        "Date": str(st.session_state["project_date"]),
        "Cost Engineer": st.session_state["cost_engineer"],
        "TP/Specialist": st.session_state["tp_specialist"],
        "Schedule": schedule,
        "Package": package,
        "Currency": currency,
        "Hours/Month": HOURS_PER_MONTH,
    }])

    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, schedule, package)
    kpbi_labour_df = calculate_kpbi_labour_costs(st.session_state[GRID_KEY], currency, schedule, package)
    total_labour = float(labour_df[f"Labour Cost ({currency})"].sum()) if not labour_df.empty else 0.0
    
    third_df = calculate_third_party_costs(st.session_state[THIRD_PARTY_KEY], total_labour, currency)
    totals = compute_totals(labour_df, kpbi_labour_df, third_df, st.session_state[MONTHLY_LOADING_KEY], currency)

    st.subheader("Project Information")
    st.dataframe(meta, use_container_width=True)

    st.subheader("Method Comparison")
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(data=[
            go.Bar(name='Method A (Exact)', x=['Total'], y=[totals['total_exact']], marker_color=BRAND1),
            go.Bar(name='Method B (KPBI)', x=['Total'], y=[totals['total_kpbi']], marker_color=BRAND2)
        ])
        fig.update_layout(title="Method Comparison", yaxis_title=f"Cost ({currency})", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.pie(values=[totals['total_labour_exact'], totals['total_third_party']],
                    names=['Labour', 'Third Party'], title="Cost Components (Method A)",
                    color_discrete_sequence=[BRAND1, BRAND2], hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    if not labour_df.empty:
        disc = labour_df.groupby("Discipline").agg({
            "Total Hours": "sum", f"Labour Cost ({currency})": "sum"
        }).reset_index().sort_values(f"Labour Cost ({currency})")
        
        fig = px.bar(disc, y="Discipline", x=f"Labour Cost ({currency})", orientation='h', color="Discipline",
                    title=f"Labour Cost by Discipline ({currency})")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if st.button("📥 Download Excel Report", type="primary", use_container_width=True):
        with st.spinner("Generating..."):
            excel = to_excel_bytes(meta, totals, labour_df, kpbi_labour_df, third_df, 
                                  st.session_state[MONTHLY_LOADING_KEY], schedule, currency)
            st.download_button("⬇️ Download", data=excel, file_name=f"MEC_{st.session_state['project_title'] or 'Output'}.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state["page"] = "TOTALS"
            do_rerun()
    with col2:
        if st.button("💾 Save", use_container_width=True):
            p = save_current_project()
            st.success(f"Saved '{p['name']}'!")
            do_rerun()
    with col3:
        if st.button("🔄 Compare", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            do_rerun()


def render_compare():
    st.header("Project Comparison")
    
    saved = st.session_state.get(SAVED_PROJECTS_KEY, [])
    if not saved:
        st.info("No saved projects. Save from Totals or Summary page.")
        if st.button("⬅️ Back"):
            st.session_state["page"] = "SUMMARY"
            do_rerun()
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
        with col3:
            badge = "up" if comp["kpbi_cost_pct"] > 5 else "down" if comp["kpbi_cost_pct"] < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Method B Change</h3>
                    <div class="value">{comp['kpbi_cost_diff']:+,.2f} {p2['currency']}</div>
                    <div><span class="comparison-badge {badge}">{comp['kpbi_cost_pct']:+.1f}%</span></div>
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
                do_rerun()

    if st.button("Clear All", type="secondary"):
        st.session_state[SAVED_PROJECTS_KEY] = []
        do_rerun()

    if st.button("⬅️ Back to Summary"):
        st.session_state["page"] = "SUMMARY"
        do_rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Main App
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="color: var(--brand1); margin-bottom: 0.5rem;">MEC TOOL</h1>
        <p style="color: var(--text-muted); font-size: 1.1rem;">
          Major Engineering Contract Tool for CE Upstream
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

render_navigation()

page = st.session_state["page"]
if page == "MAIN":
    render_main()
elif page == "TABLE":
    render_table()
elif page == "THIRD_PARTY":
    render_third_party()
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
    do_rerun()
