#!/usr/bin/env python3
"""
Generate single-file assembly for each bank with real 8051 instructions.
Uses proper labels for all branches - no raw bytes.
"""

import os
import re
import sys
from disasm8051 import Disassembler, INSTRUCTIONS

# Well-known labels from reverse engineering
KNOWN_LABELS = {
    0x0000: ("reset_vector", "Reset vector - jumps to main"),
    0x0003: ("ext0_isr_vector", "External interrupt 0 vector"),
    0x000b: ("timer0_isr_vector", "Timer 0 interrupt vector"),
    0x0013: ("ext1_isr_vector", "External interrupt 1 vector"),
    0x001b: ("timer1_isr_vector", "Timer 1 interrupt vector"),
    0x0023: ("serial_isr_vector", "Serial interrupt vector"),
    0x002b: ("timer2_isr_vector", "Timer 2 interrupt vector"),
    0x030a: ("sys_init", "System initialization"),
    0x0e5b: ("ext0_isr", "External interrupt 0 handler"),
    0x431a: ("main_entry", "Main entry point"),
    0x4352: ("main_loop", "Main processing loop"),
    0x4486: ("timer1_isr", "Timer 1 interrupt handler"),
    0x50db: ("common_handler", "Common handler routine"),
    0x0bfd: ("mul16x16", "16x16 bit multiplication"),
    0x0c9e: ("add32", "32-bit addition"),
    0x0cab: ("sub32", "32-bit subtraction"),
    0x0cb9: ("mul32", "32-bit multiplication"),
    0x0d08: ("or32", "32-bit OR"),
    0x0d15: ("xor32", "32-bit XOR"),
    0x0d46: ("shl32", "32-bit shift left"),
    0x0d78: ("idata_load_dword", "Load 32-bit from IDATA"),
    0x0d84: ("xdata_load_dword", "Load 32-bit from XDATA"),
}


def parse_header_labels(src_dir):
    """Parse function addresses from header files."""
    labels = dict(KNOWN_LABELS)
    if not os.path.exists(src_dir):
        return labels

    for root, dirs, files in os.walk(src_dir):
        for fname in files:
            if fname.endswith('.h') or fname.endswith('.c'):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r') as f:
                        content = f.read()
                    for match in re.finditer(r'/\*\s*0x([0-9a-fA-F]+)-0x[0-9a-fA-F]+\s*\*/', content):
                        addr = int(match.group(1), 16)
                        start = max(0, match.start() - 300)
                        preceding = content[start:match.start()]
                        func_match = re.search(r'(\w+)\s*\([^)]*\)\s*;?\s*$', preceding)
                        if func_match and addr not in labels:
                            labels[addr] = (func_match.group(1), f"from {fname}")
                except Exception:
                    pass
    return labels


def find_function_boundaries(data, start_addr, end_addr, call_targets):
    """Find function boundaries based on RET instructions and call targets."""
    boundaries = set()
    boundaries.add(start_addr)  # First address is always a boundary

    # All call targets are function starts
    for target in call_targets:
        if start_addr <= target < end_addr:
            boundaries.add(target)

    return sorted(boundaries)


def collect_targets_for_bank(data, start_file, end_file, base_addr):
    """Collect all branch targets and instruction addresses for a bank."""
    region_data = data[start_file:end_file]
    disasm = Disassembler(region_data, base_addr, {}, use_raw_branches=False)

    # Collect both branch targets and all instruction start addresses
    instruction_addrs = set()
    offset = 0
    while offset < len(region_data):
        addr = base_addr + offset
        instruction_addrs.add(addr)
        _, size, _ = disasm.disassemble_instruction(offset)
        offset += size

    return disasm.branch_targets, disasm.call_targets, instruction_addrs


def generate_labels(branch_targets, call_targets, known_labels, base_addr, end_addr):
    """Generate label names for all targets."""
    all_labels = {}

    # Add known labels first
    for addr, info in known_labels.items():
        if base_addr <= addr < end_addr:
            all_labels[addr] = info

    # Generate labels for branch targets
    for target in sorted(branch_targets):
        if base_addr <= target < end_addr and target not in all_labels:
            if target in call_targets:
                all_labels[target] = f'func_{target:04x}'
            else:
                all_labels[target] = f'L_{target:04x}'

    return all_labels


def format_instruction_line(instr, addr, hex_bytes, comment_col=56):
    """Format an instruction line with aligned comments."""
    # Build the instruction part (with leading tab)
    line = f'\t{instr}'
    # If instruction already has a comment (from .db raw bytes), append address at end
    if ';' in instr:
        padding = max(1, comment_col - len(line.expandtabs(8)))
        return f'{line}{" " * padding}[{addr:04x}]\n'
    else:
        # Pad to comment column and add comment
        padding = max(1, comment_col - len(line.expandtabs(8)))
        return f'{line}{" " * padding}; {addr:04x}: {hex_bytes}\n'


