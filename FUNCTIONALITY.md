# ASM2464PD USB4 eGPU Firmware

## Overview

The ASM2464PD is a USB4/Thunderbolt to PCIe bridge. It translates USB Mass Storage (SCSI) commands into NVMe transactions, enabling external SSDs and eGPUs over Thunderbolt.

```
┌─────────────┐     ┌─────────────────────────────┐     ┌─────────────┐
│  USB Host   │────>│       ASM2464PD             │────>│  NVMe SSD   │
│  (SCSI/UAS) │<────│  8051 CPU @ 114MHz          │<────│  or eGPU    │
└─────────────┘     └─────────────────────────────┘     └─────────────┘
                      │                         │
                      │  USB 3.2 Gen2x2         │  PCIe Gen4 x4
                      │  (20 Gbps)              │  (64 Gbps)
```

## Hardware Components

| Component | Registers | Purpose |
|-----------|-----------|---------|
| USB Controller | 0x9000-0x93FF | USB endpoints, CBW/CSW handling |
| PCIe Interface | 0xB200-0xB4FF | TLP transactions, config space |
| NVMe Controller | 0xC400-0xC5FF | SQ/CQ management, doorbells |
| DMA Engine | 0xC8B0-0xC8DF | Data movement USB<->PCIe |
| PHY/Link | 0xC200-0xC6FF | Signal conditioning, link training |
| Timer | 0xCC10-0xCC24 | Timeouts, delays |
| Flash | 0xC89F-0xC8AE | Firmware storage |

## Memory Map

```
XDATA Address Space:
0x0000-0x5FFF  24KB XRAM (globals, work areas)
0x6000-0x6FFF  Reserved
0x7000-0x7FFF  Flash buffer
0x8000-0x8FFF  USB/SCSI buffer (CBW parsing)
0x9000-0x9FFF  USB registers
0xA000-0xAFFF  NVMe I/O Submission Queue
0xB000-0xB1FF  NVMe Admin Queues (ASQ/ACQ)
0xB200-0xBFFF  PCIe registers
0xC000-0xCFFF  Peripheral registers
0xD800-0xDFFF  USB endpoint buffers (CSW)
0xE000-0xEFFF  Debug/status registers
0xF000-0xFFFF  NVMe data buffer
```

## Initialization Flow

```
main()
  ├─> uart_init()                    // Debug @ 921600 baud
  ├─> process_init_table()           // Hardware config from table
  ├─> usb_power_init()               // Power domains
  │     ├─ REG_POWER_ENABLE = 0x81
  │     ├─ REG_CLOCK_ENABLE = 0x03
  │     └─ REG_PHY_POWER = 0x04
  ├─> phy_init_sequence()            // PHY power up
  │     ├─ Clear USB PHY (0x920C)
  │     ├─ Enable PHY (0x92C5)
  │     └─ Poll ready (0xC6B3)
  ├─> phy_config_link_params()       // Lane config
  │     ├─ Set lanes (0xC62D = 0x07)
  │     └─ Extended PHY (0xC65B)
  └─> main_loop()                    // Service USB/PCIe/NVMe
```

## PCIe Tunnel Setup (USB4/Thunderbolt)

```
pcie_tunnel_enable (0xC00D)
  ├─> pcie_tunnel_setup (0xCD6C)
  │     └─> pcie_adapter_config (0xC8DB)
  │           ├─ Load config from 0x0A52-0x0A55
  │           └─ Write to REG_TUNNEL_* (0xB410-0xB41B)
  └─> pcie_lane_config (0xD436)
        └─> pcie_lane_config_helper (0xC089)
              ├─> phy_link_training (0xD702)
              │     └─ Configure PHY lanes 0-3 via bank 2
              └─> timer_wait (0xE80A)
                    └─ ~200ms delay for link training
```

### Tunnel Registers

