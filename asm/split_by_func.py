#!/usr/bin/env python3
"""
Split bank assembly files into function-based modules.
Module boundaries are aligned to actual function start addresses.
"""

import os
import re
import sys

# Target module boundaries (will be adjusted to nearest function)
# Format: (start_addr, end_addr, name, desc)
BANK0_TARGETS = [
    (0x0000, 0x0300, "vectors", "Interrupt vectors and reset"),
    (0x0300, 0x0600, "isr", "Interrupt service routines"),
    (0x0600, 0x0e00, "math", "Math and utility functions"),
    (0x0e00, 0x1200, "handlers", "Event handlers"),
    (0x1200, 0x2000, "usb", "USB subsystem"),
    (0x2000, 0x3000, "cmd", "Command processing"),
    (0x3000, 0x4000, "dma", "DMA and buffer management"),
    (0x4000, 0x5000, "main", "Main loop and initialization"),
    (0x5000, 0x6000, "scsi", "SCSI command processing"),
    (0x6000, 0x8000, "data", "Data tables and padding"),  # Combined flash+pcie area (no code)
    (0x8000, 0x9000, "power", "Power management"),
    (0x9000, 0xa000, "timer", "Timer and event handling"),
    (0xa000, 0xb000, "protocol", "Protocol handlers"),
    (0xb000, 0xc000, "util", "Utility functions"),
    (0xc000, 0xd000, "vendor", "Vendor-specific commands"),
    (0xd000, 0xe000, "error", "Error handling"),
    (0xe000, 0xf000, "dispatch", "Dispatch and queues"),
    (0xf000, 0x10000, "misc", "Miscellaneous functions"),
]

BANK1_TARGETS = [
    (0x8000, 0xa000, "b1_handlers", "Bank 1 event handlers"),
    (0xa000, 0xc000, "b1_protocol", "Bank 1 protocol code"),
    (0xc000, 0xe000, "b1_util", "Bank 1 utilities"),
    (0xe000, 0x10000, "b1_misc", "Bank 1 miscellaneous"),
]


def parse_asm_file(filepath):
    """Parse an assembly file and extract addresses and content."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Find header end (after .org) and base address
    header_end = 0
    base_addr = 0

    for i, line in enumerate(lines):
        if line.strip().startswith('.org'):
            header_end = i + 1
            match = re.search(r'\.org\s+(0x[0-9a-f]+)', line)
            if match:
                base_addr = int(match.group(1), 16)

    # Build address-to-line mapping
    addr_to_line = {}
    for i, line in enumerate(lines):
        # Look for address in comment
        match = re.search(r';\s*([0-9a-f]{4}):', line)
        if match:
            addr = int(match.group(1), 16)
            if addr not in addr_to_line:
                addr_to_line[addr] = i

    # Find all function start addresses
    func_addrs = set()
    for i, line in enumerate(lines):
        # Match both old format "; ============ Function at 0x..." and new format "; Function: 0x..."
        match = re.match(r'^; (?:============ )?Function(?:: | at )(0x[0-9a-f]+)', line)
        if match:
            addr = int(match.group(1), 16)
            func_addrs.add(addr)

    return lines, header_end, base_addr, addr_to_line, func_addrs


def find_line_for_addr(addr_to_line, target_addr):
    """Find the line number for an address, or nearest before it."""
    if target_addr in addr_to_line:
        return addr_to_line[target_addr]

    # Find nearest address <= target
    candidates = [a for a in addr_to_line.keys() if a <= target_addr]
    if candidates:
        nearest = max(candidates)
        return addr_to_line[nearest]

    return None


def find_nearest_func_before(func_addrs, target_addr):
    """Find the nearest function address <= target_addr."""
    candidates = [a for a in func_addrs if a <= target_addr]
    if candidates:
        return max(candidates)
    return None


def split_into_modules(lines, header_end, targets, addr_to_line, func_addrs):
    """Split the assembly into modules based on address ranges."""
    modules = []

    # Find the max address in the file
    max_addr = max(addr_to_line.keys()) if addr_to_line else 0

    for i, (start_addr, end_addr, name, desc) in enumerate(targets):
        # Find the line for the start address
        start_line = find_line_for_addr(addr_to_line, start_addr)

        # For end_line: if end_addr is beyond the file, include to the end
        if end_addr > max_addr:
            end_line = len(lines)
        else:
            end_line = find_line_for_addr(addr_to_line, end_addr)

        if start_line is None:
            continue

        if end_line is None:
            end_line = len(lines)

        # Adjust start to include any function marker or label before it
        while start_line > header_end:
            prev_line = lines[start_line - 1].strip()
            if (prev_line.startswith('; ===') or prev_line.startswith('; Function:') or
                prev_line.endswith(':') or prev_line == ''):
                start_line -= 1
            else:
                break

        # Adjust end to EXCLUDE any label/comment that belongs to the next module
        # (but only if we're not at end of file)
        if end_addr <= max_addr:
            while end_line > start_line:
                prev_line = lines[end_line - 1].strip()
                if (prev_line.startswith('; ===') or prev_line.startswith('; Function:') or
                    prev_line.endswith(':') or prev_line == '' or prev_line.startswith('; from')):
                    end_line -= 1
                else:
                    break

        # For the first module, include from after header
        if i == 0:
            start_line = header_end + 1

        module_lines = lines[start_line:end_line]

        # Count functions in this module
        func_count = sum(1 for a in func_addrs if start_addr <= a < end_addr)

        modules.append({
            'name': name,
            'desc': desc,
            'start_addr': start_addr,
            'end_addr': end_addr,
            'lines': module_lines,
            'start_line': start_line,
            'end_line': end_line,
            'func_count': func_count,
        })

    return modules, lines[:header_end + 1]


def write_module(output_dir, module, bank_name, header_lines, is_first=False):
    """Write a module to a file."""
    filepath = os.path.join(output_dir, f"{module['name']}.asm")

    with open(filepath, 'w') as f:
        # Write module header
        f.write(f""";
