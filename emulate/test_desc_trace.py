#!/usr/bin/env python3
"""
Trace the exact code path for GET_DEVICE_DESCRIPTOR in original firmware.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from emu import Emulator


def test_device_descriptor_trace():
    """Trace firmware handling of GET_DEVICE_DESCRIPTOR."""
    print("=" * 70)
    print("Testing GET_DEVICE_DESCRIPTOR path in original firmware")
    print("=" * 70)

    # Create emulator
    emu = Emulator(log_uart=False)
    emu.reset()

    # Load ORIGINAL firmware
    fw_path = os.path.join(os.path.dirname(__file__), '..', 'fw.bin')
    print(f"Loading original firmware: {fw_path}")
    emu.load_firmware(fw_path)

    # Run boot sequence
    print("\nRunning boot sequence...")
    emu.run(max_cycles=100000)
    print(f"After boot: PC=0x{emu.cpu.pc:04X}")

    # CRITICAL: Remove the 0x07E1 = 0x05 cheat
    # We want to see what the FIRMWARE sets, not what the emulator sets
    emu.memory.xdata[0x07E1] = 0x00  # Clear to see what firmware writes

    # Inject GET_DESCRIPTOR
    print("\n" + "=" * 70)
    print("Injecting GET_DESCRIPTOR (device descriptor)")
    print("=" * 70)

    hw = emu.hw
    hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=0x0100,  # Device descriptor
        wIndex=0x0000,
        wLength=18
    )

    # Clear 0x07E1 again after injection (in case inject_control_transfer set it)
    emu.memory.xdata[0x07E1] = 0x00

    # Set up interrupt
    hw._pending_usb_interrupt = True
    emu.cpu._ext0_pending = True
    ie = emu.memory.read_sfr(0xA8)
    ie |= 0x81
    emu.memory.write_sfr(0xA8, ie)

    # Key addresses to watch
    key_pcs = {
        0x874E: "Descriptor type switch",
        0x8777: "Device descriptor handler",
        0x8783: "lcall 0x8a5f",
        0x8786: "lcall 0xa4cc (get speed)",
        0x878A: "cjne r7, #0x02 (speed check)",
        0x879D: "read 0x0ACC (USB mode)",
        0x87A1: "jb acc.1 (USB3 mode check)",
        0x87A4: "ljmp 0x8a35 (USB2 path)",
        0x87A7: "USB3 path",
        0x87B1: "ljmp 0x8914",
        0x8914: "USB3 intermediate",
        0x891A: "ljmp 0x8a35",
        0x8A35: "USB handler - read 0x0AE4",
        0x8A40: "read 0x0A83 into R7",
        0x8A45: "ret from USB handler",
        0xA657: "lcall 0x874e (from dispatch table)",
        0xA65A: "sjmp 0xa699 (after descriptor)",
        0xA699: "write R7 to 0x07E1",
        0xB3FC: "Get USB speed for DMA",
        0xB403: "SuperSpeed: R6=2, R7=0",
        0xB409: "Non-SuperSpeed: R6=0, R7=0x40",
        0xD088: "DMA trigger check",
    }

    # Watch addresses
    watch_addrs = {
        0x07E1: "USB_DESC_STATE",
        0x0A83: "USB_DESC_R7",
        0x0ACC: "USB_MODE_FLAGS",
        0x0AD7: "USB_DMA_FLAGS",
        0x0AE4: "USB_AE4_FLAG",
    }

    for addr, name in watch_addrs.items():
        emu.setup_watch(addr, name)

    # Also watch the setup packet copy area
    emu.setup_watch(0x0AD4, "USB_WLEN_LO")
    emu.setup_watch(0x0AD5, "USB_WLEN_HI")
    emu.setup_watch(0x0AD6, "USB_SPEED_MODE")
    emu.setup_watch(0x0ADD, "USB_0ADD")
    emu.setup_watch(0x0ADE, "USB_0ADE")
    emu.setup_watch(0x0ADB, "USB_0ADB")
    emu.setup_watch(0x0ADC, "USB_0ADC")

    print("\nKey addresses:")
    for addr, name in sorted(key_pcs.items())[:15]:
        print(f"  0x{addr:04X}: {name}")

    # Track PCs hit and register values at key points
    pcs_seen = set()
    r7_values = {}

    print("\n" + "=" * 70)
    print("Running firmware...")
    print("=" * 70)

    cycles_start = emu.cpu.cycles
    max_cycles = 100000

    while emu.cpu.cycles - cycles_start < max_cycles:
        try:
            emu.step()
            pc = emu.cpu.pc

            if pc in key_pcs and pc not in pcs_seen:
                # Get current R7 value from CPU (R7 is at IDATA[7])
                r7 = emu.memory.idata[7]
                a_reg = emu.memory.read_sfr(0xE0)  # ACC is SFR 0xE0
                pcs_seen.add(pc)
                r7_values[pc] = r7

                print(f"  [{emu.cpu.cycles:8d}] Hit 0x{pc:04X}: {key_pcs[pc]} (R7=0x{r7:02X}, A=0x{a_reg:02X})")

                # Special checks
                if pc == 0x8A40:
                    # About to read 0x0A83 into R7
                    val_0a83 = emu.memory.xdata[0x0A83]
                    print(f"                 0x0A83 = 0x{val_0a83:02X}")
                elif pc == 0xA699:
                    # About to write R7 to 0x07E1
                    print(f"                 Will write R7=0x{r7:02X} to 0x07E1")
                elif pc == 0xD088:
                    # DMA trigger check
                    val_07e1 = emu.memory.xdata[0x07E1]
                    print(f"                 0x07E1 = 0x{val_07e1:02X} (need 0x05 for DMA)")
                    break  # We've reached the DMA check, stop here
                elif pc == 0x87A1:
                    # USB mode check
                    val_0acc = emu.memory.xdata[0x0ACC]
                    print(f"                 0x0ACC = 0x{val_0acc:02X} (bit 1 = USB3 mode)")
                elif pc == 0x878A:
                    # Speed check
                    print(f"                 Checking if R7 == 0x02 (SuperSpeed)")

        except Exception as e:
            print(f"Error at PC=0x{emu.cpu.pc:04X}: {e}")
            import traceback
            traceback.print_exc()
            break

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    val_07e1 = emu.memory.xdata[0x07E1]
    val_0a83 = emu.memory.xdata[0x0A83]
    val_0acc = emu.memory.xdata[0x0ACC]
    val_9100 = emu.hw.regs.get(0x9100, 0)

    print(f"0x07E1 (USB_DESC_STATE) = 0x{val_07e1:02X}")
    print(f"0x0A83 (USB_DESC_R7) = 0x{val_0a83:02X}")
    print(f"0x0ACC (USB_MODE_FLAGS) = 0x{val_0acc:02X} (bit 1 = USB3 mode)")
    print(f"0x9100 (USB_SPEED) = 0x{val_9100:02X}")

    if val_07e1 == 0x05:
        print("\nSUCCESS: 0x07E1 = 0x05 - DMA trigger check will pass!")
    elif val_07e1 == 0x03:
        print("\nISSUE: 0x07E1 = 0x03 - USB2 path was taken, DMA will not trigger")
    elif val_07e1 == 0x00:
        print("\nISSUE: 0x07E1 = 0x00 - Value was not set by firmware")
    else:
        print(f"\nISSUE: 0x07E1 = 0x{val_07e1:02X} - Unexpected value")

    # Check USB buffer
    buf = bytes(emu.memory.xdata[0x8000:0x8020])
    print(f"\nUSB buffer (0x8000): {buf.hex()}")

    return val_07e1


if __name__ == "__main__":
    result = test_device_descriptor_trace()
