# app/index_string.py
#
# Custom Dash index_string that injects CSS custom properties and the
# Google Fonts <link> into <head>. Dash replaces its default HTML shell
# with this string — the {%...%} placeholders are required by Dash.



from app.config import (
    # Surfaces
    BG_BASE, PANEL_BG, PANEL_BORDER,
    # Typography
    FONT_PRIMARY, FONT_DIM, FONT_FAMILY, GOOGLE_FONTS_URL,
    FONT_SIZE_KPI, FONT_SIZE_LABEL, FONT_SIZE_HEADER, FONT_SIZE_STATUS,
    # Status
    STATUS_LIVE,
    # Accents
    ACCENT_VECTORS, ACCENT_TRAJECTORY, ACCENT_GRAVITY, ACCENT_RANGE,
    # Layout
    HEADER_BRAND_HEIGHT, HEADER_STATUS_HEIGHT,
    TRAJECTORY_MIN_HEIGHT,
    SCRUBBER_HEIGHT, SCRUBBER_BORDER_RADIUS, SCRUBBER_HORIZONTAL_MARGIN,
    SCRUBBER_DOT_SIZE, SCRUBBER_DOT_ACTIVE,
    TELEMETRY_MIN_HEIGHT, PANEL_BORDER_RADIUS, PANEL_GAP, PANEL_PADDING,
    SPARKLINE_HEIGHT,
    # Trajectory viz
    COLOR_TRAJECTORY, COLOR_TRAJECTORY_DIM,
    # Playback
    PLAYBACK_BTN_SIZE, PLAYBACK_BTN_FONT_SIZE,
)



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
            /* ── Surfaces ── */
            --bg-base:            {BG_BASE};
            --panel-bg:           {PANEL_BG};
            --panel-border:       {PANEL_BORDER};

            /* ── Typography ── */
            --font-family:        {FONT_FAMILY};
            --font-primary:       {FONT_PRIMARY};
            --font-dim:           {FONT_DIM};
            --font-size-kpi:      {FONT_SIZE_KPI}px;
            --font-size-label:    {FONT_SIZE_LABEL}px;
            --font-size-header:   {FONT_SIZE_HEADER}px;
            --font-size-status:   {FONT_SIZE_STATUS}px;

            /* ── Status ── */
            --status-live:        {STATUS_LIVE};

            /* ── Panel accents ── */
            --accent-vectors:     {ACCENT_VECTORS};
            --accent-trajectory:  {ACCENT_TRAJECTORY};
            --accent-gravity:     {ACCENT_GRAVITY};
            --accent-range:       {ACCENT_RANGE};

            /* ── Layout ── */
            --header-brand-h:      {HEADER_BRAND_HEIGHT}px;
            --header-status-h:     {HEADER_STATUS_HEIGHT}px;
            --traj-min-h:          {TRAJECTORY_MIN_HEIGHT}px;
            --scrubber-h:          {SCRUBBER_HEIGHT}px;
            --scrubber-radius:     {SCRUBBER_BORDER_RADIUS}px;
            --scrubber-h-margin:   {SCRUBBER_HORIZONTAL_MARGIN}px;
            --scrubber-dot:        {SCRUBBER_DOT_SIZE}px;
            --scrubber-dot-active: {SCRUBBER_DOT_ACTIVE}px;
            --telem-min-h:         {TELEMETRY_MIN_HEIGHT}px;
            --panel-radius:        {PANEL_BORDER_RADIUS}px;
            --panel-gap:           {PANEL_GAP}px;
            --panel-padding:       {PANEL_PADDING}px;
            --sparkline-h:         {SPARKLINE_HEIGHT}px;

            /* ── Trajectory colors (for CSS-side use) ── */
            --color-trajectory:     {COLOR_TRAJECTORY};
            --color-trajectory-dim: {COLOR_TRAJECTORY_DIM};
            
            /* Playback */
            --playback-btn-size:      {PLAYBACK_BTN_SIZE}px;
            --playback-btn-font-size: {PLAYBACK_BTN_FONT_SIZE}px;

            /* ── Dashboard bounds ── */
            --dashboard-max-w:    1400px;
        }}
    </style>

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