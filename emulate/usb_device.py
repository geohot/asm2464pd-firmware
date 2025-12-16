"""
ASM2464PD USB Device Emulation

Connects raw-gadget USB device to the 8051 firmware emulator.
ALL USB traffic is passed through to the firmware via MMIO registers.

Architecture:
  Host <--USB--> raw-gadget
                    |
                    └── ALL USB traffic --> firmware via MMIO

Control Transfer Flow:
1. Setup packet (8 bytes) written to 0x9E00-0x9E07
2. USB interrupt triggered (EX0 at 0x0E33)
3. Firmware reads setup packet from MMIO registers
4. Firmware processes request (GET_DESCRIPTOR, SET_ADDRESS, etc.)
5. Firmware writes response to USB buffer at 0x8000
6. Response read back and sent to host

Bulk Transfer Flow (E4/E5 vendor commands):
1. CDB written to 0x910D-0x9112
2. USB interrupt triggers vendor handler (0x5333 -> 0x4583 -> 0x35B7)
3. Firmware processes E4 read or E5 write
4. Response at 0x8000

The firmware handles ALL USB endpoints including control endpoint 0.
USB descriptors are provided by firmware, not hardcoded in Python.

Setup:
  sudo modprobe dummy_hcd raw_gadget
  sudo python emulate/usb_device.py fw.bin
"""

import os
import sys
import struct
import threading
import time
from typing import Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass

from raw_gadget import (
    RawGadget, RawGadgetError, USBRawEventType, USBControlRequest,
    USBSpeed, USB_DIR_IN, USB_DIR_OUT, USB_DT_ENDPOINT,
    check_raw_gadget_available
)

if TYPE_CHECKING:
    from emu import Emulator

# USB request types
USB_TYPE_STANDARD = 0x00
USB_TYPE_CLASS = 0x20
USB_TYPE_VENDOR = 0x40

# Standard requests
USB_REQ_GET_STATUS = 0x00
USB_REQ_CLEAR_FEATURE = 0x01
USB_REQ_SET_FEATURE = 0x03
USB_REQ_SET_ADDRESS = 0x05
USB_REQ_GET_DESCRIPTOR = 0x06
USB_REQ_SET_DESCRIPTOR = 0x07
USB_REQ_GET_CONFIGURATION = 0x08
USB_REQ_SET_CONFIGURATION = 0x09
USB_REQ_GET_INTERFACE = 0x0A
USB_REQ_SET_INTERFACE = 0x0B

# Descriptor types
USB_DT_DEVICE = 0x01
USB_DT_CONFIG = 0x02
USB_DT_STRING = 0x03
USB_DT_INTERFACE = 0x04
USB_DT_ENDPOINT = 0x05
USB_DT_BOS = 0x0F

# VID:PID
ASM2464_VID = 0xADD1
ASM2464_PID = 0x0001


@dataclass
class USBSetupPacket:
    """USB control transfer setup packet."""
    bmRequestType: int
    bRequest: int
    wValue: int
    wIndex: int
    wLength: int

    @classmethod
    def from_bytes(cls, data: bytes) -> 'USBSetupPacket':
        bmRequestType, bRequest, wValue, wIndex, wLength = struct.unpack('<BBHHH', data[:8])
        return cls(bmRequestType, bRequest, wValue, wIndex, wLength)

    def to_bytes(self) -> bytes:
        return struct.pack('<BBHHH', self.bmRequestType, self.bRequest,
                          self.wValue, self.wIndex, self.wLength)


