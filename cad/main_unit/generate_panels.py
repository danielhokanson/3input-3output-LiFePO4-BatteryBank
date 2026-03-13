#!/usr/bin/env python3
"""
Generate split guide SVGs for the Main Unit enclosure (Rev 3.2).

Shows construction plane positions for splitting each monolithic shell
body into panels that fit the Prusa Core One build volume (250x220mm).

Usage:
    python cad/main_unit/generate_panels.py

Output:
    cad/main_unit/guides/overview.svg
    cad/main_unit/guides/shell1_splits.svg   (ASA outer)
    cad/main_unit/guides/shell2_splits.svg   (PETG structural)
"""

import os
import math

# ---------------------------------------------------------------------------
# PARAMETRIC DIMENSIONS — must match generate_dxf.py
# ---------------------------------------------------------------------------

CELL_L = 129.0
CELL_W = 36.0
CELL_H = 256.0
TERMINAL_H = 4.0
CELLS_S = 4
CELLS_P = 2
STACK_W = CELLS_S * CELL_W + (CELLS_S - 1) * 2 + 8
STACK_D = CELLS_P * CELL_L + (CELLS_P - 1) * 10
STACK_H = CELL_H + TERMINAL_H + 30.0

ELEC_ZONE_W = 320.0
ELEC_ZONE_D = STACK_D
ELEC_ZONE_H = max(312.0, STACK_H)  # MPPT panel + BMS + wiring, or match stack

WALL = 5.0
WALL_S2 = 5.0    # Shell 2 wall thickness
FOAM = 30.0
ZONE_GAP = 20.0
ZONE_MARGIN = 10.0
BASE_THICK = WALL

INNER_W = 2 * ZONE_MARGIN + STACK_W + ZONE_GAP + ELEC_ZONE_W
INNER_D = max(STACK_D, ELEC_ZONE_D) + 2 * ZONE_MARGIN
INNER_H = max(STACK_H, ELEC_ZONE_H) + BASE_THICK
MID_W = INNER_W + 2 * WALL_S2
MID_D = INNER_D + 2 * WALL_S2
MID_H = INNER_H + WALL_S2
OUTER_W = MID_W + 2 * (FOAM + WALL)
OUTER_D = MID_D + 2 * (FOAM + WALL)
OUTER_H = MID_H + FOAM + WALL + BASE_THICK

SHELL2_Z = BASE_THICK + FOAM

# ---------------------------------------------------------------------------
# PRINT BED & FINGER JOINT PARAMETERS
# ---------------------------------------------------------------------------

BED_W = 250.0
BED_D = 220.0
TAB_WIDTH = 10.0
FIRST_TAB_WIDTH = 12.0
TAB_DEPTH = 5.0
TAB_GAP = 10.0
FIRST_TAB_OFFSET = 8.0
JOINT_CLEARANCE = 0.15

# ---------------------------------------------------------------------------
# SHELL CONFIGURATIONS
# ---------------------------------------------------------------------------

SHELLS = [
    {"id": 1, "W": OUTER_W, "D": OUTER_D, "H": OUTER_H,
     "wall": WALL, "material": "ASA", "join": "Acetone/MEK weld",
     "z_offset": 0},
    {"id": 2, "W": MID_W, "D": MID_D, "H": MID_H,
     "wall": WALL_S2, "material": "PETG", "join": "CA glue",
     "z_offset": SHELL2_Z},
]

GUIDE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guides")


# ---------------------------------------------------------------------------
# SPLIT CALCULATION
# ---------------------------------------------------------------------------

def fits_bed(w, h):
    return (w <= BED_W and h <= BED_D) or (w <= BED_D and h <= BED_W)


def min_splits(dim):
    for n in range(1, 20):
        if dim / n <= max(BED_W, BED_D):
            return n
    return 20


