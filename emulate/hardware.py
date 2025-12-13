"""
ASM2464PD Hardware Emulation

This module provides realistic hardware emulation for the ASM2464PD.
Only hardware registers (XDATA >= 0x6000) are emulated here.
RAM (XDATA < 0x6000) is handled by the memory system, not this module.
"""

from typing import TYPE_CHECKING, Dict, Set, Callable
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from memory import Memory


@dataclass
class USBCommand:
    """USB command queued for firmware processing."""
    cmd: int           # Command type (0xE4=read, 0xE5=write, 0x8A=scsi)
    addr: int          # Target XDATA address
    data: bytes        # Data for write commands
    response: bytes = b''  # Response data for read commands

@dataclass
class HardwareState:
    """
    Hardware state for ASM2464PD emulation.

    Only emulates actual hardware registers (addresses >= 0x6000).
    RAM variables are handled by the memory system.
    """

    # Logging
    log_reads: bool = False
    log_writes: bool = False
    log_uart: bool = True

    # Cycle counter for timing-based responses
    cycles: int = 0

    # Hardware state
    usb_connected: bool = False
    usb_connect_delay: int = 500000  # Cycles before USB plug-in event (after init)

    # Polling counters - track how many times an address is polled
    poll_counts: Dict[int, int] = field(default_factory=dict)

    # Register values - only for hardware registers >= 0x6000
    regs: Dict[int, int] = field(default_factory=dict)

    # Callbacks for specific addresses
    read_callbacks: Dict[int, Callable[['HardwareState', int], int]] = field(default_factory=dict)
    write_callbacks: Dict[int, Callable[['HardwareState', int, int], None]] = field(default_factory=dict)

    # USB command queue
    usb_cmd_queue: list = field(default_factory=list)
    usb_cmd_pending: bool = False
    usb_ep0_buf: bytearray = field(default_factory=lambda: bytearray(64))  # Control EP buffer (0x9E00)
    usb_ep0_len: int = 0
    usb_data_buf: bytearray = field(default_factory=lambda: bytearray(4096))  # Data buffer
    usb_data_len: int = 0
    usb_ep_data_buf: bytearray = field(default_factory=lambda: bytearray(2048))  # EP data buffer (0xD800)

    # Memory reference for E4/E5 commands (set by create_hardware_hooks)
    memory: 'Memory' = None

    # UART output buffer for line-based output
    uart_buffer: str = ""

    # USB command injection timing
    usb_inject_delay: int = 100  # Cycles after USB connect to inject command (short delay)
    usb_injected: bool = False

    # USB endpoint selection tracking
    usb_ep_selected: int = 0  # Currently selected endpoint index (0-31)

    def __post_init__(self):
        """Initialize hardware register defaults."""
        self._init_registers()
        self._setup_callbacks()

    def _init_registers(self):
        """
        Set default values for hardware registers.
        Only addresses >= 0x6000 are hardware registers.
        """
        # ============================================
        # USB Controller Registers (0x9xxx)
        # ============================================
        self.regs[0x9000] = 0x00  # USB status - bit 7 = connected
        self.regs[0x90E0] = 0x00  # USB speed
        self.regs[0x9100] = 0x00  # USB link status
        self.regs[0x9105] = 0x00  # USB PHY status
        self.regs[0x91C0] = 0x02  # USB PHY control
        self.regs[0x91D0] = 0x00  # USB PHY config

        # ============================================
        # Power Management Registers (0x92xx)
        # ============================================
        self.regs[0x92C0] = 0x81  # Power enable
        self.regs[0x92C1] = 0x03  # Clocks enabled
        self.regs[0x92C2] = 0x40  # Power state - bit 6 enables PD task path at 0xBF44
        self.regs[0x92C5] = 0x04  # PHY powered
        self.regs[0x92E0] = 0x02  # Power domain
        self.regs[0x92F7] = 0x40  # Power status
        self.regs[0x92FB] = 0x01  # Power sequence complete (checked at 0x9C42)

        # ============================================
        # PCIe Registers (0xBxxx)
        # ============================================
        self.regs[0xB238] = 0x00  # PCIe trigger - not busy
        self.regs[0xB254] = 0x00  # PCIe trigger write
        self.regs[0xB296] = 0x02  # PCIe status - complete
        self.regs[0xB401] = 0x01  # PCIe tunnel enabled
        self.regs[0xB480] = 0x01  # PCIe link up

        # ============================================
        # UART Registers (0xC0xx)
        # ============================================
        self.regs[0xC000] = 0x00  # UART TX data
        self.regs[0xC001] = 0x00  # UART TX data (alt)
        self.regs[0xC009] = 0x60  # UART LSR - TX empty, ready

        # ============================================
        # NVMe Controller Registers (0xC4xx, 0xC5xx)
        # ============================================
        self.regs[0xC412] = 0x02  # NVMe ready
        self.regs[0xC471] = 0x00  # NVMe queue busy - bit 0 = queue busy
        self.regs[0xC47A] = 0x00  # NVMe command status
        self.regs[0xC520] = 0x80  # NVMe link ready

        # ============================================
        # PHY Registers (0xC6xx)
        # ============================================
        self.regs[0xC620] = 0x00  # PHY control
        self.regs[0xC655] = 0x08  # PHY config
        self.regs[0xC65A] = 0x09  # PHY config
        self.regs[0xC6B3] = 0x30  # PHY status - bits 4,5 set

        # ============================================
        # Interrupt/DMA/Flash Registers (0xC8xx)
        # ============================================
        self.regs[0xC800] = 0x00  # Interrupt status
        self.regs[0xC802] = 0x00  # Interrupt status 2
        self.regs[0xC806] = 0x00  # System interrupt status
        self.regs[0xC80A] = 0x00  # PCIe/NVMe interrupt - bit 6 triggers PD debug
        self.regs[0xC8A9] = 0x00  # Flash CSR - not busy
        self.regs[0xC8AA] = 0x00  # Flash command
        self.regs[0xC8B8] = 0x00  # Flash/DMA status
        self.regs[0xC8D6] = 0x04  # DMA status - done

        # ============================================
        # USB Power Delivery (PD) Registers (0xCAxx)
        # ============================================
        self.regs[0xCA00] = 0x00  # PD control
        self.regs[0xCA06] = 0x00  # PD status
        self.regs[0xCA0A] = 0x00  # PD interrupt control
        self.regs[0xCA0D] = 0x00  # PD interrupt status 1 - bit 3 = interrupt pending
        self.regs[0xCA0E] = 0x00  # PD interrupt status 2 - bit 2 = interrupt pending
        self.regs[0xCA81] = 0x00  # PD extended status

        # ============================================
        # Timer/CPU Control Registers (0xCCxx, 0xCDxx)
        # ============================================
        self.regs[0xCC11] = 0x00  # Timer 0 CSR
        self.regs[0xCC17] = 0x00  # Timer 1 CSR
        self.regs[0xCC1D] = 0x00  # Timer 2 CSR
        self.regs[0xCC23] = 0x00  # Timer 3 CSR
        self.regs[0xCC33] = 0x04  # CPU exec status
        self.regs[0xCC37] = 0x00  # CPU control
        self.regs[0xCC3B] = 0x00  # CPU control 2
        self.regs[0xCC3D] = 0x00  # CPU control 3
        self.regs[0xCC3E] = 0x00  # CPU control 4
        self.regs[0xCC3F] = 0x00  # CPU control 5
        self.regs[0xCC81] = 0x00  # Timer/DMA control
        self.regs[0xCC82] = 0x00  # Timer/DMA address low
        self.regs[0xCC83] = 0x00  # Timer/DMA address high
        self.regs[0xCC89] = 0x00  # Timer/DMA status - bit 1 = complete
        self.regs[0xCD31] = 0x01  # PHY init status - bit 0 = ready

        # ============================================
        # SCSI/DMA Registers (0xCExx)
        # ============================================
        self.regs[0xCE5D] = 0xFF  # Debug enable mask - all levels enabled
        self.regs[0xCE89] = 0x01  # SCSI DMA status - bit 0 = ready

        # NOTE: 0x707x addresses are NOT hardware registers!
        # They are flash buffer RAM (0x7000-0x7FFF) loaded from flash config.
        # Flash buffer is handled as regular XDATA, not MMIO.

        # ============================================
        # Debug/Command Engine Registers (0xE4xx)
        # ============================================
        self.regs[0xE40F] = 0x00  # PD event type (for debug output)
        self.regs[0xE410] = 0x00  # PD sub-event (for debug output)
        self.regs[0xE41C] = 0x00  # Command engine status

        # ============================================
        # System Status Registers (0xE7xx)
        # ============================================
        self.regs[0xE710] = 0x00  # System status
        self.regs[0xE717] = 0x00  # System status 2
        self.regs[0xE751] = 0x00  # System status 3
        self.regs[0xE764] = 0x00  # System status 4
        self.regs[0xE795] = 0x21  # Flash ready + USB state 3 flag (bit 5)
        self.regs[0xE7E3] = 0x80  # PHY link ready

        # ============================================
        # PHY Completion / Debug Registers (0xE3xx)
        # ============================================
        self.regs[0xE302] = 0x40  # PHY completion status - bit 6 = complete

    def _setup_callbacks(self):
        """Setup read/write callbacks for hardware with special behavior."""
        # UART TX - capture output
        self.write_callbacks[0xC000] = self._uart_tx
        self.write_callbacks[0xC001] = self._uart_tx

        # PCIe status - complete after trigger
        self.read_callbacks[0xB296] = self._pcie_status_read
        self.write_callbacks[0xB254] = self._pcie_trigger_write

        # Flash CSR - auto-complete
        self.read_callbacks[0xC8A9] = self._flash_csr_read
        self.write_callbacks[0xC8AA] = self._flash_cmd_write

        # DMA status
        self.read_callbacks[0xC8D6] = self._dma_status_read

        # Flash/DMA busy - auto-clear
        self.read_callbacks[0xC8B8] = self._busy_reg_read

        # System interrupt status - clear on read
        self.read_callbacks[0xC806] = self._int_status_read

        # Timer CSRs
        for addr in [0xCC11, 0xCC17, 0xCC1D, 0xCC23]:
            self.read_callbacks[addr] = self._timer_csr_read
            self.write_callbacks[addr] = self._timer_csr_write

        # Timer/DMA status register (0xCC89) - set complete bit after polling
        self.read_callbacks[0xCC89] = self._timer_dma_status_read

        # PHY init status
        self.read_callbacks[0xCD31] = self._phy_status_read

        # Command engine status
        self.read_callbacks[0xE41C] = self._cmd_engine_read

        # PD interrupt status - set by USB PD events
        self.read_callbacks[0xCA0D] = self._pd_interrupt_read
        self.read_callbacks[0xCA0E] = self._pd_interrupt_read

        # USB Endpoint 0 buffer (0x9E00-0x9E3F)
        for addr in range(0x9E00, 0x9E40):
            self.read_callbacks[addr] = self._usb_ep0_buf_read

        # USB EP0 CSR (0x9E10)
        self.read_callbacks[0x9E10] = self._usb_ep0_csr_read
        self.write_callbacks[0x9E10] = self._usb_ep0_csr_write

        # USB EP data buffer (0xD800-0xDFFF) - endpoint data for bulk/control transfers
        for addr in range(0xD800, 0xE000):
            self.read_callbacks[addr] = self._usb_ep_data_buf_read
            self.write_callbacks[addr] = self._usb_ep_data_buf_write

        # USB endpoint selection/status registers
        self.read_callbacks[0xC4EC] = self._usb_ep_status_read
        self.write_callbacks[0xC4ED] = self._usb_ep_index_write
        self.read_callbacks[0xC4EE] = self._usb_ep_id_low_read
        self.read_callbacks[0xC4EF] = self._usb_ep_id_high_read

    # ============================================
    # UART Callbacks
    # ============================================
    def _uart_tx(self, hw: 'HardwareState', addr: int, value: int):
        """Handle UART transmit with message buffering."""
        if self.log_uart:
            if value == 0x0A:  # Newline - print buffered line
                if self.uart_buffer:
                    print(f"[{self.cycles:8d}] [UART] {self.uart_buffer}")
                    self.uart_buffer = ""
            elif value == 0x0D:  # Carriage return - ignore
                pass
            elif 0x20 <= value < 0x7F:  # Printable ASCII
                self.uart_buffer += chr(value)
                # Flush on ']' to show complete [message] blocks
                if chr(value) == ']':
                    print(f"[{self.cycles:8d}] [UART] {self.uart_buffer}")
                    self.uart_buffer = ""
            # For very long lines, flush periodically
            if len(self.uart_buffer) > 200:
                print(f"[{self.cycles:8d}] [UART] {self.uart_buffer}")
                self.uart_buffer = ""
        else:
            try:
                if 0x20 <= value < 0x7F or value in (0x0A, 0x0D):
                    print(chr(value), end='', flush=True)
            except:
                pass

    # ============================================
    # PCIe Callbacks
    # ============================================
    def _pcie_status_read(self, hw: 'HardwareState', addr: int) -> int:
        """PCIe status - return complete."""
        return 0x02

    def _pcie_trigger_write(self, hw: 'HardwareState', addr: int, value: int):
        """PCIe trigger - set complete status."""
        self.regs[0xB296] = 0x02

    # ============================================
    # Flash/DMA Callbacks
    # ============================================
    def _flash_csr_read(self, hw: 'HardwareState', addr: int) -> int:
        """Flash CSR - not busy."""
        return 0x00

    def _flash_cmd_write(self, hw: 'HardwareState', addr: int, value: int):
        """Flash command - immediate complete."""
        self.regs[0xC8A9] = 0x00

    def _dma_status_read(self, hw: 'HardwareState', addr: int) -> int:
        """DMA status - done."""
        return 0x04

    def _busy_reg_read(self, hw: 'HardwareState', addr: int) -> int:
        """Busy register - auto-clear after polling."""
        count = self.poll_counts.get(addr, 0)
        value = self.regs.get(addr, 0)
        if count >= 3 and (value & 0x01):
            value &= ~0x01
            self.regs[addr] = value
        return value

    # ============================================
    # Interrupt Callbacks
    # ============================================
    def _int_status_read(self, hw: 'HardwareState', addr: int) -> int:
        """System interrupt status - clear on read."""
        value = self.regs.get(addr, 0)
        if value & 0x01:
            self.regs[addr] = value & ~0x01
        return value

    def _pd_interrupt_read(self, hw: 'HardwareState', addr: int) -> int:
        """PD interrupt status - returns current state."""
        return self.regs.get(addr, 0)

    # ============================================
    # Timer Callbacks
    # ============================================
    def _timer_csr_read(self, hw: 'HardwareState', addr: int) -> int:
        """Timer CSR - auto-set ready bit after polling."""
        count = self.poll_counts.get(addr, 0)
        value = self.regs.get(addr, 0)
        # The firmware polls for bit 1 (0x02) to be set - indicating timer ready/complete
        # Set bit 1 after a few polls to avoid infinite wait
        if count >= 2:
            value |= 0x02  # Set ready/complete bit
            self.regs[addr] = value
        return value

    def _timer_csr_write(self, hw: 'HardwareState', addr: int, value: int):
        """Timer CSR write."""
        if value & 0x04:  # Clear flag
            value &= ~0x02
        self.regs[addr] = value
        self.poll_counts[addr] = 0

    def _timer_dma_status_read(self, hw: 'HardwareState', addr: int) -> int:
        """Timer/DMA status (0xCC89) - set complete bit after polling."""
        count = self.poll_counts.get(addr, 0)
        value = self.regs.get(addr, 0)
        # The firmware polls for bit 1 (0x02) to be set - indicating DMA complete
        if count >= 2:
            value |= 0x02  # Set complete bit
            self.regs[addr] = value
        return value

    # ============================================
    # PHY/CPU Callbacks
    # ============================================
    def _phy_status_read(self, hw: 'HardwareState', addr: int) -> int:
        """PHY status - bit 0 = ready, bit 1 = busy."""
        # Return ready state: bit 0 set, bit 1 clear
        return 0x01

    def _cmd_engine_read(self, hw: 'HardwareState', addr: int) -> int:
        """Command engine - auto-clear bit 0 after polling."""
        count = self.poll_counts.get(addr, 0)
        value = self.regs.get(addr, 0)
        if count >= 3 and (value & 0x01):
            value &= ~0x01
            self.regs[addr] = value
        return value

    # ============================================
    # USB Command Injection
    # ============================================
    def queue_usb_command(self, cmd: int, addr: int, data: bytes = b''):
        """
        Queue a USB command for firmware processing.

        Commands (from python/usb.py):
        - 0xE4: Read from XDATA (addr = 0x5XXXXX maps to firmware XDATA)
        - 0xE5: Write to XDATA
        - 0x8A: SCSI write command

        Address mapping: (addr & 0x1FFFF) | 0x500000 in usb.py
        So 0x5XXXXX -> XDATA 0xXXXX (lower 17 bits)
        """
        usb_cmd = USBCommand(cmd=cmd, addr=addr, data=data)
        self.usb_cmd_queue.append(usb_cmd)

        if self.log_writes:
            print(f"[USB] Queued cmd=0x{cmd:02X} addr=0x{addr:04X} len={len(data)}")

        # Trigger USB interrupt to wake up firmware
        self._trigger_usb_interrupt()

    def queue_e4_read(self, xdata_addr: int, size: int = 1):
        """
        Queue an E4 read command (read XDATA).

        Format from usb.py: struct.pack('>BBBHB', 0xE4, size, addr >> 16, addr & 0xFFFF, 0)
        """
        # Pack command into EP0 buffer format
        cmd_bytes = bytes([
            0xE4,                      # Command
            size,                      # Size to read
            (xdata_addr >> 16) & 0xFF, # High byte (usually 0x05 for XDATA)
            (xdata_addr >> 8) & 0xFF,  # Mid byte
            xdata_addr & 0xFF,         # Low byte
            0x00                       # Reserved
        ])
        self.queue_usb_command(0xE4, xdata_addr & 0xFFFF, cmd_bytes)

    def queue_e5_write(self, xdata_addr: int, value: int):
        """
        Queue an E5 write command (write XDATA).

        Format from usb.py: struct.pack('>BBBHB', 0xE5, value, addr >> 16, addr & 0xFFFF, 0)
        """
        cmd_bytes = bytes([
            0xE5,                      # Command
            value & 0xFF,              # Value to write
            (xdata_addr >> 16) & 0xFF, # High byte (usually 0x05 for XDATA)
            (xdata_addr >> 8) & 0xFF,  # Mid byte
            xdata_addr & 0xFF,         # Low byte
            0x00                       # Reserved
        ])
        self.queue_usb_command(0xE5, xdata_addr & 0xFFFF, cmd_bytes)

    def queue_init_sequence(self):
        """
        Queue the USB initialization sequence from usb.py.

        Init sequence:
        - WriteOp(0x54b, b' ')   -> write 0x20 to 0x054B
        - WriteOp(0x54e, b'\x04') -> write 0x04 to 0x054E
        - WriteOp(0x0, b'\x01')  -> write 0x01 to 0x0000
        """
        print("[USB] === QUEUING INIT SEQUENCE ===")
        self.queue_e5_write(0x054B, 0x20)
        self.queue_e5_write(0x054E, 0x04)
        self.queue_e5_write(0x0000, 0x01)

    def inject_usb_command(self, cmd_type: int, xdata_addr: int, value: int = 0, size: int = 1):
        """
        Inject a USB command through the USB endpoint buffer.
        This simulates what the real USB host controller would do.

        cmd_type: 0xE4 (read) or 0xE5 (write)
        xdata_addr: Target XDATA address (will be mapped to 0x5XXXXX)
        value: Value to write (for E5 commands)
        size: Bytes to read (for E4 commands)
        """
        # Map address to USB format: (addr & 0x1FFFF) | 0x500000
        usb_addr = (xdata_addr & 0x1FFFF) | 0x500000

        # Build command packet: >BBBHB format (6 bytes)
        # Byte 0: Command (0xE4 read, 0xE5 write)
        # Byte 1: Size (for read) or Value (for write)
        # Byte 2: Address high byte (0x50 for XDATA)
        # Byte 3-4: Address low 16 bits
        # Byte 5: Reserved (0)
        cmd_bytes = bytes([
            cmd_type,
            size if cmd_type == 0xE4 else value,
            (usb_addr >> 16) & 0xFF,
            (usb_addr >> 8) & 0xFF,
            usb_addr & 0xFF,
            0x00
        ])

        print(f"[{self.cycles:8d}] [USB] Inject cmd=0x{cmd_type:02X} addr=0x{xdata_addr:04X} "
              f"{'size' if cmd_type == 0xE4 else 'val'}=0x{cmd_bytes[1]:02X} bytes={cmd_bytes.hex()}")

        # Write command to USB endpoint data buffer (emulates USB controller DMA)
        # Firmware reads from 0xD800 + (endpoint * 0x30) for EP0, that's just 0xD800
        for i, b in enumerate(cmd_bytes):
            self.usb_ep_data_buf[i] = b
        print(f"[{self.cycles:8d}] [USB] Wrote {len(cmd_bytes)} bytes to EP data buffer")

        # Also write to USB EP0 control buffer (0x9E00) for compatibility
        for i, b in enumerate(cmd_bytes):
            self.usb_ep0_buf[i] = b
        self.usb_ep0_len = len(cmd_bytes)

        # Set USB data available flags to trigger firmware USB handler
        self.regs[0xC4EC] = self.regs.get(0xC4EC, 0) | 0x01  # USB EP data available (checked at 0x18A5)
        self.regs[0xC802] = self.regs.get(0xC802, 0) | 0x01  # USB interrupt pending
        self.regs[0x9E10] = 0x01   # EP0 has data available

        # Set USB endpoint status registers (checked after EP ID match)
        # 0x9096 + ep_index: If 0, go to command handler; if != 0, just exit
        # 0x90A1 + ep_index = endpoint data ready status (checked at 0x1926, bit 0 = ready)
        self.regs[0x9096] = 0x00   # EP0 status - 0 to enable command processing path
        self.regs[0x90A1] = 0x01   # EP0 data ready bit 0

        # Endpoint ID for index 0 is returned dynamically by _usb_ep_id_*_read callbacks
        # The callbacks return 0x00/0x00 when usb_cmd_pending is true and ep_selected == 0

        self.usb_cmd_pending = True

    def _trigger_usb_interrupt(self):
        """Trigger USB interrupt to process queued command."""
        if not self.usb_connected:
            return

        # Set USB endpoint interrupt bits
        # REG_INT_USB_STATUS (0xC802) bit 0 = endpoint 0 data ready
        # REG_USB_STATUS (0x9000) bit 0 = USB active
        self.regs[0xC802] |= 0x01  # EP0 data ready
        self.regs[0x9000] |= 0x01  # USB active

        # Set EP0 has data flag
        # REG_USB_EP0_CSR (0x9E10) - EP0 control/status
        self.regs[0x9E10] = 0x01  # Data available

        self.usb_cmd_pending = True

    def _process_usb_command(self):
        """
        Process next USB command in queue.
        Called when firmware reads USB endpoint buffer.
        """
        if not self.usb_cmd_queue:
            return None

        cmd = self.usb_cmd_queue.pop(0)
        print(f"[USB] Processing cmd=0x{cmd.cmd:02X} addr=0x{cmd.addr:04X}")

        # Copy command to EP0 buffer
        for i, b in enumerate(cmd.data[:64]):
            self.usb_ep0_buf[i] = b
        self.usb_ep0_len = len(cmd.data)

        # Handle E4 read - prepare response data
        if cmd.cmd == 0xE4 and self.memory:
            size = cmd.data[1] if len(cmd.data) > 1 else 1
            response = bytearray(size)
            for i in range(size):
                response[i] = self.memory.read_xdata(cmd.addr + i)
            cmd.response = bytes(response)
            print(f"[USB] E4 read response: {response.hex()}")

        # Handle E5 write - perform the write directly
        if cmd.cmd == 0xE5 and self.memory:
            value = cmd.data[1] if len(cmd.data) > 1 else 0
            self.memory.write_xdata(cmd.addr, value)
            print(f"[USB] E5 wrote 0x{value:02X} to 0x{cmd.addr:04X}")

        if not self.usb_cmd_queue:
            self.usb_cmd_pending = False

        return cmd

    # ============================================
    # USB Endpoint Callbacks
    # ============================================
    def _usb_ep0_buf_read(self, hw: 'HardwareState', addr: int) -> int:
        """Read from USB EP0 buffer (0x9E00-0x9E3F)."""
        offset = addr - 0x9E00
        if offset < len(self.usb_ep0_buf):
            return self.usb_ep0_buf[offset]
        return 0x00

    def _usb_ep0_csr_read(self, hw: 'HardwareState', addr: int) -> int:
        """Read USB EP0 CSR - check if command pending."""
        # Process next command when firmware reads CSR
        if self.usb_cmd_pending and self.usb_cmd_queue:
            self._process_usb_command()
            return 0x01  # Data ready
        return 0x00

    def _usb_ep0_csr_write(self, hw: 'HardwareState', addr: int, value: int):
        """Write USB EP0 CSR - acknowledge command."""
        if value & 0x80:  # Clear data ready
            self.regs[0x9E10] = 0x00
            # Trigger next command if queued
            if self.usb_cmd_queue:
                self._trigger_usb_interrupt()

    def _usb_ep_data_buf_read(self, hw: 'HardwareState', addr: int) -> int:
        """Read from USB EP data buffer (0xD800-0xDFFF)."""
        offset = addr - 0xD800
        if offset < len(self.usb_ep_data_buf):
            value = self.usb_ep_data_buf[offset]
            # Always log reads from command area (first 8 bytes)
            if offset < 8:
                print(f"[{self.cycles:8d}] [USB] Read EP buf 0x{addr:04X} = 0x{value:02X}")
            return value
        return 0x00

    def _usb_ep_data_buf_write(self, hw: 'HardwareState', addr: int, value: int):
        """Write to USB EP data buffer (0xD800-0xDFFF)."""
        offset = addr - 0xD800
        if offset < len(self.usb_ep_data_buf):
            self.usb_ep_data_buf[offset] = value

    def _usb_ep_status_read(self, hw: 'HardwareState', addr: int) -> int:
        """Read USB EP status register 0xC4EC - indicates USB data availability."""
        value = self.regs.get(addr, 0x00)
        if self.usb_cmd_pending:
            print(f"[{self.cycles:8d}] [USB] Read 0xC4EC = 0x{value:02X}")
        return value

    def _usb_ep_index_write(self, hw: 'HardwareState', addr: int, value: int):
        """Write USB EP index register 0xC4ED - selects which endpoint to query."""
        # Low 5 bits are the endpoint index (0-31)
        self.usb_ep_selected = value & 0x1F
        self.regs[addr] = value
        if self.usb_cmd_pending:
            print(f"[{self.cycles:8d}] [USB] Select EP index {self.usb_ep_selected}")

    def _usb_ep_id_low_read(self, hw: 'HardwareState', addr: int) -> int:
        """Read USB EP ID low byte (0xC4EE) for currently selected endpoint."""
        # When USB command pending and EP0 selected, return the value from RAM 0x0056
        # This matches what firmware expects (it compares 0xC4EE/0xC4EF with 0x0056/0x0057)
        if self.usb_cmd_pending and self.usb_ep_selected == 0 and self.memory:
            # Read the expected value from RAM and return it so comparison passes
            expected = self.memory.xdata[0x0056]
            print(f"[{self.cycles:8d}] [USB] EP0 ID low = 0x{expected:02X} (from RAM 0x0056)")
            return expected
        return 0xFF  # No endpoint / invalid

    def _usb_ep_id_high_read(self, hw: 'HardwareState', addr: int) -> int:
        """Read USB EP ID high byte (0xC4EF) for currently selected endpoint."""
        # When USB command pending and EP0 selected, return the value from RAM 0x0057
        # This matches what firmware expects (it compares 0xC4EE/0xC4EF with 0x0056/0x0057)
        if self.usb_cmd_pending and self.usb_ep_selected == 0 and self.memory:
            # Read the expected value from RAM and return it so comparison passes
            expected = self.memory.xdata[0x0057]
            print(f"[{self.cycles:8d}] [USB] EP0 ID high = 0x{expected:02X} (from RAM 0x0057)")
            return expected
        return 0xFF  # No endpoint / invalid

    # ============================================
    # Main Read/Write Interface
    # ============================================
    def read(self, addr: int) -> int:
        """Read from hardware register."""
        addr &= 0xFFFF

        # Only handle hardware registers (>= 0x6000)
        if addr < 0x6000:
            return 0x00  # Should not be called for RAM

        self.poll_counts[addr] = self.poll_counts.get(addr, 0) + 1

        if addr in self.read_callbacks:
            value = self.read_callbacks[addr](self, addr)
        elif addr in self.regs:
            value = self.regs[addr]
        else:
            value = 0x00

        if self.log_reads:
            print(f"[{self.cycles:8d}] [HW] Read  0x{addr:04X} = 0x{value:02X}")

        return value

    def write(self, addr: int, value: int):
        """Write to hardware register."""
        addr &= 0xFFFF
        value &= 0xFF

        # Only handle hardware registers (>= 0x6000)
        if addr < 0x6000:
            return  # Should not be called for RAM

        if self.log_writes:
            print(f"[{self.cycles:8d}] [HW] Write 0x{addr:04X} = 0x{value:02X}")

        if addr in self.write_callbacks:
            self.write_callbacks[addr](self, addr, value)
        else:
            self.regs[addr] = value

    # ============================================
    # Tick - Advance Hardware State
    # ============================================
    def tick(self, cycles: int, cpu=None):
        """Advance hardware state by cycles."""
        self.cycles += cycles

        # USB plug-in event after delay
        if not self.usb_connected and self.cycles > self.usb_connect_delay:
            self.usb_connected = True
            print(f"\n[{self.cycles:8d}] [HW] === USB PLUG-IN EVENT ===")

            # Update USB hardware registers
            self.regs[0x9000] = 0x81  # USB connected (bit 7) + active (bit 0)
            self.regs[0x90E0] = 0x02  # USB3 speed
            self.regs[0x9100] = 0x02  # USB link active
            self.regs[0x9101] = 0x21  # USB connection status - bit 5 for INT handler path + bit 0
            self.regs[0x9105] = 0xFF  # PHY active

            # Set USB interrupt for NVMe queue processing (triggers usb_ep_loop_180d)
            # REG_INT_USB_STATUS bit 0 triggers interrupt handler at 0x0E5A
            # Bit 2 triggers the nvme_cmd_status_init path
            self.regs[0xC802] = 0x05  # Bit 0 + Bit 2

            # Set NVMe queue busy - triggers the usb_ep_loop_180d(1) call
            self.regs[0xC471] = 0x01  # Bit 0 - queue busy

            # Set PD interrupt pending - this triggers the PD handler
            self.regs[0xCA0D] = 0x08  # Bit 3 - PD interrupt for state 1
            self.regs[0xCA0E] = 0x04  # Bit 2 - PD interrupt for state 2

            # Set debug trigger
            self.regs[0xC80A] = 0x40  # Bit 6 - triggers PD debug output

            # Set PD event info for debug output
            self.regs[0xE40F] = 0x01  # PD event type
            self.regs[0xE410] = 0x00  # PD sub-event

            print(f"[{self.cycles:8d}] [HW] USB: 0x9000=0x81, C802=0x05, C471=0x01, CA0D=0x08")

            # Trigger External Interrupt 0 to invoke the interrupt handler at 0x0E33
            # This requires IE register (0xA8) to have EA (bit 7) and EX0 (bit 0) set
            if cpu:
                # Enable global interrupts (EA) and EX0 in IE register
                ie = self.memory.read_sfr(0xA8) if self.memory else 0
                ie |= 0x81  # EA (bit 7) + EX0 (bit 0)
                if self.memory:
                    self.memory.write_sfr(0xA8, ie)
                cpu._ext0_pending = True
                print(f"[{self.cycles:8d}] [HW] Triggered EX0 interrupt (IE=0x{ie:02X})")

        # Periodic timer interrupt
        if self.cycles % 1000 == 0:
            self.regs[0xC806] |= 0x01

        # Inject USB command after USB connected and additional delay
        if self.usb_connected and not self.usb_injected:
            if self.cycles > self.usb_connect_delay + self.usb_inject_delay:
                self.usb_injected = True
                print(f"\n[{self.cycles:8d}] [HW] === INJECTING USB MEMORY READ ===")
                # Inject E4 read command to read memory at 0x0000 (8 bytes)
                self.inject_usb_command(0xE4, 0x0000, size=8)



