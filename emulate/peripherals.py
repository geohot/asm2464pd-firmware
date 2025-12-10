"""
ASM2464PD Peripheral Emulation

This module implements MMIO peripherals for the ASM2464PD including:
- UART Controller
- Timer/Counter
- USB Interface (stub)
- NVMe Interface (stub)
- PCIe/Thunderbolt Interface (stub)
- DMA Controller (stub)
- Flash Controller (stub)
"""

from typing import TYPE_CHECKING, Callable, Optional
from dataclasses import dataclass, field
import struct

if TYPE_CHECKING:
    from memory import Memory


@dataclass
class UART:
    """UART Controller Emulation (0xC000-0xC00F)."""

    # UART Registers
    thr_rbr: int = 0  # 0xC000/0xC001 - TX/RX data
    ier: int = 0      # 0xC002 - Interrupt Enable
    fcr_iir: int = 0  # 0xC004 - FIFO Control/Interrupt ID
    tfbf: int = 0     # 0xC006 - TX FIFO status
    lcr: int = 0      # 0xC007 - Line Control
    mcr: int = 0      # 0xC008 - Modem Control
    lsr: int = 0x60   # 0xC009 - Line Status (TX empty + TX holding empty)
    msr: int = 0      # 0xC00A - Modem Status
    status: int = 0   # 0xC00E - UART status

    # TX/RX buffers
    tx_buffer: list = field(default_factory=list)
    rx_buffer: list = field(default_factory=list)

    # Callbacks
    on_tx: Optional[Callable[[int], None]] = None

    def read(self, addr: int) -> int:
        """Read UART register."""
        offset = addr - 0xC000
        if offset in (0, 1):  # RBR
            if self.rx_buffer:
                return self.rx_buffer.pop(0)
            return 0
        elif offset == 2:
            return self.ier
        elif offset == 4:  # IIR
            return self.fcr_iir | 0x01  # No interrupt pending
        elif offset == 6:
            return self.tfbf
        elif offset == 7:
            return self.lcr
        elif offset == 8:
            return self.mcr
        elif offset == 9:
            # LSR: bit 0 = data ready, bit 5 = TX holding empty, bit 6 = TX empty
            lsr = 0x60  # TX ready
            if self.rx_buffer:
                lsr |= 0x01  # Data ready
            return lsr
        elif offset == 0xA:
            return self.msr
        elif offset == 0xE:
            return self.status
        return 0

    def write(self, addr: int, value: int):
        """Write UART register."""
        offset = addr - 0xC000
        if offset in (0, 1):  # THR
            self.tx_buffer.append(value)
            if self.on_tx:
                self.on_tx(value)
            # Echo to stdout for debugging
            print(chr(value), end='', flush=True)
        elif offset == 2:
            self.ier = value
        elif offset == 4:  # FCR
            self.fcr_iir = value
        elif offset == 6:
            self.tfbf = value
        elif offset == 7:
            self.lcr = value
        elif offset == 8:
            self.mcr = value
        elif offset == 0xE:
            self.status = value

    def inject_rx(self, data: bytes):
        """Inject data into RX buffer (for testing)."""
        self.rx_buffer.extend(data)