def calculate_splits(shell):
    W, D, H = shell["W"], shell["D"], shell["H"]
    sid = shell["id"]

    x_cols = min_splits(W)
    col_w = W / x_cols
    x_planes = [round(-W / 2 + i * col_w, 1) for i in range(1, x_cols)]

    y_rows = min_splits(D)
    y_planes = [round(-D / 2 + i * (D / y_rows), 1) for i in range(1, y_rows)]

    z_rows = 1
    z_planes = []
    if not fits_bed(col_w, H):
        z_rows = min_splits(H)
        row_h = H / z_rows
        z_planes = [round(shell["z_offset"] + i * row_h, 1) for i in range(1, z_rows)]

    side_w = D - 2 * WALL
    side_cols = min_splits(side_w)
    row_h = H / z_rows if z_rows > 1 else H
    side_piece = side_w / side_cols
    base_row_d = D / y_rows

    panels = []
    for face in ["front", "back"]:
        for c in range(x_cols):
            for r in range(z_rows):
                panels.append({
                    "face": face, "col": c, "row": r,
                    "w": round(col_w, 1), "h": round(row_h, 1),
                    "id": f"S{sid}_{face}_{chr(65+c)}" +
                          (str(r+1) if z_rows > 1 else ""),
                })
    for face in ["left", "right"]:
        for c in range(side_cols):
            for r in range(z_rows):
                panels.append({
                    "face": face, "col": c, "row": r,
                    "w": round(side_piece, 1), "h": round(row_h, 1),
                    "id": f"S{sid}_{face}_{chr(65+c)}" +
                          (str(r+1) if z_rows > 1 else ""),
                })
    for c in range(x_cols):
        for r in range(y_rows):
            panels.append({
                "face": "base", "col": c, "row": r,
                "w": round(col_w, 1), "h": round(base_row_d, 1),
                "id": f"S{sid}_base_{chr(65+c)}{r+1}",
            })

    return {
        "x_planes": x_planes, "y_planes": y_planes, "z_planes": z_planes,
        "x_cols": x_cols, "y_rows": y_rows, "z_rows": z_rows,
        "col_w": round(col_w, 1), "row_h": round(row_h, 1),
        "side_piece": round(side_piece, 1), "side_cols": side_cols,
        "base_row_d": round(base_row_d, 1), "panels": panels,
    }


# ---------------------------------------------------------------------------
# SVG BUILDER
# ---------------------------------------------------------------------------

class SVGBuilder:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.elements = []
        self.defs = []

    def rect(self, x, y, w, h, fill="none", stroke="#333", stroke_width=1.5,
             opacity=1.0, dash=None, rx=0):
        attrs = (f'x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
                 f'opacity="{opacity}"')
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        if rx:
            attrs += f' rx="{rx}"'
        self.elements.append(f'  <rect {attrs}/>')

    def line(self, x1, y1, x2, y2, stroke="#333", stroke_width=1, dash=None):
        attrs = (f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{stroke}" stroke-width="{stroke_width}"')
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        self.elements.append(f'  <line {attrs}/>')

    def text(self, x, y, content, font_size=12, fill="#333", anchor="start",
             font_weight="normal", rotate=0):
        transform = f' transform="rotate({rotate},{x:.1f},{y:.1f})"' if rotate else ""
        safe = str(content).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.elements.append(
            f'  <text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{font_weight}" '
            f'font-family="Arial, sans-serif"{transform}>{safe}</text>')

    def save(self, filepath):
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">',
            '  <style>text { font-family: Arial, Helvetica, sans-serif; }</style>',
        ]
        if self.defs:
            parts.append('  <defs>')
            parts.extend(self.defs)
            parts.append('  </defs>')
        parts.append(f'  <rect width="{self.width}" height="{self.height}" fill="white"/>')
        parts.extend(self.elements)
        parts.append('</svg>')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(parts))
        print(f"  Created: {filepath}")


COLORS = {
    1: {"fill": "#ff6b6b", "stroke": "#cc3333", "label": "#991111", "bg": "#fff0f0"},
    2: {"fill": "#51cf66", "stroke": "#2b8a3e", "label": "#1a6628", "bg": "#f0fff0"},
}


# ---------------------------------------------------------------------------
# OVERVIEW SVG
# ---------------------------------------------------------------------------

