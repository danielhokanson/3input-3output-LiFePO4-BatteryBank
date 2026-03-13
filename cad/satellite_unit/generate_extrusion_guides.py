#!/usr/bin/env python3
"""
Generate annotated SVG extrusion guide images for the Satellite Unit enclosure.

Shows how to go from 2D DXF profiles to 3D bodies in Fusion 360, with
step-by-step workflow annotations for each shell and the cap.

Produces SVGs in cad/satellite_unit/guides/ showing:
  1. extrusion_overview.svg  — Front cross-section of two nested shells
  2. shell1_extrusion.svg    — Shell 1 (ASA outer) plan + side profile
  3. shell2_extrusion.svg    — Shell 2 (PETG structural)
  4. cap_extrusion.svg       — Cap rim plan + extrusion
  5. lid_extrusion.svg        — Lid plan + profile + workflow

All dimensions in millimeters.

Usage:
    python cad/satellite_unit/generate_extrusion_guides.py

Output:
    cad/satellite_unit/guides/extrusion_overview.svg
    cad/satellite_unit/guides/shell1_extrusion.svg
    cad/satellite_unit/guides/shell2_extrusion.svg
    cad/satellite_unit/guides/cap_extrusion.svg
    cad/satellite_unit/guides/lid_extrusion.svg
"""

import os

# ---------------------------------------------------------------------------
# PARAMETRIC DIMENSIONS (all in mm) — mirrored from generate_dxf.py
# ---------------------------------------------------------------------------

CELL_L = 129.0
CELL_W = 36.0
CELL_H = 256.0
TERMINAL_H = 4.0
CELLS_S = 4
CELLS_P = 1

STACK_W = CELLS_S * CELL_W + (CELLS_S - 1) * 2 + 8   # 158
STACK_D = CELL_L + 10.0                                # 139
STACK_H = CELL_H + TERMINAL_H + 30.0                   # 290

THERM_W = 70.0
THERM_D = STACK_D   # 139
THERM_H = STACK_H   # 290

WALL = 5.0
WALL_S2 = 5.0
FOAM = 30.0
ZONE_GAP = 15.0
ZONE_MARGIN = 10.0

# Rib and nub dimensions (foam-pressure ribs + spacer nubs)
RIB_W = 3.0
RIB_H = 10.0
RIB_SPACING = 100.0
NUB_W = 15.0
NUB_H = 30.0  # full foam gap
BASE_THICK = WALL

# Derived — Shell 3 (inner)
INNER_W = 2 * ZONE_MARGIN + STACK_W + ZONE_GAP + THERM_W   # 263
INNER_D = max(STACK_D, THERM_D) + 2 * ZONE_MARGIN           # 159
INNER_H = max(STACK_H, THERM_H) + BASE_THICK                # 293

# Derived — Shell 2 (mid) — wraps directly around component space
MID_W = INNER_W + 2 * WALL_S2   # 271
MID_D = INNER_D + 2 * WALL_S2   # 167
MID_H = INNER_H + WALL_S2       # 297

# Derived — Shell 1 (outer)
OUTER_W = MID_W + 2 * (FOAM + WALL)  # 345
OUTER_D = MID_D + 2 * (FOAM + WALL)  # 241
OUTER_H = MID_H + FOAM + WALL + BASE_THICK  # 337

# Cap — flush with S1 outer, inner lip slips inside S2
CAP_LIP = 0.0
CAP_THICK = 8.0
CAP_OUTER_W = OUTER_W + 2 * CAP_LIP  # = OUTER_W (flush)
CAP_OUTER_D = OUTER_D + 2 * CAP_LIP  # = OUTER_D (flush)

# Lid
LID_THICK = 25.0
LID_OVERHANG = 15.0
LID_SKIRT = 20.0
LID_W = CAP_OUTER_W + 2 * LID_OVERHANG
LID_D = CAP_OUTER_D + 2 * LID_OVERHANG

# Gasket / bolt / insert (must match generate_dxf.py)
CAP_GASKET_W = 4.0         # gasket cord diameter / groove width
CAP_GASKET_D = 2.5         # groove depth cut into cap top surface
CAP_GASKET_MARGIN = 3.0    # margin from foam edge to gasket center
CAP_BOLT_SPACING = 80.0
M4_HOLE = 4.5
INSERT_OD = 6.0            # M4 brass heat-set insert outer diameter
INSERT_DEPTH = 6.0         # insert pressed into cap from below

# Foam anchor teeth
FOAM_TOOTH_W = 5.0
FOAM_TOOTH_D = 10.0
FOAM_TOOTH_THICK = FOAM - 4.0
FOAM_TOOTH_SPACING = 50.0

# Z-offsets for each shell base
S1_Z = 0
S2_Z = BASE_THICK + FOAM   # 33

# ---------------------------------------------------------------------------
# COLORS
# ---------------------------------------------------------------------------

CLR_S1 = "#ff9a3c"       # orange — Shell 1
CLR_S1_DARK = "#cc6600"
CLR_S1_FILL = "#fff3e6"
CLR_S2 = "#51cf66"       # green — Shell 2
CLR_S2_DARK = "#2b8a3e"
CLR_S2_FILL = "#e6f9ec"
CLR_FOAM = "#ffe0b2"
CLR_FOAM_STROKE = "#ff8f00"
CLR_NUB = "#d35400"
CLR_DIM = "#555"
CLR_TEXT = "#333"
CLR_ARROW = "#666"
CLR_BG_BOX = "#f8f9fa"
CLR_LID = "#be4bdb"
CLR_LID_DARK = "#862e9c"
CLR_LID_FILL = "#f8f0fc"
CLR_CAP = "#ff922b"
CLR_CAP_DARK = "#d9480f"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guides")


# ---------------------------------------------------------------------------
# SVG HELPERS
# ---------------------------------------------------------------------------

def svg_header(w, h):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">\n'
        f'  <style>text {{ font-family: Arial, Helvetica, sans-serif; }}</style>\n'
        f'  <rect width="{w}" height="{h}" fill="white"/>\n'
    )


def svg_footer():
    return '</svg>\n'


def svg_rect(x, y, w, h, fill="none", stroke="#000", sw=1.5, opacity=1.0, rx=0):
    return (
        f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
        f'opacity="{opacity}" rx="{rx}"/>\n'
    )


def svg_rect_dashed(x, y, w, h, stroke="#000", sw=1.5):
    return (
        f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="none" stroke="{stroke}" stroke-width="{sw}" '
        f'stroke-dasharray="6,4"/>\n'
    )


def svg_text(x, y, text, size=12, fill="#333", anchor="start", weight="normal"):
    return (
        f'  <text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}">{text}</text>\n'
    )


