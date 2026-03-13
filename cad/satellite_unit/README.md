# Satellite Unit — CAD Roughout

Rev 3.2 | Updated 2026-03-12

## Overview

Each **satellite unit** is a self-contained battery expansion pod. It contains
one 4S cell string (4 cells in series) and thermal management only. All power
electronics stay in the main unit. The satellite connects via external leads:

- **Positive lead** (+) — goes to positive expansion bus in main unit
- **Negative lead** (−) — goes to negative expansion bus in main unit
- **BMS sense wire bundle** — 5 wires (4 cell tap + ground) to Smart BMS board
- **Thermal 12V feed** — heater strip + fan power from main unit

## What Goes Inside

| Zone | Contents |
|---|---|
| Battery zone | 4× Narada 105Ah cells (1× 4S string) |
| Battery zone | Compression plates, threaded rod, busbars |
| Thermal zone | 12V heater strip, 80mm fan, STC-1000 thermostat module |
| Conduit sleeve | Leads routed through embedded ASA sleeve to main unit |

**No BMS, no MPPT, no fuses, no distribution bus inside satellite.**

## Cell Layout (4S, 4 cells)

Narada 105Ah measured dimensions: **129 × 36 × 256 mm** (L × W × H) + 4mm terminal protrusion

```
Front view — 4 cells in a row (single 4S string)

  [−][+][−][+]   ← series string, 4 cells

Width:  4 × 36mm + 6mm gaps + 8mm compression = ~158mm
Depth:  1 × 129mm + margins = ~139mm
Height: 256mm cells + 4mm terminals + 30mm busbars = ~290mm
```

Cells compressed with threaded rod through aluminium compression plates.
BMS sense wires tap each cell terminal for SoC/cell-balance monitoring.

## Thermal Zone

```
  [CELLS][CELLS][CELLS][CELLS] | THERM ZONE
                                 ┌──────────┐
                                 │  FAN →   │
                                 │  HEATER  │
                                 │  THERM   │
                                 └──────────┘
```

- 80mm 12V fan (push/pull on end wall)
- Self-adhesive 24V silicone heater pad (via 12V→24V boost converter)
- STC-1000 thermostat module (controls heater + fan)
- Operating range: −26°C to +60°C

## Enclosure Dimensions (derived)

All values in mm. Shell 1 wall = 5mm, Shell 2 wall = 5mm, Foam = 30mm.
Two-shell construction: Shell 1 (ASA outer) + foam + Shell 2 (PETG structural/inner).
Shell 2 serves as both structural shell and direct inner container for components.

| Shell | Material | Wall | W × D × H |
|---|---|---|---|
| Shell 2 (structural/inner) | PETG | 5mm | 273 × 169 × 300 |
| Shell 1 (outer/boulder) | ASA | 5mm | 343 × 239 × 340 |
| Cap rim | ASA | — | 363 × 259 × 8 |
| Lid | ASA | — | 393 × 289 × 25 |

> Dimensions based on measured Narada 105Ah cells (129×36×256mm + 4mm terminals).

## Two-Shell Build

- **Shell 1 (ASA):** Outdoor UV-stable boulder aesthetic, 5mm wall
- **Shell 2 (PETG):** Structural shell, 5mm wall, direct inner container
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

## Integrated Spacers

Instead of separate spacer pieces, extrude standoff nubs directly from each
shell body into the foam gap. Shell 1 nubs point inward; Shell 2 nubs point
outward. They meet in the middle (~15mm each) to hold the 30mm gap during
the foam pour.

- Extrude from shell inner/outer faces at corner and mid-wall positions
- Same positions as the legacy spacer plan (4 corners + mid-walls, 2 vertical levels)
- No separate parts to align or slip during pour
- Foam bonds around and between nubs

## Conduit Penetrations (Right Face)

| Conduit | Size | Count | Purpose |
|---|---|---|---|
| Battery leads | 16mm | 1 | Bundle: +/− power leads + BMS sense wires |
| Thermal 12V feed | 10mm | 1 | Heater + fan power from main unit |
| Thermostat probe | 8mm | 1 | External temperature probe |

### Conduit Sleeves

