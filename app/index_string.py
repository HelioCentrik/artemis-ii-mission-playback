# app/index_string.py
#
# Custom Dash index_string that injects CSS custom properties and the
# Google Fonts <link> into <head>. Dash replaces its default HTML shell
# with this string — the {%...%} placeholders are required by Dash.

import json

from app.config import (
    # Surfaces
    BG_BASE, PANEL_BG, PANEL_BORDER,
    # Typography
    FONT_PRIMARY, FONT_DIM, FONT_FAMILY, GOOGLE_FONTS_URL,
    FONT_SIZE_TITLE_MIN, FONT_SIZE_TITLE_VW, FONT_SIZE_TITLE_MAX,
    FONT_SIZE_KPI_MIN, FONT_SIZE_KPI_VW, FONT_SIZE_KPI_MAX,
    FONT_SIZE_LABEL, FONT_SIZE_HEADER, FONT_SIZE_STATUS, FONT_SIZE_TOOLTIP, FONT_SIZE_SIDE_PANEL,
    # Status
    STATUS_LIVE,
    # Accents
    ACCENT_VECTORS, ACCENT_TRAJECTORY, ACCENT_GRAVITY, ACCENT_RANGE,
    # Layout
    HOME_MEDIA_ROW_HEIGHT, HOME_CREW_CARD_HEIGHT,
    SIDE_PANEL_WIDTH, SIDE_PANEL_TRANSITION,
    HEADER_BRAND_HEIGHT,
    SCRUBBER_HEIGHT, SCRUBBER_BORDER_RADIUS, SCRUBBER_HORIZONTAL_MARGIN, SCRUBBER_DOT_SIZE,
    TRAJECTORY_HEIGHT, TELEMETRY_HEIGHT,
    PANEL_BORDER_RADIUS,
    PANEL_GAP_MIN, PANEL_GAP_VW, PANEL_GAP_MAX,
    PANEL_PADDING_MIN, PANEL_PADDING_VW, PANEL_PADDING_MAX,
    # Trajectory viz
    COLOR_TRAJECTORY, COLOR_TRAJECTORY_DIM,
    # Playback
    PLAYBACK_BTN_SIZE, PLAYBACK_BTN_FONT_SIZE,
    # Telemetry
    KPI_SVG_VIEWBOX_WIDTH, KPI_SVG_VIEWBOX_HEIGHT,
    SPARKLINE_PAD_X, SPARKLINE_PAD_Y, SPARKLINE_WIDTH, SPARKLINE_HEIGHT,
    DIAL_RADIUS, DIAL_ANGLE_MIN, DIAL_ANGLE_MAX, DIAL_STROKE_WIDTH,
    DIAL_STROKE_LINECAP, DIAL_CY_OFFSET, DASHBOARD_WIDTH_MAX, DASHBOARD_WIDTH_MIN, DASHBOARD_WIDTH_VW,
)


def _build_artemis_config_script() -> str:
    """
    Emit a <script> block that sets window._artemisConfig from live Python config values.
    Injected into <head> before playback.js loads — do not move below {%css%}.
    """
    cfg = {
        # KPI viz size
        "KPI_SVG_WIDTH":      KPI_SVG_VIEWBOX_WIDTH,
        "KPI_SVG_HEIGHT":     KPI_SVG_VIEWBOX_HEIGHT,
        # Dial geometry
        "DIAL_CY_OFFSET":     DIAL_CY_OFFSET,
        "DIAL_RADIUS":        DIAL_RADIUS,
        "DIAL_ANGLE_MIN":     DIAL_ANGLE_MIN,
        "DIAL_ANGLE_MAX":     DIAL_ANGLE_MAX,
        "DIAL_STROKE_WIDTH":  DIAL_STROKE_WIDTH,
        "DIAL_STROKE_LINECAP": DIAL_STROKE_LINECAP,
        # Sparkline geometry
        "SPARKLINE_WIDTH":    SPARKLINE_WIDTH,
        "SPARKLINE_HEIGHT":   SPARKLINE_HEIGHT,
        "SPARKLINE_PAD_X":    SPARKLINE_PAD_X,
        "SPARKLINE_PAD_Y":    SPARKLINE_PAD_Y,
    }
    return f"<script>window._artemisConfig = {json.dumps(cfg)};</script>"


