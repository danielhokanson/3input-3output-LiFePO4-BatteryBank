#!/usr/bin/env python3
"""
Panel Splitter — Separate shell STL into flat, bed-sized panels with engraved IDs.

Workflow:
  1. Group mesh faces by dominant normal direction (±X, ±Y, ±Z)
  2. Separate into face panels (FRONT, BACK, LEFT, RIGHT, BASE)
  3. Rotate each panel flat (outer face down, 5mm print height)
  4. Subdivide oversized panels to fit print bed with overlap splices
  5. Engrave panel ID on inner face (top surface when printing)
  6. Export as individual STL files + assembly map

Usage:
    python cad/split_panels.py "cad/main_unit/product stl/Shell 1.stl" --prefix S1
    python cad/split_panels.py "cad/main_unit/product stl/Shell 2.stl" --prefix S2
    python cad/split_panels.py "cad/main_unit/product stl/Cap.stl" --prefix CAP
    python cad/split_panels.py "cad/main_unit/product stl/Lid.stl" --prefix LID

Output:
    cad/main_unit/panels/<prefix>-BASE-01.stl, <prefix>-FRONT-01.stl, ...
    cad/main_unit/panels/assembly_map_<prefix>.txt
"""

import argparse
import math
import os
import sys

import numpy as np

try:
    import trimesh
except ImportError:
    print("ERROR: pip install trimesh")
    sys.exit(1)

try:
    import manifold3d
    HAS_MANIFOLD = True
except ImportError:
    HAS_MANIFOLD = False
    print("WARNING: manifold3d not installed — engraving will use embossed (raised) text instead")

# ============================================================================
# PIXEL FONT — 5×7 grid per character
# ============================================================================