def svg_line(x1, y1, x2, y2, stroke="#000", sw=1.5, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return (
        f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{sw}"{d}/>\n'
    )


def svg_arrow_v(x, y_top, y_bot, color="#666", sw=1.5, head=8):
    """Vertical arrow from y_top to y_bot (pointing down). Returns SVG string."""
    s = svg_line(x, y_top, x, y_bot, stroke=color, sw=sw)
    # Arrowhead at bottom
    s += (
        f'  <polygon points="{x:.1f},{y_bot:.1f} '
        f'{x - head / 2:.1f},{y_bot - head:.1f} '
        f'{x + head / 2:.1f},{y_bot - head:.1f}" fill="{color}"/>\n'
    )
    # Arrowhead at top (pointing up)
    s += (
        f'  <polygon points="{x:.1f},{y_top:.1f} '
        f'{x - head / 2:.1f},{y_top + head:.1f} '
        f'{x + head / 2:.1f},{y_top + head:.1f}" fill="{color}"/>\n'
    )
    return s


def svg_arrow_up(x, y_bot, y_top, color="#666", sw=1.5, head=8):
    """Single upward arrow from y_bot to y_top."""
    s = svg_line(x, y_bot, x, y_top, stroke=color, sw=sw)
    s += (
        f'  <polygon points="{x:.1f},{y_top:.1f} '
        f'{x - head / 2:.1f},{y_top + head:.1f} '
        f'{x + head / 2:.1f},{y_top + head:.1f}" fill="{color}"/>\n'
    )
    return s


def svg_circle(cx, cy, r, fill="none", stroke="#333", sw=1.5):
    return (
        f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>\n'
    )


def svg_dim_h(x1, x2, y, label, color="#555", offset=0):
    """Horizontal dimension line with label above."""
    s = ''
    tick = 5
    ly = y + offset
    s += svg_line(x1, ly - tick, x1, ly + tick, stroke=color, sw=1)
    s += svg_line(x2, ly - tick, x2, ly + tick, stroke=color, sw=1)
    s += svg_line(x1, ly, x2, ly, stroke=color, sw=1)
    mx = (x1 + x2) / 2
    s += svg_text(mx, ly - 4, label, size=10, fill=color, anchor="middle")
    return s


def svg_dim_v(x, y1, y2, label, color="#555", offset=0):
    """Vertical dimension line with label beside."""
    s = ''
    tick = 5
    lx = x + offset
    s += svg_line(lx - tick, y1, lx + tick, y1, stroke=color, sw=1)
    s += svg_line(lx - tick, y2, lx + tick, y2, stroke=color, sw=1)
    s += svg_line(lx, y1, lx, y2, stroke=color, sw=1)
    my = (y1 + y2) / 2
    s += svg_text(lx + 6, my + 4, label, size=10, fill=color, anchor="start")
    return s


def write_svg(filename, content):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# 1. EXTRUSION OVERVIEW — Front cross-section with all three nested shells
# ---------------------------------------------------------------------------

def generate_extrusion_overview():
    W, H = 1100, 820
    s = svg_header(W, H)

    # Title
    s += svg_text(20, 30, "SATELLITE UNIT \u2014 EXTRUSION OVERVIEW (Rev 3.2)",
                  size=18, fill=CLR_TEXT, weight="bold")
    s += svg_text(20, 50,
                  "Front cross-section showing two nested shells, foam cavity, and Z-offsets",
                  size=11, fill=CLR_DIM)

    # Drawing area: cross-section centered
    # Scale: fit OUTER_H (337) + cap into ~450px vertical, OUTER_W (345) into ~500px horiz
    scale = 1.25
    cx = 380  # center X of drawing
    base_y = 720  # bottom of Shell 1

    def sx(mm):
        return cx + mm * scale

    def sy(mm):
        return base_y - mm * scale

    # Shell 1 (orange)
    s1_x = cx - OUTER_W / 2 * scale
    s1_y = sy(OUTER_H)
    s1_w = OUTER_W * scale
    s1_h = OUTER_H * scale
    s += svg_rect(s1_x, s1_y, s1_w, s1_h, fill=CLR_S1_FILL, stroke=CLR_S1, sw=2.5)

    # Foam cavity (between S1 inner and S2 outer)
    foam_x = s1_x + WALL * scale
    foam_y = sy(OUTER_H - WALL)
    foam_w = s1_w - 2 * WALL * scale
    foam_h = (OUTER_H - WALL - BASE_THICK) * scale
    s += svg_rect(foam_x, foam_y, foam_w, foam_h,
                  fill=CLR_FOAM, stroke=CLR_FOAM_STROKE, sw=1.5)
    # Label foam
    s += svg_text(foam_x + 5, foam_y + 18, "FOAM (30mm)",
                  size=9, fill=CLR_FOAM_STROKE)

    # --- Foam-pressure ribs and spacer nubs (between S1 and S2) ---
    # S1 inner wall ribs: protrude inward from S1 inner wall into foam
    rib_w_px = RIB_W * scale
    rib_h_px = RIB_H * scale
    nub_w_px = NUB_W * scale
    nub_h_px = NUB_H * scale

    # Left side ribs (S1 inner wall = foam_x)
    rib_base_z = 50.0  # ~50mm from base
    for i in range(3):
        rz = rib_base_z + i * RIB_SPACING
        ry = sy(rz + RIB_W)  # rib vertical position (using RIB_W as rib height on wall)
        # S1 left inner wall ribs — protrude rightward into foam
        s += svg_rect(foam_x, ry, rib_h_px, rib_w_px,
                      fill=CLR_FOAM_STROKE, stroke=CLR_FOAM_STROKE, sw=0.5)
        # S1 right inner wall ribs — protrude leftward into foam
        s += svg_rect(foam_x + foam_w - rib_h_px, ry, rib_h_px, rib_w_px,
                      fill=CLR_FOAM_STROKE, stroke=CLR_FOAM_STROKE, sw=0.5)

    # S2 outer wall ribs: protrude outward from S2 into foam
    s2_left_x = cx - MID_W / 2 * scale
    s2_right_x = cx + MID_W / 2 * scale
    for i in range(3):
        rz = rib_base_z + i * RIB_SPACING + S2_Z
        ry = sy(rz + RIB_W)
        # S2 left outer ribs — protrude leftward
        s += svg_rect(s2_left_x - rib_h_px, ry, rib_h_px, rib_w_px,
                      fill=CLR_S2, stroke=CLR_S2_DARK, sw=0.5)
        # S2 right outer ribs — protrude rightward
        s += svg_rect(s2_right_x, ry, rib_h_px, rib_w_px,
                      fill=CLR_S2, stroke=CLR_S2_DARK, sw=0.5)

    # Spacer nubs on S1 inner walls (span full foam gap, 30mm)
    nub_z1 = rib_base_z + 50.0  # between first and second rib
    for nz in [nub_z1, nub_z1 + RIB_SPACING]:
        ny = sy(nz + NUB_W)
        # Left nub
        s += svg_rect(foam_x, ny, nub_h_px, nub_w_px,
                      fill=CLR_NUB, stroke=CLR_NUB, sw=0.5, opacity=0.8)
        # Right nub
        s += svg_rect(foam_x + foam_w - nub_h_px, ny, nub_h_px, nub_w_px,
                      fill=CLR_NUB, stroke=CLR_NUB, sw=0.5, opacity=0.8)

    # Labels for ribs and nubs
    rib_label_y = sy(rib_base_z + RIB_W / 2)
    s += svg_text(foam_x + rib_h_px + 3, rib_label_y + 4, "RIBS",
                  size=7, fill=CLR_FOAM_STROKE)
    nub_label_y = sy(nub_z1 + NUB_W / 2)
    s += svg_text(foam_x + nub_h_px + 3, nub_label_y + 4, "NUB",
                  size=7, fill=CLR_NUB)

    # Shell 2 (green)
    s2_x = cx - MID_W / 2 * scale
    s2_y = sy(S2_Z + MID_H)
    s2_w = MID_W * scale
    s2_h = MID_H * scale
    s += svg_rect(s2_x, s2_y, s2_w, s2_h, fill=CLR_S2_FILL, stroke=CLR_S2, sw=2.5)

    # Interior labels
    s += svg_text(cx, s2_y + s2_h / 2, "CELL + THERMAL ZONES",
                  size=11, fill=CLR_S2_DARK, anchor="middle", weight="bold")

    # --- Vertical arrows for extrusion heights (right side) ---
    arr_x_base = s1_x + s1_w + 15

    # Shell 1 arrow
    s += svg_arrow_v(arr_x_base, s1_y, base_y, color=CLR_S1, sw=2)
    s += svg_text(arr_x_base + 8, (s1_y + base_y) / 2 - 6,
                  f"S1 = {OUTER_H:.0f}mm", size=11, fill=CLR_S1_DARK, weight="bold")
    s += svg_text(arr_x_base + 8, (s1_y + base_y) / 2 + 8,
                  f"Z-offset: {S1_Z}mm", size=9, fill=CLR_S1_DARK)

    # Shell 2 arrow
    arr_x2 = arr_x_base + 110
    s += svg_arrow_v(arr_x2, s2_y, sy(S2_Z), color=CLR_S2, sw=2)
    s += svg_text(arr_x2 + 8, (s2_y + sy(S2_Z)) / 2 - 6,
                  f"S2 = {MID_H:.0f}mm", size=11, fill=CLR_S2_DARK, weight="bold")
    s += svg_text(arr_x2 + 8, (s2_y + sy(S2_Z)) / 2 + 8,
                  f"Z-offset: {S2_Z:.0f}mm", size=9, fill=CLR_S2_DARK)

    # Z-offset dashed lines
    for z_val, clr in [(S2_Z, CLR_S2)]:
        y_line = sy(z_val)
        s += svg_line(s1_x - 30, y_line, arr_x2 + 80, y_line,
                      stroke=clr, sw=1, dash="4,4")
        s += svg_text(s1_x - 35, y_line + 4, f"Z={z_val:.0f}",
                      size=9, fill=clr, anchor="end")

    # Ground line
    s += svg_line(s1_x - 30, base_y, arr_x2 + 80, base_y,
                  stroke=CLR_TEXT, sw=1, dash="4,4")
    s += svg_text(s1_x - 35, base_y + 4, "Z=0",
                  size=9, fill=CLR_TEXT, anchor="end")

    # Width dimension below
    s += svg_dim_h(s1_x, s1_x + s1_w, base_y + 25,
                   f"{OUTER_W:.0f}mm (Shell 1)", color=CLR_S1_DARK)

    # --- Legend ---
    leg_x = 20
    leg_y = 68
    s += svg_rect(leg_x - 5, leg_y - 5, 300, 190, fill=CLR_BG_BOX,
                  stroke="#dee2e6", sw=1, rx=4)
    s += svg_text(leg_x, leg_y + 14, "LEGEND", size=13, fill=CLR_TEXT, weight="bold")

    items = [
        (CLR_S1, CLR_S1_DARK, "Shell 1 (ASA outer)",
         f"{OUTER_W:.0f} x {OUTER_D:.0f} x {OUTER_H:.0f}mm"),
        (CLR_S2, CLR_S2_DARK, "Shell 2 (PETG structural)",
         f"{MID_W:.0f} x {MID_D:.0f} x {MID_H:.0f}mm"),
        (CLR_FOAM, CLR_FOAM_STROKE, "Foam cavity", "30mm between S1 and S2"),
        (CLR_FOAM_STROKE, CLR_FOAM_STROKE, "Foam-pressure ribs",
         f"{RIB_W:.0f} x {RIB_H:.0f}mm, {RIB_SPACING:.0f}mm spacing"),
        (CLR_NUB, CLR_NUB, "Spacer nubs",
         f"{NUB_W:.0f} x {NUB_H:.0f}mm (full foam gap)"),
    ]
    for i, (clr, clr_d, label, dims) in enumerate(items):
        iy = leg_y + 30 + i * 30
        s += svg_rect(leg_x + 5, iy - 10, 16, 16, fill=clr, stroke=clr_d, sw=1, rx=2)
        s += svg_text(leg_x + 28, iy + 2, label, size=11, fill=CLR_TEXT, weight="bold")
        s += svg_text(leg_x + 28, iy + 15, dims, size=9, fill=CLR_DIM)

    s += svg_footer()
    write_svg("extrusion_overview.svg", s)


# ---------------------------------------------------------------------------
# SHELL EXTRUSION GUIDE (generic for shells 1-3)
# ---------------------------------------------------------------------------

def generate_shell_extrusion(
    filename, shell_num, material,
    plan_w, plan_d, ext_h, z_offset,
    dxf_file, color, color_dark, color_fill,
    wall_thick, conduits=None
):
    W, H = 1100, 750
    s = svg_header(W, H)

    title = f"SATELLITE UNIT \u2014 SHELL {shell_num} EXTRUSION ({material})"
    s += svg_text(20, 30, title, size=18, fill=CLR_TEXT, weight="bold")
    s += svg_text(20, 50,
                  f"Rev 3.2  |  Plan: {plan_w:.0f} x {plan_d:.0f}mm  |  "
                  f"Extrude: {ext_h:.0f}mm  |  Z-offset: {z_offset:.0f}mm",
                  size=11, fill=CLR_DIM)

    # --- LEFT: Plan view ---
    plan_scale = min(380 / plan_w, 350 / plan_d)
    pw = plan_w * plan_scale
    pd = plan_d * plan_scale
    px = 60
    py = 130

    s += svg_text(px + pw / 2, py - 15, "PLAN VIEW (top-down)",
                  size=13, fill=CLR_TEXT, anchor="middle", weight="bold")

    s += svg_rect(px, py, pw, pd, fill=color_fill, stroke=color, sw=2.5)

    # Width dimension
    s += svg_dim_h(px, px + pw, py + pd + 20,
                   f"{plan_w:.0f}mm", color=color_dark)
    # Depth dimension
    s += svg_dim_v(px + pw + 15, py, py + pd,
                   f"{plan_d:.0f}mm", color=color_dark)

    # Center crosshair
    ccx = px + pw / 2
    ccy = py + pd / 2
    ch = 15
    s += svg_line(ccx - ch, ccy, ccx + ch, ccy, stroke=color, sw=0.5)
    s += svg_line(ccx, ccy - ch, ccx, ccy + ch, stroke=color, sw=0.5)

    # --- Rib and nub indicators on plan view ---
    if shell_num == 1:
        # Shell 1: tick marks on inner perimeter for ribs
        rib_tick = 6  # px length of tick mark
        # Top and bottom edges — 3 ticks each
        for frac in [0.25, 0.50, 0.75]:
            tx = px + frac * pw
            s += svg_line(tx, py, tx, py + rib_tick,
                          stroke=CLR_FOAM_STROKE, sw=1.5)
            s += svg_line(tx, py + pd - rib_tick, tx, py + pd,
                          stroke=CLR_FOAM_STROKE, sw=1.5)
        # Left and right edges
        for frac in [0.25, 0.50, 0.75]:
            ty = py + frac * pd
            s += svg_line(px, ty, px + rib_tick, ty,
                          stroke=CLR_FOAM_STROKE, sw=1.5)
            s += svg_line(px + pw - rib_tick, ty, px + pw, ty,
                          stroke=CLR_FOAM_STROKE, sw=1.5)
        # Corner nub squares
        nub_sz = 5  # px
        for (nx, ny) in [(px, py), (px + pw - nub_sz, py),
                         (px, py + pd - nub_sz), (px + pw - nub_sz, py + pd - nub_sz)]:
            s += svg_rect(nx, ny, nub_sz, nub_sz,
                          fill=CLR_NUB, stroke=CLR_NUB, sw=0.5, opacity=0.8)
    elif shell_num == 2:
        # Shell 2: tick marks on outer perimeter for ribs
        rib_tick = 6
        for frac in [0.25, 0.50, 0.75]:
            tx = px + frac * pw
            s += svg_line(tx, py - rib_tick, tx, py,
                          stroke=CLR_S2, sw=1.5)
            s += svg_line(tx, py + pd, tx, py + pd + rib_tick,
                          stroke=CLR_S2, sw=1.5)
        for frac in [0.25, 0.50, 0.75]:
            ty = py + frac * pd
            s += svg_line(px - rib_tick, ty, px, ty,
                          stroke=CLR_S2, sw=1.5)
            s += svg_line(px + pw, ty, px + pw + rib_tick, ty,
                          stroke=CLR_S2, sw=1.5)

    # DXF file reference
    s += svg_text(px + pw / 2, py + pd + 50,
                  f"Source: {dxf_file}", size=10, fill=CLR_DIM, anchor="middle")

    # --- Conduit penetrations on plan view ---
    if conduits:
        conduit_clr = "#e64980"  # magenta-pink for visibility
        for c in conduits:
            # c = (x_frac, y_frac, dia_mm, label)
            cx = px + c[0] * pw
            cy = py + c[1] * pd
            cr = (c[2] / 2) * plan_scale
            cr = max(cr, 3)  # minimum visible radius
            s += svg_circle(cx, cy, cr, fill="white", stroke=conduit_clr, sw=1.5)
            s += svg_text(cx, cy + cr + 10, c[3], size=7,
                          fill=conduit_clr, anchor="middle")
        s += svg_text(px + pw / 2, py + pd + 65,
                      "Conduit holes — cut after extrusion (see DXF Drawing 4)",
                      size=9, fill=conduit_clr, anchor="middle")

    # --- RIGHT: Side profile (extrusion) ---
    side_scale = min(250 / plan_w, 380 / ext_h)
    sw_px = plan_w * side_scale
    sh_px = ext_h * side_scale
    side_x = 620
    side_y = 130

    s += svg_text(side_x + sw_px / 2 + 40, side_y - 15,
                  "SIDE PROFILE (extrusion direction)",
                  size=13, fill=CLR_TEXT, anchor="middle", weight="bold")

    # Base profile (cross-section)
    s += svg_rect(side_x, side_y + sh_px, sw_px, 4,
                  fill=color, stroke=color_dark, sw=1.5)
    s += svg_text(side_x + sw_px / 2, side_y + sh_px + 20,
                  f"{plan_w:.0f}mm", size=10, fill=color_dark, anchor="middle")

    # Extruded body (dashed outline)
    s += svg_rect_dashed(side_x, side_y, sw_px, sh_px, stroke=color, sw=1.5)

    # Fill with light color
    s += svg_rect(side_x + 1, side_y + 1, sw_px - 2, sh_px - 2,
                  fill=color_fill, stroke="none", sw=0, opacity=0.4)

    # --- Ribs and nubs on side profile ---
    rib_side_w = RIB_W * side_scale
    rib_side_h = RIB_H * side_scale
    nub_side_w = NUB_W * side_scale
    nub_side_h = NUB_H * side_scale
    if shell_num == 1:
        # Ribs on inner surface (protrude inward = toward center)
        rib_start_y = side_y + sh_px * 0.15  # ~50mm from base equivalent
        for i in range(3):
            ry = rib_start_y + i * (RIB_SPACING * side_scale)
            if ry + rib_side_w > side_y + sh_px:
                break
            # Left inner wall rib
            s += svg_rect(side_x + rib_side_h, ry, rib_side_h, rib_side_w,
                          fill=CLR_FOAM_STROKE, stroke=CLR_FOAM_STROKE, sw=0.5)
            # Right inner wall rib
            s += svg_rect(side_x + sw_px - 2 * rib_side_h, ry,
                          rib_side_h, rib_side_w,
                          fill=CLR_FOAM_STROKE, stroke=CLR_FOAM_STROKE, sw=0.5)
        # Nubs between ribs
        nub_y1 = rib_start_y + 0.5 * (RIB_SPACING * side_scale)
        for ny in [nub_y1, nub_y1 + RIB_SPACING * side_scale]:
            if ny + nub_side_w > side_y + sh_px:
                break
            s += svg_rect(side_x, ny, nub_side_h, nub_side_w,
                          fill=CLR_NUB, stroke=CLR_NUB, sw=0.5, opacity=0.8)
            s += svg_rect(side_x + sw_px - nub_side_h, ny,
                          nub_side_h, nub_side_w,
                          fill=CLR_NUB, stroke=CLR_NUB, sw=0.5, opacity=0.8)
    elif shell_num == 2:
        # Ribs on outer surface (protrude outward)
        rib_start_y = side_y + sh_px * 0.15
        for i in range(3):
            ry = rib_start_y + i * (RIB_SPACING * side_scale)
            if ry + rib_side_w > side_y + sh_px:
                break
            # Left outer rib
            s += svg_rect(side_x - rib_side_h, ry, rib_side_h, rib_side_w,
                          fill=CLR_S2, stroke=CLR_S2_DARK, sw=0.5)
            # Right outer rib
            s += svg_rect(side_x + sw_px, ry, rib_side_h, rib_side_w,
                          fill=CLR_S2, stroke=CLR_S2_DARK, sw=0.5)

    # Upward arrow showing extrusion direction
    arr_x = side_x + sw_px + 20
    s += svg_arrow_v(arr_x, side_y, side_y + sh_px, color=color, sw=2)
    s += svg_text(arr_x + 10, side_y + sh_px / 2 - 6,
                  f"Extrude Z = {ext_h:.0f}mm", size=12, fill=color_dark, weight="bold")
    s += svg_text(arr_x + 10, side_y + sh_px / 2 + 10,
                  f"(upward from Z = {z_offset:.0f}mm)", size=10, fill=CLR_DIM)

    # Z-offset label
    s += svg_line(side_x - 20, side_y + sh_px, side_x + sw_px + 10,
                  side_y + sh_px, stroke=color, sw=1, dash="4,3")
    s += svg_text(side_x - 25, side_y + sh_px + 4,
                  f"Z={z_offset:.0f}", size=9, fill=color_dark, anchor="end")

    # Top line
    s += svg_line(side_x - 20, side_y, side_x + sw_px + 10,
                  side_y, stroke=color, sw=1, dash="4,3")
    s += svg_text(side_x - 25, side_y + 4,
                  f"Z={z_offset + ext_h:.0f}", size=9, fill=color_dark, anchor="end")

    # --- WORKFLOW STEPS ---
    step_y = side_y + sh_px + 70

    steps = [
        f"1. Import {dxf_file} \u2192 Insert > Insert DXF (select XY plane)",
        f"2. Extrude profile upward: Z = {ext_h:.0f}mm (New Body)",
        f"3. Shell command: wall thickness = {wall_thick:.0f}mm, select top face to hollow",
        f"4. Move body: translate Z = +{z_offset:.0f}mm to final position"
        if z_offset > 0 else
        "4. Shell 1 sits at Z = 0 (no translation needed)",
        f"5. Cut conduit holes (Extrude > Cut) per 4_lead_exit_view.dxf",
    ]
    if shell_num == 1:
        steps += [
            f"6. Add foam-pressure ribs on inner face: 3mm x 10mm, 100mm spacing",
            f"7. Add spacer nubs between ribs: 30mm inward (full foam gap), corners + mid-walls",
            f"8. Add conduit sleeves: 5mm-wall tubes around conduit holes, 30mm inward",
            f"9. Verify outer dims: {plan_w:.0f} x {plan_d:.0f} x {ext_h:.0f}mm",
        ]
    else:
        steps += [
            f"6. Add foam-pressure ribs on outer face: 3mm x 10mm, 100mm spacing",
            f"7. Verify outer dims: {plan_w:.0f} x {plan_d:.0f} x {ext_h:.0f}mm",
        ]
    box_h = 45 + len(steps) * 22
    s += svg_rect(15, step_y - 10, W - 30, box_h, fill=CLR_BG_BOX,
                  stroke="#dee2e6", sw=1, rx=4)
    s += svg_text(30, step_y + 10,
                  "FUSION 360 WORKFLOW", size=14, fill=CLR_TEXT, weight="bold")
    for i, step in enumerate(steps):
        s += svg_text(40, step_y + 35 + i * 22, step,
                      size=11, fill=CLR_TEXT)

    s += svg_footer()
    write_svg(filename, s)


# ---------------------------------------------------------------------------
# 5. CAP EXTRUSION
# ---------------------------------------------------------------------------

def generate_cap_extrusion():
    W, H = 1100, 1500
    s = svg_header(W, H)

    s += svg_text(20, 30, "SATELLITE UNIT \u2014 CAP EXTRUSION (Rev 3.2, Flush)",
                  size=18, fill=CLR_TEXT, weight="bold")
    s += svg_text(20, 50,
                  f"Flush with S1: {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f}mm  |  "
                  f"Thickness: {CAP_THICK:.0f}mm  |  "
                  f"Foam teeth: {FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm",
                  size=11, fill=CLR_DIM)

    # --- Plan view with outer + inner cutout ---
    plan_scale = min(400 / CAP_OUTER_W, 300 / CAP_OUTER_D)
    ow = CAP_OUTER_W * plan_scale
    od = CAP_OUTER_D * plan_scale
    px = 60
    py = 130

    s += svg_text(px + ow / 2, py - 15, "PLAN VIEW (top-down)",
                  size=13, fill=CLR_TEXT, anchor="middle", weight="bold")

    # Outer cap rectangle
    s += svg_rect(px, py, ow, od, fill=CLR_S1_FILL, stroke=CLR_S1, sw=2.5)

    # Inner cutout — show the shell-1 footprint as the opening
    # The cap sits on top of shell 1, so the inner opening is ~OUTER_W x OUTER_D
    # (minus lip thickness on each side)
    inner_w_mm = OUTER_W
    inner_d_mm = OUTER_D
    iw = inner_w_mm * plan_scale
    id_ = inner_d_mm * plan_scale
    ix = px + (ow - iw) / 2
    iy = py + (od - id_) / 2
    s += svg_rect(ix, iy, iw, id_, fill="white", stroke=CLR_S1_DARK, sw=1.5)

    # Label inner opening
    s += svg_text(ix + iw / 2, iy + id_ / 2 + 4, "INNER OPENING",
                  size=10, fill=CLR_DIM, anchor="middle")
    s += svg_text(ix + iw / 2, iy + id_ / 2 + 18,
                  f"({inner_w_mm:.0f} x {inner_d_mm:.0f}mm)",
                  size=9, fill=CLR_DIM, anchor="middle")

    # Gasket groove tracks (two dashed rectangles between outer and inner)
    og_inset = WALL + CAP_GASKET_MARGIN + CAP_GASKET_W / 2
    ig_inset = WALL + FOAM - CAP_GASKET_MARGIN - CAP_GASKET_W / 2
    cap_cx = px + ow / 2
    cap_cy = py + od / 2
    for inset_mm in [og_inset, ig_inset]:
        gw = (CAP_OUTER_W - 2 * inset_mm) * plan_scale
        gd = (CAP_OUTER_D - 2 * inset_mm) * plan_scale
        gx = cap_cx - gw / 2
        gy = cap_cy - gd / 2
        s += (f'  <rect x="{gx:.1f}" y="{gy:.1f}" width="{gw:.1f}" '
              f'height="{gd:.1f}" fill="none" stroke="#e03131" '
              f'stroke-width="1.5" stroke-dasharray="6,3" rx="1"/>\n')

    # Bolt / insert positions (circles between gasket tracks)
    bolt_inset = (og_inset + ig_inset) / 2
    bolt_r_px = (INSERT_OD / 2) * plan_scale
    bolt_positions_mm = []  # collect for tooth conflict check
    for side in ["top", "bottom", "left", "right"]:
        if side in ("top", "bottom"):
            half_w = CAP_OUTER_W / 2 - bolt_inset
            n_bolts = max(2, int(half_w * 2 / CAP_BOLT_SPACING) + 1)
            for i in range(n_bolts):
                bx_mm = -half_w + i * (half_w * 2 / max(1, n_bolts - 1))
                by_mm = ((-1 if side == "top" else 1) *
                         (CAP_OUTER_D / 2 - bolt_inset))
                bolt_positions_mm.append((bx_mm, by_mm))
                bx = cap_cx + bx_mm * plan_scale
                by = cap_cy + by_mm * plan_scale
                s += (f'  <circle cx="{bx:.1f}" cy="{by:.1f}" r="{bolt_r_px:.1f}" '
                      f'fill="none" stroke="#495057" stroke-width="1.2"/>\n')
        else:
            half_d = CAP_OUTER_D / 2 - bolt_inset
            n_bolts = max(2, int(half_d * 2 / CAP_BOLT_SPACING) + 1)
            for i in range(n_bolts):
                by_mm = -half_d + i * (half_d * 2 / max(1, n_bolts - 1))
                bx_mm = ((-1 if side == "left" else 1) *
                         (CAP_OUTER_W / 2 - bolt_inset))
                bolt_positions_mm.append((bx_mm, by_mm))
                bx = cap_cx + bx_mm * plan_scale
                by = cap_cy + by_mm * plan_scale
                s += (f'  <circle cx="{bx:.1f}" cy="{by:.1f}" r="{bolt_r_px:.1f}" '
                      f'fill="none" stroke="#495057" stroke-width="1.2"/>\n')

    # Foam anchor teeth (small filled rectangles along foam gap centerline)
    # Skip teeth that would conflict with bolt/insert positions
    tooth_inset = WALL + FOAM / 2
    tooth_loop_w = CAP_OUTER_W - 2 * tooth_inset
    tooth_loop_d = CAP_OUTER_D - 2 * tooth_inset

    def _tooth_near_bolt(tx_mm, ty_mm, bolts_mm, clearance=15.0):
        for bx, by in bolts_mm:
            if ((tx_mm - bx) ** 2 + (ty_mm - by) ** 2) ** 0.5 < clearance:
                return True
        return False

    n_teeth_w = max(2, round(tooth_loop_w / FOAM_TOOTH_SPACING) + 1)
    for i in range(n_teeth_w):
        tx_mm = -tooth_loop_w / 2 + i * tooth_loop_w / max(1, n_teeth_w - 1)
        for sign_y in [-1, 1]:
            ty_mm = sign_y * tooth_loop_d / 2
            if _tooth_near_bolt(tx_mm, ty_mm, bolt_positions_mm):
                continue
            tx_px = cap_cx + tx_mm * plan_scale
            ty_px = cap_cy + ty_mm * plan_scale
            tw_px = FOAM_TOOTH_W * plan_scale
            th_px = FOAM_TOOTH_THICK * plan_scale
            s += svg_rect(tx_px - tw_px / 2, ty_px - th_px / 2,
                          tw_px, th_px, fill="#c68c00", stroke="#8B6914",
                          sw=0.8, rx=0, opacity=0.7)
    n_teeth_d = max(1, round(tooth_loop_d / FOAM_TOOTH_SPACING) - 1)
    for i in range(n_teeth_d):
        ty_mm = -tooth_loop_d / 2 + (i + 1) * tooth_loop_d / (n_teeth_d + 1)
        for sign_x in [-1, 1]:
            tx_mm = sign_x * tooth_loop_w / 2
            if _tooth_near_bolt(tx_mm, ty_mm, bolt_positions_mm):
                continue
            tx_px = cap_cx + tx_mm * plan_scale
            ty_px = cap_cy + ty_mm * plan_scale
            tw_px = FOAM_TOOTH_THICK * plan_scale
            th_px = FOAM_TOOTH_W * plan_scale
            s += svg_rect(tx_px - tw_px / 2, ty_px - th_px / 2,
                          tw_px, th_px, fill="#c68c00", stroke="#8B6914",
                          sw=0.8, rx=0, opacity=0.7)

    # Gasket/insert/tooth labels
    s += svg_text(cap_cx, iy - 8,
                  "Dual gasket grooves (red dashed)", size=8,
                  fill="#e03131", anchor="middle")
    s += svg_text(cap_cx, iy - 20,
                  f"M4 bolt + {INSERT_OD:.0f}mm insert (circles)", size=8,
                  fill="#495057", anchor="middle")

    # Flush annotation
    s += svg_text(cap_cx, iy + id_ + 18,
                  "Flush with Shell 1 outer", size=8,
                  fill=CLR_S1_DARK, anchor="middle")
    s += svg_text(cap_cx, iy + id_ + 32,
                  f"Foam teeth (gold): {FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm "
                  f"every {FOAM_TOOTH_SPACING:.0f}mm",
                  size=7, fill="#8B6914", anchor="middle")

    # Outer dimensions
    s += svg_dim_h(px, px + ow, py + od + 20,
                   f"{CAP_OUTER_W:.0f}mm", color=CLR_S1_DARK)
    s += svg_dim_v(px + ow + 15, py, py + od,
                   f"{CAP_OUTER_D:.0f}mm", color=CLR_S1_DARK)

    # Source DXF
    s += svg_text(px + ow / 2, py + od + 50,
                  "Source: 7_cap_top_view.dxf + 8_cap_profile.dxf",
                  size=10, fill=CLR_DIM, anchor="middle")

    # --- RIGHT: Profile cross-section ---
    prof_x = 620
    prof_y = 130
    prof_scale = min(300 / CAP_OUTER_W, 100 / CAP_THICK)
    prof_cx = prof_x + (CAP_OUTER_W * prof_scale) / 2
    prof_base_y = 250

    pp_w = CAP_OUTER_W * prof_scale
    pp_h = CAP_THICK * prof_scale
    pp_x = prof_cx - pp_w / 2
    pp_y = prof_base_y - pp_h

    s += svg_text(prof_cx, prof_y - 15, "PROFILE CROSS-SECTION",
                  size=13, fill=CLR_TEXT, anchor="middle", weight="bold")
    s += svg_text(prof_cx, prof_y,
                  "(height exaggerated for clarity)",
                  size=9, fill=CLR_DIM, anchor="middle")

    # Outer profile
    s += svg_rect(pp_x, pp_y, pp_w, pp_h,
                  fill=CLR_S1_FILL, stroke=CLR_S1, sw=2.5)

    # Inner cutout in profile
    ci_prof_w = OUTER_W * prof_scale
    ci_prof_x = prof_cx - ci_prof_w / 2
    s += svg_rect(ci_prof_x, pp_y, ci_prof_w, pp_h,
                  fill="white", stroke=CLR_S1_DARK, sw=1.5)

    # Thickness dimension
    s += svg_dim_v(pp_x + pp_w + 15, pp_y, prof_base_y,
                   f"{CAP_THICK:.0f}mm", color=CLR_DIM, offset=8)

    # Width dimension
    s += svg_dim_h(pp_x, pp_x + pp_w, prof_base_y + 20,
                   f"{CAP_OUTER_W:.0f}mm", color=CLR_DIM)

    # Foam teeth on profile (hanging down from cap underside)
    tooth_inset_px = (WALL + FOAM / 2) * prof_scale
    tooth_w_px = max(3, FOAM_TOOTH_THICK * prof_scale)
    tooth_h_px = max(8, FOAM_TOOTH_D * prof_scale * 2)  # exaggerated for visibility
    for side in [1, -1]:
        tx = prof_cx + side * (CAP_OUTER_W / 2 - WALL - FOAM / 2) * prof_scale
        s += svg_rect(tx - tooth_w_px / 2, prof_base_y,
                      tooth_w_px, tooth_h_px,
                      fill="#c68c00", stroke="#8B6914", sw=1, rx=0)
    # Label
    tx_right = prof_cx + (CAP_OUTER_W / 2 - WALL - FOAM / 2) * prof_scale
    s += svg_text(tx_right + tooth_w_px / 2 + 5, prof_base_y + tooth_h_px / 2 + 3,
                  f"Foam teeth ({FOAM_TOOTH_D:.0f}mm)", size=8, fill="#8B6914")

    # Extrusion arrow
    arr_x = pp_x + pp_w + 60
    s += svg_arrow_up(arr_x, prof_base_y, pp_y - 15, color=CLR_S1, sw=2)
    s += svg_text(arr_x + 10, (pp_y + prof_base_y) / 2 + 4,
                  f"{CAP_THICK:.0f}mm", size=11, fill=CLR_S1_DARK, weight="bold")

    # =================================================================
    # BOLT + INSERT POCKET DETAIL DIAGRAM
    # =================================================================
    s += svg_text(20, 490, "BOLT + INSERT POCKET DETAIL", size=13,
                  fill=CLR_TEXT, weight="bold")
    s += svg_text(20, 507,
                  "Cross-section through a single M4 bolt hole (not to scale)",
                  size=10, fill=CLR_DIM)

    det_cx = 200      # center of detail
    det_top = 540     # top of cap in detail (SVG y)
    det_h = 130       # cap thickness in pixels
    det_bot = det_top + det_h
    det_w = 280

    # Cap body
    s += svg_rect(det_cx - det_w / 2, det_top, det_w, det_h,
                  fill=CLR_S1_FILL, stroke=CLR_S1, sw=2)
    s += svg_text(det_cx - det_w / 2 + 6, det_top + 14,
                  "CAP BODY (ASA)", size=9, fill=CLR_S1_DARK, weight="bold")

    # Gasket groove (left of bolt)
    gg_w_px = 30
    gg_d_px = 35
    gg_cx = det_cx - 70
    s += svg_rect(gg_cx - gg_w_px / 2, det_top, gg_w_px, gg_d_px,
                  fill="white", stroke="#e03131", sw=1.5)
    cord_r = gg_w_px / 2 - 3
    s += svg_circle(gg_cx, det_top + gg_d_px - cord_r - 2, cord_r,
                    fill="#ffcccc", stroke="#e03131", sw=1)
    s += svg_text(gg_cx, det_top - 6,
                  "Gasket groove", size=8, fill="#e03131", anchor="middle")
    s += svg_text(gg_cx, det_top + gg_d_px + 12,
                  f"{CAP_GASKET_W:.0f}W x {CAP_GASKET_D:.1f}D mm",
                  size=7, fill="#e03131", anchor="middle")

    # M4 bolt through-hole
    bolt_w_px = 28
    bolt_cx = det_cx + 10
    s += svg_rect(bolt_cx - bolt_w_px / 2, det_top, bolt_w_px, det_h,
                  fill="#e8e8e8", stroke="#495057", sw=1.5)
    # Centerline
    s += svg_line(bolt_cx, det_top - 30, bolt_cx, det_bot + 80,
                  stroke="#495057", sw=0.8, dash="4,3")

    # Bolt shaft
    shaft_w = 14
    s += svg_rect(bolt_cx - shaft_w / 2, det_top - 15, shaft_w, det_h + 15 + 30,
                  fill="#a0a0a0", stroke="#495057", sw=1)

    # Bolt head
    head_w = 50
    head_h = 22
    s += svg_rect(bolt_cx - head_w / 2, det_top - 15 - head_h, head_w, head_h,
                  fill="#6c757d", stroke="#333", sw=1.5, rx=2)
    s += svg_text(bolt_cx, det_top - 15 - head_h / 2 + 4,
                  "M4 BOLT HEAD", size=8, fill="white",
                  anchor="middle", weight="bold")

    # Insert pocket (counterbore from underside)
    ins_w_px = 48
    ins_d_px = 60
    pocket_top_y = det_bot - ins_d_px

    s += svg_rect(bolt_cx - ins_w_px / 2, pocket_top_y, ins_w_px, ins_d_px,
                  fill="#fff3e0", stroke="#d9480f", sw=2)

    # Brass insert hatching
    for hy in range(int(pocket_top_y) + 4, int(det_bot) - 2, 5):
        s += svg_line(bolt_cx - ins_w_px / 2 + 2, hy,
                      bolt_cx - bolt_w_px / 2 - 1, hy,
                      stroke="#c68c00", sw=1.5)
        s += svg_line(bolt_cx + bolt_w_px / 2 + 1, hy,
                      bolt_cx + ins_w_px / 2 - 2, hy,
                      stroke="#c68c00", sw=1.5)

    # Insert label
    s += svg_text(bolt_cx, det_bot - ins_d_px / 2 + 4,
                  "BRASS", size=7, fill="#8B6914", anchor="middle", weight="bold")

    # Thread indication
    for ty in range(int(pocket_top_y) + 8, int(det_bot) - 4, 8):
        s += svg_line(bolt_cx - bolt_w_px / 2, ty,
                      bolt_cx - bolt_w_px / 2 + 4, ty + 3,
                      stroke="#8B6914", sw=0.8)
        s += svg_line(bolt_cx + bolt_w_px / 2, ty,
                      bolt_cx + bolt_w_px / 2 - 4, ty + 3,
                      stroke="#8B6914", sw=0.8)

    # Dimension annotations
    dim_r = det_cx + det_w / 2 + 15
    s += svg_dim_v(dim_r, det_top, det_bot,
                   f"{CAP_THICK:.0f}mm cap", color="#555", offset=8)

    dim_l = det_cx - det_w / 2 - 15
    s += svg_line(dim_l - 5, pocket_top_y, dim_l + 5, pocket_top_y,
                  stroke="#d9480f", sw=1)
    s += svg_line(dim_l - 5, det_bot, dim_l + 5, det_bot,
                  stroke="#d9480f", sw=1)
    s += svg_line(dim_l, pocket_top_y, dim_l, det_bot,
                  stroke="#d9480f", sw=1)
    s += svg_text(dim_l - 3, (pocket_top_y + det_bot) / 2 + 4,
                  f"{INSERT_DEPTH:.0f}mm", size=9, fill="#d9480f",
                  anchor="end", weight="bold")

    # Bore + insert labels with leader lines
    s += svg_text(bolt_cx + bolt_w_px / 2 + 30, det_top + det_h / 2 - 15,
                  f"M4 thru-hole ({M4_HOLE:.1f}mm)", size=9, fill="#495057")
    s += svg_line(bolt_cx + bolt_w_px / 2 + 2, det_top + det_h / 2 - 10,
                  bolt_cx + bolt_w_px / 2 + 28, det_top + det_h / 2 - 18,
                  stroke="#495057", sw=0.8)

    s += svg_text(bolt_cx + ins_w_px / 2 + 30, det_bot - ins_d_px / 2,
                  f"Insert pocket ({INSERT_OD:.0f}mm OD)", size=9,
                  fill="#d9480f")
    s += svg_line(bolt_cx + ins_w_px / 2 + 2, det_bot - ins_d_px / 2 - 5,
                  bolt_cx + ins_w_px / 2 + 28, det_bot - ins_d_px / 2 - 5,
                  stroke="#d9480f", sw=0.8)

    # Callout labels
    s += svg_text(det_cx - det_w / 2, det_bot + 14,
                  "CAP UNDERSIDE (faces shell)", size=8, fill=CLR_DIM)
    s += svg_text(det_cx - det_w / 2, det_top - 20,
                  "CAP TOP (faces lid + weather)", size=8, fill=CLR_DIM)

    # =================================================================
    # FOAM ANCHOR TOOTH DETAIL (right of bolt detail)
    # =================================================================
    ft_cx = 470       # center X of foam tooth detail
    ft_top = det_top  # align with bolt detail
    ft_h = det_h      # same cap thickness representation
    ft_bot = ft_top + ft_h
    ft_w = 200

    s += svg_text(ft_cx, ft_top - 30, "FOAM ANCHOR TOOTH DETAIL",
                  size=11, fill="#8B6914", anchor="middle", weight="bold")
    s += svg_text(ft_cx, ft_top - 16, "(cross-section, not to scale)",
                  size=8, fill=CLR_DIM, anchor="middle")

    # Cap body slice
    s += svg_rect(ft_cx - ft_w / 2, ft_top, ft_w, ft_h,
                  fill=CLR_S1_FILL, stroke=CLR_S1, sw=2)
    s += svg_text(ft_cx - ft_w / 2 + 6, ft_top + 14,
                  "CAP FLANGE", size=8, fill=CLR_S1_DARK, weight="bold")

    # Tooth hanging down from cap underside
    tooth_px_w = 40   # tooth width (along perimeter) in pixels
    tooth_px_h = 70   # tooth depth (protrusion) in pixels
    tooth_px_thick = 90  # tooth thickness (radial) in pixels

    s += svg_rect(ft_cx - tooth_px_thick / 2, ft_bot,
                  tooth_px_thick, tooth_px_h,
                  fill="#fff3e0", stroke="#8B6914", sw=2)

    # Hatching inside tooth
    for hy in range(int(ft_bot) + 5, int(ft_bot + tooth_px_h) - 3, 6):
        s += svg_line(ft_cx - tooth_px_thick / 2 + 3, hy,
                      ft_cx + tooth_px_thick / 2 - 3, hy,
                      stroke="#c68c00", sw=1)

    s += svg_text(ft_cx, ft_bot + tooth_px_h / 2 + 4,
                  "TOOTH", size=9, fill="#8B6914",
                  anchor="middle", weight="bold")

    # Shell walls on either side (S1 inner left, S2 outer right)
    wall_w = 20
    wall_h = ft_h + tooth_px_h + 20
    # S1 inner wall (left)
    s += svg_rect(ft_cx - tooth_px_thick / 2 - 8 - wall_w,
                  ft_top - 10, wall_w, wall_h,
                  fill=CLR_S1_FILL, stroke=CLR_S1, sw=1.5)
    s += svg_text(ft_cx - tooth_px_thick / 2 - 8 - wall_w / 2,
                  ft_top + wall_h - 15,
                  "S1", size=7, fill=CLR_S1_DARK, anchor="middle")

    # S2 outer wall (right)
    s += svg_rect(ft_cx + tooth_px_thick / 2 + 8,
                  ft_top - 10, wall_w, wall_h,
                  fill=CLR_S2_FILL, stroke=CLR_S2, sw=1.5)
    s += svg_text(ft_cx + tooth_px_thick / 2 + 8 + wall_w / 2,
                  ft_top + wall_h - 15,
                  "S2", size=7, fill=CLR_S2_DARK, anchor="middle")

    # Foam fill around tooth (dotted fill suggestion)
    foam_left = ft_cx - tooth_px_thick / 2 - 8
    foam_right = ft_cx + tooth_px_thick / 2 + 8
    s += svg_rect(foam_left, ft_bot + tooth_px_h,
                  foam_right - foam_left, 20,
                  fill=CLR_FOAM, stroke=CLR_FOAM_STROKE, sw=1, rx=0, opacity=0.6)
    s += svg_text(ft_cx, ft_bot + tooth_px_h + 14,
                  "FOAM (cured)", size=7, fill=CLR_FOAM_STROKE, anchor="middle")

    # Dimension: tooth depth
    td_x = ft_cx + tooth_px_thick / 2 + 40
    s += svg_line(td_x - 3, ft_bot, td_x + 3, ft_bot,
                  stroke="#8B6914", sw=1)
    s += svg_line(td_x - 3, ft_bot + tooth_px_h, td_x + 3, ft_bot + tooth_px_h,
                  stroke="#8B6914", sw=1)
    s += svg_line(td_x, ft_bot, td_x, ft_bot + tooth_px_h,
                  stroke="#8B6914", sw=1)
    s += svg_text(td_x + 5, ft_bot + tooth_px_h / 2 + 4,
                  f"{FOAM_TOOTH_D:.0f}mm", size=9, fill="#8B6914", weight="bold")

    # Dimension: tooth thickness (radial)
    s += svg_dim_h(ft_cx - tooth_px_thick / 2, ft_cx + tooth_px_thick / 2,
                   ft_bot + tooth_px_h + 30, color="#8B6914",
                   label=f"{FOAM_TOOTH_THICK:.0f}mm (fills gap)")

    # Clearance arrows
    s += svg_text(ft_cx - tooth_px_thick / 2 - 4,
                  ft_bot + tooth_px_h / 2 + 4,
                  "2mm", size=7, fill="#999", anchor="end")
    s += svg_text(ft_cx + tooth_px_thick / 2 + 4,
                  ft_bot + tooth_px_h / 2 + 4,
                  "2mm", size=7, fill="#999")

    # --- How-it-works callout box ---
    hw_x = 20
    hw_y = max(det_bot, ft_bot + tooth_px_h + 50) + 10
    s += svg_rect(hw_x, hw_y, 540, 115, fill="#f8f9fa", stroke="#dee2e6",
                  sw=1, rx=4)
    s += svg_text(hw_x + 10, hw_y + 16,
                  "HOW IT WORKS:", size=10, fill=CLR_TEXT, weight="bold")
    s += svg_text(hw_x + 10, hw_y + 32,
                  f"1. Drill {M4_HOLE:.1f}mm through-holes + counterbore "
                  f"{INSERT_OD:.0f}x{INSERT_DEPTH:.0f}mm insert pockets "
                  f"(see bolt detail left)",
                  size=9, fill="#555")
    s += svg_text(hw_x + 10, hw_y + 46,
                  "2. Press M4 brass heat-set inserts with soldering iron at 220-240C",
                  size=9, fill="#555")
    s += svg_text(hw_x + 10, hw_y + 60,
                  f"3. Foam teeth ({FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm) "
                  f"are printed as part of the cap \u2014 no assembly needed",
                  size=9, fill="#555")
    s += svg_text(hw_x + 10, hw_y + 74,
                  "4. Place cap on shells while PU foam is still wet \u2014 teeth embed in foam",
                  size=9, fill="#555")
    s += svg_text(hw_x + 10, hw_y + 88,
                  "5. Foam cures around teeth: permanent alignment + mechanical interlock + seal",
                  size=9, fill="#555")
    s += svg_text(hw_x + 10, hw_y + 102,
                  "6. M4 bolts through cap + lid compress gaskets for weather seal",
                  size=9, fill="#555")

    # --- WORKFLOW STEPS ---
    steps = [
        "1. Import DXF profiles",
        "   File > Insert > Insert DXF",
        "   Select 7_cap_top_view.dxf (plan outline)",
        "   Select 8_cap_profile.dxf (cross-section)",
        "",
        f"2. Extrude cap rim: {CAP_THICK:.0f}mm upward",
        f"   Cap is FLUSH with Shell 1 outer ({CAP_OUTER_W:.0f}x{CAP_OUTER_D:.0f}mm)",
        f"   Inner lip drops inside Shell 2 for centering",
        "",
        "3. Cut dual gasket grooves into cap top surface",
        f"   {CAP_GASKET_W:.0f}mm wide x {CAP_GASKET_D:.1f}mm deep (Extrude > Cut)",
        "",
        f"4. Drill M4 bolt through-holes ({M4_HOLE:.1f}mm dia)",
        f"   Between gaskets, ~{CAP_BOLT_SPACING:.0f}mm spacing",
        "",
        f"5. Counterbore {INSERT_OD:.0f}mm x {INSERT_DEPTH:.0f}mm insert pockets",
        "   From cap underside \u2014 press M4 brass heat-set inserts",
        "",
        f"6. Add foam anchor teeth on flange underside",
        f"   {FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm, "
        f"every {FOAM_TOOTH_SPACING:.0f}mm",
        "   Fill foam gap for alignment + cure into foam",
        "",
        "7. May split into panels for print bed if needed",
    ]

    step_y = hw_y + 135
    box_h = 30 + len(steps) * 22 + 10
    s += svg_rect(15, step_y - 10, W - 30, box_h, fill=CLR_BG_BOX,
                  stroke="#dee2e6", sw=1, rx=4)
    s += svg_text(30, step_y + 10,
                  "FUSION 360 WORKFLOW", size=14, fill=CLR_TEXT, weight="bold")

    for i, step_text in enumerate(steps):
        s += svg_text(40, step_y + 35 + i * 22, step_text,
                      size=11, fill=CLR_TEXT)

    s += svg_footer()
    write_svg("cap_extrusion.svg", s)


# ---------------------------------------------------------------------------
# LID EXTRUSION GUIDE
# ---------------------------------------------------------------------------

def generate_lid_extrusion():
    W, H = 1100, 750
    s = svg_header(W, H)

    s += svg_text(20, 30, "SATELLITE UNIT \u2014 LID EXTRUSION (Rev 3.2)",
                  size=18, fill=CLR_TEXT, weight="bold")
    s += svg_text(20, 50,
                  f"Lid: {LID_W:.0f} x {LID_D:.0f}mm  |  "
                  f"Body: {LID_THICK:.0f}mm (20% infill = insulation)  |  "
                  f"Skirt: {LID_SKIRT:.0f}mm  |  "
                  f"Overhang: {LID_OVERHANG:.0f}mm past cap rim",
                  size=11, fill=CLR_DIM)

    # --- Plan view ---
    plan_scale = min(400 / LID_W, 300 / LID_D)
    lw = LID_W * plan_scale
    ld = LID_D * plan_scale
    px = 60
    py = 130

    s += svg_text(px + lw / 2, py - 15, "PLAN VIEW (lid outline + cap rim ref)",
                  size=13, fill=CLR_TEXT, anchor="middle", weight="bold")

    # Lid outline
    s += svg_rect(px, py, lw, ld, fill=CLR_LID_FILL, stroke=CLR_LID, sw=2.5)

    # Cap rim reference
    cw = CAP_OUTER_W * plan_scale
    cd = CAP_OUTER_D * plan_scale
    cx = px + (lw - cw) / 2
    cy = py + (ld - cd) / 2
    s += svg_rect(cx, cy, cw, cd, fill="none", stroke=CLR_CAP, sw=1.5)

    # Shell 1 reference
    sw_s1 = OUTER_W * plan_scale
    sd_s1 = OUTER_D * plan_scale
    sx = px + (lw - sw_s1) / 2
    sy = py + (ld - sd_s1) / 2
    s += svg_rect(sx, sy, sw_s1, sd_s1, fill="none", stroke=CLR_S1, sw=1)

    # Labels
    s += svg_text(px + lw / 2, py - 3,
                  f"Lid: {LID_W:.0f} x {LID_D:.0f}mm",
                  size=10, fill=CLR_LID_DARK, anchor="middle", weight="bold")
    s += svg_text(px + lw / 2, py + ld / 2 + 4,
                  f"Cap rim: {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f}mm",
                  size=9, fill=CLR_CAP_DARK, anchor="middle")

    # Overhang dim
    s += svg_dim_h(px, cx, py + ld + 20,
                   f"{LID_OVERHANG:.0f}mm overhang", color=CLR_LID_DARK)

    # Outer dims
    s += svg_dim_h(px, px + lw, py + ld + 50,
                   f"{LID_W:.0f}mm", color=CLR_LID_DARK)
    s += svg_dim_v(px + lw + 15, py, py + ld,
                   f"{LID_D:.0f}mm", color=CLR_LID_DARK)

    # Source DXF
    s += svg_text(px + lw / 2, py + ld + 80,
                  "Source: 9_lid_top_view.dxf + 8_cap_profile.dxf",
                  size=10, fill=CLR_DIM, anchor="middle")

    # --- Side profile ---
    side_x = 620
    side_y = 180
    side_scale = min(300 / LID_W, 200 / (LID_THICK + LID_SKIRT))

    body_w = LID_W * side_scale
    body_h = LID_THICK * side_scale
    skirt_h = LID_SKIRT * side_scale
    total_h = body_h + skirt_h

    s += svg_text(side_x + body_w / 2, side_y - 30,
                  "SIDE PROFILE (body + skirt)",
                  size=13, fill=CLR_TEXT, anchor="middle", weight="bold")

    # Lid body
    s += svg_rect(side_x, side_y, body_w, body_h,
                  fill=CLR_LID_FILL, stroke=CLR_LID, sw=2.5)

    # Skirts (left and right)
    skirt_w = max(8 * side_scale, 8)
    s += svg_rect(side_x, side_y + body_h, skirt_w, skirt_h,
                  fill=CLR_LID_FILL, stroke=CLR_LID, sw=2)
    s += svg_rect(side_x + body_w - skirt_w, side_y + body_h,
                  skirt_w, skirt_h,
                  fill=CLR_LID_FILL, stroke=CLR_LID, sw=2)

    # Cap rim reference below
    cap_w = CAP_OUTER_W * side_scale
    cap_x = side_x + (body_w - cap_w) / 2
    cap_h = max(CAP_THICK * side_scale, 4)
    s += svg_rect(cap_x, side_y + body_h, cap_w, cap_h,
                  fill="none", stroke=CLR_CAP, sw=1.5)
    s += svg_text(cap_x + cap_w / 2, side_y + body_h + cap_h + 15,
                  "Cap rim (below lid)", size=9, fill=CLR_CAP_DARK, anchor="middle")

    # Dimensions
    s += svg_dim_v(side_x + body_w + 15, side_y, side_y + body_h,
                   f"Body {LID_THICK:.0f}mm", color=CLR_LID_DARK)
    s += svg_dim_v(side_x + body_w + 15, side_y + body_h,
                   side_y + body_h + skirt_h,
                   f"Skirt {LID_SKIRT:.0f}mm", color=CLR_LID_DARK)
    s += svg_text(side_x + body_w / 2, side_y + total_h + 40,
                  f"{LID_W:.0f}mm", size=10, fill=CLR_LID_DARK, anchor="middle")

    # --- Workflow ---
    step_y = 520
    s += svg_rect(15, step_y - 10, W - 30, 200, fill=CLR_BG_BOX,
                  stroke="#dee2e6", sw=1, rx=4)
    s += svg_text(30, step_y + 10,
                  "FUSION 360 WORKFLOW", size=14, fill=CLR_TEXT, weight="bold")

    steps = [
        "1. Import 9_lid_top_view.dxf \u2192 Insert > Insert DXF (select XY plane at Z = top of cap rim)",
        f"2. Extrude lid body: select outer rectangle, Extrude Z = {LID_THICK:.0f}mm upward (New Body)",
        f"3. Extrude rain skirt: select perimeter ring, Extrude Z = {LID_SKIRT:.0f}mm downward (Join)",
        "4. Cut drip edge groove on skirt underside: 3mm inset, 3mm deep, 2mm wide channel (Extrude > Cut)",
        f"5. Cut M4 bolt through-holes from 9_lid_top_view.dxf (Extrude > Cut > All) — threads into {INSERT_OD:.0f}mm inserts in cap",
        "6. Chamfer top edges: Modify > Chamfer 3mm on all top perimeter edges",
        f"7. Verify: {LID_W:.0f} x {LID_D:.0f}mm, body {LID_THICK:.0f}mm, "
        f"skirt {LID_SKIRT:.0f}mm, overhang {LID_OVERHANG:.0f}mm",
        "8. Print: ASA, 20% infill (trapped air = insulation), no foam behind lid",
    ]
    for i, step_text in enumerate(steps):
        s += svg_text(40, step_y + 35 + i * 22, step_text,
                      size=11, fill=CLR_TEXT)

    s += svg_footer()
    write_svg("lid_extrusion.svg", s)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating Satellite Unit extrusion guide SVGs (Rev 3.2)...")
    print(f"Output: {OUTPUT_DIR}")
    print()
    print("Dimensions:")
    print(f"  Shell 1 (ASA):   {OUTER_W:.0f} x {OUTER_D:.0f} x {OUTER_H:.0f}mm  Z={S1_Z}")
    print(f"  Shell 2 (PETG):  {MID_W:.0f} x {MID_D:.0f} x {MID_H:.0f}mm  Z={S2_Z:.0f}")
    print(f"  Cap:             {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f} x {CAP_THICK:.0f}mm")
    print(f"  Lid:             {LID_W:.0f} x {LID_D:.0f} x {LID_THICK:.0f}mm")
    print()

    generate_extrusion_overview()

    # Conduit positions on right face (right edge of plan view)
    # (x_frac, y_frac, dia_mm, label) — x_frac ~1.0 = right edge
    right_conduits = [
        (0.92, 0.35, 16, "LEADS"),
        (0.92, 0.55, 10, "12V"),
        (0.92, 0.70, 8, "PROBE"),
        (0.92, 0.50, 80, "FAN"),
    ]

    generate_shell_extrusion(
        "shell1_extrusion.svg", 1, "ASA",
        OUTER_W, OUTER_D, OUTER_H, S1_Z,
        "1_top_view.dxf", CLR_S1, CLR_S1_DARK, CLR_S1_FILL,
        WALL, conduits=right_conduits
    )

    generate_shell_extrusion(
        "shell2_extrusion.svg", 2, "PETG",
        MID_W, MID_D, MID_H, S2_Z,
        "1_top_view.dxf", CLR_S2, CLR_S2_DARK, CLR_S2_FILL,
        WALL_S2, conduits=right_conduits
    )

    generate_cap_extrusion()
    generate_lid_extrusion()

    print()
    print("Done. Open SVGs in browser or Fusion reference panel.")


if __name__ == "__main__":
    main()
