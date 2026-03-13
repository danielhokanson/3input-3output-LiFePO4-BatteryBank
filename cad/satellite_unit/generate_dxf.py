#!/usr/bin/env python3
"""
Generate DXF enclosure drawings for the Satellite Unit (Rev 3.2).

Each satellite unit contains:
  - 1× 4S string (4× Narada 105Ah LiFePO4 cells)
  - Thermal management only (heater, fan, thermostat)
  - NO BMS, NO MPPT, NO fuses — all electronics in main unit
  - External leads to main unit (power + BMS sense wires)

Produces 2D profile drawings importable into Autodesk Fusion as sketches.
All dimensions in millimeters.

Usage:
    python cad/satellite_unit/generate_dxf.py

Output:
    cad/satellite_unit/dxf/1_top_view.dxf
    cad/satellite_unit/dxf/2_cross_section_front.dxf
    cad/satellite_unit/dxf/3_cross_section_side.dxf
    cad/satellite_unit/dxf/4_lead_exit_view.dxf
    cad/satellite_unit/dxf/5_zone_layout.dxf
    cad/satellite_unit/dxf/6_cell_layout_detail.dxf
    cad/satellite_unit/dxf/7_cap_top_view.dxf
    cad/satellite_unit/dxf/8_cap_profile.dxf
    cad/satellite_unit/dxf/9_lid_top_view.dxf
"""

import os
import ezdxf

# ---------------------------------------------------------------------------
# PARAMETRIC DIMENSIONS (all in mm)
# NOTE: Narada 105Ah cell dimensions are PLACEHOLDER — verify against datasheet
# ---------------------------------------------------------------------------

# Individual LiFePO4 cell (Narada 105Ah — MEASURED)
CELL_L = 129.0   # length (footprint, long axis)
CELL_W = 36.0    # width (footprint, short axis / thickness)
CELL_H = 256.0   # height (body only, standing upright)
TERMINAL_H = 4.0 # terminal protrusion above cell body

# Battery zone — 1× 4S string (4 cells in a single row)
CELLS_S = 4      # cells in series
CELLS_P = 1      # parallel strings (just one per satellite)

STACK_W = CELLS_S * CELL_W + (CELLS_S - 1) * 2 + 8   # 4×62 + gaps + compression = 262
STACK_D = CELL_L + 10.0                                # 1 cell deep + margin = 185
STACK_H = CELL_H + TERMINAL_H + 30.0                    # cells + terminals + busbars + clearance

# Thermal zone — heater + fan + thermostat
# Mounted as a compartment at one end of the battery zone
THERM_W = 70.0    # width (compact, beside cells)
THERM_D = STACK_D # same depth as cells
THERM_H = STACK_H # same height as cells

# Fan specs (80mm fan on end wall)
FAN_DIAM = 80.0

# Shell geometry
WALL = 5.0       # Shell 1 wall thickness
WALL_S2 = 5.0    # Shell 2 wall thickness
FOAM = 30.0

# Foam-pressure ribs (visual guides for Fusion — protrude into foam cavity)
RIB_W = 3.0         # rib width (along wall surface)
RIB_H = 10.0        # rib height (protrusion into foam cavity)
RIB_SPACING = 100.0  # center-to-center spacing around perimeter

# Conduit sizes
CONDUIT_LEADS = 16.0   # power leads + BMS sense wires
CONDUIT_THERMAL = 10.0 # heater/fan 12V feed
CONDUIT_PROBE = 8.0    # thermostat probe

# Spacing
ZONE_GAP = 15.0
ZONE_MARGIN = 10.0
BASE_THICK = WALL

# Cap rim — flush with Shell 1 outer, inner lip slips inside Shell 2
CAP_LIP = 0.0          # flush with S1 outer (no overhang)
CAP_THICK = 8.0
CAP_FOAM_FLANGE = 20.0 # flange drops from S1 inner to S2 outer in foam gap
CAP_INNER_LIP = 3.0    # small lip that slips inside S2 inner wall
CAP_INNER_LIP_DROP = 10.0  # how far the inner lip extends below S2 top
CAP_GASKET_W = 4.0         # gasket cord diameter / groove width
CAP_GASKET_D = 2.5         # groove depth cut into cap top surface
CAP_GASKET_MARGIN = 3.0    # margin from foam edge to gasket center
CAP_BOLT_SPACING = 80.0
INSERT_OD = 6.0            # M4 brass heat-set insert outer diameter
INSERT_DEPTH = 6.0         # insert pressed into cap from below

# Foam anchor teeth — protrude from cap flange underside into wet foam
# Sized to fill the foam gap for alignment (cap can only drop straight down)
FOAM_TOOTH_W = 5.0         # tooth width along cap perimeter
FOAM_TOOTH_D = 10.0        # protrusion depth downward into foam
FOAM_TOOTH_THICK = FOAM - 4.0  # radial thickness (26mm in 30mm gap = 2mm clearance/side)
FOAM_TOOTH_SPACING = 50.0  # center-to-center spacing around perimeter

# Lid (thick for insulation — infill replaces foam)
LID_THICK = 25.0          # thick body; 20% infill = insulation
LID_OVERHANG = 15.0       # beyond cap rim on all sides
LID_SKIRT = 20.0          # rain skirt drops around cap rim
LID_TOTAL_H = LID_THICK + LID_SKIRT
LID_DRIP_INSET = 3.0      # drip edge groove on skirt underside
LID_DRIP_DEPTH = 3.0
LID_DRIP_WIDTH = 2.0

# Fillet / chamfer (applied in Fusion after panel splitting)
FILLET_OUTER = 8.0         # outer boulder edges (Shell 1) — rounded
FILLET_INNER = 5.0         # inner structural edges (Shell 2) — matches wall thickness
CHAMFER_LID = 3.0          # lid top edges — 45° chamfer for print overhang

# Fasteners
M4_HOLE = 4.5
M4_EDGE_DIST = 10.0

# ---------------------------------------------------------------------------
# DERIVED DIMENSIONS
# ---------------------------------------------------------------------------

# Component space (defines interior volume)
INNER_W = 2 * ZONE_MARGIN + STACK_W + ZONE_GAP + THERM_W
INNER_D = max(STACK_D, THERM_D) + 2 * ZONE_MARGIN
INNER_H = max(STACK_H, THERM_H) + BASE_THICK

# Middle structural shell (Shell 2) — wraps directly around component space
MID_W = INNER_W + 2 * WALL_S2
MID_D = INNER_D + 2 * WALL_S2
MID_H = INNER_H + WALL_S2

# Outer boulder shell (Shell 1)
OUTER_W = MID_W + 2 * (FOAM + WALL)
OUTER_D = MID_D + 2 * (FOAM + WALL)
OUTER_H = MID_H + FOAM + WALL + BASE_THICK

# Cap
CAP_OUTER_W = OUTER_W + 2 * CAP_LIP
CAP_OUTER_D = OUTER_D + 2 * CAP_LIP
CAP_INNER_W = INNER_W - 2 * CAP_INNER_LIP
CAP_INNER_D = INNER_D - 2 * CAP_INNER_LIP

# Lid
LID_W = CAP_OUTER_W + 2 * LID_OVERHANG
LID_D = CAP_OUTER_D + 2 * LID_OVERHANG

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dxf")

# ---------------------------------------------------------------------------
# LAYER DEFINITIONS
# ---------------------------------------------------------------------------

LAYERS = {
    "SHELL_1":      {"color": 1},   # red   — ASA outer
    "SHELL_2":      {"color": 3},   # green — PETG structural
    "FOAM_CAVITY":  {"color": 40},  # orange
    "BATTERY_ZONE": {"color": 2},   # yellow
    "THERMAL_ZONE": {"color": 10},  # red-orange
    "CELLS":        {"color": 6},   # magenta
    "COMPONENTS":   {"color": 30},  # orange-brown
    "CONDUITS":     {"color": 4},   # cyan
    "DIMENSIONS":   {"color": 7},   # white
    "FASTENERS":    {"color": 2},   # yellow
    "ANNOTATIONS":  {"color": 7},   # white
    "CAP":          {"color": 30},  # orange-brown
    "LID":          {"color": 6},   # magenta
    "GASKET":       {"color": 8},   # gray
}


