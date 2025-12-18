#!/usr/bin/env python3
"""Trace where firmware gets stuck on config descriptor request."""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test():
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot firmware
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Inject config descriptor request
    print("=== Injecting GET_DESCRIPTOR: CONFIG ===")
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=0x0200,  # Config descriptor
        wIndex=0x0000,
        wLength=9
    )

    # Track PC distribution - where does firmware spend time?
    pc_counts = {}
    last_pc_segment = None
    segment_switches = []

    for _ in range(200000):
        pc = emu.cpu.pc
        segment = pc & 0xF000  # Track 4KB segments
        if segment != last_pc_segment:
            segment_switches.append(f"0x{pc:04X} (segment 0x{segment:04X})")
            last_pc_segment = segment

        if 0x0300 <= pc <= 0x0400:
            pc_counts[pc] = pc_counts.get(pc, 0) + 1
        if 0xA500 <= pc <= 0xA700:  # Setup packet handler area
            pc_counts[pc] = pc_counts.get(pc, 0) + 1
        if 0xD000 <= pc <= 0xD100:  # DMA handler area
            pc_counts[pc] = pc_counts.get(pc, 0) + 1
        if 0x2000 <= pc <= 0x2100:  # Main loop area
            pc_counts[pc] = pc_counts.get(pc, 0) + 1

        emu.cpu.step()
        emu.hw.cycles += 1

    print("\n=== Top PCs by hit count ===")
    sorted_pcs = sorted(pc_counts.items(), key=lambda x: -x[1])[:20]
    for pc, count in sorted_pcs:
        print(f"  0x{pc:04X}: {count} hits")

    print("\n=== Segment switches (first 30) ===")
    for sw in segment_switches[:30]:
        print(f"  {sw}")

    # Check key values
    print(f"\n0x07E1 = 0x{emu.memory.xdata[0x07E1]:02X}")
    print(f"0x9091 = 0x{emu.hw.regs.get(0x9091, 0):02X}")
    print(f"0x9092 = 0x{emu.hw.regs.get(0x9092, 0):02X}")

    # Check if setup packet was copied
    print(f"\n0x0ACE-0x0AD5 (setup packet copy):")
    for i in range(8):
        print(f"  0x{0x0ACE+i:04X} = 0x{emu.memory.xdata[0x0ACE+i]:02X}")

if __name__ == '__main__':
    test()
