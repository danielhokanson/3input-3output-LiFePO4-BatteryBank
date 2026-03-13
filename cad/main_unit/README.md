# Main Unit — CAD Roughout

Rev 3.2 | Updated 2026-03-12

## Overview

The **main unit** is the central control enclosure. It houses all power electronics
and the initial 4S2P cell bank (8 cells). Satellite units connect to it via external
leads and share the same BMS sense wires.

## What Goes Inside

| Zone | Contents |
|---|---|
| Battery zone | 8× Narada 105Ah cells (4S2P) — expandable via satellites |
| Electronics zone | 4× EPever Tracer 2210AN MPPT, 2× 4S 100A Smart BMS |
| Electronics zone | LEM HASS 100-S current sensor, distribution bus bars |
| Electronics zone | 2× 60A ATC fuse holder, terminal blocks, MC4 combiner |
| Thermal zone | 12V heater element, 120mm fan, STC-1000 thermostat |

## Cell Layout (4S2P, 8 cells)

Narada 105Ah measured dimensions: **129 × 36 × 256 mm** (L × W × H) + 4mm terminal protrusion

```
Front view — 4 cells across (series), 2 rows deep (parallel)

  [−][+][−][+]  ← row 1 (parallel string A)
  [−][+][−][+]  ← row 2 (parallel string B)

Width:  4 × 36mm + 6mm gaps + 8mm compression = ~158mm
Depth:  2 × 129mm + 10mm gap = ~268mm
Height: 256mm cells + 4mm terminals + 30mm busbars = ~290mm
```

Cells must be compressed: use threaded rod through compression plates
at each end of the 4-cell series stack.

## Electronics Zone Layout

```
┌──────────────────────────────────────────────────┐
│  [MPPT1]   [MPPT2]   │  Bus bar / fuses          │
│  [MPPT3]   [MPPT4]   │  2× BMS                   │
│  ← DIN rail ──────── │  Sensor / terminal blocks  │
│  Bottom: cable mgmt  │                             │
└──────────────────────────────────────────────────┘
```

EPever Tracer 2210AN: ~186 × 76 × 47 mm each.
2×2 grid on vertical mounting panel with 50mm clearance above each unit.

## Enclosure Dimensions (derived)

All values in mm. Shell 1 wall = 5mm, Shell 2 wall = 5mm, Foam = 30mm.

| Shell | Material | Wall | W × D × H |
|---|---|---|---|
| Interior space | — | — | 518 × 288 × 317 |
| Shell 2 (structural) | PETG | 5mm | 528 × 298 × 322 |
| Shell 1 (outer/boulder) | ASA | 5mm | 598 × 368 × 362 |
| Cap rim | ASA | — | 618 × 388 × 8 |
| Lid | ASA | — | 648 × 418 × 25 |

> Dimensions based on measured Narada 105Ah cells (129×36×256mm + 4mm terminals).

## Two-Shell Build

- **Shell 1 (ASA):** Outdoor UV-stable boulder aesthetic, 5mm wall, foam-bonded
- **Shell 2 (PETG):** Structural shell, 5mm wall, direct inner container for components
- **Foam:** 30mm PU two-part pour between Shell 1 and Shell 2
- **Cap rim:** Spans both shells; outer lip over S1, flange into foam zone, inner lip into S2; dual gaskets + M4 bolts
- **Lid:** 25mm thick ASA (20% infill = insulation), 20mm rain skirt with drip edge, bolts through cap rim

## Lid Design

The lid has no foam backing, so its thickness provides insulation via trapped air in
the infill pattern. Print at **20% infill** for optimal insulation-to-weight ratio.

| Parameter | Value |
|---|---|
| Lid thickness | 25mm (infill = insulation) |
| Lid overhang | 15mm beyond cap rim |
| Rain skirt | 20mm drop with drip edge groove |
| Drip edge | 3mm inset, 3mm deep, 2mm wide groove |
| Bolt pattern | Through-holes matching cap M4 pattern |
| Material | ASA (UV-stable, same as Shell 1) |

Shown in DXF Drawings 2, 3 (cross-sections), 8 (cap+lid profile), 9 (lid top view).

## Foam-Pressure Ribs

Ribs protrude into the foam cavity from Shell 1's inner surface and Shell 2's
outer surface. They interlock with cured foam to resist hydrostatic pressure
during the pour and improve long-term mechanical bond.

| Parameter | Value |
|---|---|
| Rib width | 3mm (along wall surface) |
| Rib height | 10mm (protrusion into foam cavity) |
| Rib spacing | 100mm center-to-center |
| First rib | ~50mm from base |
| Shown in | DXF Drawings 2 (front) and 3 (side) cross-sections |

Add ribs in Fusion as extruded features on the inner face of Shell 1 and
outer face of Shell 2 before the foam pour. Ribs do not change the 30mm
foam gap parameter -- they protrude into it.

## Integrated Spacers

Instead of separate spacer pieces, extrude standoff nubs directly from each
shell body into the foam gap. Shell 1 nubs point inward; Shell 2 nubs point
outward. They meet in the middle (~15mm each) to hold the 30mm gap during
the foam pour.

