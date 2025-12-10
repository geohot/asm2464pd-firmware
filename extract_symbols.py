#!/usr/bin/env python3
"""
Extract symbols from C source files and headers and generate ghidra_import_symbols.py.
"""

import re
import os
from collections import defaultdict

def extract_function_addresses(src_dir):
    """Extract function addresses from C source file comments and header declarations."""
    functions = {}
    bank1_functions = {}

    # Pattern for "Address: 0xNNNN" comments in .c files (with optional Bank 1)
    addr_pattern = re.compile(r'\*\s*Address:\s*0x([0-9a-fA-F]{4,5})')
    # Bank 1 patterns: either "Bank 1 Address: 0xNNNN" or "Address: 0xNNNN (Bank 1)"
    addr_bank1_pattern = re.compile(r'\*\s*(?:Bank 1 Address:\s*0x([0-9a-fA-F]{4,5})|Address:\s*0x([0-9a-fA-F]{4,5}).*\(Bank 1\))')
    # Pattern for function definition that follows
    func_pattern = re.compile(r'^(?:void|uint8_t|uint16_t|uint32_t|int8_t|int16_t|int32_t|bool|__bit)\s+(\w+)\s*\(')

    # Pattern for header file declarations with inline address comments
    # e.g.: void func_name(void);  /* 0xNNNN-0xNNNN */
    # Bank 1 pattern must be checked first, then Bank 0 pattern excludes "(Bank 1)"
    bank1_header_pattern = re.compile(
        r'^(?:void|uint8_t|uint16_t|uint32_t|int8_t|int16_t|int32_t|bool|__bit|__xdata\s+uint8_t\s+\*)\s*'
        r'(\w+)\s*\([^)]*\)\s*;\s*/\*\s*0x([0-9a-fA-F]{4,5})'
        r'(?:-0x[0-9a-fA-F]+)?'
        r'\s*\(Bank 1\)\s*\*/'
    )
    # Bank 0 pattern - must NOT contain "(Bank 1)"
    header_pattern = re.compile(
        r'^(?:void|uint8_t|uint16_t|uint32_t|int8_t|int16_t|int32_t|bool|__bit|__xdata\s+uint8_t\s+\*)\s*'
        r'(\w+)\s*\([^)]*\)\s*;\s*/\*\s*0x([0-9a-fA-F]{4,5})'
        r'(?:-0x[0-9a-fA-F]+)?'
        r'\s*\*/'
    )

    for root, dirs, files in os.walk(src_dir):
        for fname in files:
            fpath = os.path.join(root, fname)

            if fname.endswith('.c'):
                # Extract from .c files using comment-then-function pattern
                with open(fpath, 'r') as f:
                    lines = f.readlines()

                pending_addr = None
                pending_is_bank1 = False
                for i, line in enumerate(lines):
                    # Check for Bank 1 address comment first
                    m = addr_bank1_pattern.search(line)
                    if m:
                        # Either group 1 or group 2 will have the address
                        addr_str = m.group(1) or m.group(2)
                        pending_addr = int(addr_str, 16)
                        pending_is_bank1 = True
                        continue

                    # Check for regular address comment
                    m = addr_pattern.search(line)
                    if m:
                        pending_addr = int(m.group(1), 16)
                        pending_is_bank1 = False

                    # Check for function definition
                    if pending_addr is not None:
                        m = func_pattern.match(line.strip())
                        if m:
                            func_name = m.group(1)
                            if pending_is_bank1:
                                # Bank 1: CPU address -> file offset
                                file_offset = pending_addr + 0x8000
                                if file_offset not in bank1_functions:
                                    bank1_functions[file_offset] = func_name
                            else:
                                if pending_addr not in functions:
                                    functions[pending_addr] = func_name
                            pending_addr = None
                            pending_is_bank1 = False
                        elif line.strip() and not line.strip().startswith('*') and not line.strip().startswith('/'):
                            # Reset if we hit non-comment, non-function line
                            if not line.strip().startswith('/*') and '*/' not in line:
                                pending_addr = None
                                pending_is_bank1 = False

            elif fname.endswith('.h'):
                # Extract from .h files using inline comment pattern
                with open(fpath, 'r') as f:
                    for line in f:
                        # Check for Bank 1 functions first
                        m = bank1_header_pattern.search(line)
                        if m:
                            func_name = m.group(1)
                            addr = int(m.group(2), 16)
                            # Bank 1: CPU address 0x8000-0xFFFF maps to file offset 0x10000-0x17FFF
                            # addr + 0x8000 gives file offset
                            file_offset = addr + 0x8000
                            if file_offset not in bank1_functions:
                                bank1_functions[file_offset] = func_name
                            continue

                        # Check for regular (Bank 0) functions
                        m = header_pattern.search(line)
                        if m:
                            func_name = m.group(1)
                            addr = int(m.group(2), 16)
                            if addr not in functions:
                                functions[addr] = func_name

    # Remove any Bank 0 functions that have a Bank 1 equivalent
    # (Bank 1 file offset = Bank 0 addr + 0x8000 for addrs 0x8000-0xFFFF)
    bank0_to_remove = []
    for addr in functions:
        if 0x8000 <= addr < 0x10000:
            bank1_offset = addr + 0x8000
            if bank1_offset in bank1_functions:
                bank0_to_remove.append(addr)
    for addr in bank0_to_remove:
        del functions[addr]

    # Merge bank1 into functions dict
    functions.update(bank1_functions)
    return functions

