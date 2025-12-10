#!/usr/bin/env python3
"""
Analyze firmware binary and compare with original.

Provides detailed analysis of:
- Function placement
- Code size
- Byte-for-byte matching at specific addresses

Usage:
    python3 analyze.py <firmware.bin>
    python3 analyze.py <original.bin> <built.bin> --func 0x431a
"""

import sys
import argparse
import re
from pathlib import Path


def read_binary(path):
    """Read binary file."""
    with open(path, 'rb') as f:
        return f.read()


def disasm_8051(data, addr, count=10):
    """Basic 8051 disassembly (for reference only)."""
    # Simple opcode table for common instructions
    opcodes = {
        0x00: ("nop", 1),
        0x02: ("ljmp", 3),
        0x12: ("lcall", 3),
        0x22: ("ret", 1),
        0x32: ("reti", 1),
        0x74: ("mov a,#", 2),
        0x75: ("mov direct,#", 3),
        0x78: ("mov r0,#", 2),
        0x79: ("mov r1,#", 2),
        0x7a: ("mov r2,#", 2),
        0x7b: ("mov r3,#", 2),
        0x7c: ("mov r4,#", 2),
        0x7d: ("mov r5,#", 2),
        0x7e: ("mov r6,#", 2),
        0x7f: ("mov r7,#", 2),
        0x80: ("sjmp", 2),
        0x90: ("mov dptr,#", 3),
        0xe0: ("movx a,@dptr", 1),
        0xe4: ("clr a", 1),
        0xf0: ("movx @dptr,a", 1),
    }

    lines = []
    offset = 0
    for _ in range(count):
        if addr + offset >= len(data):
            break
        op = data[addr + offset]
        if op in opcodes:
            mnem, size = opcodes[op]
            if size == 1:
                lines.append(f"{addr+offset:04x}: {op:02x}          {mnem}")
            elif size == 2:
                b1 = data[addr + offset + 1] if addr + offset + 1 < len(data) else 0
                lines.append(f"{addr+offset:04x}: {op:02x} {b1:02x}       {mnem}{b1:02x}")
            elif size == 3:
                b1 = data[addr + offset + 1] if addr + offset + 1 < len(data) else 0
                b2 = data[addr + offset + 2] if addr + offset + 2 < len(data) else 0
                val = (b1 << 8) | b2
                lines.append(f"{addr+offset:04x}: {op:02x} {b1:02x} {b2:02x}    {mnem}{val:04x}")
            offset += size
        else:
            lines.append(f"{addr+offset:04x}: {op:02x}          db {op:02x}h")
            offset += 1
    return lines


def analyze_firmware(data):
    """Analyze firmware structure."""
    print(f"Firmware size: {len(data)} bytes ({len(data):#x})")
    print()

    # Check for reset vector at 0x0000
    if len(data) >= 3:
        op = data[0]
        if op == 0x02:  # LJMP
            addr = (data[1] << 8) | data[2]
            print(f"Reset vector: LJMP {addr:#06x}")
        elif op == 0x80:  # SJMP
            rel = data[1] if data[1] < 128 else data[1] - 256
            addr = 2 + rel
            print(f"Reset vector: SJMP {addr:#06x}")
        else:
            print(f"Reset vector: {op:#04x} (not a jump)")

    # Check interrupt vectors
    vectors = [
        (0x0003, "INT0"),
        (0x000B, "Timer0"),
        (0x0013, "INT1"),
        (0x001B, "Timer1"),
        (0x0023, "Serial"),
        (0x002B, "INT2 (extended)"),
        (0x0033, "INT3 (extended)"),
        (0x003B, "INT4 (extended)"),
    ]

    print("\nInterrupt vectors:")
    for addr, name in vectors:
        if addr + 2 < len(data):
            op = data[addr]
            if op == 0x02:  # LJMP
                target = (data[addr+1] << 8) | data[addr+2]
                print(f"  {addr:#06x} {name}: LJMP {target:#06x}")
            elif op == 0x32:  # RETI
                print(f"  {addr:#06x} {name}: RETI (unused)")
            elif op == 0x00:  # NOP
                print(f"  {addr:#06x} {name}: NOP (unused)")


def compare_at_address(orig, built, addr, length=32):
    """Compare two binaries at a specific address."""
    print(f"\nComparison at {addr:#06x} ({length} bytes):")

    if addr >= len(orig):
        print(f"  Address out of range in original (size: {len(orig):#x})")
        return

    if addr >= len(built):
        print(f"  Address out of range in built (size: {len(built):#x})")
        return

    end = min(addr + length, len(orig), len(built))
    orig_slice = orig[addr:end]
    built_slice = built[addr:end]

    match = orig_slice == built_slice
    print(f"  Match: {'YES' if match else 'NO'}")

    if not match:
        print(f"  Original: {orig_slice[:16].hex(' ')}")
        print(f"  Built:    {built_slice[:16].hex(' ')}")

        # Find first difference
        for i, (a, b) in enumerate(zip(orig_slice, built_slice)):
            if a != b:
                print(f"  First diff at offset +{i:#x}: orig={a:#04x} built={b:#04x}")
                break


def main():
    parser = argparse.ArgumentParser(description='Analyze firmware binary')
    parser.add_argument('files', nargs='+', help='Firmware file(s) to analyze')
    parser.add_argument('--func', type=lambda x: int(x, 0), action='append',
                        help='Function address to analyze (can be repeated)')
    parser.add_argument('--disasm', type=lambda x: int(x, 0),
                        help='Disassemble at address')
    args = parser.parse_args()

    if len(args.files) == 1:
        # Single file analysis
        data = read_binary(args.files[0])
        print(f"Analyzing: {args.files[0]}")
        print("=" * 60)
        analyze_firmware(data)

        if args.disasm is not None:
            print(f"\nDisassembly at {args.disasm:#06x}:")
            for line in disasm_8051(data, args.disasm):
                print(f"  {line}")

    elif len(args.files) == 2:
        # Comparison mode
        orig = read_binary(args.files[0])
        built = read_binary(args.files[1])

        print(f"Comparing: {args.files[0]} vs {args.files[1]}")
        print("=" * 60)
        print(f"Original size: {len(orig)} bytes")
        print(f"Built size:    {len(built)} bytes")

        if args.func:
            for addr in args.func:
                compare_at_address(orig, built, addr)
        else:
            # Compare start of file
            compare_at_address(orig, built, 0, 64)

    else:
        print("Error: Provide 1 or 2 files")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
