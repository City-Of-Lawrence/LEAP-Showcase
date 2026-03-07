"""qr_render.py

QR code rendering + SVG branding utilities for the UPIN system.

Design goals:
- No database access.
- Pure rendering: inputs -> SVG text.
- Safe defaults for scannability (logo knockout + optional debug crosshair).
"""

import os
import base64
import re
import segno


FUEL_COLORS = {
    "gas": "black",
    "oil": "brown",
    "electric": "blue",
}

# --------------------------------------------------
# Debug overlay controls (safe for QR scannability)
# --------------------------------------------------

DEBUG_SEAL_CROSSHAIR = True        # center crosshair inside white box
DEBUG_SEAL_BOX_OUTLINE = False     # outline the white box (optional)

DEBUG_CROSSHAIR_OPACITY = 0.35     # 0.25–0.45 works well
DEBUG_CROSSHAIR_STROKE_WIDTH = 1.0



ENABLE_QR_BRANDING = True
CITY_SEAL_SVG = "CoLSeal.svg"   # keep alongside this script

# logo sizing (fractions of QR size)
LOGO_SCALE = 0.20       # 0.18–0.22 is usually safest for scanners
LOGO_PAD_SCALE = 0.05   # white padding around logo
LOGO_BG_ROUNDED = 8     # rounding for the white knockout box



# Seal fill / zoom (dimensionless multipliers)
SEAL_FILL_MULT_X = 1.50
SEAL_FILL_MULT_Y = 1.30

# Bias in SVG user-units
# Positive X moves RIGHT; positive Y moves DOWN.
SEAL_X_BIAS_UNITS = 5.0
SEAL_Y_BIAS_UNITS = 2.5  # Moves up 

def _ensure_svg_xmlns(svg_text: str) -> str:
    """
    Ensure the root <svg> tag includes:
      xmlns="http://www.w3.org/2000/svg"
    """
    m = re.search(r"<svg\b[^>]*>", svg_text)
    if not m:
        return svg_text

    svg_tag = m.group(0)

    # If xmlns is already present, do nothing
    if re.search(r'\sxmlns\s*=\s*"', svg_tag):
        return svg_text

    fixed_tag = svg_tag.replace(
        "<svg",
        '<svg xmlns="http://www.w3.org/2000/svg"',
        1
    )
    return svg_text.replace(svg_tag, fixed_tag, 1)


def _ensure_svg_namespace_and_viewbox(svg_text: str) -> str:
    """
    Ensure SVG has xmlns and a viewBox so it renders consistently across viewers.
    Also adds crispEdges to improve print sharpness.
    """
    svg_text = _ensure_svg_xmlns(svg_text)

    # Add viewBox if missing (based on width/height if present)
    m = re.search(r"<svg\b[^>]*>", svg_text)
    if not m:
        return svg_text

    svg_tag = m.group(0)

    if "viewBox=" not in svg_tag:
        mw = re.search(r'width="([\d.]+)', svg_tag)
        mh = re.search(r'height="([\d.]+)', svg_tag)
        if mw and mh:
            w = mw.group(1)
            h = mh.group(1)
            fixed_tag = svg_tag.replace(
                "<svg",
                f'<svg viewBox="0 0 {w} {h}"',
                1
            )
            svg_text = svg_text.replace(svg_tag, fixed_tag, 1)
            svg_tag = re.search(r"<svg\b[^>]*>", svg_text).group(0)

    # Add crispEdges if not present
    if "shape-rendering=" not in svg_tag:
        fixed_tag = svg_tag.replace("<svg", '<svg shape-rendering="crispEdges"', 1)
        svg_text = svg_text.replace(svg_tag, fixed_tag, 1)

    return svg_text


def get_svg_canvas_size(svg_text: str):
    """
    Return (w, h) from viewBox or width/height.
    """
    m = re.search(r'viewBox="[-\d.]+\s+[-\d.]+\s+([0-9.]+)\s+([0-9.]+)"', svg_text)
    if m:
        return float(m.group(1)), float(m.group(2))

    mw = re.search(r'width="([0-9.]+)', svg_text)
    mh = re.search(r'height="([0-9.]+)', svg_text)
    if mw and mh:
        return float(mw.group(1)), float(mh.group(1))

    return 265.0, 265.0


