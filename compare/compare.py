#!/usr/bin/env python3
"""
Compare built firmware with original firmware.

Usage:
    python3 compare.py <original.bin> <built.bin> [--addr ADDRESS] [--len LENGTH]

Options:
    --addr ADDRESS   Start address for comparison (hex, default: 0)
    --len LENGTH     Number of bytes to compare (default: all)
    --verbose        Show detailed differences
"""

import sys
import argparse


def read_file(path, max_size=None):
    """Read binary file."""
    with open(path, 'rb') as f:
        data = f.read()
    if max_size and len(data) > max_size:
        data = data[:max_size]
    return data


def compare_bytes(orig, built, start=0, length=None, verbose=False):
    """Compare two byte sequences and report differences."""
    if length is None:
        length = max(len(orig), len(built)) - start

    end = start + length
    orig_slice = orig[start:end] if start < len(orig) else b''
    built_slice = built[start:end] if start < len(built) else b''

    # Pad to same length
    max_len = max(len(orig_slice), len(built_slice))
    orig_slice = orig_slice.ljust(max_len, b'\x00')
    built_slice = built_slice.ljust(max_len, b'\x00')

    # Count differences
    diff_count = 0
    diff_regions = []
    in_diff = False
    diff_start = 0

    for i in range(max_len):
        if orig_slice[i] != built_slice[i]:
            diff_count += 1
            if not in_diff:
                in_diff = True
                diff_start = i
        else:
            if in_diff:
                in_diff = False
                diff_regions.append((diff_start, i))

    if in_diff:
        diff_regions.append((diff_start, max_len))

    # Report
    print(f"Comparison: {start:#06x} to {start + max_len:#06x} ({max_len} bytes)")
    print(f"Original size: {len(orig)} bytes")
    print(f"Built size: {len(built)} bytes")
    print()

    if diff_count == 0:
        print("MATCH: No differences found!")
        return 0

    print(f"DIFFERENCES: {diff_count} bytes differ ({100*diff_count/max_len:.1f}%)")
    print(f"Diff regions: {len(diff_regions)}")
    print()

    # Show first few differences
    if verbose or len(diff_regions) <= 10:
        max_show = 20 if verbose else 5
        shown = 0
        for region_start, region_end in diff_regions[:max_show]:
            addr = start + region_start
            size = region_end - region_start
            print(f"  {addr:#06x}-{addr+size-1:#06x} ({size} bytes)")
            if verbose and size <= 32:
                orig_bytes = ' '.join(f'{b:02x}' for b in orig_slice[region_start:region_end])
                built_bytes = ' '.join(f'{b:02x}' for b in built_slice[region_start:region_end])
                print(f"    orig:  {orig_bytes}")
                print(f"    built: {built_bytes}")
            shown += 1
        if len(diff_regions) > max_show:
            print(f"  ... and {len(diff_regions) - max_show} more regions")
    else:
        print(f"  (Use --verbose to see details)")

    return diff_count


def find_function(data, addr):
    """Find the function boundaries at an address."""
    # Simple heuristic: look for RET (0x22) or LJMP (0x02)
    # This is a rough approximation
    start = addr
    end = addr

    # Look backwards for function start
    while start > 0:
        if data[start-1] in (0x22, 0x32):  # RET or RETI
            break
        start -= 1

    # Look forwards for function end
    while end < len(data) - 1:
        if data[end] in (0x22, 0x32):  # RET or RETI
            end += 1
            break
        end += 1

    return start, end


def main():
    parser = argparse.ArgumentParser(description='Compare firmware binaries')
    parser.add_argument('original', help='Original firmware file')
    parser.add_argument('built', help='Built firmware file')
    parser.add_argument('--addr', type=lambda x: int(x, 0), default=0,
                        help='Start address (hex)')
    parser.add_argument('--len', type=lambda x: int(x, 0), default=None,
                        help='Length to compare')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed differences')
    args = parser.parse_args()

    try:
        orig = read_file(args.original)
        built = read_file(args.built)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    diff_count = compare_bytes(orig, built, args.addr, args.len, args.verbose)
    return 0 if diff_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
