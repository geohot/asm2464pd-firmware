# ASM2464PD Application Tools

Tools for interacting with the ASM2464PD USB-to-PCIe bridge chip.

## scan_pcie.py

Scans for PCIe devices connected via the ASM2464PD USB enclosure.

### Usage

```bash
# Quick scan (finds bridges but not downstream GPU functions)
sudo PYTHONPATH=~/tinygrad python app/scan_pcie.py

# Deep scan - configures all bridges to find GPU at bus 4
sudo PYTHONPATH=~/tinygrad python app/scan_pcie.py --deep

# Verbose mode with config space dumps
sudo PYTHONPATH=~/tinygrad python app/scan_pcie.py --deep --verbose

# Scan specific bus
sudo PYTHONPATH=~/tinygrad python app/scan_pcie.py --bus 4
```

### Example Output (with AMD RX 7900 XTX)

```
Bus 00: 32x ASM2461 PCIe Switch Ports
Bus 01: 1x ASM2461 downstream port  
Bus 02: AMD Navi 31 Upstream Port [1002:1478]
Bus 03: AMD Navi 31 Downstream Port [1002:1479]
Bus 04:
  04:00.0: AMD Navi 31 (RX 7900 XTX) [1002:744C] - Display Controller
  04:00.1: AMD Navi 31 HDMI Audio [1002:AB30] - Multimedia Controller
```

## Memory Architecture

The ASM2464PD has several memory regions accessible via different paths:

### 1. Internal SRAM (6-8 MB)

Large internal buffer used for USB bulk transfers and NVMe data.

**NOT directly accessible via PCIe TLP** - only the firmware can access it via DMA engines.

| PCI Address    | Size   | Purpose                    |
|---------------|--------|----------------------------|
| 0x00200000    | ~6 MB  | USB/SCSI data buffer       |
| 0x00820000    | 128 KB | NVMe queue region          |

The 8051 CPU sees this through 4KB windows:
- `0x8000-0x8FFF`: USB/SCSI buffer window
- `0xF000-0xFFFF`: NVMe data buffer window

### 2. XDATA (E4/E5 Vendor Commands)

Firmware XDATA memory accessible via USB vendor commands:
- **E4**: Read from XDATA address (up to 255 bytes)
- **E5**: Write to XDATA address (1 byte at a time)

```python
from tinygrad.runtime.support.usb import ASM24Controller
usb = ASM24Controller()

# Read 16 bytes from XDATA 0x8000
data = usb.read(0x8000, 16)

# Write bytes to XDATA 0xF000
usb.write(0xF000, b'\xDE\xAD\xBE\xEF')
```

### 3. SCSI Bulk DMA Path (Fast)

High-speed path for bulk data transfers to internal SRAM:

```python
# Write up to 64KB at a time via SCSI bulk transfer
usb.scsi_write(data, lba=0)  # Data lands at 0xF000 window
```

This is the fast path used by tinygrad for GPU memory transfers:
- USB3 bulk packets (1024 bytes each)
- Hardware DMA to internal SRAM
- No CPU involvement for data bytes

### 4. PCIe Memory (TLP Requests)

Direct PCIe memory read/write via TLP (Transaction Layer Packets):

```python
# Read 4 bytes from PCIe memory address
val = usb.pcie_mem_req(address, value=None, size=4)

# Write 4 bytes to PCIe memory address  
usb.pcie_mem_req(address, value=0xDEADBEEF, size=4)

# Batch writes for better performance
usb.pcie_mem_write(address, [val1, val2, val3, ...], size=4)
```

**Note**: PCIe memory requests go to EXTERNAL devices (GPU, NVMe), not internal SRAM.

## DMA Transfer Flow

### USB Host to GPU Memory

```
1. Host sends data via USB bulk transfer
2. ASM2464 firmware DMAs to internal SRAM (0x00200000+)
3. Data visible at XDATA 0xF000 window
4. Firmware can issue PCIe TLP to copy SRAM to GPU BAR

Or using tinygrad's copy_bufs mechanism:
1. scsi_write() to 0xF000 (lands in SRAM at ctrl_addr)
2. GPU reads from mapped sys_addr via PCIe
```

### GPU Memory to USB Host

```
1. GPU writes to mapped memory region
2. Firmware reads via PCIe TLP or DMA
3. Data copied to SRAM
4. USB bulk IN transfer to host
```

## Key Registers

### PCIe TLP Engine (0xB2xx)

| Register | Purpose |
|----------|---------|
| 0xB210   | TLP format/type (0x20=mem read, 0x60=mem write) |
| 0xB217   | Byte enables |
| 0xB218   | Address bits 0-7 |
| 0xB219   | Address bits 8-15 |
| 0xB21A   | Address bits 16-23 |
| 0xB21B   | Address bits 24-31 |
| 0xB21C   | Address bits 32-39 (high) |
| 0xB220   | Data (read result / write value) |
| 0xB254   | Trigger (write 0x0F) |
| 0xB296   | Status (bit 1 = complete, bit 0 = error) |

### SCSI DMA Engine (0xCExx)

| Register | Purpose |
|----------|---------|
| 0xCE00   | DMA control (write 0x03 to start) |
| 0xCE75   | Transfer length |
| 0xCE76   | PCI address byte 0 (LSB) |
| 0xCE77   | PCI address byte 1 |
| 0xCE78   | PCI address byte 2 |
| 0xCE79   | PCI address byte 3 (MSB) |
| 0xCE89   | State machine (bit 0=ready, bit 1=success) |

## Requirements

- Python 3.10+
- tinygrad (for `ASM24Controller`)
- libusb
- Root access for USB device

```bash
# Install tinygrad
git clone https://github.com/tinygrad/tinygrad ~/tinygrad

# Run with correct path
sudo PYTHONPATH=~/tinygrad python app/scan_pcie.py
```
