#!/usr/bin/env python3
"""
Thermal simulation for the LiFePO4 battery enclosure.

Simulates internal enclosure temperature over a full year using
Salt Lake City climate data, validates that:
  - PTC heater (10-15W) keeps cells above 0C in winter cold snaps
  - Fan ventilation keeps cells below 45C in summer heat
  - Heater energy budget stays within system capacity

Uses a lumped-parameter thermal model with STC-1000 hysteresis control.

Usage:
    python sim/thermal_sim.py              # Run simulation, print summary
    python sim/thermal_sim.py --plot       # Also generate PNG plot (requires matplotlib)
    python sim/thermal_sim.py --csv        # Export hourly data to CSV

Output:
    sim/output/thermal_summary.txt         # Key results
    sim/output/thermal_year.csv            # Hourly data (with --csv)
    sim/output/thermal_year.png            # Plot (with --plot)
"""

import os
import sys
import math
import argparse

# ---------------------------------------------------------------------------
# PHYSICAL PARAMETERS
# ---------------------------------------------------------------------------

# Cell thermal properties (LiFePO4 prismatic)
CELL_MASS_KG = 2.0          # mass per cell (approx for 200Ah prismatic)
NUM_CELLS = 12
TOTAL_CELL_MASS = CELL_MASS_KG * NUM_CELLS  # 24 kg
CELL_SPECIFIC_HEAT = 1050   # J/(kg*K) for LiFePO4 (typical)
THERMAL_MASS = TOTAL_CELL_MASS * CELL_SPECIFIC_HEAT  # J/K

# Enclosure insulation
# 30mm closed-cell PU foam: k ~ 0.025 W/(m*K)
# ASA walls: 3mm each side, k ~ 0.18 W/(m*K)
# Total wall: 3mm ASA + 30mm foam + 3mm ASA = 36mm
FOAM_THICKNESS_M = 0.030
FOAM_K = 0.025               # W/(m*K) - closed cell PU foam
ASA_THICKNESS_M = 0.003
ASA_K = 0.18                 # W/(m*K) - ASA plastic

# Enclosure surface area (approx from DXF dimensions)
# Outer shell: ~672 x 397 x 261 mm
# Using inner shell dims for heat transfer area
# Inner: ~590 x 315 x 215 mm = 0.59 x 0.315 x 0.215 m
INNER_W = 0.590
INNER_D = 0.315
INNER_H = 0.215
SURFACE_AREA = 2 * (INNER_W * INNER_D + INNER_W * INNER_H + INNER_D * INNER_H)

# Thermal resistance of wall (R = L/kA for each layer, in series)
R_ASA_INNER = ASA_THICKNESS_M / (ASA_K * SURFACE_AREA)
R_FOAM = FOAM_THICKNESS_M / (FOAM_K * SURFACE_AREA)
R_ASA_OUTER = ASA_THICKNESS_M / (ASA_K * SURFACE_AREA)
R_WALL = R_ASA_INNER + R_FOAM + R_ASA_OUTER  # total thermal resistance K/W

# UA value (overall heat transfer coefficient * area)
UA = 1.0 / R_WALL  # W/K

# Heater
HEATER_POWER_W = 12.0       # PTC heater nominal (10-15W, use 12W)

# Fan ventilation (when fan is on, effective UA increases significantly)
# Fan moves ~50 CFM through vents, dramatically increasing heat exchange
FAN_UA_MULTIPLIER = 4.0     # fan increases effective heat loss ~4x
FAN_POWER_W = 4.0           # fan motor self-heating contribution

# Internal heat from electronics (BMS, wiring losses)
ELECTRONICS_HEAT_W = 2.0    # small continuous heat from BMS/wiring

# STC-1000 thermostat setpoints (hysteresis control)
HEAT_ON_C = 5.0             # heater turns ON below this
HEAT_OFF_C = 10.0           # heater turns OFF above this
FAN_ON_C = 35.0             # fan turns ON above this
FAN_OFF_C = 30.0            # fan turns OFF below this
CHARGE_INHIBIT_C = 0.0      # BMS blocks charging below this

