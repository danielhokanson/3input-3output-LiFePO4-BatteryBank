#!/usr/bin/env python3
"""
Dimensional Analysis — Main Unit & Satellite Unit (Rev 3.2)

Computes all derived dimensions from parametric values, checks component fit
against enclosure boundaries, and generates detailed SVG top-view visualizations
showing components inside open containers.

Usage:
    python cad/dimensional_analysis.py

Output:
    cad/main_unit_top_view.svg
    cad/satellite_unit_top_view.svg
    (text report to stdout)
"""

import os
import math

# ============================================================================
# COMPONENT DIMENSIONS (all in mm)
# ============================================================================

# --- Narada 105Ah LiFePO4 Cell (MEASURED) ---
CELL_L = 129.0    # length (long axis of footprint)
CELL_W = 36.0     # width (short axis / thickness)
CELL_H = 256.0    # height (body, standing upright)
TERMINAL_H = 4.0  # terminal protrusion above body

# --- EPever Tracer 2210AN MPPT Controller ---
# Datasheet: ~188 × 96 × 52mm; code uses slightly smaller values
EPEVER_W = 186.0   # front face width
EPEVER_H = 76.0    # front face height (vertical dimension when standing)
EPEVER_D = 47.0    # depth (front-to-back)
# Top-view footprint when mounted vertically (face forward): W × D = 186 × 47

# --- 4S 100A Smart BMS ---
BMS_W = 175.0     # width
BMS_H = 80.0      # height
BMS_D = 25.0      # depth (thickness)
# Top-view footprint when mounted on edge: W × D = 175 × 25

# --- LEM HASS 200-S Current Sensor ---
LEM_W = 44.0      # width
LEM_D = 32.0      # depth
LEM_H = 31.0      # height

# --- Distribution Bus Bar ---
BUS_W = 30.0      # width
BUS_D = 200.0     # length (runs vertically)

# --- Fuse Block (3-way blade) ---
FUSE_W = 80.0     # width
FUSE_D = 40.0     # depth

# --- 80A ANL Main Fuse + Holder ---
ANL_W = 60.0      # width
ANL_D = 30.0      # depth

# --- STC-1000 Thermostat ---
STC_W = 71.0      # front face width
STC_D = 29.0      # depth
STC_H = 34.0      # height
# Top-view footprint: 71 × 29mm (or ~55 × 35 as approximated in CAD)

# --- PTC Heater Element ---
HEATER_W = 50.0   # width
HEATER_D = 15.0   # depth (thin strip)

# --- 80mm Fan ---
FAN_DIAM = 80.0

# --- Compression Plates ---
COMP_PLATE_W = 4.0    # thickness
# Length matches cell height (for front elev) or cell length (for top view)

# --- Narada 50A Busbars ---
BUSBAR_W = 50.0   # approximate busbar span
BUSBAR_D = 10.0   # depth

# ============================================================================
# MAIN UNIT LAYOUT
# ============================================================================

# Battery zone — 4S2P = 8 cells
MAIN_CELLS_S = 4
MAIN_CELLS_P = 2

# Cell stack dimensions
MAIN_STACK_W = MAIN_CELLS_S * CELL_W + (MAIN_CELLS_S - 1) * 2 + 8  # 4×36 + 3×2 + 8 = 158
MAIN_STACK_D = MAIN_CELLS_P * CELL_L + (MAIN_CELLS_P - 1) * 10      # 2×129 + 10 = 268
MAIN_STACK_H = CELL_H + TERMINAL_H + 30.0                             # 256 + 4 + 30 = 290

# Electronics zone (hardcoded in generate_dxf.py)
MAIN_ELEC_W = 320.0
MAIN_ELEC_D = MAIN_STACK_D  # 268

# Spacing
MAIN_ZONE_GAP = 20.0
MAIN_ZONE_MARGIN = 10.0
MAIN_WALL = 5.0
MAIN_WALL_S2 = 5.0
MAIN_FOAM = 30.0

# Inner component space
MAIN_INNER_W = 2 * MAIN_ZONE_MARGIN + MAIN_STACK_W + MAIN_ZONE_GAP + MAIN_ELEC_W
MAIN_INNER_D = max(MAIN_STACK_D, MAIN_ELEC_D) + 2 * MAIN_ZONE_MARGIN

# Shell 2 (PETG structural)
MAIN_S2_W = MAIN_INNER_W + 2 * MAIN_WALL_S2
MAIN_S2_D = MAIN_INNER_D + 2 * MAIN_WALL_S2

# Shell 1 (ASA outer)
MAIN_S1_W = MAIN_S2_W + 2 * (MAIN_FOAM + MAIN_WALL)
MAIN_S1_D = MAIN_S2_D + 2 * (MAIN_FOAM + MAIN_WALL)

# ============================================================================
# SATELLITE UNIT LAYOUT
# ============================================================================

SAT_CELLS_S = 4
SAT_CELLS_P = 1

SAT_STACK_W = SAT_CELLS_S * CELL_W + (SAT_CELLS_S - 1) * 2 + 8  # 158
SAT_STACK_D = CELL_L + 10.0                                        # 139
SAT_STACK_H = CELL_H + TERMINAL_H + 30.0                            # 290

SAT_THERM_W = 70.0
SAT_THERM_D = SAT_STACK_D  # 139

SAT_ZONE_GAP = 15.0
SAT_ZONE_MARGIN = 10.0
SAT_WALL = 5.0
SAT_WALL_S2 = 5.0
SAT_FOAM = 30.0

SAT_INNER_W = 2 * SAT_ZONE_MARGIN + SAT_STACK_W + SAT_ZONE_GAP + SAT_THERM_W
SAT_INNER_D = max(SAT_STACK_D, SAT_THERM_D) + 2 * SAT_ZONE_MARGIN

SAT_S2_W = SAT_INNER_W + 2 * SAT_WALL_S2
SAT_S2_D = SAT_INNER_D + 2 * SAT_WALL_S2

SAT_S1_W = SAT_S2_W + 2 * (SAT_FOAM + SAT_WALL)
SAT_S1_D = SAT_S2_D + 2 * (SAT_FOAM + SAT_WALL)


# ============================================================================
# MAIN UNIT — MPPT LAYOUT CHECK (as coded in generate_dxf.py)
# ============================================================================

