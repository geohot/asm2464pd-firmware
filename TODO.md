# ASM2464PD Firmware Reimplementation - TODO

## Overview

| Metric | Value |
|--------|-------|
| Original firmware size | 98,012 bytes |
| Current implementation | 13,825 bytes |
| Completion | ~14.1% |
| Functions in original | ~660 |
| Functions implemented | ~220 |

The original firmware is approximately **7x larger** than our current implementation.

---

## Major Subsystems

### 1. USB Protocol Stack (Partial)
The USB subsystem handles host communication, endpoint management, and data transfers.

**Implemented in `usb.c` (~29 functions):**
- `usb_enable` ✓, `usb_setup_endpoint` ✓
- `usb_ep_process` ✓, `usb_buffer_handler` ✓
- `usb_ep_config_bulk` ✓, `usb_ep_config_int` ✓
- `usb_set_transfer_flag` ✓, `usb_get_nvme_data_ctrl` ✓
- `usb_calc_queue_addr` ✓, `usb_calc_queue_addr_next` ✓
- `usb_set_done_flag` ✓, `usb_copy_status_to_buffer` ✓
- `usb_read_status_pair` ✓, `usb_read_transfer_params` ✓
- `usb_func_1bcb` ✓, `usb_func_1bde` ✓, `usb_func_1bf1` ✓
- `usb_clear_mode_bit` ✓, `usb_func_1c0b` ✓

**Remaining (~70 functions):**
- `usb_parse_descriptor` - Parse USB descriptors
- `usb_validate_descriptor` - Validate descriptor format
- `usb_endpoint_handler` - Main endpoint interrupt handler
- `usb_data_handler` - USB data stage handling
- Various USB helpers at 0x1A00-0x1E00

**Location in firmware:** 0x1A00-0x1E00, 0x5200-0x5500

### 2. NVMe Command Processing (Partial)
NVMe controller for SSD communication.

**Implemented in `nvme.c` (~33 functions):**
- `nvme_load_transfer_data` ✓, `nvme_calc_buffer_offset` ✓
- `nvme_subtract_idata_16` ✓, `nvme_inc_circular_counter` ✓
- `nvme_set_ep_queue_ctrl_84` ✓, `nvme_clear_status_bit1` ✓
- `nvme_add_to_global_053a` ✓, `nvme_set_data_ctrl_bit7` ✓
- `nvme_store_idata_16` ✓, `nvme_check_completion` ✓
- `nvme_set_usb_mode_bit` ✓, `nvme_get_config_offset` ✓
- `nvme_calc_idata_offset` ✓, `nvme_check_scsi_ctrl` ✓

**Remaining (~35 functions):**
- `nvme_submit_cmd` - Submit NVMe command
- `nvme_init_step` - Initialization step
- `nvme_process_cmd` - Process NVMe command
- `nvme_io_request` - I/O request handling
- `nvme_initialize` - Full initialization

**Location in firmware:** 0x1B00-0x1D00, 0x3200-0x3600

### 3. DMA Engine ✓ (Mostly Complete)
Direct Memory Access for high-speed data transfers.

**Implemented in `dma.c` (~24 functions):**
- `dma_config_channel` ✓ - Configure DMA channel (0x4A80)
- `dma_start_transfer` ✓ - Start DMA transfer (0x4AB0)
- `dma_setup_transfer` ✓ - Setup transfer parameters (0x5270)
- `dma_check_scsi_status` ✓ - Check SCSI status (0x5290)
- `dma_clear_status` ✓, `dma_load_transfer_params` ✓
- `dma_clear_state_counters` ✓, `dma_init_ep_queue` ✓
- `scsi_get_tag_count_status` ✓, `scsi_get_queue_status` ✓
- `dma_store_and_dispatch` ✓ - Store DMA parameters
- `transfer_calc_scsi_offset` ✓ (0x1602)
- `transfer_init_dma_params` ✓ (0x161A)
- `transfer_check_scsi_counter` ✓ (0x163A)
- `transfer_calc_ep_offset` ✓ (0x1646)
- `transfer_set_dptr_0464_offset` ✓ (0x165A)
- `transfer_calc_work43_offset` ✓ (0x1668)
- `transfer_calc_work53_offset` ✓ (0x1677)
- `transfer_get_ep_queue_addr` ✓ (0x1687)
- `transfer_calc_work55_offset` ✓ (0x1696)
- `transfer_write_idata41_to_ce6e` ✓ (0x16AE)

