#!/usr/bin/env python3
"""
Generate annotated SVG extrusion guide images for the Main Unit enclosure (Rev 3.2).

Shows how to go from 2D DXF profiles to 3D bodies in Fusion 360, with
color-coded shells, dimension annotations, and step-by-step workflow.

Usage:
    python cad/main_unit/generate_extrusion_guides.py

Output:
    cad/main_unit/guides/extrusion_overview.svg
    cad/main_unit/guides/shell1_extrusion.svg   (ASA outer)
    cad/main_unit/guides/shell2_extrusion.svg   (PETG structural)
    cad/main_unit/guides/cap_extrusion.svg      (Cap rim)
    cad/main_unit/guides/lid_extrusion.svg      (Lid)
"""

import os

# ---------------------------------------------------------------------------
# PARAMETRIC DIMENSIONS —must match generate_dxf.py
# ---------------------------------------------------------------------------

CELL_L = 129.0
CELL_W = 36.0
CELL_H = 256.0
TERMINAL_H = 4.0
CELLS_S = 4
CELLS_P = 2
STACK_W = CELLS_S * CELL_W + (CELLS_S - 1) * 2 + 8       # 158
STACK_D = CELLS_P * CELL_L + (CELLS_P - 1) * 10            # 268
STACK_H = CELL_H + TERMINAL_H + 30.0                        # 290

ELEC_ZONE_W = 320.0
ELEC_ZONE_D = STACK_D
MPPT_PANEL_H = 2 * 76.0 + 30.0    # two rows of MPPT + gap = 182
BMS_H = 80.0
ELEC_ZONE_H = max(MPPT_PANEL_H + BMS_H + 50, STACK_H)  # 312

WALL = 5.0
WALL_S2 = 5.0    # Shell 2 wall thickness
FOAM = 30.0
ZONE_GAP = 20.0
ZONE_MARGIN = 10.0
BASE_THICK = WALL

# Rib and spacer nub dimensions
RIB_W = 3.0
RIB_H = 10.0
RIB_SPACING = 100.0
NUB_W = 15.0
NUB_H = 30.0  # full foam gap

# Interior component space
INNER_W = 2 * ZONE_MARGIN + STACK_W + ZONE_GAP + ELEC_ZONE_W  # 518
INNER_D = max(STACK_D, ELEC_ZONE_D) + 2 * ZONE_MARGIN          # 288
INNER_H = max(STACK_H, ELEC_ZONE_H) + BASE_THICK               # 315

# Structural shell (Shell 2) — wraps directly around component space
MID_W = INNER_W + 2 * WALL_S2   # 526
MID_D = INNER_D + 2 * WALL_S2   # 296
MID_H = INNER_H + WALL_S2       # 319

# Outer (Shell 1)
OUTER_W = MID_W + 2 * (FOAM + WALL)  # 600
OUTER_D = MID_D + 2 * (FOAM + WALL)  # 370
OUTER_H = MID_H + FOAM + WALL + BASE_THICK  # 359

# Cap — flush with S1 outer, inner lip slips inside S2
CAP_LIP = 0.0
CAP_THICK = 8.0
CAP_OUTER_W = OUTER_W + 2 * CAP_LIP  # = OUTER_W (flush)
CAP_OUTER_D = OUTER_D + 2 * CAP_LIP  # = OUTER_D (flush)

# Lid (thick for insulation — infill replaces foam)
LID_THICK = 25.0
LID_OVERHANG = 15.0
LID_SKIRT = 20.0
LID_W = CAP_OUTER_W + 2 * LID_OVERHANG
LID_D = CAP_OUTER_D + 2 * LID_OVERHANG

# Gasket / bolt / insert (must match generate_dxf.py)
CAP_GASKET_W = 4.0         # gasket cord diameter / groove width
CAP_GASKET_D = 2.5         # groove depth cut into cap top surface
CAP_GASKET_MARGIN = 3.0    # margin from foam edge to gasket center
CAP_BOLT_SPACING = 90.0
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
# COLOUR THEME
# ---------------------------------------------------------------------------

SHELL1_CLR = "#ff6b6b"
SHELL1_CLR_DARK = "#cc3333"
SHELL1_BG = "#fff0f0"

SHELL2_CLR = "#51cf66"
SHELL2_CLR_DARK = "#2b8a3e"
SHELL2_BG = "#f0fff4"

FOAM_CLR = "#ff922b"
FOAM_CLR_DARK = "#d9480f"
FOAM_BG = "#fff4e6"
NUB_CLR = "#c2410c"  # darker orange for spacer nubs

CAP_CLR = "#ff922b"
CAP_CLR_DARK = "#d9480f"
CAP_BG = "#fff4e6"

LID_CLR = "#be4bdb"
LID_CLR_DARK = "#862e9c"
LID_BG = "#f8f0fc"

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


def svg_text(x, y, text, size=11, fill="#333", anchor="start", bold=False):
    fw = "bold" if bold else "normal"
    # Escape XML entities
    text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'  <text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{fw}">{text}</text>\n'
    )


def svg_rect(x, y, w, h, fill="none", stroke="#333", sw=1.5, rx=0, opacity=1.0):
    return (
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
        f'opacity="{opacity}" rx="{rx}"/>\n'
    )


def svg_line(x1, y1, x2, y2, stroke="#333", sw=1.5, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="{sw}"{d}/>\n'
    )


def svg_arrow_v(x, y_top, y_bot, color="#333", sw=1.5, head=8):
    """Vertical arrow with heads at both ends."""
    lines = ""
    # Shaft
    lines += svg_line(x, y_top, x, y_bot, stroke=color, sw=sw)
    # Top head (pointing up)
    lines += (
        f'  <polygon points="{x},{y_top} {x - head / 2},{y_top + head} '
        f'{x + head / 2},{y_top + head}" fill="{color}"/>\n'
    )
    # Bottom head (pointing down)
    lines += (
        f'  <polygon points="{x},{y_bot} {x - head / 2},{y_bot - head} '
        f'{x + head / 2},{y_bot - head}" fill="{color}"/>\n'
    )
    return lines


def svg_arrow_up(x, y_bot, y_top, color="#333", sw=1.5, head=8):
    """Single-headed arrow pointing up."""
    lines = svg_line(x, y_bot, x, y_top, stroke=color, sw=sw)
    lines += (
        f'  <polygon points="{x},{y_top} {x - head / 2},{y_top + head} '
        f'{x + head / 2},{y_top + head}" fill="{color}"/>\n'
    )
    return lines


def svg_circle(cx, cy, r, fill="none", stroke="#333", sw=1.5):
    return (
        f'  <circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>\n'
    )


def svg_dim_h(x1, x2, y, color="#555", label="", offset=15):
    """Horizontal dimension line with label."""
    lines = ""
    lines += svg_line(x1, y, x2, y, stroke=color, sw=1)
    # Tick marks
    lines += svg_line(x1, y - 4, x1, y + 4, stroke=color, sw=1)
    lines += svg_line(x2, y - 4, x2, y + 4, stroke=color, sw=1)
    if label:
        cx = (x1 + x2) / 2
        lines += svg_text(cx, y - 5, label, size=9, fill=color, anchor="middle")
    return lines


def svg_dim_v(x, y1, y2, color="#555", label="", offset=15):
    """Vertical dimension line with label."""
    lines = ""
    lines += svg_line(x, y1, x, y2, stroke=color, sw=1)
    lines += svg_line(x - 4, y1, x + 4, y1, stroke=color, sw=1)
    lines += svg_line(x - 4, y2, x + 4, y2, stroke=color, sw=1)
    if label:
        cy = (y1 + y2) / 2
        lines += svg_text(x + offset, cy + 4, label, size=9, fill=color, anchor="start")
    return lines


