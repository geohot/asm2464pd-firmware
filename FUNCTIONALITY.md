# ASM2464PD Functionality Overview

This document describes how the ASM2464PD USB4/NVMe bridge controller works and how its hardware blocks cooperate to bridge USB Mass Storage commands to NVMe storage.

## Device Purpose

The ASM2464PD is a bridge IC that allows NVMe SSDs to appear as USB Mass Storage devices. It translates between:

- **Host side**: USB 3.2/USB4/Thunderbolt using SCSI commands over USB Mass Storage (BOT protocol)
- **Storage side**: PCIe 4.0 x4 using NVMe commands

This enables NVMe drives to work with any USB host without requiring NVMe drivers.

## High-Level Data Flow

```
USB Host                                              NVMe SSD
   |                                                     |
   |  USB Bulk Transfer (CBW)                            |
   v                                                     |
[USB Interface] --> [SCSI Parser] --> [Command Engine]   |
       |                                    |            |
       |                                    v            |
       |                           [NVMe Translation]    |
       |                                    |            |
       |                                    v            |
       |                           [PCIe TLP Engine] --> |
       |                                    |            |
       |            <-- DMA Engine <--------|            |
       |                    |                            |
       v                    v                            |
[USB Bulk Transfer (Data/CSW)] <-------------------------|
```

## Hardware Block Interactions

### 1. USB Command Reception

When the host sends a SCSI command:

1. **USB Interface (0x9000)** receives USB bulk transfer
2. CBW (Command Block Wrapper) is parsed from **USB/SCSI Buffer (0x8000)**
3. CBW signature "USBC" validated at 0x911B-0x911E
4. Transfer length extracted from 0x9123-0x9126
5. Command data parsed from buffer

### 2. SCSI Command Processing

The **Command Engine (0xE400)** processes SCSI commands:

1. SCSI opcode examined (READ_10, WRITE_10, INQUIRY, etc.)
2. For storage commands, LBA and transfer count extracted
3. Command queued in **SCSI DMA Control (0xCE00)**
4. State machine in protocol.c tracks command progress

Key SCSI commands translated:
- READ_10/READ_16 → NVMe Read
- WRITE_10/WRITE_16 → NVMe Write
- INQUIRY → Return cached device info
- READ_CAPACITY → Return drive size
- TEST_UNIT_READY → Check NVMe status

### 3. NVMe Command Submission

For storage operations, SCSI commands become NVMe commands:

1. **NVMe Interface (0xC400)** constructs NVMe command
2. Command placed in **NVMe I/O Submission Queue (0xA000)**
3. Admin commands use **Admin Submission Queue (0xB000)**
4. Doorbell written via **REG_NVME_DOORBELL (0xC42A)**

NVMe command structure (64 bytes):
- Opcode, namespace ID, PRP pointers
- LBA, transfer count
- Command-specific fields

### 4. PCIe Transaction Layer

The **PCIe TLP Engine (0xB200)** generates PCIe packets:

1. Memory write TLP for submission queue entry
2. Doorbell write TLP to notify NVMe controller
3. Memory read TLP for completion queue polling
4. Data transfer TLPs for read/write payloads

Key registers:
- REG_PCIE_FMT_TYPE (0xB210): TLP format/type
- REG_PCIE_ADDR_0-3 (0xB218-0xB21B): Target address
- REG_PCIE_DATA (0xB220): Data payload

### 5. DMA Data Movement

The **DMA Engine (0xC8B0)** moves data between buffers:

```
USB Buffer (0x8000) <--> DMA <--> NVMe Data Buffer (0xF000)
                         |
                         v
                   PCIe to/from SSD
```

DMA operations:
1. Configure source/destination addresses
2. Set transfer length (REG_DMA_XFER_CNT)
3. Trigger transfer (REG_DMA_TRIGGER)
4. Poll for completion (REG_DMA_STATUS)

### 6. Completion Handling

When NVMe command completes:

1. **NVMe Completion Queue (0xB100)** receives completion entry
2. **Interrupt Controller (0xC800)** signals CPU
3. ISR reads completion status
4. Error codes translated to SCSI sense data
5. CSW (Command Status Wrapper) built in buffer
6. USB bulk transfer sends CSW to host

## Interrupt Flow

The 8051 handles interrupts for coordination:

