#!/usr/bin/env python3
"""Test config descriptor handling - trace what addresses firmware writes for DMA."""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_descriptor_dma():
    """Test DMA address for device vs config descriptor."""
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot firmware
    print("=== Booting firmware ===")
    emu.run(max_cycles=200000)

    # Connect USB at SuperSpeed
    print("\n=== Connecting USB (SuperSpeed) ===")
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Enable write logging
    emu.hw.log_writes = True

    # Test GET_DESCRIPTOR for device descriptor (type 0x01)
    print("\n=== GET_DESCRIPTOR: DEVICE (type=0x01) ===")
    emu.hw.regs[0x905B] = 0x00  # Reset before test
    emu.hw.regs[0x905C] = 0x00

    # Inject transfer (sets _pending_usb_interrupt)
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,  # Device-to-host, standard, device
        bRequest=0x06,       # GET_DESCRIPTOR
        wValue=0x0100,       # Type=1 (device), Index=0
        wIndex=0x0000,
        wLength=18
    )
    emu.run(max_cycles=500000)  # Run until firmware handles it

    # Check what address was set
    dev_addr_hi = emu.hw.regs.get(0x905B, 0)
    dev_addr_lo = emu.hw.regs.get(0x905C, 0)
    dev_addr = (dev_addr_hi << 8) | dev_addr_lo
    print(f"\nDevice descriptor DMA address: 0x{dev_addr:04X}")

    # Check what data is at 0x8000
    data = bytes([emu.memory.xdata[0x8000 + i] for i in range(18)])
    print(f"Data at 0x8000: {data.hex()}")

    # Test GET_DESCRIPTOR for config descriptor (type 0x02)
    print("\n=== GET_DESCRIPTOR: CONFIG (type=0x02) ===")
    emu.hw.regs[0x905B] = 0x00  # Reset before test
    emu.hw.regs[0x905C] = 0x00

    # Clear 0x8000 buffer
    for i in range(64):
        emu.memory.xdata[0x8000 + i] = 0

    # Clear 0x9E00 buffer to track what firmware writes
    for i in range(64):
        emu.hw.regs[0x9E00 + i] = 0

    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,  # Device-to-host, standard, device
        bRequest=0x06,       # GET_DESCRIPTOR
        wValue=0x0200,       # Type=2 (config), Index=0
        wIndex=0x0000,
        wLength=9            # First request - just get header
    )
    emu.run(max_cycles=500000)  # Run until firmware handles it

    # Check what firmware wrote to 0x9E00
    print("\n=== 0x9E00 buffer after config request ===")
    print(f"0x9E00-0x9E0F: {bytes([emu.hw.regs.get(0x9E00 + i, 0) for i in range(16)]).hex()}")

    # Check what address was set
    cfg_addr_hi = emu.hw.regs.get(0x905B, 0)
    cfg_addr_lo = emu.hw.regs.get(0x905C, 0)
    cfg_addr = (cfg_addr_hi << 8) | cfg_addr_lo
    print(f"\nConfig descriptor DMA address: 0x{cfg_addr:04X}")

    # Check what data is at 0x8000
    data = bytes([emu.memory.xdata[0x8000 + i] for i in range(9)])
    print(f"Data at 0x8000: {data.hex()}")

    # Show expected config descriptor from ROM
    print(f"\nExpected config at 0x58CF: {bytes(emu.memory.code[0x58CF:0x58CF+9]).hex()}")

if __name__ == '__main__':
    test_descriptor_dma()