**Remaining (~5 functions):**
- `dma_transfer_handler` - Transfer completion handler (Bank 1 at 0xE941)

**Location in firmware:** 0x1600-0x1800, 0x4A00-0x4E00

### 4. PCIe/Thunderbolt Interface (Partial)
PCIe passthrough and Thunderbolt tunneling.

**Implemented in `pcie.c` (~26 functions):**
- `pcie_init` ✓, `pcie_init_alt` ✓
- `pcie_poll_and_read_completion` ✓, `pcie_get_completion_status` ✓
- `pcie_get_link_speed` ✓, `pcie_set_byte_enables` ✓
- `pcie_read_completion_data` ✓, `pcie_write_status_complete` ✓
- `pcie_set_idata_params` ✓, `pcie_clear_address_regs` ✓
- `pcie_inc_txn_counters` ✓, `pcie_wait_for_completion` ✓
- `pcie_event_handler` ✓ - Handler at 0xC105
- `pcie_error_handler` ✓ - Error recovery at 0xC00D

**Remaining (~15 functions):**
- Various dispatch stubs (0x0570-0x0650)

**Location in firmware:** 0xC100-0xC400, 0xED00-0xEF00

### 5. Flash/SPI Interface (Mostly Complete)
SPI flash for firmware storage and configuration.

**Implemented in `flash.c` (~16 functions):**
- `flash_add_to_xdata16` ✓, `flash_write_word` ✓
- `flash_write_idata_word` ✓, `flash_write_r1_xdata_word` ✓
- `flash_poll_busy` ✓, `flash_set_cmd` ✓
- `flash_set_addr_md` ✓, `flash_set_addr_hi` ✓
- `flash_set_data_len` ✓, `flash_set_mode_enable` ✓
- `flash_start_transaction` ✓, `flash_run_transaction` ✓
- `flash_wait_and_poll` ✓, `flash_read_status` ✓

**Remaining (~10 functions):**
- `flash_func_0adc` - Flash operation A
- `flash_func_0b15` - Flash operation B
- `flash_cmd_handler` - Command handler (0x0525 target)

**Location in firmware:** 0x0A00-0x0C00, 0xBA00-0xBB00

### 6. Protocol State Machine ✓ (Complete)
Main protocol handling and state transitions.

**Implemented in `protocol.c` (~3 functions):**
- `protocol_dispatch` ✓ - Protocol dispatcher
- `protocol_state_machine` ✓ - Main state machine (0x3900)
- `handler_3adb` ✓ - State/event handler (0x3ADB)

**Location in firmware:** 0x3900-0x3E00, 0x4F00-0x5100

### 7. Power Management (Partial)
Power state management and sleep modes.

**Implemented in `power.c` (~9 functions):**
- `usb_power_init` ✓ - USB power initialization
- `power_set_suspended` ✓, `power_clear_suspended` ✓
- Various power-related helpers ✓

**Remaining (~10 functions):**
- Various power-related helpers

**Location in firmware:** 0xCB00-0xCBA0, 0xD07F-0xD0A0

### 8. Error Handling and Logging (Low Priority)
Error detection, handling, and debug output.

**Implemented in `bank1.c` (stubs ~4 functions):**
- `handler_ed02` ✓ (stub)
- `handler_eef9` ✓ (stub)
- `handler_e762` ✓ (stub)
- `handler_e677` ✓ (stub)

