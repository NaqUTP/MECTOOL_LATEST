# streamlit_app.py
# MEC TOOL – Streamlit app (Excel upload mode; no internal files in repo)
# Author: Ahmad Naquib Syahmee Masror (Dev/Upstream)
# Updated: 2025-12-17
# ADDED: Project Comparison Feature
# MODIFIED: Single Excel file input (MEC TOOL.xlsx)

import io
import re
import json
import warnings
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import pandas as pd
import streamlit as st

# Silence harmless openpyxl validation warning (export uses openpyxl)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

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
      .project-card {{
        background: var(--surface-alt);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 4px solid var(--brand1);
      }}
      .comparison-metric {{
        background: var(--surface);
        border-radius: 8px;
        padding: 10px;
        text-align: center;
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
UNIT_TYPES = ["Minimum", "Maximum", "Normalise", "MMC", "DAR", "AKER", "TUAH", "PRW", "PUSB"]
RATE_SOURCES = ["Data", "U1", "U2"]

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
PROJECTS_KEY = "saved_projects"
COMPARE_KEY = "compare_selection"

# ──────────────────────────────────────────────────────────────────────────────
# Project Management Functions
# ──────────────────────────────────────────────────────────────────────────────
def save_current_project(project_name: str = None) -> str:
    """Save current project state to session state"""
    if PROJECTS_KEY not in st.session_state:
        st.session_state[PROJECTS_KEY] = {}
    
    if not project_name:
        project_name = st.session_state.get("project_title", f"Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # Create project snapshot
    project_data = {
        "id": hashlib.md5(f"{project_name}_{datetime.now().timestamp()}".encode()).hexdigest()[:8],
        "name": project_name,
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "project_title": st.session_state.get("project_title", ""),
            "cost_engineer": st.session_state.get("cost_engineer", ""),
            "tp_specialist": st.session_state.get("tp_specialist", ""),
            "project_date": str(st.session_state.get("project_date", "")),
            "type_of_package": st.session_state.get("type_of_package", ""),
            "type_of_schedule": st.session_state.get("type_of_schedule", ""),
            "rate_source": st.session_state.get("rate_source", ""),
        },
        "grid_data": st.session_state.get(GRID_KEY, pd.DataFrame()).to_dict(orient="records"),
        "totals": None,
        "line_items": None,
        "currency": None,
        "total_manhour": 0,
        "avg_rate": 0,
        "total_exact": 0,
    }
    
    # Calculate current totals if possible
    try:
        currency = currency_for(project_data["metadata"]["type_of_schedule"])
        df_out = compute_line_items(
            pd.DataFrame(project_data["grid_data"]),
            currency,
            project_data["metadata"]["rate_source"],
            project_data["metadata"]["type_of_schedule"]
        )
        total_manhour, avg_rate, total_by_average, total_exact, totals = compute_totals(df_out, currency)
        
        project_data.update({
            "totals": totals.to_dict(orient="records") if not totals.empty else [],
            "line_items": df_out.to_dict(orient="records") if not df_out.empty else [],
            "currency": currency,
            "total_manhour": float(total_manhour),
            "avg_rate": float(avg_rate),
            "total_by_average": float(total_by_average),
            "total_exact": float(total_exact),
        })
    except Exception as e:
        st.warning(f"Could not calculate totals for saving: {e}")
    
    # Save to session state
    st.session_state[PROJECTS_KEY][project_data["id"]] = project_data
    return project_data["id"]


def load_project(project_id: str) -> bool:
    """Load a saved project into current session"""
    if PROJECTS_KEY not in st.session_state or project_id not in st.session_state[PROJECTS_KEY]:
        return False
    
    project = st.session_state[PROJECTS_KEY][project_id]
    
    # Load metadata
    for key, value in project["metadata"].items():
        if key in st.session_state:
            st.session_state[key] = value
    
    # Load grid data
    if project["grid_data"]:
        st.session_state[GRID_KEY] = pd.DataFrame(project["grid_data"])
    
    return True


def delete_project(project_id: str):
    """Delete a saved project"""
    if PROJECTS_KEY in st.session_state and project_id in st.session_state[PROJECTS_KEY]:
        del st.session_state[PROJECTS_KEY][project_id]
        # Also remove from compare selection
        if COMPARE_KEY in st.session_state and project_id in st.session_state[COMPARE_KEY]:
            st.session_state[COMPARE_KEY].remove(project_id)


def get_project_summary_df() -> pd.DataFrame:
    """Get dataframe of all saved projects for display"""
    if PROJECTS_KEY not in st.session_state or not st.session_state[PROJECTS_KEY]:
        return pd.DataFrame()
    
    rows = []
    for project_id, project in st.session_state[PROJECTS_KEY].items():
        rows.append({
            "ID": project_id,
            "Project Name": project["name"],
            "Date": project["metadata"]["project_date"],
            "Schedule": project["metadata"]["type_of_schedule"],
            "Package": project["metadata"]["type_of_package"],
            "Currency": project.get("currency", ""),
            "Total Manhour": project.get("total_manhour", 0),
            "Avg Rate": project.get("avg_rate", 0),
            "Total Cost": project.get("total_exact", 0),
            "Saved": project["timestamp"][:10],
        })
    
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers (robust parsing + matching)
# ──────────────────────────────────────────────────────────────────────────────
NBSP = u"\xa0"
_num = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")  # robust number finder


def _to_float_safe(val: object) -> float:
    s = str(val or "").replace(",", "")
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
            # keep original name for rate columns
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
            cats = get_col(df, "category").dropna().astype(str).str.strip().unique().tolist()
            cats = [c for c in cats if c]
            if cats:
                return sorted(cats)
    return B_D_CATEGORY_FALLBACK if is_usd(schedule) else AC_CATEGORIES


def _rate_col_for_unit_type(df: pd.DataFrame, unit_type: str, prefer_usd: bool) -> Optional[str]:
    key = _canon(unit_type)
    pairs = [(_canon(c), c) for c in df.columns]
    if key.startswith("min"):
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
        if token in ("minimum", "maximum", "normalise") and ("unit rate" in k or "rate" in k):
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


# ──────────────────────────────────────────────────────────────────────────────
# Excel Upload Mode (single file with 3 sheets) — NOTHING stored in repo
# ──────────────────────────────────────────────────────────────────────────────
def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@st.cache_data(show_spinner=False, ttl=600)
def _read_excel_bytes(file_bytes: bytes) -> Dict[str, pd.DataFrame]:
    """Read Excel file and return dictionary of sheets"""
    try:
        # Read all sheets
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        
        # Check for required sheets
        required_sheets = ['Data', 'U1', 'U2']
        available_sheets = xls.sheet_names
        
        missing_sheets = [sheet for sheet in required_sheets if sheet not in available_sheets]
        if missing_sheets:
            st.error(f"Missing required sheets in Excel file: {', '.join(missing_sheets)}")
            st.info(f"Available sheets: {', '.join(available_sheets)}")
            return {}
        
        # Read each sheet
        sheets = {}
        for sheet_name in required_sheets:
            sheets[sheet_name] = xls.parse(sheet_name)
        
        return sheets
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return {}


def _load_tables_from_excel(excel_bytes: bytes) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load Data, U1, and U2 sheets from Excel file"""
    sheets = _read_excel_bytes(excel_bytes)
    
    if not sheets:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    data_tbl = _normalize_cols(sheets['Data'])
    u1_tbl = _normalize_cols(sheets['U1'])
    u2_tbl = _normalize_cols(sheets['U2'])
    
    return data_tbl, u1_tbl, u2_tbl


with st.sidebar:
    st.subheader("Rate Tables (Excel upload)")
    st.caption("Upload MEC TOOL.xlsx file with Data, U1, and U2 sheets.")
    
    up_excel = st.file_uploader("MEC TOOL.xlsx", type=["xlsx"], key="up_excel")
    
    st.markdown("---")
    st.subheader("Project Management")
    
    # Save current project
    save_col1, save_col2 = st.columns([2, 1])
    with save_col1:
        save_name = st.text_input("Save as", value=st.session_state.get("project_title", ""), 
                                 placeholder="Project name")
    with save_col2:
        if st.button("💾 Save", use_container_width=True):
            if save_name.strip():
                project_id = save_current_project(save_name.strip())
                st.success(f"Saved: {save_name}")
                st.session_state["current_project_id"] = project_id
            else:
                st.warning("Please enter a project name")

    if st.button("Reset app session", use_container_width=True):
        # Clear everything (safe reset)
        for k in list(st.session_state.keys()):
            if k not in [PROJECTS_KEY, COMPARE_KEY]:  # Keep saved projects
                del st.session_state[k]
        do_rerun()

if not up_excel:
    st.title("MEC TOOL")
    st.info("Please upload **MEC TOOL.xlsx** file using the sidebar to start.")
    st.markdown("""
    ### File Requirements:
    - **File name**: MEC TOOL.xlsx
    - **Required sheets**: Data, U1, U2
    - **Format**: Each sheet should contain rate tables with columns like:
        - Discipline, Personnel, Category, Schedule
        - Unit Rate columns (MYR/USD)
        - Minimum/Maximum/Normalise rates
    
    ### Download Template:
    [Download Sample MEC TOOL.xlsx Template](https://docs.google.com/spreadsheets/d/your-template-link-here)
    """)
    st.stop()

# Read Excel file once
excel_bytes = up_excel.getvalue()

upload_fingerprint = _hash_bytes(excel_bytes)[:10]
prev_fp = st.session_state.get("_upload_fp")

if prev_fp and prev_fp != upload_fingerprint:
    # Uploaded new file → reset grid to avoid mixing old selections
    st.session_state.pop(GRID_KEY, None)
    st.session_state.pop("_last_df_out", None)
    st.session_state.pop("_last_totals", None)

st.session_state["_upload_fp"] = upload_fingerprint

try:
    data_tbl, u1_tbl, u2_tbl = _load_tables_from_excel(excel_bytes)
    
    # Check if sheets are empty
    if data_tbl.empty or u1_tbl.empty or u2_tbl.empty:
        st.error("One or more sheets in the Excel file are empty or couldn't be read.")
        st.info("Please ensure the Excel file contains Data, U1, and U2 sheets with data.")
        st.stop()
        
except Exception as e:
    st.error("Failed to read the Excel file. Please confirm it's a valid MEC TOOL.xlsx file.")
    st.exception(e)
    st.stop()

# "Working Page" is not used in Excel upload mode
working = pd.DataFrame()
base_rate_col = None

# Options
schedule_opts = []
if not data_tbl.empty and "schedule" in data_tbl.columns:
    s = get_col(data_tbl, "schedule").dropna().astype(str).str.strip()
    schedule_opts = sorted([v for v in s.unique().tolist() if v])

package_opts = [s for s, df in (("U1", u1_tbl), ("U2", u2_tbl)) if not df.empty] or ["U1", "U2"]
DISC_LIST = list(DISCIPLINE_ROW_COUNTS.keys())

personnel_union = []
for _, plist in DEFAULT_PERSONNEL.items():
    personnel_union.extend(plist)
PERSONNEL_LIST = sorted(pd.Series(personnel_union).dropna().astype(str).drop_duplicates().tolist())

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

    # Excel mode: no "working" fallback
    return 0.0


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
st.session_state.setdefault(COMPARE_KEY, [])

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

# ──────────────────────────────────────────────────────────────────────────────
# Calculations
# ──────────────────────────────────────────────────────────────────────────────
def compute_line_items(grid_df: pd.DataFrame, currency: str, rate_source: str, type_of_schedule: str) -> pd.DataFrame:
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
                f"Total Cost ({currency})",
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
    for col in ["Weightage (FTE)", "Duration (months)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    df["Rate Source"] = rate_source
    df[f"Unit Rate ({currency})"] = df.apply(rate_for, axis=1).astype("float32")
    df["Total Hours"] = (
        df["Weightage (FTE)"].astype("float32") * float(HOURS_PER_MONTH) * df["Duration (months)"].astype("float32")
    )
    df[f"Total Cost ({currency})"] = (df[f"Unit Rate ({currency})"] * df["Total Hours"]).astype("float32")

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
            f"Total Cost ({currency})",
        ]
    ]


def compute_totals(df_out: pd.DataFrame, currency: str):
    total_manhour = float(df_out["Total Hours"].sum()) if not df_out.empty else 0.0
    rates_nonzero = (
        df_out[f"Unit Rate ({currency})"].replace(0, pd.NA).dropna() if not df_out.empty else pd.Series(dtype=float)
    )
    avg_rate = float(rates_nonzero.mean()) if not rates_nonzero.empty else 0.0
    total_by_average = avg_rate * total_manhour
    total_exact = float(df_out[f"Total Cost ({currency})"].sum()) if not df_out.empty else 0.0

    if df_out.empty:
        totals = pd.DataFrame(columns=["Discipline", "Manhour", f"Total Price ({currency})"])
    else:
        totals = df_out.groupby("Discipline", as_index=False).agg(
            Manhour=("Total Hours", "sum"),
            **{f"Total Price ({currency})": (f"Total Cost ({currency})", "sum")},
        )
    return total_manhour, avg_rate, total_by_average, total_exact, totals


# ──────────────────────────────────────────────────────────────────────────────
# Export to Excel (styled; 3 sheets)
# ──────────────────────────────────────────────────────────────────────────────
def to_excel_bytes(main_meta: pd.DataFrame, totals: pd.DataFrame, lines: pd.DataFrame, schedule_label: str, currency: str):
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
    ]
    r0 = 6
    for i, (lbl, val) in enumerate(fields):
        r = r0 + i
        ws[f"C{r}"].value = lbl
        ws[f"E{r}"].value = val
        ws[f"C{r}"].font = Font(bold=True)
        paint_range(
            ws,
            f"E{r}:I{r}",
            fill=PatternFill("solid", fgColor=LIGHT),
            border=Border(left=THIN, right=THIN, top=THIN, bottom=THIN),
        )

    notes = r0 + len(fields) + 3
    ws[f"C{notes}"].value = "Notes:"
    ws[f"C{notes}"].font = Font(bold=True)
    ws[f"C{notes+2}"].value = "Type of Package"
    ws[f"C{notes+3}"].value = "Package U1"
    ws[f"E{notes+3}"].value = "Feasibility Study & Conceptual Engineering for Upstream"
    ws[f"C{notes+4}"].value = "Package U2"
    ws[f"E{notes+4}"].value = "FEED & Detailed Design for Upstream"
    ws[f"C{notes+6}"].value = "Type of Schedule"
    ws[f"F{notes+6}"].value = "Currency"
    for i, (tag, desc, cur) in enumerate(
        [
            ("Schedule A", "Malaysia Project (Malaysia Base)", "MYR"),
            ("Schedule B", "Malaysia Project (International Base)", "USD"),
            ("Schedule C", "International Project (Malaysia Base)", "MYR"),
            ("Schedule D", "International Project (International Base)", "USD"),
        ]
    ):
        rr = notes + 7 + i
        ws[f"C{rr}"].value = tag
        ws[f"D{rr}"].value = desc
        ws[f"F{rr}"].value = cur

    set_col_w(ws, {"B": 2, "C": 22, "D": 40, "E": 36, "F": 12, "G": 10, "H": 10, "I": 6})
    ws.freeze_panes = "B6"

    # Working Page (export)
    ws2 = wb.create_sheet("Working Page")
    unit_rate_col = next((c for c in lines.columns if c.startswith("Unit Rate (")), f"Unit Rate ({currency})")
    total_cost_col = next((c for c in lines.columns if c.startswith("Total Cost (")), f"Total Cost ({currency})")

    work = lines[
        [
            "Discipline",
            "Personnel",
            "Category",
            "Type of Unit Rate",
            "Rate Source",
            unit_rate_col,
            "Weightage (FTE)",
            "Duration (months)",
            "Total Hours",
            total_cost_col,
        ]
    ].copy()
    NOTES_COL = "Notes"
    work[NOTES_COL] = ""

    ws2.merge_cells("B2:U3")
    ws2["B2"].value = "ENGINEERING STUDIES"
    paint_range(
        ws2,
        "B2:U3",
        fill=PatternFill("solid", fgColor=BRAND_HEX),
        font=Font(color="FFFFFF", bold=True, size=12),
        align=Alignment(horizontal="center", vertical="center"),
    )

    headers = list(work.columns)
    start_row = 5
    for j, h in enumerate(headers, start=2):
        c = ws2.cell(row=start_row, column=j, value=h)
        c.fill = PatternFill("solid", fgColor="E6F9F7")
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")
        c.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    def set_col_w2(ws, widths):
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

    set_col_w2(ws2, {"B": 16, "C": 30, "D": 18, "E": 18, "F": 14, "U": 22})
    ws2.freeze_panes = "B6"

    cur_r = start_row + 1

    def write_row(vals, row_disc: str, is_subtotal=False):
        nonlocal cur_r
        for j, v in enumerate(vals, start=2):
            cell = ws2.cell(row=cur_r, column=j, value=v)
            if not is_subtotal:
                tint = DISCIPLINE_COLORS.get(row_disc, None)
                if tint:
                    cell.fill = PatternFill("solid", fgColor=tint)
                cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
            else:
                cell.border = Border(left=THIN, right=THIN, top=MED, bottom=THIN)
                cell.font = Font(bold=True)
            if headers[j - 2] == NOTES_COL:
                cell.alignment = Alignment(horizontal="center")
            header = headers[j - 2]
            if isinstance(v, (int, float)):
                if "Rate" in header or "Cost" in header:
                    cell.number_format = f'"{currency}" #,##0.00'
                elif "Hours" in header:
                    cell.number_format = "#,##0.00"
                elif "Weightage" in header:
                    cell.number_format = "0.0"
                elif "Duration" in header:
                    cell.number_format = "0"
        cur_r += 1

    for disc, group in work.groupby("Discipline", sort=False):
        for _, row in group.iterrows():
            write_row([row[h] for h in headers], row_disc=disc, is_subtotal=False)
        sub = {h: "" for h in headers}
        sub["Discipline"] = disc
        sub[NOTES_COL] = "TOTAL PER DISCIPLINE"
        sub["Total Hours"] = float(group["Total Hours"].fillna(0).sum())
        sub[total_cost_col] = float(group[total_cost_col].fillna(0).sum())
        write_row([sub[h] for h in headers], row_disc=disc, is_subtotal=True)

    last_col = get_column_letter(1 + len(headers))
    ws2.auto_filter.ref = f"B{start_row}:{last_col}{cur_r-1}"

    # Summary
    ws3 = wb.create_sheet("Summary")
    ws3.merge_cells("C3:H4")
    ws3["C3"].value = f"TYPE OF SCHEDULE — {schedule_label}"
    paint_range(
        ws3,
        "C3:H4",
        fill=PatternFill("solid", fgColor=BRAND_HEX),
        font=Font(color="FFFFFF", bold=True, size=12),
        align=Alignment(horizontal="center", vertical="center"),
    )

    hdr_row = 6
    for i, h in enumerate(["No.", "Description", "Manhour", f"Total Price ({currency})"], start=3):
        c = ws3.cell(row=hdr_row, column=i, value=h)
        c.fill = PatternFill("solid", fgColor="E6F9F7")
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")
        c.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    ws3.merge_cells(f"C{hdr_row-1}:F{hdr_row-1}")
    ws3[f"C{hdr_row-1}"].value = "BASE SCOPE"
    ws3[f"C{hdr_row-1}"].font = Font(bold=True, color="155E59")

    r = hdr_row + 1
    if not totals.empty:
        t = totals.copy()
        t.insert(0, "No.", range(1, len(t) + 1))
        t = t.rename(columns={"Discipline": "Description"})
        for _, row in t.iterrows():
            ws3.cell(row=r, column=3, value=row["No."]).border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
            ws3.cell(row=r, column=4, value=row["Description"]).border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
            mh = ws3.cell(row=r, column=5, value=float(row["Manhour"]))
            tp = ws3.cell(row=r, column=6, value=float(row[f"Total Price ({currency})"]))
            mh.number_format = "#,##0"
            tp.number_format = f'"{currency}" #,##0.00'
            mh.border = tp.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
            r += 1

    ws3.merge_cells(f"C{r+2}:E{r+2}")
    ws3[f"C{r+2}"].value = "Total Raw Bid Price"
    ws3[f"C{r+2}"].font = Font(bold=True, color="FFFFFF")
    ws3[f"C{r+2}"].fill = PatternFill("solid", fgColor=BRAND_HEX)
    ws3[f"C{r+2}"].alignment = Alignment(horizontal="right", vertical="center")

    total_val = float(totals[f"Total Price ({currency})"].sum()) if not totals.empty else 0.0
    tc = ws3[f"F{r+2}"]
    tc.value = total_val
    tc.number_format = f'"{currency}" #,##0.00'
    tc.fill = PatternFill("solid", fgColor=BRAND_HEX)
    tc.font = Font(bold=True, color="FFFFFF")
    tc.alignment = Alignment(horizontal="center")

    ws3.freeze_panes = "C7"

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Navigation helpers
# ──────────────────────────────────────────────────────────────────────────────
def stepper(active: str):
    st.markdown(
        f"""
    <style>
      .mec-steps {{ margin: 8px 0 12px; }}
      .mec-step {{
        display:inline-block; padding:6px 10px; margin-right:6px;
        border-radius:10px; background:#E5E7EB; color:#111827; font-weight:600; font-size:13px;
      }}
      .mec-step.active {{ background: var(--brand1); color:#fff; }}
    </style>
    """,
        unsafe_allow_html=True,
    )
    steps = [("MAIN", "Main Page"), ("TABLE", "Personnel Table"), ("TOTALS", "Totals & Line Items"), 
             ("SUMMARY", "Summary & Download"), ("COMPARE", "Compare Projects")]
    html = '<div class="mec-steps">'
    for key, label in steps:
        cls = "mec-step active" if key == active else "mec-step"
        html += f"<span class='{cls}'>{label}</span>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


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
# COMPARE PROJECTS PAGE
# ──────────────────────────────────────────────────────────────────────────────
def render_compare():
    stepper("COMPARE")
    st.header("📊 Project Comparison")
    
    # Get saved projects
    projects_df = get_project_summary_df()
    
    if projects_df.empty:
        st.info("No saved projects found. Save your current project from the Main Page or Summary Page to enable comparison.")
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("⬅️ Back to Main Page", use_container_width=True):
            st.session_state["page"] = "MAIN"
            do_rerun()
        return
    
    st.subheader("Saved Projects")
    
    # Display saved projects with checkboxes for comparison
    col1, col2 = st.columns([3, 1])
    with col1:
        st.dataframe(
            projects_df.drop(columns=["ID"]),
            use_container_width=True,
            column_config={
                "Total Manhour": st.column_config.NumberColumn(format="%.0f"),
                "Avg Rate": st.column_config.NumberColumn(format="%.2f"),
                "Total Cost": st.column_config.NumberColumn(format="%.0f"),
            }
        )
    
    with col2:
        st.markdown("### Compare Selection")
        # Checkboxes for project selection
        for _, row in projects_df.iterrows():
            is_selected = st.checkbox(
                f"{row['Project Name']} ({row['Currency']})",
                value=row['ID'] in st.session_state[COMPARE_KEY],
                key=f"compare_{row['ID']}"
            )
            if is_selected and row['ID'] not in st.session_state[COMPARE_KEY]:
                st.session_state[COMPARE_KEY].append(row['ID'])
            elif not is_selected and row['ID'] in st.session_state[COMPARE_KEY]:
                st.session_state[COMPARE_KEY].remove(row['ID'])
        
        # Clear selection button
        if st.button("Clear Selection", use_container_width=True):
            st.session_state[COMPARE_KEY] = []
            do_rerun()
        
        # Load selected project button
        if st.session_state[COMPARE_KEY]:
            selected_id = st.selectbox(
                "Load project to edit:",
                options=st.session_state[COMPARE_KEY],
                format_func=lambda x: st.session_state[PROJECTS_KEY][x]["name"]
            )
            if st.button("📂 Load Selected", use_container_width=True):
                if load_project(selected_id):
                    st.success(f"Loaded: {st.session_state[PROJECTS_KEY][selected_id]['name']}")
                    st.session_state["page"] = "MAIN"
                    do_rerun()
    
    # Comparison analysis (only if at least 2 projects selected)
    if len(st.session_state[COMPARE_KEY]) >= 2:
        st.markdown("---")
        st.subheader("📈 Comparison Analysis")
        
        # Get selected projects data
        selected_projects = []
        for project_id in st.session_state[COMPARE_KEY]:
            if project_id in st.session_state.get(PROJECTS_KEY, {}):
                selected_projects.append(st.session_state[PROJECTS_KEY][project_id])
        
        if len(selected_projects) >= 2:
            # 1. High-level metrics comparison
            st.markdown("#### Key Metrics Comparison")
            
            metrics_data = []
            for project in selected_projects:
                metrics_data.append({
                    "Project": project["name"],
                    "Currency": project.get("currency", "N/A"),
                    "Total Manhour": project.get("total_manhour", 0),
                    "Avg Rate": project.get("avg_rate", 0),
                    "Total Cost": project.get("total_exact", 0),
                    "Cost per Manhour": project.get("total_exact", 0) / project.get("total_manhour", 1) if project.get("total_manhour", 0) > 0 else 0
                })
            
            metrics_df = pd.DataFrame(metrics_data)
            
            # Display metrics in columns
            cols = st.columns(len(selected_projects))
            for idx, (col, project) in enumerate(zip(cols, selected_projects)):
                with col:
                    st.markdown(f'<div class="project-card">', unsafe_allow_html=True)
                    st.markdown(f"**{project['name']}**")
                    st.markdown(f"*{project['metadata']['type_of_schedule']}*")
                    st.metric("Total Cost", f"{project.get('total_exact', 0):,.0f} {project.get('currency', '')}")
                    st.metric("Manhours", f"{project.get('total_manhour', 0):,.0f}")
                    st.metric("Avg Rate", f"{project.get('avg_rate', 0):,.2f} {project.get('currency', '')}")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # 2. Visual Comparison Charts
            st.markdown("#### Visual Comparison")
            
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Cost Comparison", "⏱️ Manhour Comparison", "💰 Rate Analysis", "📋 Detailed View"])
            
            with tab1:
                # Bar chart for total costs
                fig_cost = go.Figure(data=[
                    go.Bar(
                        name='Total Cost',
                        x=metrics_df['Project'],
                        y=metrics_df['Total Cost'],
                        text=[f"{v:,.0f} {c}" for v, c in zip(metrics_df['Total Cost'], metrics_df['Currency'])],
                        textposition='auto',
                        marker_color=BRAND1
                    )
                ])
                fig_cost.update_layout(
                    title='Total Cost Comparison',
                    xaxis_title='Project',
                    yaxis_title='Total Cost',
                    showlegend=False,
                    template='plotly_white'
                )
                st.plotly_chart(fig_cost, use_container_width=True)
            
            with tab2:
                # Bar chart for manhours
                fig_mh = go.Figure(data=[
                    go.Bar(
                        name='Total Manhour',
                        x=metrics_df['Project'],
                        y=metrics_df['Total Manhour'],
                        text=[f"{v:,.0f}" for v in metrics_df['Total Manhour']],
                        textposition='auto',
                        marker_color=BRAND2
                    )
                ])
                fig_mh.update_layout(
                    title='Total Manhour Comparison',
                    xaxis_title='Project',
                    yaxis_title='Total Manhour',
                    showlegend=False,
                    template='plotly_white'
                )
                st.plotly_chart(fig_mh, use_container_width=True)
            
            with tab3:
                # Scatter plot: Cost vs Manhour
                fig_scatter = go.Figure()
                for idx, row in metrics_df.iterrows():
                    fig_scatter.add_trace(go.Scatter(
                        x=[row['Total Manhour']],
                        y=[row['Total Cost']],
                        mode='markers+text',
                        name=row['Project'],
                        text=[row['Project']],
                        textposition="top center",
                        marker=dict(size=15, color=BRAND1),
                        hovertemplate=f"Project: {row['Project']}<br>"
                                    f"Manhour: {row['Total Manhour']:,.0f}<br>"
                                    f"Cost: {row['Total Cost']:,.0f} {row['Currency']}<br>"
                                    f"Cost/Manhour: {row['Cost per Manhour']:,.2f}"
                    ))
                
                fig_scatter.update_layout(
                    title='Cost vs Manhour (Bubble Size = Avg Rate)',
                    xaxis_title='Total Manhour',
                    yaxis_title=f'Total Cost',
                    template='plotly_white',
                    showlegend=True
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            
            with tab4:
                # Detailed comparison table
                st.dataframe(
                    metrics_df,
                    use_container_width=True,
                    column_config={
                        "Project": st.column_config.TextColumn(width="medium"),
                        "Currency": st.column_config.TextColumn(width="small"),
                        "Total Manhour": st.column_config.NumberColumn(format="%.0f"),
                        "Avg Rate": st.column_config.NumberColumn(format="%.2f"),
                        "Total Cost": st.column_config.NumberColumn(format="%.0f"),
                        "Cost per Manhour": st.column_config.NumberColumn(format="%.2f"),
                    }
                )
            
            # 3. Rate Comparison by Discipline (if available)
            st.markdown("#### Rate Comparison by Discipline")
            
            # Collect discipline-level data
            discipline_data = []
            for project in selected_projects:
                if project.get("line_items"):
                    df_items = pd.DataFrame(project["line_items"])
                    # Get unique unit rate column name
                    rate_col = next((c for c in df_items.columns if "Unit Rate" in c), None)
                    if rate_col:
                        for disc in df_items["Discipline"].unique():
                            disc_rates = df_items[df_items["Discipline"] == disc][rate_col]
                            if not disc_rates.empty:
                                discipline_data.append({
                                    "Project": project["name"],
                                    "Discipline": disc,
                                    "Avg Rate": disc_rates.mean(),
                                    "Currency": project.get("currency", "")
                                })
            
            if discipline_data:
                disc_df = pd.DataFrame(discipline_data)
                
                # Pivot for heatmap
                pivot_df = disc_df.pivot(index="Discipline", columns="Project", values="Avg Rate")
                
                # Create heatmap
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=pivot_df.values,
                    x=pivot_df.columns,
                    y=pivot_df.index,
                    colorscale='Viridis',
                    text=[[f"{v:,.0f}" for v in row] for row in pivot_df.values],
                    texttemplate="%{text}",
                    textfont={"size": 10}
                ))
                
                fig_heatmap.update_layout(
                    title='Average Rate by Discipline (Heatmap)',
                    xaxis_title='Project',
                    yaxis_title='Discipline',
                    height=max(400, len(pivot_df) * 30)
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # Bar chart comparison for each discipline
                selected_discipline = st.selectbox(
                    "Select Discipline for detailed rate comparison:",
                    options=sorted(disc_df["Discipline"].unique())
                )
                
                if selected_discipline:
                    disc_comparison = disc_df[disc_df["Discipline"] == selected_discipline]
                    fig_disc = go.Figure(data=[
                        go.Bar(
                            x=disc_comparison["Project"],
                            y=disc_comparison["Avg Rate"],
                            text=[f"{v:,.0f} {c}" for v, c in zip(disc_comparison["Avg Rate"], disc_comparison["Currency"])],
                            textposition='auto',
                            marker_color=BRAND1
                        )
                    ])
                    fig_disc.update_layout(
                        title=f'Average Rate for {selected_discipline}',
                        xaxis_title='Project',
                        yaxis_title='Average Rate',
                        showlegend=False
                    )
                    st.plotly_chart(fig_disc, use_container_width=True)
            
            # 4. Export comparison report
            st.markdown("#### Export Comparison Report")
            
            # Create comparison summary
            comparison_summary = {
                "comparison_date": datetime.now().isoformat(),
                "projects_compared": [p["name"] for p in selected_projects],
                "metrics_comparison": metrics_data,
                "notes": "Generated by MEC TOOL Project Comparison"
            }
            
            # Export options
            col1, col2 = st.columns(2)
            with col1:
                # JSON export
                json_str = json.dumps(comparison_summary, indent=2)
                st.download_button(
                    label="📥 Download JSON Report",
                    data=json_str,
                    file_name="project_comparison.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col2:
                # CSV export of metrics
                csv_data = metrics_df.to_csv(index=False)
                st.download_button(
                    label="📊 Download CSV Metrics",
                    data=csv_data,
                    file_name="project_metrics.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    elif len(st.session_state[COMPARE_KEY]) == 1:
        st.info("Select at least 2 projects for comparison.")
    
    # Project management
    st.markdown("---")
    st.subheader("Project Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Delete All Projects", use_container_width=True):
            st.session_state[PROJECTS_KEY] = {}
            st.session_state[COMPARE_KEY] = []
            st.success("All projects deleted!")
            do_rerun()
    
    with col2:
        if st.button("⬅️ Back to Summary", use_container_width=True):
            st.session_state["page"] = "SUMMARY"
            do_rerun()
    
    with col3:
        if st.button("🏠 Back to Main", use_container_width=True):
            st.session_state["page"] = "MAIN"
            do_rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Page renderers (MAIN, TABLE, TOTALS, SUMMARY)
# ──────────────────────────────────────────────────────────────────────────────
def render_main():
    stepper("MAIN")
    st.markdown("# MEC TOOL", unsafe_allow_html=True)
    st.caption("Input mode: Excel upload (MEC TOOL.xlsx with Data, U1, U2 sheets)")

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.header("Main Page")

    mp1, mp2 = st.columns(2)
    with mp1:
        st.session_state["project_title"] = st.text_input(
            "Project Title",
            value=st.session_state["project_title"],
            placeholder="e.g., PROJECT A",
        )
        st.session_state["cost_engineer"] = st.text_input(
            "Cost Engineer", value=st.session_state["cost_engineer"], placeholder="Your name"
        )
        st.session_state["tp_specialist"] = st.text_input(
            "TP/Specialist", value=st.session_state["tp_specialist"], placeholder="TP in charge"
        )

    with mp2:
        st.session_state["project_date"] = st.date_input("Date", value=st.session_state["project_date"])
        st.session_state["type_of_package"] = st.selectbox(
            "Type of Package",
            package_opts,
            index=max(
                0,
                package_opts.index(st.session_state["type_of_package"])
                if st.session_state["type_of_package"] in package_opts
                else 0,
            ),
        )
        st.session_state["type_of_schedule"] = st.selectbox(
            "Type of Schedule (from Data sheet)",
            schedule_opts if schedule_opts else ["Schedule A", "Schedule B", "Schedule C", "Schedule D"],
            index=0
            if not schedule_opts
            else max(
                0,
                schedule_opts.index(st.session_state["type_of_schedule"])
                if st.session_state["type_of_schedule"] in schedule_opts
                else 0,
            ),
        )

    rs1, rs2 = st.columns([1, 2])
    with rs1:
        package_to_rate = {"U1": "U1", "U2": "U2"}
        default_rate = package_to_rate.get(st.session_state["type_of_package"], "Data")
        st.session_state["rate_source"] = st.radio(
            "Rate Source", RATE_SOURCES, index=RATE_SOURCES.index(default_rate), horizontal=True
        )
    with rs2:
        st.metric("Hours per Month (constant)", f"{HOURS_PER_MONTH:,.0f} hrs")
        st.caption("Hours = Weightage × 176 × Duration (months)")

    st.markdown("<br/>", unsafe_allow_html=True)
    
    # Show saved projects count
    if PROJECTS_KEY in st.session_state and st.session_state[PROJECTS_KEY]:
        st.info(f"📁 You have {len(st.session_state[PROJECTS_KEY])} saved project(s). Go to Compare Projects page to analyze them.")
    
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("➡️ Go to Personnel Table", use_container_width=True):
            st.session_state["page"] = "TABLE"
            do_rerun()
    with c2:
        if st.button("↺ Reset Grid to Defaults", use_container_width=True):
            reset_grid()
            do_rerun()
    with c3:
        if st.button("📊 Compare Projects", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            do_rerun()


def render_table():
    stepper("TABLE")
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
    c1, c2 = st.columns([1, 1])
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

    # ── AG Grid ────────────────────────────────────────────────────────────────
    df = st.session_state[GRID_KEY].copy()

    categoricals = ["Discipline", "Personnel", "Category", "Type of Unit Rate"]
    for col in categoricals:
        if col in df.columns:
            df[col] = df[col].astype("category")
    for col in ["Weightage (FTE)", "Duration (months)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

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
    gb.configure_column(
        "Type of Unit Rate",
        width=220,
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": UNIT_TYPES},
    )
    gb.configure_column("Weightage (FTE)", type=["numericColumn"], width=170, editable=True)
    gb.configure_column("Duration (months)", type=["numericColumn"], width=170, editable=True)

    disc_bg = {k: f"#{v}" for k, v in DISCIPLINE_COLORS.items()}
    row_style_js = JsCode(
        """
function(params) {
  const map = %s;
  const disc = (params && params.data && params.data.Discipline) ? params.data.Discipline : "";
  const bg = map[disc] || null;
  return bg ? { backgroundColor: bg } : null;
}
"""
        % json.dumps(disc_bg)
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

    st.markdown(" ")
    col_db1, col_db2 = st.columns([1, 1])
    with col_db1:
        auto_recalc = st.toggle("Auto-recalculate totals", value=True, help="Turn off for faster editing on large tables.")
    with col_db2:
        recalc_clicked = st.button("Recalculate now", use_container_width=True)
    should_recalc = auto_recalc or recalc_clicked

    try:
        grid_resp = AgGrid(df, update_on="value_changed", **aggrid_common)
    except TypeError:
        grid_resp = AgGrid(df, update_mode=GridUpdateMode.VALUE_CHANGED, **aggrid_common)

    df_current = pd.DataFrame(grid_resp["data"])
    st.session_state[GRID_KEY] = df_current

    if should_recalc:
        df_out = compute_line_items(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
        total_manhour, avg_rate, total_by_average, total_exact, totals = compute_totals(df_out, currency)
        st.session_state["_last_df_out"] = df_out
        st.session_state["_last_totals"] = totals
    else:
        df_out = st.session_state.get("_last_df_out", pd.DataFrame())
        totals = st.session_state.get("_last_totals", pd.DataFrame())
        total_manhour = df_out.get("Total Hours", pd.Series(dtype=float)).sum() if not df_out.empty else 0.0
        avg_rate = 0.0
        total_by_average = 0.0
        total_exact = 0.0

    st.header("Results")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Manhour", f"{total_manhour:,.0f}")
    c2.metric("Avg Unit Rate", f"{avg_rate:,.2f} {currency}")
    c3.metric("Method A — Avg × MH", f"{total_by_average:,.2f} {currency}")
    c4.metric("Method B — Exact", f"{total_exact:,.2f} {currency}")
    st.caption("Method A: average of non-zero unit rates × total manhour. Method B: exact sum of line items.")

    st.markdown("<br/>", unsafe_allow_html=True)
    c3, c4 = st.columns([1, 1])
    with c3:
        if st.button("⬅️ Back to Main", use_container_width=True):
            st.session_state["page"] = "MAIN"
            do_rerun()
    with c4:
        if st.button("➡️ Go to Totals & Line Items", use_container_width=True):
            st.session_state["page"] = "TOTALS"
            do_rerun()


def render_totals():
    stepper("TOTALS")
    type_of_schedule = st.session_state["type_of_schedule"]
    rate_source = st.session_state["rate_source"]
    currency = currency_for(type_of_schedule)

    df_out = compute_line_items(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
    _, _, _, _, totals = compute_totals(df_out, currency)

    st.subheader("Totals by Discipline")
    st.dataframe(
        totals,
        use_container_width=True,
        column_config={
            "Manhour": st.column_config.NumberColumn("Manhour", format="%.0f"),
            f"Total Price ({currency})": st.column_config.NumberColumn(f"Total Price ({currency})", format=f"{currency} %.2f"),
        },
    )

    st.subheader("Line Items")
    st.dataframe(
        df_out,
        use_container_width=True,
        column_config={
            f"Unit Rate ({currency})": st.column_config.NumberColumn(f"Unit Rate ({currency})", format=f"{currency} %.2f"),
            "Total Hours": st.column_config.NumberColumn("Total Hours", format="%.2f"),
            f"Total Cost ({currency})": st.column_config.NumberColumn(f"Total Cost ({currency})", format=f"{currency} %.2f"),
        },
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("⬅️ Back to Personnel Table", use_container_width=True):
            st.session_state["page"] = "TABLE"
            do_rerun()
    with c2:
        if st.button("➡️ Go to Summary & Download", use_container_width=True):
            st.session_state["page"] = "SUMMARY"
            do_rerun()


def render_summary():
    stepper("SUMMARY")
    type_of_schedule = st.session_state["type_of_schedule"]
    rate_source = st.session_state["rate_source"]
    currency = currency_for(type_of_schedule)

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
                "Hours per Month (constant)": HOURS_PER_MONTH,
            }
        ]
    )

    df_out = compute_line_items(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
    _, _, _, _, totals = compute_totals(df_out, currency)

    st.subheader("Main Page (entered)")
    st.dataframe(main_meta, use_container_width=True)

    # Save project button in summary
    st.markdown("---")
    col_save1, col_save2, col_save3 = st.columns([2, 1, 1])
    with col_save1:
        save_name = st.text_input(
            "Save this project as:", 
            value=st.session_state.get("project_title", ""),
            placeholder="Enter project name"
        )
    with col_save2:
        if st.button("💾 Save Project", use_container_width=True):
            if save_name.strip():
                project_id = save_current_project(save_name.strip())
                st.success(f"Project '{save_name}' saved!")
                st.session_state["current_project_id"] = project_id
            else:
                st.warning("Please enter a project name")
    with col_save3:
        if st.button("📊 Compare Projects", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            do_rerun()

    # Visuals
    if not df_out.empty:
        discipline_color_map = {d: f"#{DISCIPLINE_COLORS.get(d, 'D1D5DB')}" for d in df_out["Discipline"].unique()}

        st.subheader("Visual Summary")

        totals_disp = (
            df_out.groupby("Discipline", as_index=False)[f"Total Cost ({currency})"]
            .sum()
            .sort_values(by=f"Total Cost ({currency})", ascending=False)
        )
        totals_disp[f"Total Cost ({currency})"] = totals_disp[f"Total Cost ({currency})"].round(2)

        fig_bar = px.bar(
            totals_disp,
            x=f"Total Cost ({currency})",
            y="Discipline",
            orientation="h",
            color="Discipline",
            color_discrete_map=discipline_color_map,
            hover_data=None,
            title=f"Total Price by Discipline ({currency})",
        )
        fig_bar.update_layout(
            title_x=0.0,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=13),
            margin=dict(l=10, r=10, t=48, b=10),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        cat_disp = (
            df_out.groupby("Category", as_index=False)[f"Total Cost ({currency})"]
            .sum()
            .sort_values(by=f"Total Cost ({currency})", ascending=False)
        )
        if not cat_disp.empty:
            brand_seq = [BRAND1, BRAND2, "#14B8A6", "#60A5FA", "#A78BFA", "#F59E0B", "#EF4444"]
            fig_donut = px.pie(
                cat_disp,
                values=f"Total Cost ({currency})",
                names="Category",
                hole=0.45,
                color="Category",
                color_discrete_sequence=brand_seq,
                title=f"Cost Share by Category ({currency})",
            )
            fig_donut.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="%{label}<br>%{value:,.2f}",
            )
            fig_donut.update_layout(
                title_x=0.0,
                showlegend=True,
                legend_title_text="Category",
                margin=dict(l=10, r=10, t=48, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        st.caption("Tips: Use the Personnel Table to adjust Weightage/Duration and see instant visual updates here.")

    # Download output Excel
    excel_blob = to_excel_bytes(main_meta, totals, df_out, schedule_label=type_of_schedule, currency=currency)
    st.download_button(
        "⬇️ Download Summary (Excel)",
        data=excel_blob,
        file_name="MEC_TOOL_Output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        help="Main Page, Working Page (tinted & subtotals), and Summary — styled & currency-aware",
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("⬅️ Back to Totals", use_container_width=True):
            st.session_state["page"] = "TOTALS"
            do_rerun()
    with c2:
        if st.button("🏠 Back to Main Page", use_container_width=True):
            st.session_state["page"] = "MAIN"
            do_rerun()
    with c3:
        if st.button("📊 Compare Projects", use_container_width=True):
            st.session_state["page"] = "COMPARE"
            do_rerun()


# ──────────────────────────────────────────────────────────────────────────────
# TOP HERO + ROUTER
# ──────────────────────────────────────────────────────────────────────────────
page = st.session_state["page"]
if page == "MAIN":
    render_main()
elif page == "TABLE":
    render_table()
elif page == "TOTALS":
    render_totals()
elif page == "SUMMARY":
    render_summary()
elif page == "COMPARE":
    render_compare()
else:
    st.session_state["page"] = "MAIN"
    do_rerun()
