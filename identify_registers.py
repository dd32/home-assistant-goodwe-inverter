"""
Correlation helper for unknown Modbus registers.

Takes multiple scan snapshots over time and correlates unknown register values
against known sensor readings from the goodwe library.

Usage:
    # Take a snapshot (run multiple times with different conditions):
    .venv/bin/python identify_registers.py snapshot

    # Analyze correlations across all snapshots:
    .venv/bin/python identify_registers.py analyze

    # Show the value of specific registers across snapshots:
    .venv/bin/python identify_registers.py track 35225 35226 35227
"""

import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from pymodbus.client import ModbusTcpClient

INVERTER_IP = "192.168.1.107"
INVERTER_PORT = 502
SLAVE_ADDRESS = 0xF7
SNAPSHOT_DIR = "snapshots"
BATCH_SIZE = 125
REQUEST_DELAY = 0.05

# Registers to scan — focus on ranges with known data plus gaps
SCAN_RANGES = [
    (35000, 35400),   # Device info + runtime + gaps + MPPT
    (36000, 36200),   # Meter data + gaps
    (37000, 37100),   # Battery BMS + nearby
    (39000, 39100),   # Battery 2 BMS + nearby
    (45100, 45500),   # Settings
    (47000, 47950),   # Settings + BMS
]

# Known sensor names from goodwe library for correlation
# These are the main ones we'll compare unknown registers against
CORRELATION_SENSORS = {
    35103: ("vpv1", 10, "V"),      # /10 for voltage
    35104: ("ipv1", 10, "A"),
    35107: ("vpv2", 10, "V"),
    35108: ("ipv2", 10, "A"),
    35121: ("vgrid", 10, "V"),
    35122: ("igrid", 10, "A"),
    35125: ("pgrid", 1, "W"),
    35138: ("total_inverter_power", 1, "W"),
    35140: ("active_power", 1, "W"),
    35174: ("temperature_air", 10, "°C"),
    35175: ("temperature_module", 10, "°C"),
    35176: ("temperature", 10, "°C"),
    35178: ("bus_voltage", 10, "V"),
    35180: ("vbattery1", 10, "V"),
    35181: ("ibattery1", 10, "A"),  # signed
    37007: ("battery_soc", 1, "%"),
    37008: ("battery_soh", 1, "%"),
    37003: ("battery_temperature", 10, "°C"),
}


def take_snapshot():
    """Read all registers in scan ranges and save as a timestamped snapshot."""
    Path(SNAPSHOT_DIR).mkdir(exist_ok=True)

    client = ModbusTcpClient(INVERTER_IP, port=INVERTER_PORT, timeout=3)
    if not client.connect():
        print(f"Failed to connect to {INVERTER_IP}:{INVERTER_PORT}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    registers = {}

    print(f"Taking snapshot at {timestamp}...")

    try:
        for start, end in SCAN_RANGES:
            addr = start
            while addr < end:
                count = min(BATCH_SIZE, end - addr)
                try:
                    result = client.read_holding_registers(addr, count=count, device_id=SLAVE_ADDRESS)
                    if not result.isError():
                        for i, value in enumerate(result.registers):
                            registers[addr + i] = value
                    else:
                        # Try one at a time
                        for a in range(addr, addr + count):
                            try:
                                r = client.read_holding_registers(a, count=1, device_id=SLAVE_ADDRESS)
                                if not r.isError():
                                    registers[a] = r.registers[0]
                            except Exception:
                                pass
                            time.sleep(REQUEST_DELAY)
                except Exception as e:
                    print(f"  Error at {addr}: {e}", file=sys.stderr)
                addr += count
                time.sleep(REQUEST_DELAY)
    finally:
        client.close()

    # Save snapshot
    filename = f"{SNAPSHOT_DIR}/snapshot_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "registers": {str(k): v for k, v in sorted(registers.items())}
        }, f, indent=2)

    non_zero = sum(1 for v in registers.values() if v != 0)
    print(f"Snapshot saved: {filename} ({len(registers)} registers, {non_zero} non-zero)")
    return filename


