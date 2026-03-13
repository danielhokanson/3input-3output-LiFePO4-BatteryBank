#!/usr/bin/env python3
"""
Generate spacer drawings for the Satellite Unit foam cavity (Rev 3.2).

Spacers bridge the 30mm foam gap between Shell 1 (ASA outer) and Shell 2
(PETG structural), keeping Shell 2 centered during the PU foam pour and
preventing foam expansion from distorting the walls.

Two spacer types:
  - Corner spacers: L-shaped blocks at each corner with M4 through-bolt holes
  - Mid-wall spacers: flat rectangular blocks along walls

Produces DXF and SVG drawings.

Usage:
    python cad/satellite_unit/generate_spacers.py

Output:
    cad/satellite_unit/spacers/1_spacer_plan.dxf        + .svg
    cad/satellite_unit/spacers/2_spacer_cross_section.dxf + .svg
    cad/satellite_unit/spacers/3_corner_spacer_detail.dxf + .svg
    cad/satellite_unit/spacers/4_midwall_spacer_detail.dxf + .svg
"""

import os
import ezdxf
from ezdxf.enums import TextEntityAlignment

# ---------------------------------------------------------------------------
# SHARED PARAMETRIC DIMENSIONS (must match generate_dxf.py)
# ---------------------------------------------------------------------------

CELL_L = 129.0
CELL_W = 36.0
CELL_H = 256.0
TERMINAL_H = 4.0

CELLS_S = 4
CELLS_P = 1

STACK_W = CELLS_S * CELL_W + (CELLS_S - 1) * 2 + 8
STACK_D = CELL_L + 10.0
STACK_H = CELL_H + TERMINAL_H + 30.0

THERM_W = 70.0
THERM_D = STACK_D
THERM_H = STACK_H

WALL = 5.0
WALL_S2 = 5.0
FOAM = 30.0
ZONE_GAP = 15.0
ZONE_MARGIN = 10.0
BASE_THICK = WALL

M4_HOLE = 4.5

# Derived shell dimensions
INNER_W = 2 * ZONE_MARGIN + STACK_W + ZONE_GAP + THERM_W
INNER_D = max(STACK_D, THERM_D) + 2 * ZONE_MARGIN
INNER_H = max(STACK_H, THERM_H) + BASE_THICK

MID_W = INNER_W + 2 * WALL_S2
MID_D = INNER_D + 2 * WALL_S2
MID_H = INNER_H + WALL_S2

OUTER_W = MID_W + 2 * (FOAM + WALL)
OUTER_D = MID_D + 2 * (FOAM + WALL)
OUTER_H = MID_H + FOAM + WALL + BASE_THICK

# ---------------------------------------------------------------------------
# SPACER PARAMETERS
# ---------------------------------------------------------------------------

CORNER_LEG = 25.0       # shorter legs for smaller unit
CORNER_THICK = 12.0
SPACER_DEPTH = FOAM     # 30mm
SPACER_H = 25.0

MIDWALL_W = 25.0        # slightly narrower for smaller unit
MIDWALL_THICK = FOAM
MIDWALL_H = SPACER_H

MIDWALL_SPACING = 120.0

SPACER_Z1 = MID_H * 0.30
SPACER_Z2 = MID_H * 0.65

CLAMP_HOLE = M4_HOLE

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spacers")

# ---------------------------------------------------------------------------
# LAYER DEFINITIONS
# ---------------------------------------------------------------------------

LAYERS = {
    "SHELL_1":     {"color": 1},
    "SHELL_2":     {"color": 3},
    "FOAM_CAVITY": {"color": 40},
    "SPACERS":     {"color": 6},
    "FASTENERS":   {"color": 2},
    "DIMENSIONS":  {"color": 7},
    "ANNOTATIONS": {"color": 7},
}


def setup_doc():
    doc = ezdxf.new("R2010")
    for name, props in LAYERS.items():
        doc.layers.add(name, color=props["color"])
    return doc


