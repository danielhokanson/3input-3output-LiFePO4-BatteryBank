#!/usr/bin/env python3
"""
STL Panel Splitter — Split large STL into bed-sized pieces with overlap splices.

Takes a full-assembly STL, splits it along a grid sized to fit the print bed,
adds overlap extensions at each cut for lap-joint assembly, embosses panel IDs
on inner faces, and exports numbered STL files.

Usage:
    python cad/split_stl.py <input.stl> [--bed 250x220] [--overlap 10] [--prefix S1]

Output:
    cad/panels/<prefix>-01.stl, <prefix>-02.stl, ...
    cad/panels/assembly_map.txt

Bed default: 250x220mm (XY), pieces oriented for printing flat.
"""

import argparse
import math
import os
import sys

import numpy as np

try:
    import trimesh
except ImportError:
    print("ERROR: trimesh not installed. Run: pip install trimesh")
    sys.exit(1)


def compute_cut_planes(mesh_min, mesh_max, bed_x, bed_y, overlap):
    """Compute cut plane positions along X and Y axes.

    Returns lists of X and Y cut positions that divide the mesh
    into pieces fitting within bed_x and bed_y respectively.
    Each piece overlaps its neighbor by `overlap` mm.
    """
    def cuts_for_axis(lo, hi, bed_dim, ovlp):
        span = hi - lo
        if span <= bed_dim:
            return []  # fits in one piece
        # Effective piece size (accounting for overlap on one side)
        step = bed_dim - ovlp
        n_cuts = math.ceil(span / step) - 1
        positions = []
        for i in range(1, n_cuts + 1):
            pos = lo + i * step
            if pos < hi - ovlp:  # don't cut too close to the end
                positions.append(pos)
        return positions

    x_cuts = cuts_for_axis(mesh_min[0], mesh_max[0], bed_x, overlap)
    y_cuts = cuts_for_axis(mesh_min[1], mesh_max[1], bed_y, overlap)

    return x_cuts, y_cuts


def slice_mesh_with_overlap(mesh, axis, position, overlap, keep_positive=True):
    """Slice mesh at position along axis, keeping overlap extension.

    If keep_positive=True, keeps the +side but extends overlap mm into -side.
    If keep_positive=False, keeps the -side but extends overlap mm into +side.
    """
    normal = np.zeros(3)
    point = np.zeros(3)

    if keep_positive:
        # Keep positive side, cut plane faces negative
        normal[axis] = -1.0
        point[axis] = position - overlap
    else:
        # Keep negative side, cut plane faces positive
        normal[axis] = 1.0
        point[axis] = position + overlap

    try:
        result = trimesh.intersections.slice_mesh_plane(
            mesh, plane_normal=normal, plane_origin=point, cached_dots=None
        )
        if result is None or len(result.faces) == 0:
            return None
        return result
    except Exception as e:
        print(f"  Warning: slice failed at axis={axis} pos={position:.1f}: {e}")
        return None


def create_label_mesh(text, position, normal_axis, size=8.0, depth=0.5):
    """Create a simple raised rectangular label at the given position.

    Since generating 3D text meshes is complex, we create a small raised
    rectangle as a visual marker. The panel ID is in the filename.

    For actual text embossing, use Fusion 360 or Blender after splitting.
    """
    # Create a small raised rectangle as alignment/ID marker
    hw = size / 2
    hh = size / 3

    if normal_axis == 0:  # X face
        vertices = np.array([
            [position, -hw, -hh],
            [position, hw, -hh],
            [position, hw, hh],
            [position, -hw, hh],
            [position + depth, -hw, -hh],
            [position + depth, hw, -hh],
            [position + depth, hw, hh],
            [position + depth, -hw, hh],
        ])
    elif normal_axis == 1:  # Y face
        vertices = np.array([
            [-hw, position, -hh],
            [hw, position, -hh],
            [hw, position, hh],
            [-hw, position, hh],
            [-hw, position + depth, -hh],
            [hw, position + depth, -hh],
            [hw, position + depth, hh],
            [-hw, position + depth, hh],
        ])
    else:  # Z face
        vertices = np.array([
            [-hw, -hh, position],
            [hw, -hh, position],
            [hw, hh, position],
            [-hw, hh, position],
            [-hw, -hh, position + depth],
            [hw, -hh, position + depth],
            [hw, hh, position + depth],
            [-hw, hh, position + depth],
        ])

    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # bottom
        [4, 6, 5], [4, 7, 6],  # top
        [0, 4, 5], [0, 5, 1],  # front
        [2, 6, 7], [2, 7, 3],  # back
        [0, 3, 7], [0, 7, 4],  # left
        [1, 5, 6], [1, 6, 2],  # right
    ])

    return trimesh.Trimesh(vertices=vertices, faces=faces)


