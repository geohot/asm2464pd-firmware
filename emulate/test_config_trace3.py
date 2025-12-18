#!/usr/bin/env python3
"""Compare 0x9091 write patterns between device and config descriptor requests."""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_descriptor(desc_type, wValue):
    """Test a descriptor request and count 0x9091 writes."""
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
        emu.hw.regs[0x9E00 + i] = 0

    # Count 0x9091 writes and 0x9092 writes
    writes_9091 = 0
    writes_9092 = 0
    dma_triggered = False

    original_write = emu.hw.write

    def track_writes(addr, value):
        nonlocal writes_9091, writes_9092, dma_triggered
        if addr == 0x9091:
            writes_9091 += 1
            if writes_9091 <= 5:
                print(f"  Write 0x9091 = 0x{value:02X} (#{writes_9091})")
        if addr == 0x9092:
            writes_9092 += 1
            print(f"  Write 0x9092 = 0x{value:02X} (#{writes_9092})")
            if value == 0x01:
                dma_triggered = True
        return original_write(addr, value)

    emu.hw.write = track_writes

    # Inject descriptor request
    print(f"\n=== GET_DESCRIPTOR type=0x{desc_type:02X} (wValue=0x{wValue:04X}) ===")
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=wValue,
        wIndex=0x0000,
        wLength=18 if desc_type == 1 else 9
    )

    # Run
    emu.run(max_cycles=500000)

    print(f"\nResult: 0x9091 writes={writes_9091}, 0x9092 writes={writes_9092}, DMA triggered={dma_triggered}")
    print(f"0x9091 = 0x{emu.hw.regs.get(0x9091, 0):02X}, 0x9092 = 0x{emu.hw.regs.get(0x9092, 0):02X}")
    print(f"0x8000: {bytes([emu.memory.xdata[0x8000 + i] for i in range(16)]).hex()}")

if __name__ == '__main__':
    test_descriptor(1, 0x0100)  # Device
    test_descriptor(2, 0x0200)  # Config
