"""Lailara Design System v2 — color and typography constants.

Adapted from competitive-shelf-intelligence/app/constants.py.
Added SG_ORANGE, TOKYO_ROSE, and dark callout card tokens.
"""

from __future__ import annotations

# ============================================================
# Canvas and London greyscale
# ============================================================
CANVAS      = "#f5f3ee"   # London-100 warmed — page background
INK         = "#0d0d0d"   # London-5 — chart titles, primary headings
TEXT        = "#333333"   # London-20 — body text
TEXT_SEC    = "#595959"   # London-35 — axis text, subtitles, labels
REFERENCE   = "#666666"   # London-40 — median / benchmark lines
GREY_LIGHT  = "#d9d9d9"   # London-85 — gridlines, borders
WHITE       = "#ffffff"

# ============================================================
# Brand red (text and 1px rules only — never background fill)
# ============================================================
RED         = "#cc100a"   # Red-42

# ============================================================
# Chicago — accent blue
# ============================================================
CHICAGO     = "#1f2e7a"   # Chicago-20 — primary button, chart anchor
CHICAGO_LT  = "#8e9ad0"   # Chicago-70 — chart light pair

# ============================================================
# Hong Kong sequential teal (magnitude-ranked data)
# ============================================================
TEAL        = "#158f75"   # HK-35 — Lailara default teal
HK_DARK     = "#0a5c4b"   # HK-15
HK_LIGHT    = "#6dcdb5"   # HK-70

# ============================================================
# Singapore (orange) — warning signal
# ============================================================
SG_ORANGE   = "#ee8a2a"   # SG-55 — warnings, alert icons

# ============================================================
# Tokyo (berry/rose) — risk and negative signal
# ============================================================
TOKYO_ROSE  = "#b82d4a"   # Tokyo-40 — risk, severity, deadline critical

# ============================================================
# Deadline flag colors
# ============================================================
DEADLINE_PAST_DUE = "#7a0906"   # deep red — text on fail surface
DEADLINE_CRITICAL = TOKYO_ROSE  # < 14 days
DEADLINE_WARNING  = SG_ORANGE   # 14–28 days
DEADLINE_OK       = TEAL        # > 28 days or no stockout

# ============================================================
# Deadline flag surface fills (backgrounds — never data bars)
# ============================================================
SURFACE_FAIL    = "#fde8e7"   # Red surface
SURFACE_WARN    = "#fdeee0"   # SG-95
SURFACE_PASS    = "#e4f5f0"   # HK-95

# ============================================================
# Dark callout card
# ============================================================
CARD_BG     = "#1a1a1a"              # London-10
CARD_TEXT   = "#ffffff"
CARD_SEC    = "#d8d8d8"
CARD_MUTED  = "#9a9a9a"
CARD_BORDER = "rgba(255,255,255,0.12)"
CARD_ITEM   = "#ededed"

# ============================================================
# Typography
# ============================================================
FONT_SERIF  = "'Playfair Display', Georgia, 'Times New Roman', serif"
FONT_SANS   = "'Source Sans 3', 'Source Sans Pro', 'Helvetica Neue', Helvetica, Arial, sans-serif"

# ============================================================
# Categorical chart palette
# ============================================================
CHART_PALETTE = [
    "#1f2e7a",  # Chicago-20
    "#0c6552",  # HK-20
    "#7e1f34",  # Tokyo-20
    "#7a3d10",  # SG-20
    "#8e0b07",  # Red-20
    "#8e9ad0",  # Chicago-70
    "#6dcdb5",  # HK-70
    "#e68a9a",  # Tokyo-70
]
