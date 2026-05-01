# app/config.py
#
# Single source of truth for paths, constants, design tokens, and layout
# dimensions. Everything that might be referenced from more than one module
# lives here. Grouped by concern; each section is independently importable.
#
# Color tokens are unpacked from the active theme (app/themes.py).
# Do not define raw hex values here — add them to themes.py instead.

from pathlib import Path

from app.themes import THEME_DARK as _T
from app.utils import (
    hex_to_rgb as _hex_to_rgb,
    hsl_rotate as _hsl_rotate,
)



# ═══════════════════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════════════════

APP_DIR     = Path(__file__).parent
PROJECT_DIR = APP_DIR.parent
DATA_DIR    = PROJECT_DIR / "data"
ASSETS_DIR  = PROJECT_DIR / "assets"
DB_PATH     = DATA_DIR / "artemis2.duckdb"


# ═══════════════════════════════════════════════════════════════════════════
#  JPL HORIZONS API
# ═══════════════════════════════════════════════════════════════════════════

HORIZONS_URL  = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Body identifiers
SPACECRAFT_ID = "-1024"        # Orion capsule (Artemis II)
MOON_ID       = "301"          # Moon
SUN_ID        = "10"           # Sun

# Query window
LAUNCH_TIME = "2026-04-01 22:35:00"   # UTC — SLS liftoff, LC-39B
EPHEM_START = "2026-Apr-02 01:59"     # First DSN tracking point (~T+3.5 h)
EPHEM_STOP  = "2026-Apr-10 23:54"     # Last point before reentry blackout
STEP_SIZE   = "1m"                    # 1-minute intervals

# Reference frame
CENTER     = "500@399"         # Geocenter (Earth-centered)
REF_SYSTEM = "ICRF"            # International Celestial Reference Frame
REF_PLANE  = "FRAME"           # XY aligned to ICRF equatorial plane

# Output format
OUT_UNITS  = "KM-S"           # Kilometers and km/s
VEC_TABLE  = "3"              # Position + velocity + light time + range + range rate


# ═══════════════════════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════════════════════

TABLE_TRAJECTORY = "orion_trajectory"
TABLE_ELEMENTS   = "orion_elements"
TABLE_MOON       = "moon_trajectory"
TABLE_SUN        = "sun_trajectory"

EXPECTED_ROW_COUNT = 12_836


# ═══════════════════════════════════════════════════════════════════════════
#  PHYSICAL CONSTANTS
#
#  Exact values from Metrics & Queries.md. Used for derived metric
#  calculations (orbital energy, gravitational acceleration, etc.).
# ═══════════════════════════════════════════════════════════════════════════

# Gravitational parameters (km³/s²)
GM_EARTH = 398_600.4418
GM_MOON  =   4_902.8001
GM_SUN   = 1.327_124_4e11

# Mean radii (km)
R_EARTH  = 6_371.0
R_MOON   = 1_737.4


# ═══════════════════════════════════════════════════════════════════════════
#  LAYOUT DIMENSIONS
#
#  Responsive triplets: (min_px, preferred_unit, max_px)
#  index_string.py assembles these into clamp() expressions.
#  CSS syntax never appears here.
#
#  Flat aliases kept for any existing code that imports the old names.
# ═══════════════════════════════════════════════════════════════════════════

HEADER_BRAND_HEIGHT = 44

PANEL_BORDER_RADIUS = 4   # fixed — no scaling

# Gap between panels
PANEL_GAP_MIN = 6
PANEL_GAP_VW  = 0.75   # 0.75vw ≈ 10px at 1333px wide
PANEL_GAP_MAX = 12

# Padding inside panels
PANEL_PADDING_MIN = 10
PANEL_PADDING_VW  = 1.2    # 1.2vw ≈ 16px at 1333px wide
PANEL_PADDING_MAX = 18

# Trajectory panel height
TRAJECTORY_HEIGHT_MIN = 400
TRAJECTORY_HEIGHT_VH  = 50     # 50vh = 540px at 1080p
TRAJECTORY_HEIGHT_MAX = 640

