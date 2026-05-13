# app/themes.py
#
# Theme definitions for the Artemis II Mission Dashboard.
#
# Structure:
#   Each theme is built by a private function using three internal color
#   buckets (surface, accent, viz). Only semantic tokens leave the builder
#   via the returned dict. Nothing outside themes.py reads the raw buckets.
#
#   surface — neutrals: backgrounds, borders, text scale
#   accent  — six named palette slots (accent_a → accent_f)
#   viz     — space-environment and trajectory rendering colors
#
# To add a theme: write a _build_<name>_theme() function, register it in
# THEMES, and change ACTIVE_THEME_NAME. No other files need to change.


def _build_dark_theme() -> dict:

    # ── Palette (internal — never referenced outside this builder) ─────

    surface = {
        "page":   "#050a0f",   # near-black deep-space background
        "panel":  "#0a1628",   # dark navy panel fill
        "border": "#1a2f4a",   # mid-navy panel border
        "grid":   "#0f1f35",   # subtle grid line — between bg and border
    }

    text = {
        "hi":   "#c8e8ff",   # primary — light blue-white
        "mid":  "#578fb5",   # secondary — muted steel blue
        "lo":   "#2d5473",   # tertiary — dim steel blue
        "hint": "#1e3a52",   # near-invisible — structural hints only
    }

    status = {
        "live": "#22c55e",   # green — nominal / live indicator
    }

    accent = {
        "teal":         "#00f5ab",   # accent_a
        "cyan":         "#00c3ff",   # accent_b
        "violet":       "#786afb",   # accent_c
        "amber":        "#f5ce0b",   # accent_d
        "blue_mid":     "#5082b4",   # accent_e — future arc glow base
        "blue_bright":  "#3473e8",   # accent_f — future arc core base
        "blood_orange": "#e8420a",   # accent_g
        "blue_silver":  "#82a0bc",   # accent_h
    }

    viz = {
        "space_bg":  "#000000",   # pure black — canvas behind SVG starfield
        "path":      "#ffffff",   # past trajectory arc
        "path_dim":  "#2a3f5f",   # ghost / dimmed arc tint
        "earth":     "#1e90ff",   # Earth sphere fill
        "moon":      "#b0b0b0",   # Moon sphere fill
        "starfield": "#ffffff",   # star dot color
        "marker":    "#ffffff",   # Orion spacecraft position dot
    }

    # ── Exported token dict ────────────────────────────────────────────

    return {

        # Surfaces
        "page_bg":      surface["page"],
        "panel_bg":     surface["panel"],
        "panel_border": surface["border"],

        # Typography — font choice is a theme decision
        "font_family":  "'Space Mono', monospace",

        # Text scale
        "text_hi":   text["hi"],
        "text_mid":  text["mid"],
        "text_lo":   text["lo"],
        "text_hint": text["hint"],

        # Status
        "status_live": status["live"],

        # Chart support
        "chart_grid":    surface["grid"],
        "chart_plot_bg": "rgba(0,0,0,0)",   # CSS owns the panel layer

        # Accent palette — named by slot, not by dashboard role.
        # config.py maps slots to semantic names (ACCENT_VECTORS = T["accent_a"]).
        # A future dashboard reuses this theme and remaps the slots freely.
        "accent_a": accent["teal"],
        "accent_b": accent["cyan"],
        "accent_c": accent["violet"],
        "accent_d": accent["amber"],
        "accent_e": accent["blue_mid"],
        "accent_f": accent["blue_bright"],
        "accent_g": accent["blood_orange"],
        "accent_h": accent["blue_silver"],

        # Viz — space environment & trajectory rendering
        "space_bg":       viz["space_bg"],
        "viz_path":       viz["path"],
        "viz_path_dim":   viz["path_dim"],
        "viz_body_earth": viz["earth"],
        "viz_body_moon":  viz["moon"],
        "viz_starfield":  viz["starfield"],
        "viz_marker":     viz["marker"],

        # Arc color aliases — same values as accent_e/f; named explicitly
        # so the intent is readable here without chasing the slot mapping.
        "arc_future_glow": accent["blue_mid"],
        "arc_future_core": accent["blue_bright"],
    }


# ── Registry ──────────────────────────────────────────────────────────────

THEMES = {
    "dark": _build_dark_theme(),
}

ACTIVE_THEME_NAME = "dark"
ACTIVE_THEME      = THEMES[ACTIVE_THEME_NAME]
THEME_DARK        = THEMES["dark"]   # direct alias used by config.py