def setup_doc():
    doc = ezdxf.new("R2010")
    for name, props in LAYERS.items():
        doc.layers.add(name, color=props["color"])
    return doc


def add_rect(msp, x, y, w, h, layer):
    points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})


def add_circle(msp, cx, cy, r, layer):
    msp.add_circle((cx, cy), r, dxfattribs={"layer": layer})


def add_label(msp, x, y, text, layer="ANNOTATIONS", height=4):
    msp.add_text(
        text,
        height=height,
        dxfattribs={"layer": layer, "insert": (x, y)}
    )


def tooth_positions_around_rect(rect_w, rect_d, spacing, tooth_w,
                                bolt_positions=None, clearance=15.0):
    """Return (x, y, is_horizontal) tuples for foam anchor teeth along a
    rectangle perimeter.  is_horizontal=True means the tooth lies on a
    top/bottom edge (wide axis along X).
    If bolt_positions is given, skip any tooth within clearance of a bolt."""
    positions = []
    hw, hd = rect_w / 2, rect_d / 2
    # Top / bottom edges
    n_w = max(2, round(rect_w / spacing) + 1)
    for i in range(n_w):
        x = -hw + tooth_w / 2 + i * (rect_w - tooth_w) / max(1, n_w - 1)
        positions.append((x,  hd, True))
        positions.append((x, -hd, True))
    # Left / right edges (skip corners already covered)
    n_d = max(1, round(rect_d / spacing) - 1)
    for i in range(n_d):
        y = -hd + tooth_w / 2 + (i + 1) * (rect_d - tooth_w) / (n_d + 1)
        positions.append((-hw, y, False))
        positions.append(( hw, y, False))
    # Filter out teeth that overlap bolt positions
    if bolt_positions:
        filtered = []
        for tx, ty, horiz in positions:
            conflict = False
            for bx, by in bolt_positions:
                if ((tx - bx) ** 2 + (ty - by) ** 2) ** 0.5 < clearance:
                    conflict = True
                    break
            if not conflict:
                filtered.append((tx, ty, horiz))
        positions = filtered
    return positions


def bolt_positions_around_rect(outer_w, outer_d, edge_dist, spacing):
    positions = []
    hw = outer_w / 2
    hd = outer_d / 2
    n_top = max(2, round((outer_w - 2 * edge_dist) / spacing) + 1)
    for i in range(n_top):
        x = -hw + edge_dist + i * (outer_w - 2 * edge_dist) / max(1, n_top - 1)
        positions.append((x, hd))
    for i in range(n_top):
        x = -hw + edge_dist + i * (outer_w - 2 * edge_dist) / max(1, n_top - 1)
        positions.append((x, -hd))
    # Left/right edges: bolts at x = ±hw, y spaced (skip corners)
    n_side = max(1, round((outer_d - 2 * edge_dist) / spacing) - 1)
    for i in range(n_side):
        y = -hd + edge_dist + (i + 1) * (outer_d - 2 * edge_dist) / (n_side + 1)
        positions.append((-hw, y))
    for i in range(n_side):
        y = -hd + edge_dist + (i + 1) * (outer_d - 2 * edge_dist) / (n_side + 1)
        positions.append((hw, y))
    return positions


# ---------------------------------------------------------------------------
# DRAWING 1: Top View — Footprint (plan view)
# ---------------------------------------------------------------------------

