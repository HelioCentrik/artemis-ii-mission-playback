# app/config.py
#
# Single source of truth for paths, constants, design tokens, and layout
# dimensions. Everything that might be referenced from more than one module
# lives here. Grouped by concern; each section is independently importable.

from pathlib import Path



# ═══════════════════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════════════════

APP_DIR     = Path(__file__).parent          # app/
PROJECT_DIR = APP_DIR.parent                 # project root
DATA_DIR    = PROJECT_DIR / "data"
ASSETS_DIR  = PROJECT_DIR / "assets"
DB_PATH     = DATA_DIR / "artemis2.duckdb"


# ═══════════════════════════════════════════════════════════════════════════
#  JPL HORIZONS API
# ═══════════════════════════════════════════════════════════════════════════

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Body identifiers
SPACECRAFT_ID = "-1024"        # Orion capsule (Artemis II)
MOON_ID       = "301"          # Moon
SUN_ID        = "10"           # Sun

# Query window
MISSION_START = "2026-Apr-02 01:59"   # First DSN tracking point (~T+3.5 h)
MISSION_STOP  = "2026-Apr-10 23:54"   # Last point before reentry blackout
STEP_SIZE     = "1m"                  # 1-minute intervals

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
R_EARTH = 6_371.0
R_MOON  = 1_737.4


# ═══════════════════════════════════════════════════════════════════════════
#  MISSION PHASES
#
#  Display labels only — detection logic lives in app/phases.py.
#  Index position = phase number (0-based). Tuple so it can't be
#  accidentally mutated at runtime.
# ═══════════════════════════════════════════════════════════════════════════

PHASES = (
    {"key": "early_coast",       "label": "Early Coast",       "short": "EC"},
    {"key": "translunar_coast",  "label": "Trans-Lunar Coast", "short": "TLC"},
    {"key": "lunar_approach",    "label": "Lunar Approach",    "short": "LA"},
    {"key": "closest_approach",  "label": "Closest Approach",  "short": "CA"},
    {"key": "return_coast",      "label": "Return Coast",      "short": "RC"},
)

PHASE_COUNT = len(PHASES)


# ═══════════════════════════════════════════════════════════════════════════
#  TRAJECTORY VIZ — STARFIELD + CAMERA
#
#  Controls the fixed viewport for the 2D Earth–Moon trajectory panel.
#  Adjust these to frame the arc in the panel without touching figure logic.
# ═══════════════════════════════════════════════════════════════════════════

# ── Starfield ─────────────────────────────────────────────────────────────
# Dim population: faint background stars (fraction = STAR_DIM_FRACTION of total)
# Bright population: remainder

SPACE_BG_COLOR = "#000000"

STAR_SEED  = 42
STAR_COUNT = 360
STAR_DIM_FRACTION  = 0.79

STAR_SIZE_DIM_MIN  = 0.04    # SVG viewBox units (0–100 coordinate space)
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
VIEW_Y_OFFSET_KM   =   8_000    # Shift view center down(−) / up(+) in km.

# ── Dim context arc (full mission ghost path) ─────────────────────────────
TRAJ_DIM_GLOW_RGB          = "255,255,255"
TRAJ_DIM_GLOW_WIDE         = 8
TRAJ_DIM_GLOW_WIDE_ALPHA   = 0.15
TRAJ_DIM_GLOW_NARROW       = 3
TRAJ_DIM_GLOW_NARROW_ALPHA = 0.20
TRAJ_DIM_CORE_RGB          = "255,255,255"
TRAJ_DIM_CORE_WIDTH        = 1
TRAJ_DIM_CORE_ALPHA        = 0.33
TRAJ_DIM_CORE_DASH         = "dot"

# ── Future arc ────────────────────────────────────────────────────────────
FUTURE_ARC_HOURS     = 24     # Total lookahead window (hours)
FUTURE_FADE_HOURS    = 6      # Hours at end of window that fade to transparent
FUTURE_FADE_SEGMENTS = 8      # Opacity steps across the fade window

# Glow layers (wide + narrow pass behind the core)
FUTURE_GLOW_RGB          = "80,130,180"   # R,G,B shared by both glow passes
FUTURE_GLOW_WIDE         = 6              # Wide glow pass width (px)
FUTURE_GLOW_WIDE_ALPHA   = 0.12           # Wide glow base opacity
FUTURE_GLOW_NARROW       = 3              # Narrow glow pass width (px)
FUTURE_GLOW_NARROW_ALPHA = 0.20           # Narrow glow base opacity

