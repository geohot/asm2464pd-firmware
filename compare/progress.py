#!/usr/bin/env python3
"""
Track reconstruction progress by comparing function ranges.

Parses function address comments from source files and compares
with the original firmware.

Usage:
    python3 progress.py <original.bin> [<built.bin>]
"""

import sys
import re
from pathlib import Path
import argparse


# Pattern to match function address comments
# Examples:
#   /* Address: 0x431a-0x43d2 (184 bytes) */
#   /* 0x5418-0x541e (7 bytes) */
#   * Address: 0x9a9c-0x9aa2 (7 bytes)
ADDR_PATTERN = re.compile(
    r'(?:Address:\s*)?0x([0-9a-fA-F]+)\s*-\s*0x([0-9a-fA-F]+)',
    re.IGNORECASE
)

# Pattern to match Bank 1 address comments
# Example:
#   * Bank 1 Address: 0x839c-0x83b8 (29 bytes) [actual addr: 0x1039c]
BANK1_PATTERN = re.compile(
    r'Bank\s*1\s*Address:\s*0x([0-9a-fA-F]+)\s*-\s*0x([0-9a-fA-F]+)',
    re.IGNORECASE
)


def read_binary(path):
    """Read binary file."""
    with open(path, 'rb') as f:
        return f.read()


def find_functions_in_file(filepath):
    """Extract function addresses from C source file."""
    functions = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find bank 1 functions first (they have special addresses)
    for match in BANK1_PATTERN.finditer(content):
        start = int(match.group(1), 16)
        end = int(match.group(2), 16)
        # Bank 1 addresses are 0x8000-based in code, but file offset is +0x8000
        actual_start = 0x10000 + (start - 0x8000) if start >= 0x8000 else start + 0x8000
        actual_end = 0x10000 + (end - 0x8000) if end >= 0x8000 else end + 0x8000
        functions.append({
            'start': actual_start,
            'end': actual_end,
            'size': end - start,
            'bank': 1,
            'file': str(filepath)
        })

    # Find regular functions
    for match in ADDR_PATTERN.finditer(content):
        start = int(match.group(1), 16)
        end = int(match.group(2), 16)
        # Skip if this looks like a Bank 1 address already found
        if start >= 0x8000 and end < 0x10000:
            # Check if we already have this as bank 1
            continue
        functions.append({
            'start': start,
            'end': end,
            'size': end - start,
            'bank': 0 if start < 0x10000 else 1,
            'file': str(filepath)
        })

    return functions


def find_all_functions(src_dir):
    """Find all function addresses in source files."""
    all_functions = []

    src_path = Path(src_dir)
    for c_file in src_path.rglob('*.c'):
        funcs = find_functions_in_file(c_file)
        all_functions.extend(funcs)

    # Also check header files
    for h_file in src_path.rglob('*.h'):
        funcs = find_functions_in_file(h_file)
        all_functions.extend(funcs)

    # Sort by start address and remove duplicates
    seen = set()
    unique = []
    for f in sorted(all_functions, key=lambda x: x['start']):
        key = (f['start'], f['end'])
        if key not in seen:
            seen.add(key)
            unique.append(f)

    return unique


def check_function_match(orig_data, func):
    """Check if a function's bytes exist in original firmware."""
    start = func['start']
    end = func['end']

    if start >= len(orig_data) or end > len(orig_data):
        return None, "OUT_OF_RANGE"

    # For now, we can't check actual match without built firmware
    return orig_data[start:end], "ORIGINAL"


def compare_function(orig_data, built_data, func):
    """Compare a function between original and built firmware."""
    start = func['start']
    end = func['end']

    if start >= len(orig_data):
        return "ORIG_OUT_OF_RANGE"
    if start >= len(built_data):
        return "BUILT_OUT_OF_RANGE"

    orig_end = min(end, len(orig_data))
    built_end = min(end, len(built_data))

    orig_bytes = orig_data[start:orig_end]
    built_bytes = built_data[start:built_end]

    if len(orig_bytes) != len(built_bytes):
        return "SIZE_MISMATCH"

    if orig_bytes == built_bytes:
        return "MATCH"

    # Count differences
    diff = sum(1 for a, b in zip(orig_bytes, built_bytes) if a != b)
    pct = 100 * diff / len(orig_bytes)
    return f"DIFF({diff}/{len(orig_bytes)}, {pct:.0f}%)"


def main():
    parser = argparse.ArgumentParser(description='Track reconstruction progress')
    parser.add_argument('original', help='Original firmware binary')
    parser.add_argument('built', nargs='?', help='Built firmware binary (optional)')
    parser.add_argument('--src', default='src', help='Source directory (default: src)')
    args = parser.parse_args()

    # Read firmware files
    try:
        orig_data = read_binary(args.original)
    except FileNotFoundError:
        print(f"Error: Original firmware not found: {args.original}")
        return 1

    built_data = None
    if args.built:
        try:
            built_data = read_binary(args.built)
        except FileNotFoundError:
            print(f"Warning: Built firmware not found: {args.built}")

    # Find all functions in source
    src_dir = Path(args.src)
    if not src_dir.exists():
        print(f"Error: Source directory not found: {args.src}")
        return 1

    functions = find_all_functions(src_dir)

    print(f"Original firmware: {len(orig_data)} bytes ({len(orig_data):#x})")
    if built_data:
        print(f"Built firmware:    {len(built_data)} bytes ({len(built_data):#x})")
    print(f"Functions found:   {len(functions)}")
    print()

    # Calculate coverage
    total_bytes = 0
    covered = set()
    for func in functions:
        total_bytes += func['size']
        for addr in range(func['start'], func['end']):
            if addr < len(orig_data):
                covered.add(addr)

    coverage_pct = 100 * len(covered) / len(orig_data) if orig_data else 0
    print(f"Coverage: {len(covered)}/{len(orig_data)} bytes ({coverage_pct:.1f}%)")
    print()

    # Print function status
    print(f"{'Address':^15} {'Size':>6} {'Bank':>4} {'Status':^20} File")
    print("-" * 80)

    for func in functions:
        addr_str = f"{func['start']:#06x}-{func['end']:#06x}"
        size_str = f"{func['size']}"
        bank_str = f"{func['bank']}"

        if built_data:
            status = compare_function(orig_data, built_data, func)
        else:
            status = "NOT_BUILT"

        # Truncate file path
        file_str = func['file']
        if len(file_str) > 25:
            file_str = "..." + file_str[-22:]

        print(f"{addr_str:^15} {size_str:>6} {bank_str:>4} {status:^20} {file_str}")

    # Summary
    if built_data:
        matches = sum(1 for f in functions
                     if compare_function(orig_data, built_data, f) == "MATCH")
        print()
        print(f"Matching functions: {matches}/{len(functions)}")


if __name__ == '__main__':
    sys.exit(main())