SCRUBBER_HEIGHT            = 44   # fixed
SCRUBBER_BORDER_RADIUS     = 20   # fixed
SCRUBBER_HORIZONTAL_MARGIN = 112  # fixed
SCRUBBER_DOT_SIZE          = 12   # fixed
SCRUBBER_DOT_ACTIVE        = 14   # fixed

# Telemetry grid height
TELEMETRY_HEIGHT_MIN = 280
TELEMETRY_HEIGHT_VH  = 33     # 33vh ≈ 356px at 1080p
TELEMETRY_HEIGHT_MAX = 480


# ═══════════════════════════════════════════════════════════════════════════
#  COLOR TOKENS
#
#  All values unpacked from the active theme. Semantic names here map to
#  slot names in themes.py — see that file for raw hex values and rationale.
# ═══════════════════════════════════════════════════════════════════════════

# ── Surfaces ──
BG_BASE      = _T["page_bg"]
PANEL_BG     = _T["panel_bg"]
PANEL_BORDER = _T["panel_border"]

# ── Typography ──
FONT_PRIMARY = _T["text_hi"]
FONT_DIM     = _T["text_mid"]
FONT_FAMILY  = _T["font_family"]

# ── Status ──
STATUS_LIVE  = _T["status_live"]

# ── Chart support ──
CHART_GRID_COLOR = _T["chart_grid"]
PLOTLY_BG        = _T["chart_plot_bg"]

# ── Panel group accents ──
ACCENT_VECTORS    = _T["accent_a"]   # teal   — velocity & vector panels
ACCENT_TRAJECTORY = _T["accent_b"]   # cyan   — orbital mechanics panels
ACCENT_GRAVITY    = _T["accent_c"]   # purple — gravity panels
ACCENT_RANGE      = _T["accent_d"]   # amber  — range / comms panels

# ── Trajectory visualization ──
COLOR_TRAJECTORY     = _T["viz_path"]
COLOR_TRAJECTORY_DIM = _T["viz_path_dim"]
COLOR_EARTH_FILL     = _T["viz_body_earth"]
COLOR_MOON_FILL      = _T["viz_body_moon"]
COLOR_STARFIELD      = _T["viz_starfield"]
COLOR_SPACECRAFT     = _T["viz_marker"]
SPACE_BG_COLOR       = _T["space_bg"]

# ── Arc RGB component strings ──
# Used in trajectory.py rgba() calls. Derived from theme hex so arc colors
# stay in sync with the palette automatically when a theme changes.
PAST_ARC_RGB      = _hex_to_rgb(_T["viz_path"])          # "255,255,255"
TRAJ_DIM_GLOW_RGB = _hex_to_rgb(_T["viz_path"])          # "255,255,255"
TRAJ_DIM_CORE_RGB = _hex_to_rgb(_T["viz_path"])          # "255,255,255"
FUTURE_GLOW_RGB   = _hex_to_rgb(_T["arc_future_glow"])   # "80,130,180"
FUTURE_CORE_RGB   = _hex_to_rgb(_T["arc_future_core"])   # "52,115,232"

# ── Arc marker dot colors ──
ARC_DOT_BURN  = _T["accent_g"]   # blood orange
ARC_DOT_COAST = _T["accent_a"]   # teal
ARC_DOT_OTHER = _T["accent_h"]   # steel silver

# Maps each phase key to its dot color category.
# Keys not listed fall back to "other".
ARC_MARKER_CATEGORY: dict[str, str] = {
    "perigee_raise":  "burn",
    "tli_burn":       "burn",
    "otc2_outbound":  "burn",
    "return_burn_1":  "burn",
    "return_burn_2":  "burn",
}


# ═══════════════════════════════════════════════════════════════════════════
#  MISSION PHASES
#
#  Each entry declares what a phase IS and where it APPEARS.
#  No timestamps or detection logic here — that lives in app/phases.py.
#
#  scrubber   : True  → appears as a clickable dot on the phase scrubber
#  arc_marker : True  → appears as a labeled marker on the trajectory arc
#
#  Adding a phase   = one new dict.
#  Changing display = flip scrubber / arc_marker.
#  Nothing else needs to change.
# ═══════════════════════════════════════════════════════════════════════════