def add_rect(msp, x, y, w, h, layer):
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    msp.add_lwpolyline(pts, dxfattribs={"layer": layer})


def add_circle(msp, cx, cy, r, layer):
    msp.add_circle((cx, cy), r, dxfattribs={"layer": layer})


def add_label(msp, x, y, text, layer="ANNOTATIONS", height=4):
    msp.add_text(
        text, height=height, dxfattribs={"layer": layer}
    ).set_placement((x, y), align=TextEntityAlignment.BOTTOM_LEFT)


# ---------------------------------------------------------------------------
# SPACER POSITION CALCULATIONS
# ---------------------------------------------------------------------------

def corner_spacer_positions():
    hw = MID_W / 2
    hd = MID_D / 2
    return [
        (-hw, -hd, (-1, -1)),
        ( hw, -hd, ( 1, -1)),
        ( hw,  hd, ( 1,  1)),
        (-hw,  hd, (-1,  1)),
    ]


def midwall_spacer_positions():
    hw = MID_W / 2
    hd = MID_D / 2
    positions = []

    # Along W axis (top and bottom walls)
    usable_w = MID_W - 2 * CORNER_LEG
    n_w = max(1, round(usable_w / MIDWALL_SPACING))
    for i in range(n_w):
        x = -hw + CORNER_LEG + (i + 0.5) * usable_w / n_w
        positions.append((x,  hd, "h"))
        positions.append((x, -hd, "h"))

    # Along D axis (left and right walls) — satellite is narrow, may get 0-1
    usable_d = MID_D - 2 * CORNER_LEG
    n_d = max(0, round(usable_d / MIDWALL_SPACING))
    for i in range(n_d):
        y = -hd + CORNER_LEG + (i + 0.5) * usable_d / n_d
        positions.append((-hw, y, "v"))
        positions.append(( hw, y, "v"))

    return positions


# ---------------------------------------------------------------------------
# SVG HELPERS
# ---------------------------------------------------------------------------

SVG_COLORS = {
    "SHELL_1": "#ff4444",
    "SHELL_2": "#44cc44",
    "FOAM_CAVITY": "#ff8800",
    "SPACERS": "#cc44cc",
    "FASTENERS": "#cccc44",
    "DIMENSIONS": "#cccccc",
    "ANNOTATIONS": "#cccccc",
}


def svg_header(width, height, viewbox):
    vb = f"{viewbox[0]} {viewbox[1]} {viewbox[2]} {viewbox[3]}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="{vb}">\n'
        f'<rect x="{viewbox[0]}" y="{viewbox[1]}" '
        f'width="{viewbox[2]}" height="{viewbox[3]}" fill="#1a1a1a"/>\n'
    )


def svg_rect(x, y, w, h, color, fill="none"):
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'stroke="{color}" stroke-width="0.8" fill="{fill}"/>\n'
    )


def svg_circle(cx, cy, r, color):
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
        f'stroke="{color}" stroke-width="0.6" fill="none"/>\n'
    )


def svg_text(x, y, text, color="#cccccc", size=5):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" '
        f'font-family="monospace" font-size="{size}">{text}</text>\n'
    )


def svg_footer():
    return "</svg>\n"


# ---------------------------------------------------------------------------
# DRAWING 1: Spacer Plan View
# ---------------------------------------------------------------------------

