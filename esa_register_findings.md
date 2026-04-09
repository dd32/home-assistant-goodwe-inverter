# GoodWe ESA (EHA-G20) Undocumented Register Findings

Discovered via Modbus TCP register scanning on a **GW9.999K-EHA-G20** inverter (platform 745 HV, model tag `NAH`).

- **Firmware**: ARM 03.111 / DSP 04.4004 (inverter firmware 01.01.01)
- **Batteries**: 6x GW8.3-BAT-D-G21 (~49.8 kWh usable), 26 cells each, BMS v5, DCDC v4
- **Modbus**: TCP port 502, slave address 0xF7

## Summary

Scanned holding registers 35000-48000. Found **376 unknown registers with meaningful values** beyond the 241 already mapped in the goodwe library (v0.4.10).

Findings verified against live Home Assistant sensor readings and SolarGo/SEMS+ app data.

## User-Confirmed Findings

### 1. Battery Serial Number (37060-37075) - COMMENTED OUT IN LIBRARY

Commented out in `et.py` but **returns valid data**. Confirmed by user against SolarGo app.

| Register | Type | Value | Description |
|----------|------|-------|-------------|
| 37060-37067 | String8 | `5BAEH1B10225BQ0045` | Battery 1 Serial Number |
| 37068-37075 | (padding) | spaces (0x2020) | Padded with spaces |

### 2. Battery Energy Capacity (37082) - NEW

| Register | Type | Value | Description | Confirmed |
|----------|------|-------|-------------|-----------|
| 37082 | Integer | 498 | /10 = 49.8 kWh total battery capacity (6 x 8.3 = 49.8) | Yes (SolarGo) |

### 3. Battery Physical Module Count (37077) - NEW

| Register | Type | Value | Description | Confirmed |
|----------|------|-------|-------------|-----------|
| 37077 | Integer | 6 | Physical battery modules installed | Yes (SolarGo) |

### 4. Extended Model Name (35060-35067) - NEW

| Register | Type | Value | Description | Confirmed |
|----------|------|-------|-------------|-----------|
| 35060-35067 | String8 | `GW9.999K-EHA-G20` | Full model name (16 chars) | Yes (SolarGo) |

### 5. Inverter Temperature (35249) - NEW

The SolarGo app shows a single "Inverter Temperature" value. This maps to register 35249, which differs from the three temperatures already exposed by the library (air/module/radiator).

| Register | Type | Value | Description | Confirmed |
|----------|------|-------|-------------|-----------|
| 35249 | Temp | 273 | /10 = 27.3C inverter chamber temperature | Yes (app showed 28C) |

### 6. BMS Version Decoding (37014) - EXISTING REGISTER, NEW INTERPRETATION

Register 37014 (`battery_sw_version`) is a compound field, not a simple version number:

| Byte | Value | Meaning | Confirmed |
|------|-------|---------|-----------|
| High byte | 5 | BMS firmware version | Yes (SolarGo) |
| Low byte | 4 | DCDC firmware version | Yes (SolarGo) |

### 7. Battery String Voltage / Cell Count (47917) - EXISTING REGISTER, NEW INTERPRETATION

| Register | Type | Value | Interpretation | Confirmed |
|----------|------|-------|----------------|-----------|
| 47917 | Integer | 832 | /10 = 83.2V = 26 cells x 3.2V nominal LFP | Yes (user confirms 26 cells) |

### 8. Charge/Discharge Power Limits (37004, 37005) - EXISTING REGISTERS, CORRECTED UNITS

The library labels these as amps, but they are in BMS-internal units. Multiply by ~14.375 to get watts:

| Register | Library Label | Raw | Calculated | App Value | Match |
|----------|-------------|-----|------------|-----------|-------|
| 37004 | Battery Charge Limit (A) | 48 | 48 x 14.375 = 690W | 0.69 kW | Exact |
| 37005 | Battery Discharge Limit (A) | 642 | 642 x 14.375 = 9229W | 9.22 kW | Exact |

The corresponding settings registers 47903 and 47905 hold the same values with 10x scaling (480, 6420).

### 9. BMS-Side Battery Power (37083) - NEW

| Register | Type | Value | Description | Confirmed |
|----------|------|-------|-------------|-----------|
| 37083 | Integer | 498 | BMS-reported battery power in W (~0.49-0.50 kW) | Yes (app showed 0.49kW) |

Note: This differs from inverter-side `pbattery1` (35182-35183) which reads higher due to DC-DC conversion losses. 37083 is the BMS-side measurement.

## High-Confidence Findings (HA Sensor Correlation)

### 10. Battery Total Charge/Discharge (37056-37059) - COMMENTED OUT IN LIBRARY

| Register | Type | Value | Description | Verification |
|----------|------|-------|-------------|-------------|
| 37056-37057 | Energy4 | 174.4 kWh | Total Battery 1 Charge | Matches `e_bat_charge_total` (35206) |
| 37058-37059 | Energy4 | 136.1 kWh | Total Battery 1 Discharge | Matches `e_bat_discharge_total` (35209) |

### 11. Extended BMS Data (37076-37096) - NEW

