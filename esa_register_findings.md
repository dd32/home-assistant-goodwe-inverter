# GoodWe ESA (EHA-G20) Undocumented Register Findings

Discovered via Modbus TCP register scanning on a **GW9.999K-EHA-G20** inverter (platform 745 HV, model tag `NAH`).

- **Firmware**: ARM 03.111 / DSP 04.4004
- **Batteries**: 6x GW8.3-BAT-D-G21 (~49.8 kWh usable)
- **Modbus**: TCP port 502, slave address 0xF7

## Summary

Scanned holding registers 35000-48000. Found **376 unknown registers with meaningful values** beyond the 241 already mapped in the goodwe library (v0.4.10).

## High-Confidence Findings (Confirmed via HA Sensor Correlation)

### 1. Battery Total Charge/Discharge (37056-37059) - ALREADY IN LIBRARY, COMMENTED OUT

These registers are commented out in `et.py` but **return valid data** on the ESA platform:

| Register | Type | Value | Description |
|----------|------|-------|-------------|
| 37056-37057 | Energy4 | 174.4 kWh | Total Battery 1 Charge (matches `e_bat_charge_total` at 35206) |
| 37058-37059 | Energy4 | 136.1 kWh | Total Battery 1 Discharge (matches `e_bat_discharge_total` at 35209) |

### 2. Battery Serial Number (37060-37075) - ALREADY IN LIBRARY, COMMENTED OUT

| Register | Type | Value | Description |
|----------|------|-------|-------------|
| 37060-37067 | String8 | `5BAEH1B10225BQ0045` | Battery 1 Serial Number |
| 37068-37075 | (padding) | spaces (0x2020) | Padded with spaces |

### 3. Extended BMS Data (37076-37096) - NEW

| Register | Type | Value | Interpretation | Confidence |
|----------|------|-------|----------------|------------|
| 37076 | Integer | 6000 | Battery total capacity (Ah or Wh units TBD) | High |
| 37077 | Integer | 6 | Battery physical module count (matches 6x GW8.3-BAT) | High |
| 37078 | Integer | 0x0606 | Battery configuration (hi=6, lo=6 - parallel/series config?) | Medium |
| 37080-37081 | Power4S | 2864 W | Battery power (matches `pbattery1` at 35182-35183: 2858W) | High |
| 37082 | Integer | 498 | /10 = 49.8 kWh total battery capacity (6 x 8.3 = 49.8!) | High |
| 37083 | Integer | 498 | Same value - possibly rated vs actual capacity | High |
| 37084 | Integer | 1 | Battery string count or status flag | Medium |
| 37086 | Integer | 71 | /10 = 7.1A battery current (matches `ibattery1`: 7.3A) | High |
| 37090 | Integer | 4136 | Unknown - possibly accumulated data | Low |
| 37092-37093 | Long | -10176 | Signed 32-bit - possibly accumulated energy (signed) | Low |
| 37094 | Integer | 261 | Cell voltage delta? Or firmware version sub-component | Low |
| 37096 | Integer | 1 | Status flag | Low |

### 4. Extended Model Name (35060-35067) - NEW

| Register | Type | Value | Description |
|----------|------|-------|-------------|
| 35060-35067 | String8 | `GW9.999K-EHA-G20` | Full model name (16 chars) |

This is a more complete model name than what `read_device_info` provides from 35011-35015 (which is limited to 10 chars).

### 5. Extended Device Info (35033-35082) - NEW

| Register | Type | Value | Interpretation | Confidence |
|----------|------|-------|----------------|------------|
| 35034 | Integer | 1 | Unknown flag | Low |
| 35041 | Integer | 3 | Platform variant or phase count? | Medium |
| 35044 | Integer | 4004 | DSP firmware sub-version (04.4004) | High |
| 35045 | Integer | 4006 | DSP SVN/build number | Medium |
| 35046 | Integer | 4 | ARM firmware major version | Medium |
| 35076-35081 | String | `0000-255-00` | Manufacturing date or batch code | Medium |

