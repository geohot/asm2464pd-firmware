#!/usr/bin/env python3
"""Trace firmware handling of config descriptor request."""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_config_trace():
    """Trace config descriptor handling."""
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot firmware
    print("=== Booting firmware ===")
    emu.run(max_cycles=200000)

    # Connect USB at SuperSpeed
    print("\n=== Connecting USB (SuperSpeed) ===")
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Clear and inject config descriptor request
    print("\n=== Injecting GET_DESCRIPTOR: CONFIG ===")
    for i in range(64):
        emu.memory.xdata[0x8000 + i] = 0
        emu.hw.regs[0x9E00 + i] = 0

    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=0x0200,  # Config descriptor type=2
        wIndex=0x0000,
        wLength=9
    )

    # Track PCs in descriptor handling ranges
    pc_log = []
    key_pcs = set()

    def trace_step():
        pc = emu.cpu.pc
        if 0x0300 <= pc <= 0x0400:  # Descriptor dispatch table area
            if pc not in key_pcs:
                key_pcs.add(pc)
                pc_log.append(f"PC=0x{pc:04X}")
        if 0xB300 <= pc <= 0xB500:  # Descriptor handler area
            if pc not in key_pcs:
                key_pcs.add(pc)
                pc_log.append(f"PC=0x{pc:04X}")

    # Run with tracing
    for _ in range(100000):
        trace_step()
        emu.cpu.step()
        emu.hw.cycles += 1

    print("\n=== Key PCs hit ===")
    for entry in pc_log[:50]:
        print(entry)

    # Check what we got
    print("\n=== 0x9E00 buffer ===")
    print(f"0x9E00-0x9E0F: {bytes([emu.hw.regs.get(0x9E00 + i, 0) for i in range(16)]).hex()}")

    # Check XDATA[0x07E1] which is used for descriptor type dispatch
    if emu.memory:
        print(f"\nXDATA[0x07E1] = 0x{emu.memory.xdata[0x07E1]:02X}")
        print(f"XDATA[0x0ACE] = 0x{emu.memory.xdata[0x0ACE]:02X} (bmRequestType)")
        print(f"XDATA[0x0ACF] = 0x{emu.memory.xdata[0x0ACF]:02X} (bRequest)")
        print(f"XDATA[0x0AD0] = 0x{emu.memory.xdata[0x0AD0]:02X} (wValue low)")
        print(f"XDATA[0x0AD1] = 0x{emu.memory.xdata[0x0AD1]:02X} (wValue high = desc type)")

if __name__ == '__main__':
    test_config_trace()
