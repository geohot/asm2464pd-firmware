# TODO Generator

Scripts to generate an up-to-date TODO.md for the ASM2464PD firmware RE project.

## Quick Start

```bash
cd /path/to/asm2464pd-firmware
python3 gen_todo/generate_todo.py
```

This will overwrite `TODO.md` with current progress.

## What It Does

The script analyzes multiple sources to build a complete picture:

1. **fw.bin** - Scans for all LCALL instructions to find function entry points and counts how often each is called (priority metric)

2. **ghidra.c** - Extracts `FUN_CODE_XXXX` patterns to find documented functions

3. **src/** - Scans all .c and .h files for address references (functions we've implemented)

4. **src/app/stubs.c** - Identifies actual stub functions (empty/placeholder bodies vs real implementations)

## Output Structure

The generated TODO.md contains:

- **Progress Summary** - Total remaining, stub count, firmware size
- **High Priority (10+ calls)** - Most-called missing functions
- **By Category** - Grouped by address range:
  - 0x0000-0x0FFF: Utility functions
  - 0x1000-0x1FFF: State machine helpers
  - 0x2000-0x3FFF: Protocol state machines
  - 0x4000-0x5FFF: SCSI/USB mass storage
  - 0x8000-0x9FFF: NVMe/PCIe config
  - 0xA000-0xBFFF: Queue/handler functions
  - 0xC000-0xDFFF: Event/error handlers
  - 0xE000-0xFFFF: Bank1 high address handlers

## Stub Detection

A function in stubs.c is considered a "stub" (needs implementation) if:
- Body has ≤2 statements
- No control flow (if/while/for/switch)
- No register or global access (REG_*, G_*)

Functions with actual logic are counted as implemented even if in stubs.c.

## Metrics

- **Function count** is the primary progress metric
- **File size** uses dense code only (~79KB, excludes 19KB padding)
- **Call count** indicates priority (frequently called = more important)

## Requirements

- Python 3.6+
- No external dependencies

## Files

- `generate_todo.py` - Main script
- `README.md` - This file