def extract_registers(registers_h):
    """Extract register definitions from registers.h."""
    registers = {}

    # Pattern for #define REG_NAME XDATA_REG8(0xNNNN)
    pattern = re.compile(r'#define\s+(REG_\w+)\s+XDATA_REG\d+\(0x([0-9a-fA-F]+)\)')

    with open(registers_h, 'r') as f:
        for line in f:
            m = pattern.search(line)
            if m:
                name = m.group(1)
                addr = int(m.group(2), 16)
                if addr not in registers:
                    registers[addr] = name

    return registers

def extract_globals(globals_h):
    """Extract global definitions from globals.h."""
    globals_dict = {}

    # Pattern for #define G_NAME XDATA_VAR8(0xNNNN)
    pattern = re.compile(r'#define\s+(G_\w+)\s+XDATA_VAR8\(0x([0-9a-fA-F]+)\)')

    with open(globals_h, 'r') as f:
        for line in f:
            m = pattern.search(line)
            if m:
                name = m.group(1)
                addr = int(m.group(2), 16)
                if addr not in globals_dict:
                    globals_dict[addr] = name

    # Also extract IDATA variables with __at()
    idata_pattern = re.compile(r'__idata\s+__at\(0x([0-9a-fA-F]+)\)\s+\w+\s+(\w+)')

    with open(globals_h, 'r') as f:
        for line in f:
            m = idata_pattern.search(line)
            if m:
                addr = int(m.group(1), 16)
                name = m.group(2)
                # IDATA is internal RAM, mark differently
                if addr not in globals_dict:
                    globals_dict[addr] = f"IDATA_{name}"

    return globals_dict

def load_existing_ghidra_symbols(ghidra_py):
    """Load existing symbols from ghidra_import_symbols.py."""
    existing_funcs = set()
    existing_regs = set()
    existing_globals = set()

    with open(ghidra_py, 'r') as f:
        content = f.read()

    # Extract function addresses
    func_pattern = re.compile(r'\(0x([0-9a-fA-F]+),\s*"(\w+)"\)')
    for m in func_pattern.finditer(content):
        addr = int(m.group(1), 16)
        existing_funcs.add(addr)
        existing_regs.add(addr)
        existing_globals.add(addr)

    return existing_funcs, existing_regs, existing_globals

