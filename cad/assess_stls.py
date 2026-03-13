#!/usr/bin/env python3
"""Assess all product STL files for mesh quality and dimensional accuracy."""

import trimesh
import numpy as np
import os
from collections import Counter

STL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_unit", "product stl")

FILES = ["Shell 1.stl", "Shell 2.stl", "Cap.stl", "Lid.stl"]

EXPECTED = {
    "Shell 1.stl": {"W": 598, "D": 368, "H": 362, "desc": "ASA outer shell (5mm wall)"},
    "Shell 2.stl": {"W": 528, "D": 298, "H": 322, "desc": "PETG structural shell (5mm wall)"},
    "Cap.stl":     {"W": 598, "D": 368, "H": None, "desc": "Cap rim (8mm thick + flanges)"},
    "Lid.stl":     {"W": 628, "D": 398, "H": 45,  "desc": "Lid (25mm body + 20mm skirt)"},
}

BED_X, BED_Y, BED_Z = 250, 220, 270


def assess_mesh(fname, mesh, exp):
    ext = mesh.extents
    bounds = mesh.bounds

    print("=" * 70)
    print(f"{fname} -- {exp['desc']}")
    print("=" * 70)
    print(f"  File size:   {os.path.getsize(os.path.join(STL_DIR, fname)):,} bytes")
    print(f"  Vertices:    {len(mesh.vertices):,}")
    print(f"  Faces:       {len(mesh.faces):,}")
    print(f"  Watertight:  {mesh.is_watertight}")

    if mesh.is_watertight:
        vol = mesh.volume / 1000.0
        print(f"  Volume:      {vol:.1f} cm3")
    else:
        print(f"  Volume:      N/A (NOT WATERTIGHT - mesh has holes!)")

    print(f"  Bounds min:  [{bounds[0][0]:.2f}, {bounds[0][1]:.2f}, {bounds[0][2]:.2f}]")
    print(f"  Bounds max:  [{bounds[1][0]:.2f}, {bounds[1][1]:.2f}, {bounds[1][2]:.2f}]")
    print(f"  Extents:     {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} mm")
    print()

    # Dimension check
    issues = []
    print("  DIMENSION CHECK:")
    if exp["W"] is not None:
        dx = abs(ext[0] - exp["W"])
        ok = "OK" if dx < 2 else f"MISMATCH (off by {dx:.1f}mm!)"
        if dx >= 2:
            issues.append(f"Width {ext[0]:.1f} != expected {exp['W']}")
        print(f"    Width:  {ext[0]:.1f}mm  (expected {exp['W']}mm)  {ok}")
    if exp["D"] is not None:
        dy = abs(ext[1] - exp["D"])
        ok = "OK" if dy < 2 else f"MISMATCH (off by {dy:.1f}mm!)"
        if dy >= 2:
            issues.append(f"Depth {ext[1]:.1f} != expected {exp['D']}")
        print(f"    Depth:  {ext[1]:.1f}mm  (expected {exp['D']}mm)  {ok}")
    if exp["H"] is not None:
        dz = abs(ext[2] - exp["H"])
        ok = "OK" if dz < 2 else f"MISMATCH (off by {dz:.1f}mm!)"
        if dz >= 2:
            issues.append(f"Height {ext[2]:.1f} != expected {exp['H']}")
        print(f"    Height: {ext[2]:.1f}mm  (expected {exp['H']}mm)  {ok}")
    print()

    # Mesh quality
    print("  MESH QUALITY:")

    # Degenerate faces
    areas = mesh.area_faces
    degen = int(np.sum(areas < 1e-8))
    print(f"    Degenerate faces (zero area): {degen}  {'OK' if degen == 0 else 'WARNING'}")
    if degen > 0:
        issues.append(f"{degen} degenerate faces")

    # Edge analysis
    edge_face_count = Counter()
    for face in mesh.faces:
        for i in range(3):
            e = tuple(sorted([face[i], face[(i + 1) % 3]]))
            edge_face_count[e] += 1
    boundary = sum(1 for c in edge_face_count.values() if c == 1)
    non_manifold = sum(1 for c in edge_face_count.values() if c > 2)
    print(f"    Boundary edges (holes): {boundary}  {'OK' if boundary == 0 else 'WARNING - open edges!'}")
    print(f"    Non-manifold edges: {non_manifold}  {'OK' if non_manifold == 0 else 'WARNING'}")
    if boundary > 0:
        issues.append(f"{boundary} boundary edges (mesh has holes)")
    if non_manifold > 0:
        issues.append(f"{non_manifold} non-manifold edges")

    # Normals
    if mesh.is_watertight:
        print(f"    Normals: consistent (watertight)")
    else:
        print(f"    Normals: CANNOT VERIFY (not watertight)")

    # Origin check
    center = (bounds[0] + bounds[1]) / 2
    print(f"    Center: [{center[0]:.1f}, {center[1]:.1f}, {center[2]:.1f}]")
    if abs(center[0]) < 5 and abs(center[1]) < 5:
        print(f"    Origin: centered XY")
    else:
        print(f"    Origin: offset from center by [{center[0]:.1f}, {center[1]:.1f}]")

    # Print bed fit
    print(f"\n  PRINT BED FIT ({BED_X}x{BED_Y}x{BED_Z}mm):")
    if ext[0] <= BED_X and ext[1] <= BED_Y:
        print(f"    Flat (XY): FITS")
    else:
        nx = max(1, int(np.ceil(ext[0] / (BED_X - 10))))
        ny = max(1, int(np.ceil(ext[1] / (BED_Y - 10))))
        print(f"    Flat (XY): NEEDS SPLIT ~{nx}x{ny} = {nx * ny} pieces")
    if ext[2] <= BED_Z:
        print(f"    Z height: OK ({ext[2]:.0f}mm <= {BED_Z}mm)")
    else:
        print(f"    Z height: EXCEEDS {BED_Z}mm! ({ext[2]:.0f}mm) -- needs Z cuts or sideways print")
        issues.append(f"Height {ext[2]:.0f}mm exceeds bed Z {BED_Z}mm")

    if issues:
        print(f"\n  ** ISSUES ({len(issues)}):")
        for iss in issues:
            print(f"    - {iss}")
    else:
        print(f"\n  ** NO ISSUES FOUND")
    print()

    return issues