FONT = {
    "0": ["01110","10001","10011","10101","11001","10001","01110"],
    "1": ["00100","01100","00100","00100","00100","00100","01110"],
    "2": ["01110","10001","00001","00110","01000","10000","11111"],
    "3": ["01110","10001","00001","00110","00001","10001","01110"],
    "4": ["00010","00110","01010","10010","11111","00010","00010"],
    "5": ["11111","10000","11110","00001","00001","10001","01110"],
    "6": ["01110","10000","11110","10001","10001","10001","01110"],
    "7": ["11111","00001","00010","00100","01000","01000","01000"],
    "8": ["01110","10001","10001","01110","10001","10001","01110"],
    "9": ["01110","10001","10001","01111","00001","00001","01110"],
    "A": ["01110","10001","10001","11111","10001","10001","10001"],
    "B": ["11110","10001","10001","11110","10001","10001","11110"],
    "C": ["01110","10001","10000","10000","10000","10001","01110"],
    "D": ["11110","10001","10001","10001","10001","10001","11110"],
    "E": ["11111","10000","10000","11110","10000","10000","11111"],
    "F": ["11111","10000","10000","11110","10000","10000","10000"],
    "G": ["01110","10001","10000","10111","10001","10001","01110"],
    "H": ["10001","10001","10001","11111","10001","10001","10001"],
    "I": ["01110","00100","00100","00100","00100","00100","01110"],
    "K": ["10001","10010","10100","11000","10100","10010","10001"],
    "L": ["10000","10000","10000","10000","10000","10000","11111"],
    "M": ["10001","11011","10101","10101","10001","10001","10001"],
    "N": ["10001","11001","10101","10011","10001","10001","10001"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "P": ["11110","10001","10001","11110","10000","10000","10000"],
    "R": ["11110","10001","10001","11110","10100","10010","10001"],
    "S": ["01110","10001","10000","01110","00001","10001","01110"],
    "T": ["11111","00100","00100","00100","00100","00100","00100"],
    "U": ["10001","10001","10001","10001","10001","10001","01110"],
    "W": ["10001","10001","10001","10101","10101","11011","10001"],
    "X": ["10001","10001","01010","00100","01010","10001","10001"],
    "-": ["00000","00000","00000","11111","00000","00000","00000"],
    " ": ["00000","00000","00000","00000","00000","00000","00000"],
}


def text_to_mesh(text, cell_size=1.5, depth=0.5, z_base=0.0):
    """Convert text string to a 3D mesh using pixel font.

    Text is generated in XY plane at z=z_base, extruding upward by depth.
    Returns trimesh.Trimesh.
    """
    boxes = []
    x_offset = 0

    for ch in text.upper():
        glyph = FONT.get(ch)
        if glyph is None:
            x_offset += 3 * cell_size  # space for unknown chars
            continue

        for row_idx, row in enumerate(glyph):
            y = (6 - row_idx) * cell_size  # top-to-bottom
            for col_idx, pixel in enumerate(row):
                if pixel == "1":
                    x = x_offset + col_idx * cell_size
                    box = trimesh.creation.box(
                        extents=[cell_size * 0.95, cell_size * 0.95, depth],
                        transform=trimesh.transformations.translation_matrix(
                            [x + cell_size / 2, y + cell_size / 2, z_base + depth / 2]
                        )
                    )
                    boxes.append(box)

        x_offset += 6 * cell_size  # character width + spacing

    if not boxes:
        return None
    return trimesh.util.concatenate(boxes)


def engrave_text(panel_mesh, text, face="top"):
    """Engrave text into a panel mesh surface.

    For 'top' face: text is cut into the +Z surface.
    Uses boolean difference if manifold3d available, otherwise embosses.
    """
    bounds = panel_mesh.bounds
    ext = panel_mesh.extents

    # Size text to ~40% of the shorter panel dimension
    text_len = len(text) * 6  # approximate character cells
    max_text_width = min(ext[0], ext[1]) * 0.6
    cell_size = max(0.8, min(2.0, max_text_width / max(1, text_len)))
    depth = 0.4  # engrave depth

    text_mesh = text_to_mesh(text, cell_size=cell_size, depth=depth * 2)
    if text_mesh is None:
        return panel_mesh

    # Center text on panel surface
    text_bounds = text_mesh.bounds
    text_ext = text_mesh.extents
    text_center = (text_bounds[0] + text_bounds[1]) / 2
    panel_center = (bounds[0] + bounds[1]) / 2

    # Position on top face
    translation = [
        panel_center[0] - text_center[0],
        panel_center[1] - text_center[1],
        bounds[1][2] - depth - text_bounds[0][2]  # sink into top surface
    ]
    text_mesh.apply_translation(translation)

    if HAS_MANIFOLD:
        try:
            # Boolean difference — engrave into surface
            result = trimesh.boolean.difference([panel_mesh, text_mesh], engine="manifold")
            if result is not None and len(result.faces) > 0:
                return result
        except Exception as e:
            print(f"    Boolean engrave failed ({e}), using emboss fallback")

    # Fallback: emboss (add raised text on top)
    text_mesh_raised = text_to_mesh(text, cell_size=cell_size, depth=depth)
    if text_mesh_raised is None:
        return panel_mesh
    translation[2] = bounds[1][2] - text_mesh_raised.bounds[0][2]
    text_mesh_raised.apply_translation(translation)
    return trimesh.util.concatenate([panel_mesh, text_mesh_raised])


# ============================================================================
# FACE SEPARATION
# ============================================================================

# Cardinal direction labels and normals
DIRECTIONS = {
    "FRONT":  np.array([0, 1, 0]),    # +Y
    "BACK":   np.array([0, -1, 0]),   # -Y
    "RIGHT":  np.array([1, 0, 0]),    # +X
    "LEFT":   np.array([-1, 0, 0]),   # -X
    "BASE":   np.array([0, 0, -1]),   # -Z (bottom)
    "TOP":    np.array([0, 0, 1]),     # +Z (top, if closed)
}


def classify_faces(mesh):
    """Classify each face by its dominant normal direction."""
    normals = mesh.face_normals
    labels = []

    for n in normals:
        best_dir = None
        best_dot = -2.0
        for name, direction in DIRECTIONS.items():
            dot = np.dot(n, direction)
            if dot > best_dot:
                best_dot = dot
                best_dir = name
        labels.append(best_dir)

    return labels


def separate_faces(mesh):
    """Separate mesh into sub-meshes by face normal direction.

    Returns dict of {direction_name: trimesh.Trimesh}.
    """
    labels = classify_faces(mesh)
    groups = {}

    for dir_name in DIRECTIONS:
        face_indices = [i for i, l in enumerate(labels) if l == dir_name]
        if not face_indices:
            continue

        # Extract submesh
        submesh = mesh.submesh([face_indices], append=True)
        if submesh is not None and len(submesh.faces) > 0:
            groups[dir_name] = submesh

    return groups


def rotate_panel_flat(panel, face_name):
    """Rotate a face panel so it lies flat in XY plane (outer face down).

    The panel's dominant normal direction gets rotated to -Z (face down).
    """
    rotations = {
        "FRONT":  trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]),
        "BACK":   trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]),
        "RIGHT":  trimesh.transformations.rotation_matrix(-math.pi / 2, [0, 1, 0]),
        "LEFT":   trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]),
        "BASE":   np.eye(4),  # already flat
        "TOP":    trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]),
    }

    rot = rotations.get(face_name, np.eye(4))
    panel.apply_transform(rot)

    # Translate so min corner is at origin
    panel.apply_translation(-panel.bounds[0])

    return panel


