# MEC TOOL — PETRONAS Upstream CE

> **Major Engineering Contract Cost Estimation Tool**  
> Built with Streamlit · Author: Ahmad Naquib Syahmee Masror

---

## Table of Contents

- [User Guide](#user-guide)
  - [Requirements](#requirements)
  - [Starting the App](#starting-the-app)
  - [Step-by-Step Workflow](#step-by-step-workflow)
    - [1. Sidebar Setup](#1-sidebar-setup)
    - [2. Home](#2-home)
    - [3. Personnel](#3-personnel)
    - [4. Third Party](#4-third-party)
    - [5. Non-Labour](#5-non-labour)
    - [6. Loading](#6-loading)
    - [7. Totals](#7-totals)
    - [8. Dashboard & Compare](#8-dashboard--compare)
  - [Excel Export](#excel-export)
- [Developer Guide](#developer-guide)
  - [Project Structure](#project-structure)
  - [Key Constants](#key-constants)
  - [Session State Keys](#session-state-keys)
  - [Page Routing](#page-routing)
  - [Core Functions](#core-functions)
  - [CSS & Theming](#css--theming)
  - [Adding a New Page](#adding-a-new-page)
  - [Adding a New Discipline](#adding-a-new-discipline)

---

## User Guide

### Requirements

- Python 3.9 or later
- A MEC rates CSV file (e.g. `MEC.csv`) — required to load rate data before use

Install Python dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt` includes: `streamlit`, `pandas`, `openpyxl`, `streamlit-aggrid`, `plotly`, `Pillow`

---

### Starting the App

```bash
cd MECTOOL_LATEST
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501` in your browser.

---

### Step-by-Step Workflow

#### 1. Sidebar Setup

Before anything else, use the **left sidebar** to:

| Field | Description |
|---|---|
| **Dark Mode** toggle | Switch between light and dark theme |
| **MEC Rates** file upload | Upload your `MEC.csv` rates file — the app will not load data until this is provided |

> The sidebar can be collapsed using the `«` arrow at the top-right of it. All navigation tabs become available once the CSV is uploaded.

---

#### 2. Home

Fill in project metadata:

| Field | Description |
|---|---|
| Project Title | Name of the project |
| Date | Estimation date |
| Cost Engineer | Name of the cost engineer |
| TP/Specialist | Third-party specialist name |
| Schedule | Schedule A (MYR) or Schedule B/D (USD) |
| Package | Package identifier (e.g. U1, U2) |

- **Reset Grid** — clears all personnel data and starts fresh.
- **Next →** — proceeds to the Personnel tab.

---

#### 3. Personnel

Configure the engineering headcount and hours.

**Bulk Actions (top of page):**
- Set **Category** (e.g. Malaysian, Expatriate) or **Rate Type** (e.g. AKER, Normalise) for all rows at once using the dropdowns and **Apply** buttons.

**Personnel Grid:**
- Each row represents one personnel role within a discipline.
- Editable columns: Discipline, Personnel, Category, Type of Unit Rate.
- Hours and costs are calculated automatically from the loaded MEC rates.
- **Add Row** — adds a new blank personnel entry.
- **Reset** — restores the grid to default discipline rows.

Navigate: **← Back** (Home) · **Next →** (Third Party)

---

#### 4. Third Party

Add third-party service cost items.

Each item has:

| Field | Description |
|---|---|
| Description | Name of the service |
| Basis | `Percentage of Labour Cost` or `Lump Sum` |
| Percentage | Applied if Basis = Percentage (enter as a decimal, e.g. `0.05` = 5%) |
| LumpSum Details | Shown if Basis = Lump Sum — add sub-line items with descriptions and amounts |

- **Add Item** — adds a new cost row.
- When using Lump Sum, click **Add Detail** to break it into named sub-amounts. The total is summed automatically.
- A calculated cost summary table is shown below the inputs.

Navigate: **← Back** (Personnel) · **Next →** (Non-Labour)

---

#### 5. Non-Labour

Identical interface to Third Party, used for non-labour costs such as tools, equipment, software licences, and travel.

Navigate: **← Back** (Third Party) · **Next →** (Loading)

---

#### 6. Loading

Distribute total costs across the project timeline.

| Control | Description |
|---|---|
| Number of Months | How many months the project spans (default: 6) |
| Update | Resizes the table to match the entered month count |
| Total Weightage | Must equal 100% — a warning is shown if it doesn't |

For each month, set:
- **Loading Factor (%)** — effort intensity (100% = normal pace, 150% = crunch)
- **Weightage Distribution (%)** — share of total cost allocated to that month

The **Effective %** and **Est. Cost** columns are read-only and calculated automatically.

Navigate: **← Back** (Non-Labour) · **Next →** (Totals)

---

#### 7. Totals

Read-only cost summary:

- Labour cost breakdown by discipline (manhours + cost)
- Third Party Services total
- Non-Labour total
- **Total Raw Bid Price (Base Scope)** — highlighted teal row
- Average Weightage per Month
- Currency per manhour rate

Use **Save Project** to snapshot the current estimate for use in the Compare page.

Navigate: **← Back** (Loading) · **Dashboard** · **Compare**

---

#### 8. Dashboard & Compare

**Dashboard** shows visual KPIs and charts:
- Total labour cost, manhours, and project duration cards
- Monthly cost bar chart (Labour + Third Party stacked)
- Cost pie chart by discipline

**Compare** shows two saved projects side-by-side:
- Select two saved snapshots from the dropdowns
- A summary table and bar chart highlight the differences

---

### Excel Export

From the **Totals** page, click **Excel Report** to download a formatted `.xlsx` file.

**Sheet: Summary**

| Column B | Column C | Column D |
|---|---|---|
| PETRONAS branded header (merged B2:I3, teal) | | |
| Project metadata labels (bold) | Values | |
| Description header | Manhour header | Total Price header |
| Labour rows by discipline | Hours | Cost |
| Third Party Services | | Total |
| Non-Labour | | Total |
| **Total Raw Bid Price** (teal, white bold) | Total hours | Total cost |
| Average Weightage per Month | Value | |
| MYR/Manhour | Value | |

All data cells have black borders. Column widths are pre-set (B = 42, C = 16, D = 24).

**Sheet: Labour Details** — full row-by-row personnel breakdown with auto-sized columns.

---

## Developer Guide

### Project Structure

```
MECTOOL_LATEST/
├── streamlit_app.py       # Entire application (single file, ~2600 lines)
├── requirements.txt       # Python dependencies
├── mec-tool-logo.png      # Logo used in sidebar and browser tab icon
├── README.md              # This file
```

---

### Key Constants

Defined near the top of `streamlit_app.py` (~lines 44–170):

| Constant | Description |
|---|---|
| `PETRONAS` | Brand colour palette dict (teal, navy, gold, greys) |
| `HOURS_PER_MONTH` | `176.0` — standard billable hours per month |
| `N_MONTHS` | `6` — default number of project months |
| `USD_SCHEDULES` | Set of schedule identifiers that use USD (`{"b", "d", ...}`) |
| `AC_CATEGORIES` | MYR categories: Malaysian, Regional, Expatriate |
| `B_D_CATEGORY_FALLBACK` | USD region categories (Americas, Europe, etc.) |
| `UNIT_TYPES` | Rate type options: Normalise, AKER, DAR, MMC, etc. |
| `DISCIPLINE_ROW_COUNTS` | Default personnel row count per discipline on grid initialisation |
| `DEFAULT_PERSONNEL` | Personnel name lists per discipline |
| `DISCIPLINE_COLORS` | Hex row background colours per discipline in the grid |
| `DISCIPLINE_SWATCH` | Emoji colour swatches rendered in the grid Swatch column |
| `PAGES` | `dict` mapping internal page keys to display labels |
| `GRID_KEY` | Session state key for the personnel DataFrame |
| `THIRD_PARTY_KEY` | Session state key for the third party DataFrame |
| `NON_LABOUR_KEY` | Session state key for the non-labour DataFrame |
| `MONTHLY_LOADING_KEY` | Session state key for the monthly loading DataFrame |

---

### Session State Keys

Initialised in `init_session_state()` (~line 157):

| Key | Type | Description |
|---|---|---|
| `page` | `str` | Current active page key (e.g. `"MAIN"`, `"TABLE"`) |
| `dark_mode` | `bool` | Dark/light theme toggle state |
| `project_title` | `str` | Project title |
| `cost_engineer` | `str` | Cost engineer name |
| `tp_specialist` | `str` | TP/specialist name |
| `project_date` | `date` | Estimation date |
| `type_of_schedule` | `str` | Selected schedule (A / B / D) |
| `type_of_package` | `str` | Package ID (e.g. U1) |
| `mec_df` | `DataFrame` | Parsed MEC rates CSV |
| `mec_data_loaded` | `bool` | Whether the CSV has been uploaded and parsed |
| `grid_df` | `DataFrame` | Personnel grid rows |
| `third_party_df` | `DataFrame` | Third party cost items |
| `non_labour_df` | `DataFrame` | Non-labour cost items |
| `monthly_loading_df` | `DataFrame` | Monthly loading/weightage rows |
| `saved_projects` | `list[dict]` | Saved project snapshots for Compare |

---

### Page Routing

The app uses a single-page architecture with manual routing via `st.session_state["page"]`.

```python
# Navigation pattern used across all pages:
if st.button("Next →", type="primary"):
    st.session_state["page"] = "THIRD_PARTY"
    st.rerun()
```

The main dispatcher (bottom of file):

```python
page = st.session_state["page"]
if   page == "MAIN":        render_main()
elif page == "TABLE":       render_table()
elif page == "THIRD_PARTY": render_third_party()
elif page == "NON_LABOUR":  render_non_labour()
elif page == "LOADING":     render_loading()
elif page == "TOTALS":      render_totals()
elif page == "SUMMARY":     render_summary()
elif page == "COMPARE":     render_compare()
```

The top navigation bar and sidebar are rendered on every page via shared calls before the dispatcher.

---

### Core Functions

| Function | Approx. Line | Description |
|---|---|---|
| `init_session_state()` | 157 | Sets all session state defaults on first load |
| `inject_css(dark)` | 178 | Builds and injects all custom CSS for the active theme |
| `currency_for(schedule)` | helper | Returns `"USD"` or `"MYR"` based on schedule string |
| `is_usd(schedule)` | helper | `True` for Schedule B/D |
| `build_category_options(sched, df)` | helper | Reads category list from the loaded MEC CSV |
| `initialize_default_grids()` | helper | Populates `grid_df` with default rows per discipline |
| `reset_grid()` | helper | Clears and re-initialises `grid_df` |
| `calculate_labour_costs(df, currency, sched, pkg)` | ~1050 | Looks up unit rates from MEC CSV and computes labour cost per row |
| `calculate_third_party_costs(df, total_labour, currency)` | ~1399 | Computes third party / non-labour cost rows |
| `parse_lumpsum_details(raw)` | ~1384 | Parses JSON-encoded LumpSum detail list from a cell value |
| `to_excel_bytes(meta, totals, labour_df, third_df, monthly_df, currency)` | ~1500 | Builds the Excel workbook and returns it as bytes |
| `render_step_bar()` | helper | Renders the horizontal progress indicator |
| `save_current_project()` | helper | Appends a snapshot dict to `saved_projects` |
| `section_header(title, icon)` | helper | Renders a styled section heading |
| `render_main()` | ~1648 | Home page — project metadata inputs |
| `render_table()` | ~1732 | Personnel grid page — AgGrid + bulk actions |
| `render_third_party()` | ~2056 | Third Party cost entry page |
| `render_non_labour()` | ~2220 | Non-Labour cost entry page |
| `render_loading()` | ~2375 | Monthly loading / weightage distribution page |
| `render_totals()` | ~1870 | Totals summary page with Excel export |
| `render_summary()` | ~1960 | Dashboard charts page |
| `render_compare()` | ~2490 | Side-by-side project comparison page |

---

### CSS & Theming

All CSS lives inside `inject_css(dark: bool)`, injected via `st.markdown(..., unsafe_allow_html=True)` on every rerun.

CSS custom properties (set on `:root`):

```css
--teal, --teal-dark, --gold
--bg, --bg-alt, --bg-card
--text, --text-muted
--border, --input-bg, --metric-bg
```

**Critical rules to keep intact:**

- `.petronas-banner *` is always forced `color: #ffffff` — do not add global text-colour rules that can override this.
- `section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] *` is forced to `#1a2535` (dark) because Streamlit's dropzone box always renders with a light background regardless of the app theme.
- AgGrid switches theme via `ag_theme = "alpine-dark" if dark else "alpine"` passed to the `AgGrid()` call.

---

### Adding a New Page

1. Add an entry to `PAGES`:
   ```python
   PAGES["MY_PAGE"] = "My Page"
   ```

2. Add it to `PAGE_STEPS` if it should appear in the step progress bar:
   ```python
   PAGE_STEPS = [..., "MY_PAGE"]
   ```

3. Write a `render_my_page()` function following the existing pattern:
   - PETRONAS banner (`petronas-banner` div)
   - `render_step_bar()`
   - Page content
   - `← Back` / `Next →` buttons at the bottom

4. Add a branch to the main dispatcher:
   ```python
   elif page == "MY_PAGE": render_my_page()
   ```

5. Update the Back/Next buttons on the adjacent pages to point to `"MY_PAGE"`.

---

### Adding a New Discipline

1. Add to `DISCIPLINE_ROW_COUNTS` (controls default row count):
   ```python
   "My Discipline": 5,
   ```

2. Add personnel list to `DEFAULT_PERSONNEL`:
   ```python
   "My Discipline": ["Lead Engineer X", "Senior Engineer X", "Engineer X", "Drafting", "Designer"],
   ```

3. Add a grid row background colour to `DISCIPLINE_COLORS` (6-digit hex, no `#`):
   ```python
   "My Discipline": "FFF3E0",
   ```

4. Add a swatch emoji to `DISCIPLINE_SWATCH`:
   ```python
   "My Discipline": "🟧",
   ```

The discipline will then appear automatically in the Personnel grid dropdown, rate lookups, Excel export breakdowns, and Dashboard charts.