@dataclass
class Timer:
    """Timer Controller Emulation (0xCC10-0xCC24)."""

    # Timer 0 (0xCC10-0xCC15)
    timer0_div: int = 0
    timer0_csr: int = 0
    timer0_threshold: int = 0
    timer0_count: int = 0

    # Timer 1 (0xCC16-0xCC1B)
    timer1_div: int = 0
    timer1_csr: int = 0
    timer1_threshold: int = 0
    timer1_count: int = 0

    # Timer 2 (0xCC1C-0xCC21)
    timer2_div: int = 0
    timer2_csr: int = 0
    timer2_threshold: int = 0
    timer2_count: int = 0

    # Timer 3 (0xCC22-0xCC27)
    timer3_div: int = 0
    timer3_csr: int = 0
    timer3_idle_timeout: int = 0

    def read(self, addr: int) -> int:
        """Read timer register."""
        if addr == 0xCC10:
            return self.timer0_div
        elif addr == 0xCC11:
            return self.timer0_csr
        elif addr == 0xCC12:
            return (self.timer0_threshold >> 8) & 0xFF
        elif addr == 0xCC13:
            return self.timer0_threshold & 0xFF
        elif addr == 0xCC16:
            return self.timer1_div
        elif addr == 0xCC17:
            return self.timer1_csr
        elif addr == 0xCC1C:
            return self.timer2_div
        elif addr == 0xCC1D:
            return self.timer2_csr
        elif addr == 0xCC22:
            return self.timer3_div
        elif addr == 0xCC23:
            return self.timer3_csr
        elif addr == 0xCC24:
            return self.timer3_idle_timeout
        return 0

    def write(self, addr: int, value: int):
        """Write timer register."""
        if addr == 0xCC10:
            self.timer0_div = value
        elif addr == 0xCC11:
            self.timer0_csr = value
            if value & 0x04:  # Clear flag
                self.timer0_csr &= ~0x02  # Clear expired
        elif addr == 0xCC12:
            self.timer0_threshold = (value << 8) | (self.timer0_threshold & 0xFF)
        elif addr == 0xCC13:
            self.timer0_threshold = (self.timer0_threshold & 0xFF00) | value
        elif addr == 0xCC16:
            self.timer1_div = value
        elif addr == 0xCC17:
            self.timer1_csr = value
        elif addr == 0xCC1C:
            self.timer2_div = value
        elif addr == 0xCC1D:
            self.timer2_csr = value
        elif addr == 0xCC22:
            self.timer3_div = value
        elif addr == 0xCC23:
            self.timer3_csr = value
        elif addr == 0xCC24:
            self.timer3_idle_timeout = value

    def tick(self, cycles: int):
        """Advance timers by given cycles."""
        # Timer 0
        if self.timer0_csr & 0x01:  # Enabled
            self.timer0_count += cycles
            if self.timer0_count >= self.timer0_threshold and self.timer0_threshold > 0:
                self.timer0_csr |= 0x02  # Set expired flag
                self.timer0_count = 0


@dataclass
class InterruptController:
    """Interrupt Controller Emulation (0xC800-0xC80F)."""

    status_c800: int = 0
    enable: int = 0       # 0xC801
    usb_status: int = 0   # 0xC802
    aux_status: int = 0   # 0xC805
    system: int = 0       # 0xC806
    ctrl: int = 0         # 0xC809
    pcie_nvme: int = 0    # 0xC80A

    def read(self, addr: int) -> int:
        if addr == 0xC800:
            return self.status_c800
        elif addr == 0xC801:
            return self.enable
        elif addr == 0xC802:
            return self.usb_status
        elif addr == 0xC805:
            return self.aux_status
        elif addr == 0xC806:
            return self.system
        elif addr == 0xC809:
            return self.ctrl
        elif addr == 0xC80A:
            return self.pcie_nvme
        return 0

    def write(self, addr: int, value: int):
        if addr == 0xC800:
            # Write to clear bits
            self.status_c800 &= ~value
        elif addr == 0xC801:
            self.enable = value
        elif addr == 0xC802:
            self.usb_status &= ~value
        elif addr == 0xC805:
            self.aux_status = value
        elif addr == 0xC806:
            self.system &= ~value
        elif addr == 0xC809:
            self.ctrl = value
        elif addr == 0xC80A:
            self.pcie_nvme &= ~value


@dataclass
class USBController:
    """USB Controller Emulation (0x9000-0x93FF)."""

    # Core registers
    status: int = 0x80      # 0x9000 - USB connected
    control: int = 0        # 0x9001
    config: int = 0         # 0x9002
    ep0_status: int = 0     # 0x9003
    ep0_len_l: int = 0      # 0x9004
    ep0_len_h: int = 0      # 0x9005
    ep0_config: int = 0     # 0x9006

    # Speed and mode
    speed: int = 0x02       # 0x90E0 - USB3 speed
    mode: int = 0           # 0x90E2

    # Link status
    link_status: int = 0    # 0x9100
    periph_status: int = 0  # 0x9101

    # CBW data for SCSI
    cbw_len_hi: int = 0
    cbw_len_lo: int = 0

    def read(self, addr: int) -> int:
        if addr == 0x9000:
            return self.status
        elif addr == 0x9001:
            return self.control
        elif addr == 0x9002:
            return self.config
        elif addr == 0x9003:
            return self.ep0_status
        elif addr == 0x90E0:
            return self.speed
        elif addr == 0x90E2:
            return self.mode
        elif addr == 0x9100:
            return self.link_status
        elif addr == 0x9101:
            return self.periph_status
        elif addr == 0x9105:
            return 0xFF  # PHY active
        return 0

    def write(self, addr: int, value: int):
        if addr == 0x9000:
            self.status = value
        elif addr == 0x9001:
            self.control = value
        elif addr == 0x9002:
            self.config = value
        elif addr == 0x9003:
            self.ep0_status = value
        elif addr == 0x90E0:
            self.speed = value
        elif addr == 0x90E2:
            self.mode = value


