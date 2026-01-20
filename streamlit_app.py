# streamlit_app.py
# MEC TOOL – Streamlit app (UI polished, performance improved)
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

# Silence harmless openpyxl validation warning
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
SAVED_PROJECTS_KEY = "saved_projects"

# ──────────────────────────────────────────────────────────────────────────────
# Navigation Pages
# ──────────────────────────────────────────────────────────────────────────────
PAGES = {
    "MAIN": "🏠 Main Page",
    "TABLE": "👥 Personnel Table", 
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


def _find_header_row(raw: pd.DataFrame, max_scan: int = 80) -> Optional[int]:
    for r in range(min(max_scan, len(raw))):
        row = [_canon(v) for v in list(raw.iloc[r, :].values)]
        hits = 0
        for key in ["discipline", "personnel", "category", "schedule", "type of unit", "unit rate", "unit rate (myr)"]:
            if any(key in v for v in row):
                hits += 1
        if hits >= 3:
            return r
    return None


def _read_sheet_smart(xl: pd.ExcelFile, sheet_names: List[str]) -> pd.DataFrame:
    for name in sheet_names:
        try:
            raw = xl.parse(name, header=None)
        except Exception:
            continue
        hdr = _find_header_row(raw)
        if hdr is None:
            continue
        df = raw.iloc[hdr + 1 :].copy()
        df.columns = [raw.iloc[hdr, i] if i < raw.shape[1] else f"col_{i}" for i in range(df.shape[1])]
        df = df.loc[:, ~pd.Index(df.columns.astype(str)).str.contains("^Unnamed", case=False, na=False)]
        df = _normalize_cols(df).dropna(how="all")
        return df
    return pd.DataFrame()


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


def _base_working_rate_col(working: pd.DataFrame) -> Optional[str]:
    for c in working.columns:
        k = _canon(c)
        if "unit rate" in k and ("myr" in k or "usd" in k or k == "unit rate" or "normalise rate" in k):
            return c
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Load workbook (bytes)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=600)  # cache for 10 minutes
def load_workbook(file_bytes: bytes, file_label: str):
    bio = io.BytesIO(file_bytes)
    xl = pd.ExcelFile(bio, engine="openpyxl")

    working = _read_sheet_smart(xl, ["Working Page", "TblWorkingView"])
    data_tbl = _read_sheet_smart(xl, ["Data"])
    u1_tbl = _read_sheet_smart(xl, ["U1"])
    u2_tbl = _read_sheet_smart(xl, ["U2"])

    base_rate_col = _base_working_rate_col(working)

    schedule_opts = []
    if not data_tbl.empty and "schedule" in data_tbl.columns:
        s = get_col(data_tbl, "schedule").dropna().astype(str).str.strip()
        schedule_opts = sorted([v for v in s.unique().tolist() if v])

    package_opts = [s for s, df in (("U1", u1_tbl), ("U2", u2_tbl)) if not df.empty] or ["U1", "U2"]

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
# HARD NO-UPLOAD MODE — load from local folder
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_HOST_DIR = r"C:\mec_inputs" if os.name == "nt" else os.path.join(os.getcwd(), "input")
SAFE_BASE_DIR = os.environ.get("MEC_ALLOWED_DIR", DEFAULT_HOST_DIR)
DEFAULT_FILE_ENV = os.environ.get("MEC_DEFAULT_FILE", "MEC TOOL.xlsx").strip()
os.makedirs(SAFE_BASE_DIR, exist_ok=True)


def _list_xlsx(base):
    try:
        return sorted(
            [f for f in os.listdir(base) if f.lower().endswith(".xlsx")],
            key=lambda n: os.path.getmtime(os.path.join(base, n)),
            reverse=True,
        )
    except Exception:
        return []


def _resolve_file():
    if DEFAULT_FILE_ENV and os.path.isabs(DEFAULT_FILE_ENV) and os.path.exists(DEFAULT_FILE_ENV):
        return DEFAULT_FILE_ENV
    if DEFAULT_FILE_ENV:
        candidate = os.path.join(SAFE_BASE_DIR, DEFAULT_FILE_ENV)
        if os.path.exists(candidate):
            return candidate
    file_list = _list_xlsx(SAFE_BASE_DIR)
    if file_list:
        return os.path.join(SAFE_BASE_DIR, file_list[0])
    raise FileNotFoundError(
        f"No .xlsx found. Put a workbook named '{DEFAULT_FILE_ENV}' into:\n {SAFE_BASE_DIR}"
    )