class USBDevicePassthrough:
    """
    USB device emulation connecting raw-gadget to firmware emulator.

    USB control transfers (setup packets) are passed through to firmware via MMIO.
    E4/E5 vendor commands via bulk endpoints also go through firmware.
    """

    # USB setup packet registers (8-byte setup packet at 0x9E00)
    # These are the actual registers the firmware reads for control transfers
    REG_USB_EP0_DATA = 0x9E00      # EP0 data buffer base address
    REG_USB_SETUP_TYPE = 0x9E00   # bmRequestType
    REG_USB_SETUP_REQ = 0x9E01    # bRequest
    REG_USB_SETUP_VALUE_L = 0x9E02  # wValue low
    REG_USB_SETUP_VALUE_H = 0x9E03  # wValue high
    REG_USB_SETUP_INDEX_L = 0x9E04  # wIndex low
    REG_USB_SETUP_INDEX_H = 0x9E05  # wIndex high
    REG_USB_SETUP_LEN_L = 0x9E06    # wLength low
    REG_USB_SETUP_LEN_H = 0x9E07    # wLength high

    # CDB registers - firmware reads CDB from here for SCSI commands
    REG_CDB_START = 0x910D

    # USB status/control registers
    REG_USB_STATUS = 0x9000
    REG_USB_INT_FLAGS = 0x9101
    REG_USB_INT_PENDING = 0xC802
    REG_USB_EP_READY = 0x9096
    REG_USB_EP_STATUS = 0x90E3

    # Target address registers (for vendor commands)
    REG_TARGET_ADDR_HI = 0xCEB2
    REG_TARGET_ADDR_LO = 0xCEB3
    REG_CMD_TYPE = 0xCEB0

    # Response buffer in XDATA
    USB_BUFFER_ADDR = 0x8000

    def __init__(self, emulator: 'Emulator'):
        """
        Initialize passthrough with emulator reference.

        Args:
            emulator: The 8051 emulator running the firmware
        """
        self.emu = emulator
        self.gadget: Optional[RawGadget] = None
        self.running = False
        self.configured = False
        self.address_set = False
        self.usb_address = 0

        # Endpoint handles (assigned by kernel after enable)
        self.ep_data_in = None   # 0x81 - Data IN (bulk)
        self.ep_data_out = None  # 0x02 - Data OUT (bulk)
        self.ep_stat_in = None   # 0x83 - Status IN (bulk)
        self.ep_cmd_out = None   # 0x04 - Command OUT (bulk)

        # Thread for handling bulk transfers
        self._bulk_thread: Optional[threading.Thread] = None
        self._bulk_running = False

    def start(self, driver: str = "dummy_udc", device: str = "dummy_udc.0",
              speed: USBSpeed = USBSpeed.USB_SPEED_HIGH):
        """Start the USB device passthrough."""
        available, msg = check_raw_gadget_available()
        if not available:
            raise RuntimeError(f"raw-gadget not available: {msg}")

        self.gadget = RawGadget()
        self.gadget.open()
        self.gadget.init(driver, device, speed)  # driver_name, device_name, speed
        self.gadget.run()

        self.running = True
        print(f"[USB_PASS] Started on {driver}/{device} at {speed.name}")

    def stop(self):
        """Stop the USB device passthrough."""
        self.running = False
        self._bulk_running = False

        if self._bulk_thread and self._bulk_thread.is_alive():
            self._bulk_thread.join(timeout=1.0)

        if self.gadget:
            self.gadget.close()
            self.gadget = None

        print("[USB_PASS] Stopped")

    def inject_setup_packet(self, setup: USBSetupPacket):
        """
        Inject USB setup packet into emulator MMIO registers.

        This writes the setup packet fields to the appropriate hardware
        registers where the firmware will read them.
        """
        hw = self.emu.hw

        # Write setup packet to MMIO registers
        hw.regs[self.REG_USB_SETUP_TYPE] = setup.bmRequestType
        hw.regs[self.REG_USB_SETUP_REQ] = setup.bRequest
        hw.regs[self.REG_USB_SETUP_VALUE_L] = setup.wValue & 0xFF
        hw.regs[self.REG_USB_SETUP_VALUE_H] = (setup.wValue >> 8) & 0xFF
        hw.regs[self.REG_USB_SETUP_INDEX_L] = setup.wIndex & 0xFF
        hw.regs[self.REG_USB_SETUP_INDEX_H] = (setup.wIndex >> 8) & 0xFF
        hw.regs[self.REG_USB_SETUP_LEN_L] = setup.wLength & 0xFF
        hw.regs[self.REG_USB_SETUP_LEN_H] = (setup.wLength >> 8) & 0xFF

        print(f"[USB_PASS] Injected setup: type=0x{setup.bmRequestType:02X} "
              f"req=0x{setup.bRequest:02X} val=0x{setup.wValue:04X} "
              f"idx=0x{setup.wIndex:04X} len={setup.wLength}")

    def trigger_usb_interrupt(self):
        """Trigger USB interrupt in emulator to process injected request."""
        hw = self.emu.hw

        # Set USB interrupt pending
        hw.regs[self.REG_USB_INT_PENDING] |= 0x01
        hw.regs[self.REG_USB_INT_FLAGS] |= 0x01
        hw.regs[self.REG_USB_STATUS] |= 0x01

        # The emulator's run loop should process the interrupt

    def run_firmware_cycles(self, max_cycles: int = 10000):
        """Run firmware for a number of cycles to process request."""
        self.emu.run(max_cycles=self.emu.cpu.cycles + max_cycles)

    def read_response(self, length: int) -> bytes:
        """
        Read response data from firmware's USB buffer.

        Args:
            length: Number of bytes to read

        Returns:
            Response data from XDATA[0x8000+]
        """
        result = bytearray(length)
        for i in range(length):
            result[i] = self.emu.memory.xdata[self.USB_BUFFER_ADDR + i]
        return bytes(result)

    def handle_control_transfer(self, setup: USBSetupPacket, data: bytes = b'') -> Optional[bytes]:
        """
        Handle a control transfer by passing to firmware.

        ALL USB requests are handled by firmware via MMIO registers.
        The firmware reads the setup packet from 0x9E00-0x9E07 and
        processes it through the USB interrupt handler at 0x0E33.

        Args:
            setup: The USB setup packet
            data: Data phase payload (for OUT transfers)

        Returns:
            Response data for IN transfers, or None for OUT transfers
        """
        # Use USBController's inject_control_transfer to properly set up MMIO
        # and copy setup packet to RAM locations firmware expects
        self.emu.hw.usb_controller.inject_control_transfer(
            bmRequestType=setup.bmRequestType,
            bRequest=setup.bRequest,
            wValue=setup.wValue,
            wIndex=setup.wIndex,
            wLength=setup.wLength,
            data=data
        )

        # Trigger USB interrupt
        hw = self.emu.hw
        hw._pending_usb_interrupt = True
        self.emu.cpu._ext0_pending = True

        # Enable interrupts
        ie = self.emu.memory.read_sfr(0xA8)
        ie |= 0x81  # EA + EX0
        self.emu.memory.write_sfr(0xA8, ie)

        # Run firmware to process request
        self.run_firmware_cycles(max_cycles=50000)

        # For IN transfers, read response from buffer
        if setup.bmRequestType & 0x80:  # Device-to-host
            response = self.read_response(setup.wLength)
            # Check if we got a valid response (not all zeros)
            if any(b != 0 for b in response):
                return response
            # Firmware didn't produce response - may need more cycles
            self.run_firmware_cycles(max_cycles=50000)
            return self.read_response(setup.wLength)

        return None


    def handle_events(self):
        """Main event loop - process raw-gadget events."""
        if not self.gadget:
            return

        try:
            event = self.gadget.event_fetch(timeout_ms=100)
        except RawGadgetError:
            return

        if event.type == USBRawEventType.CONNECT:
            speed = event.data[0] if event.data else 0
            print(f"[USB_PASS] Connect event (speed={speed})")
            # Initialize emulator USB state
            self.emu.hw.usb_controller.connect()
            # Run firmware boot sequence
            self.emu.run(max_cycles=100000)

        elif event.type == USBRawEventType.CONTROL:
            self._handle_control_event(event.data)

        elif event.type == USBRawEventType.RESET:
            print("[USB_PASS] Reset event")
            self.configured = False
            self.address_set = False

        elif event.type == USBRawEventType.DISCONNECT:
            print("[USB_PASS] Disconnect event")
            self.configured = False
            self.address_set = False

        elif event.type == USBRawEventType.SUSPEND:
            print("[USB_PASS] Suspend event")

        elif event.type == USBRawEventType.RESUME:
            print("[USB_PASS] Resume event")

    def _handle_control_event(self, data: bytes):
        """Handle a USB control request by passing through to firmware."""
        if len(data) < 8:
            print(f"[USB_PASS] Control event too short: {len(data)} bytes")
            return

        setup = USBSetupPacket.from_bytes(data)
        direction = "IN" if setup.bmRequestType & 0x80 else "OUT"
        req_type = (setup.bmRequestType >> 5) & 0x03
        req_type_name = ["STD", "CLASS", "VENDOR", "RESERVED"][req_type]

        print(f"[USB_PASS] Control {direction} {req_type_name}: "
              f"req=0x{setup.bRequest:02X} val=0x{setup.wValue:04X} "
              f"idx=0x{setup.wIndex:04X} len={setup.wLength}")

        try:
            # ALL control transfers go through firmware
            response = self.handle_control_transfer(setup)

            # Track state changes based on what firmware processed
            if setup.bmRequestType == 0x00:
                if setup.bRequest == USB_REQ_SET_ADDRESS:
                    self.address_set = True
                    self.usb_address = setup.wValue & 0x7F
                elif setup.bRequest == USB_REQ_SET_CONFIGURATION:
                    if setup.wValue > 0:
                        self.gadget.configure()
                        self._enable_endpoints()
                        self.configured = True

            if response is not None:
                # IN transfer - send response
                if len(response) > 0:
                    print(f"[USB_PASS] Response ({len(response)} bytes): {response[:32].hex()}...")
                self.gadget.ep0_write(response)
            else:
                # OUT transfer - ACK with zero-length read
                self.gadget.ep0_read(0)

        except Exception as e:
            print(f"[USB_PASS] Error handling control: {e}")
            import traceback
            traceback.print_exc()
            self.gadget.ep0_stall()

    def _enable_endpoints(self):
        """Enable bulk endpoints after configuration."""
        if not self.gadget:
            return

        try:
            # UAS endpoints for bulk data transfer
            # EP1 IN (0x81) - Data IN (bulk, 512 bytes for high-speed)
            self.ep_data_in = self.gadget.ep_enable(0x81, 0x02, 512)
            print(f"[USB_PASS] Enabled EP1 IN (data): handle={self.ep_data_in}")

            # EP2 OUT (0x02) - Data OUT (bulk)
            self.ep_data_out = self.gadget.ep_enable(0x02, 0x02, 512)
            print(f"[USB_PASS] Enabled EP2 OUT (data): handle={self.ep_data_out}")

            # EP3 IN (0x83) - Status IN (bulk)
            self.ep_stat_in = self.gadget.ep_enable(0x83, 0x02, 512)
            print(f"[USB_PASS] Enabled EP3 IN (status): handle={self.ep_stat_in}")

            # EP4 OUT (0x04) - Command OUT (bulk)
            self.ep_cmd_out = self.gadget.ep_enable(0x04, 0x02, 512)
            print(f"[USB_PASS] Enabled EP4 OUT (command): handle={self.ep_cmd_out}")

            # Start bulk transfer thread
            self._start_bulk_thread()

        except RawGadgetError as e:
            print(f"[USB_PASS] Failed to enable endpoints: {e}")

    def _start_bulk_thread(self):
        """Start background thread for bulk transfer handling."""
        if self._bulk_thread and self._bulk_thread.is_alive():
            return

        self._bulk_running = True
        self._bulk_thread = threading.Thread(target=self._bulk_transfer_loop, daemon=True)
        self._bulk_thread.start()
        print("[USB_PASS] Bulk transfer thread started")

    def _bulk_transfer_loop(self):
        """Background thread for bulk endpoint transfers."""
        print("[BULK] Transfer loop starting")

        while self._bulk_running and self.gadget:
            try:
                if self.ep_cmd_out is None:
                    time.sleep(0.01)
                    continue

                # Read command from EP4 OUT
                cmd_data = self.gadget.ep_read(self.ep_cmd_out, 32)
                if len(cmd_data) == 0:
                    continue

                # Parse UAS command packet
                slot = cmd_data[3] if len(cmd_data) > 3 else 1
                cdb = cmd_data[16:] if len(cmd_data) > 16 else b''

                if len(cdb) < 6:
                    continue

                cmd_type = cdb[0]
                print(f"[BULK] Command: slot={slot} type=0x{cmd_type:02X}")

                # Parse CDB: [cmd, size_or_val, addr_high, addr_mid, addr_low, 0]
                size_or_val = cdb[1]
                # USB address format: (addr & 0x1FFFF) | 0x500000
                # Decode: addr_high=0x50, addr_mid/low = actual address
                usb_addr = (cdb[2] << 16) | (cdb[3] << 8) | cdb[4]
                xdata_addr = usb_addr & 0x1FFFF

                # Use inject_usb_command() for proper MMIO setup
                if cmd_type == 0xE4:  # Read XDATA
                    print(f"[BULK] E4 read: addr=0x{xdata_addr:04X} size={size_or_val}")
                    self.emu.hw.inject_usb_command(0xE4, xdata_addr, size=size_or_val)
                    self.run_firmware_cycles(50000)

                    response = self.read_response(size_or_val)
                    print(f"[BULK] E4 response: {response.hex()[:32]}...")

                    # Send data on EP1 IN
                    if self.ep_data_in:
                        self.gadget.ep_write(self.ep_data_in, response)

                    # Send status on EP3 IN
                    if self.ep_stat_in:
                        status = self._make_status(slot, 0)
                        self.gadget.ep_write(self.ep_stat_in, status)

                elif cmd_type == 0xE5:  # Write XDATA
                    print(f"[BULK] E5 write: addr=0x{xdata_addr:04X} val=0x{size_or_val:02X}")
                    self.emu.hw.inject_usb_command(0xE5, xdata_addr, value=size_or_val)
                    self.run_firmware_cycles(50000)

                    # Send status on EP3 IN
                    if self.ep_stat_in:
                        status = self._make_status(slot, 0)
                        self.gadget.ep_write(self.ep_stat_in, status)

                else:
                    print(f"[BULK] Unknown command: 0x{cmd_type:02X}")
                    if self.ep_stat_in:
                        status = self._make_status(slot, 1)  # Error
                        self.gadget.ep_write(self.ep_stat_in, status)

            except RawGadgetError as e:
                if self._bulk_running:
                    print(f"[BULK] Error: {e}")
                    time.sleep(0.1)
            except Exception as e:
                print(f"[BULK] Unexpected error: {e}")
                time.sleep(0.1)

        print("[BULK] Transfer loop stopped")

    def _make_status(self, slot: int, status: int) -> bytes:
        """Create UAS status IU response."""
        return bytes([
            0x03,       # IU type (status)
            0x00,       # Reserved
            slot >> 8, slot & 0xFF,  # Tag
            status,     # Status
            0x00, 0x00, 0x00,  # Reserved
        ])