@dataclass
class FlashController:
    """SPI Flash Controller Emulation (0xC89F-0xC8AE)."""

    con: int = 0        # 0xC89F
    addr_lo: int = 0    # 0xC8A1
    addr_md: int = 0    # 0xC8A2
    data_len: int = 0   # 0xC8A3
    data_len_hi: int = 0 # 0xC8A4
    div: int = 0        # 0xC8A6
    csr: int = 0        # 0xC8A9 - bit 0 = busy
    cmd: int = 0        # 0xC8AA
    addr_hi: int = 0    # 0xC8AB
    addr_len: int = 0   # 0xC8AC
    mode: int = 0       # 0xC8AD

    # Flash data (simulated 1MB)
    flash_data: bytearray = field(default_factory=lambda: bytearray(0x100000))

    def read(self, addr: int) -> int:
        if addr == 0xC89F:
            return self.con
        elif addr == 0xC8A1:
            return self.addr_lo
        elif addr == 0xC8A2:
            return self.addr_md
        elif addr == 0xC8A3:
            return self.data_len
        elif addr == 0xC8A4:
            return self.data_len_hi
        elif addr == 0xC8A6:
            return self.div
        elif addr == 0xC8A9:
            return self.csr  # Not busy
        elif addr == 0xC8AA:
            return self.cmd
        elif addr == 0xC8AB:
            return self.addr_hi
        elif addr == 0xC8AC:
            return self.addr_len
        elif addr == 0xC8AD:
            return self.mode
        return 0

    def write(self, addr: int, value: int):
        if addr == 0xC89F:
            self.con = value
        elif addr == 0xC8A1:
            self.addr_lo = value
        elif addr == 0xC8A2:
            self.addr_md = value
        elif addr == 0xC8A3:
            self.data_len = value
        elif addr == 0xC8A4:
            self.data_len_hi = value
        elif addr == 0xC8A6:
            self.div = value
        elif addr == 0xC8A9:
            self.csr = value
        elif addr == 0xC8AA:
            self.cmd = value
            # Execute flash command
            self._execute_cmd()
        elif addr == 0xC8AB:
            self.addr_hi = value
        elif addr == 0xC8AC:
            self.addr_len = value
        elif addr == 0xC8AD:
            self.mode = value

    def _execute_cmd(self):
        """Execute flash command (stub)."""
        # Just clear busy flag immediately
        self.csr &= ~0x01


@dataclass
class DMAController:
    """DMA Controller Emulation (0xC8B0-0xC8D9)."""

    mode: int = 0           # 0xC8B0
    chan_aux: int = 0       # 0xC8B2
    chan_aux1: int = 0      # 0xC8B3
    xfer_cnt_hi: int = 0    # 0xC8B4
    xfer_cnt_lo: int = 0    # 0xC8B5
    chan_ctrl2: int = 0     # 0xC8B6
    chan_status2: int = 0   # 0xC8B7
    trigger: int = 0        # 0xC8B8
    config: int = 0         # 0xC8D4
    queue_idx: int = 0      # 0xC8D5
    status: int = 0x04      # 0xC8D6 - DMA done
    ctrl: int = 0           # 0xC8D7
    status2: int = 0        # 0xC8D8
    status3: int = 0        # 0xC8D9

    def read(self, addr: int) -> int:
        if addr == 0xC8B0:
            return self.mode
        elif addr == 0xC8B2:
            return self.chan_aux
        elif addr == 0xC8B3:
            return self.chan_aux1
        elif addr == 0xC8B4:
            return self.xfer_cnt_hi
        elif addr == 0xC8B5:
            return self.xfer_cnt_lo
        elif addr == 0xC8B6:
            return self.chan_ctrl2
        elif addr == 0xC8B7:
            return self.chan_status2
        elif addr == 0xC8B8:
            return self.trigger
        elif addr == 0xC8D4:
            return self.config
        elif addr == 0xC8D5:
            return self.queue_idx
        elif addr == 0xC8D6:
            return self.status
        elif addr == 0xC8D7:
            return self.ctrl
        elif addr == 0xC8D8:
            return self.status2
        elif addr == 0xC8D9:
            return self.status3
        return 0

    def write(self, addr: int, value: int):
        if addr == 0xC8B0:
            self.mode = value
        elif addr == 0xC8B2:
            self.chan_aux = value
        elif addr == 0xC8B3:
            self.chan_aux1 = value
        elif addr == 0xC8B4:
            self.xfer_cnt_hi = value
        elif addr == 0xC8B5:
            self.xfer_cnt_lo = value
        elif addr == 0xC8B6:
            self.chan_ctrl2 = value
        elif addr == 0xC8B7:
            self.chan_status2 = value
        elif addr == 0xC8B8:
            self.trigger = value
        elif addr == 0xC8D4:
            self.config = value
        elif addr == 0xC8D5:
            self.queue_idx = value
        elif addr == 0xC8D6:
            self.status = value
        elif addr == 0xC8D7:
            self.ctrl = value
        elif addr == 0xC8D8:
            self.status2 = value
        elif addr == 0xC8D9:
            self.status3 = value


