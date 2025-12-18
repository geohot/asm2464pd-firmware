#!/usr/bin/env python3
"""Trace PC addresses that write to 0x9E00 buffer."""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_config_pc():
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

    # Hook the write function to log PC
    writes = []
    original_write = emu.hw.write

    def track_writes(addr, value):
        if 0x9E00 <= addr <= 0x9E1F:
            writes.append((emu.hw.cycles, emu.cpu.pc, addr, value))
        return original_write(addr, value)

    emu.hw.write = track_writes

    # Inject config descriptor request
    print("=== Injecting GET_DESCRIPTOR: CONFIG ===")
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=0x0200,
        wIndex=0x0000,
        wLength=9
    )

    # Run
    emu.run(max_cycles=500000)

    # Show writes with PC
    print("\n=== Writes to 0x9E00-0x9E1F with PC ===")
    for cycle, pc, addr, value in writes[:40]:
        print(f"  [{cycle:8d}] PC=0x{pc:04X} write 0x{addr:04X} = 0x{value:02X}")

    # Find the write of 0x12 to 0x9E02
    print("\n=== Write of 0x12 to 0x9E02 ===")
    for cycle, pc, addr, value in writes:
        if addr == 0x9E02 and value == 0x12:
            print(f"  [{cycle:8d}] PC=0x{pc:04X} write 0x{addr:04X} = 0x{value:02X}")

    # Final buffer
    print("\n0x9E00 final:")
    print(f"  {bytes([emu.hw.regs.get(0x9E00 + i, 0) for i in range(16)]).hex()}")

def test_device_pc():
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

    # Hook the write function to log PC
    writes = []
    original_write = emu.hw.write

    def track_writes(addr, value):
        if 0x9E00 <= addr <= 0x9E1F:
            writes.append((emu.hw.cycles, emu.cpu.pc, addr, value))
        return original_write(addr, value)

    emu.hw.write = track_writes

    # Inject DEVICE descriptor request
    print("=== Injecting GET_DESCRIPTOR: DEVICE ===")
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=0x0100,  # DEVICE
        wIndex=0x0000,
        wLength=18
    )

    # Run
    emu.run(max_cycles=500000)

    # Show writes with PC
    print("\n=== Writes to 0x9E00-0x9E1F with PC ===")
    for cycle, pc, addr, value in writes[:40]:
        print(f"  [{cycle:8d}] PC=0x{pc:04X} write 0x{addr:04X} = 0x{value:02X}")

    # Final buffer
    print("\n0x9E00 final:")
    print(f"  {bytes([emu.hw.regs.get(0x9E00 + i, 0) for i in range(18)]).hex()}")

if __name__ == '__main__':
    print("===== DEVICE DESCRIPTOR =====")
    test_device_pc()
    print("\n\n===== CONFIG DESCRIPTOR =====")
    test_config_pc()