def generate_bank_asm(data, output_path, start_file, end_file, base_addr, bank_name, known_labels):
    """Generate a single assembly file for a bank with real instructions."""

    region_data = data[start_file:end_file]
    region_size = end_file - start_file
    end_addr = base_addr + region_size

    print(f"Generating {bank_name}: 0x{base_addr:04x}-0x{end_addr:04x} ({region_size} bytes)")

    # First pass: collect all targets and instruction addresses
    branch_targets, call_targets, instruction_addrs = collect_targets_for_bank(data, start_file, end_file, base_addr)
    print(f"  Found {len(branch_targets)} branch targets, {len(call_targets)} call targets")
    print(f"  Found {len(instruction_addrs)} instruction addresses")

    # Generate labels - only for valid targets within this bank at instruction boundaries
    valid_branch_targets = set()
    for target in branch_targets:
        if base_addr <= target < end_addr and target in instruction_addrs:
            valid_branch_targets.add(target)
    valid_call_targets = call_targets & instruction_addrs

    all_labels = generate_labels(valid_branch_targets, valid_call_targets, known_labels, base_addr, end_addr)
    print(f"  Total labels: {len(all_labels)}")

    # Find function boundaries for section comments
    func_boundaries = find_function_boundaries(data, base_addr, end_addr, valid_call_targets)
    print(f"  Found {len(func_boundaries)} function boundaries")

    # Create disassembler with labels, valid targets, and bank end
    disasm = Disassembler(region_data, base_addr, all_labels, use_raw_branches=False,
                          valid_targets=instruction_addrs, bank_end=end_addr)

    with open(output_path, 'w') as f:
        f.write(f""";
; ASM2464PD Firmware - {bank_name}
; Address range: 0x{base_addr:04x}-0x{end_addr:04x}
; File offset: 0x{start_file:05x}-0x{end_file:05x}
;
; This file is part of the exact fw.bin reconstruction.
; DO NOT modify unless you verify the build still matches!
;

\t.module\t{bank_name}
\t.area\tCODE_{bank_name.upper()}\t(ABS,CODE)
\t.org\t0x{base_addr:04x}

""")

        # Track current function for comments
        current_func_idx = 0
        last_was_ret = False

        # Disassemble
        offset = 0
        while offset < len(region_data):
            addr = base_addr + offset

            # Check if we're entering a new function
            while current_func_idx < len(func_boundaries) - 1 and addr >= func_boundaries[current_func_idx + 1]:
                current_func_idx += 1

            # Add section separator at function boundaries
            if addr in func_boundaries and addr in call_targets:
                f.write(f'\n; {"=" * 60}\n')
                f.write(f'; Function: 0x{addr:04x}\n')
                f.write(f'; {"=" * 60}\n')

            # Add label if this is a target
            if addr in all_labels:
                label = all_labels[addr]
                if isinstance(label, tuple):
                    name, desc = label
                    f.write(f'\n; {desc}\n')
                    f.write(f'{name}:\n')
                else:
                    f.write(f'\n{label}:\n')

            # Disassemble instruction
            instr, size, _ = disasm.disassemble_instruction(offset)

            if instr:
                hex_bytes = ' '.join(f'{region_data[offset+i]:02x}' for i in range(size))
                f.write(format_instruction_line(instr, addr, hex_bytes))
                # Track if this was a ret/reti for spacing
                last_was_ret = instr.strip() in ('ret', 'reti')
            else:
                b = region_data[offset]
                f.write(format_instruction_line(f'.db\t#0x{b:02x}', addr, f'{b:02x}'))
                size = 1
                last_was_ret = False

            offset += size

    return region_size, len(all_labels)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    fw_path = os.path.join(project_root, 'fw.bin')
    src_dir = os.path.join(project_root, 'src')
    output_dir = script_dir

    if len(sys.argv) > 1:
        fw_path = sys.argv[1]

    with open(fw_path, 'rb') as f:
        data = f.read()

    print(f"Firmware size: {len(data)} bytes (0x{len(data):05x})")

    # Parse known labels from C source
    known_labels = parse_header_labels(src_dir)
    print(f"Found {len(known_labels)} known labels from headers\n")

    # Generate Bank 0 (0x0000-0xFFFF in file, 0x0000-0xFFFF in memory)
    bank0_size = min(0x10000, len(data))
    bank0_path = os.path.join(output_dir, 'bank0.asm')
    size0, labels0 = generate_bank_asm(data, bank0_path, 0, bank0_size, 0, 'bank0', known_labels)

    # Generate Bank 1 (0x10000+ in file, 0x8000+ in memory)
    if len(data) > 0x10000:
        bank1_size = len(data) - 0x10000
        bank1_path = os.path.join(output_dir, 'bank1.asm')
        # Bank 1 labels need different handling - addresses are 0x8000+ but file offset is 0x10000+
        bank1_labels = {}
        for addr, info in known_labels.items():
            if addr >= 0x10000:
                # Convert file address to mapped address
                mapped = 0x8000 + (addr - 0x10000)
                bank1_labels[mapped] = info
        size1, labels1 = generate_bank_asm(data, bank1_path, 0x10000, len(data), 0x8000, 'bank1', bank1_labels)

    print(f"\nGenerated: bank0.asm ({size0} bytes, {labels0} labels)")
    if len(data) > 0x10000:
        print(f"Generated: bank1.asm ({size1} bytes, {labels1} labels)")

    print("\nRun ./build.sh to build and verify.")


if __name__ == '__main__':
    main()
