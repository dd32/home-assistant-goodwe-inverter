"""
Modbus TCP register scanner for GoodWe ESA (EHA-G20) inverter.

Scans holding registers and logs all non-zero responses.
Uses pymodbus to connect via Modbus TCP.

Usage:
    .venv/bin/python scan_registers.py [--start 35000] [--end 48000] [--output scan_results.csv]
"""

import argparse
import csv
import sys
import time

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException

INVERTER_IP = "192.168.1.107"
INVERTER_PORT = 502
SLAVE_ADDRESS = 0xF7  # 247

# Modbus max registers per read request
BATCH_SIZE = 125

# Delay between requests (seconds) to avoid overwhelming the inverter
REQUEST_DELAY = 0.05


def scan_registers(client, start, end, slave):
    """Scan holding registers in batches, yielding (address, value) for non-zero registers."""
    addr = start
    while addr < end:
        count = min(BATCH_SIZE, end - addr)
        try:
            result = client.read_holding_registers(addr, count=count, device_id=slave)
            if result.isError():
                # Likely illegal data address — try smaller chunks to find valid ones
                if count > 1:
                    yield from _scan_singles(client, addr, addr + count, slave)
                addr += count
                time.sleep(REQUEST_DELAY)
                continue

            for i, value in enumerate(result.registers):
                if value != 0:
                    yield (addr + i, value)

        except ModbusIOException:
            # Connection issue on this batch — try individual registers
            if count > 1:
                yield from _scan_singles(client, addr, addr + count, slave)
        except Exception as e:
            print(f"  Error at {addr}: {e}", file=sys.stderr)

        addr += count
        time.sleep(REQUEST_DELAY)


def _scan_singles(client, start, end, slave):
    """Fall back to reading one register at a time for a range that failed as a batch."""
    for addr in range(start, end):
        try:
            result = client.read_holding_registers(addr, count=1, device_id=slave)
            if result.isError():
                continue
            value = result.registers[0]
            if value != 0:
                yield (addr, value)
        except Exception:
            pass
        time.sleep(REQUEST_DELAY)


def main():
    parser = argparse.ArgumentParser(description="Scan GoodWe inverter Modbus holding registers")
    parser.add_argument("--ip", default=INVERTER_IP, help=f"Inverter IP (default: {INVERTER_IP})")
    parser.add_argument("--port", type=int, default=INVERTER_PORT, help=f"Modbus TCP port (default: {INVERTER_PORT})")
    parser.add_argument("--slave", type=int, default=SLAVE_ADDRESS, help=f"Slave address (default: {SLAVE_ADDRESS})")
    parser.add_argument("--start", type=int, default=35000, help="Start register address (default: 35000)")
    parser.add_argument("--end", type=int, default=48000, help="End register address (default: 48000)")
    parser.add_argument("--output", "-o", default="scan_results.csv", help="Output CSV file (default: scan_results.csv)")
    args = parser.parse_args()

    client = ModbusTcpClient(args.ip, port=args.port, timeout=3)
    if not client.connect():
        print(f"Failed to connect to {args.ip}:{args.port}", file=sys.stderr)
        sys.exit(1)

    print(f"Connected to {args.ip}:{args.port}, scanning registers {args.start}-{args.end} (slave {args.slave})...")

    results = []
    total_found = 0
    scan_start = time.time()

    try:
        for addr, value in scan_registers(client, args.start, args.end, args.slave):
            results.append((addr, value))
            total_found += 1
            # Print progress
            signed = value if value < 32768 else value - 65536
            print(f"  {addr} (0x{addr:04X}): {value} (0x{value:04X}) signed={signed}")
    except KeyboardInterrupt:
        print("\nScan interrupted by user.", file=sys.stderr)
    finally:
        client.close()

    elapsed = time.time() - scan_start
    print(f"\nScan complete: {total_found} non-zero registers found in {elapsed:.1f}s")

    # Write CSV
    with open(args.output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["address_dec", "address_hex", "value_dec", "value_hex", "value_signed"])
        for addr, value in results:
            signed = value if value < 32768 else value - 65536
            writer.writerow([addr, f"0x{addr:04X}", value, f"0x{value:04X}", signed])

    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
