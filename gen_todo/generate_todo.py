#!/usr/bin/env python3
"""
Generate TODO.md for ASM2464PD firmware reverse engineering.

This script analyzes:
1. LCALL targets in fw.bin to find all function entry points
2. ghidra.c to find documented functions
3. src/app/stubs.c to find stub functions that need implementation
4. Our existing code to find what's already implemented

Usage:
    cd /path/to/asm2464pd-firmware
    python3 gen_todo/generate_todo.py

Output: TODO.md in the project root
"""

import os
import re
import sys

def find_lcall_targets(fw_path):
    """Find all LCALL targets in firmware - these are function entry points."""
    with open(fw_path, 'rb') as f:
        data = f.read()

    call_count = {}
    for i in range(len(data) - 2):
        if data[i] == 0x12:  # LCALL opcode
            addr = (data[i+1] << 8) | data[i+2]
            addr_hex = f"{addr:04x}"
            call_count[addr_hex] = call_count.get(addr_hex, 0) + 1

    return call_count

def find_ghidra_functions(ghidra_path):
    """Extract FUN_CODE_XXXX addresses from ghidra.c."""
    if not os.path.exists(ghidra_path):
        return set()

    with open(ghidra_path) as f:
        content = f.read()

    # Find all FUN_CODE_XXXX patterns
    matches = re.findall(r'FUN_CODE_([0-9a-fA-F]{4})', content)
    return set(m.lower() for m in matches)

def find_our_addresses(src_dir):
    """Find all addresses referenced in our source code."""
    addresses = set()

    for root, dirs, files in os.walk(src_dir):
        for fname in files:
            if fname.endswith('.c') or fname.endswith('.h'):
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()

                # Find addresses in function names and comments
                # Pattern: _XXXX or 0xXXXX where XXXX is 4 hex digits
                matches = re.findall(r'(?:_|0x)([0-9a-fA-F]{4})\b', content)
                addresses.update(m.lower() for m in matches)

    return addresses

def find_stub_functions(stubs_path):
    """
    Find actual stub functions (empty/placeholder implementations).
    Returns dict of {address: function_name}
    """
    if not os.path.exists(stubs_path):
        return {}

    with open(stubs_path) as f:
        content = f.read()

    stubs = {}
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for function definition
        match = re.match(r'^(void|uint8_t|uint16_t)\s+(\w+)\s*\([^)]*\)\s*$', line)
        if match:
            func_name = match.group(2)

            # Extract address from function name
            addr_match = re.search(r'([0-9a-fA-F]{4})', func_name)
            if not addr_match:
                i += 1
                continue

            addr = addr_match.group(1).lower()

            # Check if body is trivial (stub)
            body_lines = []
            j = i + 1
            brace_count = 0
            in_body = False

            while j < len(lines):
                if '{' in lines[j]:
                    in_body = True
                    brace_count += lines[j].count('{') - lines[j].count('}')
                elif in_body:
                    brace_count += lines[j].count('{') - lines[j].count('}')
                if in_body:
                    body_lines.append(lines[j])
                if in_body and brace_count <= 0:
                    break
                j += 1

            # Check if body is short/trivial
            body = '\n'.join(body_lines)
            body_stripped = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)
            body_stripped = re.sub(r'//.*', '', body_stripped)
            body_stripped = body_stripped.replace('{', '').replace('}', '').strip()

            # Count significant statements
            statements = [s.strip() for s in body_stripped.split(';') if s.strip()]

            # It's a stub if very few statements and no real logic
            # Real implementations have: control flow, register access, global access,
            # or function calls (helper_, FUN_CODE_, dispatch_, etc.)
            has_real_logic = any(
                kw in body for kw in [
                    'while', 'for', 'if', 'switch',  # Control flow
                    'REG_', 'G_', 'I_',              # Register/global/idata access
                    'helper_', 'FUN_CODE_', 'dispatch_',  # Function calls
                    'dma_', 'cmd_', 'usb_', 'pcie_', 'nvme_',  # Driver calls
                ]
            )
            is_stub = len(statements) <= 2 and not has_real_logic

            if is_stub:
                stubs[addr] = func_name

        i += 1

    return stubs

def get_firmware_size(fw_path, build_path):
    """Get firmware sizes for progress tracking."""
    orig_size = os.path.getsize(fw_path) if os.path.exists(fw_path) else 0
    our_size = os.path.getsize(build_path) if os.path.exists(build_path) else 0

    # Dense code is about 79KB (excluding ~19KB padding)
    dense_code = 79197

    return our_size, dense_code