def main():
    """Run the USB passthrough with emulator."""
    import argparse

    parser = argparse.ArgumentParser(description='ASM2464PD USB Device Emulation')
    parser.add_argument('firmware', nargs='?',
                       default=os.path.join(os.path.dirname(__file__), '..', 'fw.bin'),
                       help='Path to firmware binary (default: fw.bin)')
    parser.add_argument('--driver', default='dummy_udc',
                       help='UDC driver name (default: dummy_udc)')
    parser.add_argument('--device', default='dummy_udc.0',
                       help='UDC device name (default: dummy_udc.0)')
    parser.add_argument('--speed', choices=['low', 'full', 'high', 'super'],
                       default='high', help='USB speed (default: high)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    args = parser.parse_args()

    # Map speed string to enum
    speed_map = {
        'low': USBSpeed.USB_SPEED_LOW,
        'full': USBSpeed.USB_SPEED_FULL,
        'high': USBSpeed.USB_SPEED_HIGH,
        'super': USBSpeed.USB_SPEED_SUPER,
    }
    speed = speed_map[args.speed]

    # Check raw-gadget availability
    available, msg = check_raw_gadget_available()
    if not available:
        print(f"[ERROR] {msg}")
        print("\nTo set up raw-gadget:")
        print("  sudo modprobe dummy_hcd")
        print("  sudo modprobe raw_gadget")
        print("  # Or build from source: https://github.com/xairy/raw-gadget")
        sys.exit(1)

    # Import emulator
    sys.path.insert(0, os.path.dirname(__file__))
    from emu import Emulator

    # Create emulator
    print(f"[MAIN] Loading firmware: {args.firmware}")
    emu = Emulator(log_uart=True)
    emu.reset()
    emu.load_firmware(args.firmware)

    if args.verbose:
        emu.hw.log_reads = True
        emu.hw.log_writes = True

    # Run initial boot sequence
    print("[MAIN] Running firmware boot sequence...")
    emu.run(max_cycles=500000)
    print(f"[MAIN] Boot complete. PC=0x{emu.cpu.pc:04X}, cycles={emu.cpu.cycles}")

    # Create USB passthrough
    usb = USBDevicePassthrough(emu)

    try:
        print(f"[MAIN] Starting USB device on {args.driver}/{args.device} ({args.speed} speed)")
        usb.start(driver=args.driver, device=args.device, speed=speed)

        print("[MAIN] USB device ready. Press Ctrl+C to stop.")
        print("[MAIN] Connect to the emulated device with: lsusb")
        print()

        while usb.running:
            usb.handle_events()

            # Periodically run firmware to process background tasks
            if emu.cpu.cycles % 10000 == 0:
                emu.run(max_cycles=emu.cpu.cycles + 1000)

    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted")
    except Exception as e:
        print(f"\n[MAIN] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        usb.stop()
        print("[MAIN] Shutdown complete")


if __name__ == "__main__":
    main()
