# ASM2464PD Firmware - Assembly Reconstruction

This directory contains an exact byte-for-byte reconstruction of `fw.bin` using SDCC assembly with real 8051 instructions.

## Critical Rule

**The built firmware MUST be byte-for-byte identical to the original `fw.bin`.**

Every build automatically verifies this. If the comparison fails, the code is broken and must be fixed before committing.

## Directory Structure

```
asm/
├── bank0.asm           # Bank 0 code (0x0000-0xFFFF) - real 8051 assembly
├── bank1.asm           # Bank 1 code (0x8000-0xFEDC) - real 8051 assembly
├── build/              # Build artifacts
├── build.sh            # Build script
├── gen_bank.py         # Assembly generator with real instructions
├── disasm8051.py       # 8051 disassembler
└── README.md           # This file
```

## Usage

```bash
./build.sh              # Build and verify
./build.sh regen        # Regenerate assembly from fw.bin
./build.sh compare      # Compare built firmware with original
./build.sh clean        # Remove build artifacts
./build.sh help         # Show all commands
```

## Workflow

### Initial Setup
```bash
./build.sh regen        # Generate assembly from fw.bin
./build.sh              # Verify it builds correctly
```

### Making Changes
1. Edit `bank0.asm` or `bank1.asm`
2. Run `./build.sh` to build and verify
3. If verification fails, fix your changes
4. Commit only when `✓ SUCCESS` is shown

## Assembly Format

The generated assembly uses real 8051 instructions with labels:

```asm
; ============ Function at 0x0006 ============

func_0006:
    lcall   common_handler                    ; 0006: 12 50 db
    mov     dptr, #0x000a                     ; 0009: 90 00 0a
    movx    a,@dptr                           ; 000c: e0
    jz      L_0011                            ; 000d: 60 02
    dec     a                                 ; 000f: 14

L_0010:
    movx    @dptr,a                           ; 0010: f0

L_0011:
    ret                                       ; 0011: 22
```

### Branch Handling

- **Real labels** for branches within the same bank to valid instruction addresses
- **Raw bytes** for cross-bank calls and jumps to invalid targets (data sections)

Example of cross-bank call (Bank 1 calling Bank 0):
```asm
    .db     #0x12, #0x0b, #0xe6  ; lcall 0x0be6   ; calling Bank 0 function
```

## Memory Map

| Range | Bank | Description |
|-------|------|-------------|
| 0x0000-0x7FFF | Common | Always accessible |
| 0x8000-0xFFFF | Bank 0 | Default banked area |
| 0x8000-0xFFFF | Bank 1 | Switched banked area (file: 0x10000+) |

Bank 1 code is stored at file offset 0x10000+ but executes at address 0x8000 when bank 1 is active.

## Common 8051 Instructions

| Bytes | Instruction | Description |
|-------|-------------|-------------|
| `02 HH LL` | `ljmp addr` | Long jump |
| `12 HH LL` | `lcall addr` | Long call |
| `22` | `ret` | Return |
| `32` | `reti` | Return from interrupt |
| `74 NN` | `mov a, #imm` | Load immediate to A |
| `78 NN` | `mov r0, #imm` | Load immediate to R0 |
| `90 HH LL` | `mov dptr, #addr` | Load DPTR |
| `e0` | `movx a, @dptr` | Read XDATA |
| `f0` | `movx @dptr, a` | Write XDATA |
| `e4` | `clr a` | Clear A |
| `c3` | `clr c` | Clear carry |
| `d3` | `setb c` | Set carry |

## Build Requirements

- SDCC (Small Device C Compiler) with sdas8051, sdld
- Python 3

## Verification Output

Successful build:
```
=== Comparing with original firmware ===
Original: 98012 bytes
Built:    98012 bytes

✓ SUCCESS: Files are byte-for-byte identical!
```

Failed build (DO NOT COMMIT):
```
✗ DIFFERENCE: Files differ!
  0x00123: expected 0x02, got 0x03
  ...
```