### 6. Grid Monitoring Registers (35268-35277) - NEW

These appear between the battery2 extended block and MPPT data:

| Register | Type | Value | Interpretation | Confidence |
|----------|------|-------|----------------|------------|
| 35268 | Frequency | 5003 | /100 = 50.03 Hz grid frequency (matches HA exactly) | High |
| 35269 | Frequency | 5001 | /100 = 50.01 Hz nominal/reference frequency | High |
| 35270 | Voltage | 2473 | /10 = 247.3V grid voltage (high/max) | High |
| 35271 | Voltage | 2432 | /10 = 243.2V grid voltage (low/min) | High |
| 35277 | Integer | 424 | /10 = 42.4 - temperature or current | Medium |

### 7. Runtime Extended (35222-35225) - NEW

| Register | Type | Value | Interpretation | Confidence |
|----------|------|-------|----------------|------------|
| 35222 | Integer | 5 | Operation mode (5 = self_use, matches HA) | High |
| 35223 | Integer | 10000 | Rated power in W (9999W rounded) | High |
| 35224 | Integer | 32000 | Max apparent power or configuration | Medium |
| 35225 | Integer | 1 | Phase count or status | Medium |

### 8. Grid Monitoring Mirror (38000-38011) - NEW

| Register | Type | Value | Interpretation | Confidence |
|----------|------|-------|----------------|------------|
| 38000 | Integer | 1 | Status/enable flag | Medium |
| 38003 | Voltage | 2645 | /10 = 264.5V - overvoltage threshold? | Medium |
| 38004 | Voltage | 5150 | /10 = 515.0V - DC bus voltage limit? | Medium |
| 38008 | Voltage | 2467 | /10 = 246.7V grid voltage (matches HA) | High |
| 38009 | Frequency | 5002 | /100 = 50.02 Hz grid frequency | High |
| 38010 | Voltage | 2632 | /10 = 263.2V - limit or threshold | Medium |
| 38011 | Voltage | 2632 | /10 = 263.2V - same as above | Medium |

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
# New tuple after __all_sensors_battery:
__all_sensors_battery_extended_bms: tuple[Sensor, ...] = (
    Integer("battery_capacity_total", 37076, "Battery Total Capacity", "Ah", Kind.BAT),
    Integer("battery_physical_modules", 37077, "Battery Physical Modules", "", Kind.BAT),
    Integer("battery_config", 37078, "Battery Configuration", "", Kind.BAT),
    # 37079 reserved
    Power4S("battery_bms_power", 37080, "Battery BMS Power", Kind.BAT),
    Integer("battery_energy_capacity", 37082, "Battery Energy Capacity", "kWh", Kind.BAT),
    # 37083 reserved
    Integer("battery_strings", 37084, "Battery Strings", "", Kind.BAT),
    # 37085 reserved
    CurrentS("battery_bms_current", 37086, "Battery BMS Current", Kind.BAT),
)
```

### Add Extended Model Name

```python
# In read_device_info or as new sensor:
# 35060-35067: Full model name string (16 chars)
String16("model_name_full", 35060, "Full Model Name"),
```

## Registers Needing Further Investigation

- **43505-43882**: Large block of what appear to be grid safety/protection parameters (voltage/frequency trip thresholds). Values like 4750, 5015, 4975 suggest V/Hz protection curves.
- **45008-45023**: ASCII `12345678` repeated - WiFi/communication passwords?
- **45203-45213**: Extended serial/identification string
- **45374-45416**: Battery charging parameters (voltages, currents, limits)
- **46700-46794**: Boolean configuration flags
- **47424-47878**: Extended settings beyond known BMS range

## Scan Tools

- `scan_registers.py` - Raw Modbus TCP register scanner
- `analyze_registers.py` - Cross-reference against known goodwe library registers
- `identify_registers.py` - Multi-snapshot correlation tool