def generate_top_view():
    """Top/plan view — two nested shells centered on origin."""
    doc = setup_doc()
    msp = doc.modelspace()

    add_rect(msp, -OUTER_W / 2, -OUTER_D / 2, OUTER_W, OUTER_D, "SHELL_1")
    add_rect(msp, -MID_W / 2, -MID_D / 2, MID_W, MID_D, "SHELL_2")

    # Battery zone
    batt_x = -INNER_W / 2 + ZONE_MARGIN
    batt_y = -STACK_D / 2
    add_rect(msp, batt_x, batt_y, STACK_W, STACK_D, "BATTERY_ZONE")
    add_label(msp, batt_x + 5, batt_y + 5, "4S CELLS", "BATTERY_ZONE", height=5)

    # Thermal zone
    therm_x = batt_x + STACK_W + ZONE_GAP
    therm_y = -THERM_D / 2
    add_rect(msp, therm_x, therm_y, THERM_W, THERM_D, "THERMAL_ZONE")
    add_label(msp, therm_x + 3, therm_y + 5, "THERM", "THERMAL_ZONE", height=4)

    # Lead conduit exit — right end of thermal zone
    conduit_x = therm_x + THERM_W + 5
    add_circle(msp, conduit_x, 0, CONDUIT_LEADS / 2, "CONDUITS")
    add_label(msp, conduit_x + CONDUIT_LEADS / 2 + 2, -3,
              "LEADS", "CONDUITS", height=3)

    add_label(msp, OUTER_W / 2 + 5, 0, f"W={OUTER_W:.0f}", "DIMENSIONS", height=4)
    add_label(msp, 0, OUTER_D / 2 + 5, f"D={OUTER_D:.0f}", "DIMENSIONS", height=4)

    filepath = os.path.join(OUTPUT_DIR, "1_top_view.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 2: Front Cross-Section
# ---------------------------------------------------------------------------

def generate_cross_section_front():
    """Front cross-section — nested shells + foam + cell zone + thermal zone."""
    doc = setup_doc()
    msp = doc.modelspace()

    # Shell 1
    add_rect(msp, -OUTER_W / 2, 0, OUTER_W, OUTER_H, "SHELL_1")

    # Foam
    add_rect(msp, -OUTER_W / 2 + WALL, BASE_THICK,
             OUTER_W - 2 * WALL, OUTER_H - WALL - BASE_THICK, "FOAM_CAVITY")

    # Shell 2
    s2_x = -MID_W / 2
    s2_y = BASE_THICK + FOAM
    add_rect(msp, s2_x, s2_y, MID_W, MID_H, "SHELL_2")

    # Battery zone (left, 4 cells)
    batt_x = -INNER_W / 2 + ZONE_MARGIN
    batt_y = s2_y + WALL_S2
    add_rect(msp, batt_x, batt_y, STACK_W, STACK_H, "BATTERY_ZONE")
    add_label(msp, batt_x + 2, batt_y + STACK_H / 2 - 4,
              "4S CELLS", "BATTERY_ZONE", height=4)

    # Thermal zone (right, compact)
    therm_x = batt_x + STACK_W + ZONE_GAP
    therm_y = s2_y + WALL_S2
    add_rect(msp, therm_x, therm_y, THERM_W, THERM_H, "THERMAL_ZONE")
    add_label(msp, therm_x + 2, therm_y + THERM_H / 2 - 4,
              "THERM", "THERMAL_ZONE", height=4)

    # Fan opening (circle on right wall at mid-height of thermal zone)
    fan_cx = -OUTER_W / 2
    fan_cy = therm_y + THERM_H / 2
    add_circle(msp, OUTER_W / 2, fan_cy, FAN_DIAM / 2, "THERMAL_ZONE")

    # Cap rim (full profile showing flanges spanning both shells)
    cap_y = OUTER_H
    s1o_w = OUTER_W / 2
    s1i_w = s1o_w - WALL
    s2o_w = MID_W / 2
    s2i_w = s2o_w - WALL_S2
    cap_top_y = cap_y + CAP_THICK
    s2_top_y = BASE_THICK + FOAM + MID_H
    flange_bot_y = cap_y - CAP_FOAM_FLANGE
    inner_lip_bot_y = s2_top_y - CAP_INNER_LIP_DROP
    inner_lip_w = s2i_w - CAP_INNER_LIP

    # Flush cap — outer edge aligned with S1 outer
    cap_pts_r = [
        (s1o_w, cap_top_y),
        (s1o_w, cap_y),
        (s1i_w, cap_y),
        (s1i_w, flange_bot_y),
        (s2o_w, flange_bot_y),
        (s2o_w, s2_top_y),
        (s2i_w, s2_top_y),
        (s2i_w, inner_lip_bot_y),
        (inner_lip_w, inner_lip_bot_y),
        (inner_lip_w, cap_top_y),
        (s1o_w, cap_top_y),
    ]
    msp.add_lwpolyline(cap_pts_r, dxfattribs={"layer": "CAP"})
    cap_pts_l = [(-x, y) for x, y in cap_pts_r]
    msp.add_lwpolyline(cap_pts_l, dxfattribs={"layer": "CAP"})

    # Foam anchor teeth (cross-section, on flange underside)
    flange_cx_w = (s1i_w + s2o_w) / 2
    tooth_hw_w = FOAM_TOOTH_THICK / 2
    tooth_bot_y = flange_bot_y - FOAM_TOOTH_D
    for sign in [1, -1]:
        fx = sign * flange_cx_w
        msp.add_lwpolyline([
            (fx - sign * tooth_hw_w, flange_bot_y),
            (fx - sign * tooth_hw_w, tooth_bot_y),
            (fx + sign * tooth_hw_w, tooth_bot_y),
            (fx + sign * tooth_hw_w, flange_bot_y),
        ], dxfattribs={"layer": "CAP"})

    # Lid (sits on cap rim)
    lid_outer_w = s1o_w + LID_OVERHANG
    lid_top_y = cap_top_y + LID_THICK
    lid_skirt_bot_y = cap_top_y - LID_SKIRT
    add_rect(msp, -lid_outer_w, lid_skirt_bot_y,
             2 * lid_outer_w, LID_THICK + LID_SKIRT, "LID")
    # Hollow out inside (lid body sits on cap top)
    add_rect(msp, -(s1o_w + 1), cap_top_y,
             2 * (s1o_w + 1), LID_THICK, "LID")

    # --- Foam-pressure ribs (front cross-section, left/right walls) ---
    # Shell 1 inner wall ribs — protrude inward from S1 inner face into foam
    s1_inner_left = -OUTER_W / 2 + WALL
    s1_inner_right = OUTER_W / 2 - WALL
    rib_zone_bottom = BASE_THICK + 50
    rib_zone_top = OUTER_H - WALL - 50
    num_ribs_front = max(1, int((rib_zone_top - rib_zone_bottom) / RIB_SPACING) + 1)
    for i in range(num_ribs_front):
        rib_y = rib_zone_bottom + i * RIB_SPACING
        if rib_y + RIB_W > rib_zone_top:
            break
        # Left wall: rib points right (into foam)
        add_rect(msp, s1_inner_left, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")
        # Right wall: rib points left (into foam)
        add_rect(msp, s1_inner_right - RIB_H, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")

    # Shell 2 outer wall ribs — protrude outward from S2 outer face into foam
    s2_outer_left = -MID_W / 2
    s2_outer_right = MID_W / 2
    s2_rib_zone_bottom = s2_y + 50
    s2_rib_zone_top = s2_y + MID_H - 50
    num_ribs_s2_front = max(1, int((s2_rib_zone_top - s2_rib_zone_bottom) / RIB_SPACING) + 1)
    for i in range(num_ribs_s2_front):
        rib_y = s2_rib_zone_bottom + i * RIB_SPACING
        if rib_y + RIB_W > s2_rib_zone_top:
            break
        # Left wall: rib points left (into foam)
        add_rect(msp, s2_outer_left - RIB_H, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")
        # Right wall: rib points right (into foam)
        add_rect(msp, s2_outer_right, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")

    # Labels
    add_label(msp, OUTER_W / 2 + 5, OUTER_H / 2,
              f"H={OUTER_H:.0f}", "DIMENSIONS", height=4)
    add_label(msp, -OUTER_W / 2 - 50, OUTER_H / 2,
              f"W={OUTER_W:.0f}", "DIMENSIONS", height=4)
    add_label(msp, OUTER_W / 2 + 5, fan_cy + 5,
              f"FAN {FAN_DIAM:.0f}mm", "THERMAL_ZONE", height=3)

    filepath = os.path.join(OUTPUT_DIR, "2_cross_section_front.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 3: Side Cross-Section
# ---------------------------------------------------------------------------

def generate_cross_section_side():
    """Side cross-section — depth axis (cells are 1 deep)."""
    doc = setup_doc()
    msp = doc.modelspace()

    add_rect(msp, -OUTER_D / 2, 0, OUTER_D, OUTER_H, "SHELL_1")
    add_rect(msp, -OUTER_D / 2 + WALL, BASE_THICK,
             OUTER_D - 2 * WALL, OUTER_H - WALL - BASE_THICK, "FOAM_CAVITY")

    s2_y = BASE_THICK + FOAM
    add_rect(msp, -MID_D / 2, s2_y, MID_D, MID_H, "SHELL_2")

    # Cell depth profile (1 cell deep)
    batt_y = s2_y + WALL_S2
    add_rect(msp, -CELL_L / 2, batt_y, CELL_L, CELL_H, "CELLS")
    add_label(msp, -CELL_L / 2 + 2, batt_y + CELL_H / 2 - 4,
              "CELL", "CELLS", height=4)

    # Cell dimension label
    add_label(msp, OUTER_D / 2 + 5, OUTER_H / 2,
              f"D={OUTER_D:.0f}", "DIMENSIONS", height=4)
    add_label(msp, -OUTER_D / 2 - 5, batt_y + CELL_H / 2,
              f"CELL L={CELL_L:.0f}", "CELLS", height=3)

    # --- Foam-pressure ribs (side cross-section, left/right walls on depth axis) ---
    # Shell 1 inner wall ribs — protrude inward from S1 inner face into foam
    s1_inner_left_side = -OUTER_D / 2 + WALL
    s1_inner_right_side = OUTER_D / 2 - WALL
    rib_zone_bottom_side = BASE_THICK + 50
    rib_zone_top_side = OUTER_H - WALL - 50
    num_ribs_side = max(1, int((rib_zone_top_side - rib_zone_bottom_side) / RIB_SPACING) + 1)
    for i in range(num_ribs_side):
        rib_y = rib_zone_bottom_side + i * RIB_SPACING
        if rib_y + RIB_W > rib_zone_top_side:
            break
        # Left wall: rib points right (into foam)
        add_rect(msp, s1_inner_left_side, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")
        # Right wall: rib points left (into foam)
        add_rect(msp, s1_inner_right_side - RIB_H, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")

    # Shell 2 outer wall ribs — protrude outward from S2 outer face into foam
    s2_outer_left_side = -MID_D / 2
    s2_outer_right_side = MID_D / 2
    s2_rib_zone_bottom_side = s2_y + 50
    s2_rib_zone_top_side = s2_y + MID_H - 50
    num_ribs_s2_side = max(1, int((s2_rib_zone_top_side - s2_rib_zone_bottom_side) / RIB_SPACING) + 1)
    for i in range(num_ribs_s2_side):
        rib_y = s2_rib_zone_bottom_side + i * RIB_SPACING
        if rib_y + RIB_W > s2_rib_zone_top_side:
            break
        # Left wall: rib points left (into foam)
        add_rect(msp, s2_outer_left_side - RIB_H, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")
        # Right wall: rib points right (into foam)
        add_rect(msp, s2_outer_right_side, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")

    # Cap
    s1_outer = OUTER_D / 2
    s1_inner = s1_outer - WALL
    s2_outer = MID_D / 2
    s2_inner = s2_outer - WALL_S2
    s2_top = BASE_THICK + FOAM + MID_H
    cap_top = OUTER_H + CAP_THICK
    flange_bottom = OUTER_H - CAP_FOAM_FLANGE
    inner_lip_bottom = s2_top - CAP_INNER_LIP_DROP
    inner_lip_inner = s2_inner - CAP_INNER_LIP

    # Flush cap profile (side view)
    pts_r = [
        (s1_outer, cap_top),
        (s1_outer, OUTER_H),
        (s1_inner, OUTER_H),
        (s1_inner, flange_bottom),
        (s2_outer, flange_bottom),
        (s2_outer, s2_top),
        (s2_inner, s2_top),
        (s2_inner, inner_lip_bottom),
        (inner_lip_inner, inner_lip_bottom),
        (inner_lip_inner, cap_top),
        (s1_outer, cap_top),
    ]
    msp.add_lwpolyline(pts_r, dxfattribs={"layer": "CAP"})
    pts_l = [(-x, y) for x, y in pts_r]
    msp.add_lwpolyline(pts_l, dxfattribs={"layer": "CAP"})

    # Foam anchor teeth (side cross-section)
    flange_cx_d = (s1_inner + s2_outer) / 2
    tooth_hw_d = FOAM_TOOTH_THICK / 2
    tooth_bot_d = flange_bottom - FOAM_TOOTH_D
    for sign in [1, -1]:
        fx = sign * flange_cx_d
        msp.add_lwpolyline([
            (fx - sign * tooth_hw_d, flange_bottom),
            (fx - sign * tooth_hw_d, tooth_bot_d),
            (fx + sign * tooth_hw_d, tooth_bot_d),
            (fx + sign * tooth_hw_d, flange_bottom),
        ], dxfattribs={"layer": "CAP"})

    # Lid (sits on cap rim)
    lid_outer_d = s1_outer + LID_OVERHANG
    lid_top_y = cap_top + LID_THICK
    lid_skirt_bot_y = cap_top - LID_SKIRT
    lid_pts = [
        (lid_outer_d, lid_top_y),
        (lid_outer_d, lid_skirt_bot_y),
        (s1_outer + 1, lid_skirt_bot_y),
        (s1_outer + 1, cap_top),
        (inner_lip_inner - 1, cap_top),
        (inner_lip_inner - 1, lid_skirt_bot_y),
        (-lid_outer_d, lid_skirt_bot_y),
        (-lid_outer_d, lid_top_y),
        (lid_outer_d, lid_top_y),
    ]
    msp.add_lwpolyline(lid_pts, dxfattribs={"layer": "LID"})
    add_label(msp, lid_outer_d + 3, lid_top_y - LID_THICK / 2,
              f"LID {LID_THICK:.0f}mm", "LID", height=3)

    filepath = os.path.join(OUTPUT_DIR, "3_cross_section_side.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 4: Lead Exit View (right-side face — conduits)
# ---------------------------------------------------------------------------

def generate_lead_exit_view():
    """Right face showing lead/conduit exit points to main unit.

    X = depth axis (outer shell depth), Y = height axis.
    """
    doc = setup_doc()
    msp = doc.modelspace()

    # Right face outline (depth × height)
    add_rect(msp, -OUTER_D / 2, 0, OUTER_D, OUTER_H, "SHELL_1")

    # Conduit positions on right face
    conduit_y = OUTER_H * 0.4  # mid-lower area

    # Main lead bundle (power + BMS sense wires) — large conduit
    lead_x = 0
    add_circle(msp, lead_x, conduit_y, CONDUIT_LEADS / 2, "CONDUITS")
    add_label(msp, lead_x + CONDUIT_LEADS / 2 + 3, conduit_y - 4,
              f"LEADS (+/-/BMS) dia={CONDUIT_LEADS:.0f}mm", "CONDUITS", height=4)

    # Thermal 12V feed conduit
    therm_x = lead_x + 50
    add_circle(msp, therm_x, conduit_y, CONDUIT_THERMAL / 2, "CONDUITS")
    add_label(msp, therm_x + CONDUIT_THERMAL / 2 + 3, conduit_y - 4,
              f"THERM 12V dia={CONDUIT_THERMAL:.0f}mm", "THERMAL_ZONE", height=4)

    # Probe conduit
    probe_x = therm_x + 40
    add_circle(msp, probe_x, conduit_y, CONDUIT_PROBE / 2, "CONDUITS")
    add_label(msp, probe_x + CONDUIT_PROBE / 2 + 3, conduit_y - 4,
              f"PROBE dia={CONDUIT_PROBE:.0f}mm", "CONDUITS", height=4)

    # Fan opening (80mm circle, centered on face at thermal zone height)
    fan_y = OUTER_H * 0.5
    add_circle(msp, 0, fan_y, FAN_DIAM / 2, "THERMAL_ZONE")
    add_label(msp, FAN_DIAM / 2 + 3, fan_y,
              f"FAN OPENING {FAN_DIAM:.0f}mm", "THERMAL_ZONE", height=4)

    add_label(msp, -OUTER_D / 2 + 5, 5,
              f"RIGHT FACE (lead exit)  D={OUTER_D:.0f} x H={OUTER_H:.0f} mm",
              "ANNOTATIONS", height=5)
    add_label(msp, -OUTER_D / 2 + 5, OUTER_H - 10,
              "Conduit routes to MAIN UNIT terminal blocks",
              "ANNOTATIONS", height=4)

    filepath = os.path.join(OUTPUT_DIR, "4_lead_exit_view.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 5: Interior Zone Layout (top-down plan)
# ---------------------------------------------------------------------------

def generate_zone_layout():
    """Top-down interior layout showing cell footprints + thermal zone.

    Origin at center of inner shell.
    """
    doc = setup_doc()
    msp = doc.modelspace()

    # Shell 2 interior outline
    add_rect(msp, -INNER_W / 2, -INNER_D / 2, INNER_W, INNER_D, "SHELL_2")

    # Battery zone
    batt_x = -INNER_W / 2 + ZONE_MARGIN
    batt_y = -STACK_D / 2
    add_rect(msp, batt_x, batt_y, STACK_W, STACK_D, "BATTERY_ZONE")

    # Individual cell footprints (CELL_W × CELL_L each)
    PLATE_W = 4.0
    for col in range(CELLS_S):
        cx = batt_x + PLATE_W + 2 + col * (CELL_W + 2)
        cy = batt_y + 5
        add_rect(msp, cx, cy, CELL_W, CELL_L, "CELLS")
        polarity = "+" if col % 2 == 0 else "-"
        add_label(msp, cx + CELL_W / 2 - 4, cy + CELL_L / 2 - 3,
                  f"C{col+1}{polarity}", "CELLS", height=5)

    # Compression plates
    add_rect(msp, batt_x, batt_y + 5, PLATE_W, CELL_L, "COMPONENTS")
    add_rect(msp, batt_x + STACK_W - PLATE_W, batt_y + 5, PLATE_W, CELL_L, "COMPONENTS")

    add_label(msp, batt_x + 2, -STACK_D / 2 + STACK_D + 5,
              f"4S  ({CELL_W:.0f}W x {CELL_L:.0f}L mm each)", "BATTERY_ZONE", height=4)

    # Thermal zone
    therm_x = batt_x + STACK_W + ZONE_GAP
    therm_y = -THERM_D / 2
    add_rect(msp, therm_x, therm_y, THERM_W, THERM_D, "THERMAL_ZONE")

    # Heater strip (along bottom of thermal zone)
    add_rect(msp, therm_x + 5, therm_y + 5, THERM_W - 10, 15, "THERMAL_ZONE")
    add_label(msp, therm_x + 6, therm_y + 10, "HEATER", "THERMAL_ZONE", height=3)

    # Fan (circle at exit face end of thermal zone)
    fan_cx = therm_x + THERM_W - 5
    fan_cy = 0
    add_circle(msp, fan_cx, fan_cy, FAN_DIAM / 2, "THERMAL_ZONE")
    add_label(msp, therm_x + 3, 3, "FAN", "THERMAL_ZONE", height=4)

    # STC-1000 thermostat module
    add_rect(msp, therm_x + 5, therm_y + 30, 55, 35, "COMPONENTS")
    add_label(msp, therm_x + 7, therm_y + 40, "STC-1000", "COMPONENTS", height=4)

    # Lead conduit exit
    conduit_cx = therm_x + THERM_W + 5
    add_circle(msp, conduit_cx, 0, CONDUIT_LEADS / 2, "CONDUITS")
    add_label(msp, conduit_cx + CONDUIT_LEADS / 2 + 2, -5,
              "LEADS", "CONDUITS", height=3)

    add_label(msp, -INNER_W / 2 + 5, -INNER_D / 2 - 15,
              f"SHELL 2 INTERIOR  {INNER_W:.0f} x {INNER_D:.0f} mm (plan view)",
              "ANNOTATIONS", height=5)

    filepath = os.path.join(OUTPUT_DIR, "5_zone_layout.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 6: Cell Layout Detail (front elevation)
# ---------------------------------------------------------------------------

def generate_cell_layout_detail():
    """Front elevation of 4S cell stack with polarity, busbars, sense wires.

    X = width axis (4 cells across), Y = height axis.
    Origin at bottom-left of battery zone.
    """
    doc = setup_doc()
    msp = doc.modelspace()

    # Battery zone bounding box
    add_rect(msp, 0, 0, STACK_W, STACK_H, "BATTERY_ZONE")

    PLATE_W = 4.0

    # Compression plates
    add_rect(msp, 0, 5, PLATE_W, CELL_H, "COMPONENTS")
    add_rect(msp, STACK_W - PLATE_W, 5, PLATE_W, CELL_H, "COMPONENTS")
    add_label(msp, 0.5, CELL_H / 2 + 5, "COMP", "COMPONENTS", height=3)

    # Cells with polarity markers
    for col in range(CELLS_S):
        cell_x = PLATE_W + 2 + col * (CELL_W + 2)
        cell_y = 5
        add_rect(msp, cell_x, cell_y, CELL_W, CELL_H, "CELLS")
        polarity = "+" if col % 2 == 0 else "-"
        add_label(msp, cell_x + CELL_W / 2 - 4, cell_y + CELL_H + 2,
                  polarity, "CELLS", height=8)
        add_label(msp, cell_x + 2, cell_y + CELL_H / 2 - 3,
                  f"C{col+1}", "CELLS", height=5)

    # Busbars connecting terminals (3 busbars for 4 cells in series)
    bus_y = 5 + CELL_H + 2
    bus_h = 8
    for col in range(CELLS_S - 1):
        # Busbar connects terminal col to terminal col+1
        b_x1 = PLATE_W + 2 + col * (CELL_W + 2) + CELL_W * 0.4
        b_x2 = PLATE_W + 2 + (col + 1) * (CELL_W + 2) + CELL_W * 0.6
        add_rect(msp, b_x1, bus_y, b_x2 - b_x1, bus_h, "COMPONENTS")

    add_label(msp, STACK_W / 2 - 12, bus_y + bus_h + 3,
              "SERIES BUSBARS", "COMPONENTS", height=3)

    # BMS sense wire taps (at each cell terminal)
    sense_y = bus_y + bus_h + 15
    for col in range(CELLS_S + 1):
        # tap position at each terminal boundary
        if col == 0:
            tap_x = PLATE_W + 2
        elif col == CELLS_S:
            tap_x = PLATE_W + 2 + CELLS_S * (CELL_W + 2) - 2
        else:
            tap_x = PLATE_W + 2 + col * (CELL_W + 2) + CELL_W * 0.5
        add_circle(msp, tap_x, sense_y, 3, "COMPONENTS")
        add_label(msp, tap_x - 4, sense_y + 5, f"B{col}", "COMPONENTS", height=3)

    add_label(msp, 0, sense_y + 15,
              "BMS sense wire tap points (B0=neg, B1-B3=cell junctions, B4=pos)",
              "COMPONENTS", height=3)

    # Positive/negative output terminals
    add_label(msp, PLATE_W + 2, -12, "PACK NEG (to main unit -bus)",
              "BATTERY_ZONE", height=3)
    add_label(msp, STACK_W - 50, -12, "PACK POS (to main unit +bus)",
              "BATTERY_ZONE", height=3)

    # Threaded rod
    rod_y = 5 + CELL_H / 2
    add_circle(msp, PLATE_W / 2, rod_y, 3, "FASTENERS")
    add_circle(msp, STACK_W - PLATE_W / 2, rod_y, 3, "FASTENERS")
    add_label(msp, STACK_W + 3, rod_y - 3, "M8 ROD", "FASTENERS", height=3)

    # Dimensions
    add_label(msp, -5, 5, f"H={CELL_H:.0f}", "DIMENSIONS", height=3)
    add_label(msp, STACK_W / 2 - 25, -22,
              f"W={STACK_W:.0f}mm  (4 x {CELL_W:.0f}mm cells)",
              "DIMENSIONS", height=3)

    add_label(msp, 0, STACK_H + 10,
              f"4S CELL LAYOUT DETAIL — front elevation",
              "ANNOTATIONS", height=5)
    add_label(msp, 0, STACK_H + 22,
              f"MEASURED dims: {CELL_L:.0f}L × {CELL_W:.0f}W × {CELL_H:.0f}H mm + {TERMINAL_H:.0f}mm terminals",
              "ANNOTATIONS", height=4)

    filepath = os.path.join(OUTPUT_DIR, "6_cell_layout_detail.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 7: Cap Rim — Top View
# ---------------------------------------------------------------------------

def generate_cap_top_view():
    doc = setup_doc()
    msp = doc.modelspace()

    add_rect(msp, -CAP_OUTER_W / 2, -CAP_OUTER_D / 2,
             CAP_OUTER_W, CAP_OUTER_D, "CAP")

    # Inner cutout (S2 inner wall)
    s2_inner_w = MID_W - 2 * WALL_S2
    s2_inner_d = MID_D - 2 * WALL_S2
    add_rect(msp, -s2_inner_w / 2, -s2_inner_d / 2, s2_inner_w, s2_inner_d, "CAP")
    add_rect(msp, -OUTER_W / 2, -OUTER_D / 2, OUTER_W, OUTER_D, "SHELL_1")

    # Gasket grooves — sit above the foam gap (between S1 inner and S2 outer)
    outer_gasket_inset = WALL + CAP_GASKET_MARGIN + CAP_GASKET_W / 2
    inner_gasket_inset = WALL + FOAM - CAP_GASKET_MARGIN - CAP_GASKET_W / 2

    og_outer_w = CAP_OUTER_W - 2 * (outer_gasket_inset - CAP_GASKET_W / 2)
    og_outer_d = CAP_OUTER_D - 2 * (outer_gasket_inset - CAP_GASKET_W / 2)
    og_inner_w = og_outer_w - 2 * CAP_GASKET_W
    og_inner_d = og_outer_d - 2 * CAP_GASKET_W
    add_rect(msp, -og_outer_w / 2, -og_outer_d / 2, og_outer_w, og_outer_d, "GASKET")
    add_rect(msp, -og_inner_w / 2, -og_inner_d / 2, og_inner_w, og_inner_d, "GASKET")

    ig_outer_w = CAP_OUTER_W - 2 * (inner_gasket_inset - CAP_GASKET_W / 2)
    ig_outer_d = CAP_OUTER_D - 2 * (inner_gasket_inset - CAP_GASKET_W / 2)
    ig_inner_w = ig_outer_w - 2 * CAP_GASKET_W
    ig_inner_d = ig_outer_d - 2 * CAP_GASKET_W
    add_rect(msp, -ig_outer_w / 2, -ig_outer_d / 2, ig_outer_w, ig_outer_d, "GASKET")
    add_rect(msp, -ig_inner_w / 2, -ig_inner_d / 2, ig_inner_w, ig_inner_d, "GASKET")

    # Bolt holes — between the two gasket grooves
    bolt_inset = (outer_gasket_inset + inner_gasket_inset) / 2
    bolt_loop_w = CAP_OUTER_W - 2 * bolt_inset
    bolt_loop_d = CAP_OUTER_D - 2 * bolt_inset
    bolts = bolt_positions_around_rect(bolt_loop_w, bolt_loop_d,
                                       M4_EDGE_DIST, CAP_BOLT_SPACING)
    for bx, by in bolts:
        add_circle(msp, bx, by, M4_HOLE / 2, "FASTENERS")
        add_circle(msp, bx, by, INSERT_OD / 2, "FASTENERS")

    # Foam anchor teeth — along flange centerline (midway in foam gap)
    # Skip teeth that would conflict with bolt/insert positions
    tooth_inset = WALL + FOAM / 2  # center of foam gap from cap edge
    tooth_loop_w = CAP_OUTER_W - 2 * tooth_inset
    tooth_loop_d = CAP_OUTER_D - 2 * tooth_inset
    teeth = tooth_positions_around_rect(tooth_loop_w, tooth_loop_d,
                                        FOAM_TOOTH_SPACING, FOAM_TOOTH_W,
                                        bolt_positions=bolts)
    for tx, ty, horiz in teeth:
        if horiz:
            add_rect(msp, tx - FOAM_TOOTH_W / 2, ty - FOAM_TOOTH_THICK / 2,
                     FOAM_TOOTH_W, FOAM_TOOTH_THICK, "CAP")
        else:
            add_rect(msp, tx - FOAM_TOOTH_THICK / 2, ty - FOAM_TOOTH_W / 2,
                     FOAM_TOOTH_THICK, FOAM_TOOTH_W, "CAP")

    # Labels
    add_label(msp, CAP_OUTER_W / 2 + 5, 0,
              f"CAP TOP VIEW (flush) {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f}mm",
              "ANNOTATIONS", height=5)
    add_label(msp, og_outer_w / 2 + 5, CAP_OUTER_D / 2 - outer_gasket_inset,
              "OUTER GASKET GROOVE", "GASKET", height=3)
    add_label(msp, ig_outer_w / 2 + 5, CAP_OUTER_D / 2 - inner_gasket_inset,
              "INNER GASKET GROOVE", "GASKET", height=3)
    if bolts:
        bx0, by0 = bolts[0]
        add_label(msp, bx0 + INSERT_OD / 2 + 3, by0,
                  f"M4 + {INSERT_OD:.0f}mm INSERT", "FASTENERS", height=2.5)
    if teeth:
        tx0, ty0, _ = teeth[0]
        add_label(msp, tx0 + FOAM_TOOTH_THICK / 2 + 3, ty0,
                  f"FOAM TOOTH ({FOAM_TOOTH_W:.0f}x{FOAM_TOOTH_THICK:.0f}x{FOAM_TOOTH_D:.0f}mm)",
                  "CAP", height=2.5)

    filepath = os.path.join(OUTPUT_DIR, "7_cap_top_view.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}  ({len(bolts)} bolt holes)")


# ---------------------------------------------------------------------------
# DRAWING 8: Cap Rim — Profile Cross-Section
# ---------------------------------------------------------------------------

def generate_cap_profile():
    """Cap rim + lid profile cross-section (right half, mirrored left)."""
    doc = setup_doc()
    msp = doc.modelspace()

    s1_outer = OUTER_D / 2
    s1_inner = s1_outer - WALL
    s2_outer = MID_D / 2
    s2_inner = s2_outer - WALL_S2

    s2_top = BASE_THICK + FOAM + MID_H

    cap_top = OUTER_H + CAP_THICK
    flange_bottom = OUTER_H - CAP_FOAM_FLANGE
    inner_lip_inner = s2_inner - CAP_INNER_LIP
    inner_lip_bottom = s2_top - CAP_INNER_LIP_DROP  # lip drops below S2 top

    # --- Cap rim profile (right half) ---
    # Flush with S1 outer, spans foam gap, inner lip slips inside S2
    pts = [
        (s1_outer, cap_top),           # cap top, flush with S1 outer
        (s1_outer, OUTER_H),           # sits on S1 wall
        (s1_inner, OUTER_H),           # S1 inner face
        (s1_inner, flange_bottom),     # foam flange drops into gap
        (s2_outer, flange_bottom),     # across foam gap to S2
        (s2_outer, s2_top),            # up S2 outer to S2 top
        (s2_inner, s2_top),            # across S2 wall to inner face
        (s2_inner, inner_lip_bottom),  # inner lip drops inside S2
        (inner_lip_inner, inner_lip_bottom),  # lip inner face
        (inner_lip_inner, cap_top),    # back to cap top
        (s1_outer, cap_top),           # close
    ]
    msp.add_lwpolyline(pts, dxfattribs={"layer": "CAP"})
    # Mirror left
    pts_l = [(-x, y) for x, y in pts]
    msp.add_lwpolyline(pts_l, dxfattribs={"layer": "CAP"})

    # --- Foam anchor teeth (cross-section, on flange underside) ---
    flange_cx = (s1_inner + s2_outer) / 2  # center of foam gap
    tooth_hw = FOAM_TOOTH_THICK / 2
    tooth_bot = flange_bottom - FOAM_TOOTH_D
    for sign in [1, -1]:
        fx = sign * flange_cx
        msp.add_lwpolyline([
            (fx - sign * tooth_hw, flange_bottom),
            (fx - sign * tooth_hw, tooth_bot),
            (fx + sign * tooth_hw, tooth_bot),
            (fx + sign * tooth_hw, flange_bottom),
        ], dxfattribs={"layer": "CAP"})

    # --- Lid profile (sits on top of cap rim) ---
    lid_outer = s1_outer + LID_OVERHANG
    lid_top = cap_top + LID_THICK
    lid_skirt_bottom = cap_top - LID_SKIRT

    lid_pts = [
        (lid_outer, lid_top),
        (lid_outer, lid_skirt_bottom),
        # Drip edge groove on skirt underside
        (lid_outer - LID_DRIP_INSET, lid_skirt_bottom),
        (lid_outer - LID_DRIP_INSET, lid_skirt_bottom + LID_DRIP_DEPTH),
        (lid_outer - LID_DRIP_INSET - LID_DRIP_WIDTH, lid_skirt_bottom + LID_DRIP_DEPTH),
        (lid_outer - LID_DRIP_INSET - LID_DRIP_WIDTH, lid_skirt_bottom),
        # Skirt inner face — seats against S1 outer / cap outer face
        (s1_outer + 1, lid_skirt_bottom),  # 1mm clearance
        (s1_outer + 1, cap_top),
        # Lid bottom rests on cap top
        (inner_lip_inner - 1, cap_top),
        (inner_lip_inner - 1, lid_skirt_bottom),
        # Inner skirt
        (-lid_outer + LID_DRIP_INSET + LID_DRIP_WIDTH, lid_skirt_bottom),
        (-lid_outer + LID_DRIP_INSET + LID_DRIP_WIDTH, lid_skirt_bottom + LID_DRIP_DEPTH),
        (-lid_outer + LID_DRIP_INSET, lid_skirt_bottom + LID_DRIP_DEPTH),
        (-lid_outer + LID_DRIP_INSET, lid_skirt_bottom),
        (-lid_outer, lid_skirt_bottom),
        (-lid_outer, lid_top),
        (lid_outer, lid_top),
    ]
    msp.add_lwpolyline(lid_pts, dxfattribs={"layer": "LID"})

    # --- Gasket grooves (rectangles cut into cap top surface) ---
    # Gaskets sit above the foam gap region (between S1 inner and S2 outer)
    foam_outer_edge = s1_inner   # foam gap starts at S1 inner face
    foam_inner_edge = s2_outer   # foam gap ends at S2 outer face
    outer_gasket_cx = foam_outer_edge + CAP_GASKET_MARGIN + CAP_GASKET_W / 2
    inner_gasket_cx = foam_inner_edge - CAP_GASKET_MARGIN - CAP_GASKET_W / 2

    for gx in [outer_gasket_cx, inner_gasket_cx, -outer_gasket_cx, -inner_gasket_cx]:
        # Groove: CAP_GASKET_W wide × CAP_GASKET_D deep, cut down from cap top
        g_left = gx - CAP_GASKET_W / 2
        g_right = gx + CAP_GASKET_W / 2
        g_top = cap_top
        g_bottom = cap_top - CAP_GASKET_D
        msp.add_lwpolyline([
            (g_left, g_top), (g_left, g_bottom),
            (g_right, g_bottom), (g_right, g_top),
        ], dxfattribs={"layer": "GASKET"})

    # --- Bolt through-hole + insert pocket (cross-section) ---
    bolt_x = (outer_gasket_cx + inner_gasket_cx) / 2
    for bx in [bolt_x, -bolt_x]:
        # M4 through-hole (full cap thickness)
        hw = M4_HOLE / 2
        msp.add_line((bx - hw, cap_top), (bx - hw, OUTER_H),
                     dxfattribs={"layer": "FASTENERS"})
        msp.add_line((bx + hw, cap_top), (bx + hw, OUTER_H),
                     dxfattribs={"layer": "FASTENERS"})

        # Insert pocket (counterbore from underside)
        ihw = INSERT_OD / 2
        pocket_top = OUTER_H + INSERT_DEPTH  # pocket starts INSERT_DEPTH up from cap bottom
        msp.add_lwpolyline([
            (bx - ihw, OUTER_H), (bx - ihw, pocket_top),
            (bx + ihw, pocket_top), (bx + ihw, OUTER_H),
        ], dxfattribs={"layer": "FASTENERS"})

    # Reference shell top sections
    wall_show_h = 40
    for outer, inner, label in [
        (s1_outer, s1_inner, "SHELL_1"),
        (s2_outer, s2_inner, "SHELL_2"),
    ]:
        for sign in [1, -1]:
            msp.add_lwpolyline([
                (sign * outer, OUTER_H), (sign * outer, OUTER_H - wall_show_h),
                (sign * inner, OUTER_H - wall_show_h), (sign * inner, OUTER_H),
            ], dxfattribs={"layer": label})

    # Labels for main drawing
    add_label(msp, s1_outer + 5, cap_top - 4, "CAP RIM (flush)", "CAP", height=3)
    add_label(msp, lid_outer + 5, lid_top - LID_THICK / 2,
              f"LID {LID_THICK:.0f}mm (infill=insulation)", "LID", height=3)
    add_label(msp, lid_outer + 5, lid_skirt_bottom + 3,
              f"SKIRT {LID_SKIRT:.0f}mm + drip edge", "LID", height=3)
    # Foam tooth label
    add_label(msp, flange_cx + tooth_hw + 3, tooth_bot + FOAM_TOOTH_D / 2,
              f"FOAM TEETH {FOAM_TOOTH_D:.0f}mm", "CAP", height=2.5)
    add_label(msp, outer_gasket_cx + 3, cap_top + 5,
              f"GASKET GROOVE {CAP_GASKET_W:.0f}x{CAP_GASKET_D:.1f}mm", "GASKET", height=2.5)

    # ===================================================================
    # ZOOMED DETAIL — Bolt + Insert Pocket Cross-Section
    # ===================================================================
    detail_cx = s1_outer + 120
    detail_base_y = OUTER_H
    detail_scale = 8.0

    add_label(msp, detail_cx - 35, detail_base_y + CAP_THICK * detail_scale + 20,
              "DETAIL: BOLT + INSERT POCKET", "FASTENERS", height=3.5)
    add_label(msp, detail_cx - 35, detail_base_y + CAP_THICK * detail_scale + 14,
              "(Section through single bolt hole, 8x scale)", "ANNOTATIONS", height=2.5)

    # Cap body block (zoomed)
    cap_w_detail = 20.0 * detail_scale
    cap_h_detail = CAP_THICK * detail_scale
    cx_left = detail_cx - cap_w_detail / 2
    cx_right = detail_cx + cap_w_detail / 2
    cy_bottom = detail_base_y
    cy_top = detail_base_y + cap_h_detail

    msp.add_lwpolyline([
        (cx_left, cy_bottom), (cx_right, cy_bottom),
        (cx_right, cy_top), (cx_left, cy_top),
    ], close=True, dxfattribs={"layer": "CAP"})

    # Gasket groove in detail
    gg_cx = detail_cx - 6 * detail_scale
    gg_hw = (CAP_GASKET_W / 2) * detail_scale
    gg_depth = CAP_GASKET_D * detail_scale
    msp.add_lwpolyline([
        (gg_cx - gg_hw, cy_top), (gg_cx - gg_hw, cy_top - gg_depth),
        (gg_cx + gg_hw, cy_top - gg_depth), (gg_cx + gg_hw, cy_top),
    ], dxfattribs={"layer": "GASKET"})
    add_label(msp, gg_cx - gg_hw - 2, cy_top - gg_depth / 2,
              f"{CAP_GASKET_D:.1f}", "GASKET", height=2)
    add_label(msp, gg_cx, cy_top + 4,
              f"{CAP_GASKET_W:.0f}mm groove", "GASKET", height=2)

    # M4 bolt through-hole in detail
    bolt_hw = (M4_HOLE / 2) * detail_scale
    msp.add_lwpolyline([
        (detail_cx - bolt_hw, cy_top), (detail_cx - bolt_hw, cy_bottom),
        (detail_cx + bolt_hw, cy_bottom), (detail_cx + bolt_hw, cy_top),
    ], dxfattribs={"layer": "FASTENERS"})

    # Bolt centerline (dashed ticks)
    for tick_y in range(int(cy_bottom), int(cy_top), 3):
        msp.add_line((detail_cx, tick_y), (detail_cx, tick_y + 1.5),
                     dxfattribs={"layer": "ANNOTATIONS"})

    # Bolt head
    head_hw = 3.5 * detail_scale
    head_h = 2.8 * detail_scale
    msp.add_lwpolyline([
        (detail_cx - head_hw, cy_top),
        (detail_cx - head_hw, cy_top + head_h),
        (detail_cx + head_hw, cy_top + head_h),
        (detail_cx + head_hw, cy_top),
    ], close=True, dxfattribs={"layer": "FASTENERS"})

    # Insert pocket in detail
    ins_hw = (INSERT_OD / 2) * detail_scale
    ins_depth = INSERT_DEPTH * detail_scale
    pocket_top_z = cy_bottom + ins_depth

    msp.add_lwpolyline([
        (detail_cx - ins_hw, cy_bottom), (detail_cx - ins_hw, pocket_top_z),
        (detail_cx - bolt_hw, pocket_top_z), (detail_cx - bolt_hw, cy_bottom),
    ], dxfattribs={"layer": "FASTENERS"})
    msp.add_lwpolyline([
        (detail_cx + bolt_hw, cy_bottom), (detail_cx + bolt_hw, pocket_top_z),
        (detail_cx + ins_hw, pocket_top_z), (detail_cx + ins_hw, cy_bottom),
    ], dxfattribs={"layer": "FASTENERS"})

    # Brass insert hatching
    for hatch_y_off in range(2, int(INSERT_DEPTH * detail_scale), 4):
        hy = cy_bottom + hatch_y_off
        msp.add_line((detail_cx - ins_hw + 1, hy),
                     (detail_cx - bolt_hw - 1, hy),
                     dxfattribs={"layer": "FASTENERS"})
        msp.add_line((detail_cx + bolt_hw + 1, hy),
                     (detail_cx + ins_hw - 1, hy),
                     dxfattribs={"layer": "FASTENERS"})

    # Dimension annotations
    dim_x_right = detail_cx + cap_w_detail / 2 + 8
    msp.add_line((dim_x_right, cy_bottom), (dim_x_right + 15, cy_bottom),
                 dxfattribs={"layer": "ANNOTATIONS"})
    msp.add_line((dim_x_right, cy_top), (dim_x_right + 15, cy_top),
                 dxfattribs={"layer": "ANNOTATIONS"})
    msp.add_line((dim_x_right + 10, cy_bottom), (dim_x_right + 10, cy_top),
                 dxfattribs={"layer": "ANNOTATIONS"})
    add_label(msp, dim_x_right + 14, (cy_bottom + cy_top) / 2,
              f"{CAP_THICK:.0f}mm cap", "ANNOTATIONS", height=2.5)

    dim_x_left = detail_cx - cap_w_detail / 2 - 8
    msp.add_line((dim_x_left, cy_bottom), (dim_x_left - 15, cy_bottom),
                 dxfattribs={"layer": "ANNOTATIONS"})
    msp.add_line((dim_x_left, pocket_top_z), (dim_x_left - 15, pocket_top_z),
                 dxfattribs={"layer": "ANNOTATIONS"})
    msp.add_line((dim_x_left - 10, cy_bottom), (dim_x_left - 10, pocket_top_z),
                 dxfattribs={"layer": "ANNOTATIONS"})
    add_label(msp, dim_x_left - 45, (cy_bottom + pocket_top_z) / 2,
              f"{INSERT_DEPTH:.0f}mm pocket", "ANNOTATIONS", height=2.5)

    add_label(msp, detail_cx + bolt_hw + 3, (cy_top + cy_bottom) / 2 + 8,
              f"{M4_HOLE:.1f}mm thru", "FASTENERS", height=2)
    add_label(msp, detail_cx + ins_hw + 3, cy_bottom + ins_depth / 2,
              f"{INSERT_OD:.0f}mm ins OD", "FASTENERS", height=2)

    add_label(msp, detail_cx - cap_w_detail / 2, cy_bottom - 6,
              "CAP UNDERSIDE (faces shell)", "ANNOTATIONS", height=2)
    add_label(msp, detail_cx - cap_w_detail / 2, cy_top + head_h + 5,
              "CAP TOP (faces lid + weather)", "ANNOTATIONS", height=2)
    add_label(msp, detail_cx + ins_hw + 3, cy_bottom + 3,
              "BRASS INSERT", "FASTENERS", height=2)
    add_label(msp, detail_cx + head_hw + 3, cy_top + head_h / 2,
              "M4 BOLT HEAD", "FASTENERS", height=2)

    # Leader line from main drawing
    msp.add_line((bolt_x, cap_top + 3),
                 (detail_cx - cap_w_detail / 2 - 5, cy_top + cap_h_detail / 2),
                 dxfattribs={"layer": "ANNOTATIONS"})

    filepath = os.path.join(OUTPUT_DIR, "8_cap_profile.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 9: Lid — Top View
# ---------------------------------------------------------------------------

def generate_lid_top_view():
    """Lid top view showing outline, bolt through-holes, and drip edge."""
    doc = setup_doc()
    msp = doc.modelspace()

    # Lid outline
    add_rect(msp, -LID_W / 2, -LID_D / 2, LID_W, LID_D, "LID")

    # Cap rim outline (reference)
    add_rect(msp, -CAP_OUTER_W / 2, -CAP_OUTER_D / 2,
             CAP_OUTER_W, CAP_OUTER_D, "CAP")

    # Shell 1 top (reference)
    add_rect(msp, -OUTER_W / 2, -OUTER_D / 2, OUTER_W, OUTER_D, "SHELL_1")

    # Bolt through-holes (same pattern as cap)
    foam_start = CAP_LIP + WALL
    og_inner_edge = foam_start + CAP_GASKET_MARGIN + CAP_GASKET_W
    ig_outer_edge = foam_start + FOAM - CAP_GASKET_MARGIN - CAP_GASKET_W - 8
    bolt_inset = (og_inner_edge + ig_outer_edge) / 2 - M4_EDGE_DIST
    bolt_loop_w = CAP_OUTER_W - 2 * bolt_inset
    bolt_loop_d = CAP_OUTER_D - 2 * bolt_inset
    bolts = bolt_positions_around_rect(bolt_loop_w, bolt_loop_d,
                                       M4_EDGE_DIST, CAP_BOLT_SPACING)
    for bx, by in bolts:
        add_circle(msp, bx, by, M4_HOLE / 2, "FASTENERS")

    # Labels
    add_label(msp, -LID_W / 2 + 5, LID_D / 2 + 5,
              f"LID  {LID_W:.0f} x {LID_D:.0f} x {LID_THICK:.0f}mm"
              f"  (print at 20% infill for insulation)", "ANNOTATIONS", height=5)
    add_label(msp, -LID_W / 2 + 5, LID_D / 2 + 15,
              f"Skirt: {LID_SKIRT:.0f}mm, drip edge, {len(bolts)} bolt holes",
              "ANNOTATIONS", height=4)
    add_label(msp, -LID_W / 2 + 5, -LID_D / 2 - 10,
              f"Fillet outer edges R={FILLET_OUTER:.0f}, chamfer top edges {CHAMFER_LID:.0f}mm",
              "ANNOTATIONS", height=3)

    filepath = os.path.join(OUTPUT_DIR, "9_lid_top_view.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}  ({len(bolts)} bolt holes)")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating Satellite Unit DXF drawings (Rev 3.2)...")
    print(f"Output: {OUTPUT_DIR}")
    print()
    print("Cell (Narada 105Ah MEASURED):")
    print(f"  {CELL_L:.0f}L x {CELL_W:.0f}W x {CELL_H:.0f}H mm + {TERMINAL_H:.0f}mm terminals")
    print()
    print("Battery zone (4S single string = 4 cells):")
    print(f"  {STACK_W:.0f} x {STACK_D:.0f} x {STACK_H:.0f} mm")
    print()
    print("Thermal zone:")
    print(f"  {THERM_W:.0f} x {THERM_D:.0f} x {THERM_H:.0f} mm")
    print()
    print("Derived enclosure dimensions:")
    print(f"  Shell 2 (PETG struct):   {MID_W:.0f} x {MID_D:.0f} x {MID_H:.0f} mm  (wall={WALL_S2:.0f}mm)")
    print(f"  Shell 1 (ASA outer):     {OUTER_W:.0f} x {OUTER_D:.0f} x {OUTER_H:.0f} mm  (wall={WALL:.0f}mm)")
    print(f"  Foam-pressure ribs:      {RIB_W:.0f}W x {RIB_H:.0f}H mm, spacing {RIB_SPACING:.0f}mm")
    print(f"  Cap rim:                 {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f} x {CAP_THICK:.0f} mm")
    print(f"  Lid:                     {LID_W:.0f} x {LID_D:.0f} x {LID_THICK:.0f} mm")
    print()

    generate_top_view()
    generate_cross_section_front()
    generate_cross_section_side()
    generate_lead_exit_view()
    generate_zone_layout()
    generate_cell_layout_detail()
    generate_cap_top_view()
    generate_cap_profile()
    generate_lid_top_view()

    print()
    print("Done. Import DXFs via Fusion: Insert > Insert DXF")


if __name__ == "__main__":
    main()