def generate_overview_svg():
    svg = SVGBuilder(1000, 600)

    svg.text(20, 30, "MAIN UNIT — SPLIT GUIDE OVERVIEW (Rev 3.2)",
             font_size=18, font_weight="bold")
    svg.text(20, 50, f"Prusa Core One build volume: {BED_W:.0f} x {BED_D:.0f} mm",
             font_size=11, fill="#555")

    # Design notes
    y = 70
    svg.rect(15, y - 5, 970, 110, fill="#f8f9fa", stroke="#dee2e6", rx=4)
    svg.text(25, y + 14, "DESIGN NOTES", font_size=13, font_weight="bold")
    notes = [
        f"Main unit outer shell: {OUTER_W:.0f} x {OUTER_D:.0f} x {OUTER_H:.0f} mm",
        f"Battery zone (4S2P): {STACK_W:.0f} x {STACK_D:.0f} x {STACK_H:.0f} mm  "
        f"| Cell PLACEHOLDER: {CELL_L:.0f}L x {CELL_W:.0f}W x {CELL_H:.0f}H — verify Narada datasheet",
        f"Electronics zone: {ELEC_ZONE_W:.0f} x {ELEC_ZONE_D:.0f} x {ELEC_ZONE_H:.0f} mm",
        "Two-shell construction: Shell 1 ASA (outer boulder) + 30mm foam + Shell 2 PETG (structural, direct inner container)",
        "Satellite units connect via external leads; no satellite cells in main unit (expandable)",
    ]
    for i, note in enumerate(notes):
        svg.text(35, y + 36 + i * 16, note, font_size=10, fill="#333")

    # Shell summary table
    y = 200
    svg.text(20, y, "SHELL SUMMARY", font_size=13, font_weight="bold")
    y += 20
    svg.rect(15, y - 2, 970, 22, fill="#e9ecef", stroke="#ccc", rx=3)
    headers = [("Shell", 25), ("Material", 110), ("Dimensions (mm)", 210),
               ("Split Planes", 420), ("Panels", 620), ("Join Method", 720)]
    for label, hx in headers:
        svg.text(hx, y + 14, label, font_size=9, font_weight="bold")
    y += 24

    for shell in SHELLS:
        sp = calculate_splits(shell)
        sid = shell["id"]
        c = COLORS[sid]
        bg = c["bg"] if sid % 2 == 1 else "white"
        svg.rect(15, y - 2, 970, 22, fill=bg, stroke="#eee", rx=2)
        svg.rect(20, y + 3, 14, 14, fill=c["fill"], stroke=c["stroke"],
                 stroke_width=1, rx=2)
        svg.text(40, y + 14, str(sid), font_size=10, font_weight="bold",
                 fill=c["label"])
        svg.text(110, y + 14, shell["material"], font_size=9)
        svg.text(210, y + 14,
                 f'{shell["W"]:.0f} x {shell["D"]:.0f} x {shell["H"]:.0f}',
                 font_size=9)
        n_planes = len(sp["x_planes"]) + len(sp["y_planes"]) + len(sp["z_planes"])
        plane_desc = f'{len(sp["x_planes"])}x X + {len(sp["y_planes"])}x Y'
        if sp["z_planes"]:
            plane_desc += f' + {len(sp["z_planes"])}x Z'
        plane_desc += f' = {n_planes} total'
        svg.text(420, y + 14, plane_desc, font_size=9)
        svg.text(620, y + 14, f'{len(sp["panels"])} panels', font_size=9,
                 font_weight="bold")
        svg.text(720, y + 14, shell["join"], font_size=9)
        y += 24

    total = sum(len(calculate_splits(s)["panels"]) for s in SHELLS)
    svg.text(25, y + 14,
             f'Total: {total} panels across 2 shells',
             font_size=10, fill="#555")

    # Workflow
    y += 45
    svg.rect(15, y - 5, 970, 150, fill="#f0f4ff", stroke="#339af0", rx=4)
    svg.text(25, y + 14, "FUSION WORKFLOW", font_size=13, font_weight="bold",
             fill="#0d4a8a")
    steps = [
        "1. Build monolithic shell body (Insert DXFs from main_unit/dxf/ > Extrude > Shell cmd)",
        "2. Construct > Offset Plane — create planes at positions shown in shell split guides",
        "3. Modify > Split Body — select shell body + all construction planes as split tools",
        "4. Orient each segment flat (Arrange on XY), add finger joints on split faces",
        "5. Extrude Join tabs on side A, Extrude Cut pockets on side B",
        "6. Right-click each body > Save as Mesh (STL) > slice for Prusa Core One",
    ]
    for i, step in enumerate(steps):
        svg.text(35, y + 36 + i * 18, step, font_size=10, fill="#333")

    filepath = os.path.join(GUIDE_DIR, "overview.svg")
    svg.save(filepath)