def check_main_unit_layout():
    """Check if components actually fit in the allocated zones."""
    issues = []

    # Battery zone check
    # Cells: 4 across (W) × 2 deep (D)
    cells_w_needed = COMP_PLATE_W + 2 + MAIN_CELLS_S * CELL_W + (MAIN_CELLS_S - 1) * 2 + COMP_PLATE_W
    cells_d_needed = MAIN_CELLS_P * CELL_L + (MAIN_CELLS_P - 1) * 10 + 10  # +10 margins
    print(f"  Battery zone — cells need: {cells_w_needed:.0f}W × {cells_d_needed:.0f}D mm")
    print(f"  Battery zone — allocated:  {MAIN_STACK_W:.0f}W × {MAIN_STACK_D:.0f}D mm")
    if cells_w_needed > MAIN_STACK_W:
        issues.append(f"OVERFLOW: Cells need {cells_w_needed:.0f}mm width but battery zone is {MAIN_STACK_W:.0f}mm")
    if cells_d_needed > MAIN_STACK_D:
        issues.append(f"OVERFLOW: Cells need {cells_d_needed:.0f}mm depth but battery zone is {MAIN_STACK_D:.0f}mm")

    # Electronics zone — MPPT 2×2 grid (as coded)
    # Code arranges: 2 columns × 2 rows, each EPEVER_D × EPEVER_W footprint
    mppt_w_coded = 10 + 2 * EPEVER_D + 10  # left margin + 2 cols × 47 + gap = 114
    mppt_d_coded = 10 + 2 * EPEVER_W + 10  # top margin + 2 rows × 186 + gap = 402
    print(f"\n  Electronics zone — allocated: {MAIN_ELEC_W:.0f}W × {MAIN_ELEC_D:.0f}D mm")
    print(f"  MPPT 2×2 grid (as coded) needs: {mppt_w_coded:.0f}W × {mppt_d_coded:.0f}D mm")
    if mppt_d_coded > MAIN_ELEC_D:
        issues.append(
            f"CRITICAL OVERFLOW: MPPT 2×2 grid needs {mppt_d_coded:.0f}mm depth "
            f"but electronics zone is only {MAIN_ELEC_D:.0f}mm — overflow by {mppt_d_coded - MAIN_ELEC_D:.0f}mm!"
        )

    # BMS placement (as coded: right of MPPT columns)
    bms_x_start = 10 + 2 * (EPEVER_D + 10) + 10  # 134mm from elec zone left
    bms_right_edge = bms_x_start + BMS_W  # 134 + 175 = 309
    print(f"  BMS right edge at: {bms_right_edge:.0f}mm from elec zone left (zone width: {MAIN_ELEC_W:.0f}mm)")
    if bms_right_edge > MAIN_ELEC_W:
        issues.append(f"OVERFLOW: BMS extends to {bms_right_edge:.0f}mm but elec zone is {MAIN_ELEC_W:.0f}mm wide")

    # Bus bar (as coded: right of BMS)
    bus_x_start = bms_right_edge + 10  # 319mm
    bus_right_edge = bus_x_start + BUS_W  # 349mm
    print(f"  Bus bar right edge at: {bus_right_edge:.0f}mm from elec zone left")
    if bus_right_edge > MAIN_ELEC_W:
        issues.append(
            f"OVERFLOW: Bus bar extends to {bus_right_edge:.0f}mm "
            f"but elec zone is only {MAIN_ELEC_W:.0f}mm — overflow by {bus_right_edge - MAIN_ELEC_W:.0f}mm!"
        )

    # Inner space vs Shell 2
    print(f"\n  Inner component space: {MAIN_INNER_W:.0f}W × {MAIN_INNER_D:.0f}D mm")
    print(f"  Shell 2 (PETG):        {MAIN_S2_W:.0f}W × {MAIN_S2_D:.0f}D mm")
    print(f"  Shell 1 (ASA):         {MAIN_S1_W:.0f}W × {MAIN_S1_D:.0f}D mm")

    # Utilization
    elec_area = MAIN_ELEC_W * MAIN_ELEC_D
    mppt_area = 4 * EPEVER_D * EPEVER_W
    bms_area = 2 * BMS_W * BMS_D
    bus_area = BUS_W * (MAIN_ELEC_D - 20)
    therm_area = 100 * 110
    total_component_area = mppt_area + bms_area + bus_area + therm_area
    print(f"\n  Electronics zone area: {elec_area:.0f} mm²")
    print(f"  Component footprint total: {total_component_area:.0f} mm² ({100*total_component_area/elec_area:.0f}%)")

    return issues


def check_satellite_layout():
    """Check satellite unit component fit."""
    issues = []

    print(f"  Battery zone — stack: {SAT_STACK_W:.0f}W × {SAT_STACK_D:.0f}D mm")
    print(f"  Thermal zone — allocated: {SAT_THERM_W:.0f}W × {SAT_THERM_D:.0f}D mm")
    print(f"  Fan diameter: {FAN_DIAM:.0f}mm vs thermal zone width: {SAT_THERM_W:.0f}mm")

    if FAN_DIAM > SAT_THERM_W:
        issues.append(
            f"WARNING: Fan diameter ({FAN_DIAM:.0f}mm) exceeds thermal zone width ({SAT_THERM_W:.0f}mm) "
            f"by {FAN_DIAM - SAT_THERM_W:.0f}mm — OK if wall-mounted but verify clearance"
        )

    # STC-1000 in thermal zone
    stc_footprint = f"{STC_W:.0f}×{STC_D:.0f}"
    print(f"  STC-1000 footprint: {stc_footprint}mm (thermal zone: {SAT_THERM_W:.0f}×{SAT_THERM_D:.0f}mm)")
    if STC_W > SAT_THERM_W:
        issues.append(f"WARNING: STC-1000 width ({STC_W:.0f}mm) exceeds thermal zone width ({SAT_THERM_W:.0f}mm)")

    print(f"\n  Inner component space: {SAT_INNER_W:.0f}W × {SAT_INNER_D:.0f}D mm")
    print(f"  Shell 2 (PETG):        {SAT_S2_W:.0f}W × {SAT_S2_D:.0f}D mm")
    print(f"  Shell 1 (ASA):         {SAT_S1_W:.0f}W × {SAT_S1_D:.0f}D mm")

    return issues


# ============================================================================
# SVG GENERATION
# ============================================================================