# ── Hardcoded phase timestamps (UTC) ──────────────────────────────────────
# Source: NASA mission blogs + press releases. These are confirmed ops events
# with known times. Detectors in phases.py are bypassed for any key listed here.
# c3_zero is intentionally absent — it's a physics crossing, not an ops event;
# the DB detector owns it.
#
# slingshot_entry / slingshot_exit are starting estimates — tune as needed
# once you can compare against the actual C3 trace in the DB.

PHASE_HARDCODED_TIMES: dict[str, str] = {
    "perigee_raise":    "2026-04-02T11:10:00",   # ~43s burn, perigee raise (approx; wake-up was 11:06)
    "slingshot_entry":  "2026-04-02T22:00:00",   # TLI ignition — Earth slingshot begins; tune as needed
    "tli_burn":         "2026-04-02T23:49:00",   # 5m 49s, ΔV = 1,274 fps — confirmed
    "slingshot_exit":   "2026-04-03T05:00:00",   # ~21min post-TLI ignition; tune to actual C3=0 crossing
    "otc2_outbound":    "2026-04-06T03:03:00",   # 17.5s
    "lunar_soi_entry":  "2026-04-06T04:41:00",   # Moon's gravity becomes dominant
    "closest_approach": "2026-04-06T23:02:00",   # Pericynthion; distance record at +3min
    "lunar_soi_exit":   "2026-04-07T17:32:00",   # ~18.5h post-flyby (derived from NSF report)
    "return_burn_1":    "2026-04-08T00:03:00",   # 15s thruster burn
    "return_burn_2":    "2026-04-10T02:53:00",   # 9s thruster burn
}

PHASE_REGISTRY = (
    # ── Scrubber dot 0 ────────────────────────────────────────────────────
    {"key": "parking_orbit",    "label": "Parking Orbit",          "short": "PO",   "scrubber": True,  "arc_marker": False, "status_bar": True,  "status_label": "PARKING ORBIT"},
    {"key": "perigee_raise",    "label": "Perigee Raise Burn",     "short": "PRB",  "scrubber": False, "arc_marker": True,  "status_bar": False},
    # ── Scrubber dot 1 ────────────────────────────────────────────────────
    {"key": "slingshot_entry",  "label": "Earth Slingshot Entry",  "short": "SE",   "scrubber": True,  "arc_marker": False, "status_bar": True,  "status_label": "EARTH SLINGSHOT"},
    {"key": "tli_burn",         "label": "TLI Burn",               "short": "TLI",  "scrubber": False, "arc_marker": True,  "status_bar": False},
    # ── Scrubber dot 2 ────────────────────────────────────────────────────
    {"key": "slingshot_exit",   "label": "Earth Slingshot Exit",   "short": "SX",   "scrubber": True,  "arc_marker": False, "status_bar": True,  "status_label": "TRANS-LUNAR COAST"},
    {"key": "c3_zero",          "label": "Earth Escape (C3=0)",    "short": "C3",   "scrubber": False, "arc_marker": True,  "status_bar": False},
    # ── Scrubber dot 3: ~120 min before OTC-2 ─────────────────────────────
    {"key": "outbound_coast",   "label": "Outbound Coast",         "short": "OC",   "scrubber": True,  "arc_marker": False, "status_bar": False},
    {"key": "otc2_outbound",    "label": "OTC-2 Outbound",         "short": "OTC2", "scrubber": False, "arc_marker": True,  "status_bar": False},
    {"key": "lunar_soi_entry",  "label": "Lunar SOI Entry",        "short": "SOI",  "scrubber": False, "arc_marker": True,  "status_bar": True,  "status_label": "LUNAR APPROACH"},
    {"key": "closest_approach", "label": "Closest Approach",       "short": "CA",   "scrubber": False, "arc_marker": True,  "status_bar": True,  "status_label": "CLOSEST APPROACH"},
    # ── Scrubber dot 4 ────────────────────────────────────────────────────
    {"key": "lunar_soi_exit",   "label": "Lunar SOI Exit",         "short": "SOX",  "scrubber": True,  "arc_marker": True,  "status_bar": True,  "status_label": "TRANS-EARTH COAST"},
    {"key": "transearth_coast", "label": "Transearth Coast",       "short": "TC",   "scrubber": False, "arc_marker": False, "status_bar": False},
    {"key": "return_burn_1",    "label": "Return Burn 1",          "short": "RB1",  "scrubber": False, "arc_marker": True,  "status_bar": False},
    {"key": "return_burn_2",    "label": "Return Burn 2",          "short": "RB2",  "scrubber": False, "arc_marker": True,  "status_bar": False},
    # ── Scrubber dot 5 ────────────────────────────────────────────────────
    {"key": "earth_approach",   "label": "Earth Approach",         "short": "EA",   "scrubber": True,  "arc_marker": True,  "status_bar": True,  "status_label": "EARTH APPROACH"},
    {"key": "dataset_close",    "label": "Last Available Pos.",    "short": "LKP",  "scrubber": False, "arc_marker": True,  "status_bar": True,  "status_label": "LAST AVAILABLE POSITION"},
)