def cross_checks(results):
    print("=" * 70)
    print("CROSS-COMPONENT CHECKS")
    print("=" * 70)

    all_issues = []

    if "Shell 1.stl" in results and "Shell 2.stl" in results:
        s1 = results["Shell 1.stl"]
        s2 = results["Shell 2.stl"]
        gap_x = (s1.extents[0] - s2.extents[0]) / 2
        gap_y = (s1.extents[1] - s2.extents[1]) / 2
        gap_z = s1.extents[2] - s2.extents[2]
        print(f"\n  Shell 1 -> Shell 2 gap (expect ~35mm = 5mm wall + 30mm foam):")
        ok_x = "OK" if abs(gap_x - 35) < 2 else f"EXPECTED 35mm!"
        ok_y = "OK" if abs(gap_y - 35) < 2 else f"EXPECTED 35mm!"
        print(f"    X gap per side: {gap_x:.1f}mm  {ok_x}")
        print(f"    Y gap per side: {gap_y:.1f}mm  {ok_y}")
        print(f"    Z gap (top):    {gap_z:.1f}mm")
        if abs(gap_x - 35) >= 2:
            all_issues.append(f"S1-S2 X gap is {gap_x:.1f}mm, expected 35mm")
        if abs(gap_y - 35) >= 2:
            all_issues.append(f"S1-S2 Y gap is {gap_y:.1f}mm, expected 35mm")

    if "Cap.stl" in results and "Shell 1.stl" in results:
        cap = results["Cap.stl"]
        s1 = results["Shell 1.stl"]
        print(f"\n  Cap vs Shell 1 (cap should match S1 outer width/depth):")
        cw = abs(cap.extents[0] - s1.extents[0])
        cd = abs(cap.extents[1] - s1.extents[1])
        print(f"    Width: cap {cap.extents[0]:.1f} vs S1 {s1.extents[0]:.1f}  (diff {cw:.1f}mm)  {'OK' if cw < 2 else 'MISMATCH!'}")
        print(f"    Depth: cap {cap.extents[1]:.1f} vs S1 {s1.extents[1]:.1f}  (diff {cd:.1f}mm)  {'OK' if cd < 2 else 'MISMATCH!'}")
        if cw >= 2:
            all_issues.append(f"Cap width {cap.extents[0]:.1f} != S1 width {s1.extents[0]:.1f}")
        if cd >= 2:
            all_issues.append(f"Cap depth {cap.extents[1]:.1f} != S1 depth {s1.extents[1]:.1f}")

    if "Lid.stl" in results and "Cap.stl" in results:
        lid = results["Lid.stl"]
        cap = results["Cap.stl"]
        oh_x = (lid.extents[0] - cap.extents[0]) / 2
        oh_y = (lid.extents[1] - cap.extents[1]) / 2
        print(f"\n  Lid overhang beyond cap (expect ~15mm per side):")
        print(f"    X overhang: {oh_x:.1f}mm  {'OK' if abs(oh_x - 15) < 2 else 'EXPECTED 15mm!'}")
        print(f"    Y overhang: {oh_y:.1f}mm  {'OK' if abs(oh_y - 15) < 2 else 'EXPECTED 15mm!'}")
        if abs(oh_x - 15) >= 2:
            all_issues.append(f"Lid X overhang is {oh_x:.1f}mm, expected 15mm")
        if abs(oh_y - 15) >= 2:
            all_issues.append(f"Lid Y overhang is {oh_y:.1f}mm, expected 15mm")

    if "Cap.stl" in results and "Lid.stl" in results:
        cap = results["Cap.stl"]
        lid = results["Lid.stl"]
        cap_top = cap.bounds[1][2]
        lid_bot = lid.bounds[0][2]
        print(f"\n  Vertical alignment:")
        print(f"    Cap top Z:    {cap_top:.1f}mm")
        print(f"    Lid bottom Z: {lid_bot:.1f}mm")
        gap = lid_bot - cap_top
        print(f"    Gap: {gap:.1f}mm  {'OK (flush)' if abs(gap) < 1 else 'WARNING - not aligned!'}")
        if abs(gap) >= 1:
            all_issues.append(f"Cap-Lid Z gap is {gap:.1f}mm (should be 0)")

    if "Shell 1.stl" in results and "Cap.stl" in results:
        s1 = results["Shell 1.stl"]
        cap = results["Cap.stl"]
        s1_top = s1.bounds[1][2]
        cap_bot = cap.bounds[0][2]
        print(f"\n  Shell 1 top vs Cap bottom:")
        print(f"    S1 top Z:    {s1_top:.1f}mm")
        print(f"    Cap bottom Z: {cap_bot:.1f}mm")
        overlap = s1_top - cap_bot
        print(f"    Overlap: {overlap:.1f}mm  (cap should overlap S1 top)")

    if "Shell 2.stl" in results:
        s2 = results["Shell 2.stl"]
        s2_top = s2.bounds[1][2]
        s2_bot = s2.bounds[0][2]
        print(f"\n  Shell 2 position:")
        print(f"    S2 bottom Z: {s2_bot:.1f}mm  (expect ~{5 + 30:.0f}mm = S1 base + foam)")
        print(f"    S2 top Z:    {s2_top:.1f}mm")
        if abs(s2_bot - 35) >= 3:
            all_issues.append(f"S2 bottom at Z={s2_bot:.1f}, expected ~35mm")

    return all_issues


