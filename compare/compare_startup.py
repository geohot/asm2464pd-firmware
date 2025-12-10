#!/usr/bin/env python3
"""
Compare compiled startup_0016 with original firmware bytes.
"""
import sys

def parse_hex(hex_file):
    """Parse Intel HEX file and return address:byte dict"""
    data = {}
    with open(hex_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line.startswith(':'):
                continue
            n = int(line[1:3], 16)
            addr = int(line[3:7], 16)
            t = int(line[7:9], 16)
            if t == 0:  # Data record
                for i in range(n):
                    data[addr + i] = int(line[9 + i*2:11 + i*2], 16)
    return data

def read_bin(bin_file, start, length):
    """Read bytes from binary file"""
    with open(bin_file, 'rb') as f:
        f.seek(start)
        return list(f.read(length))

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <hex_file> <orig_bin>")
        sys.exit(1)

    hex_file = sys.argv[1]
    orig_bin = sys.argv[2]

    # Parse compiled hex
    compiled = parse_hex(hex_file)

    if not compiled:
        print("No data in hex file")
        sys.exit(1)

    min_addr = min(compiled.keys())
    max_addr = max(compiled.keys())
    print(f"Compiled code at 0x{min_addr:04X}-0x{max_addr:04X} ({max_addr - min_addr + 1} bytes)")

    # Read original startup_0016 (0x0016-0x0103)
    orig_start = 0x0016
    orig_end = 0x0104
    orig_bytes = read_bin(orig_bin, orig_start, orig_end - orig_start)
    print(f"Original startup_0016 at 0x{orig_start:04X}-0x{orig_end:04X} ({len(orig_bytes)} bytes)")

    # Compare instruction patterns
    compiled_bytes = [compiled[a] for a in range(min_addr, max_addr + 1)]

    print(f"\nCompiled bytes ({len(compiled_bytes)} bytes):")
    for i in range(0, len(compiled_bytes), 16):
        chunk = compiled_bytes[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        print(f"  0x{min_addr + i:04X}: {hex_str}")

    print(f"\nOriginal bytes ({len(orig_bytes)} bytes):")
    for i in range(0, len(orig_bytes), 16):
        chunk = orig_bytes[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        print(f"  0x{orig_start + i:04X}: {hex_str}")

    # Count matching patterns
    print("\n--- Pattern Analysis ---")

    # Look for key instruction sequences
    patterns = [
        ("CLR A", [0xe4]),
        ("MOV DPTR,#0001", [0x90, 0x00, 0x01]),
        ("MOVX @DPTR,A", [0xf0]),
        ("MOV A,@R0", [0xe6]),
        ("MOV A,@R1", [0xe7]),
        ("XRL A,@R0", [0x66]),
        ("INC R0", [0x08]),
        ("INC R1", [0x09]),
        ("RET", [0x22]),
    ]

    for name, pattern in patterns:
        orig_count = 0
        comp_count = 0
        for i in range(len(orig_bytes) - len(pattern) + 1):
            if orig_bytes[i:i+len(pattern)] == pattern:
                orig_count += 1
        for i in range(len(compiled_bytes) - len(pattern) + 1):
            if compiled_bytes[i:i+len(pattern)] == pattern:
                comp_count += 1
        print(f"  {name}: orig={orig_count}, compiled={comp_count}")

if __name__ == "__main__":
    main()