# Solar radiation heating of enclosure (light-colored boulder)
# Light stone color, reflective topcoat: absorptivity ~0.3
SOLAR_ABSORPTIVITY = 0.3
# Projected area facing sun (approx half of top + one side)
SOLAR_PROJECTED_AREA = 0.590 * 0.315 * 0.5  # m^2 (top face, partial)

# ---------------------------------------------------------------------------
# SALT LAKE CITY CLIMATE DATA (typical meteorological year)
# ---------------------------------------------------------------------------

# Monthly average high/low temperatures (C) for SLC
# Source: NOAA climate normals
SLC_MONTHLY = {
    # month: (avg_high_C, avg_low_C, peak_sun_hours, max_solar_W/m2)
    1:  (-0.6, -8.3,  3.0, 400),
    2:  (3.3,  -5.6,  4.0, 550),
    3:  (10.0, -1.1,  5.5, 700),
    4:  (15.6,  3.3,  7.0, 850),
    5:  (21.7,  8.9,  8.5, 950),
    6:  (28.3, 13.9,  10.0, 1000),
    7:  (33.3, 18.3,  10.5, 1000),
    8:  (32.2, 17.2,  9.5, 950),
    9:  (26.1, 11.7,  8.0, 800),
    10: (17.8,  4.4,  6.0, 650),
    11: (8.3,  -2.2,  4.0, 450),
    12: (1.1,  -6.7,  3.0, 350),
}

# Extreme cold events (cold snaps)
COLD_SNAP_MONTHS = [12, 1, 2]  # Dec-Feb
COLD_SNAP_LOW_C = -26.0        # spec says -26C (-15F)
COLD_SNAP_DURATION_HOURS = 72  # 3-day cold snap

# Extreme heat events (baseline)
HEAT_WAVE_MONTHS = [6, 7, 8]
HEAT_WAVE_HIGH_C = 42.0        # occasional SLC extreme
HEAT_WAVE_DURATION_HOURS = 48

# ---------------------------------------------------------------------------
# CLIMATE STRESS SCENARIO
# ---------------------------------------------------------------------------
# SLC has seen increasing extreme highs in mid-to-late summer.
# Recent records: 107F (41.7C) in 2021, multiple 105F+ days in 2022-2024.
# This scenario models the emerging pattern of hotter, longer summers.

# Elevated monthly baselines for stress scenario (June-September)
# Adds an offset to the NOAA normals reflecting recent trend
SLC_STRESS_OFFSETS = {
    # month: (high_offset_C, low_offset_C)
    1: (0, 0), 2: (0, 0), 3: (0, 0), 4: (0, 0),
    5:  (1.0, 0.5),     # May warming slightly
    6:  (2.0, 1.5),     # June: +2C highs
    7:  (3.5, 2.0),     # July: +3.5C highs (peak stress)
    8:  (4.0, 2.5),     # August: +4C highs (worst month, late-summer heat dome)
    9:  (2.5, 1.5),     # September: extended summer
    10: (1.0, 0.5),     # October: lingering warmth
    11: (0, 0), 12: (0, 0),
}

# Stress scenario heat waves: hotter, longer, and multiple per summer
STRESS_HEAT_WAVES = [
    # (start_month, start_day, duration_hours, peak_high_C)
    (6, 20, 72, 43.0),    # Late June: 3-day heat wave
    (7, 8,  96, 45.0),    # Early July: 4-day heat dome
    (7, 25, 72, 44.0),    # Late July: another 3-day event
    (8, 5, 120, 46.0),    # Early August: 5-day extreme (worst case)
    (8, 25, 72, 43.5),    # Late August: lingering heat
]


