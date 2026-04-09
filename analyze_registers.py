"""
Cross-reference scan results against known registers in the goodwe library.

Reads a CSV from scan_registers.py and categorizes each register as known or unknown.

Usage:
    .venv/bin/python analyze_registers.py [scan_results.csv]
"""

import csv
import sys

# All known register addresses from goodwe library et.py (ET class)
# Format: {address: (sensor_id, description)}
KNOWN_REGISTERS = {
    # Device version info (35000-35032)
    35000: ("modbus_version", "Modbus Version"),
    35001: ("rated_power", "Rated Power"),
    35002: ("ac_output_type", "AC Output Type"),
    # 35003-35010: serial number (8 registers)
    **{r: ("serial_number", f"Serial Number byte {r-35003}") for r in range(35003, 35011)},
    # 35011-35015: model name (5 registers)
    **{r: ("model_name", f"Model Name byte {r-35011}") for r in range(35011, 35016)},
    35016: ("dsp1_version", "DSP1 Version"),
    35017: ("dsp2_version", "DSP2 Version"),
    35018: ("dsp_svn_version", "DSP SVN Version"),
    35019: ("arm_version", "ARM Version"),
    35020: ("arm_svn_version", "ARM SVN Version"),
    # 35021-35027: firmware (6 registers)
    **{r: ("firmware", f"Firmware byte {r-35021}") for r in range(35021, 35027)},
    # 35027-35032: arm firmware (6 registers)
    **{r: ("arm_firmware", f"ARM Firmware byte {r-35027}") for r in range(35027, 35033)},

    # Runtime data (35100-35224)
    35100: ("timestamp", "Timestamp (year+month)"),
    35101: ("timestamp", "Timestamp (day+hour)"),
    35102: ("timestamp", "Timestamp (min+sec)"),
    35103: ("vpv1", "PV1 Voltage"),
    35104: ("ipv1", "PV1 Current"),
    35105: ("ppv1", "PV1 Power (high)"),
    35106: ("ppv1", "PV1 Power (low)"),
    35107: ("vpv2", "PV2 Voltage"),
    35108: ("ipv2", "PV2 Current"),
    35109: ("ppv2", "PV2 Power (high)"),
    35110: ("ppv2", "PV2 Power (low)"),
    35111: ("vpv3", "PV3 Voltage"),
    35112: ("ipv3", "PV3 Current"),
    35113: ("ppv3", "PV3 Power (high)"),
    35114: ("ppv3", "PV3 Power (low)"),
    35115: ("vpv4", "PV4 Voltage"),
    35116: ("ipv4", "PV4 Current"),
    35117: ("ppv4", "PV4 Power (high)"),
    35118: ("ppv4", "PV4 Power (low)"),
    35119: ("pv_mode_3_4", "PV3/PV4 Mode"),
    35120: ("pv_mode_1_2", "PV1/PV2 Mode"),
    35121: ("vgrid", "On-grid L1 Voltage"),
    35122: ("igrid", "On-grid L1 Current"),
    35123: ("fgrid", "On-grid L1 Frequency"),
    # 35124: reserved
    35125: ("pgrid", "On-grid L1 Power"),
    35126: ("vgrid2", "On-grid L2 Voltage"),
    35127: ("igrid2", "On-grid L2 Current"),
    35128: ("fgrid2", "On-grid L2 Frequency"),
    # 35129: reserved
    35130: ("pgrid2", "On-grid L2 Power"),
    35131: ("vgrid3", "On-grid L3 Voltage"),
    35132: ("igrid3", "On-grid L3 Current"),
    35133: ("fgrid3", "On-grid L3 Frequency"),
    # 35134: reserved
    35135: ("pgrid3", "On-grid L3 Power"),
    35136: ("grid_mode", "Grid Mode"),
    # 35137: reserved
    35138: ("total_inverter_power", "Total Inverter Power"),
    # 35139: reserved
    35140: ("active_power", "Active Power"),
    # 35141: reserved
    35142: ("reactive_power", "Reactive Power"),
    # 35143: reserved
    35144: ("apparent_power", "Apparent Power"),
    35145: ("backup_v1", "Back-up L1 Voltage"),
    35146: ("backup_i1", "Back-up L1 Current"),
    35147: ("backup_f1", "Back-up L1 Frequency"),
    35148: ("load_mode1", "Load Mode L1"),
    # 35149: reserved
    35150: ("backup_p1", "Back-up L1 Power"),
    35151: ("backup_v2", "Back-up L2 Voltage"),
    35152: ("backup_i2", "Back-up L2 Current"),
    35153: ("backup_f2", "Back-up L2 Frequency"),
    35154: ("load_mode2", "Load Mode L2"),
    # 35155: reserved
    35156: ("backup_p2", "Back-up L2 Power"),
    35157: ("backup_v3", "Back-up L3 Voltage"),
    35158: ("backup_i3", "Back-up L3 Current"),
    35159: ("backup_f3", "Back-up L3 Frequency"),
    35160: ("load_mode3", "Load Mode L3"),
    # 35161: reserved
    35162: ("backup_p3", "Back-up L3 Power"),
    # 35163: reserved
    35164: ("load_p1", "Load L1"),
    # 35165: reserved
    35166: ("load_p2", "Load L2"),
    # 35167: reserved
    35168: ("load_p3", "Load L3"),
    # 35169: reserved
    35170: ("backup_ptotal", "Back-up Load Total"),
    # 35171: reserved
    35172: ("load_ptotal", "Load Total"),
    35173: ("ups_load", "UPS Load %"),
    35174: ("temperature_air", "Inverter Temp (Air)"),
    35175: ("temperature_module", "Inverter Temp (Module)"),
    35176: ("temperature", "Inverter Temp (Radiator)"),
    35177: ("function_bit", "Function Bit"),
    35178: ("bus_voltage", "Bus Voltage"),
    35179: ("nbus_voltage", "NBus Voltage"),
    35180: ("vbattery1", "Battery Voltage"),
    35181: ("ibattery1", "Battery Current"),
    35182: ("pbattery1", "Battery Power (high)"),
    35183: ("pbattery1", "Battery Power (low)"),
    35184: ("battery_mode", "Battery Mode"),
    35185: ("warning_code", "Warning Code"),
    35186: ("safety_country", "Safety Country"),
    35187: ("work_mode", "Work Mode"),
    35188: ("operation_mode", "Operation Mode"),
    35189: ("error_codes", "Error Codes (high)"),
    35190: ("error_codes", "Error Codes (low)"),
    35191: ("e_total", "Total PV Generation (high)"),
    35192: ("e_total", "Total PV Generation (low)"),
    35193: ("e_day", "Today PV Generation (high)"),
    35194: ("e_day", "Today PV Generation (low)"),
    35195: ("e_total_exp", "Total Energy Export (high)"),
    35196: ("e_total_exp", "Total Energy Export (low)"),
    35197: ("h_total", "Hours Total (high)"),
    35198: ("h_total", "Hours Total (low)"),
    35199: ("e_day_exp", "Today Energy Export"),
    35200: ("e_total_imp", "Total Energy Import (high)"),
    35201: ("e_total_imp", "Total Energy Import (low)"),
    35202: ("e_day_imp", "Today Energy Import"),
    35203: ("e_load_total", "Total Load (high)"),
    35204: ("e_load_total", "Total Load (low)"),
    35205: ("e_load_day", "Today Load"),
    35206: ("e_bat_charge_total", "Total Battery Charge (high)"),
    35207: ("e_bat_charge_total", "Total Battery Charge (low)"),
    35208: ("e_bat_charge_day", "Today Battery Charge"),
    35209: ("e_bat_discharge_total", "Total Battery Discharge (high)"),
    35210: ("e_bat_discharge_total", "Total Battery Discharge (low)"),
    35211: ("e_bat_discharge_day", "Today Battery Discharge"),
    # 35212-35219: gap in known sensors
    35220: ("diagnose_result", "Diag Status (high)"),
    35221: ("diagnose_result", "Diag Status (low)"),

    # Battery 2 extended (35262-35267)
    35262: ("vbattery2", "Battery2 Voltage"),
    35263: ("ibattery2", "Battery2 Current"),
    35264: ("pbattery2", "Battery2 Power (high)"),
    35265: ("pbattery2", "Battery2 Power (low)"),
    35266: ("battery2_mode", "Battery2 Mode"),

    # MPPT data (35301-35365)
    35301: ("ppv_total", "PV Power Total (high)"),
    35302: ("ppv_total", "PV Power Total (low)"),
    35303: ("pv_channel", "PV Channel"),
    **{r: (f"vpv/ipv{5+(r-35304)//2}", f"PV{5+(r-35304)//2} {'Voltage' if (r-35304)%2==0 else 'Current'}") for r in range(35304, 35328)},
    # 35328-35336: warning/avg voltage/error extend
    **{r: (f"pmppt{r-35336}", f"MPPT{r-35336} Power") for r in range(35337, 35345)},
    **{r: (f"imppt{r-35344}", f"MPPT{r-35344} Current") for r in range(35345, 35353)},
    35353: ("reactive_power1", "Reactive Power L1 (high)"),
    35354: ("reactive_power1", "Reactive Power L1 (low)"),
    35355: ("reactive_power2", "Reactive Power L2 (high)"),
    35356: ("reactive_power2", "Reactive Power L2 (low)"),
    35357: ("reactive_power3", "Reactive Power L3 (high)"),
    35358: ("reactive_power3", "Reactive Power L3 (low)"),
    35359: ("apparent_power1", "Apparent Power L1 (high)"),
    35360: ("apparent_power1", "Apparent Power L1 (low)"),
    35361: ("apparent_power2", "Apparent Power L2 (high)"),
    35362: ("apparent_power2", "Apparent Power L2 (low)"),
    35363: ("apparent_power3", "Apparent Power L3 (high)"),
    35364: ("apparent_power3", "Apparent Power L3 (low)"),

    # Meter data (36000-36124)
    36000: ("commode", "Commode"),
    36001: ("rssi", "RSSI"),
    36002: ("manufacture_code", "Manufacture Code"),
    36003: ("meter_test_status", "Meter Test Status"),
    36004: ("meter_comm_status", "Meter Comm Status"),
    36005: ("active_power1", "Active Power L1"),
    36006: ("active_power2", "Active Power L2"),
    36007: ("active_power3", "Active Power L3"),
    36008: ("active_power_total", "Active Power Total"),
    36009: ("reactive_power_total", "Reactive Power Total"),
    36010: ("meter_power_factor1", "Meter PF L1"),
    36011: ("meter_power_factor2", "Meter PF L2"),
    36012: ("meter_power_factor3", "Meter PF L3"),
    36013: ("meter_power_factor", "Meter PF Total"),
    36014: ("meter_freq", "Meter Frequency"),
    36015: ("meter_e_total_exp", "Meter Total Export (high)"),
    36016: ("meter_e_total_exp", "Meter Total Export (low)"),
    36017: ("meter_e_total_imp", "Meter Total Import (high)"),
    36018: ("meter_e_total_imp", "Meter Total Import (low)"),
    **{r: ("meter_active_power", f"Meter Active Power {['L1','L1','L2','L2','L3','L3','Total','Total'][r-36019]}") for r in range(36019, 36027)},
    **{r: ("meter_reactive_power", f"Meter Reactive Power") for r in range(36027, 36035)},
    **{r: ("meter_apparent_power", f"Meter Apparent Power") for r in range(36035, 36043)},
    36043: ("meter_type", "Meter Type"),
    36044: ("meter_sw_version", "Meter SW Version"),
    36045: ("meter2_active_power", "Meter 2 Active Power (high)"),
    36046: ("meter2_active_power", "Meter 2 Active Power (low)"),
    36047: ("meter2_e_total_exp", "Meter 2 Total Export (high)"),
    36048: ("meter2_e_total_exp", "Meter 2 Total Export (low)"),
    36049: ("meter2_e_total_imp", "Meter 2 Total Import (high)"),
    36050: ("meter2_e_total_imp", "Meter 2 Total Import (low)"),
    36051: ("meter2_comm_status", "Meter 2 Comm Status"),
    36052: ("meter_voltage1", "Meter L1 Voltage"),
    36053: ("meter_voltage2", "Meter L2 Voltage"),
    36054: ("meter_voltage3", "Meter L3 Voltage"),
    36055: ("meter_current1", "Meter L1 Current"),
    36056: ("meter_current2", "Meter L2 Current"),
    36057: ("meter_current3", "Meter L3 Current"),
    # 36058-36091: gap
    **{r: ("meter_e_total_exp1", "Meter Export L1") for r in range(36092, 36096)},
    **{r: ("meter_e_total_exp2", "Meter Export L2") for r in range(36096, 36100)},
    **{r: ("meter_e_total_exp3", "Meter Export L3") for r in range(36100, 36104)},
    **{r: ("meter_e_total_exp", "Meter Export Total") for r in range(36104, 36108)},
    **{r: ("meter_e_total_imp1", "Meter Import L1") for r in range(36108, 36112)},
    **{r: ("meter_e_total_imp2", "Meter Import L2") for r in range(36112, 36116)},
    **{r: ("meter_e_total_imp3", "Meter Import L3") for r in range(36116, 36120)},
    **{r: ("meter_e_total_imp", "Meter Import Total") for r in range(36120, 36124)},

    # Battery BMS (37000-37023)
    37000: ("battery_bms", "Battery BMS"),
    37001: ("battery_index", "Battery Index"),
    37002: ("battery_status", "Battery Status"),
    37003: ("battery_temperature", "Battery Temperature"),
    37004: ("battery_charge_limit", "Battery Charge Limit"),
    37005: ("battery_discharge_limit", "Battery Discharge Limit"),
    37006: ("battery_error_l", "Battery Error L"),
    37007: ("battery_soc", "Battery SoC"),
    37008: ("battery_soh", "Battery SoH"),
    37009: ("battery_modules", "Battery Modules"),
    37010: ("battery_warning_l", "Battery Warning L"),
    37011: ("battery_protocol", "Battery Protocol"),
    37012: ("battery_error_h", "Battery Error H"),
    37013: ("battery_warning_h", "Battery Warning H"),
    37014: ("battery_sw_version", "Battery SW Version"),
    37015: ("battery_hw_version", "Battery HW Version"),
    37016: ("battery_max_cell_temp_id", "Max Cell Temp ID"),
    37017: ("battery_min_cell_temp_id", "Min Cell Temp ID"),
    37018: ("battery_max_cell_voltage_id", "Max Cell Voltage ID"),
    37019: ("battery_min_cell_voltage_id", "Min Cell Voltage ID"),
    37020: ("battery_max_cell_temp", "Max Cell Temp"),
    37021: ("battery_min_cell_temp", "Min Cell Temp"),
    37022: ("battery_max_cell_voltage", "Max Cell Voltage"),
    37023: ("battery_min_cell_voltage", "Min Cell Voltage"),

    # Battery 2 BMS (39000-39021)
    **{r: (f"battery2_{['status','temperature','charge_limit','discharge_limit','error_l','soc','soh','modules','warning_l','protocol','error_h','warning_h','sw_version','hw_version','max_cell_temp_id','min_cell_temp_id','max_cell_voltage_id','min_cell_voltage_id','max_cell_temp','min_cell_temp','max_cell_voltage','min_cell_voltage'][r-39000]}", f"Battery 2") for r in range(39000, 39022)},

    # Settings registers
    45127: ("comm_address", "Communication Address"),
    45132: ("modbus_baud_rate", "Modbus Baud Rate (high)"),
    45133: ("modbus_baud_rate", "Modbus Baud Rate (low)"),
    45200: ("time", "Inverter Time"),
    45201: ("time", "Inverter Time"),
    45202: ("time", "Inverter Time"),
    45246: ("sensitivity_check", "Sensitivity Check"),
    45248: ("cold_start", "Cold Start"),
    45251: ("shadow_scan", "Shadow Scan"),
    45252: ("backup_supply", "Backup Supply"),
    45264: ("unbalanced_output", "Unbalanced Output"),
    45288: ("pen_relay", "PE-N Relay"),
    45350: ("battery_capacity", "Battery Capacity"),
    45351: ("battery_modules", "Battery Modules Setting"),
    45352: ("battery_charge_voltage", "Battery Charge Voltage"),
    45353: ("battery_charge_current", "Battery Charge Current"),
    45354: ("battery_discharge_voltage", "Battery Discharge Voltage"),
    45355: ("battery_discharge_current", "Battery Discharge Current"),
    45356: ("battery_discharge_depth", "Battery Discharge Depth"),
    45357: ("battery_discharge_voltage_offline", "Battery Discharge Voltage Offline"),
    45358: ("battery_discharge_depth_offline", "Battery Discharge Depth Offline"),
    45482: ("power_factor", "Power Factor"),
    47000: ("work_mode", "Work Mode Setting"),
    47010: ("dred", "DRED"),
    47120: ("meter_target_power_offset", "Meter Target Power Offset"),
    47500: ("battery_soc_protection", "Battery SoC Protection"),
    47509: ("grid_export", "Grid Export Enabled"),
    47510: ("grid_export_limit", "Grid Export Limit"),
    47511: ("ems_mode", "EMS Mode"),
    47512: ("ems_power_limit", "EMS Power Limit"),
    47514: ("battery_protocol_code", "Battery Protocol Code"),
    # Eco mode V1 (47515-47530)
    **{r: ("eco_mode_v1", f"Eco Mode V1 reg {r}") for r in range(47515, 47531)},
    # Eco mode V2 / ARM fw 19 settings (47542-47603)
    47542: ("peak_shaving_power_limit", "Peak Shaving Power Limit (high)"),
    47543: ("peak_shaving_power_limit", "Peak Shaving Power Limit (low)"),
    47544: ("peak_shaving_soc", "Peak Shaving SoC"),
    47545: ("fast_charging", "Fast Charging Enabled"),
    47546: ("fast_charging_soc", "Fast Charging SoC"),
    **{r: ("eco_mode_v2", f"Eco Mode V2 reg {r}") for r in range(47547, 47595)},
    47595: ("load_control_mode", "Load Control Mode"),
    47596: ("load_control_switch", "Load Control Switch"),
    47597: ("load_control_soc", "Load Control SoC"),
    47599: ("hardware_feed_power", "Hardware Feed Power"),
    47602: ("dod_holding", "DoD Holding"),
    47603: ("fast_charging_power", "Fast Charging Power"),
    47605: ("backup_mode_enable", "Backup Mode Switch"),
    47606: ("max_charge_power", "Max Charge Power"),
    47609: ("smart_charging_enable", "Smart Charging Switch"),
    47612: ("eco_mode_enable", "Eco Mode Switch"),
    47760: ("soc_upper_limit", "SoC Upper Limit"),
    # BMS direct (47900-47935)
    **{r: (f"bms_setting_{r}", f"BMS Setting {r}") for r in range(47900, 47936)},
}