| Register | Address | Purpose |
|----------|---------|---------|
| REG_TUNNEL_CFG_A_LO | 0xB410 | Link config low |
| REG_TUNNEL_CFG_A_HI | 0xB411 | Link config high |
| REG_TUNNEL_CREDITS | 0xB412 | Path credits |
| REG_TUNNEL_CFG_MODE | 0xB413 | Tunnel mode |
| REG_TUNNEL_LINK_STATE | 0xB430 | Bit 0: link up |
| REG_TUNNEL_ADAPTER_MODE | 0xB482 | 0xF0 when enabled |

## Packet Flow

### USB to NVMe (Write Path)

```
USB Host                    ASM2464PD                     NVMe SSD
   │                            │                            │
   │──── CBW (SCSI WRITE) ─────>│                            │
   │     sig=USBC               │                            │
   │     tag=0x1234             │                            │
   │     len=4096               │                            │
   │     cmd=0x2A (WRITE10)     │                            │
   │     LBA=0x100              │                            │
   │                            │                            │
   │──── Data (4096 bytes) ────>│                            │
   │                            │                            │
   │                            │─── NVMe Write CMD ────────>│
   │                            │    opcode=0x02             │
   │                            │    nsid=1                  │
   │                            │    slba=0x100              │
   │                            │    nlb=7 (8 blocks-1)      │
   │                            │                            │
   │                            │<── NVMe Completion ────────│
   │                            │    status=0x00             │
   │                            │                            │
   │<─── CSW (Success) ─────────│                            │
   │     sig=USBS               │                            │
   │     tag=0x1234             │                            │
   │     residue=0              │                            │
   │     status=0x00            │                            │
```

### NVMe to USB (Read Path)

```
USB Host                    ASM2464PD                     NVMe SSD
   │                            │                            │
   │──── CBW (SCSI READ) ──────>│                            │
   │     cmd=0x28 (READ10)      │                            │
   │     LBA=0x100              │                            │
   │                            │                            │
   │                            │─── NVMe Read CMD ─────────>│
   │                            │    opcode=0x01             │
   │                            │                            │
   │                            │<── NVMe Completion ────────│
   │                            │<── Data (via DMA) ─────────│
   │                            │                            │
   │<─── Data (4096 bytes) ─────│                            │
   │<─── CSW (Success) ─────────│                            │
```

## Data Structures

### USB CBW (Command Block Wrapper)

```c
// At 0x8000
struct usb_cbw {
    uint32_t signature;      // 0x43425355 ('USBC')
    uint32_t tag;            // Transaction ID
    uint32_t transfer_len;   // Bytes to transfer
    uint8_t flags;           // Bit 7: direction (1=in)
    uint8_t lun;             // Bits 0-3: LUN
    uint8_t cb_length;       // Command length
    uint8_t command[16];     // SCSI CDB
};
```

### USB CSW (Command Status Wrapper)

```c
// At 0xD800
struct usb_csw {
    uint32_t signature;      // 0x53425355 ('USBS')
    uint32_t tag;            // Echo from CBW
    uint32_t residue;        // Bytes not transferred
    uint8_t status;          // 0=pass, 1=fail, 2=phase error
};
```

### NVMe Submission Queue Entry

```c
// At 0xA000 (DMA: 0x00820000)
struct nvme_sqe {
    uint8_t opcode;          // 0x01=read, 0x02=write
    uint8_t flags;
    uint16_t cid;            // Command ID
    uint32_t nsid;           // Namespace (1)
    uint64_t reserved;
    uint64_t mptr;
    uint64_t prp1, prp2;     // Physical region pages
    uint64_t slba;           // Starting LBA
    uint32_t nlb;            // Block count - 1
    uint32_t control;
};
```

### NVMe Completion Queue Entry

```c
// At 0xB100 (DMA: 0x00800000)
struct nvme_cqe {
    uint32_t result;
    uint32_t reserved;
    uint16_t sq_head;
    uint16_t sq_id;
    uint16_t cid;
    uint16_t status;         // Bit 0: phase, Bits 9-17: status
};
```

## SCSI Command Dispatch