# Dotted core
FUTURE_CORE_RGB   = "52, 115, 232"    # #2a3f5f as R,G,B
FUTURE_CORE_WIDTH = 1              # Core line width (px)
FUTURE_CORE_ALPHA = 1.0            # Core base opacity
FUTURE_CORE_DASH  = "dashdot"      # "dot", "dash", "dashdot", "longdashdot"

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
#  LAYOUT DIMENSIONS
#
#  All values in px unless noted. Injected as CSS custom properties.
# ═══════════════════════════════════════════════════════════════════════════

# Header
HEADER_BRAND_HEIGHT  = 44      # Top branding bar
HEADER_STATUS_HEIGHT = 32      # Status bar (GMT, MET, DOY)

# Trajectory panel
TRAJECTORY_MIN_HEIGHT = 540    # Main viz area (excluding scrubber)

# Scrubber
SCRUBBER_HEIGHT     = 48       # Phase scrubber track
SCRUBBER_DOT_SIZE   = 12       # Phase marker dot diameter
SCRUBBER_DOT_ACTIVE = 14       # Active phase marker diameter

# Telemetry
TELEMETRY_MIN_HEIGHT = 360     # Telemetry grid minimum height

# Panels
PANEL_BORDER_RADIUS = 4        # Hard-edge utilitarian feel
PANEL_GAP           = 10       # Grid gap between telemetry panels
PANEL_PADDING       = 16       # Interior padding

# Sparklines
SPARKLINE_HEIGHT = 80          # Mini-chart height inside KPI tiles


# ═══════════════════════════════════════════════════════════════════════════
#  COLOR TOKENS
#
#  Canonical color definitions. Injected as CSS custom properties via
#  index_string.py. Plotly figures reference these through the artemis2
#  template or import them directly.
# ═══════════════════════════════════════════════════════════════════════════

# ── Surface / background ──
BG_BASE      = "#050a0f"       # Page background
PANEL_BG     = "#0a1628"       # Panel card fill
PANEL_BORDER = "#1a2f4a"       # Panel card border

# ── Typography ──
FONT_PRIMARY = "#c8e8ff"       # Primary text
FONT_DIM     = "#4a7a9b"       # Secondary / labels / deemphasized

# ── Status ──
STATUS_LIVE  = "#22c55e"       # Green dot — live / nominal indicator

# ── Panel group accents ──
ACCENT_VECTORS    = "#00e5cc"  # Teal     — velocity & vector components
ACCENT_TRAJECTORY = "#00aaff"  # Cyan     — orbital mechanics, C3, eccentricity
ACCENT_GRAVITY    = "#a855f7"  # Purple   — gravitational accelerations
ACCENT_RANGE      = "#f59e0b"  # Amber    — distances, light time, comms

# ── Trajectory visualization ──
COLOR_TRAJECTORY      = "#ffffff"   # Primary arc (past path)
COLOR_TRAJECTORY_DIM  = "#2a3f5f"   # Dashed future / return arc
COLOR_EARTH_FILL      = "#1e90ff"   # Earth sphere
COLOR_EARTH_GLOW      = "#1e90ff33" # Earth glow halo (low alpha)
COLOR_MOON_FILL       = "#b0b0b0"   # Moon sphere
COLOR_MOON_GLOW       = "#b0b0b033" # Moon glow halo
COLOR_STARFIELD       = "#ffffff"   # Background star dots
COLOR_SPACECRAFT      = "#ffffff"   # Orion marker


# ═══════════════════════════════════════════════════════════════════════════
#  PANEL GROUPS
#
#  Structured definitions for telemetry panel groups. Keys are used as
#  CSS class suffixes, callback group IDs, and programmatic lookups.
#  Adding a new panel group = adding one entry here.
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

FONT_FAMILY = "'Space Mono', monospace"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Space+Mono:wght@400;700&display=swap"
)

# Font sizes (px) — referenced by Plotly template and CSS variables
FONT_SIZE_KPI    = 28          # Large KPI readout value
FONT_SIZE_LABEL  = 11          # Tile labels, axis ticks
FONT_SIZE_HEADER = 14          # Panel group headers
FONT_SIZE_STATUS = 12          # Status bar text


# ═══════════════════════════════════════════════════════════════════════════
#  PLOTLY DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════

# Transparent backgrounds — CSS owns the visual layer.
# Every figure must use these; the artemis2 Plotly template applies them
# automatically, but they're here for any manual figure construction.
PLOTLY_BG = "rgba(0,0,0,0)"