def write_svg(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# 1. EXTRUSION OVERVIEW
# ---------------------------------------------------------------------------

def gen_overview(out_dir):
    W, H = 1100, 870
    svg = svg_header(W, H)

    # Title
    svg += svg_text(20, 30, "MAIN UNIT —EXTRUSION OVERVIEW (Rev 3.2)",
                    size=18, fill="#333", bold=True)
    svg += svg_text(20, 50,
                    "Front cross-section showing nested shells, foam cavity, and Z-offsets",
                    size=11, fill="#555")

    # --- Cross-section drawing area ---
    # We'll draw a front cross-section (width x height) centered
    # Scale: fit OUTER_W(600) + margins into ~700px
    scale = 700 / OUTER_W  # ~1.167
    cx = 420  # center X of drawing
    base_y = 680  # bottom of shells (SVG y)

    def sx(mm):
        return cx - (OUTER_W / 2) * scale + mm * scale

    def sy(mm):
        return base_y - mm * scale

    # Shell 1 (outer)
    s1_x = sx(0)
    s1_y = sy(OUTER_H)
    s1_w = OUTER_W * scale
    s1_h = OUTER_H * scale
    svg += svg_rect(s1_x, s1_y, s1_w, s1_h,
                    fill=SHELL1_BG, stroke=SHELL1_CLR, sw=2.5, rx=2)

    # Foam cavity (between S1 inner wall and S2 outer wall)
    foam_x = sx(WALL)
    foam_y = sy(OUTER_H - BASE_THICK)  # foam starts above S1 base
    foam_w = (OUTER_W - 2 * WALL) * scale
    foam_h = (OUTER_H - BASE_THICK - WALL) * scale  # up to S1 top inner
    svg += svg_rect(foam_x, foam_y, foam_w, foam_h,
                    fill=FOAM_BG, stroke=FOAM_CLR, sw=1.5, rx=1)
    # Label foam
    svg += svg_text(foam_x + foam_w / 2, foam_y + 15, "FOAM (30mm)",
                    size=9, fill=FOAM_CLR_DARK, anchor="middle", bold=True)

    # Shell 2 (mid) —positioned at Z-offset S2_Z
    s2_offset_x = (FOAM + WALL)  # horizontal offset from outer edge
    s2_x = sx(s2_offset_x)
    s2_y = sy(S2_Z + MID_H)
    s2_w = MID_W * scale
    s2_h = MID_H * scale
    svg += svg_rect(s2_x, s2_y, s2_w, s2_h,
                    fill=SHELL2_BG, stroke=SHELL2_CLR, sw=2.5, rx=2)

    # --- Foam-pressure ribs ---
    # S1 inner wall ribs (left and right), protruding inward into foam
    rib_start_z = 50.0  # start ~50mm from base
    for i in range(3):
        rib_z = rib_start_z + i * RIB_SPACING
        rib_y_svg = sy(rib_z + RIB_W)  # top of rib in SVG coords
        rib_h_svg = RIB_W * scale
        rib_w_svg = RIB_H * scale
        # Left side: S1 inner wall = WALL, ribs protrude rightward into foam
        svg += svg_rect(sx(WALL), rib_y_svg, rib_w_svg, rib_h_svg,
                        fill=FOAM_CLR, stroke=FOAM_CLR_DARK, sw=0.8, opacity=0.8)
        # Right side: S1 inner wall = OUTER_W - WALL, ribs protrude leftward
        svg += svg_rect(sx(OUTER_W - WALL) - rib_w_svg, rib_y_svg, rib_w_svg, rib_h_svg,
                        fill=FOAM_CLR, stroke=FOAM_CLR_DARK, sw=0.8, opacity=0.8)

    # S2 outer wall ribs (left and right), protruding outward into foam
    for i in range(3):
        rib_z = rib_start_z + i * RIB_SPACING
        rib_y_svg = sy(S2_Z + rib_z + RIB_W)
        rib_h_svg = RIB_W * scale
        rib_w_svg = RIB_H * scale
        # Left side: S2 outer wall = WALL + FOAM, ribs protrude leftward
        svg += svg_rect(sx(WALL + FOAM) - rib_w_svg, rib_y_svg, rib_w_svg, rib_h_svg,
                        fill=FOAM_CLR, stroke=FOAM_CLR_DARK, sw=0.8, opacity=0.8)
        # Right side: S2 outer wall = OUTER_W - WALL - FOAM, ribs protrude rightward
        svg += svg_rect(sx(OUTER_W - WALL - FOAM), rib_y_svg, rib_w_svg, rib_h_svg,
                        fill=FOAM_CLR, stroke=FOAM_CLR_DARK, sw=0.8, opacity=0.8)

    # Label ribs
    svg += svg_text(sx(WALL) + RIB_H * scale + 4,
                    sy(rib_start_z + RIB_W / 2) + 4,
                    "RIBS", size=7, fill=FOAM_CLR_DARK, bold=True)

    # --- Spacer nubs (S1 inner wall, spanning full foam gap) ---
    # Place 2 nubs on each side, between rib rows
    nub_positions_z = [rib_start_z + 40, rib_start_z + RIB_SPACING + 40]
    for nub_z in nub_positions_z:
        nub_y_svg = sy(nub_z + NUB_W)
        nub_h_svg = NUB_W * scale
        nub_w_svg = NUB_H * scale
        # Left side
        svg += svg_rect(sx(WALL), nub_y_svg, nub_w_svg, nub_h_svg,
                        fill=NUB_CLR, stroke=NUB_CLR, sw=0.8, opacity=0.7)
        # Right side
        svg += svg_rect(sx(OUTER_W - WALL) - nub_w_svg, nub_y_svg, nub_w_svg, nub_h_svg,
                        fill=NUB_CLR, stroke=NUB_CLR, sw=0.8, opacity=0.7)

    # Label nubs
    svg += svg_text(sx(WALL) + NUB_H * scale + 4,
                    sy(nub_positions_z[0] + NUB_W / 2) + 4,
                    "NUBS", size=7, fill=NUB_CLR, bold=True)

    # --- Shell labels inside ---
    svg += svg_text(s1_x + 8, s1_y + 18, "S1 (ASA)", size=10,
                    fill=SHELL1_CLR_DARK, bold=True)
    svg += svg_text(s2_x + 8, s2_y + 18, "S2 (PETG)", size=10,
                    fill=SHELL2_CLR_DARK, bold=True)

    # --- Extrusion height arrows on right side ---
    arrow_x_base = sx(OUTER_W) + 30

    # S1 arrow
    a1_x = arrow_x_base
    svg += svg_arrow_v(a1_x, s1_y, base_y, color=SHELL1_CLR, sw=2)
    svg += svg_text(a1_x + 8, (s1_y + base_y) / 2 + 4,
                    f"{OUTER_H:.0f}mm", size=10, fill=SHELL1_CLR_DARK, bold=True)

    # S2 arrow
    a2_x = arrow_x_base + 55
    s2_bot = sy(S2_Z)
    s2_top = s2_y
    svg += svg_arrow_v(a2_x, s2_top, s2_bot, color=SHELL2_CLR, sw=2)
    svg += svg_text(a2_x + 8, (s2_top + s2_bot) / 2 + 4,
                    f"{MID_H:.0f}mm", size=10, fill=SHELL2_CLR_DARK, bold=True)

    # --- Z-offset labels on left side ---
    zlab_x = s1_x - 15

    # S1 base = 0
    svg += svg_line(s1_x - 30, base_y, s1_x + 15, base_y,
                    stroke="#999", sw=1, dash="4 2")
    svg += svg_text(zlab_x - 30, base_y + 4, "Z=0mm", size=9,
                    fill="#666", anchor="end")

    # S2 base
    s2_base_y = sy(S2_Z)
    svg += svg_line(s1_x - 30, s2_base_y, s2_x + 15, s2_base_y,
                    stroke="#999", sw=1, dash="4 2")
    svg += svg_text(zlab_x - 30, s2_base_y + 4, f"Z={S2_Z:.0f}mm",
                    size=9, fill="#666", anchor="end")

    # --- Legend ---
    leg_y = 720
    svg += svg_text(20, leg_y, "LEGEND", size=13, fill="#333", bold=True)

    items = [
        (SHELL1_CLR, SHELL1_CLR_DARK,
         f"Shell 1 (ASA outer) —{OUTER_W:.0f} x {OUTER_D:.0f} x {OUTER_H:.0f}mm, Z=0"),
        (SHELL2_CLR, SHELL2_CLR_DARK,
         f"Shell 2 (PETG structural) —{MID_W:.0f} x {MID_D:.0f} x {MID_H:.0f}mm, Z={S2_Z:.0f}"),
        (FOAM_CLR, FOAM_CLR_DARK,
         f"Foam cavity —30mm insulation between S1 and S2"),
        (FOAM_CLR, FOAM_CLR_DARK,
         f"Foam-pressure ribs —{RIB_W:.0f}mm x {RIB_H:.0f}mm, spaced {RIB_SPACING:.0f}mm, on S1 inner + S2 outer"),
        (NUB_CLR, NUB_CLR,
         f"Spacer nubs —{NUB_W:.0f}mm x {NUB_H:.0f}mm (full foam gap), S1 inner wall"),
    ]
    for i, (clr, clr_dk, label) in enumerate(items):
        iy = leg_y + 20 + i * 22
        svg += svg_rect(25, iy - 10, 14, 14, fill=clr, stroke=clr_dk, sw=1, rx=2)
        svg += svg_text(48, iy + 2, label, size=10, fill="#333")

    svg += svg_footer()
    write_svg(os.path.join(out_dir, "extrusion_overview.svg"), svg)


# ---------------------------------------------------------------------------
# SHELL EXTRUSION CARD (template for S1, S2, S3)
# ---------------------------------------------------------------------------

def gen_shell_card(out_dir, filename, shell_num, material, color, color_dark,
                   bg_color, plan_w, plan_d, ext_h, z_offset, wall_thick,
                   dxf_file, shell_cmd_note, conduits=None):
    W, H = 1100, 750
    svg = svg_header(W, H)

    title = f"SHELL {shell_num} ({material}) —EXTRUSION GUIDE (Rev 3.2)"
    svg += svg_text(20, 30, title, size=18, fill="#333", bold=True)
    svg += svg_text(20, 50,
                    f"Plan: {plan_w:.0f} x {plan_d:.0f}mm  |  "
                    f"Height: {ext_h:.0f}mm  |  Z-offset: {z_offset:.0f}mm",
                    size=12, fill="#555")

    # --- TOP: Plan view ---
    svg += svg_text(20, 90, "PLAN VIEW (top-down)", size=13, fill="#333", bold=True)

    # Scale plan to fit in ~450px wide area
    plan_scale = min(400 / plan_w, 250 / plan_d)
    plan_cx = 280
    plan_cy = 230
    pr_w = plan_w * plan_scale
    pr_d = plan_d * plan_scale
    pr_x = plan_cx - pr_w / 2
    pr_y = plan_cy - pr_d / 2

    svg += svg_rect(pr_x, pr_y, pr_w, pr_d,
                    fill=bg_color, stroke=color, sw=2.5, rx=3)
    svg += svg_text(plan_cx, plan_cy + 4,
                    f"{plan_w:.0f} x {plan_d:.0f}mm",
                    size=12, fill=color_dark, anchor="middle", bold=True)

    # Dimension lines for plan
    svg += svg_dim_h(pr_x, pr_x + pr_w, pr_y - 20, color="#555",
                     label=f"{plan_w:.0f}mm")
    svg += svg_dim_v(pr_x - 20, pr_y, pr_y + pr_d, color="#555",
                     label=f"{plan_d:.0f}mm", offset=-55)

    # --- Rib tick marks and nub squares on plan view ---
    tick_len = 6  # pixels
    tick_sw = 1.2
    # Rib positions as fraction of perimeter edges (3 per side)
    rib_fracs = [0.2, 0.45, 0.7]

    if shell_num == 1:
        # Inner perimeter ticks (ribs protrude inward)
        for frac in rib_fracs:
            # Left edge (ticks pointing right/inward)
            ty = pr_y + frac * pr_d
            svg += svg_line(pr_x, ty, pr_x + tick_len, ty,
                            stroke=color_dark, sw=tick_sw)
            # Right edge (ticks pointing left/inward)
            svg += svg_line(pr_x + pr_w, ty, pr_x + pr_w - tick_len, ty,
                            stroke=color_dark, sw=tick_sw)
            # Top edge (ticks pointing down/inward)
            tx = pr_x + frac * pr_w
            svg += svg_line(tx, pr_y, tx, pr_y + tick_len,
                            stroke=color_dark, sw=tick_sw)
            # Bottom edge (ticks pointing up/inward)
            svg += svg_line(tx, pr_y + pr_d, tx, pr_y + pr_d - tick_len,
                            stroke=color_dark, sw=tick_sw)
        # Spacer nub squares at corners
        nub_sq = 5  # pixel size for nub indicator
        corner_offsets = [
            (nub_sq, nub_sq),                          # top-left
            (pr_w - 2 * nub_sq, nub_sq),               # top-right
            (nub_sq, pr_d - 2 * nub_sq),               # bottom-left
            (pr_w - 2 * nub_sq, pr_d - 2 * nub_sq),   # bottom-right
        ]
        for ox, oy in corner_offsets:
            svg += svg_rect(pr_x + ox, pr_y + oy, nub_sq, nub_sq,
                            fill=NUB_CLR, stroke=NUB_CLR, sw=0.5, opacity=0.6)

    elif shell_num == 2:
        # Outer perimeter ticks (ribs protrude outward)
        for frac in rib_fracs:
            # Left edge (ticks pointing left/outward)
            ty = pr_y + frac * pr_d
            svg += svg_line(pr_x, ty, pr_x - tick_len, ty,
                            stroke=color_dark, sw=tick_sw)
            # Right edge (ticks pointing right/outward)
            svg += svg_line(pr_x + pr_w, ty, pr_x + pr_w + tick_len, ty,
                            stroke=color_dark, sw=tick_sw)
            # Top edge (ticks pointing up/outward)
            tx = pr_x + frac * pr_w
            svg += svg_line(tx, pr_y, tx, pr_y - tick_len,
                            stroke=color_dark, sw=tick_sw)
            # Bottom edge (ticks pointing down/outward)
            svg += svg_line(tx, pr_y + pr_d, tx, pr_y + pr_d + tick_len,
                            stroke=color_dark, sw=tick_sw)

    # --- Conduit penetrations on plan view ---
    if conduits:
        conduit_clr = "#e64980"  # magenta-pink for visibility
        for c in conduits:
            # c = (x_frac, y_frac, dia_mm, label)
            cx = pr_x + c[0] * pr_w
            cy = pr_y + c[1] * pr_d
            cr = (c[2] / 2) * plan_scale
            cr = max(cr, 3)  # minimum visible radius
            svg += svg_circle(cx, cy, cr, fill="white", stroke=conduit_clr, sw=1.5)
            svg += svg_text(cx, cy + cr + 10, c[3], size=7,
                            fill=conduit_clr, anchor="middle")
        svg += svg_text(pr_x + pr_w / 2, pr_y + pr_d + 35,
                        "Conduit holes — cut after extrusion (see DXF Drawing 4)",
                        size=9, fill=conduit_clr, anchor="middle")

    # --- BOTTOM: Side profile showing extrusion ---
    svg += svg_text(20, 400, "SIDE PROFILE (extrusion direction)", size=13,
                    fill="#333", bold=True)

    prof_scale = min(300 / plan_w, 250 / ext_h)
    prof_cx = 280
    prof_base_y = 680
    pp_w = plan_w * prof_scale
    pp_h = ext_h * prof_scale
    pp_x = prof_cx - pp_w / 2
    pp_y = prof_base_y - pp_h

    # The extruded body
    svg += svg_rect(pp_x, pp_y, pp_w, pp_h,
                    fill=bg_color, stroke=color, sw=2.5, rx=2)
    svg += svg_text(prof_cx, (pp_y + prof_base_y) / 2 + 4,
                    f"Extrude Z = {ext_h:.0f}mm",
                    size=11, fill=color_dark, anchor="middle", bold=True)

    # --- Ribs and nubs on side profile ---
    if shell_num == 1:
        # Ribs on inner surface (right side of rect = inner wall), protruding leftward
        for i in range(3):
            rib_z = 50 + i * RIB_SPACING
            rib_frac = rib_z / ext_h  # fraction up the height
            rib_y_pos = prof_base_y - rib_frac * pp_h - RIB_W * prof_scale
            svg += svg_rect(pp_x + pp_w - RIB_H * prof_scale, rib_y_pos,
                            RIB_H * prof_scale, RIB_W * prof_scale,
                            fill=color, stroke=color_dark, sw=0.8, opacity=0.6)
        # Nubs between ribs (spanning inward, longer)
        for nub_z in [90, 190]:
            nub_frac = nub_z / ext_h
            nub_y_pos = prof_base_y - nub_frac * pp_h - NUB_W * prof_scale
            svg += svg_rect(pp_x + pp_w - NUB_H * prof_scale, nub_y_pos,
                            NUB_H * prof_scale, NUB_W * prof_scale,
                            fill=NUB_CLR, stroke=NUB_CLR, sw=0.8, opacity=0.5)
    elif shell_num == 2:
        # Ribs on outer surface (right side of rect), protruding rightward
        for i in range(3):
            rib_z = 50 + i * RIB_SPACING
            rib_frac = rib_z / ext_h
            rib_y_pos = prof_base_y - rib_frac * pp_h - RIB_W * prof_scale
            svg += svg_rect(pp_x + pp_w, rib_y_pos,
                            RIB_H * prof_scale, RIB_W * prof_scale,
                            fill=color, stroke=color_dark, sw=0.8, opacity=0.6)

    # Extrusion arrow (upward)
    arr_x = pp_x + pp_w + 30
    svg += svg_arrow_up(arr_x, prof_base_y, pp_y - 10, color=color, sw=2, head=10)
    svg += svg_text(arr_x + 12, (pp_y + prof_base_y) / 2 + 4,
                    f"{ext_h:.0f}mm", size=11, fill=color_dark, bold=True)

    # Z-offset baseline label
    svg += svg_line(pp_x - 40, prof_base_y, pp_x + pp_w + 10, prof_base_y,
                    stroke="#999", sw=1, dash="4 2")
    svg += svg_text(pp_x - 45, prof_base_y + 4, f"Z={z_offset:.0f}mm",
                    size=9, fill="#666", anchor="end")

    # Width dimension on profile
    svg += svg_dim_h(pp_x, pp_x + pp_w, prof_base_y + 20, color="#555",
                     label=f"{plan_w:.0f}mm")

    # --- RIGHT: Fusion 360 Workflow Steps ---
    step_x = 600
    svg += svg_rect(580, 75, 490, 610, fill=bg_color, stroke=color, sw=1.5, rx=6)
    svg += svg_text(step_x, 100, "FUSION 360 WORKFLOW", size=14,
                    fill=color_dark, bold=True)

    steps = [
        f"1. Insert DXF > select {dxf_file}",
        f"   (File > Insert > Insert DXF, place at origin)",
        "",
        f"2. Extrude the profile upward",
        f"   Select closed profile > Extrude > Distance = {ext_h:.0f}mm",
        f"   Direction: One Side (positive Z)",
        "",
        f"3. {shell_cmd_note}",
        f"   Modify > Shell > select top face",
        f"   Inside thickness = {wall_thick:.0f}mm",
        "",
        f"4. Position the body at Z-offset",
        f"   Move/Copy > Z translation = {z_offset:.0f}mm",
        f"   (aligns shell base to correct height in assembly)",
        "",
        f"5. Cut conduit holes (Extrude > Cut)",
        f"   Positions per 4_rear_view.dxf",
    ]
    if shell_num == 1:
        steps += [
            "",
            f"6. Add foam-pressure ribs on inner face",
            f"   3mm wide × 10mm protrusion, spaced 100mm vertically",
            f"   Extrude inward from inner surface (Join)",
            "",
            f"7. Add spacer nubs between ribs (inner face → inward 30mm)",
            f"   Sketch pads on inner surface at corner + mid-wall positions",
            f"   Extrude 30mm inward (Join) — full foam gap depth",
            f"   Nubs fit between rib rows, 2 vertical levels",
            "",
            f"8. Add conduit sleeves (5mm-wall tubes, 30mm long)",
            f"   Sketch annular ring around each conduit hole on inner face",
            f"   Extrude 30mm inward (Join) — keeps foam out of conduits",
        ]
    else:
        steps += [
            "",
            f"6. Add foam-pressure ribs on outer face",
            f"   3mm wide × 10mm protrusion, spaced 100mm vertically",
            f"   Extrude outward from outer surface (Join)",
        ]
    step_n = 7 if shell_num == 2 else 9
    steps += [
        "",
        f"{step_n}. Verify dimensions",
        f"   Outer: {plan_w:.0f} x {plan_d:.0f} x {ext_h:.0f}mm",
        f"   Wall thickness: {wall_thick:.0f}mm",
        f"   Shell base at Z = {z_offset:.0f}mm",
    ]

    for i, step in enumerate(steps):
        sy_pos = 130 + i * 22
        is_bold = step and step[0].isdigit()
        svg += svg_text(step_x, sy_pos, step, size=11,
                        fill="#333" if step else "#999", bold=is_bold)

    # Material badge
    svg += svg_rect(580, 695, 490, 30, fill=color, stroke=color_dark, sw=1, rx=4)
    svg += svg_text(825, 715, f"Material: {material}  |  Wall: {wall_thick:.0f}mm",
                    size=12, fill="white", anchor="middle", bold=True)

    svg += svg_footer()
    write_svg(os.path.join(out_dir, filename), svg)


# ---------------------------------------------------------------------------
# 5. CAP EXTRUSION
# ---------------------------------------------------------------------------

def gen_cap(out_dir):
    W, H = 1100, 1000
    svg = svg_header(W, H)

    svg += svg_text(20, 30, "CAP RIM — EXTRUSION GUIDE (Rev 3.2, Flush)",
                    size=18, fill="#333", bold=True)
    svg += svg_text(20, 50,
                    f"Flush with S1: {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f}mm  |  "
                    f"Thickness: {CAP_THICK:.0f}mm  |  "
                    f"Foam teeth: {FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm",
                    size=12, fill="#555")

    # --- Plan view of cap (outer rect with inner cutout) ---
    svg += svg_text(20, 90, "PLAN VIEW (cap rim —outer with inner cutout)",
                    size=13, fill="#333", bold=True)

    plan_scale = min(400 / CAP_OUTER_W, 250 / CAP_OUTER_D)
    plan_cx = 280
    plan_cy = 240

    # Outer rectangle
    co_w = CAP_OUTER_W * plan_scale
    co_d = CAP_OUTER_D * plan_scale
    co_x = plan_cx - co_w / 2
    co_y = plan_cy - co_d / 2
    svg += svg_rect(co_x, co_y, co_w, co_d,
                    fill=CAP_BG, stroke=CAP_CLR, sw=2.5, rx=3)

    # Inner cutout rectangle
    ci_w = OUTER_W * plan_scale
    ci_d = OUTER_D * plan_scale
    ci_x = plan_cx - ci_w / 2
    ci_y = plan_cy - ci_d / 2
    svg += svg_rect(ci_x, ci_y, ci_w, ci_d,
                    fill="white", stroke=CAP_CLR_DARK, sw=2, rx=2)

    # Gasket groove tracks (two dashed rectangles between outer and inner)
    og_inset = WALL + CAP_GASKET_MARGIN + CAP_GASKET_W / 2
    ig_inset = WALL + FOAM - CAP_GASKET_MARGIN - CAP_GASKET_W / 2
    for inset_mm, label in [(og_inset, "OUTER GASKET"), (ig_inset, "INNER GASKET")]:
        gw = (CAP_OUTER_W - 2 * inset_mm) * plan_scale
        gd = (CAP_OUTER_D - 2 * inset_mm) * plan_scale
        gx = plan_cx - gw / 2
        gy = plan_cy - gd / 2
        svg += (f'  <rect x="{gx:.1f}" y="{gy:.1f}" width="{gw:.1f}" '
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
                bx = plan_cx + bx_mm * plan_scale
                by = plan_cy + by_mm * plan_scale
                svg += (f'  <circle cx="{bx:.1f}" cy="{by:.1f}" r="{bolt_r_px:.1f}" '
                        f'fill="none" stroke="#495057" stroke-width="1.2"/>\n')
        else:
            half_d = CAP_OUTER_D / 2 - bolt_inset
            n_bolts = max(2, int(half_d * 2 / CAP_BOLT_SPACING) + 1)
            for i in range(n_bolts):
                by_mm = -half_d + i * (half_d * 2 / max(1, n_bolts - 1))
                bx_mm = ((-1 if side == "left" else 1) *
                         (CAP_OUTER_W / 2 - bolt_inset))
                bolt_positions_mm.append((bx_mm, by_mm))
                bx = plan_cx + bx_mm * plan_scale
                by = plan_cy + by_mm * plan_scale
                svg += (f'  <circle cx="{bx:.1f}" cy="{by:.1f}" r="{bolt_r_px:.1f}" '
                        f'fill="none" stroke="#495057" stroke-width="1.2"/>\n')

    # Labels
    svg += svg_text(plan_cx, co_y - 8,
                    f"Outer: {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f}mm",
                    size=10, fill=CAP_CLR_DARK, anchor="middle", bold=True)
    svg += svg_text(plan_cx, plan_cy - 8,
                    "Dual gasket grooves (red dashed)", size=8,
                    fill="#e03131", anchor="middle")
    svg += svg_text(plan_cx, plan_cy + 4,
                    f"M4 bolt + {INSERT_OD:.0f}mm insert (circles)", size=8,
                    fill="#495057", anchor="middle")
    svg += svg_text(plan_cx, plan_cy + 16,
                    f"Inner cutout: {OUTER_W:.0f} x {OUTER_D:.0f}mm",
                    size=9, fill="#666", anchor="middle")

    # Foam anchor teeth (small filled rectangles along foam gap centerline)
    # Skip teeth that would conflict with bolt/insert positions
    tooth_inset = WALL + FOAM / 2  # center of foam gap
    tooth_loop_w = CAP_OUTER_W - 2 * tooth_inset
    tooth_loop_d = CAP_OUTER_D - 2 * tooth_inset

    def _tooth_near_bolt(tx_mm, ty_mm, bolts_mm, clearance=15.0):
        for bx, by in bolts_mm:
            if ((tx_mm - bx) ** 2 + (ty_mm - by) ** 2) ** 0.5 < clearance:
                return True
        return False

    # Top/bottom edges
    n_teeth_w = max(2, round(tooth_loop_w / FOAM_TOOTH_SPACING) + 1)
    for i in range(n_teeth_w):
        tx_mm = -tooth_loop_w / 2 + i * tooth_loop_w / max(1, n_teeth_w - 1)
        for sign_y in [-1, 1]:
            ty_mm = sign_y * tooth_loop_d / 2
            if _tooth_near_bolt(tx_mm, ty_mm, bolt_positions_mm):
                continue
            tx_px = plan_cx + tx_mm * plan_scale
            ty_px = plan_cy + ty_mm * plan_scale
            tw_px = FOAM_TOOTH_W * plan_scale
            th_px = FOAM_TOOTH_THICK * plan_scale
            svg += svg_rect(tx_px - tw_px / 2, ty_px - th_px / 2,
                            tw_px, th_px, fill="#c68c00", stroke="#8B6914",
                            sw=0.8, rx=0, opacity=0.7)
    # Left/right edges
    n_teeth_d = max(1, round(tooth_loop_d / FOAM_TOOTH_SPACING) - 1)
    for i in range(n_teeth_d):
        ty_mm = -tooth_loop_d / 2 + (i + 1) * tooth_loop_d / (n_teeth_d + 1)
        for sign_x in [-1, 1]:
            tx_mm = sign_x * tooth_loop_w / 2
            if _tooth_near_bolt(tx_mm, ty_mm, bolt_positions_mm):
                continue
            tx_px = plan_cx + tx_mm * plan_scale
            ty_px = plan_cy + ty_mm * plan_scale
            tw_px = FOAM_TOOTH_THICK * plan_scale
            th_px = FOAM_TOOTH_W * plan_scale
            svg += svg_rect(tx_px - tw_px / 2, ty_px - th_px / 2,
                            tw_px, th_px, fill="#c68c00", stroke="#8B6914",
                            sw=0.8, rx=0, opacity=0.7)

    # Flush annotation (cap = S1 outer)
    svg += svg_text(plan_cx, plan_cy + 28,
                    "Flush with Shell 1 outer", size=8,
                    fill=CAP_CLR_DARK, anchor="middle")
    svg += svg_text(plan_cx, plan_cy + 40,
                    f"Foam teeth (gold): {FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm "
                    f"every {FOAM_TOOTH_SPACING:.0f}mm",
                    size=7, fill="#8B6914", anchor="middle")

    # Outer dims
    svg += svg_dim_h(co_x, co_x + co_w, co_y - 30, color="#555",
                     label=f"{CAP_OUTER_W:.0f}mm")
    svg += svg_dim_v(co_x - 25, co_y, co_y + co_d, color="#555",
                     label=f"{CAP_OUTER_D:.0f}mm", offset=-60)

    # --- Profile cross-section ---
    svg += svg_text(20, 410, "PROFILE CROSS-SECTION", size=13,
                    fill="#333", bold=True)

    # Draw a simple cross-section of the cap rim
    prof_scale = min(300 / CAP_OUTER_W, 100 / CAP_THICK)
    prof_cx = 280
    prof_base_y = 550

    pp_w = CAP_OUTER_W * prof_scale
    pp_h = CAP_THICK * prof_scale
    pp_x = prof_cx - pp_w / 2
    pp_y = prof_base_y - pp_h

    # Outer profile
    svg += svg_rect(pp_x, pp_y, pp_w, pp_h,
                    fill=CAP_BG, stroke=CAP_CLR, sw=2.5, rx=1)

    # Inner cutout in profile (the pocket for the shell top)
    ci_prof_w = OUTER_W * prof_scale
    ci_prof_x = prof_cx - ci_prof_w / 2
    svg += svg_rect(ci_prof_x, pp_y, ci_prof_w, pp_h,
                    fill="white", stroke=CAP_CLR_DARK, sw=1.5, rx=1)

    # Thickness dimension
    svg += svg_dim_v(pp_x + pp_w + 15, pp_y, prof_base_y, color="#555",
                     label=f"{CAP_THICK:.0f}mm", offset=8)

    # Width dimension
    svg += svg_dim_h(pp_x, pp_x + pp_w, prof_base_y + 20, color="#555",
                     label=f"{CAP_OUTER_W:.0f}mm")

    # Foam teeth on profile (hanging down from cap underside)
    # Position at foam gap center: WALL + FOAM/2 from each edge
    tooth_inset_px = (WALL + FOAM / 2) * prof_scale
    tooth_w_px = max(3, FOAM_TOOTH_THICK * prof_scale)
    tooth_h_px = max(8, FOAM_TOOTH_D * prof_scale * 2)  # exaggerated for visibility
    for side in [1, -1]:
        tx = prof_cx + side * (CAP_OUTER_W / 2 - WALL - FOAM / 2) * prof_scale
        svg += svg_rect(tx - tooth_w_px / 2, prof_base_y,
                        tooth_w_px, tooth_h_px,
                        fill="#c68c00", stroke="#8B6914", sw=1, rx=0)
    # Label
    tx_right = prof_cx + (CAP_OUTER_W / 2 - WALL - FOAM / 2) * prof_scale
    svg += svg_text(tx_right + tooth_w_px / 2 + 5, prof_base_y + tooth_h_px / 2 + 3,
                    f"Foam teeth ({FOAM_TOOTH_D:.0f}mm)", size=8, fill="#8B6914")

    # Extrusion arrow
    arr_x = pp_x + pp_w + 60
    svg += svg_arrow_up(arr_x, prof_base_y, pp_y - 15, color=CAP_CLR, sw=2, head=10)
    svg += svg_text(arr_x + 12, (pp_y + prof_base_y) / 2 + 4,
                    f"{CAP_THICK:.0f}mm", size=11, fill=CAP_CLR_DARK, bold=True)

    # =================================================================
    # BOLT + INSERT POCKET DETAIL DIAGRAM
    # Zoomed cross-section of a single bolt hole showing how the
    # heat-set insert works: bolt enters from top, threads into brass
    # insert pressed into counterbore pocket from cap underside.
    # =================================================================
    svg += svg_text(20, 590, "BOLT + INSERT POCKET DETAIL (not to scale)", size=13,
                    fill="#333", bold=True)
    svg += svg_text(20, 607,
                    "Cross-section through a single M4 bolt hole in the cap rim",
                    size=10, fill="#666")

    # Detail drawing area
    det_cx = 200      # center of detail
    det_top = 640     # top of cap in detail (SVG y, where bolt head sits)
    det_h = 130       # cap thickness in pixels
    det_bot = det_top + det_h  # cap underside
    det_w = 280       # total width of detail block

    # Cap body
    svg += svg_rect(det_cx - det_w / 2, det_top, det_w, det_h,
                    fill=CAP_BG, stroke=CAP_CLR, sw=2, rx=0)
    svg += svg_text(det_cx - det_w / 2 + 6, det_top + 14,
                    "CAP BODY (ASA)", size=9, fill=CAP_CLR_DARK, bold=True)

    # --- Gasket groove (left of bolt) ---
    gg_w_px = 30    # groove width in pixels
    gg_d_px = 35    # groove depth in pixels
    gg_cx = det_cx - 70
    svg += svg_rect(gg_cx - gg_w_px / 2, det_top, gg_w_px, gg_d_px,
                    fill="white", stroke="#e03131", sw=1.5, rx=0)
    # Gasket cord (circle inside groove)
    cord_r = gg_w_px / 2 - 3
    svg += svg_circle(gg_cx, det_top + gg_d_px - cord_r - 2, cord_r,
                      fill="#ffcccc", stroke="#e03131", sw=1)
    svg += svg_text(gg_cx, det_top - 6,
                    f"Gasket groove", size=8, fill="#e03131", anchor="middle")
    svg += svg_text(gg_cx, det_top + gg_d_px + 12,
                    f"{CAP_GASKET_W:.0f}W x {CAP_GASKET_D:.1f}D mm",
                    size=7, fill="#e03131", anchor="middle")

    # --- M4 bolt through-hole ---
    bolt_w_px = 28   # bore width in pixels
    bolt_cx = det_cx + 10
    svg += svg_rect(bolt_cx - bolt_w_px / 2, det_top, bolt_w_px, det_h,
                    fill="#e8e8e8", stroke="#495057", sw=1.5, rx=0)
    # Centerline (dashed)
    svg += svg_line(bolt_cx, det_top - 30, bolt_cx, det_bot + 80,
                    stroke="#495057", sw=0.8, dash="4,3")

    # Bolt shaft (narrower line through the hole)
    shaft_w = 14
    svg += svg_rect(bolt_cx - shaft_w / 2, det_top - 15, shaft_w, det_h + 15 + 30,
                    fill="#a0a0a0", stroke="#495057", sw=1, rx=0)

    # Bolt head (on top, wider)
    head_w = 50
    head_h = 22
    svg += svg_rect(bolt_cx - head_w / 2, det_top - 15 - head_h, head_w, head_h,
                    fill="#6c757d", stroke="#333", sw=1.5, rx=2)
    svg += svg_text(bolt_cx, det_top - 15 - head_h / 2 + 4,
                    "M4 BOLT HEAD", size=8, fill="white",
                    anchor="middle", bold=True)

    # --- Insert pocket (counterbore from underside) ---
    ins_w_px = 48   # insert OD in pixels
    ins_d_px = 60   # insert depth in pixels
    pocket_top_y = det_bot - ins_d_px

    # Pocket cavity
    svg += svg_rect(bolt_cx - ins_w_px / 2, pocket_top_y, ins_w_px, ins_d_px,
                    fill="#fff3e0", stroke="#d9480f", sw=2, rx=0)

    # Brass insert body (hatched)
    ins_body_margin = 2
    for hy in range(int(pocket_top_y) + 4, int(det_bot) - 2, 5):
        # Left ring
        svg += svg_line(bolt_cx - ins_w_px / 2 + ins_body_margin, hy,
                        bolt_cx - bolt_w_px / 2 - 1, hy,
                        stroke="#c68c00", sw=1.5)
        # Right ring
        svg += svg_line(bolt_cx + bolt_w_px / 2 + 1, hy,
                        bolt_cx + ins_w_px / 2 - ins_body_margin, hy,
                        stroke="#c68c00", sw=1.5)

    # Insert label
    svg += svg_text(bolt_cx, det_bot - ins_d_px / 2 + 4,
                    "BRASS", size=7, fill="#8B6914", anchor="middle", bold=True)

    # Thread indication (small zigzag lines inside insert bore)
    for ty in range(int(pocket_top_y) + 8, int(det_bot) - 4, 8):
        svg += svg_line(bolt_cx - bolt_w_px / 2, ty,
                        bolt_cx - bolt_w_px / 2 + 4, ty + 3,
                        stroke="#8B6914", sw=0.8)
        svg += svg_line(bolt_cx + bolt_w_px / 2, ty,
                        bolt_cx + bolt_w_px / 2 - 4, ty + 3,
                        stroke="#8B6914", sw=0.8)

    # --- Dimension annotations ---
    # Cap thickness (right side)
    dim_r = det_cx + det_w / 2 + 15
    svg += svg_dim_v(dim_r, det_top, det_bot, color="#555",
                     label=f"{CAP_THICK:.0f}mm cap", offset=8)

    # Insert pocket depth (left side)
    dim_l = det_cx - det_w / 2 - 15
    svg += svg_line(dim_l - 5, pocket_top_y, dim_l + 5, pocket_top_y,
                    stroke="#d9480f", sw=1)
    svg += svg_line(dim_l - 5, det_bot, dim_l + 5, det_bot,
                    stroke="#d9480f", sw=1)
    svg += svg_line(dim_l, pocket_top_y, dim_l, det_bot,
                    stroke="#d9480f", sw=1)
    svg += svg_text(dim_l - 3, (pocket_top_y + det_bot) / 2 + 4,
                    f"{INSERT_DEPTH:.0f}mm", size=9, fill="#d9480f",
                    anchor="end", bold=True)

    # Bore diameter label
    svg += svg_text(bolt_cx + bolt_w_px / 2 + 30, det_top + det_h / 2 - 15,
                    f"M4 thru-hole ({M4_HOLE:.1f}mm)", size=9, fill="#495057")
    svg += svg_line(bolt_cx + bolt_w_px / 2 + 2, det_top + det_h / 2 - 10,
                    bolt_cx + bolt_w_px / 2 + 28, det_top + det_h / 2 - 18,
                    stroke="#495057", sw=0.8)

    # Insert OD label
    svg += svg_text(bolt_cx + ins_w_px / 2 + 30, det_bot - ins_d_px / 2,
                    f"Insert pocket ({INSERT_OD:.0f}mm OD)", size=9,
                    fill="#d9480f")
    svg += svg_line(bolt_cx + ins_w_px / 2 + 2, det_bot - ins_d_px / 2 - 5,
                    bolt_cx + ins_w_px / 2 + 28, det_bot - ins_d_px / 2 - 5,
                    stroke="#d9480f", sw=0.8)

    # =================================================================
    # FOAM ANCHOR TOOTH DETAIL (right of bolt detail)
    # Cross-section showing a tooth hanging into the foam gap
    # =================================================================
    ft_cx = 470       # center X of foam tooth detail
    ft_top = det_top  # align with bolt detail
    ft_h = det_h      # same cap thickness representation
    ft_bot = ft_top + ft_h
    ft_w = 200

    svg += svg_text(ft_cx, ft_top - 30, "FOAM ANCHOR TOOTH DETAIL",
                    size=11, fill="#8B6914", anchor="middle", bold=True)
    svg += svg_text(ft_cx, ft_top - 16, "(cross-section, not to scale)",
                    size=8, fill="#666", anchor="middle")

    # Cap body slice
    svg += svg_rect(ft_cx - ft_w / 2, ft_top, ft_w, ft_h,
                    fill=CAP_BG, stroke=CAP_CLR, sw=2, rx=0)
    svg += svg_text(ft_cx - ft_w / 2 + 6, ft_top + 14,
                    "CAP FLANGE", size=8, fill=CAP_CLR_DARK, bold=True)

    # Tooth hanging down from cap underside
    tooth_px_w = 40   # tooth width (along perimeter) in pixels
    tooth_px_h = 70   # tooth depth (protrusion) in pixels
    tooth_px_thick = 90  # tooth thickness (radial) in pixels

    svg += svg_rect(ft_cx - tooth_px_thick / 2, ft_bot,
                    tooth_px_thick, tooth_px_h,
                    fill="#fff3e0", stroke="#8B6914", sw=2, rx=0)

    # Hatching inside tooth
    for hy in range(int(ft_bot) + 5, int(ft_bot + tooth_px_h) - 3, 6):
        svg += svg_line(ft_cx - tooth_px_thick / 2 + 3, hy,
                        ft_cx + tooth_px_thick / 2 - 3, hy,
                        stroke="#c68c00", sw=1)

    svg += svg_text(ft_cx, ft_bot + tooth_px_h / 2 + 4,
                    "TOOTH", size=9, fill="#8B6914",
                    anchor="middle", bold=True)

    # Shell walls on either side (S1 inner left, S2 outer right)
    wall_w = 20
    wall_h = ft_h + tooth_px_h + 20
    # S1 inner wall (left)
    svg += svg_rect(ft_cx - tooth_px_thick / 2 - 8 - wall_w,
                    ft_top - 10, wall_w, wall_h,
                    fill=SHELL1_BG, stroke=SHELL1_CLR, sw=1.5, rx=0)
    svg += svg_text(ft_cx - tooth_px_thick / 2 - 8 - wall_w / 2,
                    ft_top + wall_h - 15,
                    "S1", size=7, fill=SHELL1_CLR_DARK, anchor="middle")

    # S2 outer wall (right)
    svg += svg_rect(ft_cx + tooth_px_thick / 2 + 8,
                    ft_top - 10, wall_w, wall_h,
                    fill=SHELL2_BG, stroke=SHELL2_CLR, sw=1.5, rx=0)
    svg += svg_text(ft_cx + tooth_px_thick / 2 + 8 + wall_w / 2,
                    ft_top + wall_h - 15,
                    "S2", size=7, fill=SHELL2_CLR_DARK, anchor="middle")

    # Foam fill around tooth (dotted fill suggestion)
    foam_left = ft_cx - tooth_px_thick / 2 - 8
    foam_right = ft_cx + tooth_px_thick / 2 + 8
    svg += svg_rect(foam_left, ft_bot + tooth_px_h,
                    foam_right - foam_left, 20,
                    fill=FOAM_BG, stroke=FOAM_CLR, sw=1, rx=0, opacity=0.6)
    svg += svg_text(ft_cx, ft_bot + tooth_px_h + 14,
                    "FOAM (cured)", size=7, fill=FOAM_CLR_DARK, anchor="middle")

    # Dimension: tooth depth
    td_x = ft_cx + tooth_px_thick / 2 + 40
    svg += svg_line(td_x - 3, ft_bot, td_x + 3, ft_bot,
                    stroke="#8B6914", sw=1)
    svg += svg_line(td_x - 3, ft_bot + tooth_px_h, td_x + 3, ft_bot + tooth_px_h,
                    stroke="#8B6914", sw=1)
    svg += svg_line(td_x, ft_bot, td_x, ft_bot + tooth_px_h,
                    stroke="#8B6914", sw=1)
    svg += svg_text(td_x + 5, ft_bot + tooth_px_h / 2 + 4,
                    f"{FOAM_TOOTH_D:.0f}mm", size=9, fill="#8B6914", bold=True)

    # Dimension: tooth thickness (radial)
    svg += svg_dim_h(ft_cx - tooth_px_thick / 2, ft_cx + tooth_px_thick / 2,
                     ft_bot + tooth_px_h + 30, color="#8B6914",
                     label=f"{FOAM_TOOTH_THICK:.0f}mm (fills gap)")

    # Clearance arrows
    svg += svg_text(ft_cx - tooth_px_thick / 2 - 4,
                    ft_bot + tooth_px_h / 2 + 4,
                    "2mm", size=7, fill="#999", anchor="end")
    svg += svg_text(ft_cx + tooth_px_thick / 2 + 4,
                    ft_bot + tooth_px_h / 2 + 4,
                    "2mm", size=7, fill="#999")

    # --- How-it-works callout box ---
    hw_x = 20
    hw_y = max(det_bot, ft_bot + tooth_px_h + 50) + 10
    svg += svg_rect(hw_x, hw_y, 540, 115, fill="#f8f9fa", stroke="#dee2e6",
                    sw=1, rx=4)
    svg += svg_text(hw_x + 10, hw_y + 16,
                    "HOW IT WORKS:", size=10, fill="#333", bold=True)
    svg += svg_text(hw_x + 10, hw_y + 32,
                    f"1. Drill {M4_HOLE:.1f}mm through-holes + counterbore "
                    f"{INSERT_OD:.0f}x{INSERT_DEPTH:.0f}mm insert pockets "
                    f"(see bolt detail left)",
                    size=9, fill="#555")
    svg += svg_text(hw_x + 10, hw_y + 46,
                    "2. Press M4 brass heat-set inserts with soldering iron at 220-240C",
                    size=9, fill="#555")
    svg += svg_text(hw_x + 10, hw_y + 60,
                    f"3. Foam teeth ({FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm) "
                    f"are printed as part of the cap — no assembly needed",
                    size=9, fill="#555")
    svg += svg_text(hw_x + 10, hw_y + 74,
                    "4. Place cap on shells while PU foam is still wet — teeth embed in foam",
                    size=9, fill="#555")
    svg += svg_text(hw_x + 10, hw_y + 88,
                    "5. Foam cures around teeth: permanent alignment + mechanical interlock + seal",
                    size=9, fill="#555")
    svg += svg_text(hw_x + 10, hw_y + 102,
                    "6. M4 bolts through cap + lid compress gaskets for weather seal",
                    size=9, fill="#555")

    # --- Workflow ---
    step_x = 600
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
        "   From cap underside — press M4 brass heat-set inserts",
        "",
        f"6. Add foam anchor teeth on flange underside",
        f"   {FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm, "
        f"every {FOAM_TOOTH_SPACING:.0f}mm",
        "   Fill foam gap for alignment + cure into foam",
        "",
        "7. May split into panels for print bed if needed",
    ]

    box_h = 130 + len(steps) * 19 + 10
    svg += svg_rect(580, 75, 490, box_h, fill=CAP_BG, stroke=CAP_CLR, sw=1.5, rx=6)
    svg += svg_text(step_x, 100, "FUSION 360 WORKFLOW", size=14,
                    fill=CAP_CLR_DARK, bold=True)

    for i, step in enumerate(steps):
        sy_pos = 125 + i * 19
        is_bold = step and step[0].isdigit()
        svg += svg_text(step_x, sy_pos, step, size=10,
                        fill="#333" if step else "#999", bold=is_bold)

    # Material badge
    badge_y = 75 + box_h + 10
    svg += svg_rect(580, badge_y, 490, 30, fill=CAP_CLR, stroke=CAP_CLR_DARK,
                    sw=1, rx=4)
    svg += svg_text(825, badge_y + 20,
                    f"Material: ASA/PETG  |  Thickness: {CAP_THICK:.0f}mm  |  "
                    f"M4 brass inserts",
                    size=12, fill="white", anchor="middle", bold=True)

    svg += svg_footer()
    write_svg(os.path.join(out_dir, "cap_extrusion.svg"), svg)


# ---------------------------------------------------------------------------
# LID EXTRUSION GUIDE
# ---------------------------------------------------------------------------

def gen_lid(out_dir):
    W, H = 1100, 750
    svg = svg_header(W, H)

    svg += svg_text(20, 30, "LID — EXTRUSION GUIDE (Rev 3.2)",
                    size=18, fill="#333", bold=True)
    svg += svg_text(20, 50,
                    f"Outer: {LID_W:.0f} x {LID_D:.0f}mm  |  "
                    f"Body: {LID_THICK:.0f}mm (20% infill = insulation)  |  "
                    f"Skirt: {LID_SKIRT:.0f}mm  |  "
                    f"Overhang: {LID_OVERHANG:.0f}mm",
                    size=12, fill="#555")

    # --- Plan view of lid ---
    svg += svg_text(20, 90, "PLAN VIEW (lid outline, bolt holes, cap rim reference)",
                    size=13, fill="#333", bold=True)

    plan_scale = min(400 / LID_W, 250 / LID_D)
    plan_cx = 280
    plan_cy = 240

    # Lid outline
    lid_pw = LID_W * plan_scale
    lid_pd = LID_D * plan_scale
    lid_px = plan_cx - lid_pw / 2
    lid_py = plan_cy - lid_pd / 2
    svg += svg_rect(lid_px, lid_py, lid_pw, lid_pd,
                    fill=LID_BG, stroke=LID_CLR, sw=2.5, rx=3)

    # Cap rim outline (reference)
    cap_pw = CAP_OUTER_W * plan_scale
    cap_pd = CAP_OUTER_D * plan_scale
    cap_px = plan_cx - cap_pw / 2
    cap_py = plan_cy - cap_pd / 2
    svg += svg_rect(cap_px, cap_py, cap_pw, cap_pd,
                    fill="none", stroke=CAP_CLR, sw=1.5, rx=2)

    # Shell 1 outline (reference)
    s1_pw = OUTER_W * plan_scale
    s1_pd = OUTER_D * plan_scale
    s1_px = plan_cx - s1_pw / 2
    s1_py = plan_cy - s1_pd / 2
    svg += svg_rect(s1_px, s1_py, s1_pw, s1_pd,
                    fill="none", stroke=SHELL1_CLR, sw=1, rx=2)

    # Labels
    svg += svg_text(plan_cx, lid_py - 8,
                    f"Lid: {LID_W:.0f} x {LID_D:.0f}mm",
                    size=10, fill=LID_CLR_DARK, anchor="middle", bold=True)
    svg += svg_text(plan_cx, plan_cy + 4,
                    f"Cap rim: {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f}mm",
                    size=9, fill=CAP_CLR_DARK, anchor="middle")

    # Overhang dimension
    svg += svg_dim_h(lid_px, cap_px, lid_py + lid_pd + 20, color=LID_CLR_DARK,
                     label=f"Overhang {LID_OVERHANG:.0f}mm")

    # Outer dims
    svg += svg_dim_h(lid_px, lid_px + lid_pw, lid_py - 30, color="#555",
                     label=f"{LID_W:.0f}mm")
    svg += svg_dim_v(lid_px - 25, lid_py, lid_py + lid_pd, color="#555",
                     label=f"{LID_D:.0f}mm", offset=-60)

    # --- Profile cross-section ---
    svg += svg_text(20, 410, "PROFILE CROSS-SECTION (lid body + skirt + drip edge)",
                    size=13, fill="#333", bold=True)

    prof_scale = min(300 / LID_W, 80 / (LID_THICK + LID_SKIRT))
    prof_cx = 280
    prof_base_y = 590

    # Lid body
    body_w = LID_W * prof_scale
    body_h = LID_THICK * prof_scale
    body_x = prof_cx - body_w / 2
    body_y = prof_base_y - (LID_THICK + LID_SKIRT) * prof_scale
    svg += svg_rect(body_x, body_y, body_w, body_h,
                    fill=LID_BG, stroke=LID_CLR, sw=2.5, rx=1)

    # Skirt (left and right)
    skirt_h = LID_SKIRT * prof_scale
    skirt_w = 8 * prof_scale  # approximate skirt wall width
    svg += svg_rect(body_x, body_y + body_h, skirt_w, skirt_h,
                    fill=LID_BG, stroke=LID_CLR, sw=2)
    svg += svg_rect(body_x + body_w - skirt_w, body_y + body_h, skirt_w, skirt_h,
                    fill=LID_BG, stroke=LID_CLR, sw=2)

    # Cap rim reference position
    cap_prof_w = CAP_OUTER_W * prof_scale
    cap_prof_x = prof_cx - cap_prof_w / 2
    cap_prof_y = body_y + body_h
    cap_prof_h = CAP_THICK * prof_scale
    svg += svg_rect(cap_prof_x, cap_prof_y, cap_prof_w, cap_prof_h,
                    fill="none", stroke=CAP_CLR, sw=1.5, rx=1)
    svg += svg_text(prof_cx, cap_prof_y + cap_prof_h + 12,
                    "Cap rim (below lid)", size=9, fill=CAP_CLR_DARK, anchor="middle")

    # Total height dimension
    total_h = (LID_THICK + LID_SKIRT) * prof_scale
    svg += svg_dim_v(body_x + body_w + 15, body_y, body_y + body_h + skirt_h,
                     color="#555", label=f"{LID_THICK + LID_SKIRT:.0f}mm total", offset=8)

    # Body thickness
    svg += svg_dim_v(body_x - 25, body_y, body_y + body_h,
                     color=LID_CLR_DARK, label=f"Body {LID_THICK:.0f}mm", offset=-50)

    # Skirt dimension
    svg += svg_dim_v(body_x - 25, body_y + body_h, body_y + body_h + skirt_h,
                     color=LID_CLR_DARK, label=f"Skirt {LID_SKIRT:.0f}mm", offset=-50)

    # Width dimension
    svg += svg_dim_h(body_x, body_x + body_w, prof_base_y + 20, color="#555",
                     label=f"{LID_W:.0f}mm")

    # --- Workflow ---
    step_x = 600
    svg += svg_rect(580, 75, 490, 640, fill=LID_BG, stroke=LID_CLR, sw=1.5, rx=6)
    svg += svg_text(step_x, 100, "FUSION 360 WORKFLOW", size=14,
                    fill=LID_CLR_DARK, bold=True)

    steps = [
        "1. Import DXF profiles",
        "   File > Insert > Insert DXF",
        "   Select 9_lid_top_view.dxf (plan outline + bolts)",
        "   Select 8_cap_profile.dxf (lid cross-section)",
        "",
        f"2. Extrude the lid body",
        f"   Select the lid outline rectangle",
        f"   Extrude > Distance = {LID_THICK:.0f}mm (upward)",
        "",
        f"3. Extrude the rain skirt",
        f"   Select the skirt border region (perimeter ring)",
        f"   Extrude > Distance = {LID_SKIRT:.0f}mm (downward from body)",
        "",
        "4. Cut the drip edge groove",
        "   Sketch groove profile on skirt underside",
        "   3mm inset, 3mm deep, 2mm wide channel",
        "   Extrude > Cut around skirt perimeter",
        "",
        "5. Cut bolt through-holes (M4)",
        "   Use bolt pattern from 9_lid_top_view.dxf",
        "   Extrude > Cut > All (through lid body + skirt)",
        f"   Bolts thread into {INSERT_OD:.0f}mm brass heat-set inserts in cap",
        "",
        "6. Add 3mm chamfer on top edges",
        "   Modify > Chamfer on all top perimeter edges",
        "",
        f"7. Verify dimensions",
        f"   Outer: {LID_W:.0f} x {LID_D:.0f}mm",
        f"   Body: {LID_THICK:.0f}mm thick",
        f"   Skirt: {LID_SKIRT:.0f}mm drop",
        f"   Overhang: {LID_OVERHANG:.0f}mm past cap rim",
        "",
        "8. Print settings",
        "   Material: ASA (UV-stable)",
        "   Infill: 20% (trapped air = insulation)",
        "   No foam behind lid — infill IS the insulation",
    ]

    for i, step in enumerate(steps):
        sy_pos = 130 + i * 19
        is_bold = step and step[0].isdigit()
        svg += svg_text(step_x, sy_pos, step, size=10,
                        fill="#333" if step else "#999", bold=is_bold)

    # Material badge
    svg += svg_rect(580, 725, 490, 30, fill=LID_CLR, stroke=LID_CLR_DARK,
                    sw=1, rx=4)
    svg += svg_text(825, 745,
                    f"Material: ASA  |  Body: {LID_THICK:.0f}mm  |  "
                    f"Skirt: {LID_SKIRT:.0f}mm  |  20% infill",
                    size=12, fill="white", anchor="middle", bold=True)

    svg += svg_footer()
    write_svg(os.path.join(out_dir, "lid_extrusion.svg"), svg)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(script_dir, "guides")
    os.makedirs(out_dir, exist_ok=True)

    print("Generating extrusion guide SVGs for Main Unit (Rev 3.2)...")
    print(f"  Output directory: {out_dir}")
    print()

    # 1. Overview
    gen_overview(out_dir)

    # Conduit positions on rear face (top edge of plan view)
    # (x_frac, y_frac, dia_mm, label) — y_frac ~0.0 = rear/top edge
    rear_conduits = [
        (0.15, 0.06, 16, "SAT1"),
        (0.25, 0.06, 16, "SAT2"),
        (0.35, 0.06, 16, "SAT3"),
        (0.45, 0.06, 16, "SAT4"),
        (0.55, 0.06, 14, "MC4-1"),
        (0.63, 0.06, 14, "MC4-2"),
        (0.71, 0.06, 14, "MC4-3"),
        (0.79, 0.06, 14, "MC4-4"),
        (0.55, 0.18, 10, "P1"),
        (0.63, 0.18, 10, "P2"),
        (0.71, 0.18, 10, "P3"),
        (0.85, 0.12, 8, "PROBE"),
    ]

    # 2. Shell 1 (ASA outer)
    gen_shell_card(
        out_dir, "shell1_extrusion.svg",
        shell_num=1, material="ASA",
        color=SHELL1_CLR, color_dark=SHELL1_CLR_DARK, bg_color=SHELL1_BG,
        plan_w=OUTER_W, plan_d=OUTER_D, ext_h=OUTER_H,
        z_offset=S1_Z, wall_thick=WALL,
        dxf_file="1_top_view.dxf",
        shell_cmd_note=f"Shell command: {WALL:.0f}mm wall",
        conduits=rear_conduits,
    )

    # 3. Shell 2 (PETG structural)
    gen_shell_card(
        out_dir, "shell2_extrusion.svg",
        shell_num=2, material="PETG",
        color=SHELL2_CLR, color_dark=SHELL2_CLR_DARK, bg_color=SHELL2_BG,
        plan_w=MID_W, plan_d=MID_D, ext_h=MID_H,
        z_offset=S2_Z, wall_thick=WALL_S2,
        dxf_file="1_top_view.dxf (mid shell profile)",
        shell_cmd_note=f"Shell command: {WALL_S2:.0f}mm wall",
        conduits=rear_conduits,
    )

    # 4. Cap
    gen_cap(out_dir)

    # 5. Lid
    gen_lid(out_dir)

    print()
    print("Done. Generated 5 extrusion guide SVGs.")


if __name__ == "__main__":
    main()