# ============================================================================
# SUBDIVISION
# ============================================================================

def subdivide_panel(panel, bed_x, bed_y, overlap):
    """Split a flat panel into bed-sized pieces with overlap.

    Returns list of (piece_mesh, col, row, n_cols, n_rows).
    """
    ext = panel.extents

    # Determine how many cuts needed
    def n_pieces(span, bed_dim, ovlp):
        if span <= bed_dim:
            return 1
        step = bed_dim - ovlp
        return max(1, math.ceil((span - ovlp) / step))

    n_x = n_pieces(ext[0], bed_x, overlap)
    n_y = n_pieces(ext[1], bed_y, overlap)

    if n_x == 1 and n_y == 1:
        return [(panel, 0, 0, 1, 1)]

    pieces = []
    x_min, y_min = panel.bounds[0][0], panel.bounds[0][1]
    x_max, y_max = panel.bounds[1][0], panel.bounds[1][1]

    step_x = (ext[0] - overlap) / n_x if n_x > 1 else ext[0]
    step_y = (ext[1] - overlap) / n_y if n_y > 1 else ext[1]

    for iy in range(n_y):
        for ix in range(n_x):
            piece = panel.copy()

            # X cuts
            if n_x > 1:
                # Left cut
                if ix > 0:
                    cut_x = x_min + ix * step_x
                    try:
                        piece = trimesh.intersections.slice_mesh_plane(
                            piece, [-1, 0, 0], [cut_x - overlap, 0, 0])
                    except Exception:
                        continue

                # Right cut
                if ix < n_x - 1:
                    cut_x = x_min + (ix + 1) * step_x + overlap
                    try:
                        piece = trimesh.intersections.slice_mesh_plane(
                            piece, [1, 0, 0], [cut_x, 0, 0])
                    except Exception:
                        continue

            # Y cuts
            if n_y > 1:
                # Front cut
                if iy > 0:
                    cut_y = y_min + iy * step_y
                    try:
                        piece = trimesh.intersections.slice_mesh_plane(
                            piece, [0, -1, 0], [0, cut_y - overlap, 0])
                    except Exception:
                        continue

                # Back cut
                if iy < n_y - 1:
                    cut_y = y_min + (iy + 1) * step_y + overlap
                    try:
                        piece = trimesh.intersections.slice_mesh_plane(
                            piece, [0, 1, 0], [0, cut_y, 0])
                    except Exception:
                        continue

            if piece is not None and len(piece.faces) > 0:
                # Reset origin
                piece.apply_translation(-piece.bounds[0])
                pieces.append((piece, ix, iy, n_x, n_y))

    return pieces


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def process_stl(input_path, bed_x=250, bed_y=220, overlap=10, prefix="S1",
                output_dir=None):
    """Full pipeline: load, separate faces, subdivide, engrave, export."""

    print(f"\nLoading: {input_path}")
    mesh = trimesh.load(input_path)

    if isinstance(mesh, trimesh.Scene):
        meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
        mesh = trimesh.util.concatenate(meshes) if meshes else None
    if mesh is None or len(mesh.faces) == 0:
        print("ERROR: No geometry found")
        return

    print(f"  Vertices: {len(mesh.vertices):,}, Faces: {len(mesh.faces):,}")
    print(f"  Extents: {mesh.extents[0]:.1f} x {mesh.extents[1]:.1f} x {mesh.extents[2]:.1f} mm")
    print(f"  Bed: {bed_x}x{bed_y}mm, Overlap: {overlap}mm")

    if output_dir is None:
        base_dir = os.path.dirname(os.path.abspath(input_path))
        output_dir = os.path.join(base_dir, "panels")
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Separate faces
    print("\n  Separating faces by normal direction...")
    face_groups = separate_faces(mesh)
    for name, submesh in face_groups.items():
        print(f"    {name}: {len(submesh.faces)} faces")

    # Step 2-5: Process each face
    assembly_entries = []
    total_panels = 0

    for face_name in ["BASE", "FRONT", "BACK", "LEFT", "RIGHT", "TOP"]:
        if face_name not in face_groups:
            continue

        face_mesh = face_groups[face_name]
        print(f"\n  Processing {face_name} ({len(face_mesh.faces)} faces)...")

        # Rotate flat
        flat_panel = rotate_panel_flat(face_mesh.copy(), face_name)
        print(f"    Flat extents: {flat_panel.extents[0]:.1f} x {flat_panel.extents[1]:.1f} x {flat_panel.extents[2]:.1f} mm")

        # Subdivide
        pieces = subdivide_panel(flat_panel, bed_x, bed_y, overlap)
        print(f"    Split into {len(pieces)} piece(s)")

        for piece, ix, iy, nx, ny in pieces:
            total_panels += 1
            if nx == 1 and ny == 1:
                panel_id = f"{prefix}-{face_name}"
            else:
                sub_idx = iy * nx + ix + 1
                panel_id = f"{prefix}-{face_name}-{sub_idx:02d}"

            ext = piece.extents
            fits = ext[0] <= bed_x + 1 and ext[1] <= bed_y + 1

            # Engrave label
            print(f"    Engraving: {panel_id}...", end="")
            try:
                piece = engrave_text(piece, panel_id)
                print(" done")
            except Exception as e:
                print(f" failed ({e})")

            # Export
            filepath = os.path.join(output_dir, f"{panel_id}.stl")
            piece.export(filepath)

            status = "OK" if fits else f"OVERSIZE"
            info = f"      {panel_id}: {ext[0]:.1f}x{ext[1]:.1f}x{ext[2]:.1f}mm, {len(piece.faces)} faces [{status}]"
            print(info)

            assembly_entries.append({
                "id": panel_id,
                "face": face_name,
                "grid": f"{ix+1}/{nx} x {iy+1}/{ny}" if nx > 1 or ny > 1 else "full",
                "extents": f"{ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f}",
                "faces": len(piece.faces),
                "fits_bed": fits,
            })

    # Write assembly map
    map_path = os.path.join(output_dir, f"assembly_map_{prefix}.txt")
    with open(map_path, "w") as f:
        f.write(f"ASSEMBLY MAP -- {prefix}\n")
        f.write(f"Source: {os.path.basename(input_path)}\n")
        f.write(f"Bed: {bed_x} x {bed_y} mm\n")
        f.write(f"Overlap: {overlap} mm\n")
        f.write(f"Total panels: {total_panels}\n")
        f.write(f"Engraving: {'boolean engrave' if HAS_MANIFOLD else 'embossed (raised)'}\n")
        f.write(f"\n{'=' * 50}\n\n")

        # Group by face
        for face_name in ["BASE", "FRONT", "BACK", "LEFT", "RIGHT", "TOP"]:
            face_entries = [e for e in assembly_entries if e["face"] == face_name]
            if not face_entries:
                continue
            f.write(f"{face_name}:\n")
            for entry in face_entries:
                bed_ok = "OK" if entry["fits_bed"] else "OVERSIZE!"
                f.write(f"  {entry['id']}: {entry['extents']}mm "
                        f"({entry['grid']}, {entry['faces']} faces) [{bed_ok}]\n")
            f.write("\n")

        f.write(f"\nPRINT NOTES:\n")
        f.write(f"  - Print each panel FLAT (outer face down on bed)\n")
        f.write(f"  - Print height is wall thickness (~5mm)\n")
        f.write(f"  - Panel ID is engraved on the inner (top) face\n")
        f.write(f"  - Overlap splice: {overlap}mm on all cut edges\n")
        f.write(f"  - Join with solvent weld (ASA) or adhesive (PETG)\n")

    print(f"\n  Assembly map: {map_path}")
    print(f"  Output: {output_dir}")
    print(f"  Total: {total_panels} panels exported")


def main():
    parser = argparse.ArgumentParser(
        description="Split shell STL into flat, bed-sized panels with engraved IDs"
    )
    parser.add_argument("input", help="Input STL file path")
    parser.add_argument("--bed", default="250x220",
                        help="Print bed XY in mm (default: 250x220)")
    parser.add_argument("--overlap", type=float, default=10,
                        help="Overlap splice width in mm (default: 10)")
    parser.add_argument("--prefix", default="S1",
                        help="Panel ID prefix (default: S1)")
    parser.add_argument("--output", default=None,
                        help="Output directory")

    args = parser.parse_args()

    bed_parts = args.bed.lower().split("x")
    bed_x, bed_y = float(bed_parts[0]), float(bed_parts[1])

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}")
        sys.exit(1)

    process_stl(args.input, bed_x=bed_x, bed_y=bed_y,
                overlap=args.overlap, prefix=args.prefix,
                output_dir=args.output)


if __name__ == "__main__":
    main()