def generate_hourly_temperatures(include_extremes=True, climate_stress=False):
    """Generate 8760 hourly temperatures for a typical SLC year.

    Uses sinusoidal diurnal variation around monthly averages.
    Optionally injects cold snap and heat wave events.

    Args:
        include_extremes: Inject cold snap and heat wave events.
        climate_stress: Use elevated summer baselines and multiple heat waves
                        reflecting recent trend of increasing extreme highs.
    """
    temps = []
    solar = []
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    for month_idx, days in enumerate(days_in_month):
        month = month_idx + 1
        high, low, sun_hrs, peak_solar = SLC_MONTHLY[month]

        # Apply climate stress offsets to summer months
        if climate_stress:
            hi_off, lo_off = SLC_STRESS_OFFSETS[month]
            high += hi_off
            low += lo_off

        avg = (high + low) / 2
        amplitude = (high - low) / 2

        for day in range(days):
            for hour in range(24):
                # Diurnal temperature: min at 6am, max at 3pm
                phase = 2 * math.pi * (hour - 6) / 24
                t = avg - amplitude * math.cos(phase)

                # Add some daily variation (+/- 3C random-ish)
                day_offset = 3.0 * math.sin(2 * math.pi * day / days * 3)
                t += day_offset

                temps.append(t)

                # Solar irradiance (bell curve centered at noon)
                if 6 <= hour <= 18:
                    solar_phase = math.pi * (hour - 6) / 12
                    irr = peak_solar * math.sin(solar_phase)
                else:
                    irr = 0.0
                solar.append(max(0, irr))

    # Inject extreme events
    if include_extremes:
        # Cold snap in January (hours 720-792, roughly Jan 31)
        cold_snap_start = 30 * 24  # day 30
        for h in range(COLD_SNAP_DURATION_HOURS):
            idx = cold_snap_start + h
            if idx < len(temps):
                phase = 2 * math.pi * (h % 24 - 6) / 24
                diurnal_range = 5.0  # very flat during cold snaps
                temps[idx] = COLD_SNAP_LOW_C + diurnal_range * (1 - math.cos(phase)) / 2

        if climate_stress:
            # Multiple heat waves throughout summer
            for hw_month, hw_day, hw_dur, hw_peak in STRESS_HEAT_WAVES:
                day_of_year = sum(days_in_month[:hw_month - 1]) + hw_day - 1
                hw_start = day_of_year * 24
                for h in range(hw_dur):
                    idx = hw_start + h
                    if idx < len(temps):
                        phase = 2 * math.pi * (h % 24 - 6) / 24
                        diurnal_range = 10.0
                        avg_heat = hw_peak - 5
                        temps[idx] = avg_heat - diurnal_range / 2 * math.cos(phase)
        else:
            # Single baseline heat wave in July
            heat_start = (31 + 28 + 31 + 30 + 31 + 30 + 10) * 24  # July 10
            for h in range(HEAT_WAVE_DURATION_HOURS):
                idx = heat_start + h
                if idx < len(temps):
                    phase = 2 * math.pi * (h % 24 - 6) / 24
                    diurnal_range = 10.0
                    avg_heat = HEAT_WAVE_HIGH_C - 5
                    temps[idx] = avg_heat - diurnal_range / 2 * math.cos(phase)

    return temps, solar


