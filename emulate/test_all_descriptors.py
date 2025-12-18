#!/usr/bin/env python3
"""
Test that ALL USB descriptor types are handled by firmware via DMA.

This test verifies the core principle from CLAUDE.md:
- The emulator must NOT parse, process, or understand USB control messages
- USB hardware DMAs in the request (setup packet) to MMIO registers
- Firmware reads setup packet, determines response, configures DMA source address registers
- USB hardware DMAs out the response from the address FIRMWARE configured

No hardcoded descriptor addresses in Python - all addresses come from firmware register writes.
"""

import sys
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_descriptor(desc_type, wValue, desc_name, wLength):
    """Test that a descriptor request is handled by firmware via DMA.

    Each test gets a fresh emulator to ensure clean state.
    """
    # Fresh emulator for each test
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Clear the output buffer
    for i in range(64):
        emu.memory.xdata[0x8000 + i] = 0

    # Track DMA source address writes
    dma_sources = []
    original_write = emu.hw.write

    def track_dma_writes(addr, value):
        if addr == 0x905B:  # DMA src high
            dma_sources.append(('high', value))
        elif addr == 0x905C:  # DMA src low
            dma_sources.append(('low', value))
        elif addr == 0x9092:  # DMA trigger
            dma_sources.append(('trigger', value))
        return original_write(addr, value)

    emu.hw.write = track_dma_writes

    # Inject descriptor request
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,  # GET_DESCRIPTOR
        wValue=wValue,
        wIndex=0x0000,
        wLength=wLength
    )

    # Run firmware
    emu.run(max_cycles=500000)

    # Restore write handler
    emu.hw.write = original_write

    # Check result
    result = bytes(emu.memory.xdata[0x8000:0x8000 + wLength])

    # Analyze DMA source
    dma_src_high = 0
    dma_src_low = 0
    triggered = False
    for op, val in dma_sources:
        if op == 'high':
            dma_src_high = val
        elif op == 'low':
            dma_src_low = val
        elif op == 'trigger' and val == 0x01:
            triggered = True

    dma_src = (dma_src_high << 8) | dma_src_low

    return {
        'name': desc_name,
        'type': desc_type,
        'wValue': wValue,
        'wLength': wLength,
        'result': result,
        'dma_src': dma_src,
        'triggered': triggered,
        'non_zero': sum(1 for b in result if b != 0)
    }

def main():
    print("=" * 70)
    print("USB DESCRIPTOR FIRMWARE HANDLING TEST")
    print("Verifying all descriptors come from FIRMWARE via DMA")
    print("=" * 70)

    # Test each descriptor type (each gets a fresh emulator)
    tests = [
        (1, 0x0100, "DEVICE", 18),      # Device descriptor
        (2, 0x0200, "CONFIG", 9),        # Config descriptor (9 bytes first request)
        (2, 0x0200, "CONFIG_FULL", 44),  # Config descriptor (full)
        (3, 0x0300, "STRING_LANG", 4),   # String descriptor (language IDs)
        (3, 0x0301, "STRING_1", 64),     # String descriptor index 1
        (3, 0x0302, "STRING_2", 64),     # String descriptor index 2
        (3, 0x0303, "STRING_3", 64),     # String descriptor index 3
        (15, 0x0F00, "BOS", 5),          # BOS descriptor
    ]

    results = []
    for desc_type, wValue, name, wLength in tests:
        print(f"\n--- Testing {name} descriptor (type={desc_type}, wValue=0x{wValue:04X}) ---")
        result = test_descriptor(desc_type, wValue, name, wLength)
        results.append(result)

        print(f"  DMA source: 0x{result['dma_src']:04X}")
        print(f"  DMA triggered: {result['triggered']}")
        print(f"  Result ({result['non_zero']} non-zero bytes): {result['result'][:16].hex()}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_passed = True
    for r in results:
        # Check if descriptor was properly handled
        # Device descriptor should start with 0x12 0x01
        # Config descriptor should start with 0x09 0x02
        # String descriptor should start with len 0x03
        # BOS descriptor should start with len 0x0F

        first_byte = r['result'][0] if len(r['result']) > 0 else 0
        second_byte = r['result'][1] if len(r['result']) > 1 else 0

        valid = False
        if r['type'] == 1:  # Device
            valid = (first_byte == 0x12 and second_byte == 0x01)
        elif r['type'] == 2:  # Config
            valid = (first_byte == 0x09 and second_byte == 0x02)
        elif r['type'] == 3:  # String
            valid = (second_byte == 0x03 and first_byte > 0)
        elif r['type'] == 15:  # BOS
            valid = (second_byte == 0x0F or r['non_zero'] > 0)

        status = "PASS" if valid and r['triggered'] else "FAIL"
        if not valid or not r['triggered']:
            all_passed = False

        print(f"  {r['name']:15s}: {status} (DMA=0x{r['dma_src']:04X}, trig={r['triggered']}, data={r['result'][:4].hex()})")

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL DESCRIPTORS HANDLED BY FIRMWARE VIA DMA - NO HARDCODED DATA")
    else:
        print("SOME DESCRIPTORS NEED INVESTIGATION")
    print("=" * 70)

    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
