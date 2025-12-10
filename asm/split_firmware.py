#!/usr/bin/env python3
"""
Split fw.bin into logical assembly modules with real 8051 instructions.

Uses global symbols for cross-module references, allowing the linker
to resolve branch targets properly.
"""

import os
import re
import sys
from disasm8051 import Disassembler, INSTRUCTIONS

# Firmware regions
BANK0_REGIONS = [
    (0x0000, 0x0300, "vectors", "Interrupt vectors and early initialization"),
    (0x0300, 0x0600, "isr_core", "Core ISR implementations"),
    (0x0600, 0x0e00, "math_utils", "Math routines and low-level utilities"),
    (0x0e00, 0x1200, "isr_handlers", "Interrupt handlers"),
    (0x1200, 0x2000, "usb", "USB subsystem"),
    (0x2000, 0x3000, "cmd", "Command processing"),
    (0x3000, 0x4000, "dma_buffer", "DMA and buffer management"),
    (0x4000, 0x5000, "main", "Main loop and system initialization"),
    (0x5000, 0x6000, "scsi", "SCSI command processing"),
    (0x6000, 0x7000, "flash", "Flash memory operations"),
    (0x7000, 0x8000, "pcie", "PCIe and NVMe subsystem"),
    (0x8000, 0x9000, "power_phy", "Power management and PHY control"),
    (0x9000, 0xa000, "timer_event", "Timer and event handling"),
    (0xa000, 0xb000, "protocol", "Protocol handlers"),
    (0xb000, 0xc000, "utils", "Utility functions"),
    (0xc000, 0xd000, "vendor", "Vendor-specific commands"),
    (0xd000, 0xe000, "error", "Error handling and logging"),
    (0xe000, 0xf000, "dispatch", "Dispatch and queue handling"),
    (0xf000, 0x10000, "misc", "Miscellaneous functions"),
]

BANK1_REGIONS = [
    (0x10000, 0x12000, "bank1_handlers", "Bank 1 event handlers"),
    (0x12000, 0x14000, "bank1_protocol", "Bank 1 protocol code"),
    (0x14000, 0x16000, "bank1_utils", "Bank 1 utility functions"),
    (0x16000, 0x18000, "bank1_misc", "Bank 1 miscellaneous"),
]

# Well-known labels
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


def get_region_for_addr(addr, all_regions):
    """Find which region an address belongs to."""
    for start, end, name, _ in all_regions:
        if start <= addr < end:
            return name
    return None


def first_pass_all(data, all_regions, labels):
    """
    First pass over entire firmware to collect all branch targets.
    Returns: (all_targets, targets_by_region)
    """
    all_targets = set()
    call_targets = set()

    for start, end, name, _ in all_regions:
        if start >= len(data):
            continue
        actual_end = min(end, len(data))
        if start >= actual_end:
            continue

        # For bank1, calculate mapped address
        if start >= 0x10000:
            mapped_addr = 0x8000 + (start - 0x10000)
        else:
            mapped_addr = start

        region_data = data[start:actual_end]
        disasm = Disassembler(region_data, mapped_addr, {}, use_raw_branches=False)
        disasm.first_pass()
        all_targets.update(disasm.branch_targets)
        call_targets.update(disasm.call_targets)

    # Generate labels for all targets
    all_labels = dict(labels)
    for target in sorted(all_targets):
        if target not in all_labels:
            if target in call_targets:
                all_labels[target] = f'func_{target:04x}'
            else:
                all_labels[target] = f'L_{target:04x}'

    return all_targets, all_labels


def generate_module(data, output_path, start_addr, end_addr, mapped_addr,
                    module_name, description, all_labels, all_targets,
                    all_regions, is_bank1=False):
    """Generate a module file with disassembled code."""

    region_data = data[start_addr:end_addr]
    region_end_mapped = mapped_addr + (end_addr - start_addr)

    # Find labels defined in this region
    local_labels = set()
    external_labels = set()

    for target in all_targets:
        if mapped_addr <= target < region_end_mapped:
            local_labels.add(target)
        else:
            # Check if any instruction in this region references this target
            external_labels.add(target)

    # Create disassembler - use real branch instructions with labels
    disasm = Disassembler(region_data, mapped_addr, all_labels, use_raw_branches=False)

    bank_str = "Bank 1" if is_bank1 else "Bank 0"
    file_range = f"0x{start_addr:05x}-0x{end_addr:05x}"
    mapped_range = f"0x{mapped_addr:04x}-0x{region_end_mapped:04x}"

    with open(output_path, 'w') as f:
        f.write(f""";
; ASM2464PD Firmware - {module_name}
; {description}
;
; {bank_str} File Range: {file_range}
; Mapped Address: {mapped_range}
;
; This file is part of the exact fw.bin reconstruction.
; DO NOT modify unless you verify the build still matches!
;

\t.module\t{module_name}
\t.area\tCODE_{module_name.upper()}\t(ABS,CODE)
\t.org\t0x{mapped_addr:04x}

""")

        # Disassemble
        offset = 0
        while offset < len(region_data):
            addr = mapped_addr + offset

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
                f.write(f'\t{instr:<40}; {addr:04x}: {hex_bytes}\n')
            else:
                b = region_data[offset]
                f.write(f'\t.db\t#0x{b:02x}\t\t\t\t\t\t; {addr:04x}\n')
                size = 1

            offset += size

    return end_addr - start_addr