Each conduit hole gets a **5mm-wall tube** extruded from Shell 1 inward (or Shell 2
outward) spanning the ~30mm foam gap. This prevents foam from filling the conduit
openings during the pour.

- Sleeve OD = conduit ID + 2×5mm wall (e.g., 10mm conduit → 20mm OD sleeve)
- Sleeve length = foam gap (~30mm)
- Extrude as Fusion boss from the conduit hole perimeter
- Shell 1 and Shell 2 sleeves meet or overlap in the foam zone

Route satellite leads through conduit to the main unit's terminal block.

## Aesthetic

Boulder style matching main unit. ASA Shell 1 provides UV and thermal resistance.
Scale is intentionally compact vs the main unit.

## Foam Cavity Spacers (Legacy — see Integrated Spacers)

Spacers bridge the 30mm foam gap between Shell 1 and Shell 2, keeping
Shell 2 centered during the PU foam pour and preventing wall distortion.

| Type | Dimensions | Qty | Features |
|---|---|---|---|
| Corner spacer | L-shape 25×25×25mm, wall 12mm | 8 (4 corners × 2 levels) | M4 through-bolt clamp hole |
| Mid-wall spacer | 25×30×25mm block | 12 (6 positions × 2 levels) | Friction fit, foam bonds around |

Placed at two vertical levels (Z1 ≈ 90mm, Z2 ≈ 196mm from Shell 2 base).
Material: PETG. Corner spacers accept M4 bolts for clamping during pour.

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
on each panel body after Split Body.

## Panel Identification

Each panel gets a 0.5mm raised ID embossed on its **inner face** during Fusion modeling.
This prevents mix-ups during assembly of 28 panels.

**Format:** `S{shell}-{face}-{##}`

| Code | Meaning |
|---|---|
| `S1` / `S2` | Shell number |
| `F` / `B` / `L` / `R` / `T` | Face: Front, Back, Left, Right, Top |
| `01`–`99` | Sequential panel number within that face |

**Examples:** `S1-F-01`, `S1-L-02`, `S2-R-03`, `S2-T-01`

**Fusion steps:**
1. After Split Body, select each panel's inner face
2. Create Sketch > Text (monospace font, ~8mm height)
3. Extrude text **0.5mm outward** from inner surface (Join to panel body)
4. Inner face placement keeps IDs hidden from exterior boulder surface

## Running the Scripts

```bash
cd cad/satellite_unit

# DXF profiles for Fusion import (9 drawings)
python generate_dxf.py

# Split guide SVGs
python generate_panels.py

# Spacer drawings (DXF + SVG) — legacy, see Integrated Spacers
python generate_spacers.py
```

Outputs go to `cad/satellite_unit/dxf/`, `cad/satellite_unit/guides/`, and `cad/satellite_unit/spacers/`.

## Fusion Workflow

1. Import DXFs via **Insert > Insert DXF** onto appropriate sketch planes
2. Extrude to build monolithic shell bodies
3. Apply **Modify > Shell** command (Shell 1: 5mm wall, Shell 2: 5mm wall)
4. Add foam-pressure ribs (Extrude from inner/outer faces into foam cavity)
5. Add integrated spacer nubs (Extrude standoffs at corner/mid-wall positions)
6. Add conduit sleeves (Extrude 5mm-wall tubes around conduit holes, spanning foam gap)
7. Cut conduit holes (Extrude > Cut), positions per `4_lead_exit_view.dxf`
8. Import split guides → create construction planes → **Modify > Split Body**
9. Add finger joints on each split face
10. Apply fillets (Shell 1: R8, Shell 2: R5) and chamfers (lid: 3mm)
11. Emboss panel IDs on inner faces (0.5mm raised text, see Panel Identification above)
12. Export panels as STL for Prusa Core One printing

## Expansion

Each satellite adds one 4S parallel string. Connect up to 4 satellites to
the main unit for 4S6P total (24 cells, ~6,450 Wh usable). BMS sense wire
bundles extend to each satellite unit's cell taps. Current satellites planned:

| Unit | Cells | Config | Location |
|---|---|---|---|
| Main unit | 8 | 4S2P | Main enclosure |
| Satellite 1 | 4 | +4S string | Adjacent to main |
| Satellite 2–4 | 4 each | +4S string | Future expansion |