def split_stl(input_path, bed_x=250, bed_y=220, overlap=10, prefix="S1",
              output_dir=None):
    """Split an STL into bed-sized panels with overlap splices."""

    print(f"Loading: {input_path}")
    mesh = trimesh.load(input_path)

    if isinstance(mesh, trimesh.Scene):
        # Combine all geometries in scene
        meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            print("ERROR: No mesh geometry found in file")
            return
        mesh = trimesh.util.concatenate(meshes)

    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Faces: {len(mesh.faces):,}")
    print(f"  Extents: {mesh.extents[0]:.1f} x {mesh.extents[1]:.1f} x {mesh.extents[2]:.1f} mm")
    print(f"  Watertight: {mesh.is_watertight}")
    print(f"  Bed size: {bed_x} x {bed_y} mm")
    print(f"  Overlap: {overlap} mm")

    bounds_min = mesh.bounds[0]
    bounds_max = mesh.bounds[1]

    # Compute cut planes
    x_cuts, y_cuts = compute_cut_planes(bounds_min, bounds_max, bed_x, bed_y, overlap)

    print(f"\n  X cuts ({len(x_cuts)}): {[f'{c:.1f}' for c in x_cuts]}")
    print(f"  Y cuts ({len(y_cuts)}): {[f'{c:.1f}' for c in y_cuts]}")

    n_x = len(x_cuts) + 1
    n_y = len(y_cuts) + 1
    total = n_x * n_y
    print(f"  Grid: {n_x} x {n_y} = {total} panels")

    # Set up output directory
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(input_path)), "panels")
    os.makedirs(output_dir, exist_ok=True)

    # Define X boundaries for each column
    x_bounds = [bounds_min[0]] + x_cuts + [bounds_max[0]]
    y_bounds = [bounds_min[1]] + y_cuts + [bounds_max[1]]

    assembly_map = []
    panel_num = 0

    for iy in range(n_y):
        for ix in range(n_x):
            panel_num += 1
            panel_id = f"{prefix}-{panel_num:02d}"

            # Start with full mesh, slice down to this cell
            piece = mesh.copy()

            # Cut left boundary (keep right/positive side)
            if ix > 0:
                cut_pos = x_bounds[ix]
                piece = slice_mesh_with_overlap(piece, 0, cut_pos,
                                                 overlap, keep_positive=True)
                if piece is None:
                    print(f"  {panel_id}: empty after X-left cut, skipping")
                    continue

            # Cut right boundary (keep left/negative side)
            if ix < n_x - 1:
                cut_pos = x_bounds[ix + 1]
                piece = slice_mesh_with_overlap(piece, 0, cut_pos,
                                                 overlap, keep_positive=False)
                if piece is None:
                    print(f"  {panel_id}: empty after X-right cut, skipping")
                    continue

            # Cut front boundary (keep back/positive side)
            if iy > 0:
                cut_pos = y_bounds[iy]
                piece = slice_mesh_with_overlap(piece, 1, cut_pos,
                                                 overlap, keep_positive=True)
                if piece is None:
                    print(f"  {panel_id}: empty after Y-front cut, skipping")
                    continue

            # Cut back boundary (keep front/negative side)
            if iy < n_y - 1:
                cut_pos = y_bounds[iy + 1]
                piece = slice_mesh_with_overlap(piece, 1, cut_pos,
                                                 overlap, keep_positive=False)
                if piece is None:
                    print(f"  {panel_id}: empty after Y-back cut, skipping")
                    continue

            if len(piece.faces) == 0:
                print(f"  {panel_id}: no geometry, skipping")
                continue

            # Add a small raised marker nub on the inner face for identification
            # (the panel ID is also in the filename)
            center = piece.centroid
            try:
                marker = create_label_mesh(
                    panel_id,
                    position=center[2],  # Z position (inner face when printing flat)
                    normal_axis=2,
                    size=6.0,
                    depth=0.4
                )
                marker.apply_translation([center[0], center[1], 0])
                piece = trimesh.util.concatenate([piece, marker])
            except Exception:
                pass  # marker is cosmetic, don't fail on it

            # Translate piece so min corner is at origin (for slicer)
            piece.apply_translation(-piece.bounds[0])

            # Export
            ext = piece.extents
            filepath = os.path.join(output_dir, f"{panel_id}.stl")
            piece.export(filepath)

            fits_bed = ext[0] <= bed_x + 1 and ext[1] <= bed_y + 1
            status = "OK" if fits_bed else f"OVERSIZE ({ext[0]:.0f}x{ext[1]:.0f})"

            info = (f"  {panel_id}: {len(piece.faces):,} faces, "
                    f"{ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm  [{status}]")
            print(info)

            assembly_map.append({
                "id": panel_id,
                "file": f"{panel_id}.stl",
                "grid": f"col {ix+1}/{n_x}, row {iy+1}/{n_y}",
                "extents": f"{ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f}",
                "faces": len(piece.faces),
                "x_range": f"{x_bounds[ix]:.1f} to {x_bounds[min(ix+1, n_x-1)]:.1f}",
                "y_range": f"{y_bounds[iy]:.1f} to {y_bounds[min(iy+1, n_y-1)]:.1f}",
                "overlap": f"{overlap}mm on cut edges",
            })

    # Write assembly map
    map_path = os.path.join(output_dir, "assembly_map.txt")
    with open(map_path, "w") as f:
        f.write(f"ASSEMBLY MAP — {prefix}\n")
        f.write(f"Source: {os.path.basename(input_path)}\n")
        f.write(f"Bed: {bed_x} x {bed_y} mm\n")
        f.write(f"Overlap: {overlap} mm (lap joint on all cut edges)\n")
        f.write(f"Grid: {n_x} columns x {n_y} rows = {total} panels\n")
        f.write(f"\nCut positions:\n")
        f.write(f"  X: {[f'{c:.1f}' for c in x_cuts]}\n")
        f.write(f"  Y: {[f'{c:.1f}' for c in y_cuts]}\n")
        f.write(f"\n{'='*60}\n\n")

        # Grid diagram
        f.write("GRID LAYOUT (top view):\n\n")
        for iy in range(n_y):
            row = ""
            for ix in range(n_x):
                idx = iy * n_x + ix + 1
                row += f"  [{prefix}-{idx:02d}]"
            f.write(f"  Row {iy+1}: {row}\n")
        f.write(f"\n{'='*60}\n\n")

        for entry in assembly_map:
            f.write(f"{entry['id']}:\n")
            f.write(f"  File: {entry['file']}\n")
            f.write(f"  Grid position: {entry['grid']}\n")
            f.write(f"  Extents: {entry['extents']} mm\n")
            f.write(f"  Faces: {entry['faces']:,}\n")
            f.write(f"  X range: {entry['x_range']}\n")
            f.write(f"  Y range: {entry['y_range']}\n")
            f.write(f"  Joint: {entry['overlap']}\n")
            f.write(f"\n")

    print(f"\n  Assembly map: {map_path}")
    print(f"  Output dir: {output_dir}")
    print(f"\nDone — {len(assembly_map)} panels exported.")
    print(f"\nAssembly notes:")
    print(f"  - Each cut edge has {overlap}mm overlap extension")
    print(f"  - Lap-joint: sand inner face of overlap zone, solvent-weld (ASA) or epoxy (PETG)")
    print(f"  - Small raised nub on each piece marks the panel (see filename for ID)")
    print(f"  - Print each piece flat (cut face down) for best surface quality")


def main():
    parser = argparse.ArgumentParser(
        description="Split large STL into bed-sized panels with overlap splices"
    )
    parser.add_argument("input", help="Input STL file path")
    parser.add_argument("--bed", default="250x220",
                        help="Print bed XY dimensions in mm (default: 250x220)")
    parser.add_argument("--overlap", type=float, default=10,
                        help="Overlap splice width in mm (default: 10)")
    parser.add_argument("--prefix", default="S1",
                        help="Panel ID prefix (default: S1)")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: <input_dir>/panels/)")

    args = parser.parse_args()

    bed_parts = args.bed.lower().split("x")
    if len(bed_parts) != 2:
        print("ERROR: --bed must be in format WxH, e.g. 250x220")
        sys.exit(1)
    bed_x, bed_y = float(bed_parts[0]), float(bed_parts[1])

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}")
        sys.exit(1)

    split_stl(args.input, bed_x=bed_x, bed_y=bed_y,
              overlap=args.overlap, prefix=args.prefix,
              output_dir=args.output)


if __name__ == "__main__":
    main()