# ═══════════════════════════════════════════════════════════════════════════
#  TELEMETRY METRICS
#
#  Single source of truth for all telemetry tile configuration.
#  Keyed by panel group (same keys as PANEL_GROUPS), each value is an
#  ordered list of metric dicts consumed by telemetry.py, kpi.py, and
#  playback.js.
#
#  Keys per metric:
#    column   — DuckDB column name in the preload join query
#    label    — display label in the tile header (uppercase)
#    unit     — display unit string
#    fmt      — Python format string for server-side value rendering
#    decimals — decimal places for JS .toFixed() during playback
#    locale   — if True, JS uses toLocaleString() for thousands separators
# ═══════════════════════════════════════════════════════════════════════════

TELEMETRY_METRICS: dict[str, list[dict]] = {
    "vectors": [
        {"column": "speed_kms",    "label": "TOTAL SPEED", "unit": "km/s", "fmt": "{:.3f}", "decimals": 3, "locale": False, "viz_type": "sparkline"},
        {"column": "v_escape_kms", "label": "ESCAPE VEL",  "unit": "km/s", "fmt": "{:.3f}", "decimals": 3, "locale": False, "viz_type": "value_only"},
        {"column": "rr_kms",       "label": "RADIAL VEL",  "unit": "km/s", "fmt": "{:.3f}", "decimals": 3, "locale": False, "viz_type": "bidir_bar",
         "bidir_neg_color": ACCENT_GRAVITY},
    ],
    "trajectory": [
        {"column": "c3_km2s2", "label": "CHAR ENERGY",  "unit": "km²/s²", "fmt": "{:.2f}", "decimals": 2, "locale": False, "viz_type": "bidir_bar",
         "bidir_center": 0.0, "bidir_pos_color": ACCENT_RANGE,   "bidir_neg_color": ACCENT_TRAJECTORY, "bidir_mid": 0.85},
        {"column": "ec",       "label": "ECCENTRICITY", "unit": "—",      "fmt": "{:.4f}", "decimals": 4, "locale": False, "viz_type": "bidir_bar",
         "bidir_center": 1.0, "bidir_pos_color": ACCENT_VECTORS, "bidir_neg_color": ACCENT_TRAJECTORY, "bidir_mid": 0.85},
        {"column": "inc_deg",  "label": "INCLINATION",  "unit": "deg",    "fmt": "{:.2f}", "decimals": 2, "locale": False, "viz_type": "dial"},
    ],
    "gravity": [
        {"column": "grav_earth_ms2",  "label": "EARTH GRAV", "unit": "m/s²", "fmt": "{:.6f}", "decimals": 6, "locale": False, "viz_type": "bar",       "log_scale": True},
        {"column": "grav_moon_ms2",   "label": "MOON GRAV",  "unit": "m/s²", "fmt": "{:.6f}", "decimals": 6, "locale": False, "viz_type": "bar",       "log_scale": True},
        {"column": "dominance_ratio", "label": "MOON/EARTH", "unit": "—",    "fmt": "{:.6f}", "decimals": 6, "locale": False, "viz_type": "sparkline", "log_scale": False},
    ],
    "range": [
        {"column": "rg_km",     "label": "EARTH DIST", "unit": "km", "fmt": "{:,.1f}", "decimals": 1, "locale": True,  "viz_type": "sparkline"},
        {"column": "lt_sec",    "label": "LIGHT TIME",  "unit": "ls", "fmt": "{:.3f}", "decimals": 3, "locale": False, "viz_type": "value_only"},
        {"column": "r_moon_km", "label": "MOON DIST",  "unit": "km", "fmt": "{:,.1f}", "decimals": 1, "locale": True,  "viz_type": "sparkline"},
    ],
}