with st.sidebar:
    st.subheader("Workbook (local, no-upload)")
    st.caption(f"Folder: {SAFE_BASE_DIR}")
    if st.button("Reload file", use_container_width=True):
        st.session_state.pop("file_bytes", None)
        st.session_state.pop("file_label", None)
        do_rerun()
    st.markdown(
        """
Drop your MEC workbook in the folder above, then click Reload.
""",
        unsafe_allow_html=True,
    )

file_bytes = st.session_state.get("file_bytes")
file_label = st.session_state.get("file_label")
if not file_bytes:
    try:
        path = _resolve_file()
        with open(path, "rb") as f:
            file_bytes = f.read()
        file_label = os.path.basename(path)
        st.session_state["file_bytes"] = file_bytes
        st.session_state["file_label"] = file_label
        st.success(f"Loaded: {file_label}")
    except Exception as e:
        st.error(str(e))
        st.stop()

# Parse workbook from bytes
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
) = load_workbook(file_bytes, file_label)

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
    # downcast types to reduce payload
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
# Project Saving/Loading for Comparison
# ──────────────────────────────────────────────────────────────────────────────
def save_current_project():
    """Save current project configuration and results for later comparison"""
    type_of_schedule = st.session_state["type_of_schedule"]
    rate_source = st.session_state["rate_source"]
    currency = currency_for(type_of_schedule)
    
    df_out = compute_line_items(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
    total_manhour, avg_rate, total_by_average, total_exact, totals = compute_totals(df_out, currency)
    
    project_data = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "name": st.session_state["project_title"] or f"Project_{datetime.now().strftime('%Y%m%d_%H%M')}",
        "timestamp": datetime.now().isoformat(),
        "project_title": st.session_state["project_title"],
        "type_of_package": st.session_state["type_of_package"],
        "type_of_schedule": type_of_schedule,
        "rate_source": rate_source,
        "currency": currency,
        "total_manhour": total_manhour,
        "avg_rate": avg_rate,
        "total_by_average": total_by_average,
        "total_exact": total_exact,
        "totals": totals.to_dict('records'),
        "line_items": df_out.to_dict('records'),
        "personnel_count": len(st.session_state[GRID_KEY]),
        "disciplines_used": st.session_state[GRID_KEY]["Discipline"].nunique()
    }
    
    # Add to saved projects
    st.session_state[SAVED_PROJECTS_KEY].append(project_data)
    return project_data