def _read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _svg_bytes_to_data_uri(svg_bytes: bytes) -> str:
    # Strip XML + DOCTYPE for fewer viewer quirks when embedded
    txt = svg_bytes.decode("utf-8", errors="replace")
    txt = re.sub(r"<\?xml[^>]*\?>\s*", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<!DOCTYPE[^>]*>\s*", "", txt, flags=re.IGNORECASE)
    b = txt.encode("utf-8")
    return "data:image/svg+xml;base64," + base64.b64encode(b).decode("ascii")


def add_city_seal_overlay(svg_text: str, seal_svg_path: str = CITY_SEAL_SVG) -> str:
    if not ENABLE_QR_BRANDING:
        return svg_text
    if not seal_svg_path or not os.path.exists(seal_svg_path):
        return svg_text

    svg_text = _ensure_svg_namespace_and_viewbox(svg_text)

    w, h = get_svg_canvas_size(svg_text)
    size = min(w, h)

    # White knockout square (behind seal)
    bg_size = size * LOGO_SCALE
    pad = size * LOGO_PAD_SCALE
    box = bg_size + 2 * pad

    x = (w - box) / 2.0
    y = (h - box) / 2.0

    # Center of the white box (for crosshair)
    cx = x + (box / 2.0)
    cy = y + (box / 2.0)

    # Seal as embedded SVG image (data URI)
    seal_uri = _svg_bytes_to_data_uri(_read_file_bytes(seal_svg_path))

    # Zoom the seal image inside the box, then clip to box
    seal_box_w = box * SEAL_FILL_MULT_X
    seal_box_h = box * SEAL_FILL_MULT_Y
    dx = (seal_box_w - box) / 2.0
    dy = (seal_box_h - box) / 2.0

    # Bias in absolute SVG units
    image_x = (x - dx) + SEAL_X_BIAS_UNITS
    image_y = (y - dy) + SEAL_Y_BIAS_UNITS

    # Optional debug marks (kept inside the white box)
    debug_box = ""
    debug_crosshair = ""

    if DEBUG_SEAL_BOX_OUTLINE:
        debug_box = (
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{box:.2f}" height="{box:.2f}" '
            f'fill="none" stroke="gray" stroke-width="{DEBUG_CROSSHAIR_STROKE_WIDTH:.1f}" '
            f'opacity="{DEBUG_CROSSHAIR_OPACITY:.2f}"/>'
        )

    if DEBUG_SEAL_CROSSHAIR:
        debug_crosshair = (
            f'<line x1="{cx:.2f}" y1="{y:.2f}" x2="{cx:.2f}" y2="{(y + box):.2f}" '
            f'stroke="gray" stroke-width="{DEBUG_CROSSHAIR_STROKE_WIDTH:.1f}" '
            f'opacity="{DEBUG_CROSSHAIR_OPACITY:.2f}"/>'
            f'<line x1="{x:.2f}" y1="{cy:.2f}" x2="{(x + box):.2f}" y2="{cy:.2f}" '
            f'stroke="gray" stroke-width="{DEBUG_CROSSHAIR_STROKE_WIDTH:.1f}" '
            f'opacity="{DEBUG_CROSSHAIR_OPACITY:.2f}"/>'
        )

    overlay = f"""
  <g id="city_seal_overlay">
    <defs>
      <clipPath id="seal_clip">
        <rect x="{x:.2f}" y="{y:.2f}" width="{box:.2f}" height="{box:.2f}"
              rx="{LOGO_BG_ROUNDED}" ry="{LOGO_BG_ROUNDED}" />
      </clipPath>
    </defs>

    <!-- White knockout -->
    <rect x="{x:.2f}" y="{y:.2f}" width="{box:.2f}" height="{box:.2f}"
          rx="{LOGO_BG_ROUNDED}" ry="{LOGO_BG_ROUNDED}" fill="white"/>

    <!-- Debug overlay (optional) -->
    {debug_box}
    {debug_crosshair}

    <!-- Seal -->
    <image x="{image_x:.2f}" y="{image_y:.2f}"
           width="{seal_box_w:.2f}" height="{seal_box_h:.2f}"
           href="{seal_uri}"
           preserveAspectRatio="xMidYMid slice"
           clip-path="url(#seal_clip)"/>
  </g>
"""
    return svg_text.replace("</svg>", overlay + "\n</svg>", 1)





def generate_qr_svg(data_string, fuel_type, vision_id, lean_eligibility=None):
    """
    Generate SVG markup for a QR code.
    - Overall QR "dots" are colored by fuel_type (black/brown/blue).
    - Finder squares are:
        * green if lean_eligibility == 'LEAN'
        * red   if lean_eligibility == 'LMF'
        * otherwise same as main data color.
    """
    cleaned_fuel = (fuel_type or "").strip().lower()
    cleaned_lean = (lean_eligibility or "").strip().upper()
    fill_color = FUEL_COLORS.get(cleaned_fuel, "black")
    background_color = "white"
    finder_color = fill_color
    if cleaned_lean == "LEAN":
        finder_color = "green"
    elif cleaned_lean == "LMF":
        finder_color = "red"
    qr = segno.make(f"https://gis.vgsi.com/lawrencema/Parcel.aspx?Pid={vision_id}", error='h')
    svg = qr.svg_inline(
    scale=5,
    border=8,                 # keep 8 (this solved the chopped finder issue)
    dark=fill_color,
    light=background_color,
    finder_dark=finder_color,
    )

    svg = _ensure_svg_namespace_and_viewbox(svg)
    svg = add_city_seal_overlay(svg)
    return svg

   
# -------------------------------------------------------------------
# QR export / regeneration
# -------------------------------------------------------------------