```
INT0 (External 0): USB events
  └─> USB packet received/transmitted
  └─> Endpoint status changes

INT1 (External 1): PCIe/NVMe events
  └─> NVMe completion available
  └─> PCIe link status changes
  └─> DMA completion

Timer: Periodic tasks
  └─> Link monitoring
  └─> Timeout handling
  └─> Power management
```

## State Machines

### Protocol State Machine (G_IO_CMD_STATE at 0x0002)

Tracks overall command processing:
- 0x28: Starting new command
- 0x2A: Processing in progress
- 0x88: Data phase
- 0x8A: Status phase

### USB State Machine

Tracks USB connection:
- Disconnected
- Default (after reset)
- Addressed
- Configured
- Suspended

### NVMe State Machine

Tracks NVMe initialization and operation:
- Controller reset
- Admin queue setup
- I/O queue creation
- Normal operation
- Error recovery

## Buffer Architecture

```
┌─────────────────────────────────────────────────────────┐
│ XDATA Memory Map                                        │
├─────────────────────────────────────────────────────────┤
│ 0x0000-0x5FFF: RAM                                      │
│   ├─ Global variables                                   │
│   ├─ Stack                                              │
│   └─ Work areas                                         │
├─────────────────────────────────────────────────────────┤
│ 0x7000-0x7FFF: Flash Buffer (4KB)                       │
│   └─ Firmware updates, flash operations                 │
├─────────────────────────────────────────────────────────┤
│ 0x8000-0x8FFF: USB/SCSI Buffer (4KB)                    │
│   ├─ CBW reception                                      │
│   ├─ Data staging                                       │
│   └─ CSW transmission                                   │
├─────────────────────────────────────────────────────────┤
│ 0xA000-0xAFFF: NVMe I/O Submission Queue (4KB)          │
│   └─ Up to 64 queued I/O commands                       │
├─────────────────────────────────────────────────────────┤
│ 0xB000-0xB0FF: NVMe Admin Submission Queue              │
│ 0xB100-0xB1FF: NVMe Admin Completion Queue              │
│   └─ Controller management commands                     │
├─────────────────────────────────────────────────────────┤
│ 0xF000-0xFFFF: NVMe Data Buffer (4KB)                   │
│   └─ Read/write data staging to/from SSD               │
└─────────────────────────────────────────────────────────┘
```

## Initialization Sequence

1. **CPU startup**: Reset vector, stack setup
2. **Clock configuration**: PLL, clock dividers
3. **PHY initialization**: USB and PCIe PHYs
4. **USB setup**: Descriptors, endpoints
5. **PCIe link training**: Wait for link up
6. **NVMe initialization**:
   - Read controller capabilities
   - Create admin queues
   - Identify controller/namespace
   - Create I/O queues
7. **Ready for commands**: Main loop active

## Power Management

The **Power Management (0x92C0)** block handles:

- USB suspend/resume
- PCIe power states (L0, L1, L2)
- NVMe power states (PS0-PS4)
- Clock gating for idle blocks

Power transitions coordinated through:
- REG_POWER_ENABLE (0x92C0)
- REG_CLOCK_ENABLE (0x92C1)
- REG_POWER_STATUS (0x92C2)

## Error Handling

Errors at each layer are caught and translated:

| Source | Detection | Response |
|--------|-----------|----------|
| USB protocol | Invalid CBW signature | STALL endpoint, send CSW with error |
| SCSI command | Unsupported opcode | CHECK CONDITION sense data |
| NVMe error | Completion status != 0 | Map to SCSI sense code |
| PCIe timeout | No completion | Reset link, retry |
| DMA error | REG_DMA_STATUS bit 3 | Abort transfer |

## Code Bank Switching

With 98KB firmware in 64KB address space:

- Bank 0: 0x0000-0xFFFF direct access
- Bank 1: 0x10000-0x17FFF mapped at 0x8000

**Dispatch stubs** at 0x0300-0x0650 handle cross-bank calls:
1. Save current bank state
2. Switch DPX register
3. Call target function
4. Restore bank state
5. Return to caller

## Performance Path

For maximum throughput (USB to NVMe read):

1. USB bulk OUT → CBW in USB buffer
2. Parse CBW, extract LBA/count (fast path in protocol.c)
3. Build NVMe read command
4. Ring doorbell
5. DMA data from SSD → NVMe buffer → USB buffer
6. USB bulk IN → data to host
7. USB bulk IN → CSW to host

The DMA engine supports scatter-gather and can pipeline multiple commands for queue depth > 1.