- Extrude from shell inner/outer faces at corner and mid-wall positions
- Same positions as the legacy spacer plan (4 corners + mid-walls, 2 vertical levels)
- No separate parts to align or slip during pour
- Foam bonds around and between nubs

## Conduit Penetrations (Rear Face)

| Conduit | Size | Count | Purpose |
|---|---|---|---|
| Solar MC4 pairs | 12mm | 4 | One per MPPT (3× Solariver + 1× Renogy) |
| Satellite leads | 16mm | 4 | One per satellite unit (future expansion) |
| Pump output | 10mm | 3 | 12V pump power (3× Solariver pumps) |
| Thermostat probe | 8mm | 1 | External temperature probe |
| Ethernet/comms | 8mm | 1 | Future monitoring |

### Conduit Sleeves

Each conduit hole gets a **5mm-wall tube** extruded from Shell 1 inward (or Shell 2
outward) spanning the ~30mm foam gap. This prevents foam from filling the conduit
openings during the pour.

- Sleeve OD = conduit ID + 2×5mm wall (e.g., 10mm conduit → 20mm OD sleeve)
- Sleeve length = foam gap (~30mm)
- Extrude as Fusion boss from the conduit hole perimeter
- Shell 1 and Shell 2 sleeves meet or overlap in the foam zone

## Foam Cavity Spacers (Legacy — see Integrated Spacers)

Spacers bridge the 30mm foam gap between Shell 1 and Shell 2, keeping
Shell 2 centered during the PU foam pour and preventing wall distortion.

| Type | Dimensions | Qty | Features |
|---|---|---|---|
| Corner spacer | L-shape 30×30×25mm, wall 12mm | 8 (4 corners × 2 levels) | M4 through-bolt clamp hole |
| Mid-wall spacer | 30×30×25mm block | 20 (10 positions × 2 levels) | Friction fit, foam bonds around |

Placed at two vertical levels (Z1 ≈ 90mm, Z2 ≈ 196mm from Shell 2 base).
Material: PETG (same as Shell 2). Corner spacers accept M4 bolts through
Shell 1 + spacer + Shell 2 for clamping during pour — remove or cap after cure.

> **Note:** Integrated spacers (extruded from shell bodies) are preferred over
> separate spacer pieces. The legacy spacer scripts are retained for reference.

## Fillet / Chamfer

Edge treatments applied in Fusion after panel splitting:

| Edge | Treatment | Size |
|---|---|---|
| Shell 1 outer edges | Fillet (rounded) | R = 8mm |
| Shell 2 inner edges | Fillet (stress relief) | R = 5mm |
| Lid top edges | 45° chamfer | 3mm |

Apply fillets/chamfers in Fusion using **Modify > Fillet** or **Modify > Chamfer**
on each panel body after Split Body. This softens the boulder aesthetic and
improves printability (reduces overhang stress).

## Running the Scripts

```bash
cd cad/main_unit

# DXF profiles for Fusion import (9 drawings)
python generate_dxf.py

# Split guide SVGs (construction plane positions)
python generate_panels.py

# Spacer drawings (DXF + SVG) — legacy, see Integrated Spacers
python generate_spacers.py
```

Outputs go to `cad/main_unit/dxf/`, `cad/main_unit/guides/`, and `cad/main_unit/spacers/`.

## Panel Identification

Each panel gets a 0.5mm raised ID embossed on its **inner face** during Fusion modeling.
This prevents mix-ups during assembly of 52 panels.

**Format:** `S{shell}-{face}-{##}`

| Code | Meaning |
|---|---|
| `S1` / `S2` | Shell number |
| `F` / `B` / `L` / `R` / `T` | Face: Front, Back, Left, Right, Top |
| `01`–`99` | Sequential panel number within that face |

**Examples:** `S1-F-01`, `S1-R-03`, `S2-B-02`, `S2-T-01`

**Fusion steps:**
1. After Split Body, select each panel's inner face
2. Create Sketch > Text (monospace font, ~8mm height)
3. Extrude text **0.5mm outward** from inner surface (Join to panel body)
4. Inner face placement keeps IDs hidden from exterior boulder surface

## Fusion Workflow

1. Import DXFs via **Insert > Insert DXF** onto appropriate sketch planes
2. Extrude to build monolithic shell bodies
3. Apply **Modify > Shell** command (Shell 1: 5mm wall, Shell 2: 5mm wall)
4. Add foam-pressure ribs (Extrude from inner/outer faces into foam cavity)
5. Add integrated spacer nubs (Extrude standoffs at corner/mid-wall positions)
6. Add conduit sleeves (Extrude 5mm-wall tubes around conduit holes, spanning foam gap)
7. Cut conduit holes (Extrude > Cut), positions per `4_rear_view.dxf`
8. Import split guides → create construction planes → **Modify > Split Body**
9. Add finger joints on each split face
10. Apply fillets (Shell 1: R8, Shell 2: R5) and chamfers (lid: 3mm)
11. Emboss panel IDs on inner faces (0.5mm raised text, see Panel Identification above)
12. Export panels as STL for Prusa Core One printing