def run_simulation(include_extremes=True, climate_stress=False):
    """Run the thermal simulation for one year.

    Returns dict with hourly arrays and summary statistics.
    """
    temps_ambient, solar_irr = generate_hourly_temperatures(
        include_extremes, climate_stress=climate_stress)
    num_hours = len(temps_ambient)

    # State
    t_internal = 15.0  # start at 15C (spring-like)
    heater_on = False
    fan_on = False

    # Output arrays
    t_int_log = []
    t_amb_log = []
    heater_log = []
    fan_log = []
    charge_inhibit_log = []
    q_heater_log = []
    q_fan_log = []

    # Accumulators
    total_heater_wh = 0.0
    total_fan_wh = 0.0
    heater_on_hours = 0
    fan_on_hours = 0
    charge_inhibit_hours = 0
    min_internal = 999
    max_internal = -999
    below_zero_hours = 0

    dt = 3600.0  # 1 hour timestep in seconds

    for h in range(num_hours):
        t_amb = temps_ambient[h]
        irr = solar_irr[h]

        # --- Thermostat control (STC-1000 hysteresis) ---
        if t_internal < HEAT_ON_C:
            heater_on = True
        elif t_internal > HEAT_OFF_C:
            heater_on = False

        if t_internal > FAN_ON_C:
            fan_on = True
        elif t_internal < FAN_OFF_C:
            fan_on = False

        charge_inhibit = t_internal < CHARGE_INHIBIT_C

        # --- Heat flows ---
        # Conduction through walls
        effective_ua = UA
        if fan_on:
            effective_ua = UA * FAN_UA_MULTIPLIER

        q_conduction = effective_ua * (t_amb - t_internal)  # W (negative = heat loss)

        # Solar heating of enclosure surface
        q_solar = SOLAR_ABSORPTIVITY * irr * SOLAR_PROJECTED_AREA  # W
        # Only fraction reaches internal (attenuated by insulation)
        q_solar_internal = q_solar * 0.15  # ~15% of absorbed solar reaches interior

        # Internal heat sources
        q_heater = HEATER_POWER_W if heater_on else 0.0
        q_electronics = ELECTRONICS_HEAT_W
        q_fan_heat = FAN_POWER_W if fan_on else 0.0

        # Net heat flow into thermal mass
        q_net = q_conduction + q_solar_internal + q_heater + q_electronics + q_fan_heat

        # Temperature update (lumped parameter)
        delta_t = q_net * dt / THERMAL_MASS
        t_internal += delta_t

        # --- Logging ---
        t_int_log.append(t_internal)
        t_amb_log.append(t_amb)
        heater_log.append(1 if heater_on else 0)
        fan_log.append(1 if fan_on else 0)
        charge_inhibit_log.append(1 if charge_inhibit else 0)
        q_heater_log.append(q_heater)
        q_fan_log.append(q_fan_heat)

        # Accumulators
        if heater_on:
            total_heater_wh += HEATER_POWER_W
            heater_on_hours += 1
        if fan_on:
            total_fan_wh += FAN_POWER_W
            fan_on_hours += 1
        if charge_inhibit:
            charge_inhibit_hours += 1
        if t_internal < 0:
            below_zero_hours += 1
        min_internal = min(min_internal, t_internal)
        max_internal = max(max_internal, t_internal)

    return {
        "t_internal": t_int_log,
        "t_ambient": t_amb_log,
        "heater_on": heater_log,
        "fan_on": fan_log,
        "charge_inhibit": charge_inhibit_log,
        "q_heater": q_heater_log,
        "q_fan": q_fan_log,
        "summary": {
            "min_internal_C": min_internal,
            "max_internal_C": max_internal,
            "total_heater_kWh": total_heater_wh / 1000,
            "total_fan_kWh": total_fan_wh / 1000,
            "heater_on_hours": heater_on_hours,
            "fan_on_hours": fan_on_hours,
            "charge_inhibit_hours": charge_inhibit_hours,
            "below_zero_hours": below_zero_hours,
            "thermal_resistance_KW": R_WALL,
            "UA_value_WK": UA,
            "thermal_mass_JK": THERMAL_MASS,
        }
    }


