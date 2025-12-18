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
  sudo python emulate/usb_device.py
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

        # USB speed for emulator (0=Full, 1=High, 2=Super, 3=Super+)
        self._emu_speed = 1  # Default to High Speed

    def start(self, driver: str = "dummy_udc", device: str = "dummy_udc.0",
              speed: USBSpeed = USBSpeed.USB_SPEED_HIGH):
        """Start the USB device passthrough."""
        available, msg = check_raw_gadget_available()
        if not available:
            raise RuntimeError(f"raw-gadget not available: {msg}")

        # Map USBSpeed enum to our internal speed values for emulator
        # Linux kernel: LOW=1, FULL=2, HIGH=3, SUPER=5, SUPER_PLUS=6
        # Our internal: Full=0, High=1, Super=2, Super+=3
        speed_map = {
            USBSpeed.USB_SPEED_LOW: 0,    # Treat low as full speed
            USBSpeed.USB_SPEED_FULL: 0,
            USBSpeed.USB_SPEED_HIGH: 1,
            USBSpeed.USB_SPEED_SUPER: 2,
        }
        # Handle SUPER_PLUS if it exists in the enum
        if hasattr(USBSpeed, 'USB_SPEED_SUPER_PLUS'):
            speed_map[USBSpeed.USB_SPEED_SUPER_PLUS] = 3
        self._emu_speed = speed_map.get(speed, 1)  # Default to High Speed

        self.gadget = RawGadget()
        self.gadget.open()
        self.gadget.init(driver, device, speed)  # driver_name, device_name, speed
        self.gadget.run()

        self.running = True
        print(f"[USB_PASS] Started on {driver}/{device} at {speed.name} (emu_speed={self._emu_speed})")

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

        E4/E5 vendor commands can be sent via vendor control transfers:
        - E4 read: bmRequestType=0xC0, bRequest=0xE4, wValue=size, wIndex=addr
        - E5 write: bmRequestType=0x40, bRequest=0xE5, wValue=value, wIndex=addr

        Args:
            setup: The USB setup packet
            data: Data phase payload (for OUT transfers)

        Returns:
            Response data for IN transfers, or None for OUT transfers
        """
        hw = self.emu.hw

        # Check for E4/E5 vendor commands
        req_type = (setup.bmRequestType >> 5) & 0x03
        if req_type == 2:  # Vendor request
            if setup.bRequest == 0xE4:  # E4 read
                return self._handle_e4_read(setup.wIndex, setup.wValue)
            elif setup.bRequest == 0xE5:  # E5 write
                value = data[0] if data else (setup.wValue & 0xFF)
                return self._handle_e5_write(setup.wIndex, value)

        # Use USBController's inject_control_transfer to properly set up MMIO
        # and copy setup packet to RAM locations firmware expects
        hw.usb_controller.inject_control_transfer(
            bmRequestType=setup.bmRequestType,
            bRequest=setup.bRequest,
            wValue=setup.wValue,
            wIndex=setup.wIndex,
            wLength=setup.wLength,
            data=data
        )

        # Trigger USB interrupt
        hw._pending_usb_interrupt = True
        self.emu.cpu._ext0_pending = True

        # Enable interrupts
        ie = self.emu.memory.read_sfr(0xA8)
        ie |= 0x81  # EA + EX0
        self.emu.memory.write_sfr(0xA8, ie)

        # Run firmware to process request - run in smaller chunks to let bulk thread run
        # This is critical: running too many cycles blocks the GIL and starves the bulk thread
        import time as _time
        remaining_cycles = 50000
        chunk_size = 5000  # Run in smaller chunks
        is_get_descriptor = (setup.bmRequestType == 0x80 and setup.bRequest == USB_REQ_GET_DESCRIPTOR)
        while remaining_cycles > 0:
            try:
                self.run_firmware_cycles(max_cycles=min(chunk_size, remaining_cycles))
            except Exception as e:
                print(f"[USB_PASS] Firmware run failed: {e}")
                import traceback
                traceback.print_exc()
                break
            remaining_cycles -= chunk_size
            # For GET_DESCRIPTOR, re-set main loop conditions after each chunk
            # The ISR may have run but main loop handler not reached yet
            if is_get_descriptor and remaining_cycles > 0:
                hw.regs[0x9002] = 0x00  # Bit 1 CLEAR
                hw.regs[0x9091] = 0x02  # Bit 1 SET
                if self.emu.memory:
                    self.emu.memory.xdata[0x07E1] = 0x05
            _time.sleep(0)  # Explicit GIL release to let bulk thread run

        # For IN transfers, read response from buffer
        if setup.bmRequestType & 0x80:  # Device-to-host
            # Debug: check DMA configuration after running firmware
            if is_get_descriptor:
                dma_hi = hw.regs.get(0x905B, 0)
                dma_lo = hw.regs.get(0x905C, 0)
                dma_addr = (dma_hi << 8) | dma_lo
                ep0_buf = bytes(hw.usb_ep0_buf[:8])
                xdata_07e1 = self.emu.memory.xdata[0x07E1] if self.emu.memory else 0
                print(f"[USB_PASS] DEBUG: DMA addr=0x{dma_addr:04X}, ep0_buf={ep0_buf.hex()}, 0x07E1=0x{xdata_07e1:02X}")
            # Check if the control transfer was handled
            # If usb_control_transfer_active is still True, firmware didn't handle it
            if hw.usb_control_transfer_active:
                # Request not handled - return None to trigger STALL
                print(f"[USB_PASS] Request not handled (type=0x{setup.bmRequestType:02X} "
                      f"req=0x{setup.bRequest:02X} val=0x{setup.wValue:04X}) - will STALL")
                hw.usb_control_transfer_active = False
                return None  # Will trigger STALL

            response = self.read_response(setup.wLength)
            # Check if we got a valid response (not all zeros)
            if any(b != 0 for b in response):
                return response
            # Firmware didn't produce response - re-set conditions and retry
            # Main loop conditions may have been cleared during first run
            hw.regs[0x9002] = 0x00  # Bit 1 CLEAR to allow 0x9091 check
            hw.regs[0x9091] = 0x02  # Bit 1 SET to trigger descriptor handler
            if self.emu.memory:
                self.emu.memory.xdata[0x07E1] = 0x05  # Descriptor request pending
            self.run_firmware_cycles(max_cycles=50000)
            return self.read_response(setup.wLength)

        return None

    def _handle_e4_read(self, xdata_addr: int, size: int) -> bytes:
        """
        Handle E4 vendor command (read XDATA).

        E4 commands read from the ASM2464PD's internal XDATA memory.
        The firmware processes this through its vendor command handler.

        Args:
            xdata_addr: XDATA address to read from
            size: Number of bytes to read

        Returns:
            Bytes read from XDATA
        """
        print(f"[USB_PASS] E4 read: addr=0x{xdata_addr:04X} size={size}")

        # Inject vendor command through proper MMIO path
        self.emu.hw.inject_usb_command(0xE4, xdata_addr, size=size)

        # Trigger interrupt and run firmware
        self.emu.cpu._ext0_pending = True
        ie = self.emu.memory.read_sfr(0xA8)
        ie |= 0x81
        self.emu.memory.write_sfr(0xA8, ie)

        # Run firmware to process command
        self.run_firmware_cycles(max_cycles=100000)

        # Read response from USB buffer (0x8000) or directly from XDATA
        # The firmware copies data to 0x8000, but for testing we can read XDATA directly
        result = bytearray(size)
        for i in range(size):
            result[i] = self.emu.memory.xdata[xdata_addr + i]

        print(f"[USB_PASS] E4 response: {result.hex()}")
        return bytes(result)

    def _handle_e5_write(self, xdata_addr: int, value: int) -> Optional[bytes]:
        """
        Handle E5 vendor command (write XDATA).

        E5 commands write to the ASM2464PD's internal XDATA memory.
        For the emulator, we directly write to XDATA (mirroring the E4 direct read).

        Args:
            xdata_addr: XDATA address to write to
            value: Byte value to write

        Returns:
            None (OUT transfer)
        """
        print(f"[USB_PASS] E5 write: addr=0x{xdata_addr:04X} value=0x{value:02X}")

        # Directly write to XDATA (like E4 directly reads)
        self.emu.memory.xdata[xdata_addr] = value

        print(f"[USB_PASS] E5 write complete: XDATA[0x{xdata_addr:04X}] = 0x{value:02X}")
        return None  # OUT transfer - no response data


    def handle_events(self):
        """Main event loop - process raw-gadget events."""
        if not self.gadget:
            return

        try:
            event = self.gadget.event_fetch(timeout_ms=100)
        except RawGadgetError:
            return

        if event.type == USBRawEventType.CONNECT:
            raw_speed = event.data[0] if event.data else 0
            print(f"[USB_PASS] Connect event (raw_speed={raw_speed}, emu_speed={self._emu_speed})")
            # Initialize emulator USB state with our configured speed
            self.emu.hw.usb_controller.connect(speed=self._emu_speed)
            # Run firmware boot sequence
            self.emu.run(max_cycles=100000)

        elif event.type == USBRawEventType.CONTROL:
            self._handle_control_event(event.data)

        elif event.type == USBRawEventType.RESET:
            import time as _t
            print(f"[USB_PASS] Reset event at t={_t.monotonic():.6f}")
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
                elif setup.bRequest == USB_REQ_SET_INTERFACE:
                    # Switch between alt settings
                    alt_setting = setup.wValue
                    print(f"[USB_PASS] SET_INTERFACE: alt={alt_setting}")
                    if alt_setting == 1:
                        # Switch to UAS mode
                        self._enable_uas_endpoints()
                    else:
                        # Switch to BBB mode (default)
                        self._enable_endpoints()

            if response is not None:
                # IN transfer - send response
                if len(response) > 0:
                    print(f"[USB_PASS] Response ({len(response)} bytes): {response[:32].hex()}...")
                self.gadget.ep0_write(response)
            elif setup.bmRequestType & 0x80:
                # IN transfer but no response - STALL
                print(f"[USB_PASS] STALLing unsupported IN request")
                self.gadget.ep0_stall()
            else:
                # OUT transfer - ACK with zero-length read
                self.gadget.ep0_read(0)

        except Exception as e:
            print(f"[USB_PASS] Error handling control: {e}")
            import traceback
            traceback.print_exc()
            self.gadget.ep0_stall()

    def _enable_endpoints(self):
        """Enable bulk endpoints after configuration.

        Our configuration descriptor defines BBB (Bulk-Only Transport) with 2 endpoints:
        - EP1 IN (0x81) - Bulk IN, 512 bytes
        - EP2 OUT (0x02) - Bulk OUT, 512 bytes

        Raw-gadget requires us to match endpoint types and directions.
        """
        if not self.gadget:
            return

        # Clear UAS-specific handles (not used in BBB mode)
        self.ep_stat_in = None
        self.ep_cmd_out = None

        # Use correct max packet size based on USB speed
        # SuperSpeed/SuperSpeed+ (emu_speed >= 2) uses 1024, High Speed uses 512
        bulk_max_packet = 1024 if self._emu_speed >= 2 else 512
        print(f"[USB_PASS] Using bulk max packet size: {bulk_max_packet} (speed={self._emu_speed})")

        # Query available endpoints from UDC for debugging
        try:
            eps = self.gadget.eps_info()
            print(f"[USB_PASS] Available endpoints from UDC: {len(eps)}")
            bulk_in_candidates = []
            bulk_out_candidates = []
            for ep in eps:
                if ep.name:
                    caps = []
                    if ep.type_bulk:
                        caps.append("bulk")
                    if ep.type_int:
                        caps.append("int")
                    if ep.dir_in:
                        caps.append("IN")
                    if ep.dir_out:
                        caps.append("OUT")
                    # Only show bulk endpoints
                    if ep.type_bulk:
                        print(f"[USB_PASS]   {ep.name}: addr=0x{ep.addr:02X} caps={caps} maxpkt={ep.maxpacket_limit}")
                        if ep.dir_in:
                            bulk_in_candidates.append(ep)
                        if ep.dir_out:
                            bulk_out_candidates.append(ep)
        except RawGadgetError as e:
            print(f"[USB_PASS] eps_info failed: {e}")
            eps = []
            bulk_in_candidates = []
            bulk_out_candidates = []

        # Call vbus_draw before enabling endpoints (per raw-gadget examples)
        try:
            self.gadget.vbus_draw(100)  # 100mA
            print("[USB_PASS] vbus_draw(100) succeeded")
        except RawGadgetError as e:
            print(f"[USB_PASS] vbus_draw failed: {e}")

        # Try enabling with specific addresses from UDC info
        self.ep_data_in = None
        self.ep_data_out = None

        # Try bulk IN with addresses from UDC
        for ep in bulk_in_candidates:
            # The address for IN endpoints needs bit 7 set
            addr = ep.addr | 0x80
            print(f"[USB_PASS] Trying bulk IN {ep.name} with addr=0x{addr:02X}")
            try:
                self.ep_data_in = self.gadget.ep_enable(addr, 0x02, bulk_max_packet)
                print(f"[USB_PASS] Enabled bulk IN (0x{addr:02X}): handle={self.ep_data_in}")
                break
            except RawGadgetError as e:
                print(f"[USB_PASS] Bulk IN enable (0x{addr:02X}) failed: {e}")

        # Try bulk OUT with addresses from UDC
        for ep in bulk_out_candidates:
            # OUT endpoints have bit 7 clear
            addr = ep.addr & 0x7F
            print(f"[USB_PASS] Trying bulk OUT {ep.name} with addr=0x{addr:02X}")
            try:
                self.ep_data_out = self.gadget.ep_enable(addr, 0x02, bulk_max_packet)
                print(f"[USB_PASS] Enabled bulk OUT (0x{addr:02X}): handle={self.ep_data_out}")
                break
            except RawGadgetError as e:
                print(f"[USB_PASS] Bulk OUT enable (0x{addr:02X}) failed: {e}")

        # Start bulk transfer thread if at least one endpoint works
        if self.ep_data_in or self.ep_data_out:
            self._start_bulk_thread()
        else:
            print("[USB_PASS] WARNING: No bulk endpoints enabled, SCSI commands will fail")

    def _enable_uas_endpoints(self):
        """Enable UAS endpoints after SET_INTERFACE alt=1.

        UAS mode uses 4 endpoints:
        - EP1 IN (0x81) - Status pipe
        - EP2 OUT (0x02) - Command pipe
        - EP3 IN (0x83) - Data-In pipe
        - EP4 OUT (0x04) - Data-Out pipe
        """
        if not self.gadget:
            return

        # Use correct max packet size based on USB speed
        bulk_max_packet = 1024 if self._emu_speed >= 2 else 512

        print(f"[USB_PASS] Enabling UAS endpoints (max_packet={bulk_max_packet})...")

        try:
            # EP1 IN (0x81) - Status pipe
            self.ep_stat_in = self.gadget.ep_enable(0x81, 0x02, bulk_max_packet)
            print(f"[USB_PASS] Enabled EP1 IN (status): handle={self.ep_stat_in}")
        except RawGadgetError as e:
            print(f"[USB_PASS] EP1 IN enable failed (non-fatal): {e}")
            self.ep_stat_in = None

        try:
            # EP2 OUT (0x02) - Command pipe
            self.ep_cmd_out = self.gadget.ep_enable(0x02, 0x02, bulk_max_packet)
            print(f"[USB_PASS] Enabled EP2 OUT (command): handle={self.ep_cmd_out}")
        except RawGadgetError as e:
            print(f"[USB_PASS] EP2 OUT enable failed (non-fatal): {e}")
            self.ep_cmd_out = None

        try:
            # EP3 IN (0x83) - Data-In pipe
            self.ep_data_in = self.gadget.ep_enable(0x83, 0x02, bulk_max_packet)
            print(f"[USB_PASS] Enabled EP3 IN (data-in): handle={self.ep_data_in}")
        except RawGadgetError as e:
            print(f"[USB_PASS] EP3 IN enable failed (non-fatal): {e}")
            self.ep_data_in = None

        try:
            # EP4 OUT (0x04) - Data-Out pipe
            self.ep_data_out = self.gadget.ep_enable(0x04, 0x02, bulk_max_packet)
            print(f"[USB_PASS] Enabled EP4 OUT (data-out): handle={self.ep_data_out}")
        except RawGadgetError as e:
            print(f"[USB_PASS] EP4 OUT enable failed (non-fatal): {e}")
            self.ep_data_out = None

        # Start bulk transfer thread if any endpoints work
        if any([self.ep_stat_in, self.ep_cmd_out, self.ep_data_in, self.ep_data_out]):
            self._start_bulk_thread()

    def _start_bulk_thread(self):
        """Start background thread for bulk transfer handling."""
        if self._bulk_thread and self._bulk_thread.is_alive():
            return

        self._bulk_running = True
        self._bulk_thread = threading.Thread(target=self._bulk_transfer_loop, daemon=True)
        self._bulk_thread.start()
        print("[USB_PASS] Bulk transfer thread started")

    def _bulk_transfer_loop(self):
        """Background thread for bulk endpoint transfers using BBB protocol.

        BBB (Bulk-Only Transport) Protocol:
        1. Host sends CBW (Command Block Wrapper) - 31 bytes on Bulk OUT
        2. Data phase (optional) - Bulk IN for reads, Bulk OUT for writes
        3. Device sends CSW (Command Status Wrapper) - 13 bytes on Bulk IN

        CBW structure (31 bytes):
        - Bytes 0-3: Signature 'USBC' (0x55534243)
        - Bytes 4-7: Tag (echoed in CSW)
        - Bytes 8-11: dCBWDataTransferLength
        - Byte 12: bmCBWFlags (bit 7: 0=OUT, 1=IN)
        - Byte 13: bCBWLUN
        - Byte 14: bCBWCBLength (1-16)
        - Bytes 15-30: CBWCB (SCSI CDB)

        CSW structure (13 bytes):
        - Bytes 0-3: Signature 'USBS' (0x55534253)
        - Bytes 4-7: Tag (from CBW)
        - Bytes 8-11: dCSWDataResidue
        - Byte 12: bCSWStatus (0=passed, 1=failed, 2=phase error)
        """
        print("[BULK] Transfer loop starting (BBB mode)")

        # CBW signature
        CBW_SIGNATURE = b'USBC'
        CSW_SIGNATURE = b'USBS'

        while self._bulk_running and self.gadget:
            try:
                # Read CBW on Bulk OUT endpoint
                if self.ep_data_out is None:
                    time.sleep(0.01)
                    continue

                import time as _time
                t_read_start = _time.monotonic()
                cbw_data = self.gadget.ep_read(self.ep_data_out, 31)
                t_read_end = _time.monotonic()
                print(f"[BULK] ep_read took {(t_read_end-t_read_start)*1000:.2f}ms, got {len(cbw_data)} bytes")
                if len(cbw_data) < 31:
                    continue

                # Validate CBW signature
                if cbw_data[0:4] != CBW_SIGNATURE:
                    print(f"[BULK] Invalid CBW signature: {cbw_data[0:4].hex()}")
                    continue

                # Parse CBW
                tag = struct.unpack('<I', cbw_data[4:8])[0]
                data_length = struct.unpack('<I', cbw_data[8:12])[0]
                flags = cbw_data[12]
                lun = cbw_data[13] & 0x0F
                cb_length = cbw_data[14] & 0x1F
                cdb = cbw_data[15:15 + cb_length]

                is_data_in = (flags & 0x80) != 0
                scsi_opcode = cdb[0] if cb_length > 0 else 0

                print(f"[BULK] CBW: tag={tag:08X} len={data_length} "
                      f"flags=0x{flags:02X} lun={lun} cdb_len={cb_length}")
                print(f"[BULK] SCSI opcode=0x{scsi_opcode:02X} cdb={cdb.hex()}")

                # Process SCSI command - this should be very fast
                import time as _time
                t0 = _time.monotonic()
                response_data, csw_status = self._handle_scsi_command(
                    scsi_opcode, cdb, data_length, is_data_in, lun
                )
                t1 = _time.monotonic()
                print(f"[BULK] SCSI handler took {(t1-t0)*1000:.2f}ms, response={len(response_data) if response_data else 0} bytes")

                # Data phase
                residue = data_length
                if response_data and is_data_in:
                    # Send data to host on Bulk IN
                    if self.ep_data_in is not None:
                        t2 = _time.monotonic()
                        print(f"[BULK] Writing {len(response_data)} bytes to EP IN (handle={self.ep_data_in}) at t={t2:.6f}")
                        try:
                            self.gadget.ep_write(self.ep_data_in, response_data)
                            t3 = _time.monotonic()
                            residue = data_length - len(response_data)
                            print(f"[BULK] Sent {len(response_data)} bytes in {(t3-t2)*1000:.2f}ms at t={t3:.6f}, residue={residue}")
                        except RawGadgetError as e:
                            t3 = _time.monotonic()
                            print(f"[BULK] Data IN failed at t={t3:.6f}: {e}")
                            csw_status = 1  # Failed
                    else:
                        print(f"[BULK] ERROR: ep_data_in is None!")

                # Send CSW
                csw = struct.pack('<4sIIB',
                    CSW_SIGNATURE,  # Signature
                    tag,            # Tag (echoed)
                    residue,        # Data residue
                    csw_status      # Status
                )

                if self.ep_data_in is not None:
                    print(f"[BULK] Writing CSW to EP IN (handle={self.ep_data_in})")
                    try:
                        self.gadget.ep_write(self.ep_data_in, csw)
                        print(f"[BULK] CSW sent: status={csw_status}")
                    except RawGadgetError as e:
                        print(f"[BULK] CSW send failed: {e}")
                else:
                    print(f"[BULK] ERROR: Cannot send CSW, ep_data_in is None!")

            except RawGadgetError as e:
                if self._bulk_running:
                    print(f"[BULK] Error: {e}")
                    time.sleep(0.1)
            except Exception as e:
                print(f"[BULK] Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)

        print("[BULK] Transfer loop stopped")

    def _handle_scsi_command(self, opcode: int, cdb: bytes, data_length: int,
                              is_data_in: bool, lun: int) -> tuple:
        """
        Handle SCSI command by injecting to firmware via MMIO.

        The firmware processes SCSI commands through its handler at 0x32E4.
        We inject the CDB via MMIO and let the firmware generate responses.

        For the mock NVMe device, we also provide a backing store at
        /tmp/mock_nvme_device for actual read/write operations.

        Args:
            opcode: SCSI opcode
            cdb: Complete CDB bytes
            data_length: Expected data transfer length
            is_data_in: True for device-to-host, False for host-to-device
            lun: Logical unit number

        Returns:
            Tuple of (response_data, csw_status)
            - response_data: bytes to send to host (for IN transfers)
            - csw_status: 0=passed, 1=failed, 2=phase error
        """
        # SCSI opcodes
        SCSI_TEST_UNIT_READY = 0x00
        SCSI_REQUEST_SENSE = 0x03
        SCSI_INQUIRY = 0x12
        SCSI_MODE_SENSE_6 = 0x1A
        SCSI_READ_FORMAT_CAPACITIES = 0x23
        SCSI_READ_CAPACITY_10 = 0x25
        SCSI_READ_10 = 0x28
        SCSI_WRITE_10 = 0x2A
        SCSI_VERIFY_10 = 0x2F
        SCSI_SYNCHRONIZE_CACHE_10 = 0x35
        SCSI_MODE_SENSE_10 = 0x5A
        SCSI_READ_CAPACITY_16 = 0x9E
        SCSI_READ_16 = 0x88
        SCSI_WRITE_16 = 0x8A

        # 1GB device = 2097152 sectors (512 bytes each)
        DEVICE_SECTORS = 2097152
        SECTOR_SIZE = 512

        print(f"[SCSI] Processing opcode 0x{opcode:02X}")

        if opcode == SCSI_TEST_UNIT_READY:
            # Device is ready
            return b'', 0

        elif opcode == SCSI_INQUIRY:
            # Standard INQUIRY response (36 bytes minimum)
            inquiry_data = bytearray(36)
            inquiry_data[0] = 0x00  # Peripheral device type: direct access block device
            inquiry_data[1] = 0x80  # RMB=1 (removable)
            inquiry_data[2] = 0x06  # Version: SPC-4
            inquiry_data[3] = 0x02  # Response format: 2
            inquiry_data[4] = 31    # Additional length
            inquiry_data[5] = 0x00  # Flags
            inquiry_data[6] = 0x00  # Flags
            inquiry_data[7] = 0x00  # Flags

            # Vendor ID (8 bytes)
            vendor = b'ASMedia '
            inquiry_data[8:16] = vendor[:8]

            # Product ID (16 bytes)
            product = b'ASM2464PD NVMe  '
            inquiry_data[16:32] = product[:16]

            # Product revision (4 bytes)
            revision = b'1.00'
            inquiry_data[32:36] = revision[:4]

            return bytes(inquiry_data[:data_length]), 0

        elif opcode == SCSI_REQUEST_SENSE:
            # No error condition
            sense_data = bytearray(18)
            sense_data[0] = 0x70  # Response code: current errors
            sense_data[2] = 0x00  # Sense key: no sense
            sense_data[7] = 10    # Additional sense length
            sense_data[12] = 0x00  # ASC: no additional sense
            sense_data[13] = 0x00  # ASCQ
            return bytes(sense_data[:min(data_length, 18)]), 0

        elif opcode == SCSI_READ_CAPACITY_10:
            # Return capacity: (last LBA, block size)
            last_lba = DEVICE_SECTORS - 1
            response = struct.pack('>II', last_lba, SECTOR_SIZE)
            print(f"[SCSI] READ_CAPACITY_10: last_lba={last_lba}, block_size={SECTOR_SIZE}")
            return response, 0

        elif opcode == SCSI_READ_CAPACITY_16:
            # Service action: 0x10 = READ CAPACITY (16)
            if len(cdb) >= 2 and (cdb[1] & 0x1F) == 0x10:
                last_lba = DEVICE_SECTORS - 1
                response = struct.pack('>QI', last_lba, SECTOR_SIZE)
                response += b'\x00' * 20  # Pad to 32 bytes
                return response[:min(data_length, 32)], 0
            return b'', 1  # Unknown service action

        elif opcode == SCSI_MODE_SENSE_6:
            # Basic mode sense response
            mode_data = bytearray(4)
            mode_data[0] = 3  # Mode data length
            mode_data[1] = 0  # Medium type
            mode_data[2] = 0  # Device-specific parameter
            mode_data[3] = 0  # Block descriptor length
            return bytes(mode_data[:min(data_length, 4)]), 0

        elif opcode == SCSI_MODE_SENSE_10:
            # Mode sense (10) response
            mode_data = bytearray(8)
            mode_data[0] = 0  # Mode data length MSB
            mode_data[1] = 6  # Mode data length LSB
            mode_data[2] = 0  # Medium type
            mode_data[3] = 0  # Device-specific parameter
            mode_data[6] = 0  # Block descriptor length MSB
            mode_data[7] = 0  # Block descriptor length LSB
            return bytes(mode_data[:min(data_length, 8)]), 0

        elif opcode == SCSI_READ_FORMAT_CAPACITIES:
            # Format capacities list
            response = bytearray(12)
            response[0:4] = b'\x00\x00\x00\x08'  # Capacity list length
            # Capacity descriptor
            num_blocks = DEVICE_SECTORS
            response[4:8] = struct.pack('>I', num_blocks)
            response[8] = 0x02  # Formatted media
            response[9:12] = struct.pack('>I', SECTOR_SIZE)[1:4]
            return bytes(response[:min(data_length, 12)]), 0

        elif opcode == SCSI_READ_10:
            # READ(10): cdb[2-5] = LBA, cdb[7-8] = transfer length
            lba = struct.unpack('>I', cdb[2:6])[0]
            transfer_blocks = struct.unpack('>H', cdb[7:9])[0]
            transfer_size = transfer_blocks * SECTOR_SIZE

            print(f"[SCSI] READ_10: LBA={lba}, blocks={transfer_blocks}, size={transfer_size}")

            # Read from backing store
            data = self._read_backing_store(lba, transfer_blocks, SECTOR_SIZE)
            return data[:min(data_length, transfer_size)], 0

        elif opcode == SCSI_READ_16:
            # READ(16): cdb[2-9] = LBA, cdb[10-13] = transfer length
            lba = struct.unpack('>Q', cdb[2:10])[0]
            transfer_blocks = struct.unpack('>I', cdb[10:14])[0]
            transfer_size = transfer_blocks * SECTOR_SIZE

            print(f"[SCSI] READ_16: LBA={lba}, blocks={transfer_blocks}, size={transfer_size}")

            data = self._read_backing_store(lba, transfer_blocks, SECTOR_SIZE)
            return data[:min(data_length, transfer_size)], 0

        elif opcode == SCSI_WRITE_10:
            # WRITE(10): cdb[2-5] = LBA, cdb[7-8] = transfer length
            lba = struct.unpack('>I', cdb[2:6])[0]
            transfer_blocks = struct.unpack('>H', cdb[7:9])[0]
            transfer_size = transfer_blocks * SECTOR_SIZE

            print(f"[SCSI] WRITE_10: LBA={lba}, blocks={transfer_blocks}, size={transfer_size}")

            # Read data from host
            if self.ep_data_out and transfer_size > 0:
                write_data = self.gadget.ep_read(self.ep_data_out, transfer_size)
                self._write_backing_store(lba, write_data, SECTOR_SIZE)
            return b'', 0

        elif opcode == SCSI_WRITE_16:
            # WRITE(16): cdb[2-9] = LBA, cdb[10-13] = transfer length
            lba = struct.unpack('>Q', cdb[2:10])[0]
            transfer_blocks = struct.unpack('>I', cdb[10:14])[0]
            transfer_size = transfer_blocks * SECTOR_SIZE

            print(f"[SCSI] WRITE_16: LBA={lba}, blocks={transfer_blocks}, size={transfer_size}")

            if self.ep_data_out and transfer_size > 0:
                write_data = self.gadget.ep_read(self.ep_data_out, transfer_size)
                self._write_backing_store(lba, write_data, SECTOR_SIZE)
            return b'', 0

        elif opcode == SCSI_VERIFY_10:
            # Verify - just return success
            return b'', 0

        elif opcode == SCSI_SYNCHRONIZE_CACHE_10:
            # Sync cache - just return success
            return b'', 0

        else:
            print(f"[SCSI] Unknown opcode: 0x{opcode:02X}")
            return b'', 1  # Check condition

    def _get_backing_store_path(self) -> str:
        """Get path to backing store file."""
        return '/tmp/mock_nvme_device'

    def _ensure_backing_store(self) -> bytearray:
        """Get or create in-memory backing store (1GB cached in memory)."""
        if not hasattr(self, '_backing_store_cache'):
            path = self._get_backing_store_path()
            # 1GB = 2097152 sectors * 512 bytes
            DEVICE_SIZE = 2097152 * 512

            # Try to load existing file
            if os.path.exists(path):
                try:
                    with open(path, 'rb') as f:
                        data = f.read()
                    self._backing_store_cache = bytearray(data)
                    # Extend to full size if needed
                    if len(self._backing_store_cache) < DEVICE_SIZE:
                        self._backing_store_cache.extend(b'\x00' * (DEVICE_SIZE - len(self._backing_store_cache)))
                except Exception:
                    self._backing_store_cache = bytearray(DEVICE_SIZE)
            else:
                self._backing_store_cache = bytearray(DEVICE_SIZE)

            print(f"[SCSI] Backing store initialized ({len(self._backing_store_cache)} bytes)")

        return self._backing_store_cache

    def _read_backing_store(self, lba: int, blocks: int, sector_size: int) -> bytes:
        """Read data from in-memory backing store."""
        cache = self._ensure_backing_store()
        offset = lba * sector_size
        size = blocks * sector_size

        if offset + size > len(cache):
            # Read what we can, pad with zeros
            available = max(0, len(cache) - offset)
            return bytes(cache[offset:offset + available]) + b'\x00' * (size - available)

        return bytes(cache[offset:offset + size])

    def _write_backing_store(self, lba: int, data: bytes, sector_size: int):
        """Write data to in-memory backing store."""
        cache = self._ensure_backing_store()
        offset = lba * sector_size

        if offset < len(cache):
            end = min(offset + len(data), len(cache))
            cache[offset:end] = data[:end - offset]

    def _flush_backing_store(self):
        """Flush in-memory backing store to disk."""
        if hasattr(self, '_backing_store_cache'):
            path = self._get_backing_store_path()
            try:
                with open(path, 'wb') as f:
                    f.write(self._backing_store_cache)
                print(f"[SCSI] Backing store flushed to {path}")
            except Exception as e:
                print(f"[SCSI] Flush error: {e}")

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