```c
scsi_dispatch_command() {
  switch (G_SCSI_CMD_TYPE) {
    case 0x12: return scsi_inquiry();
    case 0x25: return scsi_read_capacity();
    case 0x28: return nvme_read();   // SCSI READ(10)
    case 0x2A: return nvme_write();  // SCSI WRITE(10)
    case 0x2F: return scsi_verify();
  }
}
```

## DMA Transfer

```c
dma_start_transfer() {
    REG_DMA_MODE = mode;
    REG_DMA_CHAN_AUX = buffer_hi;
    REG_DMA_CHAN_AUX+1 = buffer_lo;
    REG_DMA_XFER_CNT = size;

    // Direction: bit 1 of CTRL2
    // 0 = read (NVMe->USB), 1 = write (USB->NVMe)
    REG_DMA_CHAN_CTRL2 = direction ? 0x02 : 0x00;

    REG_DMA_TRIGGER = 0x01;
    while (REG_DMA_TRIGGER & 0x01);  // Poll done
}
```

## Main Loop

```c
while (1) {
    // 1. Check USB endpoints
    status = REG_USB_EP_STATUS;
    if (status) {
        ep = dispatch_table[status];
        scsi_dispatch_command();
    }

    // 2. Check NVMe completions
    if (nvme_check_cq()) {
        usb_send_csw();
    }

    // 3. Handle PCIe events
    if (REG_INT_PCIE_NVME & 0x20) {
        pcie_handle_link_event();
    }

    // 4. Timer events
    if (REG_INT_SYSTEM & 0x10) {
        system_timer_handler();
    }
}
```

## Key Registers

### USB

| Register | Address | Purpose |
|----------|---------|---------|
| REG_USB_STATUS | 0x9000 | Main status |
| REG_USB_EP_STATUS | 0x9118 | Endpoint bitmap |
| REG_USB_CBW_FLAGS | 0x9127 | CBW flags |
| REG_USB_SPEED | 0x90E0 | USB speed mode |

### PCIe TLP

| Register | Address | Purpose |
|----------|---------|---------|
| REG_PCIE_FMT_TYPE | 0xB210 | TLP type (read/write/cfg) |
| REG_PCIE_ADDR | 0xB218-B21B | 32-bit address |
| REG_PCIE_DATA | 0xB220 | TLP data |
| REG_PCIE_TRIGGER | 0xB254 | Send TLP (write 0x0F) |
| REG_PCIE_STATUS | 0xB296 | Completion status |

### NVMe

| Register | Address | Purpose |
|----------|---------|---------|
| REG_NVME_CTRL | 0xC400 | Controller enable |
| REG_NVME_CMD_OPCODE | 0xC421 | Command opcode |
| REG_NVME_LBA | 0xC422-C424 | LBA address |
| REG_NVME_DOORBELL | 0xC42A | SQ doorbell |

### DMA

| Register | Address | Purpose |
|----------|---------|---------|
| REG_DMA_MODE | 0xC8B0 | Transfer mode |
| REG_DMA_CHAN_AUX | 0xC8B2-3 | Buffer address |
| REG_DMA_XFER_CNT | 0xC8B4-5 | Transfer size |
| REG_DMA_TRIGGER | 0xC8B8 | Start/poll |
| REG_DMA_STATUS | 0xC8D6 | Done/error |

## Implementation Status

```
scsi_transfer_dispatch (0x466B)     [DONE]
  └─> pcie_tunnel_enable (0xC00D)   [DONE]
        ├─> pcie_tunnel_setup (0xCD6C)      [DONE]
        │     └─> pcie_adapter_config (0xC8DB)  [DONE]
        └─> pcie_lane_config (0xD436)       [DONE]
              └─> pcie_lane_config_helper (0xC089)  [DONE]
                    ├─> phy_link_training (0xD702)  [DONE]
                    └─> timer_wait (0xE80A)         [DONE]
```

## Build

```
35,670 / 98,012 bytes (36.3%)
```