KPI_SVG_VIEWBOX_WIDTH  = 100    # internal SVG x range (0 → 100 = full mission)
KPI_SVG_VIEWBOX_HEIGHT = 84     # internal SVG y range


# ═══════════════════════════════════════════════════════════════════════════
#  SPARKLINE SVG
#
#  Controls the inline SVG sparkline rendered in each KPI tile.
#  Internal coordinate space (VIEWBOX_*) is independent of CSS px size —
#  the SVG scales to fill .tile-sparkline via width/height="100%".
#  Colors are inherited from CSS var(--panel-accent) — no tokens needed.
# ═══════════════════════════════════════════════════════════════════════════

SPARKLINE_PAD_X          = 10     # left/right padding inside sparkline
SPARKLINE_PAD_Y          = 4      # top/bottom padding inside sparkline
SPARKLINE_WIDTH          = 100    # usable sparkline width inside tile
SPARKLINE_HEIGHT         = KPI_SVG_VIEWBOX_HEIGHT     # usable sparkline height inside tile
SPARKLINE_PATH_OPACITY   = 0.85   # sparkline line opacity
SPARKLINE_PATH_WIDTH     = 1.5    # sparkline stroke-width (SVG units)
SPARKLINE_NEEDLE_OPACITY = 0.85   # position needle opacity
SPARKLINE_NEEDLE_WIDTH   = 1.8    # needle stroke-width (SVG units)
SPARKLINE_DOWNSAMPLE_N   = 200    # points in the SVG polyline (visual fidelity vs payload size)

SPARKLINE_FUTURE_OPACITY = 0.075  # unplayed-portion polyline opacity (dimmed, not hidden)
SPARKLINE_STAR_RADIUS    = 1.5    # star marker radius (SVG viewBox units, 0–100 x-axis)
SPARKLINE_STAR_GLOW_BLUR = 4.0    # feGaussianBlur stdDeviation for star glow filter

# ═══════════════════════════════════════════════════════════════════════════
#  BAR VIZ
#
#  Controls standard bar and both halves of the bi-directional bar.
#  Height is in CSS px — matches tile-sparkline slot height so all
#  sub-viz types occupy the same vertical space in the tile.
# ═══════════════════════════════════════════════════════════════════════════

BAR_HEIGHT        = KPI_SVG_VIEWBOX_HEIGHT - 4     # px — filled rect height
BAR_BORDER_RADIUS = 1     # px — rounded cap on the fill rect

# ═══════════════════════════════════════════════════════════════════════════
#  BI-DIRECTIONAL BAR VIZ
#
#  Positive side uses var(--panel-accent) (same as sparklines).
#  Negative side uses a fixed cool color so directionality reads clearly
#  regardless of which panel accent is active.
# ═══════════════════════════════════════════════════════════════════════════

BIDIR_HUE_OFFSET     = 100
BIDIR_NEGATIVE_COLOR = _hsl_rotate(_T["accent_a"], BIDIR_HUE_OFFSET)