def generate_symbols_include(output_dir, all_labels, all_regions, data):
    """Generate a symbols.inc file with all global declarations."""
    symbols_path = os.path.join(output_dir, "symbols.inc")

    # Group labels by region
    labels_by_region = {}
    for addr, label in all_labels.items():
        if isinstance(label, tuple):
            label = label[0]

        region_name = None
        for start, end, name, _ in all_regions:
            if start >= 0x10000:
                mapped = 0x8000 + (start - 0x10000)
                mapped_end = mapped + min(end, len(data)) - start
            else:
                mapped = start
                mapped_end = min(end, len(data))

            if mapped <= addr < mapped_end:
                region_name = name
                break

        if region_name:
            if region_name not in labels_by_region:
                labels_by_region[region_name] = []
            labels_by_region[region_name].append((addr, label))

    with open(symbols_path, 'w') as f:
        f.write(""";
; ASM2464PD Firmware - Global Symbols
; Auto-generated - do not edit
;

""")
        for region_name in sorted(labels_by_region.keys()):
            f.write(f"; {region_name}\n")
            for addr, label in sorted(labels_by_region[region_name]):
                f.write(f"\t.globl\t{label:<24}; 0x{addr:04x}\n")
            f.write("\n")

    print(f"  Generated: symbols.inc ({len(all_labels)} symbols)")


def split_firmware(fw_path, output_dir, src_dir=None):
    """Split firmware into modules with global symbol resolution."""

    with open(fw_path, 'rb') as f:
        data = f.read()

    print(f"Firmware size: {len(data)} bytes (0x{len(data):05x})")

    labels = parse_header_labels(src_dir) if src_dir else dict(KNOWN_LABELS)
    print(f"Found {len(labels)} labeled addresses from headers")

    os.makedirs(output_dir, exist_ok=True)

    # Combine all regions
    all_regions = list(BANK0_REGIONS)
    if len(data) > 0x10000:
        all_regions.extend(BANK1_REGIONS)

    # First pass: collect all targets across all regions
    print("\nFirst pass: collecting branch targets...")
    all_targets, all_labels = first_pass_all(data, all_regions, labels)
    print(f"  Found {len(all_targets)} branch targets")
    print(f"  Total labels: {len(all_labels)}")

    # Generate symbols include file
    generate_symbols_include(output_dir, all_labels, all_regions, data)

    bank0_modules = []
    bank1_modules = []

    # Generate bank 0 modules
    print("\nBank 0 modules:")
    for start, end, name, desc in BANK0_REGIONS:
        if start >= len(data):
            continue
        actual_end = min(end, len(data), 0x10000)
        if start >= actual_end:
            continue

        bank0_modules.append((name, start, actual_end))
        output_path = os.path.join(output_dir, f"{name}.asm")

        size = generate_module(data, output_path, start, actual_end, start,
                               name, desc, all_labels, all_targets,
                               all_regions, is_bank1=False)
        print(f"  {name}.asm ({size} bytes)")

    # Generate bank 1 modules
    if len(data) > 0x10000:
        print("\nBank 1 modules:")
        for start, end, name, desc in BANK1_REGIONS:
            if start >= len(data):
                continue
            actual_end = min(end, len(data))
            if start >= actual_end:
                continue

            mapped_addr = 0x8000 + (start - 0x10000)
            bank1_modules.append((name, start, actual_end, mapped_addr))
            output_path = os.path.join(output_dir, f"{name}.asm")

            size = generate_module(data, output_path, start, actual_end, mapped_addr,
                                   name, desc, all_labels, all_targets,
                                   all_regions, is_bank1=True)
            print(f"  {name}.asm ({size} bytes)")

    # Generate main include file
    generate_main_file(output_dir, bank0_modules, bank1_modules)

    return bank0_modules, bank1_modules


def generate_main_file(output_dir, bank0_modules, bank1_modules):
    """Generate the main orchestrating file."""
    main_path = os.path.join(output_dir, "firmware.asm")
    with open(main_path, 'w') as f:
        f.write(""";
; ASM2464PD Firmware - Main Assembly File
;
; Build with: ./build.sh
; IMPORTANT: The built firmware MUST be byte-for-byte identical to fw.bin!
;

\t.module\tfirmware

; Include global symbol declarations
\t.include "symbols.inc"

; =============================================================================
; Bank 0 Modules (0x0000-0xFFFF)
; =============================================================================

""")
        for name, start, end in bank0_modules:
            f.write(f"\t.include \"{name}.asm\"\t; 0x{start:04x}-0x{end:04x}\n")

        if bank1_modules:
            f.write("""
; =============================================================================
; Bank 1 Modules (0x10000+, mapped at 0x8000)
; =============================================================================

""")
            for name, start, end, mapped in bank1_modules:
                f.write(f"\t.include \"{name}.asm\"\t; 0x{start:05x} -> 0x{mapped:04x}\n")

        f.write("\n\t.end\n")

    print(f"\nGenerated: firmware.asm")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    fw_path = os.path.join(project_root, 'fw.bin')
    src_dir = os.path.join(project_root, 'src')
    output_dir = os.path.join(script_dir, 'src')

    if len(sys.argv) > 1:
        fw_path = sys.argv[1]

    print("Splitting firmware into modules with global symbols...")
    print(f"Output directory: {output_dir}\n")

    split_firmware(fw_path, output_dir, src_dir)

    print("\nDone! Run ./build.sh to verify the build still matches.")


if __name__ == '__main__':
    main()