class SVGBuilder:
    """Simple SVG builder for top-view component layout diagrams."""

    def __init__(self, width, height, title=""):
        self.svg_w = width
        self.svg_h = height
        self.title = title
        self.elements = []
        self.defs = []

    def add_rect(self, x, y, w, h, fill="none", stroke="#333", stroke_width=1,
                 opacity=1.0, rx=0, label="", label_size=10, label_color="#333",
                 stroke_dash="", css_class=""):
        dash_attr = f' stroke-dasharray="{stroke_dash}"' if stroke_dash else ""
        cls_attr = f' class="{css_class}"' if css_class else ""
        self.elements.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}" rx="{rx}"{dash_attr}{cls_attr}/>'
        )
        if label:
            lx = x + w / 2
            ly = y + h / 2 + label_size / 3
            self.elements.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{label_size}" '
                f'fill="{label_color}" text-anchor="middle" '
                f'font-family="monospace">{label}</text>'
            )

    def add_circle(self, cx, cy, r, fill="none", stroke="#333", stroke_width=1,
                   opacity=1.0, label="", label_size=10, label_color="#333"):
        self.elements.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}"/>'
        )
        if label:
            self.elements.append(
                f'<text x="{cx:.1f}" y="{cy + label_size/3:.1f}" font-size="{label_size}" '
                f'fill="{label_color}" text-anchor="middle" '
                f'font-family="monospace">{label}</text>'
            )

    def add_text(self, x, y, text, size=12, color="#333", anchor="start",
                 weight="normal", font="monospace"):
        self.elements.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'font-family="{font}">{text}</text>'
        )

    def add_line(self, x1, y1, x2, y2, stroke="#999", stroke_width=0.5, dash=""):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.elements.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}"{dash_attr}/>'
        )

    def add_dim_line(self, x1, y1, x2, y2, label, offset=15, color="#666"):
        """Add a dimension line with arrows and label."""
        # Main line
        self.add_line(x1, y1, x2, y2, stroke=color, stroke_width=0.7)
        # Tick marks
        if y1 == y2:  # horizontal
            self.add_line(x1, y1 - 3, x1, y1 + 3, stroke=color, stroke_width=0.7)
            self.add_line(x2, y2 - 3, x2, y2 + 3, stroke=color, stroke_width=0.7)
            self.add_text((x1 + x2) / 2, y1 - 5, label, size=8, color=color, anchor="middle")
        else:  # vertical
            self.add_line(x1 - 3, y1, x1 + 3, y1, stroke=color, stroke_width=0.7)
            self.add_line(x2 - 3, y2, x2 + 3, y2, stroke=color, stroke_width=0.7)
            self.add_text(x1 + 8, (y1 + y2) / 2, label, size=8, color=color, anchor="start")

    def render(self):
        defs_str = "\n".join(self.defs)
        elems_str = "\n  ".join(self.elements)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.svg_w}" height="{self.svg_h}" '
            f'viewBox="0 0 {self.svg_w} {self.svg_h}">\n'
            f'<defs>\n{defs_str}\n</defs>\n'
            f'<rect width="100%" height="100%" fill="#1a1a2e"/>\n'
            f'  {elems_str}\n'
            f'</svg>'
        )


# ============================================================================
# MAIN UNIT TOP VIEW
# ============================================================================