@dataclass
class NVMeController:
    """NVMe Controller Emulation (0xC400-0xC5FF)."""

    ctrl: int = 0           # 0xC400
    status: int = 0         # 0xC401
    ctrl_status: int = 0x02 # 0xC412 - NVMe ready
    config: int = 0         # 0xC413
    data_ctrl: int = 0      # 0xC414
    dev_status: int = 0     # 0xC415
    link_status: int = 0x80 # 0xC520 - Link ready

    def read(self, addr: int) -> int:
        if addr == 0xC400:
            return self.ctrl
        elif addr == 0xC401:
            return self.status
        elif addr == 0xC412:
            return self.ctrl_status
        elif addr == 0xC413:
            return self.config
        elif addr == 0xC414:
            return self.data_ctrl
        elif addr == 0xC415:
            return self.dev_status
        elif addr == 0xC520:
            return self.link_status
        return 0

    def write(self, addr: int, value: int):
        if addr == 0xC400:
            self.ctrl = value
        elif addr == 0xC401:
            self.status = value
        elif addr == 0xC412:
            self.ctrl_status = value
        elif addr == 0xC413:
            self.config = value
        elif addr == 0xC414:
            self.data_ctrl = value
        elif addr == 0xC415:
            self.dev_status = value
        elif addr == 0xC520:
            self.link_status = value


@dataclass
class PCIeController:
    """PCIe/Thunderbolt Controller Emulation (0xB200-0xB8FF)."""

    fmt_type: int = 0       # 0xB210
    tlp_ctrl: int = 0       # 0xB213
    tlp_length: int = 0     # 0xB216
    byte_en: int = 0        # 0xB217
    addr: bytearray = field(default_factory=lambda: bytearray(8))  # 0xB218-0xB21F
    data: bytearray = field(default_factory=lambda: bytearray(4))  # 0xB220-0xB223
    trigger: int = 0        # 0xB254
    status: int = 0x02      # 0xB296 - Complete
    tunnel_cfg: int = 0     # 0xB298

    def read(self, addr: int) -> int:
        if addr == 0xB210:
            return self.fmt_type
        elif addr == 0xB213:
            return self.tlp_ctrl
        elif addr == 0xB216:
            return self.tlp_length
        elif addr == 0xB217:
            return self.byte_en
        elif 0xB218 <= addr <= 0xB21F:
            return self.addr[addr - 0xB218]
        elif 0xB220 <= addr <= 0xB223:
            return self.data[addr - 0xB220]
        elif addr == 0xB254:
            return self.trigger
        elif addr == 0xB296:
            return self.status
        elif addr == 0xB298:
            return self.tunnel_cfg
        return 0

    def write(self, addr: int, value: int):
        if addr == 0xB210:
            self.fmt_type = value
        elif addr == 0xB213:
            self.tlp_ctrl = value
        elif addr == 0xB216:
            self.tlp_length = value
        elif addr == 0xB217:
            self.byte_en = value
        elif 0xB218 <= addr <= 0xB21F:
            self.addr[addr - 0xB218] = value
        elif 0xB220 <= addr <= 0xB223:
            self.data[addr - 0xB220] = value
        elif addr == 0xB254:
            self.trigger = value
            # Simulate instant completion
            self.status = 0x02
        elif addr == 0xB296:
            # Write to clear
            self.status &= ~value
        elif addr == 0xB298:
            self.tunnel_cfg = value


@dataclass
class CPUControl:
    """CPU/System Control Emulation (0xCC30-0xCCFF, 0xCA00-0xCAFF)."""

    mode: int = 0           # 0xCC30
    exec_ctrl: int = 0      # 0xCC31
    exec_status: int = 0    # 0xCC32
    exec_status_2: int = 0  # 0xCC33
    mode_next: int = 0      # 0xCA06
    ctrl_ca81: int = 0      # 0xCA81

    def read(self, addr: int) -> int:
        if addr == 0xCC30:
            return self.mode
        elif addr == 0xCC31:
            return self.exec_ctrl
        elif addr == 0xCC32:
            return self.exec_status
        elif addr == 0xCC33:
            return self.exec_status_2
        elif addr == 0xCA06:
            return self.mode_next
        elif addr == 0xCA81:
            return self.ctrl_ca81
        return 0

    def write(self, addr: int, value: int):
        if addr == 0xCC30:
            self.mode = value
        elif addr == 0xCC31:
            self.exec_ctrl = value
        elif addr == 0xCC32:
            self.exec_status = value
        elif addr == 0xCC33:
            self.exec_status_2 = value
        elif addr == 0xCA06:
            self.mode_next = value
        elif addr == 0xCA81:
            self.ctrl_ca81 = value