def generate_spacer_plan():
    doc = setup_doc()
    msp = doc.modelspace()

    add_rect(msp, -OUTER_W / 2, -OUTER_D / 2, OUTER_W, OUTER_D, "SHELL_1")
    s1i_w = OUTER_W - 2 * WALL
    s1i_d = OUTER_D - 2 * WALL
    add_rect(msp, -s1i_w / 2, -s1i_d / 2, s1i_w, s1i_d, "SHELL_1")
    add_rect(msp, -MID_W / 2, -MID_D / 2, MID_W, MID_D, "SHELL_2")

    for cx, cy, (sx, sy) in corner_spacer_positions():
        hleg_x = cx - (CORNER_LEG if sx > 0 else 0)
        hleg_y = cy - (CORNER_THICK if sy > 0 else 0)
        add_rect(msp, hleg_x, hleg_y, CORNER_LEG, CORNER_THICK, "SPACERS")

        vleg_x = cx - (CORNER_THICK if sx > 0 else 0)
        vleg_y = cy - (CORNER_LEG if sy > 0 else 0)
        add_rect(msp, vleg_x, vleg_y, CORNER_THICK, CORNER_LEG, "SPACERS")

        bolt_cx = cx - sx * CORNER_THICK / 2
        bolt_cy = cy - sy * CORNER_THICK / 2
        add_circle(msp, bolt_cx, bolt_cy, CLAMP_HOLE / 2, "FASTENERS")

    for cx, cy, orient in midwall_spacer_positions():
        if orient == "h":
            sy = 1 if cy > 0 else -1
            sy_off = 0 if sy < 0 else -FOAM
            add_rect(msp, cx - MIDWALL_W / 2, cy + sy_off, MIDWALL_W, FOAM, "SPACERS")
        else:
            sx = 1 if cx > 0 else -1
            sx_off = 0 if sx < 0 else -FOAM
            add_rect(msp, cx + sx_off, cy - MIDWALL_W / 2, FOAM, MIDWALL_W, "SPACERS")

    corners = corner_spacer_positions()
    midwalls = midwall_spacer_positions()
    add_label(msp, -OUTER_W / 2 + 5, -OUTER_D / 2 - 15,
              f"SPACER PLAN — foam cavity  |  Z levels: {SPACER_Z1:.0f} & {SPACER_Z2:.0f}mm",
              height=4)
    add_label(msp, -OUTER_W / 2 + 5, -OUTER_D / 2 - 25,
              f"{len(corners)} corner + {len(midwalls)} mid-wall x2 levels = "
              f"{(len(corners) + len(midwalls)) * 2} total",
              height=3)

    filepath = os.path.join(OUTPUT_DIR, "1_spacer_plan.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")

    # --- SVG ---
    margin = 30
    vb_x = -OUTER_W / 2 - margin
    vb_y = -OUTER_D / 2 - margin
    vb_w = OUTER_W + 2 * margin
    vb_h = OUTER_D + 2 * margin + 30
    svg = svg_header(700, 500, (vb_x, vb_y, vb_w, vb_h))

    svg += svg_rect(-OUTER_W / 2, -OUTER_D / 2, OUTER_W, OUTER_D, SVG_COLORS["SHELL_1"])
    svg += svg_rect(-s1i_w / 2, -s1i_d / 2, s1i_w, s1i_d, SVG_COLORS["SHELL_1"])
    svg += svg_rect(-MID_W / 2, -MID_D / 2, MID_W, MID_D, SVG_COLORS["SHELL_2"])

    for cx, cy, (sx, sy) in corner_spacer_positions():
        hleg_x = cx - (CORNER_LEG if sx > 0 else 0)
        hleg_y = cy - (CORNER_THICK if sy > 0 else 0)
        svg += svg_rect(hleg_x, hleg_y, CORNER_LEG, CORNER_THICK,
                        SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
        vleg_x = cx - (CORNER_THICK if sx > 0 else 0)
        vleg_y = cy - (CORNER_LEG if sy > 0 else 0)
        svg += svg_rect(vleg_x, vleg_y, CORNER_THICK, CORNER_LEG,
                        SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
        bolt_cx = cx - sx * CORNER_THICK / 2
        bolt_cy = cy - sy * CORNER_THICK / 2
        svg += svg_circle(bolt_cx, bolt_cy, CLAMP_HOLE / 2, SVG_COLORS["FASTENERS"])

    for cx, cy, orient in midwall_spacer_positions():
        if orient == "h":
            sy = 1 if cy > 0 else -1
            sy_off = 0 if sy < 0 else -FOAM
            svg += svg_rect(cx - MIDWALL_W / 2, cy + sy_off, MIDWALL_W, FOAM,
                            SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.2)")
        else:
            sx = 1 if cx > 0 else -1
            sx_off = 0 if sx < 0 else -FOAM
            svg += svg_rect(cx + sx_off, cy - MIDWALL_W / 2, FOAM, MIDWALL_W,
                            SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.2)")

    svg += svg_text(vb_x + 5, vb_y + vb_h - 8,
                    f"SPACER PLAN — Satellite  |  {len(corners)} corner + {len(midwalls)} mid-wall x2",
                    size=5)
    svg += svg_footer()

    svg_path = os.path.join(OUTPUT_DIR, "1_spacer_plan.svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"  Created: {svg_path}")


# ---------------------------------------------------------------------------
# DRAWING 2: Spacer Cross-Section
# ---------------------------------------------------------------------------

def generate_spacer_cross_section():
    doc = setup_doc()
    msp = doc.modelspace()

    add_rect(msp, -OUTER_W / 2, 0, OUTER_W, OUTER_H, "SHELL_1")
    add_rect(msp, -OUTER_W / 2 + WALL, BASE_THICK,
             OUTER_W - 2 * WALL, OUTER_H - WALL - BASE_THICK, "FOAM_CAVITY")

    s2_x = -MID_W / 2
    s2_y = BASE_THICK + FOAM
    add_rect(msp, s2_x, s2_y, MID_W, MID_H, "SHELL_2")

    for z in [SPACER_Z1, SPACER_Z2]:
        spacer_y = s2_y + z - SPACER_H / 2

        left_x = -OUTER_W / 2 + WALL
        add_rect(msp, left_x, spacer_y, FOAM, SPACER_H, "SPACERS")
        add_circle(msp, left_x + FOAM / 2, spacer_y + SPACER_H / 2,
                   CLAMP_HOLE / 2, "FASTENERS")

        right_x = OUTER_W / 2 - WALL - FOAM
        add_rect(msp, right_x, spacer_y, FOAM, SPACER_H, "SPACERS")
        add_circle(msp, right_x + FOAM / 2, spacer_y + SPACER_H / 2,
                   CLAMP_HOLE / 2, "FASTENERS")

    z1_y = s2_y + SPACER_Z1
    z2_y = s2_y + SPACER_Z2
    add_label(msp, OUTER_W / 2 + 5, z1_y, f"Z1={SPACER_Z1:.0f}", "DIMENSIONS", height=3)
    add_label(msp, OUTER_W / 2 + 5, z2_y, f"Z2={SPACER_Z2:.0f}", "DIMENSIONS", height=3)

    add_label(msp, -OUTER_W / 2, -12,
              "FRONT CROSS-SECTION — spacers in foam cavity", height=4)

    filepath = os.path.join(OUTPUT_DIR, "2_spacer_cross_section.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")

    # --- SVG ---
    margin = 30
    vb_x = -OUTER_W / 2 - margin
    vb_y = -margin
    vb_w = OUTER_W + 2 * margin
    vb_h = OUTER_H + 2 * margin
    svg = svg_header(700, 500, (vb_x, vb_y, vb_w, vb_h))

    svg += svg_rect(-OUTER_W / 2, 0, OUTER_W, OUTER_H, SVG_COLORS["SHELL_1"])
    svg += svg_rect(-OUTER_W / 2 + WALL, BASE_THICK,
                    OUTER_W - 2 * WALL, OUTER_H - WALL - BASE_THICK,
                    SVG_COLORS["FOAM_CAVITY"], fill="rgba(255,136,0,0.1)")
    svg += svg_rect(s2_x, s2_y, MID_W, MID_H, SVG_COLORS["SHELL_2"])

    for z in [SPACER_Z1, SPACER_Z2]:
        spacer_y = s2_y + z - SPACER_H / 2
        left_x = -OUTER_W / 2 + WALL
        right_x = OUTER_W / 2 - WALL - FOAM
        svg += svg_rect(left_x, spacer_y, FOAM, SPACER_H,
                        SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.4)")
        svg += svg_rect(right_x, spacer_y, FOAM, SPACER_H,
                        SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.4)")
        svg += svg_circle(left_x + FOAM / 2, spacer_y + SPACER_H / 2,
                          CLAMP_HOLE / 2, SVG_COLORS["FASTENERS"])
        svg += svg_circle(right_x + FOAM / 2, spacer_y + SPACER_H / 2,
                          CLAMP_HOLE / 2, SVG_COLORS["FASTENERS"])

    svg += svg_text(vb_x + 5, vb_y + vb_h - 8,
                    "CROSS-SECTION — spacers in foam cavity", size=5)
    svg += svg_footer()

    svg_path = os.path.join(OUTPUT_DIR, "2_spacer_cross_section.svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"  Created: {svg_path}")


# ---------------------------------------------------------------------------
# DRAWING 3: Corner Spacer Detail
# ---------------------------------------------------------------------------

def generate_corner_spacer_detail():
    doc = setup_doc()
    msp = doc.modelspace()

    ox, oy = 0, 0
    add_rect(msp, ox, oy, CORNER_LEG, CORNER_THICK, "SPACERS")
    add_rect(msp, ox, oy, CORNER_THICK, CORNER_LEG, "SPACERS")
    add_circle(msp, ox + CORNER_THICK / 2, oy + CORNER_THICK / 2,
               CLAMP_HOLE / 2, "FASTENERS")

    add_label(msp, ox, oy - 8, f"{CORNER_LEG:.0f}", "DIMENSIONS", height=3)
    add_label(msp, ox + CORNER_LEG + 3, oy + CORNER_THICK / 2 - 2,
              f"{CORNER_THICK:.0f}", "DIMENSIONS", height=3)
    add_label(msp, ox - 8, oy + CORNER_LEG / 2, f"{CORNER_LEG:.0f}", "DIMENSIONS", height=3)
    add_label(msp, ox, oy + CORNER_LEG + 10, "PLAN VIEW", height=4)

    sx, sy = CORNER_LEG + 50, 0
    add_rect(msp, sx, sy, CORNER_LEG, SPACER_H, "SPACERS")
    add_circle(msp, sx + CORNER_THICK / 2, sy + SPACER_H / 2,
               CLAMP_HOLE / 2, "FASTENERS")
    add_label(msp, sx + CORNER_LEG + 3, sy + SPACER_H / 2 - 2,
              f"H={SPACER_H:.0f}", "DIMENSIONS", height=3)
    add_label(msp, sx, sy + SPACER_H + 10, "SIDE VIEW", height=4)

    fx, fy = 2 * (CORNER_LEG + 50), 0
    add_rect(msp, fx, fy, SPACER_DEPTH, SPACER_H, "SPACERS")
    add_circle(msp, fx + SPACER_DEPTH / 2, fy + SPACER_H / 2,
               CLAMP_HOLE / 2, "FASTENERS")
    add_label(msp, fx, fy - 8, f"DEPTH={SPACER_DEPTH:.0f}", "DIMENSIONS", height=3)
    add_label(msp, fx, fy + SPACER_H + 10, "FRONT VIEW", height=4)

    add_label(msp, 0, CORNER_LEG + 30,
              f"CORNER SPACER — PETG  |  Qty: 8  |  "
              f"L-shape {CORNER_LEG:.0f}x{CORNER_LEG:.0f}x{SPACER_H:.0f}mm, "
              f"wall {CORNER_THICK:.0f}mm",
              height=5)

    filepath = os.path.join(OUTPUT_DIR, "3_corner_spacer_detail.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")

    # --- SVG ---
    total_w = 3 * (CORNER_LEG + 50)
    total_h = max(CORNER_LEG, SPACER_H) + 50
    margin = 15
    vb = (-margin, -margin, total_w + 2 * margin, total_h + 2 * margin)
    svg = svg_header(700, 350, vb)

    svg += svg_rect(ox, oy, CORNER_LEG, CORNER_THICK,
                    SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
    svg += svg_rect(ox, oy, CORNER_THICK, CORNER_LEG,
                    SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
    svg += svg_circle(ox + CORNER_THICK / 2, oy + CORNER_THICK / 2,
                      CLAMP_HOLE / 2, SVG_COLORS["FASTENERS"])
    svg += svg_text(ox, oy + CORNER_LEG + 12, "PLAN VIEW", size=5)

    svg += svg_rect(sx, sy, CORNER_LEG, SPACER_H,
                    SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
    svg += svg_circle(sx + CORNER_THICK / 2, sy + SPACER_H / 2,
                      CLAMP_HOLE / 2, SVG_COLORS["FASTENERS"])
    svg += svg_text(sx, sy + SPACER_H + 12, "SIDE VIEW", size=5)

    svg += svg_rect(fx, fy, SPACER_DEPTH, SPACER_H,
                    SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
    svg += svg_circle(fx + SPACER_DEPTH / 2, fy + SPACER_H / 2,
                      CLAMP_HOLE / 2, SVG_COLORS["FASTENERS"])
    svg += svg_text(fx, fy + SPACER_H + 12, "FRONT VIEW", size=5)

    svg += svg_text(0, total_h + margin - 3,
                    f"CORNER SPACER — PETG  |  Qty: 8  |  "
                    f"L-shape {CORNER_LEG:.0f}x{CORNER_LEG:.0f}x{SPACER_H:.0f}mm",
                    size=5)
    svg += svg_footer()

    svg_path = os.path.join(OUTPUT_DIR, "3_corner_spacer_detail.svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"  Created: {svg_path}")


# ---------------------------------------------------------------------------
# DRAWING 4: Mid-Wall Spacer Detail
# ---------------------------------------------------------------------------

def generate_midwall_spacer_detail():
    doc = setup_doc()
    msp = doc.modelspace()

    midwalls = midwall_spacer_positions()
    qty = len(midwalls) * 2

    ox, oy = 0, 0
    add_rect(msp, ox, oy, MIDWALL_W, MIDWALL_THICK, "SPACERS")
    add_label(msp, ox, oy - 8, f"{MIDWALL_W:.0f}", "DIMENSIONS", height=3)
    add_label(msp, ox + MIDWALL_W + 3, oy + MIDWALL_THICK / 2 - 2,
              f"{MIDWALL_THICK:.0f}", "DIMENSIONS", height=3)
    add_label(msp, ox, oy + MIDWALL_THICK + 8, "PLAN VIEW", height=4)

    fx, fy = MIDWALL_W + 50, 0
    add_rect(msp, fx, fy, MIDWALL_W, MIDWALL_H, "SPACERS")
    add_label(msp, fx + MIDWALL_W + 3, fy + MIDWALL_H / 2 - 2,
              f"H={MIDWALL_H:.0f}", "DIMENSIONS", height=3)
    add_label(msp, fx, fy + MIDWALL_H + 8, "FRONT VIEW", height=4)

    sx, sy = 2 * (MIDWALL_W + 50), 0
    add_rect(msp, sx, sy, MIDWALL_THICK, MIDWALL_H, "SPACERS")
    add_label(msp, sx, sy - 8, f"DEPTH={MIDWALL_THICK:.0f}", "DIMENSIONS", height=3)
    add_label(msp, sx, sy + MIDWALL_H + 8, "SIDE VIEW", height=4)

    add_label(msp, 0, max(MIDWALL_THICK, MIDWALL_H) + 25,
              f"MID-WALL SPACER — PETG  |  Qty: {qty}  |  "
              f"{MIDWALL_W:.0f}x{MIDWALL_THICK:.0f}x{MIDWALL_H:.0f}mm block",
              height=5)

    filepath = os.path.join(OUTPUT_DIR, "4_midwall_spacer_detail.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")

    # --- SVG ---
    total_w = 3 * (MIDWALL_W + 50)
    total_h = max(MIDWALL_THICK, MIDWALL_H) + 45
    margin = 15
    vb = (-margin, -margin, total_w + 2 * margin, total_h + 2 * margin)
    svg = svg_header(700, 250, vb)

    svg += svg_rect(ox, oy, MIDWALL_W, MIDWALL_THICK,
                    SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
    svg += svg_text(ox, oy + MIDWALL_THICK + 10, "PLAN VIEW", size=5)

    svg += svg_rect(fx, fy, MIDWALL_W, MIDWALL_H,
                    SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
    svg += svg_text(fx, fy + MIDWALL_H + 10, "FRONT VIEW", size=5)

    svg += svg_rect(sx, sy, MIDWALL_THICK, MIDWALL_H,
                    SVG_COLORS["SPACERS"], fill="rgba(204,68,204,0.3)")
    svg += svg_text(sx, sy + MIDWALL_H + 10, "SIDE VIEW", size=5)

    svg += svg_text(0, total_h + margin - 3,
                    f"MID-WALL SPACER — PETG  |  Qty: {qty}  |  "
                    f"{MIDWALL_W:.0f}x{MIDWALL_THICK:.0f}x{MIDWALL_H:.0f}mm",
                    size=5)
    svg += svg_footer()

    svg_path = os.path.join(OUTPUT_DIR, "4_midwall_spacer_detail.svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"  Created: {svg_path}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    corners = corner_spacer_positions()
    midwalls = midwall_spacer_positions()
    total = (len(corners) + len(midwalls)) * 2

    print("Generating Satellite Unit Spacer Drawings (Rev 3.2)...")
    print(f"Output: {OUTPUT_DIR}")
    print()
    print("Shell dimensions (foam cavity):")
    print(f"  Shell 1 inner: {OUTER_W - 2 * WALL:.0f} x {OUTER_D - 2 * WALL:.0f} mm")
    print(f"  Shell 2 outer: {MID_W:.0f} x {MID_D:.0f} mm")
    print(f"  Foam gap:      {FOAM:.0f} mm")
    print()
    print("Spacer specs:")
    print(f"  Corner spacer: L-shape {CORNER_LEG:.0f}x{CORNER_LEG:.0f}x{SPACER_H:.0f}mm, "
          f"wall {CORNER_THICK:.0f}mm, M4 bolt hole")
    print(f"  Mid-wall spacer: {MIDWALL_W:.0f}x{MIDWALL_THICK:.0f}x{MIDWALL_H:.0f}mm block")
    print(f"  Vertical levels: Z1={SPACER_Z1:.0f}mm, Z2={SPACER_Z2:.0f}mm")
    print()
    print(f"Quantities:")
    print(f"  Corner spacers:   {len(corners)} positions x 2 levels = {len(corners) * 2}")
    print(f"  Mid-wall spacers: {len(midwalls)} positions x 2 levels = {len(midwalls) * 2}")
    print(f"  Total pieces:     {total}")
    print()

    generate_spacer_plan()
    generate_spacer_cross_section()
    generate_corner_spacer_detail()
    generate_midwall_spacer_detail()

    print()
    print("Done. Import DXFs via Fusion: Insert > Insert DXF")
    print("SVGs can be viewed in any browser.")


if __name__ == "__main__":
    main()