| Register | Type | Value | Interpretation | Confidence |
|----------|------|-------|----------------|------------|
| 37076 | Integer | 6000 | Battery total capacity in BMS units | High |
| 37077 | Integer | 6 | Battery physical module count | Confirmed |
| 37078 | Integer | 0x0606 | Battery configuration (hi=module_count, lo=module_count) | Medium |
| 37080-37081 | Power4S | ~2860 W | Inverter-side battery power (matches pbattery1) | High |
| 37082 | Integer | 498 | /10 = 49.8 kWh total energy capacity | Confirmed |
| 37083 | Integer | ~498 | BMS-side battery power in W | Confirmed |
| 37084 | Integer | 1 | Status flag | Medium |
| 37086 | Integer | 71 | /10 = 7.1A battery current (matches ibattery1) | High |
| 37091 | Integer | 4136 | Unknown | Low |
| 37094 | Integer | 261 | 0x0105 -> possible sub-version 1.5 | Low |

### 12. Grid Monitoring Registers (35268-35271) - NEW

| Register | Type | Value | Interpretation | Confidence |
|----------|------|-------|----------------|------------|
| 35268 | Frequency | 5003 | /100 = 50.03 Hz grid frequency (matches HA) | High |
| 35269 | Frequency | 5001 | /100 = 50.01 Hz nominal/reference frequency | High |
| 35270 | Voltage | 2473 | /10 = 247.3V grid voltage (high/max) | High |
| 35271 | Voltage | 2432 | /10 = 243.2V grid voltage (low/min) | High |

### 13. Runtime Extended (35222-35225) - NEW

| Register | Type | Value | Interpretation | Confidence |
|----------|------|-------|----------------|------------|
| 35222 | Integer | 5 | Operation mode (5 = self_use, matches HA) | High |
| 35223 | Integer | 10000 | Rated power in W (9999W rounded) | High |
| 35224 | Integer | 32000 | Max apparent power or configuration | Medium |

## Per-Module Battery Data

The SolarGo app (via Bluetooth) shows per-module data including individual SoC, temperatures, and serial numbers. This data is **NOT available via Modbus TCP** — it comes through the Bluetooth/BMS direct connection. The inverter's Modbus interface only exposes aggregate battery data.

- Individual SoC example: 94.3%, 94.7%, 94.6%, 94.6%, 94.6%, 94.6%
- Aggregate SoC (37007): 94% (truncated floor)
- Battery 2 S/N (from app): `5BAEH1C10225CE0313` (not in Modbus registers)

## Proposed Changes to goodwe Library (et.py)

### Uncomment Existing (37056-37075)

```python
# In __all_sensors_battery, uncomment these:
Energy4("battery_total_charge", 37056, "Total Battery 1 Charge", Kind.BAT),
Energy4("battery_total_discharge", 37058, "Total Battery 1 Discharge", Kind.BAT),
String8("battery_sn", 37060, "Battery S/N", Kind.BAT),
```

### Add New BMS Extended Sensors

```python
# New sensors after existing __all_sensors_battery:
Integer("battery_capacity_total", 37076, "Battery Total Capacity", "", Kind.BAT),
Integer("battery_physical_modules", 37077, "Battery Physical Modules", "", Kind.BAT),
Integer("battery_config", 37078, "Battery Configuration", "", Kind.BAT),
# 37079 reserved
Power4S("battery_bms_power", 37080, "Battery BMS Power", Kind.BAT),
Integer("battery_energy_capacity", 37082, "Battery Energy Capacity", "kWh", Kind.BAT),
Integer("battery_bms_power_w", 37083, "Battery BMS Power (W)", "W", Kind.BAT),
Integer("battery_strings", 37084, "Battery Strings", "", Kind.BAT),
# 37085 reserved
CurrentS("battery_bms_current", 37086, "Battery BMS Current", Kind.BAT),
```

### Add Inverter Temperature

```python
Temp("temperature_chamber", 35249, "Inverter Temperature (Chamber)", Kind.AC),
```

### Add Extended Model Name

```python
# 35060-35067: Full model name string (16 chars)
String16("model_name_full", 35060, "Full Model Name"),
```

### Fix BMS Version Interpretation

```python
# 37014 should be decoded as compound: hi=BMS version, lo=DCDC version
ByteH("battery_bms_version", 37014, "Battery BMS Version", "", Kind.BAT),
ByteL("battery_dcdc_version", 37014, "Battery DCDC Version", "", Kind.BAT),
```

## Registers Needing Further Investigation

- **37001 (`battery_index`)**: Library names this "Battery Index" but the value (465) is suspiciously close to battery power readings. May have a different meaning on ESA platform.
- **37004/37005**: Library labels as amps but actual unit is BMS-internal (~14.375 W/unit). Needs confirmation on other inverter models.
- **43505-43882**: Grid safety/protection parameters (voltage/frequency trip thresholds)
- **45374-45416**: Battery charging parameters
- **47424-47878**: Extended settings beyond known BMS range
- **38000-38011**: Grid monitoring mirror registers

## Scan Tools

- `scan_registers.py` - Raw Modbus TCP register scanner (pymodbus, Modbus TCP)
- `analyze_registers.py` - Cross-reference against known goodwe library registers
- `identify_registers.py` - Multi-snapshot correlation tool
