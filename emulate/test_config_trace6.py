#!/usr/bin/env python3
"""Check what firmware writes to 0x905B/0x905C for DMA source address."""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_dma_regs(desc_type, wValue, desc_name):
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Clear
    for i in range(64):
        emu.memory.xdata[0x8000 + i] = 0

    # Track DMA register writes
    dma_writes = []
    original_write = emu.hw.write

    def track_writes(addr, value):
        if addr in (0x905B, 0x905C, 0x9004, 0x9092):
            dma_writes.append((emu.hw.cycles, addr, value))
            print(f"  [{emu.hw.cycles:8d}] Write 0x{addr:04X} = 0x{value:02X}")
        return original_write(addr, value)

    emu.hw.write = track_writes

    print(f"\n=== {desc_name} DESCRIPTOR ===")
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=wValue,
        wIndex=0x0000,
        wLength=18 if desc_type == 1 else 9
    )

    emu.run(max_cycles=500000)

    print(f"\nFinal DMA registers:")
    print(f"  0x905B (addr hi) = 0x{emu.hw.regs.get(0x905B, 0):02X}")
    print(f"  0x905C (addr lo) = 0x{emu.hw.regs.get(0x905C, 0):02X}")
    print(f"  0x9004 (length)  = 0x{emu.hw.regs.get(0x9004, 0):02X}")
    print(f"  DMA source = 0x{(emu.hw.regs.get(0x905B, 0) << 8) | emu.hw.regs.get(0x905C, 0):04X}")

if __name__ == '__main__':
    test_dma_regs(1, 0x0100, "DEVICE")
    test_dma_regs(2, 0x0200, "CONFIG")
