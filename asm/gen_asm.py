#!/usr/bin/env python3
"""
Generate SDCC assembly file from fw.bin

This script creates assembly files that reconstruct fw.bin exactly.
Uses SDCC's sdas8051 assembler syntax.
"""

import sys
import os

# Known functions/labels from the codebase
KNOWN_LABELS_BANK0 = {
    0x0000: 'reset_vector',
    0x0003: 'ext0_vector',
    0x0006: 'func_timer0_overlap',
    0x0013: 'timer1_vector',
    0x030a: 'init_030a',
    0x0e5b: 'ext0_isr',
    0x431a: 'main_entry',
    0x4352: 'main_loop',
    0x4486: 'timer1_isr',
    0x50db: 'func_50db',
}

def generate_bank_asm(data, output_path, start_addr, end_addr, org_addr, module_name, area_name, bytes_per_line=16):
    """Generate assembly for a bank."""

    with open(output_path, 'w') as f:
        f.write(f""";
; ASM2464PD Firmware - {module_name}
; Generated from fw.bin
; File range: 0x{start_addr:05x}-0x{end_addr:05x}
; Mapped at: 0x{org_addr:04x}
;

\t.module\t{module_name}
\t.area\t{area_name}\t(ABS,CODE)
\t.org\t0x{org_addr:04x}

""")

        addr = start_addr
        mapped = org_addr
        while addr < end_addr:
            # Check for known labels (only in bank 0)
            if start_addr == 0 and mapped in KNOWN_LABELS_BANK0:
                f.write(f"\n; === {KNOWN_LABELS_BANK0[mapped]} ===\n")
                f.write(f"{KNOWN_LABELS_BANK0[mapped]}:\n")

            # Determine chunk size (align to known labels)
            chunk_size = bytes_per_line
            if start_addr == 0:
                for label_addr in KNOWN_LABELS_BANK0:
                    if mapped < label_addr < mapped + chunk_size:
                        chunk_size = label_addr - mapped
                        break

            # Ensure we don't exceed end
            if addr + chunk_size > end_addr:
                chunk_size = end_addr - addr

            # Write bytes - SDCC format uses #0xNN
            chunk = data[addr:addr + chunk_size]
            hex_bytes = ', '.join(f'#0x{b:02x}' for b in chunk)

            # Add ASCII comment
            ascii_chars = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)

            f.write(f"\t.db\t{hex_bytes}\t; {addr:05x}: {ascii_chars}\n")

            addr += len(chunk)
            mapped += len(chunk)

    print(f"Generated: {output_path} ({end_addr - start_addr} bytes)")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    fw_path = os.path.join(project_root, 'fw.bin')

    if len(sys.argv) > 1:
        fw_path = sys.argv[1]

    with open(fw_path, 'rb') as f:
        data = f.read()

    print(f"Firmware size: {len(data)} bytes (0x{len(data):05x})")

    # Bank 0: file 0x0000-0xFFFF, mapped at 0x0000
    bank0_end = min(len(data), 0x10000)
    generate_bank_asm(data,
                      os.path.join(script_dir, 'bank0.asm'),
                      start_addr=0,
                      end_addr=bank0_end,
                      org_addr=0x0000,
                      module_name='bank0',
                      area_name='CABS')

    # Bank 1: file 0x10000+, mapped at 0x8000
    if len(data) > 0x10000:
        generate_bank_asm(data,
                          os.path.join(script_dir, 'bank1.asm'),
                          start_addr=0x10000,
                          end_addr=len(data),
                          org_addr=0x8000,
                          module_name='bank1',
                          area_name='BANK1')


if __name__ == '__main__':
    main()