; ASM2464PD Firmware - {module['name']}
; {module['desc']}
;
; Address range: 0x{module['start_addr']:04x}""")

        if module['end_addr']:
            f.write(f"-0x{module['end_addr']:04x}")
        f.write(f"""
;
; This file is part of the exact fw.bin reconstruction.
;

""")

        # Only first module needs .module, .area, .org
        if is_first:
            for line in header_lines:
                f.write(line)
            f.write('\n')

        # Write module content
        for line in module['lines']:
            f.write(line)

    return filepath


def generate_makefile(output_dir, modules, bank_name):
    """Generate a modules list file for the build."""
    filepath = os.path.join(output_dir, f"{bank_name}_modules.txt")

    with open(filepath, 'w') as f:
        for module in modules:
            f.write(f"{module['name']}.asm\n")

    return filepath


def split_bank(input_file, output_dir, targets, bank_name):
    """Split a bank assembly file into modules."""
    print(f"\nProcessing {bank_name}...")

    lines, header_end, base_addr, addr_to_line, func_addrs = parse_asm_file(input_file)
    print(f"  Found {len(func_addrs)} functions, {len(addr_to_line)} addresses")

    modules, header_lines = split_into_modules(lines, header_end, targets, addr_to_line, func_addrs)
    print(f"  Created {len(modules)} modules:")

    os.makedirs(output_dir, exist_ok=True)

    for i, module in enumerate(modules):
        filepath = write_module(output_dir, module, bank_name, header_lines, is_first=(i == 0))
        size = module['end_addr'] - module['start_addr']
        print(f"    {module['name']}.asm: 0x{module['start_addr']:04x}-0x{module['end_addr']:04x} ({len(module['lines'])} lines, {module['func_count']} funcs)")

    generate_makefile(output_dir, modules, bank_name)

    return modules


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    bank0_asm = os.path.join(script_dir, 'bank0.asm')
    bank1_asm = os.path.join(script_dir, 'bank1.asm')
    output_dir = os.path.join(script_dir, 'src')

    if not os.path.exists(bank0_asm):
        print(f"Error: {bank0_asm} not found. Run ./build.sh regen first.")
        sys.exit(1)

    print("Splitting bank files into function-based modules...")

    # Split bank 0
    bank0_modules = split_bank(bank0_asm, output_dir, BANK0_TARGETS, 'bank0')

    # Split bank 1
    if os.path.exists(bank1_asm):
        bank1_modules = split_bank(bank1_asm, output_dir, BANK1_TARGETS, 'bank1')

    print(f"\nOutput directory: {output_dir}")
    print("Run ./build.sh to build and verify.")


if __name__ == '__main__':
    main()