def generate_main_unit_svg():
    """Generate detailed top-view SVG of main unit with all components."""

    # SVG canvas with padding for labels and legend
    pad = 80
    scale = 1.2  # pixels per mm
    legend_w = 280

    canvas_w = MAIN_S1_W * scale + 2 * pad + legend_w
    canvas_h = MAIN_S1_D * scale + 2 * pad + 160  # extra for title + notes
    title_h = 60

    svg = SVGBuilder(canvas_w, canvas_h + title_h)

    # Title
    svg.add_text(canvas_w / 2, 30, "MAIN UNIT — Top View (Open, Looking Down)", size=18,
                 color="#e0e0e0", anchor="middle", weight="bold")
    svg.add_text(canvas_w / 2, 50, f"Shell 1: {MAIN_S1_W:.0f}×{MAIN_S1_D:.0f}mm  |  "
                 f"Shell 2: {MAIN_S2_W:.0f}×{MAIN_S2_D:.0f}mm  |  "
                 f"Interior: {MAIN_INNER_W:.0f}×{MAIN_INNER_D:.0f}mm",
                 size=11, color="#aaa", anchor="middle")

    # Offset for drawing area
    ox = pad
    oy = pad + title_h

    def sx(mm):
        return ox + mm * scale

    def sy(mm):
        return oy + mm * scale

    def sw(mm):
        return mm * scale

    # --- Shell 1 (ASA outer) ---
    svg.add_rect(sx(0), sy(0), sw(MAIN_S1_W), sw(MAIN_S1_D),
                 fill="#4a3728", stroke="#8B6914", stroke_width=2, opacity=0.3,
                 label="", rx=8)

    # --- Foam cavity (area between S1 and S2) ---
    foam_inset = MAIN_WALL
    svg.add_rect(sx(foam_inset), sy(foam_inset),
                 sw(MAIN_S1_W - 2 * foam_inset), sw(MAIN_S1_D - 2 * foam_inset),
                 fill="#f0e68c", stroke="#b8a000", stroke_width=1, opacity=0.15,
                 label="")

    # --- Shell 2 (PETG structural) ---
    s2_offset = MAIN_WALL + MAIN_FOAM
    svg.add_rect(sx(s2_offset), sy(s2_offset),
                 sw(MAIN_S2_W), sw(MAIN_S2_D),
                 fill="#2a4a6a", stroke="#4a9ade", stroke_width=2, opacity=0.25,
                 label="", rx=4)

    # --- Interior space ---
    inner_offset = s2_offset + MAIN_WALL_S2
    svg.add_rect(sx(inner_offset), sy(inner_offset),
                 sw(MAIN_INNER_W), sw(MAIN_INNER_D),
                 fill="none", stroke="#4a9ade", stroke_width=0.5, stroke_dash="4,3")

    # ---- BATTERY ZONE ----
    batt_x = inner_offset + MAIN_ZONE_MARGIN
    batt_y = inner_offset + MAIN_ZONE_MARGIN

    # Battery zone boundary
    svg.add_rect(sx(batt_x), sy(batt_y), sw(MAIN_STACK_W), sw(MAIN_STACK_D),
                 fill="#1a3a1a", stroke="#2d8a2d", stroke_width=1.5, opacity=0.3)

    # Compression plates
    svg.add_rect(sx(batt_x), sy(batt_y + 5), sw(COMP_PLATE_W), sw(MAIN_STACK_D - 10),
                 fill="#888", stroke="#666", stroke_width=0.5, opacity=0.5,
                 label="", label_size=6)
    svg.add_rect(sx(batt_x + MAIN_STACK_W - COMP_PLATE_W), sy(batt_y + 5),
                 sw(COMP_PLATE_W), sw(MAIN_STACK_D - 10),
                 fill="#888", stroke="#666", stroke_width=0.5, opacity=0.5)

    # Individual cells — 4S × 2P
    cell_colors = ["#2d7a2d", "#258a25", "#2d7a2d", "#258a25"]
    for row in range(MAIN_CELLS_P):
        for col in range(MAIN_CELLS_S):
            cx = batt_x + COMP_PLATE_W + 2 + col * (CELL_W + 2)
            cy = batt_y + 5 + row * (CELL_L + 10)
            color = cell_colors[col]
            svg.add_rect(sx(cx), sy(cy), sw(CELL_W), sw(CELL_L),
                         fill=color, stroke="#1a5a1a", stroke_width=1, opacity=0.7,
                         rx=1)
            polarity = "+" if col % 2 == 0 else "-"
            cell_num = row * MAIN_CELLS_S + col + 1
            svg.add_text(sx(cx + CELL_W / 2), sy(cy + CELL_L / 2 - 5),
                         f"C{cell_num}", size=8, color="#c0ffc0", anchor="middle")
            svg.add_text(sx(cx + CELL_W / 2), sy(cy + CELL_L / 2 + 7),
                         f"{CELL_W:.0f}×{CELL_L:.0f}", size=6, color="#90d090", anchor="middle")
            # Terminal indicator (small dot at top)
            svg.add_circle(sx(cx + CELL_W / 2), sy(cy + 5), 3,
                           fill="#ffd700" if polarity == "+" else "#c0c0c0",
                           stroke="#333", stroke_width=0.5, opacity=0.8)

    # Busbars between cells (connecting series)
    for col in range(MAIN_CELLS_S - 1):
        for row in range(MAIN_CELLS_P):
            bx = batt_x + COMP_PLATE_W + 2 + col * (CELL_W + 2) + CELL_W - 3
            by = batt_y + 5 + row * (CELL_L + 10) + 3
            svg.add_rect(sx(bx), sy(by), sw(CELL_W / 2 + 5), sw(8),
                         fill="#cd7f32", stroke="#8B4513", stroke_width=0.5, opacity=0.7,
                         label="", label_size=5)

    # Battery zone label
    svg.add_text(sx(batt_x + MAIN_STACK_W / 2), sy(batt_y - 6),
                 f"BATTERY ZONE  {MAIN_STACK_W:.0f}×{MAIN_STACK_D:.0f}mm",
                 size=9, color="#4ade4a", anchor="middle", weight="bold")
    svg.add_text(sx(batt_x + MAIN_STACK_W / 2), sy(batt_y + MAIN_STACK_D + 12),
                 f"4S2P — 8× Narada 105Ah", size=8, color="#4ade4a", anchor="middle")

    # ---- ELECTRONICS ZONE ----
    elec_x = batt_x + MAIN_STACK_W + MAIN_ZONE_GAP
    elec_y = inner_offset + MAIN_ZONE_MARGIN

    # Electronics zone boundary
    svg.add_rect(sx(elec_x), sy(elec_y), sw(MAIN_ELEC_W), sw(MAIN_ELEC_D),
                 fill="#1a1a3a", stroke="#4a4ade", stroke_width=1.5, opacity=0.3,
                 label="", label_size=8)

    # MPPT controllers — 2×2 grid (as coded — shows overflow!)
    # As coded: 2 cols of EPEVER_D wide, 2 rows of EPEVER_W deep
    mppt_colors = ["#3a3a8a", "#4040a0", "#3535c0", "#3a3a8a"]
    overflow_shown = False
    for row in range(2):
        for col in range(2):
            mx = elec_x + 10 + col * (EPEVER_D + 10)
            my = elec_y + 10 + row * (EPEVER_W + 10)
            idx = row * 2 + col
            # Check if this MPPT overflows the zone
            overflows = (my + EPEVER_W) > (elec_y + MAIN_ELEC_D)
            fill = "#8a2020" if overflows else mppt_colors[idx]
            stroke_c = "#ff4444" if overflows else "#6a6ade"
            sw_val = 2 if overflows else 1
            svg.add_rect(sx(mx), sy(my), sw(EPEVER_D), sw(EPEVER_W),
                         fill=fill, stroke=stroke_c, stroke_width=sw_val, opacity=0.6,
                         rx=2)
            svg.add_text(sx(mx + EPEVER_D / 2), sy(my + EPEVER_W / 2 - 8),
                         f"MPPT{idx+1}", size=8, color="#c0c0ff", anchor="middle")
            svg.add_text(sx(mx + EPEVER_D / 2), sy(my + EPEVER_W / 2 + 4),
                         f"{EPEVER_D:.0f}×{EPEVER_W:.0f}", size=6, color="#9090cc", anchor="middle")
            svg.add_text(sx(mx + EPEVER_D / 2), sy(my + EPEVER_W / 2 + 14),
                         "EPever 2210AN", size=5, color="#8080aa", anchor="middle")
            if overflows and not overflow_shown:
                # Mark overflow region
                overflow_y = elec_y + MAIN_ELEC_D
                overflow_h = (my + EPEVER_W) - overflow_y
                svg.add_rect(sx(elec_x), sy(overflow_y), sw(MAIN_ELEC_W), sw(overflow_h),
                             fill="#ff0000", stroke="#ff0000", stroke_width=1, opacity=0.1,
                             stroke_dash="3,2")
                svg.add_text(sx(elec_x + MAIN_ELEC_W / 2), sy(overflow_y + overflow_h / 2),
                             f"OVERFLOW: {overflow_h:.0f}mm!", size=10, color="#ff4444",
                             anchor="middle", weight="bold")
                overflow_shown = True

    # BMS units (as coded: right of MPPT columns)
    bms_x_off = 10 + 2 * (EPEVER_D + 10) + 10  # 134mm from elec zone left
    for i in range(2):
        bx = elec_x + bms_x_off
        by = elec_y + 10 + i * (BMS_D + 15)
        overflows_w = (bx + BMS_W) > (elec_x + MAIN_ELEC_W)
        fill = "#8a4020" if overflows_w else "#6a3a6a"
        stroke_c = "#ff8844" if overflows_w else "#9a6a9a"
        svg.add_rect(sx(bx), sy(by), sw(BMS_W), sw(BMS_D),
                     fill=fill, stroke=stroke_c, stroke_width=1, opacity=0.6, rx=1)
        svg.add_text(sx(bx + BMS_W / 2), sy(by + BMS_D / 2 + 3),
                     f"BMS{i+1}  {BMS_W:.0f}×{BMS_D:.0f}", size=7,
                     color="#d0a0d0", anchor="middle")

    # Bus bar (as coded: right of BMS)
    bus_x = elec_x + bms_x_off + BMS_W + 10
    bus_d = MAIN_ELEC_D - 20
    overflows_bus = (bus_x + BUS_W) > (elec_x + MAIN_ELEC_W)
    fill = "#8a2020" if overflows_bus else "#8a8a30"
    stroke_c = "#ff4444" if overflows_bus else "#aaaa50"
    svg.add_rect(sx(bus_x), sy(elec_y + 10), sw(BUS_W), sw(bus_d),
                 fill=fill, stroke=stroke_c, stroke_width=1, opacity=0.5, rx=1,
                 label="BUS", label_size=7, label_color="#dddd80")
    if overflows_bus:
        svg.add_text(sx(bus_x + BUS_W / 2), sy(elec_y + 10 + bus_d / 2 + 12),
                     "OVERFLOW!", size=7, color="#ff4444", anchor="middle", weight="bold")

    # Fuse block
    fuse_x = elec_x + bms_x_off
    fuse_y = elec_y + 10 + 2 * (BMS_D + 15) + 10
    svg.add_rect(sx(fuse_x), sy(fuse_y), sw(FUSE_W), sw(FUSE_D),
                 fill="#8a6a20", stroke="#aa8a30", stroke_width=0.8, opacity=0.5, rx=1,
                 label=f"FUSE BLOCK {FUSE_W:.0f}×{FUSE_D:.0f}", label_size=6,
                 label_color="#ddcc80")

    # ANL main fuse
    anl_x = fuse_x + FUSE_W + 10
    anl_y = fuse_y + 5
    svg.add_rect(sx(anl_x), sy(anl_y), sw(ANL_W), sw(ANL_D),
                 fill="#8a5020", stroke="#aa7030", stroke_width=0.8, opacity=0.5, rx=1,
                 label=f"80A ANL", label_size=6, label_color="#ddbb80")

    # LEM current sensor
    lem_x = fuse_x
    lem_y = fuse_y + FUSE_D + 10
    svg.add_rect(sx(lem_x), sy(lem_y), sw(LEM_W), sw(LEM_D),
                 fill="#20608a", stroke="#4090ba", stroke_width=0.8, opacity=0.5, rx=1,
                 label=f"LEM", label_size=7, label_color="#80c0e0")

    # Thermal zone (upper corner of electronics zone)
    therm_x = elec_x + 5
    therm_y = elec_y + MAIN_ELEC_D - 120
    svg.add_rect(sx(therm_x), sy(therm_y), sw(100), sw(110),
                 fill="#6a2020", stroke="#aa4040", stroke_width=1, opacity=0.3,
                 stroke_dash="3,2")
    svg.add_text(sx(therm_x + 50), sy(therm_y + 12),
                 "THERMAL", size=8, color="#ee8080", anchor="middle", weight="bold")

    # Fan circle
    fan_cx = therm_x + 50
    fan_cy = therm_y + 60
    svg.add_circle(sx(fan_cx), sy(fan_cy), sw(FAN_DIAM / 2),
                   fill="#4a2020", stroke="#cc4444", stroke_width=0.8, opacity=0.4,
                   label="FAN 80mm", label_size=7, label_color="#ee8080")

    # Heater strip
    svg.add_rect(sx(therm_x + 5), sy(therm_y + 95), sw(90), sw(12),
                 fill="#cc4444", stroke="#ee6666", stroke_width=0.5, opacity=0.4,
                 label="HEATER", label_size=6, label_color="#ff9999")

    # Electronics zone label
    svg.add_text(sx(elec_x + MAIN_ELEC_W / 2), sy(elec_y - 6),
                 f"ELECTRONICS ZONE  {MAIN_ELEC_W:.0f}×{MAIN_ELEC_D:.0f}mm",
                 size=9, color="#6a6aff", anchor="middle", weight="bold")

    # Zone gap label
    gap_cx = batt_x + MAIN_STACK_W + MAIN_ZONE_GAP / 2
    svg.add_text(sx(gap_cx), sy(inner_offset + MAIN_INNER_D / 2),
                 f"{MAIN_ZONE_GAP:.0f}", size=7, color="#888", anchor="middle")
    svg.add_line(sx(batt_x + MAIN_STACK_W + 2), sy(inner_offset + MAIN_INNER_D / 2 - 10),
                 sx(batt_x + MAIN_STACK_W + 2), sy(inner_offset + MAIN_INNER_D / 2 + 10),
                 stroke="#666", stroke_width=0.5)
    svg.add_line(sx(elec_x - 2), sy(inner_offset + MAIN_INNER_D / 2 - 10),
                 sx(elec_x - 2), sy(inner_offset + MAIN_INNER_D / 2 + 10),
                 stroke="#666", stroke_width=0.5)

    # --- Dimension lines ---
    # Shell 1 width
    svg.add_dim_line(sx(0), sy(-12), sx(MAIN_S1_W), sy(-12),
                     f"S1: {MAIN_S1_W:.0f}mm", color="#8B6914")
    # Shell 2 width
    svg.add_dim_line(sx(s2_offset), sy(-5), sx(s2_offset + MAIN_S2_W), sy(-5),
                     f"S2: {MAIN_S2_W:.0f}mm", color="#4a9ade")
    # Shell 1 depth (left side)
    svg.add_dim_line(sx(-12), sy(0), sx(-12), sy(MAIN_S1_D),
                     f"S1: {MAIN_S1_D:.0f}mm", color="#8B6914")
    # Foam thickness indicator
    svg.add_text(sx(MAIN_WALL + MAIN_FOAM / 2), sy(MAIN_S1_D / 2),
                 f"FOAM {MAIN_FOAM:.0f}mm", size=7, color="#b8a000", anchor="middle")

    # --- Shell labels ---
    svg.add_text(sx(MAIN_S1_W / 2), sy(MAIN_S1_D + 15),
                 "Shell 1 (ASA outer)", size=9, color="#8B6914", anchor="middle")
    svg.add_text(sx(MAIN_S1_W / 2), sy(MAIN_S1_D + 28),
                 "Shell 2 (PETG structural)", size=9, color="#4a9ade", anchor="middle")

    # --- LEGEND ---
    lx = ox + MAIN_S1_W * scale + 30
    ly = oy + 10
    svg.add_text(lx, ly, "LEGEND", size=12, color="#e0e0e0", weight="bold")
    legend_items = [
        ("#4a3728", "#8B6914", "Shell 1 (ASA) — 5mm wall"),
        ("#f0e68c", "#b8a000", f"Foam cavity — {MAIN_FOAM:.0f}mm"),
        ("#2a4a6a", "#4a9ade", "Shell 2 (PETG) — 5mm wall"),
        ("#2d7a2d", "#1a5a1a", f"LiFePO4 cell — {CELL_W:.0f}×{CELL_L:.0f}mm"),
        ("#3a3a8a", "#6a6ade", f"EPever MPPT — {EPEVER_D:.0f}×{EPEVER_W:.0f}mm"),
        ("#6a3a6a", "#9a6a9a", f"Smart BMS — {BMS_W:.0f}×{BMS_D:.0f}mm"),
        ("#8a8a30", "#aaaa50", f"Distribution bus — {BUS_W:.0f}mm wide"),
        ("#8a6a20", "#aa8a30", "Fuse block / ANL fuse"),
        ("#20608a", "#4090ba", f"LEM sensor — {LEM_W:.0f}×{LEM_D:.0f}mm"),
        ("#6a2020", "#aa4040", "Thermal zone"),
        ("#888", "#666", "Compression plates"),
        ("#cd7f32", "#8B4513", "Busbars (series)"),
        ("#ff0000", "#ff4444", "OVERFLOW (component > zone)"),
    ]
    for i, (fill, stroke, desc) in enumerate(legend_items):
        iy = ly + 20 + i * 22
        svg.add_rect(lx, iy - 8, 14, 14, fill=fill, stroke=stroke, stroke_width=1, opacity=0.7, rx=2)
        svg.add_text(lx + 20, iy + 3, desc, size=9, color="#ccc")

    # --- ISSUES PANEL ---
    iy = ly + 20 + len(legend_items) * 22 + 20
    svg.add_text(lx, iy, "DIMENSIONAL ISSUES", size=12, color="#ff6666", weight="bold")
    issues_text = [
        f"1. MPPT 2×2 grid depth: {10 + 2*EPEVER_W + 10:.0f}mm",
        f"   vs zone depth: {MAIN_ELEC_D:.0f}mm",
        f"   OVERFLOW: {10 + 2*EPEVER_W + 10 - MAIN_ELEC_D:.0f}mm!",
        "",
        f"2. BMS+Bus right edge: {10 + 2*(EPEVER_D+10) + 10 + BMS_W + 10 + BUS_W:.0f}mm",
        f"   vs zone width: {MAIN_ELEC_W:.0f}mm",
        f"   OVERFLOW: {10 + 2*(EPEVER_D+10) + 10 + BMS_W + 10 + BUS_W - MAIN_ELEC_W:.0f}mm!",
        "",
        "SUGGESTED FIX:",
        f"  Arrange 4 MPPTs in single row:",
        f"  4×{EPEVER_D:.0f} + 3×10 = {4*EPEVER_D + 30:.0f}mm W",
        f"  × {EPEVER_W:.0f}mm D — fits in zone!",
        f"  BMS below MPPTs, bus beside",
    ]
    for j, line in enumerate(issues_text):
        color = "#ff8888" if "OVERFLOW" in line else "#ccaa88"
        if "SUGGESTED" in line or "Arrange" in line or "fits" in line:
            color = "#88cc88"
        svg.add_text(lx, iy + 18 + j * 15, line, size=8, color=color)

    # Save
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_unit_top_view.svg")
    with open(filepath, "w") as f:
        f.write(svg.render())
    print(f"\n  Created: {filepath}")
    return filepath