def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "scan_results.csv"

    try:
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"Error: {csv_file} not found. Run scan_registers.py first.", file=sys.stderr)
        sys.exit(1)

    known = []
    unknown = []

    for row in rows:
        addr = int(row["address_dec"])
        value = int(row["value_dec"])
        signed = int(row["value_signed"])
        hex_addr = row["address_hex"]

        if addr in KNOWN_REGISTERS:
            sensor_id, desc = KNOWN_REGISTERS[addr]
            known.append((addr, hex_addr, value, signed, sensor_id, desc))
        else:
            unknown.append((addr, hex_addr, value, signed))

    print(f"Total non-zero registers: {len(rows)}")
    print(f"Known (mapped in goodwe library): {len(known)}")
    print(f"UNKNOWN (not in goodwe library): {len(unknown)}")

    if unknown:
        print(f"\n{'='*80}")
        print("UNKNOWN REGISTERS (potential new discoveries)")
        print(f"{'='*80}")
        print(f"{'Address':>8} {'Hex':>8} {'Value':>8} {'Signed':>8}  Notes")
        print(f"{'-'*8:>8} {'-'*8:>8} {'-'*8:>8} {'-'*8:>8}  {'-'*30}")

        # Group by proximity
        prev_addr = None
        for addr, hex_addr, value, signed in unknown:
            if prev_addr and addr - prev_addr > 5:
                print()  # visual separator between groups

            # Try to annotate based on nearby known registers
            note = _guess_context(addr)
            print(f"{addr:>8} {hex_addr:>8} {value:>8} {signed:>8}  {note}")
            prev_addr = addr

    if known:
        print(f"\n{'='*80}")
        print("KNOWN REGISTERS (already mapped)")
        print(f"{'='*80}")
        print(f"{'Address':>8} {'Hex':>8} {'Value':>8} {'Signed':>8}  {'Sensor ID':<35} Description")
        print(f"{'-'*8:>8} {'-'*8:>8} {'-'*8:>8} {'-'*8:>8}  {'-'*35:<35} {'-'*30}")
        for addr, hex_addr, value, signed, sensor_id, desc in known:
            print(f"{addr:>8} {hex_addr:>8} {value:>8} {signed:>8}  {sensor_id:<35} {desc}")


def _guess_context(addr):
    """Try to guess what region an unknown register belongs to based on proximity."""
    if 35000 <= addr < 35100:
        return "Near device info (35000-35032)"
    if 35100 <= addr < 35225:
        return "In runtime data region (35100-35224)"
    if 35225 <= addr < 35262:
        return "Gap between runtime and battery2 ext"
    if 35262 <= addr < 35301:
        return "Near battery2 extended (35262-35267)"
    if 35301 <= addr < 35400:
        return "In/near MPPT data (35301-35365)"
    if 36000 <= addr < 36200:
        return "In/near meter data (36000-36124)"
    if 37000 <= addr < 37100:
        return "In/near battery BMS (37000-37023)"
    if 37100 <= addr < 39000:
        return "Gap between BMS and battery2 BMS"
    if 39000 <= addr < 39100:
        return "In/near battery2 BMS (39000-39021)"
    if 45000 <= addr < 46000:
        return "In settings region (45xxx)"
    if 47000 <= addr < 48000:
        return "In settings region (47xxx)"
    return f"Outside known regions"


if __name__ == "__main__":
    main()
