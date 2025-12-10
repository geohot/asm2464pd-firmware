Our goal is to emulate the fw.bin in emulate/

## Running the Emulator

```bash
# Basic execution (10M cycle limit)
python3 emulate/emu.py fw.bin

# With instruction tracing
python3 emulate/emu.py fw.bin --trace

# Limit instructions
python3 emulate/emu.py fw.bin --max-inst 1000

# Set breakpoint
python3 emulate/emu.py fw.bin --break 0x431A --trace

# Dump state on exit
python3 emulate/emu.py fw.bin --max-inst 1000 --dump
```

## Architecture

- `emulate/cpu.py` - 8051 CPU core with full instruction set
- `emulate/memory.py` - Memory subsystem with code banking (DPX register)
- `emulate/peripherals.py` - MMIO peripheral emulators:
  - UART (0xC000-0xC00F) - output echoed to stdout
  - Timers (0xCC10-0xCC27)
  - USB Controller (0x9000-0x93FF)
  - NVMe Controller (0xC400-0xC5FF)
  - PCIe/Thunderbolt (0xB200-0xB8FF)
  - DMA Controller (0xC8B0-0xC8D9)
  - Flash Controller (0xC89F-0xC8AE)
  - Interrupt Controller (0xC800-0xC80F)
  - Power Management (0x92C0-0x92E0)
- `emulate/emu.py` - Main emulator driver

## Memory Banking

The ASM2464PD has ~98KB firmware but 8051 can only address 64KB.
Banking is controlled via the DPX register (SFR 0x96):
- 0x0000-0x7FFF: Always bank 0 (shared)
- 0x8000-0xFFFF with DPX=0: Bank 0
- 0x8000-0xFFFF with DPX=1: Bank 1 (file offset 0x10000+)

## TODO

- [ ] Complete peripheral emulation (currently stubs)
- [ ] Add USB device emulation for testing
- [ ] Add NVMe command injection
- [ ] Better debugging/watchpoints