# ============================================================================
# SATELLITE UNIT TOP VIEW
# ============================================================================

def generate_satellite_svg():
    """Generate detailed top-view SVG of satellite unit with all components."""

    pad = 80
    scale = 1.8
    legend_w = 260

    canvas_w = SAT_S1_W * scale + 2 * pad + legend_w
    canvas_h = SAT_S1_D * scale + 2 * pad + 120
    title_h = 60

    svg = SVGBuilder(canvas_w, canvas_h + title_h)

    # Title
    svg.add_text(canvas_w / 2, 30, "SATELLITE UNIT — Top View (Open, Looking Down)", size=18,
                 color="#e0e0e0", anchor="middle", weight="bold")
    svg.add_text(canvas_w / 2, 50, f"Shell 1: {SAT_S1_W:.0f}×{SAT_S1_D:.0f}mm  |  "
                 f"Shell 2: {SAT_S2_W:.0f}×{SAT_S2_D:.0f}mm  |  "
                 f"Interior: {SAT_INNER_W:.0f}×{SAT_INNER_D:.0f}mm",
                 size=11, color="#aaa", anchor="middle")

    ox = pad
    oy = pad + title_h

    def sx(mm):
        return ox + mm * scale

    def sy(mm):
        return oy + mm * scale

    def sw(mm):
        return mm * scale

    # --- Shell 1 (ASA outer) ---
    svg.add_rect(sx(0), sy(0), sw(SAT_S1_W), sw(SAT_S1_D),
                 fill="#4a3728", stroke="#8B6914", stroke_width=2, opacity=0.3, rx=8)

    # --- Foam cavity ---
    foam_inset = SAT_WALL
    svg.add_rect(sx(foam_inset), sy(foam_inset),
                 sw(SAT_S1_W - 2 * foam_inset), sw(SAT_S1_D - 2 * foam_inset),
                 fill="#f0e68c", stroke="#b8a000", stroke_width=1, opacity=0.15)

    # --- Shell 2 (PETG) ---
    s2_off = SAT_WALL + SAT_FOAM
    svg.add_rect(sx(s2_off), sy(s2_off), sw(SAT_S2_W), sw(SAT_S2_D),
                 fill="#2a4a6a", stroke="#4a9ade", stroke_width=2, opacity=0.25, rx=4)

    # --- Interior ---
    inner_off = s2_off + SAT_WALL_S2
    svg.add_rect(sx(inner_off), sy(inner_off), sw(SAT_INNER_W), sw(SAT_INNER_D),
                 fill="none", stroke="#4a9ade", stroke_width=0.5, stroke_dash="4,3")

    # ---- BATTERY ZONE ----
    batt_x = inner_off + SAT_ZONE_MARGIN
    batt_y = inner_off + SAT_ZONE_MARGIN

    svg.add_rect(sx(batt_x), sy(batt_y), sw(SAT_STACK_W), sw(SAT_STACK_D),
                 fill="#1a3a1a", stroke="#2d8a2d", stroke_width=1.5, opacity=0.3)

    # Compression plates
    svg.add_rect(sx(batt_x), sy(batt_y + 5), sw(COMP_PLATE_W), sw(CELL_L),
                 fill="#888", stroke="#666", stroke_width=0.5, opacity=0.5)
    svg.add_rect(sx(batt_x + SAT_STACK_W - COMP_PLATE_W), sy(batt_y + 5),
                 sw(COMP_PLATE_W), sw(CELL_L),
                 fill="#888", stroke="#666", stroke_width=0.5, opacity=0.5)

    # 4 cells in single row
    cell_colors = ["#2d7a2d", "#258a25", "#2d7a2d", "#258a25"]
    for col in range(SAT_CELLS_S):
        cx = batt_x + COMP_PLATE_W + 2 + col * (CELL_W + 2)
        cy = batt_y + 5
        svg.add_rect(sx(cx), sy(cy), sw(CELL_W), sw(CELL_L),
                     fill=cell_colors[col], stroke="#1a5a1a", stroke_width=1, opacity=0.7, rx=1)
        polarity = "+" if col % 2 == 0 else "-"
        svg.add_text(sx(cx + CELL_W / 2), sy(cy + CELL_L / 2 - 8),
                     f"C{col+1}{polarity}", size=9, color="#c0ffc0", anchor="middle")
        svg.add_text(sx(cx + CELL_W / 2), sy(cy + CELL_L / 2 + 6),
                     f"{CELL_W:.0f}×{CELL_L:.0f}", size=7, color="#90d090", anchor="middle")
        # Terminal
        svg.add_circle(sx(cx + CELL_W / 2), sy(cy + 5), 3,
                       fill="#ffd700" if polarity == "+" else "#c0c0c0",
                       stroke="#333", stroke_width=0.5, opacity=0.8)

    # Busbars
    for col in range(SAT_CELLS_S - 1):
        bx = batt_x + COMP_PLATE_W + 2 + col * (CELL_W + 2) + CELL_W - 3
        by = batt_y + 5 + 3
        svg.add_rect(sx(bx), sy(by), sw(CELL_W / 2 + 5), sw(8),
                     fill="#cd7f32", stroke="#8B4513", stroke_width=0.5, opacity=0.7)

    svg.add_text(sx(batt_x + SAT_STACK_W / 2), sy(batt_y - 6),
                 f"BATTERY  {SAT_STACK_W:.0f}×{SAT_STACK_D:.0f}mm",
                 size=9, color="#4ade4a", anchor="middle", weight="bold")
    svg.add_text(sx(batt_x + SAT_STACK_W / 2), sy(batt_y + SAT_STACK_D + 12),
                 "4S — 4× Narada 105Ah", size=8, color="#4ade4a", anchor="middle")

    # ---- THERMAL ZONE ----
    therm_x = batt_x + SAT_STACK_W + SAT_ZONE_GAP
    therm_y = inner_off + SAT_ZONE_MARGIN

    svg.add_rect(sx(therm_x), sy(therm_y), sw(SAT_THERM_W), sw(SAT_THERM_D),
                 fill="#3a1a1a", stroke="#aa4040", stroke_width=1.5, opacity=0.3,
                 stroke_dash="3,2")

    # Heater strip
    svg.add_rect(sx(therm_x + 5), sy(therm_y + 5), sw(SAT_THERM_W - 10), sw(HEATER_D),
                 fill="#cc4444", stroke="#ee6666", stroke_width=0.5, opacity=0.5,
                 label="HEATER", label_size=7, label_color="#ff9999")

    # STC-1000
    svg.add_rect(sx(therm_x + 5), sy(therm_y + 30), sw(min(STC_W, SAT_THERM_W - 10)), sw(STC_D),
                 fill="#6a5020", stroke="#aa8040", stroke_width=0.8, opacity=0.5)
    svg.add_text(sx(therm_x + 5 + min(STC_W, SAT_THERM_W - 10) / 2), sy(therm_y + 30 + STC_D / 2 + 3),
                 f"STC-1000", size=7, color="#ddbb80", anchor="middle")
    # Flag if STC-1000 overflows
    if STC_W > SAT_THERM_W - 10:
        svg.add_text(sx(therm_x + SAT_THERM_W / 2), sy(therm_y + 30 + STC_D + 10),
                     f"STC {STC_W:.0f}mm > zone {SAT_THERM_W - 10:.0f}mm!",
                     size=6, color="#ff8844", anchor="middle")

    # Fan (circle — may extend beyond thermal zone width)
    fan_cx = therm_x + SAT_THERM_W / 2
    fan_cy = therm_y + SAT_THERM_D - FAN_DIAM / 2 - 5
    svg.add_circle(sx(fan_cx), sy(fan_cy), sw(FAN_DIAM / 2),
                   fill="#4a2020", stroke="#cc4444", stroke_width=1, opacity=0.35,
                   label="FAN 80mm", label_size=8, label_color="#ee8080")
    # Fan overflow indicator
    if FAN_DIAM > SAT_THERM_W:
        svg.add_text(sx(fan_cx), sy(fan_cy + FAN_DIAM / 2 + 10),
                     f"Fan {FAN_DIAM:.0f}mm > zone {SAT_THERM_W:.0f}mm",
                     size=7, color="#ff8844", anchor="middle")

    # Thermal zone label
    svg.add_text(sx(therm_x + SAT_THERM_W / 2), sy(therm_y - 6),
                 f"THERMAL  {SAT_THERM_W:.0f}×{SAT_THERM_D:.0f}mm",
                 size=9, color="#ee8080", anchor="middle", weight="bold")

    # Conduit indicators (right wall)
    conduit_x = inner_off + SAT_INNER_W + SAT_WALL_S2
    for i, (label, diam) in enumerate([("LEADS 16mm", 16), ("THERM 10mm", 10), ("PROBE 8mm", 8)]):
        cy = inner_off + 30 + i * 45
        svg.add_circle(sx(conduit_x), sy(cy), sw(diam / 2),
                       fill="#555", stroke="#888", stroke_width=0.8, opacity=0.6,
                       label="", label_size=6)
        svg.add_text(sx(conduit_x + diam / 2 + 8), sy(cy + 3),
                     label, size=6, color="#999")

    # --- Dimension lines ---
    svg.add_dim_line(sx(0), sy(-12), sx(SAT_S1_W), sy(-12),
                     f"S1: {SAT_S1_W:.0f}mm", color="#8B6914")
    svg.add_dim_line(sx(s2_off), sy(-5), sx(s2_off + SAT_S2_W), sy(-5),
                     f"S2: {SAT_S2_W:.0f}mm", color="#4a9ade")
    svg.add_dim_line(sx(-12), sy(0), sx(-12), sy(SAT_S1_D),
                     f"S1: {SAT_S1_D:.0f}mm", color="#8B6914")

    # Foam label
    svg.add_text(sx(SAT_WALL + SAT_FOAM / 2), sy(SAT_S1_D / 2),
                 f"FOAM {SAT_FOAM:.0f}mm", size=7, color="#b8a000", anchor="middle")

    # Shell labels
    svg.add_text(sx(SAT_S1_W / 2), sy(SAT_S1_D + 15),
                 "Shell 1 (ASA outer)", size=9, color="#8B6914", anchor="middle")
    svg.add_text(sx(SAT_S1_W / 2), sy(SAT_S1_D + 28),
                 "Shell 2 (PETG structural)", size=9, color="#4a9ade", anchor="middle")

    # --- LEGEND ---
    lx = ox + SAT_S1_W * scale + 30
    ly = oy + 10
    svg.add_text(lx, ly, "LEGEND", size=12, color="#e0e0e0", weight="bold")
    legend_items = [
        ("#4a3728", "#8B6914", "Shell 1 (ASA) — 5mm wall"),
        ("#f0e68c", "#b8a000", f"Foam cavity — {SAT_FOAM:.0f}mm"),
        ("#2a4a6a", "#4a9ade", "Shell 2 (PETG) — 5mm wall"),
        ("#2d7a2d", "#1a5a1a", f"LiFePO4 cell — {CELL_W:.0f}×{CELL_L:.0f}mm"),
        ("#888", "#666", "Compression plates"),
        ("#cd7f32", "#8B4513", "Busbars (series)"),
        ("#cc4444", "#ee6666", f"PTC heater — {HEATER_W:.0f}×{HEATER_D:.0f}mm"),
        ("#6a5020", "#aa8040", f"STC-1000 — {STC_W:.0f}×{STC_D:.0f}mm"),
        ("#4a2020", "#cc4444", f"Fan — {FAN_DIAM:.0f}mm diameter"),
        ("#555", "#888", "Conduit penetrations"),
    ]
    for i, (fill, stroke, desc) in enumerate(legend_items):
        iy = ly + 20 + i * 22
        svg.add_rect(lx, iy - 8, 14, 14, fill=fill, stroke=stroke, stroke_width=1, opacity=0.7, rx=2)
        svg.add_text(lx + 20, iy + 3, desc, size=9, color="#ccc")

    # --- NOTES ---
    ny = ly + 20 + len(legend_items) * 22 + 15
    svg.add_text(lx, ny, "NOTES", size=11, color="#e0e0e0", weight="bold")
    notes = [
        f"Fan 80mm > zone width 70mm",
        f"  (wall-mounted, extends into cell zone)",
        f"STC-1000: 71mm > zone width 60mm",
        f"  (mount rotated or on zone wall)",
        f"Conduits exit right wall to main unit",
        f"No BMS/MPPT — all in main unit",
    ]
    for j, note in enumerate(notes):
        color = "#ff8844" if ">" in note else "#aaa"
        svg.add_text(lx, ny + 16 + j * 14, note, size=8, color=color)

    # Save
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "satellite_unit_top_view.svg")
    with open(filepath, "w") as f:
        f.write(svg.render())
    print(f"\n  Created: {filepath}")
    return filepath


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("DIMENSIONAL ANALYSIS — Rev 3.2")
    print("=" * 70)

    # --- Component Dimensions Table ---
    print("\n--- COMPONENT DIMENSIONS (mm) ---")
    print(f"  Narada 105Ah cell (MEASURED):  {CELL_L}L × {CELL_W}W × {CELL_H}H + {TERMINAL_H}mm terminals")
    print(f"  EPever Tracer 2210AN MPPT:     {EPEVER_W}W × {EPEVER_H}H × {EPEVER_D}D (top-view: {EPEVER_D}×{EPEVER_W})")
    print(f"  4S 100A Smart BMS:             {BMS_W}W × {BMS_H}H × {BMS_D}D (top-view on edge: {BMS_W}×{BMS_D})")
    print(f"  LEM HASS 200-S sensor:         {LEM_W}W × {LEM_D}D × {LEM_H}H")
    print(f"  Distribution bus bar:          {BUS_W}W × ~{BUS_D}D")
    print(f"  3-way fuse block:              {FUSE_W}W × {FUSE_D}D")
    print(f"  80A ANL fuse + holder:         {ANL_W}W × {ANL_D}D")
    print(f"  STC-1000 thermostat:           {STC_W}W × {STC_D}D × {STC_H}H")
    print(f"  PTC heater strip:              {HEATER_W}W × {HEATER_D}D")
    print(f"  80mm fan:                      {FAN_DIAM}mm diameter")
    print(f"  Compression plate:             {COMP_PLATE_W}mm thick")

    # --- Main Unit ---
    print("\n" + "=" * 70)
    print("MAIN UNIT")
    print("=" * 70)

    print(f"\n--- Cell Stack (4S2P = 8 cells) ---")
    print(f"  Width:  {MAIN_CELLS_S}×{CELL_W} + {MAIN_CELLS_S-1}×2 (gaps) + 8 (compression) = {MAIN_STACK_W:.0f}mm")
    print(f"  Depth:  {MAIN_CELLS_P}×{CELL_L} + {MAIN_CELLS_P-1}×10 (gap) = {MAIN_STACK_D:.0f}mm")
    print(f"  Height: {CELL_H} + {TERMINAL_H} + 30 (clearance) = {MAIN_STACK_H:.0f}mm")

    print(f"\n--- Interior & Shells ---")
    issues = check_main_unit_layout()

    if issues:
        print(f"\n--- ISSUES FOUND: {len(issues)} ---")
        for i, issue in enumerate(issues, 1):
            print(f"  [{i}] {issue}")

    # --- Satellite Unit ---
    print("\n" + "=" * 70)
    print("SATELLITE UNIT")
    print("=" * 70)

    print(f"\n--- Cell Stack (4S = 4 cells) ---")
    print(f"  Width:  {SAT_CELLS_S}×{CELL_W} + {SAT_CELLS_S-1}×2 + 8 = {SAT_STACK_W:.0f}mm")
    print(f"  Depth:  {CELL_L} + 10 = {SAT_STACK_D:.0f}mm")
    print(f"  Height: {CELL_H} + {TERMINAL_H} + 30 = {SAT_STACK_H:.0f}mm")

    print(f"\n--- Interior & Shells ---")
    sat_issues = check_satellite_layout()

    if sat_issues:
        print(f"\n--- ISSUES FOUND: {len(sat_issues)} ---")
        for i, issue in enumerate(sat_issues, 1):
            print(f"  [{i}] {issue}")

    # --- Suggested Fixes ---
    print("\n" + "=" * 70)
    print("SUGGESTED LAYOUT FIXES")
    print("=" * 70)

    print("\nMAIN UNIT — Electronics Zone MPPT arrangement:")
    print(f"  Current (broken):  2x2 grid, {EPEVER_D}x{EPEVER_W} each -> needs {10+2*EPEVER_W+10:.0f}mm depth (have {MAIN_ELEC_D:.0f}mm)")
    opt_a_w = 4 * EPEVER_D + 3 * 10
    print(f"  Option A: 4-across → {opt_a_w:.0f}mm W × {EPEVER_W:.0f}mm D  {'✓ FITS' if opt_a_w <= MAIN_ELEC_W and EPEVER_W <= MAIN_ELEC_D else '✗ OVERFLOW'}")
    opt_b_w = EPEVER_D
    opt_b_d = 4 * EPEVER_W + 3 * 10
    print(f"  Option B: 1-column → {opt_b_w:.0f}mm W × {opt_b_d:.0f}mm D  {'✓ FITS' if opt_b_w <= MAIN_ELEC_W and opt_b_d <= MAIN_ELEC_D else '✗ OVERFLOW'}")
    opt_c_w = 2 * EPEVER_D + 10
    opt_c_d = 2 * EPEVER_W + 10
    print(f"  Option C: 2×2 rotated → {opt_c_w:.0f}mm W × {opt_c_d:.0f}mm D  {'✓ FITS' if opt_c_w <= MAIN_ELEC_W and opt_c_d <= MAIN_ELEC_D else '✗ OVERFLOW'}")

    # Best fit: option A (4 across)
    if opt_a_w <= MAIN_ELEC_W:
        remaining_d = MAIN_ELEC_D - EPEVER_W - 10  # space below MPPTs
        print(f"\n  RECOMMENDED: Option A (4-across)")
        print(f"    MPPTs:    {opt_a_w:.0f}mm W × {EPEVER_W:.0f}mm D")
        print(f"    Remaining below: {MAIN_ELEC_W:.0f}mm W × {remaining_d:.0f}mm D")
        print(f"    → BMS stacked on-edge: {BMS_W}×{2*BMS_D+10:.0f}mm — FITS below MPPTs")
        print(f"    → Bus bar, fuse block, LEM sensor alongside BMS")

    print("\nSATELLITE UNIT:")
    print(f"  Fan (80mm) > thermal zone width (70mm) — mount on end wall, protruding is fine")
    print(f"  STC-1000 (71mm) > zone usable width (60mm) — mount rotated or on wall bracket")
    print(f"  Overall satellite layout is VIABLE with minor accommodation")

    # --- Generate SVGs ---
    print("\n" + "=" * 70)
    print("GENERATING SVG VISUALIZATIONS")
    print("=" * 70)

    generate_main_unit_svg()
    generate_satellite_svg()

    print("\nDone.")


if __name__ == "__main__":
    main()