# ═══════════════════════════════════════════════════════════════════════════
#  DIAL VIZ
#
#  SVG arc indicator for inclination.
#  Arc sweeps DIAL_ANGLE_MIN → DIAL_ANGLE_MAX degrees (SVG clock convention:
#  0° = 3 o'clock, angles increase clockwise).
#  Background arc is always full sweep; filled arc shows current value.
# ═══════════════════════════════════════════════════════════════════════════

DIAL_CY_OFFSET      = 8       # dial vertical offset
DIAL_RADIUS         = 64      # arc radius in SVG units
DIAL_STROKE_WIDTH   = 36      # arc stroke width
DIAL_ANGLE_MIN      = 170     # degrees — left endpoint (just inside 9 o'clock)
DIAL_ANGLE_MAX      = 10      # degrees — right endpoint (just inside 3 o'clock)
DIAL_VAL_MIN        = 0.0     # data value mapped to DIAL_ANGLE_MIN
DIAL_VAL_MAX        = 180.0   # data value mapped to DIAL_ANGLE_MAX
DIAL_STROKE_LINECAP = "butt"  # SVG stroke-linecap: "butt" | "round" | "square"


# ── Arc marker dot sizing + label offset ──
ARC_DOT_SIZE      = 7     # px — dot diameter
ARC_LABEL_SIZE    = 9     # px — short-code label font size
ARC_LABEL_YSHIFT  = 14    # px upward — label offset above dot center


# ═══════════════════════════════════════════════════════════════════════════
#  TRAJECTORY VIZ — STARFIELD + CAMERA
#
#  Controls the fixed viewport for the 2D Earth–Moon trajectory panel.
#  Adjust these to frame the arc in the panel without touching figure logic.
# ═══════════════════════════════════════════════════════════════════════════

# ── Starfield ─────────────────────────────────────────────────────────────
# Dim population: faint background stars (fraction = STAR_DIM_FRACTION of total)
# Bright population: remainder

STAR_SEED  = 42
STAR_COUNT = 360
STAR_DIM_FRACTION  = 0.79

STAR_SIZE_DIM_MIN  = 0.04
STAR_SIZE_DIM_MAX  = 0.07
STAR_SIZE_FG_MIN   = 0.06
STAR_SIZE_FG_MAX   = 0.08

STAR_ALPHA_DIM_MIN = 0.12
STAR_ALPHA_DIM_MAX = 0.35
STAR_ALPHA_FG_MIN  = 0.45
STAR_ALPHA_FG_MAX  = 0.75

# ── Camera ────────────────────────────────────────────────────────────────
VIEW_ROTATION_DEG  = 125.0      # Scene rotation CCW (degrees). Turn until the arc sits nicely across the wide panel.
VIEW_ZOOM          =   0.2325   # Fraction of full mission bounding box shown. < 1.0 zooms in, > 1.0 zooms out.
VIEW_X_OFFSET_KM   = -10_000    # Shift view center left(−) / right(+) in km.
VIEW_Y_OFFSET_KM   =     000    # Shift view center down(−) / up(+) in km.

# ── Dim context arc (full mission ghost path) ─────────────────────────────
TRAJ_DIM_GLOW_WIDE         = 8
TRAJ_DIM_GLOW_WIDE_ALPHA   = 0.15
TRAJ_DIM_GLOW_NARROW       = 3
TRAJ_DIM_GLOW_NARROW_ALPHA = 0.20
TRAJ_DIM_CORE_WIDTH        = 1
TRAJ_DIM_CORE_ALPHA        = 0.33
TRAJ_DIM_CORE_DASH         = "dot"

# ── Dim context arc (full mission ghost path) ─────────────────────────────
PAST_ARC_GLOW_WIDTH = 6
PAST_ARC_GLOW_ALPHA = 0.20
PAST_ARC_CORE_WIDTH = 1
PAST_ARC_CORE_ALPHA = 0.85

# ── Future arc ────────────────────────────────────────────────────────────
FUTURE_ARC_HOURS     = 36     # Total lookahead window (hours)
FUTURE_FADE_HOURS    = 9      # Hours at end of window that fade to transparent
FUTURE_FADE_SEGMENTS = 12     # Opacity steps across the fade window