# ---------------------------------------------------------------------------
# PER-SHELL SPLIT DIAGRAMS
# ---------------------------------------------------------------------------

def generate_shell_split_svg(shell):
    sid = shell["id"]
    W, D, H = shell["W"], shell["D"], shell["H"]
    sp = calculate_splits(shell)
    c = COLORS[sid]

    svg = SVGBuilder(1200, 920)

    svg.text(20, 28,
             f"MAIN UNIT — SHELL {sid} SPLIT GUIDE ({shell['material']})",
             font_size=16, font_weight="bold", fill=c["label"])
    svg.text(20, 46,
             f'{W:.0f} x {D:.0f} x {H:.0f} mm | {len(sp["panels"])} panels | '
             f'{shell["join"]} | Z-offset: +{shell["z_offset"]:.0f} mm',
             font_size=11, fill="#555")

    # TOP VIEW
    tv_title_y = 65
    svg.text(20, tv_title_y, "TOP VIEW (XY)", font_size=12, font_weight="bold")

    scale = min(480 / W, 240 / D)
    tv_cx = 300
    tv_cy = tv_title_y + 30 + (D * scale) / 2
    tv_x0 = tv_cx - W * scale / 2
    tv_y0 = tv_cy - D * scale / 2
    tv_w = W * scale
    tv_h = D * scale

    svg.rect(tv_x0, tv_y0, tv_w, tv_h,
             fill=c["fill"], stroke=c["stroke"], stroke_width=2, opacity=0.15)

    # Zone reference lines (only Shell 2 — inner container)
    if sid == 2:
        batt_zone_w = STACK_W * scale
        svg.line(tv_x0 + ZONE_MARGIN * scale, tv_y0,
                 tv_x0 + ZONE_MARGIN * scale + batt_zone_w, tv_y0 + tv_h,
                 stroke="#ffd43b", stroke_width=1, dash="4,2")
        svg.line(tv_x0 + ZONE_MARGIN * scale + batt_zone_w, tv_y0,
                 tv_x0 + ZONE_MARGIN * scale + batt_zone_w, tv_y0 + tv_h,
                 stroke="#ffd43b", stroke_width=1, dash="4,2")
        svg.text(tv_x0 + ZONE_MARGIN * scale + 3, tv_y0 + 10,
                 "BATT", font_size=7, fill="#b37400")
        svg.text(tv_x0 + ZONE_MARGIN * scale + batt_zone_w + ZONE_GAP * scale + 3,
                 tv_y0 + 10, "ELEC", font_size=7, fill="#0d4a8a")

    for xp in sp["x_planes"]:
        px = tv_cx + xp * scale
        svg.line(px, tv_y0 - 10, px, tv_y0 + tv_h + 10,
                 stroke="#e03131", stroke_width=2, dash="6,3")
        svg.text(px, tv_y0 - 14, f'X={xp:+.1f}',
                 font_size=8, fill="#e03131", anchor="middle", font_weight="bold")

    for yp in sp["y_planes"]:
        py = tv_cy + yp * scale
        svg.line(tv_x0 - 10, py, tv_x0 + tv_w + 10, py,
                 stroke="#1864ab", stroke_width=2, dash="6,3")
        svg.text(tv_x0 + tv_w + 14, py + 4, f'Y={yp:+.1f}',
                 font_size=8, fill="#1864ab", font_weight="bold")

    base_panels = [p for p in sp["panels"] if p["face"] == "base"]
    for p in base_panels:
        px = tv_x0 + p["col"] * (tv_w / sp["x_cols"]) + (tv_w / sp["x_cols"]) / 2
        py = tv_y0 + p["row"] * (tv_h / sp["y_rows"]) + (tv_h / sp["y_rows"]) / 2
        svg.text(px, py + 3, p["id"], font_size=7, fill=c["label"], anchor="middle")

    svg.text(tv_cx, tv_y0 - 28, "X (width)", font_size=9, fill="#888", anchor="middle")
    svg.text(tv_x0 - 30, tv_cy, "Y", font_size=9, fill="#888", anchor="middle", rotate=-90)
    svg.text(tv_cx, tv_y0 + tv_h + 30, f'W = {W:.0f} mm', font_size=9,
             fill="#666", anchor="middle")

    # CONSTRUCTION PLANE TABLE
    tbl_x = 640
    tbl_y = tv_title_y
    svg.text(tbl_x, tbl_y, "CONSTRUCTION PLANES", font_size=12, font_weight="bold")
    tbl_y += 20
    svg.rect(tbl_x - 5, tbl_y - 2, 540, 22, fill="#e9ecef", stroke="#ccc", rx=3)
    for label, hx in [("#", tbl_x), ("Type", tbl_x + 25), ("Offset", tbl_x + 140),
                       ("Splits", tbl_x + 240)]:
        svg.text(hx, tbl_y + 14, label, font_size=9, font_weight="bold")
    tbl_y += 24

    plane_num = 1
    all_planes = []
    for xp in sp["x_planes"]:
        all_planes.append(("YZ Plane", f"X = {xp:+.1f} mm",
                           "Front, Back, Base (width)", "#e03131"))
    for yp in sp["y_planes"]:
        all_planes.append(("XZ Plane", f"Y = {yp:+.1f} mm",
                           "Left, Right walls + Base (depth)", "#1864ab"))
    for zp in sp["z_planes"]:
        all_planes.append(("XY Plane", f"Z = {zp:.1f} mm",
                           "All walls (height)", "#2f9e44"))

    for ptype, offset, splits, color in all_planes:
        bg = "#f8f8f8" if plane_num % 2 == 1 else "white"
        svg.rect(tbl_x - 5, tbl_y - 2, 540, 22, fill=bg, stroke="#eee", rx=2)
        svg.rect(tbl_x + 2, tbl_y + 3, 12, 12, fill=color, rx=2)
        svg.text(tbl_x + 18, tbl_y + 14, str(plane_num), font_size=9,
                 fill=color, font_weight="bold")
        svg.text(tbl_x + 25, tbl_y + 14, ptype, font_size=9)
        svg.text(tbl_x + 140, tbl_y + 14, offset, font_size=9,
                 font_weight="bold", fill=color)
        svg.text(tbl_x + 240, tbl_y + 14, splits, font_size=9, fill="#555")
        tbl_y += 24
        plane_num += 1

    svg.text(tbl_x, tbl_y + 10,
             f'{len(all_planes)} construction plane(s) total',
             font_size=10, fill="#666")

    # FRONT VIEW
    fv_y_start = max(tv_y0 + tv_h + 65, tbl_y + 40)
    svg.text(20, fv_y_start, "FRONT VIEW (XZ)", font_size=12, font_weight="bold")

    fv_scale = min(480 / W, 200 / H)
    fv_cx = 300
    fv_cy = fv_y_start + 25 + (H * fv_scale) / 2
    fv_x0 = fv_cx - W * fv_scale / 2
    fv_y0 = fv_cy - H * fv_scale / 2
    fv_w = W * fv_scale
    fv_h = H * fv_scale

    svg.rect(fv_x0, fv_y0, fv_w, fv_h,
             fill=c["fill"], stroke=c["stroke"], stroke_width=2, opacity=0.2)

    for xp in sp["x_planes"]:
        px = fv_cx + xp * fv_scale
        svg.line(px, fv_y0 - 8, px, fv_y0 + fv_h + 8,
                 stroke="#e03131", stroke_width=2, dash="6,3")

    for zp in sp["z_planes"]:
        rel_z = zp - shell["z_offset"]
        py = fv_y0 + fv_h - rel_z * fv_scale
        svg.line(fv_x0 - 10, py, fv_x0 + fv_w + 10, py,
                 stroke="#2f9e44", stroke_width=2, dash="6,3")
        svg.text(fv_x0 + fv_w + 14, py + 4, f'Z={zp:.1f}',
                 font_size=8, fill="#2f9e44", font_weight="bold")

    front_panels = [p for p in sp["panels"] if p["face"] == "front"]
    for p in front_panels:
        px = fv_x0 + p["col"] * (fv_w / sp["x_cols"]) + (fv_w / sp["x_cols"]) / 2
        py = fv_y0 + (sp["z_rows"] - 1 - p["row"]) * (fv_h / sp["z_rows"]) + \
             (fv_h / sp["z_rows"]) / 2
        svg.text(px, py + 3, p["id"], font_size=7, fill=c["label"], anchor="middle")

    svg.text(fv_cx, fv_y0 - 12, "X (width)", font_size=9, fill="#888", anchor="middle")
    svg.text(fv_cx, fv_y0 + fv_h + 28, f'W = {W:.0f} mm', font_size=9,
             fill="#666", anchor="middle")

    # PANEL INVENTORY
    inv_y = fv_y0 + fv_h + 55
    svg.text(20, inv_y, "PANEL INVENTORY", font_size=12, font_weight="bold")
    inv_y += 18
    svg.rect(15, inv_y - 2, 1170, 20, fill="#e9ecef", stroke="#ccc", rx=3)
    for label, hx in [("Face", 25), ("Pieces", 100), ("Panel Size (mm)", 180),
                       ("Fits Bed?", 360), ("IDs", 460)]:
        svg.text(hx, inv_y + 13, label, font_size=9, font_weight="bold")
    inv_y += 22

    faces = [
        ("front", "Front wall", sp["x_cols"], sp["z_rows"], sp["col_w"], sp["row_h"]),
        ("back", "Back wall", sp["x_cols"], sp["z_rows"], sp["col_w"], sp["row_h"]),
        ("left", "Left wall", sp["side_cols"], sp["z_rows"], sp["side_piece"], sp["row_h"]),
        ("right", "Right wall", sp["side_cols"], sp["z_rows"], sp["side_piece"], sp["row_h"]),
        ("base", "Base", sp["x_cols"], sp["y_rows"], sp["col_w"], sp["base_row_d"]),
    ]
    for i, (face_key, face_name, cols, rows, pw, ph) in enumerate(faces):
        bg = "#f8f8f8" if i % 2 == 0 else "white"
        svg.rect(15, inv_y - 2, 1170, 20, fill=bg, stroke="#eee", rx=2)
        svg.text(25, inv_y + 13, face_name, font_size=9)
        n = cols * rows
        svg.text(100, inv_y + 13, f'{cols}x{rows} = {n}', font_size=9)
        svg.text(180, inv_y + 13, f'{pw:.1f} x {ph:.1f}', font_size=9, font_weight="bold")
        bed_ok = fits_bed(pw, ph)
        fit_note = "Yes" if bed_ok and not (pw > BED_W or ph > BED_D) else \
                   "Yes (rotate 90)" if bed_ok else "NO — check Z-split"
        svg.text(360, inv_y + 13, fit_note, font_size=9,
                 fill="#2f9e44" if bed_ok else "#e03131")
        face_panels = [p for p in sp["panels"] if p["face"] == face_key]
        ids = ", ".join(p["id"] for p in face_panels[:6])
        if len(face_panels) > 6:
            ids += f" … ({len(face_panels)} total)"
        svg.text(460, inv_y + 13, ids, font_size=8, fill="#888")
        inv_y += 22

    svg.text(25, inv_y + 10,
             f'Total: {len(sp["panels"])} panels | Material: {shell["material"]} | '
             f'Join: {shell["join"]} | Wall: {shell["wall"]:.0f}mm',
             font_size=10, fill=c["label"], font_weight="bold")

    filepath = os.path.join(GUIDE_DIR, f"shell{sid}_splits.svg")
    svg.save(filepath)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    os.makedirs(GUIDE_DIR, exist_ok=True)

    print("Generating Main Unit split guide SVGs (Rev 3.2)...")
    print(f"Build volume: {BED_W:.0f} x {BED_D:.0f} mm")
    print(f"Outer shell: {OUTER_W:.0f} x {OUTER_D:.0f} x {OUTER_H:.0f} mm")
    print()

    for shell in SHELLS:
        sp = calculate_splits(shell)
        n_planes = len(sp["x_planes"]) + len(sp["y_planes"]) + len(sp["z_planes"])
        print(f"  Shell {shell['id']} ({shell['material']}): "
              f"{shell['W']:.0f}x{shell['D']:.0f}x{shell['H']:.0f}mm -> "
              f"{n_planes} construction planes -> "
              f"{len(sp['panels'])} panels")

    print()
    generate_overview_svg()
    for shell in SHELLS:
        generate_shell_split_svg(shell)

    total = sum(len(calculate_splits(s)["panels"]) for s in SHELLS)
    print()
    print(f"Done! {total} total panels across 2 shells.")


if __name__ == "__main__":
    main()