def categorize_address(addr_int):
    """Return category name for an address."""
    if addr_int < 0x1000:
        return 'Utility Functions (0x0000-0x0FFF)'
    elif addr_int < 0x2000:
        return 'State Machine Helpers (0x1000-0x1FFF)'
    elif addr_int < 0x4000:
        return 'Protocol State Machines (0x2000-0x3FFF)'
    elif addr_int < 0x6000:
        return 'SCSI/USB Mass Storage (0x4000-0x5FFF)'
    elif addr_int < 0xa000:
        return 'NVMe/PCIe Config (0x8000-0x9FFF)'
    elif addr_int < 0xc000:
        return 'Queue/Handler Functions (0xA000-0xBFFF)'
    elif addr_int < 0xe000:
        return 'Event/Error Handlers (0xC000-0xDFFF)'
    else:
        return 'Bank1 High (0xE000-0xFFFF)'

def generate_todo(project_root):
    """Generate TODO.md content."""

    fw_path = os.path.join(project_root, 'fw.bin')
    ghidra_path = os.path.join(project_root, 'ghidra.c')
    src_dir = os.path.join(project_root, 'src')
    stubs_path = os.path.join(project_root, 'src', 'app', 'stubs.c')
    build_path = os.path.join(project_root, 'build', 'firmware.bin')

    print("Analyzing firmware...")
    call_count = find_lcall_targets(fw_path)
    print(f"  Found {len(call_count)} LCALL targets")

    print("Analyzing ghidra.c...")
    ghidra_addrs = find_ghidra_functions(ghidra_path)
    print(f"  Found {len(ghidra_addrs)} functions in ghidra.c")

    print("Analyzing our source code...")
    our_addrs = find_our_addresses(src_dir)
    print(f"  Found {len(our_addrs)} addresses referenced")

    print("Finding stub functions...")
    stubs = find_stub_functions(stubs_path)
    print(f"  Found {len(stubs)} stub functions")

    # Find missing functions: in firmware or ghidra but not in our code
    # Plus any stubs we have
    fw_addrs = set(call_count.keys())
    all_known = fw_addrs | ghidra_addrs
    missing = (all_known - our_addrs) | set(stubs.keys())

    # Filter to code regions only
    code_regions = lambda a: (
        (0x0000 <= a < 0x5d2e) or
        (0x8000 <= a < 0xe975) or
        (0x10000 <= a < 0x17000)
    )

    missing_filtered = set()
    for addr in missing:
        try:
            a = int(addr, 16)
            if code_regions(a):
                missing_filtered.add(addr)
        except:
            pass

    print(f"  Total TODO: {len(missing_filtered)} functions")

    # Categorize
    categories = {}
    for addr in missing_filtered:
        try:
            a = int(addr, 16)
        except:
            continue

        cat = categorize_address(a)
        if cat not in categories:
            categories[cat] = []

        categories[cat].append({
            'addr': f"0x{addr}",
            'calls': call_count.get(addr, 0),
            'is_stub': addr in stubs,
            'stub_name': stubs.get(addr, ''),
        })

    # Sort each category
    for cat in categories:
        categories[cat].sort(key=lambda x: (-x['calls'], x['addr']))

    # Get sizes
    our_size, dense_size = get_firmware_size(fw_path, build_path)

    # Generate output
    output = []
    output.append("# ASM2464PD Firmware Reverse Engineering TODO")
    output.append("")
    output.append("## Progress Summary")
    output.append("")

    total = len(missing_filtered)
    total_stubs = len(stubs)
    high_priority = sum(1 for cat in categories.values()
                       for e in cat if e['calls'] >= 5)

    pct = (our_size / dense_size * 100) if dense_size > 0 else 0

    output.append(f"- **Functions remaining**: ~{total}")
    output.append(f"- **Stub functions** (empty placeholder): {total_stubs}")
    output.append(f"- **High-priority** (called 5+ times): {high_priority}")
    output.append(f"- **Firmware size**: {our_size:,} / {dense_size:,} bytes ({pct:.0f}% of actual code)")
    output.append("")
    output.append("### Metrics Note")
    output.append("")
    output.append("Function count is the primary metric. File size comparison uses dense code only (~79KB, excludes ~19KB padding).")
    output.append("SDCC generates different code than the original compiler (likely Keil C51), so byte-exact matching is not possible.")
    output.append("")
    output.append("---")
    output.append("")

    # High priority section
    output.append("## High Priority Functions (called 10+ times)")
    output.append("")
    output.append("These functions are called frequently and should be prioritized:")
    output.append("")
    output.append("| Address | Calls | Status | Name |")
    output.append("|---------|-------|--------|------|")

    all_entries = [e for cat in categories.values() for e in cat]
    all_entries.sort(key=lambda x: -x['calls'])

    for e in all_entries:
        if e['calls'] >= 10:
            status = "STUB" if e['is_stub'] else "TODO"
            name = e['stub_name'] if e['stub_name'] else "-"
            output.append(f"| {e['addr']} | {e['calls']} | {status} | {name} |")

    output.append("")
    output.append("---")
    output.append("")

    # Categories
    cat_order = [
        'Utility Functions (0x0000-0x0FFF)',
        'State Machine Helpers (0x1000-0x1FFF)',
        'Protocol State Machines (0x2000-0x3FFF)',
        'SCSI/USB Mass Storage (0x4000-0x5FFF)',
        'NVMe/PCIe Config (0x8000-0x9FFF)',
        'Queue/Handler Functions (0xA000-0xBFFF)',
        'Event/Error Handlers (0xC000-0xDFFF)',
        'Bank1 High (0xE000-0xFFFF)',
    ]

    for cat in cat_order:
        entries = categories.get(cat, [])
        if not entries:
            continue

        stubs_count = sum(1 for e in entries if e['is_stub'])
        high = sum(1 for e in entries if e['calls'] >= 5)

        output.append(f"## {cat}")
        output.append("")
        output.append(f"**Total: {len(entries)}** | Stubs: {stubs_count} | High-priority: {high}")
        output.append("")

        # Stubs
        stub_entries = [e for e in entries if e['is_stub']]
        if stub_entries:
            output.append("### Stubs (need implementation)")
            output.append("")
            for e in stub_entries:
                output.append(f"- [ ] `{e['addr']}` - {e['stub_name']} ({e['calls']} calls)")
            output.append("")

        # High priority
        hp_entries = [e for e in entries if e['calls'] >= 5 and not e['is_stub']]
        if hp_entries:
            output.append("### High Priority (5+ calls)")
            output.append("")
            for e in hp_entries:
                output.append(f"- [ ] `{e['addr']}` ({e['calls']} calls)")
            output.append("")

        # Other
        other = [e for e in entries if not e['is_stub'] and e['calls'] < 5]
        if other:
            output.append(f"### Other ({len(other)} functions)")
            output.append("")
            for e in other[:25]:
                output.append(f"- [ ] `{e['addr']}` ({e['calls']} calls)")
            if len(other) > 25:
                output.append(f"- ... and {len(other) - 25} more")

        output.append("")
        output.append("---")
        output.append("")

    # Notes
    output.append("## Notes")
    output.append("")
    output.append("### Memory Layout")
    output.append("- Bank 0 low: 0x0000-0x5D2E (~24KB code)")
    output.append("- Bank 0 high: 0x8000-0xE975 (~27KB code)")
    output.append("- Bank 1: 0x10000-0x16EBA (~28KB code, mapped to 0x8000 when active)")
    output.append("- Padding regions: ~19KB (not real code)")
    output.append("")
    output.append("### Key Subsystems")
    output.append("- **0x9000-0x9FFF**: NVMe command engine, PCIe config")
    output.append("- **0xA000-0xAFFF**: Admin commands, queue management")
    output.append("- **0xB000-0xBFFF**: PCIe TLP handlers, register helpers")
    output.append("- **0xC000-0xCFFF**: Error logging, event handlers")
    output.append("- **0xD000-0xDFFF**: Power management, PHY config")
    output.append("- **0xE000-0xEFFF**: Bank1 handlers (via dispatch stubs)")

    return '\n'.join(output)

def main():
    # Find project root (directory containing fw.bin)
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # Assume we're in gen_todo/ or project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(script_dir) == 'gen_todo':
            project_root = os.path.dirname(script_dir)
        else:
            project_root = script_dir

    if not os.path.exists(os.path.join(project_root, 'fw.bin')):
        print(f"Error: fw.bin not found in {project_root}")
        print("Usage: python3 generate_todo.py [project_root]")
        sys.exit(1)

    print(f"Project root: {project_root}")
    print("")

    content = generate_todo(project_root)

    output_path = os.path.join(project_root, 'TODO.md')
    with open(output_path, 'w') as f:
        f.write(content)

    print("")
    print(f"Written to: {output_path}")

if __name__ == '__main__':
    main()
