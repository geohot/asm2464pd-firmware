#!/usr/bin/env python3
"""Check key XDATA values that control descriptor handling paths."""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_xdata_values(desc_type, wValue, desc_name):
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    print(f"\n=== {desc_name} DESCRIPTOR ===")

    # Check key XDATA values before inject
    print("\nBefore inject:")
    for addr in [0x07B5, 0x07E1, 0x0ACC, 0x0AD1, 0x0AD6]:
        print(f"  XDATA[0x{addr:04X}] = 0x{emu.memory.xdata[addr]:02X}")

    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=wValue,
        wIndex=0x0000,
        wLength=18 if desc_type == 1 else 9
    )

    # Run a bit and check XDATA
    emu.run(max_cycles=400000)

    print("\nAfter inject + run:")
    for addr in [0x07B5, 0x07E1, 0x0ACC, 0x0AD1, 0x0AD6]:
        print(f"  XDATA[0x{addr:04X}] = 0x{emu.memory.xdata[addr]:02X}")

    # Check 0x9E00 result
    print(f"\n0x9E00 buffer: {bytes([emu.hw.regs.get(0x9E00 + i, 0) for i in range(16)]).hex()}")
    print(f"0x8000 result: {bytes([emu.memory.xdata[0x8000 + i] for i in range(16)]).hex()}")

if __name__ == '__main__':
    test_xdata_values(1, 0x0100, "DEVICE")
    test_xdata_values(2, 0x0200, "CONFIG")