INDEX_STRING = f"""<!DOCTYPE html>
<html>
<head>
    {{%metas%}}
    <title>Artemis II · Mission Playback</title>

    <!-- Space Mono — monospace throughout -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{GOOGLE_FONTS_URL}" rel="stylesheet">

    <style>
        :root {{
        
            /* ── Side panel ── */
            --side-panel-width:      {SIDE_PANEL_WIDTH}px;
            --side-panel-transition: {SIDE_PANEL_TRANSITION};

            /* ── Surfaces ── */
            --bg-base:            {BG_BASE};
            --panel-bg:           {PANEL_BG};
            --panel-border:       {PANEL_BORDER};

            /* ── Typography ── */
            --font-family:          {FONT_FAMILY};
            --font-primary:         {FONT_PRIMARY};
            --font-dim:             {FONT_DIM};
            --font-size-kpi:        clamp({FONT_SIZE_KPI_MIN}px, {FONT_SIZE_KPI_VW}vw, {FONT_SIZE_KPI_MAX}px);
            --font-size-title:      clamp({FONT_SIZE_TITLE_MIN}px, {FONT_SIZE_TITLE_VW}vw, {FONT_SIZE_TITLE_MAX}px);
            --font-size-label:      {FONT_SIZE_LABEL}px;
            --font-size-header:     {FONT_SIZE_HEADER}px;
            --font-size-status:     {FONT_SIZE_STATUS}px;
            --font-size-tooltip:    {FONT_SIZE_TOOLTIP}px;
            --font-size-side-panel: {FONT_SIZE_SIDE_PANEL}px;

            /* ── Status ── */
            --status-live:        {STATUS_LIVE};

            /* ── Panel accents ── */
            --accent-vectors:     {ACCENT_VECTORS};
            --accent-trajectory:  {ACCENT_TRAJECTORY};
            --accent-gravity:     {ACCENT_GRAVITY};
            --accent-range:       {ACCENT_RANGE};

            /* ── Layout ── */
            --home-media-height:   {HOME_MEDIA_ROW_HEIGHT}px;
            --home-crew-height:    {HOME_CREW_CARD_HEIGHT}px;
            --header-brand-h:      {HEADER_BRAND_HEIGHT}px;
            --traj-h:              {TRAJECTORY_HEIGHT}px;
            --scrubber-h:          {SCRUBBER_HEIGHT}px;
            --scrubber-radius:     {SCRUBBER_BORDER_RADIUS}px;
            --scrubber-h-margin:   {SCRUBBER_HORIZONTAL_MARGIN}px;
            --scrubber-dot:        {SCRUBBER_DOT_SIZE}px;
            --telem-h:             {TELEMETRY_HEIGHT}px;
            --panel-radius:        {PANEL_BORDER_RADIUS}px;
            --panel-gap:           clamp({PANEL_GAP_MIN}px, {PANEL_GAP_VW}vw, {PANEL_GAP_MAX}px);
            --panel-padding:       clamp({PANEL_PADDING_MIN}px, {PANEL_PADDING_VW}vw, {PANEL_PADDING_MAX}px);
            --sparkline-h:         {SPARKLINE_HEIGHT}px;

            /* ── Trajectory colors (for CSS-side use) ── */
            --color-trajectory:     {COLOR_TRAJECTORY};
            --color-trajectory-dim: {COLOR_TRAJECTORY_DIM};

            /* ── Playback ── */
            --playback-btn-size:      {PLAYBACK_BTN_SIZE}px;
            --playback-btn-font-size: {PLAYBACK_BTN_FONT_SIZE}px;

            /* ── Dashboard bounds ── */
            --dashboard-width:    clamp({DASHBOARD_WIDTH_MIN}px, {DASHBOARD_WIDTH_VW}vw, {DASHBOARD_WIDTH_MAX}px);
        }}
    </style>

    {_build_artemis_config_script()}
    {{%css%}}

</head>
<body>
    {{%app_entry%}}
    <footer>
        {{%config%}}
        {{%scripts%}}
        {{%renderer%}}
    </footer>
</body>
</html>
"""