def generate_ghidra_script(functions, registers, globals_dict, output_path):
    """Generate the complete ghidra_import_symbols.py file."""

    # Split functions into bank0 and bank1
    bank0_funcs = sorted([(addr, name) for addr, name in functions.items() if addr < 0x10000])
    bank1_funcs = sorted([(addr, name) for addr, name in functions.items() if addr >= 0x10000])

    # Filter registers (>= 0x6000) and globals (< 0x6000 or flash buffer area)
    reg_list = sorted([(addr, name) for addr, name in registers.items() if addr >= 0x6000])
    glob_list = sorted([(addr, name) for addr, name in globals_dict.items()
                        if addr < 0x6000 or (addr >= 0x7000 and addr < 0x8000)])

    script = '''# Ghidra Python Script for AS2464 USB4/NVMe Firmware
# Imports function names, register labels, and global variables from reverse engineering work
#
# To use: Run in Ghidra's Script Manager on the loaded fw.bin
# The script handles both CODE_BANK0 (0x0000-0xFFFF) and CODE_BANK1 (0x10000-0x17FFF)
#
# Memory Layout:
#   CODE_BANK0: 0x0000-0xFFFF  (first 64KB, always accessible)
#   CODE_BANK1: 0x10000-0x17FFF (second bank, mapped to 0x8000-0xFFFF when DPX=1)
#   EXTMEM: 0x0000-0xFFFF (XDATA space - RAM, MMIO registers)
#
# Auto-generated by extract_symbols.py from C source files
#
# @author reverse-asm2464 project
# @category ASMedia.AS2464

from ghidra.program.model.symbol import SourceType
from ghidra.program.model.address import AddressSet

def create_function_if_needed(addr, name):
    """Create function at address if it doesn't exist, then set the name"""
    func = getFunctionAt(addr)
    if func is None:
        createFunction(addr, name)
        func = getFunctionAt(addr)
    if func is not None:
        func.setName(name, SourceType.USER_DEFINED)
        print("Added function: {} at {}".format(name, addr))
        return True
    else:
        # Try to just set a label
        createLabel(addr, name, True)
        print("Added label: {} at {}".format(name, addr))
        return True
    return False

def create_label(addr, name):
    """Create a label at the given address"""
    try:
        createLabel(addr, name, True)
        print("Added label: {} at {}".format(name, addr))
        return True
    except:
        print("Failed to add label: {} at {}".format(name, addr))
        return False

def add_bank0_functions():
    """Add all known Bank 0 function names (0x0000-0xFFFF)"""

    # Bank 0 Function mappings: (address, name)
    # These are verified addresses from our C reimplementation
    functions = [
'''

    # Add bank0 functions
    for addr, name in bank0_funcs:
        script += f'        (0x{addr:04x}, "{name}"),\n'

    script += '''    ]

    count = 0
    for addr_int, name in functions:
        try:
            # Bank 0 functions are in CODE space at their actual address
            addr = toAddr("CODE:{:04X}".format(addr_int))
            if create_function_if_needed(addr, name):
                count += 1
        except:
            try:
                addr = toAddr(addr_int)
                if create_function_if_needed(addr, name):
                    count += 1
            except Exception as e:
                print("Error adding Bank 0 function {} at 0x{:04X}: {}".format(name, addr_int, e))

    return count

def add_bank1_functions():
    """Add all known Bank 1 function names (file offset 0x10000-0x17FFF, CPU addr 0x8000-0xFFFF)"""

    # Bank 1 Function mappings: (file_offset, name)
    # File offset = CPU address + 0x8000 for addresses >= 0x8000
    # CPU addresses in Bank 1 are 0x8000-0xFFFF but mapped from file 0x10000-0x17FFF
    #
    # In Ghidra with CODE_BANK1 overlay:
    #   - Use file offset directly (0x10000+) OR
    #   - Use CPU addr + CODE_BANK1 overlay
    functions = [
'''

    # Add bank1 functions
    for addr, name in bank1_funcs:
        script += f'        (0x{addr:05x}, "{name}"),\n'

    script += '''    ]

    count = 0
    for file_offset, name in functions:
        try:
            # Convert file offset to CPU address for CODE_BANK1 overlay
            # File offset 0x10000 = CPU 0x8000, so CPU addr = file_offset - 0x8000
            cpu_addr = file_offset - 0x8000
            addr = toAddr("CODE_BANK1:{:04X}".format(cpu_addr))
            if create_function_if_needed(addr, name):
                count += 1
        except:
            try:
                # Try direct file offset
                addr = toAddr(file_offset)
                if create_function_if_needed(addr, name):
                    count += 1
            except Exception as e:
                print("Error adding Bank 1 function {} at file offset 0x{:05X}: {}".format(name, file_offset, e))

    return count

def add_registers():
    """Add all known register labels to EXTMEM space"""

    # Register mappings: (address, name)
    # These are hardware registers (>= 0x6000)
    registers = [
'''

    # Add registers
    for addr, name in reg_list:
        script += f'        (0x{addr:04X}, "{name}"),\n'

    script += '''    ]

    count = 0
    for addr_int, name in registers:
        try:
            # Try EXTMEM space first
            addr = toAddr("EXTMEM:{:04X}".format(addr_int))
            if create_label(addr, name):
                count += 1
        except:
            try:
                # Fall back to direct address
                addr = toAddr(addr_int)
                if create_label(addr, name):
                    count += 1
            except Exception as e:
                print("Error adding register {} at 0x{:04X}: {}".format(name, addr_int, e))

    return count

def add_globals():
    """Add all known global variable labels to EXTMEM space"""

    # Global variable mappings: (address, name)
    # These are RAM locations (< 0x6000)
    globals_list = [
'''

    # Add globals
    for addr, name in glob_list:
        script += f'        (0x{addr:04X}, "{name}"),\n'

    script += '''    ]

    count = 0
    for addr_int, name in globals_list:
        try:
            # Try EXTMEM space first
            addr = toAddr("EXTMEM:{:04X}".format(addr_int))
            if create_label(addr, name):
                count += 1
        except:
            try:
                # Fall back to direct address
                addr = toAddr(addr_int)
                if create_label(addr, name):
                    count += 1
            except Exception as e:
                print("Error adding global {} at 0x{:04X}: {}".format(name, addr_int, e))

    return count

def run():
    """Main entry point"""
    print("=" * 70)
    print("AS2464 USB4/NVMe Firmware Symbol Import Script")
    print("Auto-generated from C reimplementation project")
    print("")
    print("This script handles both CODE_BANK0 and CODE_BANK1 sections:")
    print("  CODE_BANK0: 0x0000-0xFFFF  (always accessible)")
    print("  CODE_BANK1: 0x10000-0x17FFF (file offsets, mapped to 0x8000-0xFFFF)")
    print("=" * 70)

    print("\\nAdding Bank 0 function names (0x0000-0xFFFF)...")
    func0_count = add_bank0_functions()
    print("Added {} Bank 0 functions".format(func0_count))

    print("\\nAdding Bank 1 function names (file 0x10000-0x17FFF)...")
    func1_count = add_bank1_functions()
    print("Added {} Bank 1 functions".format(func1_count))

    print("\\nAdding register labels (EXTMEM)...")
    reg_count = add_registers()
    print("Added {} registers".format(reg_count))

    print("\\nAdding global variable labels (EXTMEM)...")
    glob_count = add_globals()
    print("Added {} globals".format(glob_count))

    print("\\n" + "=" * 70)
    print("Import complete!")
    print("Total symbols added: {}".format(func0_count + func1_count + reg_count + glob_count))
    print("  Bank 0 functions: {}".format(func0_count))
    print("  Bank 1 functions: {}".format(func1_count))
    print("  Registers: {}".format(reg_count))
    print("  Globals: {}".format(glob_count))
    print("=" * 70)

# Run the script
run()
'''

    with open(output_path, 'w') as f:
        f.write(script)

    print(f"Generated {output_path}")
    print(f"  Bank 0 functions: {len(bank0_funcs)}")
    print(f"  Bank 1 functions: {len(bank1_funcs)}")
    print(f"  Registers: {len(reg_list)}")
    print(f"  Globals: {len(glob_list)}")


def main():
    base_dir = '/home/light/fun/asm2464pd-firmware'
    src_dir = os.path.join(base_dir, 'src')
    registers_h = os.path.join(base_dir, 'src/include/registers.h')
    globals_h = os.path.join(base_dir, 'src/include/globals.h')
    output_py = os.path.join(base_dir, 'ghidra_import_symbols.py')

    print("Extracting function addresses from C source files...")
    functions = extract_function_addresses(src_dir)
    print(f"Found {len(functions)} functions with addresses")

    print("\nExtracting registers from registers.h...")
    registers = extract_registers(registers_h)
    print(f"Found {len(registers)} registers")

    print("\nExtracting globals from globals.h...")
    globals_dict = extract_globals(globals_h)
    print(f"Found {len(globals_dict)} globals")

    print("\nGenerating ghidra_import_symbols.py...")
    generate_ghidra_script(functions, registers, globals_dict, output_py)


if __name__ == '__main__':
    main()