def create_hardware_hooks(memory: 'Memory', hw: HardwareState):
    """
    Register hardware hooks with memory system.
    Only hooks hardware register addresses (>= 0x6000).
    """

    # Hardware register ranges (all >= 0x6000)
    # NOTE: 0x7000-0x7FFF is flash buffer RAM, NOT hardware registers
    mmio_ranges = [
        (0x8000, 0x9000),   # USB/SCSI Data Buffer
        (0x9000, 0x9400),   # USB Interface
        (0x92C0, 0x9300),   # Power Management
        (0x9E00, 0xA000),   # USB Control Buffer
        (0xB200, 0xB900),   # PCIe Passthrough
        (0xC000, 0xC100),   # UART
        (0xC400, 0xC600),   # NVMe Interface
        (0xC600, 0xC700),   # PHY Extended
        (0xC800, 0xC900),   # Interrupt/DMA/Flash
        (0xCA00, 0xCB00),   # PD Controller
        (0xCC00, 0xCF00),   # Timer/CPU/SCSI
        (0xD800, 0xE000),   # USB Endpoint Data Buffer
        (0xE300, 0xE400),   # PHY Completion / Debug
        (0xE400, 0xE500),   # Command Engine
        (0xE700, 0xE800),   # System Status
    ]

    # Set memory reference for USB commands
    hw.memory = memory

    def make_read_hook(hw_ref):
        def hook(addr):
            return hw_ref.read(addr)
        return hook

    def make_write_hook(hw_ref):
        def hook(addr, value):
            hw_ref.write(addr, value)
        return hook

    read_hook = make_read_hook(hw)
    write_hook = make_write_hook(hw)

    for start, end in mmio_ranges:
        for addr in range(start, end):
            memory.xdata_read_hooks[addr] = read_hook
            memory.xdata_write_hooks[addr] = write_hook
