#!/usr/bin/env python3
"""Trace exactly what firmware writes to 0x9E00 buffer."""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_config_writes():
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Clear buffers
    for i in range(64):
        emu.memory.xdata[0x8000 + i] = 0
        emu.hw.regs[0x9E00 + i] = 0

    # Track writes to 0x9E00-0x9E1F
    writes = []
    original_write = emu.hw.write

    def track_writes(addr, value):
        if 0x9E00 <= addr <= 0x9E1F:
            writes.append((emu.hw.cycles, addr, value))
        return original_write(addr, value)

    emu.hw.write = track_writes

    # Inject config descriptor request
    print("=== Injecting GET_DESCRIPTOR: CONFIG ===")
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=0x0200,  # Config descriptor type=2
        wIndex=0x0000,
        wLength=9
    )

    # Check 0x9E00 buffer immediately after inject (before firmware runs)
    print("\n0x9E00 after inject (before run):")
    print(f"  {bytes([emu.hw.regs.get(0x9E00 + i, 0) for i in range(16)]).hex()}")

    # Run
    emu.run(max_cycles=500000)

    # Show all writes
    print("\n=== Writes to 0x9E00-0x9E1F ===")
    for cycle, addr, value in writes[:30]:
        print(f"  [{cycle:8d}] 0x{addr:04X} = 0x{value:02X}")

    # Final buffer state
    print("\n0x9E00 after run:")
    print(f"  {bytes([emu.hw.regs.get(0x9E00 + i, 0) for i in range(16)]).hex()}")

    print("\n0x8000 after DMA:")
    print(f"  {bytes([emu.memory.xdata[0x8000 + i] for i in range(16)]).hex()}")

    # Check firmware state
    print(f"\nXDATA[0x07E1] = 0x{emu.memory.xdata[0x07E1]:02X} (request type indicator)")
    print(f"XDATA[0x0AD1] = 0x{emu.memory.xdata[0x0AD1]:02X} (descriptor type from setup)")

if __name__ == '__main__':
    test_config_writes()