# Glow layers (wide + narrow pass behind the core)
FUTURE_GLOW_WIDE         = 6              # Wide glow pass width (px)
FUTURE_GLOW_WIDE_ALPHA   = 0.20           # Wide glow base opacity
FUTURE_GLOW_NARROW       = 3              # Narrow glow pass width (px)
FUTURE_GLOW_NARROW_ALPHA = 0.30           # Narrow glow base opacity

# Dotted core
FUTURE_CORE_WIDTH = 0.8              # Core line width (px)
FUTURE_CORE_ALPHA = 1.0              # Core base opacity
FUTURE_CORE_DASH  = "dot"            # "dot", "dash", "dashdot", "longdashdot"

# ── Body label positions ──────────────────────────────────────────────────
# Vertical offset multipliers.
EARTH_LABEL_Y_MULT = 2.5
MOON_LABEL_Y_MULT  = 7.0

# ── Orion callout label ───────────────────────────────────────────────────
ORION_LABEL_SHOW     = True    # False hides the annotation entirely
ORION_LABEL_BG_ALPHA = 0.33    # Background box opacity (0.0 = invisible, 1.0 = solid)
ORION_LABEL_XSHIFT   = -40     # Arrow / offset x (px) — still controls box position
ORION_LABEL_YSHIFT   = 40      # Arrow / offset y (px)

# ── Orion spacecraft marker ───────────────────────────────────────────────
ORION_MARKER_SIZE = 5          # Diameter of the position dot (px)


# ═══════════════════════════════════════════════════════════════════════════
#  PLAYBACK
# ═══════════════════════════════════════════════════════════════════════════

PLAYBACK_FRAME_INTERVAL_MIN       = 1
PLAYBACK_INTERVAL_MS              = 100   # dcc.Interval tick rate (ms) — 10fps
PLAYBACK_FRAMES_PER_TICK          = 6    # frames advanced per tick (60 rows = 1 hr at 1-min resolution)
PLAYBACK_ANNOTATION_WINDOW_FRAMES = 180
PLAYBACK_SPEED_MULT               = PLAYBACK_FRAMES_PER_TICK * (1000 // PLAYBACK_INTERVAL_MS) * 60
PLAYBACK_SPEED_LABEL              = f"PLAYBACK · {PLAYBACK_SPEED_MULT}×"


PLAYBACK_BTN_SIZE      = 32   # px — play/pause button diameter
PLAYBACK_BTN_FONT_SIZE = 20   # px


# ═══════════════════════════════════════════════════════════════════════════
#  PANEL GROUPS
# ═══════════════════════════════════════════════════════════════════════════

PANEL_GROUPS = {
    "vectors": {
        "label":  "VECTORS",
        "code":   "VEC",
        "accent": ACCENT_VECTORS,
    },
    "trajectory": {
        "label":  "TRAJECTORY / ORBITAL",
        "code":   "TRJ",
        "accent": ACCENT_TRAJECTORY,
    },
    "gravity": {
        "label":  "GRAVITATIONAL PULL",
        "code":   "GRV",
        "accent": ACCENT_GRAVITY,
    },
    "range": {
        "label":  "RANGE / COMMS",
        "code":   "RNG",
        "accent": ACCENT_RANGE,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════════════════

# FONT_FAMILY is unpacked from the theme above (color tokens section).
# Non-theme typography constants (sizes, Google Fonts URL) live here.

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Space+Mono:wght@400;700&display=swap"
)

FONT_SIZE_TITLE_MIN = 16
FONT_SIZE_TITLE_VW  = 1.4
FONT_SIZE_TITLE_MAX = 28

FONT_SIZE_HEADER  = 14
FONT_SIZE_LABEL   = 11
FONT_SIZE_STATUS  = 14
FONT_SIZE_TOOLTIP = 13

FONT_SIZE_KPI_MIN = 20
FONT_SIZE_KPI_VW  = 1.8    # clamp(20px, 1.8vw, 28px) as specified
FONT_SIZE_KPI_MAX = 28
FONT_SIZE_KPI     = FONT_SIZE_KPI_MAX   # alias — used for Python-side sizing math