def compare_projects(project1, project2):
    """Compare two projects and return comparison metrics"""
    comparison = {
        "manhour_diff": project2["total_manhour"] - project1["total_manhour"],
        "manhour_pct": ((project2["total_manhour"] - project1["total_manhour"]) / project1["total_manhour"] * 100) if project1["total_manhour"] > 0 else 0,
        "cost_diff": project2["total_exact"] - project1["total_exact"],
        "cost_pct": ((project2["total_exact"] - project1["total_exact"]) / project1["total_exact"] * 100) if project1["total_exact"] > 0 else 0,
        "avg_rate_diff": project2["avg_rate"] - project1["avg_rate"],
        "avg_rate_pct": ((project2["avg_rate"] - project1["avg_rate"]) / project1["avg_rate"] * 100) if project1["avg_rate"] > 0 else 0,
    }
    
    # Discipline-wise comparison
    df1 = pd.DataFrame(project1["totals"])
    df2 = pd.DataFrame(project2["totals"])
    
    # Merge for comparison
    if not df1.empty and not df2.empty:
        merged = pd.merge(
            df1[["Discipline", "Manhour", f"Total Price ({project1['currency']})"]],
            df2[["Discipline", "Manhour", f"Total Price ({project2['currency']})"]],
            on="Discipline",
            how="outer",
            suffixes=("_1", "_2")
        )
        merged = merged.fillna(0)
        
        # Calculate differences
        merged["Manhour_Diff"] = merged["Manhour_2"] - merged["Manhour_1"]
        merged["Cost_Diff"] = merged[f"Total Price ({project2['currency']})_2"] - merged[f"Total Price ({project1['currency']})_1"]
        
        comparison["discipline_comparison"] = merged.to_dict('records')
    else:
        comparison["discipline_comparison"] = []
    
    return comparison


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
        paint_range(ws, f"E{r}:I{r}", fill=PatternFill("solid", fgColor=LIGHT), border=Border(left=THIN, right=THIN, top=THIN, bottom=THIN))

    notes = r0 + len(fields) + 3
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

    # Working Page
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

    def set_col_w(ws, widths):
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

    set_col_w(ws2, {"B": 16, "C": 30, "D": 18, "E": 18, "F": 14, "U": 22})
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
                📍 Current: {PAGES[current_page].replace('🏠', '').replace('👥', '').replace('📊', '').replace('📈', '').replace('🔄', '').strip()}
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
    
    st.caption(f"📄 Workbook: {st.session_state.get('file_label','(loaded)')}")

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

    st.markdown("<br/>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("➡️ Go to Personnel Table", use_container_width=True, type="primary"):
            st.session_state["page"] = "TABLE"
            do_rerun()
    with c2:
        if st.button("↺ Reset Grid to Defaults", use_container_width=True):
            reset_grid()
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

    # Debounce computations for performance
    st.markdown(" ")
    col_db1, col_db2 = st.columns([1, 1])
    with col_db1:
        auto_recalc = st.toggle(
            "Auto‑recalculate totals",
            value=True,
            help="Turn off for faster editing on large tables.",
        )
    with col_db2:
        recalc_clicked = st.button("Recalculate now", use_container_width=True)
    should_recalc = auto_recalc or recalc_clicked

    try:
        grid_resp = AgGrid(df, update_on="value_changed", **aggrid_common)  # new API
    except TypeError:
        # Fallback to old API name
        grid_resp = AgGrid(df, update_mode=GridUpdateMode.VALUE_CHANGED, **aggrid_common)

    df_current = pd.DataFrame(grid_resp["data"])
    st.session_state[GRID_KEY] = df_current

    # Results at bottom
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
    
    # Improved metrics display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Total Manhour</h3>
                <div class="value">{total_manhour:,.0f}</div>
                <div class="subvalue">person-hours</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Average Unit Rate</h3>
                <div class="value">{avg_rate:,.2f}</div>
                <div class="subvalue">{currency}/hour</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Method A — Avg × MH</h3>
                <div class="value">{total_by_average:,.2f}</div>
                <div class="subvalue">{currency}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Method B — Exact</h3>
                <div class="value">{total_exact:,.2f}</div>
                <div class="subvalue">{currency}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.caption("Method A: average of non-zero unit rates × total manhour. Method B: exact sum of line items.")

    st.markdown("<br/>", unsafe_allow_html=True)
    c3, c4 = st.columns([1, 1])
    with c3:
        if st.button("💾 Save for Comparison", use_container_width=True):
            saved_project = save_current_project()
            st.success(f"Project '{saved_project['name']}' saved for comparison!")
            do_rerun()
    with c4:
        if st.button("➡️ Go to Totals & Line Items", use_container_width=True, type="primary"):
            st.session_state["page"] = "TOTALS"
            do_rerun()


def render_totals():
    type_of_schedule = st.session_state["type_of_schedule"]
    rate_source = st.session_state["rate_source"]
    currency = currency_for(type_of_schedule)

    df_out = compute_line_items(st.session_state[GRID_KEY], currency, rate_source, type_of_schedule)
    total_manhour, avg_rate, total_by_average, total_exact, totals = compute_totals(df_out, currency)

    # Summary metrics at top
    st.markdown(
        f"""
        <div class="summary-card">
            <h2 style="color: var(--brand1); margin-top: 0;">Project Summary</h2>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                <div>
                    <h3 style="color: var(--text-muted); margin-bottom: 0.5rem; font-size: 0.9rem;">Total Cost ({currency})</h3>
                    <div style="font-size: 2.2rem; font-weight: 700; color: var(--text);">{total_exact:,.2f}</div>
                </div>
                <div>
                    <h3 style="color: var(--text-muted); margin-bottom: 0.5rem; font-size: 0.9rem;">Total Manhours</h3>
                    <div style="font-size: 2.2rem; font-weight: 700; color: var(--text);">{total_manhour:,.0f}</div>
                </div>
                <div>
                    <h3 style="color: var(--text-muted); margin-bottom: 0.5rem; font-size: 0.9rem;">Average Rate</h3>
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--brand2);">{avg_rate:,.2f} {currency}/hour</div>
                </div>
                <div>
                    <h3 style="color: var(--text-muted); margin-bottom: 0.5rem; font-size: 0.9rem;">Disciplines</h3>
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--brand2);">{totals.shape[0]}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        if not totals.empty:
            # Bar chart for totals by discipline
            fig = px.bar(
                totals.sort_values(f"Total Price ({currency})", ascending=True),
                y="Discipline",
                x=f"Total Price ({currency})",
                orientation='h',
                color="Discipline",
                color_discrete_map={d: f"#{DISCIPLINE_COLORS.get(d, 'D1D5DB')}" for d in totals["Discipline"]},
                title=f"Cost by Discipline ({currency})",
                height=400
            )
            fig.update_layout(
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12),
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis=dict(
                    title=f"Total Price ({currency})",
                    tickformat=",.0f",
                    gridcolor='rgba(0,0,0,0.1)'
                ),
                yaxis=dict(
                    title=None,
                    categoryorder='total ascending'
                )
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if not totals.empty and totals.shape[0] > 1:
            # Donut chart for cost distribution
            fig = px.pie(
                totals,
                values=f"Total Price ({currency})",
                names="Discipline",
                hole=0.4,
                title="Cost Distribution by Discipline",
                height=400,
                color="Discipline",
                color_discrete_map={d: f"#{DISCIPLINE_COLORS.get(d, 'D1D5DB')}" for d in totals["Discipline"]}
            )
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate="<b>%{label}</b><br>%{value:,.0f} " + currency + "<br>%{percent}"
            )
            fig.update_layout(
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12),
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

    # Detailed totals table
    st.subheader("Totals by Discipline")
    
    if not totals.empty:
        # Format the totals for display
        display_totals = totals.copy()
        display_totals["Manhour"] = display_totals["Manhour"].apply(lambda x: f"{x:,.0f}")
        display_totals[f"Total Price ({currency})"] = display_totals[f"Total Price ({currency})"].apply(lambda x: f"{x:,.2f}")
        
        st.dataframe(
            display_totals,
            use_container_width=True,
            column_config={
                "Discipline": st.column_config.TextColumn("Discipline", width="medium"),
                "Manhour": st.column_config.TextColumn("Manhour", width="small"),
                f"Total Price ({currency})": st.column_config.TextColumn(f"Total Price ({currency})", width="medium"),
            },
            hide_index=True
        )
    
    # Line items table
    st.subheader("Line Items")
    
    if not df_out.empty:
        # Format line items for display
        display_line_items = df_out.copy()
        display_line_items[f"Unit Rate ({currency})"] = display_line_items[f"Unit Rate ({currency})"].apply(lambda x: f"{x:,.2f}")
        display_line_items["Total Hours"] = display_line_items["Total Hours"].apply(lambda x: f"{x:,.2f}")
        display_line_items[f"Total Cost ({currency})"] = display_line_items[f"Total Cost ({currency})"].apply(lambda x: f"{x:,.2f}")
        
        st.dataframe(
            display_line_items,
            use_container_width=True,
            column_config={
                "Discipline": st.column_config.TextColumn("Discipline", width="small"),
                "Personnel": st.column_config.TextColumn("Personnel", width="medium"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Type of Unit Rate": st.column_config.TextColumn("Rate Type", width="small"),
                "Rate Source": st.column_config.TextColumn("Source", width="small"),
                f"Unit Rate ({currency})": st.column_config.TextColumn(f"Rate ({currency})", width="small"),
                "Weightage (FTE)": st.column_config.NumberColumn("Weightage", format="%.1f", width="small"),
                "Duration (months)": st.column_config.NumberColumn("Duration", format="%d", width="small"),
                "Total Hours": st.column_config.TextColumn("Hours", width="small"),
                f"Total Cost ({currency})": st.column_config.TextColumn(f"Cost ({currency})", width="medium"),
            },
            hide_index=True
        )

    st.markdown("<br/>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("⬅️ Back to Personnel Table", use_container_width=True):
            st.session_state["page"] = "TABLE"
            do_rerun()
    with c2:
        if st.button("💾 Save for Comparison", use_container_width=True, type="primary"):
            saved_project = save_current_project()
            st.success(f"Project '{saved_project['name']}' saved for comparison!")
            do_rerun()
    with c3:
        if st.button("➡️ Go to Summary & Download", use_container_width=True):
            st.session_state["page"] = "SUMMARY"
            do_rerun()


def render_summary():
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

    # =========================
    # Visuals (colored)
    # =========================
    if not df_out.empty:
        # Build color map for disciplines from XLSX tint palette
        discipline_color_map = {d: f"#{DISCIPLINE_COLORS.get(d, 'D1D5DB')}" for d in df_out["Discipline"].unique()}

        st.subheader("Visual Summary")

        # Chart 1: Total Price by Discipline (Bar)
        totals_disp = (
            df_out.groupby("Discipline", as_index=False)[f"Total Cost ({currency})"]
            .sum()
            .sort_values(by=f"Total Cost ({currency})", ascending=False)
        )
        # Round to reduce payload
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

        # Chart 2: Cost Share by Category (Donut)
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
            fig_donut.update_traces(textposition="inside", textinfo="percent+label", hovertemplate="%{label}<br>%{value:,.2f}")
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

    # Download
    excel_blob = to_excel_bytes(main_meta, totals, df_out, schedule_label=type_of_schedule, currency=currency)
    try:
        st.download_button(
            "⬇️ Download Summary (Excel)",
            data=excel_blob,
            file_name="MEC_TOOL_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            help="Main Page, Working Page (tinted & subtotals), and Summary — styled & currency-aware",
            use_container_width=True
        )
    except TypeError:
        st.download_button(
            "⬇️ Download Summary (Excel)",
            data=excel_blob,
            file_name="MEC_TOOL_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Main Page, Working Page (tinted & subtotals), and Summary — styled & currency-aware",
            use_container_width=True
        )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("⬅️ Back to Totals", use_container_width=True):
            st.session_state["page"] = "TOTALS"
            do_rerun()
    with c2:
        if st.button("💾 Save for Comparison", use_container_width=True, type="primary"):
            saved_project = save_current_project()
            st.success(f"Project '{saved_project['name']}' saved for comparison!")
            do_rerun()
    with c3:
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
            manhour_change = comparison["manhour_pct"]
            manhour_badge = "up" if manhour_change > 5 else "down" if manhour_change < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Manhour Change</h3>
                    <div class="value">{comparison["manhour_diff"]:+,.0f}</div>
                    <div class="subvalue">
                        <span class="comparison-badge {manhour_badge}">
                            {comparison["manhour_pct"]:+.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            cost_change = comparison["cost_pct"]
            cost_badge = "up" if cost_change > 5 else "down" if cost_change < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Cost Change</h3>
                    <div class="value">{comparison["cost_diff"]:+,.2f} {project2['currency']}</div>
                    <div class="subvalue">
                        <span class="comparison-badge {cost_badge}">
                            {comparison["cost_pct"]:+.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col3:
            rate_change = comparison["avg_rate_pct"]
            rate_badge = "up" if rate_change > 5 else "down" if rate_change < -5 else "neutral"
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>Avg Rate Change</h3>
                    <div class="value">{comparison["avg_rate_diff"]:+,.2f} {project2['currency']}/hr</div>
                    <div class="subvalue">
                        <span class="comparison-badge {rate_badge}">
                            {comparison["avg_rate_pct"]:+.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Detailed comparison table
        st.subheader("Discipline-wise Comparison")
        
        if comparison["discipline_comparison"]:
            comp_df = pd.DataFrame(comparison["discipline_comparison"])
            
            # Clean up column names
            comp_df.columns = [col.replace(f"Total Price ({project1['currency']})_1", f"Cost_1 ({project1['currency']})")
                              .replace(f"Total Price ({project2['currency']})_2", f"Cost_2 ({project2['currency']})")
                              for col in comp_df.columns]
            
            # Calculate percentage changes
            comp_df["Manhour_Change_Pct"] = ((comp_df["Manhour_2"] - comp_df["Manhour_1"]) / comp_df["Manhour_1"].replace(0, 1)) * 100
            comp_df["Cost_Change_Pct"] = ((comp_df[f"Cost_2 ({project2['currency']})"] - comp_df[f"Cost_1 ({project1['currency']})"]) / 
                                        comp_df[f"Cost_1 ({project1['currency']})"].replace(0, 1)) * 100
            
            # Format for display
            display_df = comp_df[["Discipline", "Manhour_1", "Manhour_2", "Manhour_Diff", "Manhour_Change_Pct",
                                 f"Cost_1 ({project1['currency']})", f"Cost_2 ({project2['currency']})", 
                                 "Cost_Diff", "Cost_Change_Pct"]].copy()
            
            # Format numeric columns
            for col in ["Manhour_1", "Manhour_2", "Manhour_Diff"]:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}")
            
            for col in [f"Cost_1 ({project1['currency']})", f"Cost_2 ({project2['currency']})", "Cost_Diff"]:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}")
            
            display_df["Manhour_Change_Pct"] = display_df["Manhour_Change_Pct"].apply(lambda x: f"{x:+.1f}%")
            display_df["Cost_Change_Pct"] = display_df["Cost_Change_Pct"].apply(lambda x: f"{x:+.1f}%")
            
            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "Discipline": st.column_config.TextColumn("Discipline", width="small"),
                    "Manhour_1": st.column_config.TextColumn(f"{project1['name'][:10]}... MH", width="small"),
                    "Manhour_2": st.column_config.TextColumn(f"{project2['name'][:10]}... MH", width="small"),
                    "Manhour_Diff": st.column_config.TextColumn("MH Diff", width="small"),
                    "Manhour_Change_Pct": st.column_config.TextColumn("MH %", width="small"),
                    f"Cost_1 ({project1['currency']})": st.column_config.TextColumn(f"{project1['name'][:10]}... Cost", width="medium"),
                    f"Cost_2 ({project2['currency']})": st.column_config.TextColumn(f"{project2['name'][:10]}... Cost", width="medium"),
                    "Cost_Diff": st.column_config.TextColumn("Cost Diff", width="medium"),
                    "Cost_Change_Pct": st.column_config.TextColumn("Cost %", width="small"),
                },
                hide_index=True
            )
        
        # Visualization
        st.subheader("Visual Comparison")
        
        if comparison["discipline_comparison"]:
            comp_df = pd.DataFrame(comparison["discipline_comparison"])
            
            # Create comparison bar chart
            fig = go.Figure()
            
            # Add bars for project 1
            fig.add_trace(go.Bar(
                name=project1['name'][:20],
                y=comp_df['Discipline'],
                x=comp_df[f'Total Price ({project1["currency"]})_1'],
                orientation='h',
                marker_color=BRAND1,
                opacity=0.7
            ))
            
            # Add bars for project 2
            fig.add_trace(go.Bar(
                name=project2['name'][:20],
                y=comp_df['Discipline'],
                x=comp_df[f'Total Price ({project2["currency"]})_2'],
                orientation='h',
                marker_color=BRAND2,
                opacity=0.7
            ))
            
            fig.update_layout(
                barmode='group',
                title=f"Cost Comparison by Discipline",
                xaxis_title="Total Cost",
                yaxis_title="Discipline",
                height=max(400, len(comp_df) * 30),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12),
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Project management
    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("Manage Saved Projects")
    
    if saved_projects:
        # Display saved projects
        for i, project in enumerate(saved_projects):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{project['name']}**")
                st.caption(f"{project['type_of_schedule']} • {project['currency']} • {project['total_manhour']:,.0f} MH • {project['total_exact']:,.2f} {project['currency']}")
            with col2:
                st.caption(f"Saved: {datetime.fromisoformat(project['timestamp']).strftime('%Y-%m-%d %H:%M')}")
            with col3:
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
elif page == "TOTALS":
    render_totals()
elif page == "SUMMARY":
    render_summary()
elif page == "COMPARE":
    render_compare()
else:
    st.session_state["page"] = "MAIN"
    do_rerun()