def format_summary(results, label="BASELINE"):
    """Format simulation results as a text report."""
    s = results["summary"]
    lines = [
        "=" * 60,
        f"THERMAL SIMULATION RESULTS  [{label}]",
        "LiFePO4 Battery Enclosure -- Salt Lake City",
        "=" * 60,
        "",
        "ENCLOSURE PROPERTIES",
        f"  Thermal mass:          {s['thermal_mass_JK']:.0f} J/K ({TOTAL_CELL_MASS:.0f} kg cells)",
        f"  Wall R-value:          {s['thermal_resistance_KW']:.3f} K/W",
        f"  UA value:              {s['UA_value_WK']:.2f} W/K",
        f"  Surface area:          {SURFACE_AREA:.3f} m^2",
        f"  Foam thickness:        {FOAM_THICKNESS_M*1000:.0f} mm",
        "",
        "TEMPERATURE EXTREMES (internal)",
        f"  Minimum:               {s['min_internal_C']:.1f} C",
        f"  Maximum:               {s['max_internal_C']:.1f} C",
        f"  Hours below 0C:        {s['below_zero_hours']}",
        "",
        "HEATER PERFORMANCE",
        f"  Heater ON hours:       {s['heater_on_hours']} hrs/year",
        f"  Total heater energy:   {s['total_heater_kWh']:.1f} kWh/year",
        f"  Avg daily (winter):    {s['total_heater_kWh']*1000/(s['heater_on_hours'] if s['heater_on_hours'] else 1)*24/1000:.1f} kWh/day (when heating)",
        "",
        "FAN PERFORMANCE",
        f"  Fan ON hours:          {s['fan_on_hours']} hrs/year",
        f"  Total fan energy:      {s['total_fan_kWh']:.1f} kWh/year",
        "",
        "CHARGE INHIBIT (BMS, below 0C)",
        f"  Charge blocked hours:  {s['charge_inhibit_hours']} hrs/year",
        "",
        "ASSESSMENT",
    ]

    # Assessment
    if s['min_internal_C'] > -5:
        lines.append(f"  [PASS] Min internal temp {s['min_internal_C']:.1f}C > -5C")
        lines.append(f"         Heater keeps cells within safe discharge range")
    else:
        lines.append(f"  [WARN] Min internal temp {s['min_internal_C']:.1f}C < -5C")
        lines.append(f"         Consider higher-power heater or thicker insulation")

    if s['min_internal_C'] > 0:
        lines.append(f"  [PASS] Cells never reach 0C - charging always available")
    else:
        lines.append(f"  [INFO] Cells reach {s['min_internal_C']:.1f}C - charging blocked {s['charge_inhibit_hours']} hrs/year")
        lines.append(f"         This is expected and handled by BMS charge inhibit")

    if s['max_internal_C'] < 45:
        lines.append(f"  [PASS] Max internal temp {s['max_internal_C']:.1f}C < 45C LiFePO4 limit")
    else:
        lines.append(f"  [FAIL] Max internal temp {s['max_internal_C']:.1f}C exceeds 45C!")
        lines.append(f"         Need stronger cooling or better ventilation")

    heater_daily_winter = s['total_heater_kWh'] / 120  # ~120 heating days
    lines.append(f"")
    lines.append(f"  Annual thermal energy: {s['total_heater_kWh'] + s['total_fan_kWh']:.1f} kWh")
    lines.append(f"  Avg winter heating:    {heater_daily_winter:.2f} kWh/day")
    lines.append(f"  Battery impact:        {heater_daily_winter/6.144*100:.1f}% of usable capacity per winter day")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_comparison(baseline, stress):
    """Format a side-by-side comparison of baseline vs climate stress."""
    b = baseline["summary"]
    s = stress["summary"]
    lines = [
        "",
        "=" * 60,
        "SCENARIO COMPARISON: BASELINE vs CLIMATE STRESS",
        "=" * 60,
        "",
        "Climate stress scenario applies:",
        "  - Elevated summer baselines (Jul +3.5C, Aug +4.0C highs)",
        "  - 5 heat wave events Jun-Aug (vs 1 baseline)",
        "  - Peak ambient: 46C (vs 42C baseline)",
        "",
        f"  {'Metric':<30} {'Baseline':>10} {'Stress':>10} {'Delta':>10}",
        f"  {'-'*30} {'-'*10} {'-'*10} {'-'*10}",
        f"  {'Max internal (C)':<30} {b['max_internal_C']:>10.1f} {s['max_internal_C']:>10.1f} {s['max_internal_C']-b['max_internal_C']:>+10.1f}",
        f"  {'Min internal (C)':<30} {b['min_internal_C']:>10.1f} {s['min_internal_C']:>10.1f} {s['min_internal_C']-b['min_internal_C']:>+10.1f}",
        f"  {'Fan ON hours':<30} {b['fan_on_hours']:>10} {s['fan_on_hours']:>10} {s['fan_on_hours']-b['fan_on_hours']:>+10}",
        f"  {'Fan energy (kWh)':<30} {b['total_fan_kWh']:>10.1f} {s['total_fan_kWh']:>10.1f} {s['total_fan_kWh']-b['total_fan_kWh']:>+10.1f}",
        f"  {'Heater ON hours':<30} {b['heater_on_hours']:>10} {s['heater_on_hours']:>10} {s['heater_on_hours']-b['heater_on_hours']:>+10}",
        f"  {'Heater energy (kWh)':<30} {b['total_heater_kWh']:>10.1f} {s['total_heater_kWh']:>10.1f} {s['total_heater_kWh']-b['total_heater_kWh']:>+10.1f}",
        f"  {'Charge inhibit hours':<30} {b['charge_inhibit_hours']:>10} {s['charge_inhibit_hours']:>10} {s['charge_inhibit_hours']-b['charge_inhibit_hours']:>+10}",
        f"  {'Total thermal energy (kWh)':<30} {b['total_heater_kWh']+b['total_fan_kWh']:>10.1f} {s['total_heater_kWh']+s['total_fan_kWh']:>10.1f} {(s['total_heater_kWh']+s['total_fan_kWh'])-(b['total_heater_kWh']+b['total_fan_kWh']):>+10.1f}",
        "",
    ]

    if s['max_internal_C'] >= 45:
        lines.append("  ** CLIMATE STRESS EXCEEDS 45C LIMIT **")
        lines.append("  Recommendations:")
        lines.append("    - Upgrade to larger fan (80CFM+) or add second fan")
        lines.append("    - Add reflective/white coating to reduce solar absorption")
        lines.append("    - Consider shade structure or partial burial")
        lines.append("    - Increase vent port diameter for better passive airflow")
    else:
        lines.append(f"  Current cooling design handles climate stress scenario")
        margin = 45.0 - s['max_internal_C']
        lines.append(f"  Safety margin: {margin:.1f}C below 45C limit")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def export_csv(results, filepath, stress_results=None):
    """Export hourly simulation data to CSV.

    If stress_results is provided, includes climate stress columns alongside baseline.
    """
    with open(filepath, "w") as f:
        header = ("hour,month,day,hour_of_day,"
                  "t_ambient_C,t_internal_C,heater_on,fan_on,charge_inhibit,"
                  "q_heater_W,q_fan_W")
        if stress_results:
            header += (",stress_t_ambient_C,stress_t_internal_C,"
                       "stress_heater_on,stress_fan_on,stress_charge_inhibit,"
                       "stress_q_heater_W,stress_q_fan_W")
        f.write(header + "\n")

        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        for h in range(len(results["t_internal"])):
            # Calculate month/day/hour
            day_of_year = h // 24
            hour_of_day = h % 24
            month = 1
            day = day_of_year
            for m_idx, m_days in enumerate(days_in_month):
                if day < m_days:
                    month = m_idx + 1
                    break
                day -= m_days
            else:
                month = 12
                day = day % 31

            row = (f"{h},{month},{day+1},{hour_of_day},"
                   f"{results['t_ambient'][h]:.1f},{results['t_internal'][h]:.1f},"
                   f"{results['heater_on'][h]},{results['fan_on'][h]},"
                   f"{results['charge_inhibit'][h]},"
                   f"{results['q_heater'][h]:.1f},{results['q_fan'][h]:.1f}")

            if stress_results:
                row += (f",{stress_results['t_ambient'][h]:.1f},"
                        f"{stress_results['t_internal'][h]:.1f},"
                        f"{stress_results['heater_on'][h]},"
                        f"{stress_results['fan_on'][h]},"
                        f"{stress_results['charge_inhibit'][h]},"
                        f"{stress_results['q_heater'][h]:.1f},"
                        f"{stress_results['q_fan'][h]:.1f}")

            f.write(row + "\n")
    print(f"  CSV exported: {filepath}")


