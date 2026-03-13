#!/usr/bin/env python3
"""
Generate DXF enclosure drawings for the Main Unit (Rev 3.2).

The main unit houses:
  - 4S2P cell bank (8× Narada 105Ah LiFePO4)
  - 4× EPever Tracer 2210AN MPPT controllers
  - 2× 4S 100A Smart BMS
  - LEM HASS current sensor, distribution bus, fuses
  - Active thermal management

Produces 2D profile drawings importable into Autodesk Fusion as sketches.
All dimensions in millimeters.

Usage:
    python cad/main_unit/generate_dxf.py

Output:
    cad/main_unit/dxf/1_top_view.dxf
    cad/main_unit/dxf/2_cross_section_front.dxf
    cad/main_unit/dxf/3_cross_section_side.dxf
    cad/main_unit/dxf/4_rear_view.dxf
    cad/main_unit/dxf/5_zone_layout.dxf
    cad/main_unit/dxf/6_battery_zone_detail.dxf
    cad/main_unit/dxf/7_cap_top_view.dxf
    cad/main_unit/dxf/8_cap_profile.dxf
    cad/main_unit/dxf/9_lid_top_view.dxf
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

# Battery zone — 4S2P = 8 cells
# Cells arranged 4-wide (series) × 2-deep (parallel)
CELLS_S = 4      # cells in series
CELLS_P = 2      # parallel strings

STACK_W = CELLS_S * CELL_W + (CELLS_S - 1) * 2 + 8   # 4×62 + gaps + compression = 262 → 265
STACK_D = CELLS_P * CELL_L + (CELLS_P - 1) * 10       # 2×175 + gap = 360
STACK_H = CELL_H + TERMINAL_H + 30.0                    # cells + terminals + busbars + clearance

# Electronics zone
# Contains: 4× EPever 2210AN MPPT, 2× Smart BMS, bus bars, fuses, sensor
EPEVER_W = 186.0    # EPever 2210AN width
EPEVER_H = 76.0     # EPever 2210AN height (mount vertically, face forward)
EPEVER_D = 47.0     # EPever 2210AN depth

# MPPT 2×2 grid on mounting panel
MPPT_PANEL_W = 2 * EPEVER_W + 20.0    # two columns + center gap = 392
MPPT_PANEL_H = 2 * EPEVER_H + 30.0    # two rows + gap = 182

BMS_W = 175.0    # approximate Smart BMS module width
BMS_H = 80.0     # approximate Smart BMS module height
BMS_D = 25.0     # approximate Smart BMS module depth

# Electronics zone totals
ELEC_ZONE_W = MPPT_PANEL_W + 30.0   # MPPT panel + BMS/bus beside it = 422 → use 320+
ELEC_ZONE_W = 320.0                  # rounded: MPPT + BMS + bus + fuses + wiring
ELEC_ZONE_D = STACK_D                # match battery depth
ELEC_ZONE_H = max(MPPT_PANEL_H + BMS_H + 50, STACK_H)   # match cell stack or MPPT/BMS layout

# Thermal zone (fan + heater strip + thermostat) — shares electronics zone
# Mounted in upper corner of electronics zone; not a separate physical zone

# Shell wall thickness (Shell 1: ASA, Shell 2: PETG)
WALL = 5.0       # Shell 1 wall thickness
WALL_S2 = 5.0    # Shell 2 wall thickness

# Foam-pressure ribs (protrude into foam cavity from Shell 1 inner / Shell 2 outer)
RIB_W = 3.0          # rib width (along wall surface)
RIB_H = 10.0         # rib height (protrusion into foam cavity)
RIB_SPACING = 100.0   # center-to-center spacing around perimeter

# Foam cavity between Shell 1 (outer) and Shell 2 (middle)
FOAM = 30.0

# Fasteners
M4_HOLE = 4.5
M4_EDGE_DIST = 10.0

# Conduits (inner diameters)
CONDUIT_SOLAR = 14.0    # MC4 solar pair (4× channels)
CONDUIT_SAT = 16.0      # satellite unit leads (4× future)
CONDUIT_PUMP = 10.0     # 12V pump output (3× Solariver)
CONDUIT_PROBE = 8.0     # thermostat probe / comms

# Spacing / margins
ZONE_GAP = 20.0         # gap between battery and electronics zones
ZONE_MARGIN = 10.0      # margin between zone contents and inner shell wall
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
CAP_BOLT_SPACING = 90.0
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

# ---------------------------------------------------------------------------
# DERIVED DIMENSIONS
# ---------------------------------------------------------------------------

# Interior component space (Shell 2 wraps directly around this)
INNER_W = 2 * ZONE_MARGIN + STACK_W + ZONE_GAP + ELEC_ZONE_W
INNER_D = max(STACK_D, ELEC_ZONE_D) + 2 * ZONE_MARGIN
INNER_H = max(STACK_H, ELEC_ZONE_H) + BASE_THICK

# Structural shell (Shell 2) — wraps directly around component space
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
CAP_INNER_W = MID_W - 2 * (WALL_S2 + CAP_INNER_LIP)
CAP_INNER_D = MID_D - 2 * (WALL_S2 + CAP_INNER_LIP)

# Lid
LID_W = CAP_OUTER_W + 2 * LID_OVERHANG
LID_D = CAP_OUTER_D + 2 * LID_OVERHANG

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dxf")

# ---------------------------------------------------------------------------
# LAYER DEFINITIONS
# ---------------------------------------------------------------------------

LAYERS = {
    "SHELL_1":     {"color": 1},    # red   — ASA outer
    "SHELL_2":     {"color": 3},    # green — PETG structural
    "FOAM_CAVITY": {"color": 40},   # orange
    "BATTERY_ZONE":{"color": 2},    # yellow
    "ELEC_ZONE":   {"color": 4},    # cyan
    "CELLS":       {"color": 6},    # magenta
    "COMPONENTS":  {"color": 30},   # orange-brown
    "CONDUITS":    {"color": 4},    # cyan
    "DIMENSIONS":  {"color": 7},    # white
    "FASTENERS":   {"color": 2},    # yellow
    "ANNOTATIONS": {"color": 7},    # white
    "CAP":         {"color": 30},   # orange-brown
    "LID":         {"color": 6},    # magenta
    "GASKET":      {"color": 8},    # gray
    "THERMAL":     {"color": 10},   # red-orange
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
    """Place bolts around the perimeter of a rectangle.
    Bolts sit ON the rectangle edges (not inset from them).
    edge_dist controls how far from corners the first/last bolt is
    placed ALONG each edge."""
    positions = []
    hw = outer_w / 2
    hd = outer_d / 2
    # Top/bottom edges: bolts at y = ±hd, x spaced along edge
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

    # Shell 1 outer
    add_rect(msp, -OUTER_W / 2, -OUTER_D / 2, OUTER_W, OUTER_D, "SHELL_1")
    # Shell 2
    add_rect(msp, -MID_W / 2, -MID_D / 2, MID_W, MID_D, "SHELL_2")

    # Zone outlines inside Shell 2 (for orientation)
    # Battery zone (left half)
    batt_x = -INNER_W / 2 + ZONE_MARGIN
    batt_y = -STACK_D / 2
    add_rect(msp, batt_x, batt_y, STACK_W, STACK_D, "BATTERY_ZONE")
    add_label(msp, batt_x + 5, batt_y + 5, "BATT ZONE", "BATTERY_ZONE", height=5)

    # Electronics zone (right half)
    elec_x = batt_x + STACK_W + ZONE_GAP
    elec_y = -ELEC_ZONE_D / 2
    add_rect(msp, elec_x, elec_y, ELEC_ZONE_W, ELEC_ZONE_D, "ELEC_ZONE")
    add_label(msp, elec_x + 5, elec_y + 5, "ELEC ZONE", "ELEC_ZONE", height=5)

    # Dimension annotations
    add_label(msp, OUTER_W / 2 + 5, 0, f"OUTER W={OUTER_W:.0f}", height=4)
    add_label(msp, 0, OUTER_D / 2 + 5, f"OUTER D={OUTER_D:.0f}", height=4)

    filepath = os.path.join(OUTPUT_DIR, "1_top_view.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 2: Front Cross-Section
# ---------------------------------------------------------------------------

def generate_cross_section_front():
    """Front cross-section — nested shells + foam + zone heights."""
    doc = setup_doc()
    msp = doc.modelspace()

    # Shell 1
    add_rect(msp, -OUTER_W / 2, 0, OUTER_W, OUTER_H, "SHELL_1")

    # Foam cavity
    add_rect(msp, -OUTER_W / 2 + WALL, BASE_THICK,
             OUTER_W - 2 * WALL, OUTER_H - WALL - BASE_THICK, "FOAM_CAVITY")

    # Shell 2
    s2_x = -MID_W / 2
    s2_y = BASE_THICK + FOAM
    add_rect(msp, s2_x, s2_y, MID_W, MID_H, "SHELL_2")

    # Battery zone (left portion of Shell 2 interior)
    batt_x = s2_x + WALL_S2 + ZONE_MARGIN
    batt_y = s2_y + WALL_S2
    add_rect(msp, batt_x, batt_y, STACK_W, STACK_H, "BATTERY_ZONE")
    add_label(msp, batt_x + 2, batt_y + STACK_H / 2, "BATTERY", "BATTERY_ZONE", height=4)

    # Electronics zone (right portion)
    elec_x = batt_x + STACK_W + ZONE_GAP
    elec_y = s2_y + WALL_S2
    add_rect(msp, elec_x, elec_y, ELEC_ZONE_W, ELEC_ZONE_H, "ELEC_ZONE")
    add_label(msp, elec_x + 2, elec_y + ELEC_ZONE_H / 2, "ELEC", "ELEC_ZONE", height=4)

    # --- Foam-pressure ribs (front cross-section: left & right walls) ---
    # Calculate rib count based on available wall height in foam cavity
    foam_base_y = BASE_THICK
    foam_top_y = OUTER_H - WALL
    foam_height = foam_top_y - foam_base_y
    rib_start = 50.0  # first rib ~50mm from base
    num_ribs = max(1, int((foam_height - rib_start) / RIB_SPACING) + 1)

    # Shell 1 inner surface x-positions
    s1_inner_left = -OUTER_W / 2 + WALL
    s1_inner_right = OUTER_W / 2 - WALL

    # Shell 2 outer surface x-positions
    s2_outer_left = -MID_W / 2
    s2_outer_right = MID_W / 2

    for i in range(num_ribs):
        rib_y = foam_base_y + rib_start + i * RIB_SPACING
        if rib_y + RIB_W > foam_top_y:
            break

        # Shell 1 left inner wall ribs (pointing right, into foam)
        add_rect(msp, s1_inner_left, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")
        # Shell 1 right inner wall ribs (pointing left, into foam)
        add_rect(msp, s1_inner_right - RIB_H, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")

        # Shell 2 left outer wall ribs (pointing left, into foam)
        add_rect(msp, s2_outer_left - RIB_H, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")
        # Shell 2 right outer wall ribs (pointing right, into foam)
        add_rect(msp, s2_outer_right, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")

    add_label(msp, s1_inner_left + 1, foam_base_y + rib_start - 6,
              "RIBS", "FOAM_CAVITY", height=3)

    # Cap rim (full profile showing flanges spanning both shells)
    cap_y = OUTER_H
    s1o_w = OUTER_W / 2
    s1i_w = s1o_w - WALL
    s2o_w = MID_W / 2
    s2i_w = s2o_w - WALL_S2
    cap_top_y = cap_y + CAP_THICK
    flange_bot_y = cap_y - CAP_FOAM_FLANGE
    s2_top_y = BASE_THICK + FOAM + MID_H
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

    # Dimension labels
    add_label(msp, OUTER_W / 2 + 5, OUTER_H / 2,
              f"H={OUTER_H:.0f}", "DIMENSIONS", height=4)
    add_label(msp, -OUTER_W / 2 - 35, OUTER_H / 2,
              f"W={OUTER_W:.0f}", "DIMENSIONS", height=4)

    filepath = os.path.join(OUTPUT_DIR, "2_cross_section_front.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 3: Side Cross-Section
# ---------------------------------------------------------------------------

def generate_cross_section_side():
    """Side cross-section — depth view."""
    doc = setup_doc()
    msp = doc.modelspace()

    # Shell 1
    add_rect(msp, -OUTER_D / 2, 0, OUTER_D, OUTER_H, "SHELL_1")

    # Foam
    add_rect(msp, -OUTER_D / 2 + WALL, BASE_THICK,
             OUTER_D - 2 * WALL, OUTER_H - WALL - BASE_THICK, "FOAM_CAVITY")

    # Shell 2
    s2_x = -MID_D / 2
    s2_y = BASE_THICK + FOAM
    add_rect(msp, s2_x, s2_y, MID_D, MID_H, "SHELL_2")

    # Battery zone depth indicator
    batt_y = s2_y + WALL_S2
    add_rect(msp, -STACK_D / 2, batt_y, STACK_D, STACK_H, "BATTERY_ZONE")

    # --- Foam-pressure ribs (side cross-section: left & right walls along depth) ---
    foam_base_y_side = BASE_THICK
    foam_top_y_side = OUTER_H - WALL
    foam_height_side = foam_top_y_side - foam_base_y_side
    rib_start_side = 50.0
    num_ribs_side = max(1, int((foam_height_side - rib_start_side) / RIB_SPACING) + 1)

    s1_inner_left_d = -OUTER_D / 2 + WALL
    s1_inner_right_d = OUTER_D / 2 - WALL
    s2_outer_left_d = -MID_D / 2
    s2_outer_right_d = MID_D / 2

    for i in range(num_ribs_side):
        rib_y = foam_base_y_side + rib_start_side + i * RIB_SPACING
        if rib_y + RIB_W > foam_top_y_side:
            break

        # Shell 1 left inner wall ribs (pointing right, into foam)
        add_rect(msp, s1_inner_left_d, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")
        # Shell 1 right inner wall ribs (pointing left, into foam)
        add_rect(msp, s1_inner_right_d - RIB_H, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")

        # Shell 2 left outer wall ribs (pointing left, into foam)
        add_rect(msp, s2_outer_left_d - RIB_H, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")
        # Shell 2 right outer wall ribs (pointing right, into foam)
        add_rect(msp, s2_outer_right_d, rib_y, RIB_H, RIB_W, "FOAM_CAVITY")

    add_label(msp, s1_inner_left_d + 1, foam_base_y_side + rib_start_side - 6,
              "RIBS", "FOAM_CAVITY", height=3)

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

    # Labels
    add_label(msp, OUTER_D / 2 + 5, OUTER_H / 2,
              f"D={OUTER_D:.0f}", "DIMENSIONS", height=4)
    add_label(msp, -OUTER_D / 2 - 5, STACK_H / 2 + BASE_THICK + FOAM + WALL + 5,
              f"BATT D={STACK_D:.0f}", "BATTERY_ZONE", height=3)

    filepath = os.path.join(OUTPUT_DIR, "3_cross_section_side.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 4: Rear View — Conduit Penetrations
# ---------------------------------------------------------------------------

def generate_rear_view():
    """Rear face showing conduit holes.

    Conduits penetrate the rear face of the outer shell.
    X = horizontal (centered on outer shell width), Y = height (Z axis).
    """
    doc = setup_doc()
    msp = doc.modelspace()

    # Outer shell rear face
    add_rect(msp, -OUTER_W / 2, 0, OUTER_W, OUTER_H, "SHELL_1")

    # --- Conduit layout: top of enclosure, single organized row ---
    # Top row Y — near top, below cap rim area
    top_row_y = OUTER_H - 40           # main conduit row
    second_row_y = top_row_y - 35      # pump row (below MC4s)

    # Horizontal spacing: SAT1-4 on left, MC4-1 to MC4-4 continuing right
    # Start from left edge with margin, evenly space all 8 top-row conduits
    left_margin = 50
    spacing = (OUTER_W - 2 * left_margin) / 8  # ~62mm between centers
    start_x = -OUTER_W / 2 + left_margin + spacing / 2

    # Satellite lead conduits (4×) — left side of top row
    for i in range(4):
        cx = start_x + i * spacing
        add_circle(msp, cx, top_row_y, CONDUIT_SAT / 2, "CONDUITS")
        add_label(msp, cx - 8, top_row_y + CONDUIT_SAT / 2 + 3,
                  f"SAT{i+1}", "CONDUITS", height=3)

    # Solar MC4 conduits (4×) — right side of top row
    for i in range(4):
        cx = start_x + (4 + i) * spacing
        add_circle(msp, cx, top_row_y, CONDUIT_SOLAR / 2, "CONDUITS")
        add_label(msp, cx - 10, top_row_y + CONDUIT_SOLAR / 2 + 3,
                  f"MC4-{i+1}", "CONDUITS", height=3)

    # Pump output conduits (3×) — second row, centered under MC4s
    pump_center_x = start_x + 5 * spacing  # centered under MC4-2/MC4-3
    for i in range(3):
        cx = pump_center_x + (i - 1) * 35
        add_circle(msp, cx, second_row_y, CONDUIT_PUMP / 2, "CONDUITS")
        add_label(msp, cx - 4, second_row_y + CONDUIT_PUMP / 2 + 3,
                  f"P{i+1}", "CONDUITS", height=3)

    # Probe / comms conduit — far right of second row
    probe_x = start_x + 7 * spacing
    add_circle(msp, probe_x, second_row_y, CONDUIT_PROBE / 2, "CONDUITS")
    add_label(msp, probe_x - 8, second_row_y + CONDUIT_PROBE / 2 + 3,
              "PROBE", "CONDUITS", height=3)

    add_label(msp, -OUTER_W / 2 + 5, 5,
              f"REAR FACE  {OUTER_W:.0f} x {OUTER_H:.0f} mm", "ANNOTATIONS", height=5)

    filepath = os.path.join(OUTPUT_DIR, "4_rear_view.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 5: Interior Zone Layout (top-down with component blocks)
# ---------------------------------------------------------------------------

def generate_zone_layout():
    """Interior top-down layout showing component positions within Shell 2.

    Origin at center of inner shell.
    """
    doc = setup_doc()
    msp = doc.modelspace()

    # Shell 2 outline
    add_rect(msp, -MID_W / 2, -MID_D / 2, MID_W, MID_D, "SHELL_2")

    # Battery zone
    batt_x = -INNER_W / 2 + ZONE_MARGIN
    batt_y = -STACK_D / 2
    add_rect(msp, batt_x, batt_y, STACK_W, STACK_D, "BATTERY_ZONE")

    # Individual cells (footprint: CELL_W × CELL_L each)
    for row in range(CELLS_P):
        for col in range(CELLS_S):
            cx = batt_x + 4 + col * (CELL_W + 2)   # 4mm compression plate
            cy = batt_y + row * (CELL_L + 10) + 5
            add_rect(msp, cx, cy, CELL_W, CELL_L, "CELLS")
            add_label(msp, cx + 2, cy + CELL_L / 2 - 3,
                      f"C{row * CELLS_S + col + 1}", "CELLS", height=4)

    add_label(msp, batt_x + 2, -STACK_D / 2 + STACK_D + 5,
              f"4S2P ({CELLS_S}S x {CELLS_P}P)", "BATTERY_ZONE", height=5)

    # Electronics zone
    elec_x = batt_x + STACK_W + ZONE_GAP
    elec_y = -ELEC_ZONE_D / 2

    # MPPT 2×2 grid (footprint: EPEVER_D × EPEVER_W)
    for row in range(2):
        for col in range(2):
            mx = elec_x + 10 + col * (EPEVER_D + 10)
            my = elec_y + 10 + row * (EPEVER_W + 10)
            add_rect(msp, mx, my, EPEVER_D, EPEVER_W, "ELEC_ZONE")
            add_label(msp, mx + 2, my + EPEVER_W / 2 - 3,
                      f"MPPT{row * 2 + col + 1}", "ELEC_ZONE", height=4)

    # BMS units (2×)
    bms_x = elec_x + 10 + 2 * (EPEVER_D + 10) + 10
    for i in range(2):
        by = elec_y + 10 + i * (BMS_D + 15)
        add_rect(msp, bms_x, by, BMS_W, BMS_D, "COMPONENTS")
        add_label(msp, bms_x + 2, by + BMS_D / 2 - 3, f"BMS{i+1}", "COMPONENTS", height=4)

    # Distribution bus bar
    bus_x = bms_x + BMS_W + 10
    add_rect(msp, bus_x, elec_y + 10, 30, ELEC_ZONE_D - 20, "COMPONENTS")
    add_label(msp, bus_x + 2, elec_y + ELEC_ZONE_D / 2, "BUS", "COMPONENTS", height=4)

    # Thermal zone (fan side — upper corner of electronics zone)
    therm_x = elec_x
    therm_y = elec_y + ELEC_ZONE_D - 120
    add_rect(msp, therm_x, therm_y, 100, 110, "THERMAL")
    add_label(msp, therm_x + 5, therm_y + 55, "THERMAL", "THERMAL", height=4)

    add_label(msp, -MID_W / 2 + 5, -MID_D / 2 - 15,
              f"SHELL 2 INTERIOR  {INNER_W:.0f} x {INNER_D:.0f} mm (plan view)",
              "ANNOTATIONS", height=5)

    filepath = os.path.join(OUTPUT_DIR, "5_zone_layout.dxf")
    doc.saveas(filepath)
    print(f"  Created: {filepath}")


# ---------------------------------------------------------------------------
# DRAWING 6: Battery Zone Detail (front elevation of cell stack)
# ---------------------------------------------------------------------------

def generate_battery_zone_detail():
    """Front elevation of the battery zone showing cell arrangement.

    X = width axis (4 cells side by side), Y = height axis.
    Origin at bottom-left of battery zone interior.
    """
    doc = setup_doc()
    msp = doc.modelspace()

    # Battery zone bounding box
    add_rect(msp, 0, 0, STACK_W, STACK_H, "BATTERY_ZONE")

    # Compression plates at each end
    PLATE_W = 4.0
    PLATE_H = CELL_H
    add_rect(msp, 0, 5, PLATE_W, PLATE_H, "COMPONENTS")
    add_rect(msp, STACK_W - PLATE_W, 5, PLATE_W, PLATE_H, "COMPONENTS")
    add_label(msp, 1, PLATE_H / 2 + 5, "COMP", "COMPONENTS", height=3)

    # Cells (front row — parallel string A shown)
    for col in range(CELLS_S):
        cell_x = PLATE_W + 2 + col * (CELL_W + 2)
        cell_y = 5
        add_rect(msp, cell_x, cell_y, CELL_W, CELL_H, "CELLS")
        # Terminal polarity (alternating +/-)
        polarity = "+" if col % 2 == 0 else "-"
        add_label(msp, cell_x + CELL_W / 2 - 4, cell_y + CELL_H + 2,
                  polarity, "CELLS", height=6)
        add_label(msp, cell_x + 2, cell_y + CELL_H / 2 - 3,
                  f"C{col + 1}", "CELLS", height=4)

    # Busbar above cells
    bus_y = 5 + CELL_H + 2
    add_rect(msp, PLATE_W + 2, bus_y, STACK_W - 2 * PLATE_W - 4, 8, "COMPONENTS")
    add_label(msp, STACK_W / 2 - 10, bus_y + 10, "BUSBARS", "COMPONENTS", height=3)

    # Compression threaded rods (circles at each end)
    add_circle(msp, PLATE_W / 2, CELL_H / 2 + 5, 3, "FASTENERS")
    add_circle(msp, STACK_W - PLATE_W / 2, CELL_H / 2 + 5, 3, "FASTENERS")

    # Dimension lines
    add_label(msp, -5, 5, f"H={CELL_H:.0f}+busbars", "DIMENSIONS", height=3)
    add_label(msp, STACK_W / 2 - 15, -10,
              f"W={STACK_W:.0f} ({CELLS_S} cells × {CELL_W:.0f}mm)", "DIMENSIONS", height=3)

    add_label(msp, 0, STACK_H + 8,
              f"BATTERY ZONE — front elevation  (2P parallel strings stacked in depth)",
              "ANNOTATIONS", height=4)
    add_label(msp, 0, STACK_H + 18,
              f"MEASURED dims: {CELL_L:.0f}L × {CELL_W:.0f}W × {CELL_H:.0f}H mm + {TERMINAL_H:.0f}mm terminals",
              "ANNOTATIONS", height=4)

    filepath = os.path.join(OUTPUT_DIR, "6_battery_zone_detail.dxf")
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
    add_rect(msp, -CAP_INNER_W / 2, -CAP_INNER_D / 2,
             CAP_INNER_W, CAP_INNER_D, "CAP")

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
        pocket_top = OUTER_H + INSERT_DEPTH
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
    # Placed to the right of the main drawing as a callout
    # ===================================================================
    detail_cx = s1_outer + 120  # center X of detail view
    detail_base_y = OUTER_H      # align with cap bottom
    detail_scale = 8.0            # 8× zoom for clarity

    # Detail title
    add_label(msp, detail_cx - 35, detail_base_y + CAP_THICK * detail_scale + 20,
              "DETAIL: BOLT + INSERT POCKET", "FASTENERS", height=3.5)
    add_label(msp, detail_cx - 35, detail_base_y + CAP_THICK * detail_scale + 14,
              "(Section through single bolt hole, 8x scale)", "ANNOTATIONS", height=2.5)

    # Draw cap body block (zoomed)
    cap_w_detail = 20.0 * detail_scale  # 20mm slice of cap, zoomed
    cap_h_detail = CAP_THICK * detail_scale
    cx_left = detail_cx - cap_w_detail / 2
    cx_right = detail_cx + cap_w_detail / 2
    cy_bottom = detail_base_y   # cap underside
    cy_top = detail_base_y + cap_h_detail  # cap top surface

    # Cap body outline
    msp.add_lwpolyline([
        (cx_left, cy_bottom), (cx_right, cy_bottom),
        (cx_right, cy_top), (cx_left, cy_top),
    ], close=True, dxfattribs={"layer": "CAP"})

    # Gasket groove (one side, centered at detail_cx - 5*scale)
    gg_cx = detail_cx - 6 * detail_scale
    gg_hw = (CAP_GASKET_W / 2) * detail_scale
    gg_depth = CAP_GASKET_D * detail_scale
    msp.add_lwpolyline([
        (gg_cx - gg_hw, cy_top), (gg_cx - gg_hw, cy_top - gg_depth),
        (gg_cx + gg_hw, cy_top - gg_depth), (gg_cx + gg_hw, cy_top),
    ], dxfattribs={"layer": "GASKET"})

    # Gasket groove label + dim
    add_label(msp, gg_cx - gg_hw - 2, cy_top - gg_depth / 2,
              f"{CAP_GASKET_D:.1f}", "GASKET", height=2)
    add_label(msp, gg_cx, cy_top + 4,
              f"{CAP_GASKET_W:.0f}mm groove", "GASKET", height=2)

    # M4 bolt through-hole (centered in detail)
    bolt_hw = (M4_HOLE / 2) * detail_scale
    msp.add_lwpolyline([
        (detail_cx - bolt_hw, cy_top), (detail_cx - bolt_hw, cy_bottom),
        (detail_cx + bolt_hw, cy_bottom), (detail_cx + bolt_hw, cy_top),
    ], dxfattribs={"layer": "FASTENERS"})

    # Bolt shaft centerline (dashed effect — short ticks)
    for tick_y in range(int(cy_bottom), int(cy_top), 3):
        msp.add_line((detail_cx, tick_y), (detail_cx, tick_y + 1.5),
                     dxfattribs={"layer": "ANNOTATIONS"})

    # Bolt head on top (hex head, shown as rectangle in cross-section)
    head_hw = 3.5 * detail_scale  # M4 hex head ~7mm across flats
    head_h = 2.8 * detail_scale   # M4 head height ~2.8mm
    msp.add_lwpolyline([
        (detail_cx - head_hw, cy_top),
        (detail_cx - head_hw, cy_top + head_h),
        (detail_cx + head_hw, cy_top + head_h),
        (detail_cx + head_hw, cy_top),
    ], close=True, dxfattribs={"layer": "FASTENERS"})

    # Insert pocket (counterbore from underside, zoomed)
    ins_hw = (INSERT_OD / 2) * detail_scale
    ins_depth = INSERT_DEPTH * detail_scale
    pocket_top_z = cy_bottom + ins_depth

    msp.add_lwpolyline([
        (detail_cx - ins_hw, cy_bottom),
        (detail_cx - ins_hw, pocket_top_z),
        (detail_cx - bolt_hw, pocket_top_z),
        (detail_cx - bolt_hw, cy_bottom),
    ], dxfattribs={"layer": "FASTENERS"})
    msp.add_lwpolyline([
        (detail_cx + bolt_hw, cy_bottom),
        (detail_cx + bolt_hw, pocket_top_z),
        (detail_cx + ins_hw, pocket_top_z),
        (detail_cx + ins_hw, cy_bottom),
    ], dxfattribs={"layer": "FASTENERS"})

    # Brass insert body (hatched area — show with inner lines)
    # The insert sits in the pocket: INSERT_OD wide, INSERT_DEPTH tall
    # Show it as a filled-looking rectangle with cross-hatch lines
    for hatch_y_off in range(2, int(INSERT_DEPTH * detail_scale), 4):
        hy = cy_bottom + hatch_y_off
        msp.add_line((detail_cx - ins_hw + 1, hy),
                     (detail_cx - bolt_hw - 1, hy),
                     dxfattribs={"layer": "FASTENERS"})
        msp.add_line((detail_cx + bolt_hw + 1, hy),
                     (detail_cx + ins_hw - 1, hy),
                     dxfattribs={"layer": "FASTENERS"})

    # --- Dimension annotations for detail ---
    dim_x_right = detail_cx + cap_w_detail / 2 + 8

    # Cap thickness dimension
    msp.add_line((dim_x_right, cy_bottom), (dim_x_right + 15, cy_bottom),
                 dxfattribs={"layer": "ANNOTATIONS"})
    msp.add_line((dim_x_right, cy_top), (dim_x_right + 15, cy_top),
                 dxfattribs={"layer": "ANNOTATIONS"})
    msp.add_line((dim_x_right + 10, cy_bottom), (dim_x_right + 10, cy_top),
                 dxfattribs={"layer": "ANNOTATIONS"})
    add_label(msp, dim_x_right + 14, (cy_bottom + cy_top) / 2,
              f"{CAP_THICK:.0f}mm cap", "ANNOTATIONS", height=2.5)

    # Insert pocket depth dimension
    dim_x_left = detail_cx - cap_w_detail / 2 - 8
    msp.add_line((dim_x_left, cy_bottom), (dim_x_left - 15, cy_bottom),
                 dxfattribs={"layer": "ANNOTATIONS"})
    msp.add_line((dim_x_left, pocket_top_z), (dim_x_left - 15, pocket_top_z),
                 dxfattribs={"layer": "ANNOTATIONS"})
    msp.add_line((dim_x_left - 10, cy_bottom), (dim_x_left - 10, pocket_top_z),
                 dxfattribs={"layer": "ANNOTATIONS"})
    add_label(msp, dim_x_left - 45, (cy_bottom + pocket_top_z) / 2,
              f"{INSERT_DEPTH:.0f}mm pocket", "ANNOTATIONS", height=2.5)

    # Bolt hole diameter label
    add_label(msp, detail_cx + bolt_hw + 3, (cy_top + cy_bottom) / 2 + 8,
              f"{M4_HOLE:.1f}mm thru", "FASTENERS", height=2)

    # Insert OD label
    add_label(msp, detail_cx + ins_hw + 3, cy_bottom + ins_depth / 2,
              f"{INSERT_OD:.0f}mm ins OD", "FASTENERS", height=2)

    # Callout labels
    add_label(msp, detail_cx - cap_w_detail / 2, cy_bottom - 6,
              "CAP UNDERSIDE (faces shell)", "ANNOTATIONS", height=2)
    add_label(msp, detail_cx - cap_w_detail / 2, cy_top + head_h + 5,
              "CAP TOP (faces lid + weather)", "ANNOTATIONS", height=2)
    add_label(msp, detail_cx + ins_hw + 3, cy_bottom + 3,
              "BRASS INSERT", "FASTENERS", height=2)
    add_label(msp, detail_cx + head_hw + 3, cy_top + head_h / 2,
              "M4 BOLT HEAD", "FASTENERS", height=2)

    # Leader line from main drawing bolt to detail
    msp.add_line((bolt_x, cap_top + 3), (detail_cx - cap_w_detail / 2 - 5, cy_top + cap_h_detail / 2),
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

    # Cap rim outline (reference — hidden beneath lid)
    add_rect(msp, -CAP_OUTER_W / 2, -CAP_OUTER_D / 2,
             CAP_OUTER_W, CAP_OUTER_D, "CAP")

    # Shell 1 top (reference)
    add_rect(msp, -OUTER_W / 2, -OUTER_D / 2, OUTER_W, OUTER_D, "SHELL_1")

    # Bolt through-holes — MUST match cap bolt pattern exactly
    outer_gasket_inset = WALL + CAP_GASKET_MARGIN + CAP_GASKET_W / 2
    inner_gasket_inset = WALL + FOAM - CAP_GASKET_MARGIN - CAP_GASKET_W / 2
    bolt_inset = (outer_gasket_inset + inner_gasket_inset) / 2
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

    print("Generating Main Unit DXF drawings (Rev 3.2)...")
    print(f"Output: {OUTPUT_DIR}")
    print()
    print("Cell (Narada 105Ah MEASURED):")
    print(f"  {CELL_L:.0f}L x {CELL_W:.0f}W x {CELL_H:.0f}H mm + {TERMINAL_H:.0f}mm terminals")
    print()
    print("Battery zone (4S2P = 8 cells):")
    print(f"  {STACK_W:.0f} x {STACK_D:.0f} x {STACK_H:.0f} mm")
    print()
    print("Electronics zone:")
    print(f"  {ELEC_ZONE_W:.0f} x {ELEC_ZONE_D:.0f} x {ELEC_ZONE_H:.0f} mm")
    print()
    print("Derived enclosure dimensions:")
    print(f"  Interior space:          {INNER_W:.0f} x {INNER_D:.0f} x {INNER_H:.0f} mm")
    print(f"  Shell 2 (PETG struct):   {MID_W:.0f} x {MID_D:.0f} x {MID_H:.0f} mm")
    print(f"  Shell 1 (ASA outer):     {OUTER_W:.0f} x {OUTER_D:.0f} x {OUTER_H:.0f} mm")
    print(f"  Cap rim:                 {CAP_OUTER_W:.0f} x {CAP_OUTER_D:.0f} x {CAP_THICK:.0f} mm")
    print(f"  Lid:                     {LID_W:.0f} x {LID_D:.0f} x {LID_THICK:.0f} mm")
    print()

    generate_top_view()
    generate_cross_section_front()
    generate_cross_section_side()
    generate_rear_view()
    generate_zone_layout()
    generate_battery_zone_detail()
    generate_cap_top_view()
    generate_cap_profile()
    generate_lid_top_view()

    print()
    print("Done. Import DXFs via Fusion: Insert > Insert DXF")


if __name__ == "__main__":
    main()