@dataclass
class PowerController:
    """Power Management Emulation (0x92C0-0x92E0)."""

    enable: int = 0x81      # 0x92C0 - Power on
    clock_enable: int = 0x03 # 0x92C1 - Clocks on
    status: int = 0         # 0x92C2
    misc_ctrl: int = 0      # 0x92C4
    phy_power: int = 0x04   # 0x92C5 - PHY powered
    domain: int = 0x02      # 0x92E0

    def read(self, addr: int) -> int:
        if addr == 0x92C0:
            return self.enable
        elif addr == 0x92C1:
            return self.clock_enable
        elif addr == 0x92C2:
            return self.status
        elif addr == 0x92C4:
            return self.misc_ctrl
        elif addr == 0x92C5:
            return self.phy_power
        elif addr == 0x92E0:
            return self.domain
        return 0

    def write(self, addr: int, value: int):
        if addr == 0x92C0:
            self.enable = value
        elif addr == 0x92C1:
            self.clock_enable = value
        elif addr == 0x92C2:
            self.status = value
        elif addr == 0x92C4:
            self.misc_ctrl = value
        elif addr == 0x92C5:
            self.phy_power = value
        elif addr == 0x92E0:
            self.domain = value


@dataclass
class Peripherals:
    """Container for all peripheral emulators."""

    uart: UART = field(default_factory=UART)
    timer: Timer = field(default_factory=Timer)
    interrupt: InterruptController = field(default_factory=InterruptController)
    usb: USBController = field(default_factory=USBController)
    flash: FlashController = field(default_factory=FlashController)
    dma: DMAController = field(default_factory=DMAController)
    nvme: NVMeController = field(default_factory=NVMeController)
    pcie: PCIeController = field(default_factory=PCIeController)
    cpu_ctrl: CPUControl = field(default_factory=CPUControl)
    power: PowerController = field(default_factory=PowerController)

    def register_hooks(self, memory: "Memory"):
        """Register all peripheral MMIO hooks with memory system."""

        # UART (0xC000-0xC00F)
        for addr in range(0xC000, 0xC010):
            memory.add_xdata_hook(addr, self.uart.read, self.uart.write)

        # Timer (0xCC10-0xCC27)
        for addr in range(0xCC10, 0xCC28):
            memory.add_xdata_hook(addr, self.timer.read, self.timer.write)

        # Interrupt Controller (0xC800-0xC80F)
        for addr in range(0xC800, 0xC810):
            memory.add_xdata_hook(addr, self.interrupt.read, self.interrupt.write)

        # USB Controller (0x9000-0x93FF)
        for addr in range(0x9000, 0x9400):
            memory.add_xdata_hook(addr, self.usb.read, self.usb.write)

        # Flash Controller (0xC89F-0xC8AF)
        for addr in range(0xC89F, 0xC8B0):
            memory.add_xdata_hook(addr, self.flash.read, self.flash.write)

        # DMA Controller (0xC8B0-0xC8DA)
        for addr in range(0xC8B0, 0xC8DA):
            memory.add_xdata_hook(addr, self.dma.read, self.dma.write)

        # NVMe Controller (0xC400-0xC600)
        for addr in range(0xC400, 0xC600):
            memory.add_xdata_hook(addr, self.nvme.read, self.nvme.write)

        # PCIe Controller (0xB200-0xB300)
        for addr in range(0xB200, 0xB300):
            memory.add_xdata_hook(addr, self.pcie.read, self.pcie.write)

        # CPU Control (0xCA00-0xCB00, 0xCC30-0xCD00)
        for addr in range(0xCA00, 0xCB00):
            memory.add_xdata_hook(addr, self.cpu_ctrl.read, self.cpu_ctrl.write)
        for addr in range(0xCC30, 0xCD00):
            memory.add_xdata_hook(addr, self.cpu_ctrl.read, self.cpu_ctrl.write)

        # Power Controller (0x92C0-0x92F0)
        for addr in range(0x92C0, 0x92F0):
            memory.add_xdata_hook(addr, self.power.read, self.power.write)

    def tick(self, cycles: int):
        """Advance all peripherals by given cycles."""
        self.timer.tick(cycles)