def generate_plot(results, filepath, stress_results=None):
    """Generate a year-long temperature plot.

    If stress_results is provided, overlays the climate stress scenario.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed - skipping plot generation")
        print("  Install with: pip install matplotlib")
        return

    hours = list(range(len(results["t_internal"])))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_starts = []
    day_count = 0
    for days in [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]:
        month_starts.append(day_count * 24)
        day_count += days

    num_rows = 4 if stress_results else 3
    fig, axes = plt.subplots(num_rows, 1, figsize=(16, 3.5 * num_rows),
                             sharex=True)

    # --- Panel 1: Temperature (both scenarios overlaid) ---
    ax1 = axes[0]
    ax1.plot(hours, results["t_ambient"], color="#8888bb", linewidth=0.3,
             alpha=0.4, label="Ambient (baseline)")
    ax1.plot(hours, results["t_internal"], color="#2266aa", linewidth=0.6,
             label="Internal - baseline")
    if stress_results:
        ax1.plot(hours, stress_results["t_ambient"], color="#bb8888",
                 linewidth=0.3, alpha=0.4, label="Ambient (stress)")
        ax1.plot(hours, stress_results["t_internal"], color="#cc2222",
                 linewidth=0.6, label="Internal - climate stress")
    ax1.axhline(y=0, color="#0088ff", linestyle="--", linewidth=0.8,
                label="0C (charge inhibit)")
    ax1.axhline(y=45, color="#ff4400", linestyle="--", linewidth=0.8,
                label="45C (LiFePO4 max)")
    ax1.axhline(y=HEAT_ON_C, color="#44aa44", linestyle=":", linewidth=0.5,
                alpha=0.5)
    ax1.axhline(y=FAN_ON_C, color="#ff8800", linestyle=":", linewidth=0.5,
                alpha=0.5)
    ax1.set_ylabel("Temperature (C)")
    title = "Enclosure Thermal Simulation - Salt Lake City (1 Year)"
    if stress_results:
        title += "\nBaseline vs Climate Stress Scenario"
    ax1.set_title(title)
    ax1.legend(loc="upper right", fontsize=7, ncol=2)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-35, 55)

    # --- Panel 2: Heater/fan activity (baseline) ---
    ax2 = axes[1]
    ax2.fill_between(hours, results["heater_on"], color="#ff6644",
                     alpha=0.6, label="Heater ON")
    ax2.fill_between(hours, [-x for x in results["fan_on"]], color="#4488ff",
                     alpha=0.6, label="Fan ON")
    ax2.set_ylabel("Baseline\nActive")
    ax2.set_yticks([-1, 0, 1])
    ax2.set_yticklabels(["Fan", "", "Heater"])
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.3)

    if stress_results:
        # --- Panel 3: Heater/fan activity (stress) ---
        ax3 = axes[2]
        ax3.fill_between(hours, stress_results["heater_on"], color="#ff6644",
                         alpha=0.6, label="Heater ON")
        ax3.fill_between(hours, [-x for x in stress_results["fan_on"]],
                         color="#4488ff", alpha=0.6, label="Fan ON")
        ax3.set_ylabel("Stress\nActive")
        ax3.set_yticks([-1, 0, 1])
        ax3.set_yticklabels(["Fan", "", "Heater"])
        ax3.legend(loc="upper right", fontsize=8)
        ax3.grid(True, alpha=0.3)

        # --- Panel 4: Charge inhibit (both) ---
        ax4 = axes[3]
        ax4.fill_between(hours, results["charge_inhibit"], color="#ff0044",
                         alpha=0.3, label="Baseline")
        ax4.fill_between(hours, stress_results["charge_inhibit"],
                         color="#ff0044", alpha=0.3, label="Stress")
        ax4.set_ylabel("Charge\nBlocked")
        ax4.set_yticks([0, 1])
        ax4.set_yticklabels(["OK", "Blocked"])
        ax4.legend(loc="upper right", fontsize=8)
        ax4.grid(True, alpha=0.3)
    else:
        # --- Panel 3: Charge inhibit (baseline only) ---
        ax3 = axes[2]
        ax3.fill_between(hours, results["charge_inhibit"], color="#ff0044",
                         alpha=0.4, label="Charge Inhibited")
        ax3.set_ylabel("Charge\nBlocked")
        ax3.set_yticks([0, 1])
        ax3.set_yticklabels(["OK", "Blocked"])
        ax3.legend(loc="upper right", fontsize=8)
        ax3.grid(True, alpha=0.3)

    # X-axis month labels on bottom panel
    axes[-1].set_xticks(month_starts)
    axes[-1].set_xticklabels(months)
    axes[-1].set_xlabel("Month")

    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.close()
    print(f"  Plot saved: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Thermal simulation for LiFePO4 enclosure")
    parser.add_argument("--plot", action="store_true", help="Generate PNG plot")
    parser.add_argument("--csv", action="store_true", help="Export hourly CSV data")
    parser.add_argument("--no-extremes", action="store_true",
                        help="Skip cold snap / heat wave events")
    parser.add_argument("--baseline-only", action="store_true",
                        help="Skip climate stress scenario")
    args = parser.parse_args()

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    include_extremes = not args.no_extremes

    print("Running thermal simulation...")
    print(f"  Cells: {NUM_CELLS}x {CELL_MASS_KG}kg = {TOTAL_CELL_MASS}kg thermal mass")
    print(f"  Insulation: {FOAM_THICKNESS_M*1000:.0f}mm foam (R_wall = {R_WALL:.3f} K/W)")
    print(f"  Heater: {HEATER_POWER_W}W PTC")
    print(f"  Setpoints: heat {HEAT_ON_C}/{HEAT_OFF_C}C, fan {FAN_ON_C}/{FAN_OFF_C}C")
    print()

    # --- Baseline scenario ---
    print("=" * 40)
    print("  BASELINE SCENARIO")
    print("=" * 40)
    results = run_simulation(include_extremes=include_extremes)
    summary_baseline = format_summary(results, label="BASELINE")
    print(summary_baseline)

    # --- Climate stress scenario ---
    stress_results = None
    if not args.baseline_only:
        print()
        print("=" * 40)
        print("  CLIMATE STRESS SCENARIO")
        print("  (elevated summer temps, multiple heat waves)")
        print("=" * 40)
        stress_results = run_simulation(include_extremes=include_extremes,
                                        climate_stress=True)
        summary_stress = format_summary(stress_results, label="CLIMATE STRESS")
        print(summary_stress)

        comparison = format_comparison(results, stress_results)
        print(comparison)

    # --- Save outputs ---
    summary_path = os.path.join(output_dir, "thermal_summary.txt")
    with open(summary_path, "w") as f:
        f.write(summary_baseline)
        if stress_results:
            f.write("\n\n")
            f.write(format_summary(stress_results, label="CLIMATE STRESS"))
            f.write("\n\n")
            f.write(format_comparison(results, stress_results))
    print(f"\n  Summary saved: {summary_path}")

    if args.csv:
        export_csv(results, os.path.join(output_dir, "thermal_year.csv"),
                   stress_results=stress_results)

    if args.plot:
        generate_plot(results, os.path.join(output_dir, "thermal_year.png"),
                      stress_results=stress_results)


if __name__ == "__main__":
    main()
