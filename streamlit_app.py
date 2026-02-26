# streamlit_app.py
# MEC TOOL – Streamlit app (Uploadable CSV version with updated rate types)
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
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="MEC TOOL", layout="wide")

# ──────────────────────────────────────────────────────────────────────────────
# Theme presets (Emerald / Purple) + minimalist Look & Feel
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
    # Light/dark surface & text harmonization
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
      /* App background + text */
      .stApp {{ background: var(--surface); color: var(--text); }}
      /* Headings */
      .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: var(--text); }}
      /* Small captions & labels */
      .stCaption, p, label, .st-emotion-cache-16idsys span {{ color: var(--text-muted); }}
      /* Metric titles & values */
      div[data-testid="metric-container"] label p {{ color: var(--text-muted) !important; }}
      div[data-testid="metric-container"] div {{ color: var(--text) !important; }}
      /* Buttons – accent hover */
      .stButton button {{
        border: 1px solid var(--brand1);
        color: #fff; background: var(--brand1);
      }}
      .stButton button:hover {{
        filter: brightness(0.95); box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand1) 30%, transparent);
      }}
      /* Panels/tables */
      .stDataFrame, .st-emotion-cache-oco5fk, .st-emotion-cache-1k2qj1w {{
        background: var(--surface-alt);
      }}
      /* Custom cards */
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
      /* Monthly loading table styling */
      .monthly-loading-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
      }}
      .monthly-loading-table th {{
        background-color: var(--brand1);
        color: white;
        padding: 8px;
        text-align: center;
      }}
      .monthly-loading-table td {{
        padding: 8px;
        text-align: center;
        border: 1px solid var(--text-muted);
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
# Domain constants & defaults
# ──────────────────────────────────────────────────────────────────────────────
HOURS_PER_MONTH = 176.0
USD_SCHEDULES = {"schedule b", "b", "schedule d", "d"}
B_D_CATEGORY_FALLBACK = [
    "America (North/South/Canada/Australia)",
    "Middle East/Africa",
    "Europe",
    "Asia",
    "Japan",
    "Others",
]
AC_CATEGORIES = ["Malaysian", "Regional", "Expatriate"]

# UPDATED: Rate types as requested
UNIT_TYPES = ["Minimum", "Maximum", "Normalise", "Rate A", "Rate B", "Rate C", "Rate D", "Rate E", "Rate F"]

# Mapping from old to new (for reference)
RATE_MAPPING = {
    "MMC": "Rate A",
    "DAR": "Rate B",
    "AKER": "Rate C",
    "TUAH": "Rate D",
    "PRW": "Rate E",
    "PUSB": "Rate F"
}

RATE_SOURCES = ["Data", "U1", "U2"]

# Third Party & Non-Labour cost categories
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

DEFAULT_PERSONNEL: Dict[str, List[str]] = {
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

GRID_KEY = "grid_df"
THIRD_PARTY_KEY = "third_party_df"
MONTHLY_LOADING_KEY = "monthly_loading_df"
SAVED_PROJECTS_KEY = "saved_projects"

# ──────────────────────────────────────────────────────────────────────────────
# Navigation Pages
# ──────────────────────────────────────────────────────────────────────────────
PAGES = {
    "MAIN": "🏠 Main Page",
    "TABLE": "👥 Personnel Table", 
    "THIRD_PARTY": "💰 Third Party & Non-Labour",
    "LOADING": "📅 Monthly Loading",
    "TOTALS": "📊 Totals & Line Items",
    "SUMMARY": "📈 Summary & Download",
    "COMPARE": "🔄 Compare Projects"
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers (robust parsing + matching)
# ──────────────────────────────────────────────────────────────────────────────
NBSP = u"\xa0"
_num = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")  # robust number finder


def _to_float_safe(val: object) -> float:
    s = str(val or "").replace(",", "")  # remove thousand separators
    s = s.replace(NBSP, " ").strip()
    s = re.sub(r"(usd|myr|rm|\$)", " ", s, flags=re.I)
    m = _num.search(s)
    return float(m.group(0)) if m else 0.0


def _canon(s: str) -> str:
    s = str(s or "").replace(NBSP, " ").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("type of unit", "type of unit rate")
    s = s.replace("unit rate ( myr )", "unit rate (myr)")
    return s


def _canon_disc(s: str) -> str:
    s = str(s or "").replace(NBSP, " ").lower().replace("&", "and")
    s = s.replace("instrumentation", "instrument")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def _canon_sched_tag(s: str) -> str:
    t = _canon(s)
    m = re.search(r"(?:schedule\s*)?([abcd])$", t)
    return m.group(1) if m else t


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    colmap = {}
    for c in df.columns:
        cl = _canon(c)
        if "discipline" in cl:
            colmap[c] = "discipline"
        elif "personnel" in cl:
            colmap[c] = "personnel"
        elif "position" in cl:
            colmap[c] = "position"
        elif "category" in cl or "nationality" in cl or "region" in cl:
            colmap[c] = "category"
        elif "schedule" in cl:
            colmap[c] = "schedule"
        elif "type of unit rate" in cl or cl in ("type", "rate type", "unit type"):
            colmap[c] = "type of unit rate"
        elif ("unit rate" in cl and ("myr" in cl or "usd" in cl or cl == "unit rate")) or ("normalise rate" in cl):
            colmap[c] = c
        else:
            colmap[c] = c
    return df.rename(columns=colmap)


def get_col(df: pd.DataFrame, name: str) -> pd.Series:
    s = df[name]
    if isinstance(s, pd.DataFrame):
        s = s.bfill(axis=1).iloc[:, 0]
    return s


def canon_series(s):
    # accepts Series or DataFrame
    if isinstance(s, pd.DataFrame):
        s = s.bfill(axis=1).iloc[:, 0]
    return s.astype(str).str.replace(NBSP, " ").str.strip().str.lower()


def is_usd(schedule: str) -> bool:
    return _canon(schedule) in USD_SCHEDULES or _canon_sched_tag(schedule) in {"b", "d"}


def currency_for(schedule: str) -> str:
    return "USD" if is_usd(schedule) else "MYR"


def build_category_options(schedule: str, rate_source: str, data_tbl, u1_tbl, u2_tbl) -> List[str]:
    sheet = {"Data": data_tbl, "U1": u1_tbl, "U2": u2_tbl}.get(rate_source, pd.DataFrame())
    if sheet is not None and not sheet.empty:
        df = sheet.copy()
        if "schedule" in df.columns and schedule:
            tag = _canon_sched_tag(schedule)
            df = df[canon_series(get_col(df, "schedule")).apply(_canon_sched_tag) == tag]
        if "category" in df.columns:
            cats = (
                get_col(df, "category")
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            cats = [c for c in cats if c]
            if cats:
                return sorted(cats)
    return B_D_CATEGORY_FALLBACK if is_usd(schedule) else AC_CATEGORIES


def _rate_col_for_unit_type(df: pd.DataFrame, unit_type: str, prefer_usd: bool) -> Optional[str]:
    key = _canon(unit_type)
    pairs = [(_canon(c), c) for c in df.columns]
    
    # Map new rate types to their old equivalents for backward compatibility with CSV data
    if key.startswith("rate a") or key in [_canon("Rate A"), "rate a"]:
        token = "mmc"  # Map to old MMC
    elif key.startswith("rate b") or key in [_canon("Rate B"), "rate b"]:
        token = "dar"  # Map to old DAR
    elif key.startswith("rate c") or key in [_canon("Rate C"), "rate c"]:
        token = "aker"  # Map to old AKER
    elif key.startswith("rate d") or key in [_canon("Rate D"), "rate d"]:
        token = "tuah"  # Map to old TUAH
    elif key.startswith("rate e") or key in [_canon("Rate E"), "rate e"]:
        token = "prw"  # Map to old PRW
    elif key.startswith("rate f") or key in [_canon("Rate F"), "rate f"]:
        token = "pusb"  # Map to old PUSB
    elif key.startswith("min"):
        token = "minimum"
    elif key.startswith("max"):
        token = "maximum"
    elif key.startswith("norm"):
        token = "normalise"
    else:
        token = key

    ranked = []
    for k, c in pairs:
        has_token = token in k
        has_rate = ("rate" in k or "unit rate" in k)
        has_usd = "usd" in k
        has_myr = "myr" in k
        score = 0
        if has_token:
            score += 3
        if has_rate:
            score += 1
        if prefer_usd and has_usd:
            score += 2
        if (not prefer_usd) and has_myr:
            score += 2
        if token in ("minimum", "maximum", "normalise", "mmc", "dar", "aker", "tuah", "prw", "pusb") and ("unit rate" in k or "rate" in k):
            score += 1
        if score > 0:
            ranked.append((score, c))

    if ranked:
        ranked.sort(reverse=True)
        return ranked[0][1]

    for k, c in pairs:
        if "unit rate" in k or "rate" in k:
            return c
    return None


def _base_working_rate_col(working: pd.DataFrame) -> Optional[str]:
    for c in working.columns:
        k = _canon(c)
        if "unit rate" in k and ("myr" in k or "usd" in k or k == "unit rate" or "normalise rate" in k):
            return c
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Load CSV files from upload
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=600)  # cache for 10 minutes
def load_csv_files_from_upload(data_file, u1_file, u2_file):
    """Load three CSV files from uploaded file objects"""
    
    def read_csv_safe(file_obj):
        try:
            if file_obj is not None:
                # Read the uploaded file
                df = pd.read_csv(file_obj)
                
                # Try to detect if there's a header row that needs cleaning
                if len(df) > 0:
                    # Check if first row might be a header
                    first_row = df.iloc[0].astype(str).str.lower()
                    if any(key in ' '.join(first_row) for key in ['discipline', 'personnel', 'category', 'schedule']):
                        # Use first row as header and skip it in data
                        new_header = df.iloc[0]
                        df = df[1:]
                        df.columns = new_header
                
                # Clean up column names
                df = _normalize_cols(df)
                # Remove any rows that are all NaN
                df = df.dropna(how='all')
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.warning(f"Error reading CSV file: {e}")
            return pd.DataFrame()
    
    # Reset file pointers to beginning
    if data_file:
        data_file.seek(0)
    if u1_file:
        u1_file.seek(0)
    if u2_file:
        u2_file.seek(0)
    
    data_tbl = read_csv_safe(data_file)
    u1_tbl = read_csv_safe(u1_file)
    u2_tbl = read_csv_safe(u2_file)
    
    # Create a working dataframe from Data table (or first available)
    working = data_tbl.copy() if not data_tbl.empty else (u1_tbl.copy() if not u1_tbl.empty else u2_tbl.copy())
    
    base_rate_col = _base_working_rate_col(working)

    schedule_opts = []
    if not data_tbl.empty and "schedule" in data_tbl.columns:
        s = get_col(data_tbl, "schedule").dropna().astype(str).str.strip()
        schedule_opts = sorted([v for v in s.unique().tolist() if v])

    package_opts = []
    if not u1_tbl.empty:
        package_opts.append("U1")
    if not u2_tbl.empty:
        package_opts.append("U2")
    if not package_opts:
        package_opts = ["U1", "U2"]

    disciplines = list(DISCIPLINE_ROW_COUNTS.keys())

    personnel_union = []
    for _, plist in DEFAULT_PERSONNEL.items():
        personnel_union.extend(plist)
    if not working.empty and "personnel" in working.columns:
        personnel_union.extend(get_col(working, "personnel").dropna().astype(str).tolist())
    personnel_union = sorted(pd.Series(personnel_union).dropna().astype(str).drop_duplicates().tolist())

    return (
        working,
        data_tbl,
        u1_tbl,
        u2_tbl,
        base_rate_col,
        schedule_opts,
        package_opts,
        disciplines,
        personnel_union,
    )


# ──────────────────────────────────────────────────────────────────────────────
# File Upload Section in Sidebar
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("📁 Upload CSV Files")
    st.caption("Upload the required CSV files")
    
    # File uploaders for the three CSV files
    data_file = st.file_uploader(
        "DATA.csv",
        type=["csv"],
        key="data_uploader",
        help="Upload the DATA.csv file containing rate information"
    )
    
    u1_file = st.file_uploader(
        "U1.csv",
        type=["csv"],
        key="u1_uploader",
        help="Upload the U1.csv file (Package U1 rates)"
    )
    
    u2_file = st.file_uploader(
        "U2.csv",
        type=["csv"],
        key="u2_uploader",
        help="Upload the U2.csv file (Package U2 rates)"
    )
    
    # Check if all required files are uploaded
    all_files_uploaded = data_file is not None and u1_file is not None and u2_file is not None
    
    if all_files_uploaded:
        st.success("✅ All CSV files uploaded!")
        
        # Add a button to load/reload the data
        if st.button("Load CSV Data", type="primary", use_container_width=True):
            st.session_state.pop("csv_data_loaded", None)
            st.cache_data.clear()
            do_rerun()
    else:
        missing = []
        if data_file is None:
            missing.append("DATA.csv")
        if u1_file is None:
            missing.append("U1.csv")
        if u2_file is None:
            missing.append("U2.csv")
        
        st.warning(f"Missing: {', '.join(missing)}")
        st.info("Please upload all three CSV files to continue.")
        st.stop()

# Load CSV data from uploaded files
if all_files_uploaded and "csv_data_loaded" not in st.session_state:
    with st.spinner("Loading CSV data..."):
        (
            working,
            data_tbl,
            u1_tbl,
            u2_tbl,
            base_rate_col,
            schedule_opts,
            package_opts,
            DISC_LIST,
            PERSONNEL_LIST,
        ) = load_csv_files_from_upload(data_file, u1_file, u2_file)
        
        # Store in session state
        st.session_state["working"] = working
        st.session_state["data_tbl"] = data_tbl
        st.session_state["u1_tbl"] = u1_tbl
        st.session_state["u2_tbl"] = u2_tbl
        st.session_state["base_rate_col"] = base_rate_col
        st.session_state["schedule_opts"] = schedule_opts
        st.session_state["package_opts"] = package_opts
        st.session_state["DISC_LIST"] = DISC_LIST
        st.session_state["PERSONNEL_LIST"] = PERSONNEL_LIST
        st.session_state["csv_data_loaded"] = True
        
        st.success("CSV data loaded successfully!")
        do_rerun()

# Retrieve from session state
working = st.session_state.get("working", pd.DataFrame())
data_tbl = st.session_state.get("data_tbl", pd.DataFrame())
u1_tbl = st.session_state.get("u1_tbl", pd.DataFrame())
u2_tbl = st.session_state.get("u2_tbl", pd.DataFrame())
base_rate_col = st.session_state.get("base_rate_col")
schedule_opts = st.session_state.get("schedule_opts", [])
package_opts = st.session_state.get("package_opts", ["U1", "U2"])
DISC_LIST = st.session_state.get("DISC_LIST", list(DISCIPLINE_ROW_COUNTS.keys()))
PERSONNEL_LIST = st.session_state.get("PERSONNEL_LIST", [])

# ──────────────────────────────────────────────────────────────────────────────
# Session defaults
# ──────────────────────────────────────────────────────────────────────────────
st.session_state.setdefault("page", "MAIN")
st.session_state.setdefault("project_title", "")
st.session_state.setdefault("cost_engineer", "")
st.session_state.setdefault("tp_specialist", "")
st.session_state.setdefault("project_date", None)
st.session_state.setdefault("type_of_package", package_opts[0] if package_opts else "U1")
st.session_state.setdefault("type_of_schedule", schedule_opts[0] if schedule_opts else "Schedule A")
st.session_state.setdefault("rate_source", RATE_SOURCES[0])
st.session_state.setdefault("kpbi_rate", 0.0)  # KPBI rate for Method B
st.session_state.setdefault("apply_kpbi_to_all", True)  # Apply KPBI rate to all labour costs

# Initialize Personnel Table
if GRID_KEY not in st.session_state:
    rows = []
    tmp_schedule = st.session_state["type_of_schedule"]
    tmp_categories = build_category_options(tmp_schedule, st.session_state["rate_source"], data_tbl, u1_tbl, u2_tbl)
    if not tmp_categories:
        tmp_categories = B_D_CATEGORY_FALLBACK if is_usd(tmp_schedule) else AC_CATEGORIES
    for disc, count in DISCIPLINE_ROW_COUNTS.items():
        defaults = DEFAULT_PERSONNEL.get(disc, [])
        for i in range(count):
            personnel = defaults[i] if i < len(defaults) else (PERSONNEL_LIST[0] if PERSONNEL_LIST else "")
            rows.append(
                {
                    "Swatch": DISCIPLINE_SWATCH.get(disc, "⬜"),
                    "Discipline": disc,
                    "Personnel": personnel,
                    "Category": tmp_categories[0] if tmp_categories else "",
                    "Type of Unit Rate": "Normalise",
                    "Weightage (FTE)": 0.0,
                    "Duration (months)": 1.0,
                }
            )
    st.session_state[GRID_KEY] = pd.DataFrame(rows)

# Initialize Third Party & Non-Labour items
if THIRD_PARTY_KEY not in st.session_state:
    third_party_rows = []
    for category in THIRD_PARTY_CATEGORIES:
        third_party_rows.append(
            {
                "Category": category,
                "Description": "",
                "Basis": "% of Labour Cost",
                "Percentage": 0.0,
                "Fixed Amount": 0.0,
                "Remarks": ""
            }
        )
    st.session_state[THIRD_PARTY_KEY] = pd.DataFrame(third_party_rows)

# Initialize Monthly Loading
if MONTHLY_LOADING_KEY not in st.session_state:
    # Create default 12-month loading (100% each month)
    months = [f"Month {i+1:02d}" for i in range(12)]
    monthly_data = {
        "Month": months,
        "Loading Factor (%)": [100.0] * 12,
        "Weightage Distribution": [100.0/12] * 12  # Equal distribution
    }
    st.session_state[MONTHLY_LOADING_KEY] = pd.DataFrame(monthly_data)

# Initialize saved projects
if SAVED_PROJECTS_KEY not in st.session_state:
    st.session_state[SAVED_PROJECTS_KEY] = []

# ──────────────────────────────────────────────────────────────────────────────
# Rate lookup (relaxed matching)
# ──────────────────────────────────────────────────────────────────────────────
def _canonical_col(df: pd.DataFrame, name: str) -> pd.Series:
    s = get_col(df, name)
    return s.astype(str).str.replace(NBSP, " ").str.strip().str.lower()


def _relaxed_match(df: pd.DataFrame, discipline: str, personnel: str, category: str, schedule: Optional[str]) -> pd.DataFrame:
    m = df.copy()
    if "discipline" in m.columns:
        disc_s = _canonical_col(m, "discipline").apply(_canon_disc)
        m = m[disc_s == _canon_disc(discipline)]

    if "personnel" in m.columns:
        pers_s = _canonical_col(m, "personnel")
        pick = pers_s == str(personnel).strip().lower()
        if pick.any():
            m = m[pick]

    if "category" in m.columns:
        cat_s = _canonical_col(m, "category")
        pick = cat_s == str(category).strip().lower()
        if pick.any():
            m = m[pick]

    if schedule and "schedule" in m.columns:
        sch_s = _canonical_col(m, "schedule").apply(_canon_sched_tag)
        tag = _canon_sched_tag(schedule)
        pick = sch_s == tag
        if pick.any():
            m = m[pick]

    return m


def get_rate(
    rate_source: str,
    working: pd.DataFrame,
    base_rate_col: Optional[str],
    data_tbl: pd.DataFrame,
    u1_tbl: pd.DataFrame,
    u2_tbl: pd.DataFrame,
    discipline: str,
    personnel: str,
    category: str,
    unit_type: str,
    schedule: str,
) -> float:
    prefer_usd = is_usd(schedule)
    sheet_map = {"data": data_tbl, "u1": u1_tbl, "u2": u2_tbl}
    sheet = sheet_map.get(rate_source.strip().lower())

    if sheet is not None and not sheet.empty:
        col = _rate_col_for_unit_type(sheet, unit_type, prefer_usd)
        if col:
            m = _relaxed_match(sheet, discipline, personnel, category, schedule)
            if not m.empty:
                return _to_float_safe(get_col(m, col).iloc[0])

    if not working.empty:
        for c in working.columns:
            k = _canon(c)
            if "unit rate" in k and (rate_source.strip().lower() in k):
                m = _relaxed_match(working, discipline, personnel, category, schedule)
                if not m.empty:
                    return _to_float_safe(get_col(m, c).iloc[0])

    if base_rate_col and base_rate_col in working.columns:
        m = _relaxed_match(working, discipline, personnel, category, schedule)
        if not m.empty:
            return _to_float_safe(get_col(m, base_rate_col).iloc[0])

    return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Calculations
# ──────────────────────────────────────────────────────────────────────────────
def calculate_labour_costs(grid_df: pd.DataFrame, currency: str, rate_source: str, type_of_schedule: str) -> pd.DataFrame:
    """Calculate labour costs from personnel table"""
    if grid_df.empty:
        return pd.DataFrame(
            columns=[
                "Discipline",
                "Personnel",
                "Category",
                "Type of Unit Rate",
                "Rate Source",
                f"Unit Rate ({currency})",
                "Weightage (FTE)",
                "Duration (months)",
                "Total Hours",
                f"Labour Cost ({currency})",
            ]
        )

    cache: dict = {}

    def rate_for(row):
        key = (
            row["Discipline"],
            row["Personnel"],
            row["Category"],
            row["Type of Unit Rate"],
            type_of_schedule,
            rate_source,
        )
        if key in cache:
            return cache[key]
        val = get_rate(
            rate_source,
            working,
            base_rate_col,
            data_tbl,
            u1_tbl,
            u2_tbl,
            key[0],
            key[1],
            key[2],
            key[3],
            key[4],
        )
        cache[key] = val
        return val

    df = grid_df.copy()
    # downcast types to reduce payload
    for col in ["Weightage (FTE)", "Duration (months)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    df["Rate Source"] = rate_source
    df[f"Unit Rate ({currency})"] = df.apply(rate_for, axis=1).astype("float32")
    df["Total Hours"] = (
        df["Weightage (FTE)"].astype("float32") * float(HOURS_PER_MONTH) * df["Duration (months)"].astype("float32")
    )
    df[f"Labour Cost ({currency})"] = (df[f"Unit Rate ({currency})"] * df["Total Hours"]).astype("float32")

    return df[
        [
            "Discipline",
            "Personnel",
            "Category",
            "Type of Unit Rate",
            "Rate Source",
            f"Unit Rate ({currency})",
            "Weightage (FTE)",
            "Duration (months)",
            "Total Hours",
            f"Labour Cost ({currency})",
        ]
    ]


def calculate_third_party_costs(third_party_df: pd.DataFrame, total_labour_cost: float, currency: str) -> pd.DataFrame:
    """Calculate third party and non-labour costs based on percentage or fixed amount"""
    if third_party_df.empty:
        return pd.DataFrame(columns=["Category", "Description", "Basis", f"Cost ({currency})", "Remarks"])
    
    df = third_party_df.copy()
    df[f"Cost ({currency})"] = 0.0
    
    for idx, row in df.iterrows():
        if row["Basis"] == "% of Labour Cost":
            df.loc[idx, f"Cost ({currency})"] = total_labour_cost * (float(row["Percentage"]) / 100.0)
        else:  # Fixed Amount
            df.loc[idx, f"Cost ({currency})"] = float(row["Fixed Amount"])
    
    return df[["Category", "Description", "Basis", f"Cost ({currency})", "Remarks"]]


def apply_monthly_loading(labour_df: pd.DataFrame, third_party_df: pd.DataFrame, 
                         monthly_loading_df: pd.DataFrame, currency: str) -> Dict:
    """Apply monthly loading factors to costs"""
    if monthly_loading_df.empty:
        return {
            "monthly_labour": {},
            "monthly_third_party": {},
            "total_by_month": {}
        }
    
    months = monthly_loading_df["Month"].tolist()
    loading_factors = monthly_loading_df["Loading Factor (%)"].tolist()
    weightage_dist = monthly_loading_df["Weightage Distribution"].tolist()
    
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0
    total_third_party = third_party_df[f"Cost ({currency})"].sum() if not third_party_df.empty else 0
    
    monthly_labour = {}
    monthly_third_party = {}
    total_by_month = {}
    
    for i, month in enumerate(months):
        factor = loading_factors[i] / 100.0
        weight = weightage_dist[i] / 100.0
        
        # Apply loading to costs
        monthly_labour[month] = total_labour * weight * factor
        monthly_third_party[month] = total_third_party * weight * factor
        total_by_month[month] = monthly_labour[month] + monthly_third_party[month]
    
    return {
        "monthly_labour": monthly_labour,
        "monthly_third_party": monthly_third_party,
        "total_by_month": total_by_month,
        "months": months
    }


def compute_totals(labour_df: pd.DataFrame, third_party_df: pd.DataFrame, 
                  monthly_loading_df: pd.DataFrame, currency: str, kpbi_rate: float):
    """Compute totals with Method A (Exact) and Method B (KPBI rate)"""
    # Labour costs
    total_labour_exact = float(labour_df[f"Labour Cost ({currency})"].sum()) if not labour_df.empty else 0.0
    total_hours = float(labour_df["Total Hours"].sum()) if not labour_df.empty else 0.0
    
    # KPBI Method (Method B) - apply KPBI rate to all labour hours
    total_labour_kpbi = total_hours * kpbi_rate if kpbi_rate > 0 else 0.0
    
    # Third party costs (these are the same for both methods)
    total_third_party = float(third_party_df[f"Cost ({currency})"].sum()) if not third_party_df.empty else 0.0
    
    # Method A: Exact labour costs + third party costs
    total_exact = total_labour_exact + total_third_party
    
    # Method B: KPBI labour costs + third party costs
    total_kpbi = total_labour_kpbi + total_third_party
    
    # Discipline-wise totals (for exact method)
    if not labour_df.empty:
        discipline_totals = labour_df.groupby("Discipline", as_index=False).agg(
            Manhour=("Total Hours", "sum"),
            **{f"Labour Cost ({currency})": (f"Labour Cost ({currency})", "sum")},
        )
    else:
        discipline_totals = pd.DataFrame(columns=["Discipline", "Manhour", f"Labour Cost ({currency})"])
    
    # Apply monthly loading
    monthly_breakdown = apply_monthly_loading(labour_df, third_party_df, monthly_loading_df, currency)
    
    return {
        "total_hours": total_hours,
        "total_labour_exact": total_labour_exact,
        "total_labour_kpbi": total_labour_kpbi,
        "total_third_party": total_third_party,
        "total_exact": total_exact,
        "total_kpbi": total_kpbi,
        "kpbi_rate": kpbi_rate,
        "discipline_totals": discipline_totals,
        "monthly_breakdown": monthly_breakdown
    }


# ──────────────────────────────────────────────────────────────────────────────
# Project Saving/Loading for Comparison
# ──────────────────────────────────────────────────────────────────────────────
def save_current_project():
    """Save current project configuration and results for later comparison"""
    type_of_schedule = st.session_state["type_of_schedule"]
    rate_source = st.session_state["rate_source"]
    currency = currency_for(type_of_schedule)
    kpbi_rate = st.session_state["kpbi_rate"]
    
    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
    total_labour = float(labour_df[f"Labour Cost ({currency})"].sum()) if not labour_df.empty else 0.0
    third_party_df = calculate_third_party_costs(st.session_state[THIRD_PARTY_KEY], total_labour, currency)
    totals = compute_totals(labour_df, third_party_df, st.session_state[MONTHLY_LOADING_KEY], currency, kpbi_rate)
    
    project_data = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "name": st.session_state["project_title"] or f"Project_{datetime.now().strftime('%Y%m%d_%H%M')}",
        "timestamp": datetime.now().isoformat(),
        "project_title": st.session_state["project_title"],
        "type_of_package": st.session_state["type_of_package"],
        "type_of_schedule": type_of_schedule,
        "rate_source": rate_source,
        "currency": currency,
        "kpbi_rate": kpbi_rate,
        "total_hours": totals["total_hours"],
        "total_labour_exact": totals["total_labour_exact"],
        "total_labour_kpbi": totals["total_labour_kpbi"],
        "total_third_party": totals["total_third_party"],
        "total_exact": totals["total_exact"],
        "total_kpbi": totals["total_kpbi"],
        "discipline_totals": totals["discipline_totals"].to_dict('records') if not totals["discipline_totals"].empty else [],
        "labour_line_items": labour_df.to_dict('records'),
        "third_party_items": third_party_df.to_dict('records'),
        "personnel_count": len(st.session_state[GRID_KEY]),
        "disciplines_used": st.session_state[GRID_KEY]["Discipline"].nunique()
    }
    
    # Add to saved projects
    st.session_state[SAVED_PROJECTS_KEY].append(project_data)
    return project_data


def compare_projects(project1, project2):
    """Compare two projects and return comparison metrics"""
    comparison = {
        "hours_diff": project2["total_hours"] - project1["total_hours"],
        "hours_pct": ((project2["total_hours"] - project1["total_hours"]) / project1["total_hours"] * 100) if project1["total_hours"] > 0 else 0,
        "exact_cost_diff": project2["total_exact"] - project1["total_exact"],
        "exact_cost_pct": ((project2["total_exact"] - project1["total_exact"]) / project1["total_exact"] * 100) if project1["total_exact"] > 0 else 0,
        "kpbi_cost_diff": project2["total_kpbi"] - project1["total_kpbi"],
        "kpbi_cost_pct": ((project2["total_kpbi"] - project1["total_kpbi"]) / project1["total_kpbi"] * 100) if project1["total_kpbi"] > 0 else 0,
    }
    
    return comparison


# ──────────────────────────────────────────────────────────────────────────────
# Export to Excel (styled; multiple sheets)
# ──────────────────────────────────────────────────────────────────────────────
def to_excel_bytes(main_meta: pd.DataFrame, totals: dict, labour_df: pd.DataFrame, 
                   third_party_df: pd.DataFrame, monthly_df: pd.DataFrame, 
                   schedule_label: str, currency: str):
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    wb = Workbook()
    BRAND_HEX = BRAND1.replace("#", "")
    LIGHT = "E6F9F7"
    WHITE = "FFFFFF"
    THIN = Side(style="thin", color="999999")
    MED = Side(style="medium", color="000000")

    def paint_range(ws, rng, fill=None, font=None, align=None, border=None):
        for row in ws[rng]:
            for cell in row:
                if fill:
                    cell.fill = fill
                if font:
                    cell.font = font
                if align:
                    cell.alignment = align
                if border:
                    cell.border = border

    def set_col_w(ws, widths):
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

    # Main Page
    ws = wb.active
    ws.title = "Main Page"
    ws.merge_cells("B2:I3")
    ws["B2"].value = "MAJOR ENGINEERING CONTRACT (MEC) TOOL FOR CE UPSTREAM"
    paint_range(
        ws,
        "B2:I3",
        fill=PatternFill("solid", fgColor=BRAND_HEX),
        font=Font(color=WHITE, bold=True, size=12),
        align=Alignment(horizontal="center", vertical="center"),
    )

    fields = [
        ("PROJECT TITLE", main_meta.iloc[0].get("Project Title", "")),
        ("DATE", main_meta.iloc[0].get("Date", "")),
        ("COST ENGINEER", main_meta.iloc[0].get("Cost Engineer", "")),
        ("TP/SPECIALIST", main_meta.iloc[0].get("TP/Specialist", "")),
        ("TYPE OF PACKAGE", main_meta.iloc[0].get("Type of Package", "")),
        ("TYPE OF SCHEDULE", main_meta.iloc[0].get("Type of Schedule", "")),
        ("KPBI RATE", f"{main_meta.iloc[0].get('KPBI Rate', 0):,.2f}"),
    ]
    r0 = 6
    for i, (lbl, val) in enumerate(fields):
        r = r0 + i
        ws[f"C{r}"].value = lbl
        ws[f"E{r}"].value = val
        ws[f"C{r}"].font = Font(bold=True)
        paint_range(ws, f"E{r}:I{r}", fill=PatternFill("solid", fgColor=LIGHT), border=Border(left=THIN, right=THIN, top=THIN, bottom=THIN))

    # Summary Results
    summary_r = r0 + len(fields) + 3
    ws[f"C{summary_r}"].value = "SUMMARY RESULTS"
    ws[f"C{summary_r}"].font = Font(bold=True, size=14)
    
    results = [
        ("Total Manhours", f"{totals['total_hours']:,.0f}"),
        ("Labour Cost (Exact)", f"{currency} {totals['total_labour_exact']:,.2f}"),
        ("Labour Cost (KPBI)", f"{currency} {totals['total_labour_kpbi']:,.2f}"),
        ("Third Party Cost", f"{currency} {totals['total_third_party']:,.2f}"),
        ("METHOD A - Exact Total", f"{currency} {totals['total_exact']:,.2f}"),
        ("METHOD B - KPBI Total", f"{currency} {totals['total_kpbi']:,.2f}"),
    ]
    
    for i, (lbl, val) in enumerate(results):
        r = summary_r + 2 + i
        ws[f"C{r}"].value = lbl
        ws[f"E{r}"].value = val
        ws[f"C{r}"].font = Font(bold=True)

    notes = summary_r + len(results) + 5
    ws[f"C{notes}"].value = "Notes:"
    ws[f"C{notes}"].font = Font(bold=True)
    ws[f"C{notes+2}"].value = "Type of Package"
    ws[f"C{notes+3}"].value = "Package U1"; ws[f"E{notes+3}"].value = "Feasibility Study & Conceptual Engineering for Upstream"
    ws[f"C{notes+4}"].value = "Package U2"; ws[f"E{notes+4}"].value = "FEED & Detailed Design for Upstream"
    ws[f"C{notes+6}"].value = "Type of Schedule"; ws[f"F{notes+6}"].value = "Currency"
    for i, (tag, desc, cur) in enumerate([
        ("Schedule A", "Malaysia Project (Malaysia Base)", "MYR"),
        ("Schedule B", "Malaysia Project (International Base)", "USD"),
        ("Schedule C", "International Project (Malaysia Base)", "MYR"),
        ("Schedule D", "International Project (International Base)", "USD"),
    ]):
        rr = notes + 7 + i
        ws[f"C{rr}"].value = tag
        ws[f"D{rr}"].value = desc
        ws[f"F{rr}"].value = cur

    set_col_w(ws, {"B": 2, "C": 22, "D": 40, "E": 36, "F": 12, "G": 10, "H": 10, "I": 6})
    ws.freeze_panes = "B6"

    # Labour Working Page
    ws2 = wb.create_sheet("Labour Costs")
    ws2.merge_cells("B2:U3")
    ws2["B2"].value = "LABOUR COSTS"
    paint_range(
        ws2,
        "B2:U3",
        fill=PatternFill("solid", fgColor=BRAND_HEX),
        font=Font(color="FFFFFF", bold=True, size=12),
        align=Alignment(horizontal="center", vertical="center"),
    )

    headers = list(labour_df.columns)
    start_row = 5
    for j, h in enumerate(headers, start=2):
        c = ws2.cell(row=start_row, column=j, value=h)
        c.fill = PatternFill("solid", fgColor="E6F9F7")
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")
        c.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    set_col_w(ws2, {"B": 16, "C": 30, "D": 18, "E": 18, "F": 14, "U": 22})
    ws2.freeze_panes = "B6"

    cur_r = start_row + 1
    for _, row in labour_df.iterrows():
        for j, val in enumerate(row, start=2):
            cell = ws2.cell(row=cur_r, column=j, value=val)
            cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        cur_r += 1

    # Third Party Page
    ws3 = wb.create_sheet("Third Party & Non-Labour")
    ws3.merge_cells("B2:J3")
    ws3["B2"].value = "THIRD PARTY & NON-LABOUR COSTS"
    paint_range(
        ws3,
        "B2:J3",
        fill=PatternFill("solid", fgColor=BRAND_HEX),
        font=Font(color="FFFFFF", bold=True, size=12),
        align=Alignment(horizontal="center", vertical="center"),
    )

    tp_headers = list(third_party_df.columns)
    start_row_tp = 5
    for j, h in enumerate(tp_headers, start=2):
        c = ws3.cell(row=start_row_tp, column=j, value=h)
        c.fill = PatternFill("solid", fgColor="E6F9F7")
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")
        c.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    cur_r_tp = start_row_tp + 1
    for _, row in third_party_df.iterrows():
        for j, val in enumerate(row, start=2):
            cell = ws3.cell(row=cur_r_tp, column=j, value=val)
            cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        cur_r_tp += 1

    # Monthly Loading Page
    ws4 = wb.create_sheet("Monthly Loading")
    ws4.merge_cells("B2:H3")
    ws4["B2"].value = "MONTHLY LOADING DISTRIBUTION"
    paint_range(
        ws4,
        "B2:H3",
        fill=PatternFill("solid", fgColor=BRAND_HEX),
        font=Font(color="FFFFFF", bold=True, size=12),
        align=Alignment(horizontal="center", vertical="center"),
    )

    monthly_headers = list(monthly_df.columns) + [f"Labour Cost ({currency})", f"Third Party ({currency})", f"Total ({currency})"]
    start_row_monthly = 5
    for j, h in enumerate(monthly_headers, start=2):
        c = ws4.cell(row=start_row_monthly, column=j, value=h)
        c.fill = PatternFill("solid", fgColor="E6F9F7")
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")
        c.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    monthly_breakdown = totals["monthly_breakdown"]
    cur_r_monthly = start_row_monthly + 1
    for i, month in enumerate(monthly_breakdown["months"]):
        ws4.cell(row=cur_r_monthly, column=2, value=month).border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        ws4.cell(row=cur_r_monthly, column=3, value=monthly_df.iloc[i]["Loading Factor (%)"]).border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        ws4.cell(row=cur_r_monthly, column=4, value=monthly_df.iloc[i]["Weightage Distribution"]).border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        
        cell_labour = ws4.cell(row=cur_r_monthly, column=5, value=monthly_breakdown["monthly_labour"][month])
        cell_labour.number_format = f'"{currency}" #,##0.00'
        cell_labour.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        
        cell_tp = ws4.cell(row=cur_r_monthly, column=6, value=monthly_breakdown["monthly_third_party"][month])
        cell_tp.number_format = f'"{currency}" #,##0.00'
        cell_tp.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        
        cell_total = ws4.cell(row=cur_r_monthly, column=7, value=monthly_breakdown["total_by_month"][month])
        cell_total.number_format = f'"{currency}" #,##0.00'
        cell_total.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        
        cur_r_monthly += 1

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Navigation helpers
# ──────────────────────────────────────────────────────────────────────────────
def render_navigation():
    """Render the navigation buttons at the top of the page"""
    current_page = st.session_state["page"]
    
    # Create navigation buttons
    cols = st.columns(len(PAGES))
    
    for idx, (page_key, page_label) in enumerate(PAGES.items()):
        with cols[idx]:
            if st.button(
                page_label,
                key=f"nav_{page_key}",
                use_container_width=True,
                type="primary" if current_page == page_key else "secondary"
            ):
                st.session_state["page"] = page_key
                do_rerun()
    
    # Add visual indicator
    st.markdown(
        f"""
        <div style="text-align: center; margin: 10px 0 20px 0;">
            <span style="background: var(--brand1); color: white; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 0.9rem;">
                📍 Current: {PAGES[current_page].replace('🏠', '').replace('👥', '').replace('💰', '').replace('📅', '').replace('📊', '').replace('📈', '').replace('🔄', '').strip()}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("---")


def reset_grid():
    tmp_schedule = st.session_state["type_of_schedule"]
    categories = build_category_options(tmp_schedule, st.session_state["rate_source"], data_tbl, u1_tbl, u2_tbl)
    if not categories:
        categories = B_D_CATEGORY_FALLBACK if is_usd(tmp_schedule) else AC_CATEGORIES
    rows = []
    for disc, count in DISCIPLINE_ROW_COUNTS.items():
        defaults = DEFAULT_PERSONNEL.get(disc, [])
        for i in range(count):
            personnel = defaults[i] if i < len(defaults) else (PERSONNEL_LIST[0] if PERSONNEL_LIST else "")
            rows.append(
                {
                    "Swatch": DISCIPLINE_SWATCH.get(disc, "⬜"),
                    "Discipline": disc,
                    "Personnel": personnel,
                    "Category": categories[0] if categories else "",
                    "Type of Unit Rate": "Normalise",
                    "Weightage (FTE)": 0.0,
                    "Duration (months)": 1.0,
                }
            )
    st.session_state[GRID_KEY] = pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# Page renderers
# ──────────────────────────────────────────────────────────────────────────────
def render_main():
    st.markdown(
        f"""
        <h1 style="color: var(--brand1); margin-bottom: 0.5rem;">MEC TOOL</h1>
        <p style="color: var(--text-muted); font-size: 1.1rem; margin-bottom: 2rem;">
          Major Engineering Contract Tool for CE Upstream
        </p>
        """,
        unsafe_allow_html=True,
    )
    
    st.caption(f"📁 Uploaded CSV Files: DATA.csv, U1.csv, U2.csv")

    st.markdown("<hr style='margin: 2rem 0;'/>", unsafe_allow_html=True)
    st.header("Main Page")

    mp1, mp2 = st.columns(2)
    with mp1:
        st.session_state["project_title"] = st.text_input(
            "Project Title",
            value=st.session_state["project_title"],
            placeholder="e.g., PROJECT A",
            help="Enter the project title for identification"
        )
        st.session_state["cost_engineer"] = st.text_input(
            "Cost Engineer", 
            value=st.session_state["cost_engineer"], 
            placeholder="Your name",
            help="Name of the cost engineer responsible"
        )
        st.session_state["tp_specialist"] = st.text_input(
            "TP/Specialist", 
            value=st.session_state["tp_specialist"], 
            placeholder="TP in charge",
            help="Technical Professional or Specialist in charge"
        )

    with mp2:
        st.session_state["project_date"] = st.date_input(
            "Date", 
            value=st.session_state["project_date"],
            help="Project date"
        )
        st.session_state["type_of_package"] = st.selectbox(
            "Type of Package",
            package_opts,
            index=max(
                0,
                package_opts.index(st.session_state["type_of_package"])
                if st.session_state["type_of_package"] in package_opts
                else 0,
            ),
            help="Select the package type (U1/U2)"
        )
        st.session_state["type_of_schedule"] = st.selectbox(
            "Type of Schedule (from DATA.csv)",
            schedule_opts if schedule_opts else ["Schedule A", "Schedule B", "Schedule C", "Schedule D"],
            index=0
            if not schedule_opts
            else max(
                0,
                schedule_opts.index(st.session_state["type_of_schedule"])
                if st.session_state["type_of_schedule"] in schedule_opts
                else 0,
            ),
            help="Select the schedule type (A/B/C/D)"
        )

    rs1, rs2 = st.columns([1, 2])
    with rs1:
        package_to_rate = {"U1": "U1", "U2": "U2"}
        default_rate = package_to_rate.get(st.session_state["type_of_package"], "Data")
        st.session_state["rate_source"] = st.radio(
            "Rate Source", RATE_SOURCES, index=RATE_SOURCES.index(default_rate), horizontal=True
        )
    with rs2:
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

    # KPBI Rate input
    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("KPBI Rate Settings (Method B)")
    kpbi_col1, kpbi_col2 = st.columns([1, 3])
    with kpbi_col1:
        st.session_state["kpbi_rate"] = st.number_input(
            "KPBI Rate (per hour)",
            min_value=0.0,
            value=st.session_state.get("kpbi_rate", 0.0),
            step=10.0,
            format="%.2f",
            help="KPBI rate to be used for Method B calculation"
        )
    with kpbi_col2:
        st.info("Method B calculates labour costs using: Total Hours × KPBI Rate + Third Party Costs")

    st.markdown("<br/>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("➡️ Go to Personnel Table", use_container_width=True, type="primary"):
            st.session_state["page"] = "TABLE"
            do_rerun()
    with c2:
        if st.button("↺ Reset Grid to Defaults", use_container_width=True):
            reset_grid()
            do_rerun()
    with c3:
        if st.button("💰 Third Party Costs", use_container_width=True):
            st.session_state["page"] = "THIRD_PARTY"
            do_rerun()


def render_table():
    type_of_schedule = st.session_state["type_of_schedule"]
    rate_source = st.session_state["rate_source"]
    currency = currency_for(type_of_schedule)

    category_options_global = build_category_options(type_of_schedule, rate_source, data_tbl, u1_tbl, u2_tbl)
    if not category_options_global:
        category_options_global = B_D_CATEGORY_FALLBACK if is_usd(type_of_schedule) else AC_CATEGORIES

    st.header(f"Personnel Table — Currency: {currency}")

    # Reconcile categories after schedule/source changes
    df_tmp = st.session_state[GRID_KEY].copy()
    if "Category" in df_tmp.columns and category_options_global:
        df_tmp["Category"] = df_tmp["Category"].where(df_tmp["Category"].isin(category_options_global), category_options_global[0])
    df_tmp["Swatch"] = df_tmp["Discipline"].map(DISCIPLINE_SWATCH).fillna("⬜")
    st.session_state[GRID_KEY] = df_tmp

    # Bulk actions
    st.subheader("Bulk actions")
    c_w, c_cat, c_type, c_dur = st.columns(4)
    with c_w:
        new_w = st.number_input("Weightage for ALL", min_value=0.0, step=0.1, value=0.0, key="bulk_w")
        if st.button("Apply weightage", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df["Weightage (FTE)"] = float(st.session_state["bulk_w"])
            st.session_state[GRID_KEY] = df
            do_rerun()
    with c_cat:
        new_cat = st.selectbox("Category for ALL", category_options_global, key="bulk_cat")
        if st.button("Apply category", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df["Category"] = st.session_state["bulk_cat"]
            st.session_state[GRID_KEY] = df
            do_rerun()
    with c_type:
        # UPDATED: Using new UNIT_TYPES with Rate A, Rate B, etc.
        new_type = st.selectbox("Type of Unit Rate for ALL", UNIT_TYPES, key="bulk_type")
        if st.button("Apply type", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df["Type of Unit Rate"] = st.session_state["bulk_type"]
            st.session_state[GRID_KEY] = df
            do_rerun()
    with c_dur:
        new_dur = st.number_input("Duration for ALL (months)", min_value=0, step=1, value=1, key="bulk_dur")
        if st.button("Apply duration", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df["Duration (months)"] = int(st.session_state["bulk_dur"])
            st.session_state[GRID_KEY] = df
            do_rerun()

    # Row controls
    st.markdown("<br/>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("➕ Add blank row", use_container_width=True):
            df = st.session_state[GRID_KEY].copy()
            df.loc[len(df)] = {
                "Swatch": "⬜",
                "Discipline": list(DISCIPLINE_ROW_COUNTS.keys())[0],
                "Personnel": (PERSONNEL_LIST[0] if PERSONNEL_LIST else ""),
                "Category": category_options_global[0] if category_options_global else "",
                "Type of Unit Rate": "Normalise",
                "Weightage (FTE)": 0.0,
                "Duration (months)": 1.0,
            }
            st.session_state[GRID_KEY] = df
            do_rerun()
    with c2:
        if st.button("↺ Reset to defaults", use_container_width=True):
            reset_grid()
            do_rerun()
    with c3:
        if st.button("📅 Next: Monthly Loading", use_container_width=True):
            st.session_state["page"] = "LOADING"
            do_rerun()

    # ── AG Grid ────────────────────────────────────────────────────────────────
    df = st.session_state[GRID_KEY].copy()

    # Downcast types: categorical reduces JSON payload
    categoricals = ["Discipline", "Personnel", "Category", "Type of Unit Rate"]
    for col in categoricals:
        if col in df.columns:
            df[col] = df[col].astype("category")
    for col in ["Weightage (FTE)", "Duration (months)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    # Dynamic grid height
    row_height, header_height = 34, 36
    grid_height = min(700, max(260, int(len(df) * row_height + header_height + 16)))

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_grid_options(rowHeight=row_height, headerHeight=header_height, suppressMenuHide=True, ensureDomOrder=True)
    gb.configure_default_column(resizable=True, sortable=True, filter=True, wrapText=False)

    gb.configure_column("Swatch", pinned="left", width=70, editable=False)
    gb.configure_column(
        "Discipline",
        pinned="left",
        width=190,
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": list(DISCIPLINE_ROW_COUNTS.keys())},
    )
    gb.configure_column(
        "Personnel",
        width=260,
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": PERSONNEL_LIST},
    )
    gb.configure_column(
        "Category",
        width=240,
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": category_options_global},
    )
    # UPDATED: Using new UNIT_TYPES
    gb.configure_column(
        "Type of Unit Rate",
        width=220,
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": UNIT_TYPES},
    )
    gb.configure_column("Weightage (FTE)", type=["numericColumn"], width=170, editable=True)
    gb.configure_column("Duration (months)", type=["numericColumn"], width=170, editable=True)

    # Row tint by discipline
    disc_bg = {k: f"#{v}" for k, v in DISCIPLINE_COLORS.items()}
    row_style_js = JsCode(
        """
function(params) {
  const map = %s;
  const disc = (params && params.data && params.data.Discipline) ? params.data.Discipline : "";
  const bg = map[disc] || null;
  return bg ? { backgroundColor: bg } : null;
}
""" % json.dumps(disc_bg)
    )
    gb.configure_grid_options(getRowStyle=row_style_js)
    grid_opts = gb.build()

    aggrid_common = dict(
        gridOptions=grid_opts,
        height=grid_height,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        theme="streamlit",
    )

    try:
        grid_resp = AgGrid(df, update_on="value_changed", **aggrid_common)  # new API
    except TypeError:
        # Fallback to old API name
        grid_resp = AgGrid(df, update_mode=GridUpdateMode.VALUE_CHANGED, **aggrid_common)

    df_current = pd.DataFrame(grid_resp["data"])
    st.session_state[GRID_KEY] = df_current

    # Quick preview of labour costs
    st.subheader("Labour Cost Preview")
    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0
    
    st.markdown(
        f"""
        <div style="background: var(--surface-alt); padding: 1rem; border-radius: 10px;">
            <h3 style="margin: 0; color: var(--brand1);">Total Labour Cost: {currency} {total_labour:,.2f}</h3>
            <p style="margin: 0.5rem 0 0 0; color: var(--text-muted);">Based on current personnel entries</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_third_party():
    st.header("💰 Third Party & Non-Labour Costs")
    st.caption("Add third party services, equipment rental, software, and other non-labour costs")
    
    currency = currency_for(st.session_state["type_of_schedule"])
    
    # Get current labour total for percentage calculations
    labour_df = calculate_labour_costs(
        st.session_state[GRID_KEY], 
        currency, 
        st.session_state["rate_source"], 
        st.session_state["type_of_schedule"]
    )
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0
    
    st.info(f"Current Total Labour Cost: {currency} {total_labour:,.2f}")
    
    # Third Party Items Table
    df = st.session_state[THIRD_PARTY_KEY].copy()
    
    # Editable columns
    col1, col2, col3, col4, col5 = st.columns([2, 3, 1.5, 1.5, 2])
    with col1:
        st.markdown("**Category**")
    with col2:
        st.markdown("**Description**")
    with col3:
        st.markdown("**Basis**")
    with col4:
        st.markdown("**% / Amount**")
    with col5:
        st.markdown("**Remarks**")
    
    # Display editable rows
    for idx, row in df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 3, 1.5, 1.5, 2])
        
        with col1:
            df.loc[idx, "Category"] = st.selectbox(
                f"cat_{idx}",
                THIRD_PARTY_CATEGORIES,
                index=THIRD_PARTY_CATEGORIES.index(row["Category"]) if row["Category"] in THIRD_PARTY_CATEGORIES else 0,
                label_visibility="collapsed",
                key=f"cat_{idx}"
            )
        
        with col2:
            df.loc[idx, "Description"] = st.text_input(
                f"desc_{idx}",
                value=row["Description"],
                label_visibility="collapsed",
                placeholder="Description",
                key=f"desc_{idx}"
            )
        
        with col3:
            basis_options = ["% of Labour Cost", "Fixed Amount"]
            df.loc[idx, "Basis"] = st.selectbox(
                f"basis_{idx}",
                basis_options,
                index=basis_options.index(row["Basis"]) if row["Basis"] in basis_options else 0,
                label_visibility="collapsed",
                key=f"basis_{idx}"
            )
        
        with col4:
            if df.loc[idx, "Basis"] == "% of Labour Cost":
                df.loc[idx, "Percentage"] = st.number_input(
                    f"pct_{idx}",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(row["Percentage"]),
                    step=0.1,
                    format="%.1f",
                    label_visibility="collapsed",
                    key=f"pct_{idx}"
                )
                # Clear fixed amount when using percentage
                df.loc[idx, "Fixed Amount"] = 0.0
            else:
                df.loc[idx, "Fixed Amount"] = st.number_input(
                    f"amt_{idx}",
                    min_value=0.0,
                    value=float(row["Fixed Amount"]),
                    step=100.0,
                    format="%.2f",
                    label_visibility="collapsed",
                    key=f"amt_{idx}"
                )
                # Clear percentage when using fixed amount
                df.loc[idx, "Percentage"] = 0.0
        
        with col5:
            df.loc[idx, "Remarks"] = st.text_input(
                f"rem_{idx}",
                value=row["Remarks"],
                label_visibility="collapsed",
                placeholder="Remarks",
                key=f"rem_{idx}"
            )
    
    st.session_state[THIRD_PARTY_KEY] = df
    
    # Add/Remove rows
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("➕ Add Item", use_container_width=True):
            new_row = pd.DataFrame([{
                "Category": THIRD_PARTY_CATEGORIES[0],
                "Description": "",
                "Basis": "% of Labour Cost",
                "Percentage": 0.0,
                "Fixed Amount": 0.0,
                "Remarks": ""
            }])
            st.session_state[THIRD_PARTY_KEY] = pd.concat([df, new_row], ignore_index=True)
            do_rerun()
    
    with col2:
        if st.button("🗑️ Remove Last Item", use_container_width=True) and len(df) > 0:
            st.session_state[THIRD_PARTY_KEY] = df.iloc[:-1].reset_index(drop=True)
            do_rerun()
    
    with col3:
        if st.button("📅 Next: Monthly Loading", use_container_width=True):
            st.session_state["page"] = "LOADING"
            do_rerun()
    
    # Calculate and display third party costs
    if len(df) > 0:
        st.subheader("Calculated Costs")
        third_party_costs = calculate_third_party_costs(df, total_labour, currency)
        
        # Display costs table
        cost_display = third_party_costs.copy()
        cost_display[f"Cost ({currency})"] = cost_display[f"Cost ({currency})"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(cost_display, use_container_width=True)
        
        total_third_party = third_party_costs[f"Cost ({currency})"].sum()
        st.markdown(
            f"""
            <div style="background: var(--surface-alt); padding: 1rem; border-radius: 10px; margin-top: 1rem;">
                <h3 style="margin: 0; color: var(--brand1);">Total Third Party Cost: {currency} {total_third_party:,.2f}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_loading():
    st.header("📅 Monthly Loading")
    st.caption("Configure monthly loading factors and weightage distribution")
    
    currency = currency_for(st.session_state["type_of_schedule"])
    
    # Get current costs
    labour_df = calculate_labour_costs(
        st.session_state[GRID_KEY], 
        currency, 
        st.session_state["rate_source"], 
        st.session_state["type_of_schedule"]
    )
    total_labour = labour_df[f"Labour Cost ({currency})"].sum() if not labour_df.empty else 0
    
    third_party_df = calculate_third_party_costs(
        st.session_state[THIRD_PARTY_KEY], 
        total_labour, 
        currency
    )
    
    df = st.session_state[MONTHLY_LOADING_KEY].copy()
    
    # Month configuration
    st.subheader("Monthly Distribution")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        num_months = st.number_input(
            "Number of Months",
            min_value=1,
            max_value=60,
            value=len(df),
            step=1,
            help="Adjust project duration in months"
        )
    
    with col2:
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("Update", use_container_width=True):
            if num_months != len(df):
                # Resize the dataframe
                months = [f"Month {i+1:02d}" for i in range(num_months)]
                if num_months > len(df):
                    # Add more months with default values
                    additional = pd.DataFrame({
                        "Month": months[len(df):],
                        "Loading Factor (%)": [100.0] * (num_months - len(df)),
                        "Weightage Distribution": [100.0/num_months] * (num_months - len(df))
                    })
                    df = pd.concat([df.iloc[:len(df)], additional], ignore_index=True)
                else:
                    # Remove months
                    df = df.iloc[:num_months].reset_index(drop=True)
                
                # Rebalance weightage distribution
                total_weight = df["Weightage Distribution"].sum()
                if total_weight != 100:
                    df["Weightage Distribution"] = 100.0 / num_months
                
                st.session_state[MONTHLY_LOADING_KEY] = df
                do_rerun()
    
    with col3:
        st.info("Loading factors multiply the cost for each month")
    
    # Display monthly table
    st.subheader("Monthly Factors")
    
    # Create editable columns for each month
    for idx, row in df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
        
        with col1:
            st.write(f"**{row['Month']}**")
        
        with col2:
            df.loc[idx, "Loading Factor (%)"] = st.number_input(
                f"load_{idx}",
                min_value=0.0,
                max_value=200.0,
                value=float(row["Loading Factor (%)"]),
                step=5.0,
                format="%.1f",
                label_visibility="collapsed",
                key=f"load_{idx}"
            )
        
        with col3:
            df.loc[idx, "Weightage Distribution"] = st.number_input(
                f"weight_{idx}",
                min_value=0.0,
                max_value=100.0,
                value=float(row["Weightage Distribution"]),
                step=0.1,
                format="%.1f",
                label_visibility="collapsed",
                key=f"weight_{idx}"
            )
        
        # Calculate effective loading
        effective = (df.loc[idx, "Loading Factor (%)"] / 100.0) * (df.loc[idx, "Weightage Distribution"] / 100.0) * 100
        with col4:
            st.metric("Effective %", f"{effective:.1f}%")
        
        # Preview cost for this month
        month_cost = total_labour * (df.loc[idx, "Weightage Distribution"] / 100.0) * (df.loc[idx, "Loading Factor (%)"] / 100.0)
        with col5:
            st.write(f"{currency} {month_cost:,.0f}")
    
    # Validate weightage sum
    total_weight = df["Weightage Distribution"].sum()
    if abs(total_weight - 100.0) > 0.01:
        st.warning(f"Weightage Distribution total is {total_weight:.1f}%. Should be 100% for accurate distribution.")
    
    st.session_state[MONTHLY_LOADING_KEY] = df
    
    # Preview monthly breakdown
    st.subheader("Monthly Cost Preview")
    
    monthly_breakdown = apply_monthly_loading(labour_df, third_party_df, df, currency)
    
    # Create preview table
    preview_data = []
    for month in monthly_breakdown["months"]:
        preview_data.append({
            "Month": month,
            f"Labour ({currency})": monthly_breakdown["monthly_labour"][month],
            f"Third Party ({currency})": monthly_breakdown["monthly_third_party"][month],
            f"Total ({currency})": monthly_breakdown["total_by_month"][month]
        })
    
    preview_df = pd.DataFrame(preview_data)
    
    # Format for display
    display_preview = preview_df.copy()
    for col in display_preview.columns[1:]:
        display_preview[col] = display_preview[col].apply(lambda x: f"{x:,.2f}")
    
    st.dataframe(display_preview, use_container_width=True)
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Back to Third Party", use_container_width=True):
            st.session_state["page"] = "THIRD_PARTY"
            do_rerun()
    with col2:
        if st.button("📊 Go to Totals", use_container_width=True, type="primary"):
            st.session_state["page"] = "TOTALS"
            do_rerun()
    with col3:
        if st.button("↺ Reset to Default", use_container_width=True):
            months = [f"Month {i+1:02d}" for i in range(12)]
            default_df = pd.DataFrame({
                "Month": months,
                "Loading Factor (%)": [100.0] * 12,
                "Weightage Distribution": [100.0/12] * 12
            })
            st.session_state[MONTHLY_LOADING_KEY] = default_df
            do_rerun()


def render_totals():
    type_of_schedule = st.session_state["type_of_schedule"]
    rate_source = st.session_state["rate_source"]
    currency = currency_for(type_of_schedule)
    kpbi_rate = st.session_state["kpbi_rate"]

    # Calculate all costs
    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
    total_labour = float(labour_df[f"Labour Cost ({currency})"].sum()) if not labour_df.empty else 0.0
    
    third_party_df = calculate_third_party_costs(st.session_state[THIRD_PARTY_KEY], total_labour, currency)
    totals = compute_totals(labour_df, third_party_df, st.session_state[MONTHLY_LOADING_KEY], currency, kpbi_rate)

    # Summary metrics with Method A (Exact) and Method B (KPBI)
    st.markdown(
        f"""
        <div class="summary-card">
            <h2 style="color: var(--brand1); margin-top: 0;">Project Summary</h2>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                <div>
                    <h3 style="color: var(--text-muted); margin-bottom: 0.5rem; font-size: 0.9rem;">Total Manhours</h3>
                    <div style="font-size: 2.2rem; font-weight: 700; color: var(--text);">{totals['total_hours']:,.0f}</div>
                </div>
                <div>
                    <h3 style="color: var(--text-muted); margin-bottom: 0.5rem; font-size: 0.9rem;">KPBI Rate</h3>
                    <div style="font-size: 2.2rem; font-weight: 700; color: var(--text);">{kpbi_rate:,.2f} {currency}/hr</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Method comparison cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>🔵 METHOD A — EXACT TOTAL</h3>
                <div class="value">{totals['total_exact']:,.2f} {currency}</div>
                <div class="subvalue">
                    Labour: {totals['total_labour_exact']:,.2f} {currency}<br/>
                    Third Party: {totals['total_third_party']:,.2f} {currency}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>🟢 METHOD B — KPBI RATE</h3>
                <div class="value">{totals['total_kpbi']:,.2f} {currency}</div>
                <div class="subvalue">
                    Labour (KPBI): {totals['total_labour_kpbi']:,.2f} {currency}<br/>
                    Third Party: {totals['total_third_party']:,.2f} {currency}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Labour cost breakdown
    st.subheader("Labour Cost Breakdown by Discipline")
    
    if not totals["discipline_totals"].empty:
        # Format for display
        display_discipline = totals["discipline_totals"].copy()
        display_discipline["Manhour"] = display_discipline["Manhour"].apply(lambda x: f"{x:,.0f}")
        display_discipline[f"Labour Cost ({currency})"] = display_discipline[f"Labour Cost ({currency})"].apply(lambda x: f"{x:,.2f}")
        
        st.dataframe(
            display_discipline,
            use_container_width=True,
            hide_index=True
        )
        
        # Bar chart
        fig = px.bar(
            totals["discipline_totals"].sort_values(f"Labour Cost ({currency})", ascending=True),
            y="Discipline",
            x=f"Labour Cost ({currency})",
            orientation='h',
            color="Discipline",
            color_discrete_map={d: f"#{DISCIPLINE_COLORS.get(d, 'D1D5DB')}" for d in totals["discipline_totals"]["Discipline"]},
            title=f"Labour Cost by Discipline ({currency})",
            height=400
        )
        fig.update_layout(
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Third Party Costs
    st.subheader("Third Party & Non-Labour Costs")
    if not third_party_df.empty:
        display_tp = third_party_df.copy()
        display_tp[f"Cost ({currency})"] = display_tp[f"Cost ({currency})"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(display_tp, use_container_width=True, hide_index=True)
    
    # Monthly Breakdown
    st.subheader("Monthly Cost Breakdown")
    
    monthly_breakdown = totals["monthly_breakdown"]
    if monthly_breakdown["months"]:
        # Create line chart for monthly costs
        monthly_data = []
        for month in monthly_breakdown["months"]:
            monthly_data.append({
                "Month": month,
                "Labour": monthly_breakdown["monthly_labour"][month],
                "Third Party": monthly_breakdown["monthly_third_party"][month],
                "Total": monthly_breakdown["total_by_month"][month]
            })
        
        monthly_df = pd.DataFrame(monthly_data)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly_df["Month"],
            y=monthly_df["Labour"],
            mode='lines+markers',
            name=f'Labour ({currency})',
            line=dict(color=BRAND1, width=3)
        ))
        fig.add_trace(go.Scatter(
            x=monthly_df["Month"],
            y=monthly_df["Third Party"],
            mode='lines+markers',
            name=f'Third Party ({currency})',
            line=dict(color=BRAND2, width=3)
        ))
        fig.add_trace(go.Scatter(
            x=monthly_df["Month"],
            y=monthly_df["Total"],
            mode='lines+markers',
            name=f'Total ({currency})',
            line=dict(color="#F59E0B", width=4, dash='dot')
        ))
        
        fig.update_layout(
            title="Monthly Cost Distribution",
            xaxis_title="Month",
            yaxis_title=f"Cost ({currency})",
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Navigation
    st.markdown("<br/>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("⬅️ Back to Loading", use_container_width=True):
            st.session_state["page"] = "LOADING"
            do_rerun()
    with col2:
        if st.button("💾 Save for Comparison", use_container_width=True):
            saved_project = save_current_project()
            st.success(f"Project '{saved_project['name']}' saved for comparison!")
            do_rerun()
    with col3:
        if st.button("📈 Go to Summary", use_container_width=True, type="primary"):
            st.session_state["page"] = "SUMMARY"
            do_rerun()
    with col4:
        if st.button("🔄 Compare", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            do_rerun()


def render_summary():
    type_of_schedule = st.session_state["type_of_schedule"]
    rate_source = st.session_state["rate_source"]
    currency = currency_for(type_of_schedule)
    kpbi_rate = st.session_state["kpbi_rate"]

    main_meta = pd.DataFrame(
        [
            {
                "Project Title": st.session_state["project_title"],
                "Date": str(st.session_state["project_date"]),
                "Cost Engineer": st.session_state["cost_engineer"],
                "TP/Specialist": st.session_state["tp_specialist"],
                "Type of Package": st.session_state["type_of_package"],
                "Type of Schedule": st.session_state["type_of_schedule"],
                "Rate Source Used": rate_source,
                "Currency": currency,
                "KPBI Rate": kpbi_rate,
                "Hours per Month (constant)": HOURS_PER_MONTH,
            }
        ]
    )

    # Calculate all costs
    labour_df = calculate_labour_costs(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
    total_labour = float(labour_df[f"Labour Cost ({currency})"].sum()) if not labour_df.empty else 0.0
    
    third_party_df = calculate_third_party_costs(st.session_state[THIRD_PARTY_KEY], total_labour, currency)
    totals = compute_totals(labour_df, third_party_df, st.session_state[MONTHLY_LOADING_KEY], currency, kpbi_rate)

    st.subheader("Main Page (entered)")
    st.dataframe(main_meta, use_container_width=True)

    # Method comparison
    st.subheader("Cost Comparison: Method A vs Method B")
    
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(data=[
            go.Bar(name='Method A (Exact)', x=['Total Cost'], y=[totals['total_exact']], marker_color=BRAND1),
            go.Bar(name='Method B (KPBI)', x=['Total Cost'], y=[totals['total_kpbi']], marker_color=BRAND2)
        ])
        fig.update_layout(
            title="Method Comparison",
            yaxis_title=f"Cost ({currency})",
            barmode='group',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Pie chart for cost components (Method A)
        fig = px.pie(
            values=[totals['total_labour_exact'], totals['total_third_party']],
            names=['Labour Cost', 'Third Party'],
            title="Cost Components (Method A)",
            color_discrete_sequence=[BRAND1, BRAND2],
            hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    # Labour cost breakdown
    if not labour_df.empty:
        st.subheader("Labour Cost Breakdown")
        
        # Group by discipline for visualization
        disc_summary = labour_df.groupby("Discipline").agg({
            "Total Hours": "sum",
            f"Labour Cost ({currency})": "sum"
        }).reset_index()
        
        # Sort by cost
        disc_summary = disc_summary.sort_values(f"Labour Cost ({currency})", ascending=True)
        
        fig = px.bar(
            disc_summary,
            y="Discipline",
            x=f"Labour Cost ({currency})",
            orientation='h',
            color="Discipline",
            title=f"Labour Cost by Discipline ({currency})",
            height=max(400, len(disc_summary) * 30)
        )
        fig.update_layout(
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # Download
    excel_blob = to_excel_bytes(
        main_meta, 
        totals, 
        labour_df, 
        third_party_df, 
        st.session_state[MONTHLY_LOADING_KEY],
        schedule_label=type_of_schedule, 
        currency=currency
    )
    
    try:
        st.download_button(
            "⬇️ Download Complete Report (Excel)",
            data=excel_blob,
            file_name=f"MEC_TOOL_{st.session_state['project_title'] or 'Output'}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            help="Complete report with all sheets: Main Page, Labour Costs, Third Party, Monthly Loading",
            use_container_width=True
        )
    except TypeError:
        st.download_button(
            "⬇️ Download Complete Report (Excel)",
            data=excel_blob,
            file_name=f"MEC_TOOL_{st.session_state['project_title'] or 'Output'}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Complete report with all sheets: Main Page, Labour Costs, Third Party, Monthly Loading",
            use_container_width=True
        )

    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Back to Totals", use_container_width=True):
            st.session_state["page"] = "TOTALS"
            do_rerun()
    with col2:
        if st.button("💾 Save for Comparison", use_container_width=True):
            saved_project = save_current_project()
            st.success(f"Project '{saved_project['name']}' saved for comparison!")
            do_rerun()
    with col3:
        if st.button("🔄 Compare Projects", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            do_rerun()


def render_compare():
    st.markdown(
        f"""
        <h1 style="color: var(--brand1); margin-bottom: 0.5rem;">Project Comparison</h1>
        <p style="color: var(--text-muted); font-size: 1.1rem; margin-bottom: 2rem;">
          Compare saved projects and analyze differences
        </p>
        """,
        unsafe_allow_html=True
    )
    
    saved_projects = st.session_state.get(SAVED_PROJECTS_KEY, [])
    
    if not saved_projects:
        st.info("No projects saved yet. Save projects from the Totals or Summary page to compare them.")
        st.markdown("<br/>", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("⬅️ Back to Summary", use_container_width=True):
                st.session_state["page"] = "SUMMARY"
                do_rerun()
        with c2:
            if st.button("🔁 Back to Main Page", use_container_width=True):
                st.session_state["page"] = "MAIN"
                do_rerun()
        return
    
    # Project selection
    st.subheader("Select Projects to Compare")
    
    project_names = [p["name"] for p in saved_projects]
    project_display = [f"{p['name']} ({p['type_of_schedule']}, {p['currency']})" for p in saved_projects]
    
    col1, col2 = st.columns(2)
    with col1:
        selected_idx_1 = st.selectbox(
            "First Project",
            range(len(saved_projects)),
            format_func=lambda i: project_display[i],
            key="compare_1"
        )
    
    with col2:
        selected_idx_2 = st.selectbox(
            "Second Project",
            range(len(saved_projects)),
            format_func=lambda i: project_display[i],
            index=min(1, len(saved_projects)-1) if len(saved_projects) > 1 else 0,
            key="compare_2"
        )
    
    if selected_idx_1 == selected_idx_2:
        st.warning("Please select two different projects for comparison.")
    else:
        project1 = saved_projects[selected_idx_1]
        project2 = saved_projects[selected_idx_2]
        
        comparison = compare_projects(project1, project2)
        
        # Summary comparison
        st.markdown("<br/>", unsafe_allow_html=True)
        st.subheader("Comparison Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            hours_change = comparison["hours_pct"]
            hours_badge = "up" if hours_change > 5 else "down" if hours_change < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Manhour Change</h3>
                    <div class="value">{comparison["hours_diff"]:+,.0f}</div>
                    <div class="subvalue">
                        <span class="comparison-badge {hours_badge}">
                            {comparison["hours_pct"]:+.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            exact_change = comparison["exact_cost_pct"]
            exact_badge = "up" if exact_change > 5 else "down" if exact_change < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Method A (Exact) Change</h3>
                    <div class="value">{comparison["exact_cost_diff"]:+,.2f} {project2['currency']}</div>
                    <div class="subvalue">
                        <span class="comparison-badge {exact_badge}">
                            {comparison["exact_cost_pct"]:+.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col3:
            kpbi_change = comparison["kpbi_cost_pct"]
            kpbi_badge = "up" if kpbi_change > 5 else "down" if kpbi_change < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Method B (KPBI) Change</h3>
                    <div class="value">{comparison["kpbi_cost_diff"]:+,.2f} {project2['currency']}</div>
                    <div class="subvalue">
                        <span class="comparison-badge {kpbi_badge}">
                            {comparison["kpbi_cost_pct"]:+.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Project management
    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("Manage Saved Projects")
    
    if saved_projects:
        # Display saved projects
        for i, project in enumerate(saved_projects):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(f"**{project['name']}**")
                st.caption(f"{project['type_of_schedule']} • {project['currency']}")
            with col2:
                st.caption(f"Method A: {project['total_exact']:,.2f}")
                st.caption(f"Method B: {project['total_kpbi']:,.2f}")
            with col3:
                st.caption(f"Saved: {datetime.fromisoformat(project['timestamp']).strftime('%Y-%m-%d %H:%M')}")
            with col4:
                if st.button("🗑️", key=f"delete_{i}", help="Delete project"):
                    st.session_state[SAVED_PROJECTS_KEY].pop(i)
                    st.success("Project deleted!")
                    do_rerun()
        
        # Clear all button
        if st.button("Clear All Saved Projects", type="secondary", use_container_width=True):
            st.session_state[SAVED_PROJECTS_KEY] = []
            st.success("All projects cleared!")
            do_rerun()
    
    st.markdown("<br/>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("⬅️ Back to Summary", use_container_width=True):
            st.session_state["page"] = "SUMMARY"
            do_rerun()
    with c2:
        if st.button("🔁 Back to Main Page", use_container_width=True):
            st.session_state["page"] = "MAIN"
            do_rerun()


# ──────────────────────────────────────────────────────────────────────────────
# TOP HERO + ROUTER
# ──────────────────────────────────────────────────────────────────────────────

# Main app header
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

# Navigation buttons
render_navigation()

# Render current page
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
