#!/usr/bin/env python3
"""Scale all main unit STLs uniformly for a proof-of-concept mini print."""

import os
import sys
import numpy as np

try:
    import trimesh
except ImportError:
    print("ERROR: trimesh not installed. Run: pip install trimesh")
    sys.exit(1)

STL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_unit", "product stl")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_unit", "poc stl")

FILES = ["Shell 1.stl", "Shell 2.stl", "Cap.stl", "Lid.stl"]

BED_X, BED_Y, BED_Z = 250, 220, 270
MARGIN = 5  # mm margin from bed edges


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Load all meshes and find the max extents across all parts
    meshes = {}
    max_extents = np.zeros(3)

    for fname in FILES:
        path = os.path.join(STL_DIR, fname)
        if not os.path.exists(path):
            print(f"MISSING: {fname}")
            continue
        m = trimesh.load(path)
        if isinstance(m, trimesh.Scene):
            parts = [g for g in m.geometry.values() if isinstance(g, trimesh.Trimesh)]
            m = trimesh.util.concatenate(parts) if parts else None
        if m is None or len(m.faces) == 0:
            print(f"EMPTY: {fname}")
            continue
        meshes[fname] = m
        max_extents = np.maximum(max_extents, m.extents)
        print(f"  {fname}: {m.extents[0]:.1f} x {m.extents[1]:.1f} x {m.extents[2]:.1f} mm")

    if not meshes:
        print("No meshes loaded!")
        return

    print(f"\nMax extents across all parts: {max_extents[0]:.1f} x {max_extents[1]:.1f} x {max_extents[2]:.1f} mm")

    # Compute uniform scale factor so the largest part fits the bed
    usable = np.array([BED_X - MARGIN, BED_Y - MARGIN, BED_Z - MARGIN])
    scale = min(usable / max_extents)
    pct = scale * 100

    print(f"Scale factor: {scale:.4f} ({pct:.1f}%)")
    print(f"Usable bed: {usable[0]} x {usable[1]} x {usable[2]} mm\n")

    for fname, mesh in meshes.items():
        scaled = mesh.copy()
        scaled.apply_scale(scale)

        # Move so min corner is at origin (ready for slicer)
        scaled.apply_translation(-scaled.bounds[0])

        ext = scaled.extents
        out_name = fname.replace(".stl", f" (POC {pct:.0f}pct).stl")
        out_path = os.path.join(OUT_DIR, out_name)
        scaled.export(out_path)

        print(f"  {out_name}: {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm  "
              f"({len(scaled.faces):,} faces)")

    print(f"\nOutput: {OUT_DIR}")
    print(f"All parts scaled to {pct:.1f}% — they will fit together at this scale.")


if __name__ == "__main__":
    main()