**Remaining (~20 functions):**
- `error_handler_e911` - Bank 1 error handler (full implementation)
- `error_handler_a066` - Bank 1 error handler
- `error_handler_ef4e` - Bank 1 error handler
- `debug_output_handler` - Debug output (0xAF5E)

**Location in firmware:** 0xE900-0xEF00 (Bank 1)

---

## Dispatch Stubs (0x0300-0x0650)

There are approximately **80 dispatch stubs** in the 0x0300-0x0650 region that route to handlers in various banks.

**Status:** ~15 dispatch stubs implemented.

---

## Bank 1 Functions (0x10000-0x17F0C)

Bank 1 contains ~32KB of code accessed via DPX=1.

| Address | Function | Status |
|---------|----------|--------|
| 0xE911 | error_handler_e911 | Stub only |
| 0xA066 | error_handler_a066 | Stub only |
| 0xEF4E | error_handler_ef4e | Stub only |
| 0xED02 | handler_ed02 | Stub ✓ |
| 0xEEF9 | handler_eef9 | Stub ✓ |
| 0xE762 | handler_e762 | Stub ✓ |
| 0xE677 | handler_e677 | Stub ✓ |

---

## Data Tables

| Address | Size | Description | Status |
|---------|------|-------------|--------|
| 0x0648 | ~200 | Initialization table | Partial |
| 0x5A6A | 256 | EP index lookup table | ✓ |
| 0x5B6A | 8 | EP bit mask table | ✓ |
| 0x5B72 | 8 | EP offset table | ✓ |
| 0x5B7A | ~100 | Additional EP tables | Not implemented |
| 0x7000 | 4096 | Flash buffer | Defined |
| 0xF000 | 4096 | USB buffer | Defined |

---

## Priority Implementation Order

### Phase 1: Core Functionality (In Progress)
1. Complete USB endpoint handler (`usb_ep_handler` at 0x5442) - partial
2. Complete USB master handler (`usb_master_handler` at 0x10E0) - partial
3. ~~Implement `usb_ep_process` (0x52A7)~~ ✓
4. Implement NVMe command submission path - partial

### Phase 2: Data Transfer ✓ (Mostly Complete)
1. ~~DMA channel configuration and start~~ ✓
2. ~~DMA transfer helper functions (0x1602-0x16CC)~~ ✓
3. ~~SCSI/Mass Storage command processing~~ ✓
4. NVMe I/O request handling - partial

### Phase 3: Protocol ✓ (Complete)
1. ~~Protocol state machine (0x3900)~~ ✓
2. ~~Event handling (0x3ADB)~~ ✓
3. ~~Core handler (0x4FF2)~~ ✓

### Phase 4: Error Handling & Misc
1. Bank 1 error handlers (full implementation)
2. Power management completion
3. Debug output

---

## Notes

### Functions by Category (approximate counts)

| Category | Total | Implemented | Remaining |
|----------|-------|-------------|-----------|
| Dispatch stubs | 80 | 15 | 65 |
| USB | 100 | 29 | 71 |
| NVMe | 70 | 33 | 37 |
| DMA | 30 | 24 | 6 |
| PCIe/PHY | 40 | 30 | 10 |
| Flash | 30 | 16 | 14 |
| Protocol/State | 60 | 10 | 50 |
| Power | 20 | 9 | 11 |
| Utility | 80 | 25 | 55 |
| Timer/ISR | 30 | 15 | 15 |
| Bank 1 | 100 | 10 | 90 |
| **Total** | **640** | **216** | **424** |

### Memory Usage (Current)

```
CODE:  13,825 bytes / 98,012 bytes (14.1%)
XDATA: Registers defined, globals defined
IDATA: Work areas defined (I_WORK_40-55)
```

### Key Files to Reference

- `ghidra.c` - Ghidra decompilation of all functions
- `fw.bin` - Original firmware binary
- `usb-to-pcie-re/ASM2x6x/doc/Notes.md` - Reverse engineering notes
- `usb.py` - Python library that talks to this chip