def main():
    print("STL ASSESSMENT -- Main Unit Components")
    print(f"Directory: {STL_DIR}")
    print()

    results = {}
    all_issues = []

    for fname in FILES:
        path = os.path.join(STL_DIR, fname)
        if not os.path.exists(path):
            print(f"MISSING: {fname}")
            all_issues.append(f"File missing: {fname}")
            continue

        m = trimesh.load(path)
        if isinstance(m, trimesh.Scene):
            meshes = [g for g in m.geometry.values() if isinstance(g, trimesh.Trimesh)]
            m = trimesh.util.concatenate(meshes) if meshes else None

        if m is None or len(m.faces) == 0:
            print(f"ERROR: {fname} has no geometry")
            all_issues.append(f"No geometry: {fname}")
            continue

        issues = assess_mesh(fname, m, EXPECTED[fname])
        all_issues.extend([(fname, i) for i in issues])
        results[fname] = m

    # Cross-component checks
    xissues = cross_checks(results)
    all_issues.extend([("CROSS", i) for i in xissues])

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if all_issues:
        print(f"\n  TOTAL ISSUES: {len(all_issues)}")
        for source, issue in all_issues:
            if isinstance(source, tuple):
                print(f"    [{source}] {issue}")
            else:
                print(f"    [{source}] {issue}")
    else:
        print("\n  ALL CHECKS PASSED -- ready for splitting!")


if __name__ == "__main__":
    main()