def analyze_correlations():
    """Analyze correlations between unknown registers and known sensors across snapshots."""
    snapshots = _load_snapshots()
    if len(snapshots) < 2:
        print(f"Need at least 2 snapshots for correlation analysis (have {len(snapshots)}).")
        print("Run 'identify_registers.py snapshot' multiple times with varying conditions")
        print("(e.g., different battery SoC, PV generation, load levels).")
        return

    print(f"Analyzing {len(snapshots)} snapshots...\n")

    # Load known register addresses
    from analyze_registers import KNOWN_REGISTERS

    # Find registers that appear in all snapshots and are NOT known
    all_addrs = set()
    for snap in snapshots:
        all_addrs.update(int(a) for a in snap["registers"].keys())

    unknown_addrs = sorted(a for a in all_addrs if a not in KNOWN_REGISTERS)
    unknown_nonzero = []
    for addr in unknown_addrs:
        values = [snap["registers"].get(str(addr), 0) for snap in snapshots]
        if any(v != 0 for v in values):
            unknown_nonzero.append(addr)

    print(f"Unknown non-zero registers across snapshots: {len(unknown_nonzero)}\n")

    # For each unknown register, check correlation with known sensors
    print(f"{'Register':>8} {'Values across snapshots':<50} {'Correlates with'}")
    print(f"{'-'*8:>8} {'-'*50:<50} {'-'*40}")

    for addr in unknown_nonzero:
        values = [snap["registers"].get(str(addr), 0) for snap in snapshots]
        signed_values = [v if v < 32768 else v - 65536 for v in values]

        # Check if values are constant
        if len(set(values)) == 1:
            val_str = f"constant={values[0]} (0x{values[0]:04X})"
            print(f"{addr:>8} {val_str:<50} (static config?)")
            continue

        val_str = ", ".join(str(v) for v in values[:8])
        if len(values) > 8:
            val_str += "..."

        # Correlate against known sensors
        best_corr = None
        best_score = 0
        for known_addr, (name, divisor, unit) in CORRELATION_SENSORS.items():
            known_values = [snap["registers"].get(str(known_addr), 0) for snap in snapshots]
            known_signed = [v if v < 32768 else v - 65536 for v in known_values]

            # Check direct match
            if values == known_values:
                best_corr = f"EXACT match: {name} ({known_addr})"
                best_score = 100
                break

            # Check scaled match (unknown = known * factor)
            for factor in [0.1, 0.5, 1, 2, 10, 100]:
                scaled = [int(v * factor) for v in known_signed]
                if signed_values == scaled and all(v != 0 for v in known_values):
                    best_corr = f"{name} * {factor}"
                    best_score = 90
                    break

            # Check if values move in same direction (simple correlation)
            if len(set(known_values)) > 1 and len(set(values)) > 1:
                score = _direction_correlation(signed_values, known_signed)
                if score > best_score:
                    best_score = score
                    best_corr = f"~{name} (direction match {score:.0f}%)"

        corr_str = best_corr if best_corr else ""
        print(f"{addr:>8} {val_str:<50} {corr_str}")


def _direction_correlation(a, b):
    """Simple directional correlation: what % of time do values move in the same direction?"""
    if len(a) < 2:
        return 0
    same = 0
    total = 0
    for i in range(1, len(a)):
        da = a[i] - a[i-1]
        db = b[i] - b[i-1]
        if da != 0 and db != 0:
            total += 1
            if (da > 0) == (db > 0):
                same += 1
    return (same / total * 100) if total > 0 else 0


def track_registers(addrs):
    """Show the value of specific registers across all snapshots."""
    snapshots = _load_snapshots()
    if not snapshots:
        print("No snapshots found. Run 'identify_registers.py snapshot' first.")
        return

    print(f"Tracking registers {addrs} across {len(snapshots)} snapshots:\n")
    header = f"{'Snapshot':<20} " + " ".join(f"{a:>8}" for a in addrs)
    print(header)
    print("-" * len(header))

    for snap in snapshots:
        ts = snap["timestamp"]
        vals = []
        for a in addrs:
            v = snap["registers"].get(str(a), None)
            if v is None:
                vals.append(f"{'N/A':>8}")
            else:
                signed = v if v < 32768 else v - 65536
                vals.append(f"{signed:>8}")
        print(f"{ts:<20} " + " ".join(vals))


def _load_snapshots():
    """Load all snapshot files sorted by timestamp."""
    snapshot_dir = Path(SNAPSHOT_DIR)
    if not snapshot_dir.exists():
        return []

    snapshots = []
    for f in sorted(snapshot_dir.glob("snapshot_*.json")):
        with open(f) as fh:
            snapshots.append(json.load(fh))
    return snapshots


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  identify_registers.py snapshot              Take a new snapshot")
        print("  identify_registers.py analyze               Correlate unknowns across snapshots")
        print("  identify_registers.py track <addr> [addr..] Track specific registers over time")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "snapshot":
        take_snapshot()
    elif cmd == "analyze":
        analyze_correlations()
    elif cmd == "track":
        if len(sys.argv) < 3:
            print("Provide register addresses to track.", file=sys.stderr)
            sys.exit(1)
        addrs = [int(a) for a in sys.argv[2:]]
        track_registers(addrs)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
