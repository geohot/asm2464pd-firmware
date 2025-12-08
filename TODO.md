# ASM2464PD Firmware Reverse Engineering TODO

## Progress Summary

- **Functions remaining**: ~774
- **Stub functions** (empty placeholder): 24 (State Machine Helpers completed)
- **High-priority** (called 5+ times): 68
- **Firmware size**: 39,826 / 79,197 bytes (50% of actual code)

### Metrics Note

Function count is the primary metric. File size comparison uses dense code only (~79KB, excludes ~19KB padding).
SDCC generates different code than the original compiler (likely Keil C51), so byte-exact matching is not possible.

---

## High Priority Functions (called 10+ times)

These functions are called frequently and should be prioritized:

| Address | Calls | Status | Name |
|---------|-------|--------|------|
| 0x9403 | 56 | TODO | - |
| 0x9388 | 48 | TODO | - |
| 0xa2df | 24 | STUB | pcie_set_state_a2df |
| 0x995a | 18 | TODO | - |
| 0xaa37 | 18 | TODO | - |
| 0xa9f9 | 16 | TODO | - |
| 0xaa02 | 16 | TODO | - |
| 0x994e | 14 | TODO | - |
| 0xd1e6 | 14 | TODO | - |
| 0xd1f2 | 14 | TODO | - |
| 0x020b | 13 | TODO | - |
| 0xe73a | 12 | STUB | helper_e73a |
| 0xa2ff | 11 | TODO | - |
| 0xbfc4 | 11 | TODO | - |
| 0xe933 | 11 | TODO | - |
| 0x9731 | 10 | TODO | - |
| 0xc1f9 | 10 | TODO | - |
| 0xd5da | 10 | TODO | - |

---

## Utility Functions (0x0000-0x0FFF)

**Total: 19** | Stubs: 5 | High-priority: 2

### Stubs (need implementation)

- [ ] `0x0557` - dispatch_handler_0557 (1 calls)
- [ ] `0x05f7` - pcie_cleanup_05f7 (1 calls)
- [ ] `0x05fc` - pcie_cleanup_05fc (1 calls)
- [ ] `0x0633` - pcie_write_reg_0633 (1 calls)
- [ ] `0x0638` - pcie_write_reg_0638 (1 calls)

### High Priority (5+ calls)

- [ ] `0x020b` (13 calls)
- [ ] `0x0c9e` (9 calls)

### Other (12 functions)

- [ ] `0x0bfd` (2 calls)
- [ ] `0x0016` (1 calls)
- [ ] `0x0110` (1 calls)
- [ ] `0x034d` (1 calls)
- [ ] `0x0555` (1 calls)
- [ ] `0x0810` (1 calls)
- [ ] `0x09e7` (1 calls)
- [ ] `0x0cb9` (1 calls)
- [ ] `0x0d15` (1 calls)
- [ ] `0x0d59` (1 calls)
- [ ] `0x0da9` (1 calls)
- [ ] `0x0e15` (1 calls)

---

## State Machine Helpers (0x1000-0x1FFF)

**Total: 49** | Stubs: 0 (all implemented) | High-priority: 5 implemented

### Stubs (all implemented)

- [x] `0x15d4` - helper_15d4 (5 calls) - DPTR setup with carry
- [x] `0x15ef` - helper_15ef (5 calls) - SCSI DMA parameter array pointer
- [x] `0x1b07` - FUN_CODE_1b07 (5 calls) - SCSI control array read
- [x] `0x1b0b` - helper_1b0b (5 calls) - XDATA read with carry
- [x] `0x180d` - usb_ep_loop_180d (4 calls) - USB endpoint processing
- [x] `0x15f1` - helper_15f1 (3 calls) - SCSI DMA parameter pointer
- [x] `0x166f` - helper_166f (1 calls) - DPTR setup for I_WORK_43

### High Priority (all implemented)

- [x] `0x120d` - state_transfer_calc_120d (8 calls) - transfer calculation
- [x] `0x1564` - xdata_write_load_triple_1564 (7 calls) - write and load triple
- [x] `0x12aa` - state_transfer_setup_12aa (5 calls) - transfer setup
- [x] `0x1b3b` - scsi_get_ctrl_ptr_1b3b (5 calls) - SCSI control pointer
- [x] `0x1bd7` - mem_read_ptr_1bd7 (5 calls) - memory read with carry

### Other (37 functions)

- [ ] `0x120b` (4 calls)
- [ ] `0x15a0` (4 calls)
- [ ] `0x1be1` (4 calls)
- [ ] `0x121b` (3 calls)
- [ ] `0x1b77` (3 calls)
- [ ] `0x1231` (2 calls)
- [ ] `0x1295` (2 calls)
- [ ] `0x1660` (2 calls)
- [ ] `0x16d2` (2 calls)
- [ ] `0x1b55` (2 calls)
- [ ] `0x1b59` (2 calls)
- [ ] `0x1006` (1 calls)
- [ ] `0x1203` (1 calls)
- [ ] `0x1205` (1 calls)
- [ ] `0x1254` (1 calls)
- [ ] `0x12a6` (1 calls)
- [ ] `0x12ab` (1 calls)
- [ ] `0x12c3` (1 calls)
- [ ] `0x12cb` (1 calls)
- [ ] `0x12ea` (1 calls)
- [ ] `0x1470` (1 calls)
- [ ] `0x1607` (1 calls)
- [ ] `0x165e` (1 calls)
- [ ] `0x168c` (1 calls)
- [ ] `0x168e` (1 calls)
- ... and 12 more

---

## Protocol State Machines (0x2000-0x3FFF)

**Total: 16** | Stubs: 0 | Implemented: 7 | High-priority: 0

### Implemented

- [x] `0x3419` - usb_ep_loop_3419 (2 calls) - USB endpoint processing loop
- [x] `0x3bcd` - helper_3bcd (3 calls) - DMA state transfer handler
- [x] `0x313a` - helper_313a_check_nonzero (2 calls) - Check 32-bit value non-zero
- [x] `0x3212` - scsi_dma_tag_setup_3212 (1 calls) - SCSI DMA tag setup
- [x] `0x38d4` - helper_38d4 (2 calls) - State machine event handler
- [x] `0x3cb8` - helper_3cb8 (1 calls) - USB event handler with state dispatch

### Other (9 functions)

- [ ] `0x3130` (2 calls)
- [ ] `0x3179` (2 calls)
- [ ] `0x31c5` (2 calls)
- [ ] `0x227f` (1 calls)
- [ ] `0x22ff` (1 calls)
- [ ] `0x2406` (1 calls)
- [ ] `0x2412` (1 calls)
- [ ] `0x24fc` (1 calls)
- [ ] `0x3226` (1 calls)
- [ ] `0x32a5` (1 calls)
- [ ] `0x3978` (1 calls)

---

## SCSI/USB Mass Storage (0x4000-0x5FFF)

**Status: COMPLETE** - All real functions implemented, remaining addresses are data/padding

### Implemented Functions (45 functions in scsi.c)

- [x] `0x4013` - scsi_setup_transfer_result
- [x] `0x4042` - scsi_process_transfer
- [x] `0x40d9` - scsi_state_dispatch
- [x] `0x419d` - scsi_setup_action
- [x] `0x425f` - scsi_init_transfer_mode
- [x] `0x43d3` - scsi_dma_dispatch
- [x] `0x4469` - scsi_dma_start_with_param
- [x] `0x4532` - scsi_buffer_threshold_config
- [x] `0x45d0` - scsi_transfer_dispatch
- [x] `0x466b` - scsi_nvme_queue_process
- [x] `0x480c` - scsi_csw_build
- [x] `0x4904` - scsi_csw_send
- [x] `0x4977` - scsi_dma_set_mode
- [x] `0x4abf` - scsi_dma_dispatch_helper
- [x] `0x4b8b` - scsi_endpoint_queue_process
- [x] `0x4c40` - scsi_dma_check_mask
- [x] `0x4c98` - scsi_queue_dispatch
- [x] `0x4d44` - scsi_state_handler
- [x] `0x4d92` - uart_print_hex_byte
- [x] `0x4ddc` - scsi_transfer_check
- [x] `0x4ef5` - scsi_queue_scan_handler
- [x] `0x4f37` - nvme_scsi_cmd_buffer_setup
- [x] `0x5008` - scsi_core_process
- [x] `0x502e` - scsi_clear_slot_entry
- [x] `0x5043` - scsi_read_slot_table
- [x] `0x5069` - scsi_transfer_check_5069
- [x] `0x50a2` - scsi_transfer_start_alt
- [x] `0x50ff` - scsi_tag_setup_50ff
- [x] `0x5112` - scsi_nvme_completion_read
- [x] `0x519e` - scsi_transfer_start
- [x] `0x51c7` - scsi_uart_print_hex
- [x] `0x51e6` - scsi_uart_print_digit
- [x] `0x51ef` - scsi_cbw_parse
- [x] `0x5216` - scsi_ep_init_handler
- [x] `0x52b1` - scsi_state_dispatch_52b1
- [x] `0x52c7` - scsi_queue_check_52c7
- [x] `0x5305` - scsi_check_link_status
- [x] `0x5321` - scsi_flash_ready_check
- [x] `0x533d` - scsi_dma_check_mask
- [x] `0x5359` - scsi_queue_dispatch
- [x] `0x5373` - scsi_decrement_pending
- [x] `0x53a7` - scsi_decrement_pending (alt)
- [x] `0x53c0` - scsi_cbw_validate
- [x] `0x53e6` - scsi_sys_status_update
- [x] `0x541f` - scsi_csw_write_residue

### Data/Mid-function Addresses (not code entry points)

- `0x4b5f` - mid-function (part of 0x4b8b)
- `0x5017`, `0x501b` - mid-function jump targets
- `0x5157` - data table (nop padding)
- `0x51f9` - mid-function (CBW signature check)
- `0x54fc`, `0x5622`, `0x573b` - data/padding regions
- `0x5058`, `0x5061`, `0x551f` - data tables

---

## NVMe/PCIe Config (0x8000-0x9FFF)

**Total: 201** | Stubs: 0 | High-priority: 19

### High Priority (5+ calls)

- [ ] `0x9403` (56 calls)
- [ ] `0x9388` (48 calls)
- [ ] `0x995a` (18 calls)
- [ ] `0x994e` (14 calls)
- [ ] `0x9731` (10 calls)
- [ ] `0x994c` (9 calls)
- [ ] `0x984d` (7 calls)
- [ ] `0x9854` (7 calls)
- [ ] `0x9777` (6 calls)
- [ ] `0x957c` (5 calls)
- [ ] `0x9695` (5 calls)
- [ ] `0x976e` (5 calls)
- [ ] `0x97bd` (5 calls)
- [ ] `0x97c9` (5 calls)
- [ ] `0x97fc` (5 calls)
- [ ] `0x9874` (5 calls)
- [ ] `0x9887` (5 calls)
- [ ] `0x996d` (5 calls)
- [ ] `0x99c7` (5 calls)

### Other (182 functions)

- [ ] `0x900a` (4 calls)
- [ ] `0x9386` (4 calls)
- [ ] `0x953d` (4 calls)
- [ ] `0x9630` (4 calls)
- [ ] `0x9641` (4 calls)
- [ ] `0x964d` (4 calls)
- [ ] `0x9661` (4 calls)
- [ ] `0x9668` (4 calls)
- [ ] `0x9670` (4 calls)
- [ ] `0x96e3` (4 calls)
- [ ] `0x9704` (4 calls)
- [ ] `0x9789` (4 calls)
- [ ] `0x97d5` (4 calls)
- [ ] `0x9803` (4 calls)
- [ ] `0x98b7` (4 calls)
- [ ] `0x98bf` (4 calls)
- [ ] `0x98c7` (4 calls)
- [ ] `0x9958` (4 calls)
- [ ] `0x99b5` (4 calls)
- [ ] `0x99d1` (4 calls)
- [ ] `0x99d8` (4 calls)
- [ ] `0x9a3e` (4 calls)
- [ ] `0x9070` (3 calls)
- [ ] `0x925a` (3 calls)
- [ ] `0x95f2` (3 calls)
- ... and 157 more

---

## Queue/Handler Functions (0xA000-0xBFFF)

**Total: 197** | Stubs: 9 | High-priority: 20

### Stubs (need implementation)

- [ ] `0xa2df` - pcie_set_state_a2df (24 calls)
- [ ] `0xa655` - usb_descriptor_helper_a655 (7 calls)
- [ ] `0xa310` - pcie_setup_lane_a310 (6 calls)
- [ ] `0xa644` - usb_descriptor_helper_a644 (5 calls)
- [ ] `0xa34f` - pcie_get_status_a34f (3 calls)
- [ ] `0xa372` - pcie_get_status_a372 (2 calls)
- [ ] `0xa38b` - pcie_setup_a38b (2 calls)
- [ ] `0xa3c4` - pcie_check_int_source_a3c4 (2 calls)
- [ ] `0xa648` - usb_descriptor_helper_a648 (1 calls)

### High Priority (5+ calls)

- [ ] `0xaa37` (18 calls)
- [ ] `0xa9f9` (16 calls)
- [ ] `0xaa02` (16 calls)
- [ ] `0xa2ff` (11 calls)
- [ ] `0xbfc4` (11 calls)
- [ ] `0xb6fa` (8 calls)
- [ ] `0xa35f` (7 calls)
- [ ] `0xb6d4` (7 calls)
- [ ] `0xbcfe` (7 calls)
- [ ] `0xa308` (6 calls)
- [ ] `0xab27` (6 calls)
- [ ] `0xbf9a` (6 calls)
- [ ] `0xbfb8` (6 calls)
- [ ] `0xa348` (5 calls)
- [ ] `0xaa36` (5 calls)
- [ ] `0xb6f0` (5 calls)

### Other (172 functions)

- [ ] `0xa2f8` (4 calls)
- [ ] `0xa2f9` (4 calls)
- [ ] `0xa334` (4 calls)
- [ ] `0xa344` (4 calls)
- [ ] `0xaa09` (4 calls)
- [ ] `0xaa2b` (4 calls)
- [ ] `0xaa42` (4 calls)
- [ ] `0xaa7d` (4 calls)
- [ ] `0xaaab` (4 calls)
- [ ] `0xaaad` (4 calls)
- [ ] `0xa2c2` (3 calls)
- [ ] `0xa31c` (3 calls)
- [ ] `0xa3db` (3 calls)
- [ ] `0xa3f5` (3 calls)
- [ ] `0xa647` (3 calls)
- [ ] `0xaa57` (3 calls)
- [ ] `0xaa7f` (3 calls)
- [ ] `0xaa90` (3 calls)
- [ ] `0xaab5` (3 calls)
- [ ] `0xaadf` (3 calls)
- [ ] `0xaae1` (3 calls)
- [ ] `0xab3a` (3 calls)
- [ ] `0xab44` (3 calls)
- [ ] `0xab63` (3 calls)
- [ ] `0xab87` (3 calls)
- ... and 147 more

---

## Event/Error Handlers (0xC000-0xDFFF)

**Total: 214** | Stubs: 2 | High-priority: 13

### Stubs (need implementation)

- [ ] `0xd17a` - helper_d17a (1 calls)
- [ ] `0xd8d5` - pcie_handler_d8d5 (1 calls)

### High Priority (5+ calls)

- [ ] `0xd1e6` (14 calls)
- [ ] `0xd1f2` (14 calls)
- [ ] `0xc1f9` (10 calls)
- [ ] `0xd5da` (10 calls)
- [ ] `0xc2e7` (8 calls)
- [ ] `0xda9f` (7 calls)
- [ ] `0xc2f8` (6 calls)
- [ ] `0xd185` (6 calls)
- [ ] `0xc20f` (5 calls)
- [ ] `0xc2bf` (5 calls)
- [ ] `0xc2f1` (5 calls)
- [ ] `0xce23` (5 calls)
- [ ] `0xceab` (5 calls)

### Other (199 functions)

- [ ] `0xc2e0` (4 calls)
- [ ] `0xc34a` (4 calls)
- [ ] `0xc351` (4 calls)
- [ ] `0xc358` (4 calls)
- [ ] `0xc35f` (4 calls)
- [ ] `0xc366` (4 calls)
- [ ] `0xc36d` (4 calls)
- [ ] `0xc374` (4 calls)
- [ ] `0xc37b` (4 calls)
- [ ] `0xc382` (4 calls)
- [ ] `0xc389` (4 calls)
- [ ] `0xcb0f` (4 calls)
- [ ] `0xd172` (4 calls)
- [ ] `0xd17e` (4 calls)
- [ ] `0xd229` (4 calls)
- [ ] `0xd235` (4 calls)
- [ ] `0xd265` (4 calls)
- [ ] `0xdde2` (4 calls)
- [ ] `0xc027` (3 calls)
- [ ] `0xc031` (3 calls)
- [ ] `0xc074` (3 calls)
- [ ] `0xc09e` (3 calls)
- [ ] `0xc1af` (3 calls)
- [ ] `0xc261` (3 calls)
- [ ] `0xc29e` (3 calls)
- ... and 174 more

---

## Bank1 High (0xE000-0xFFFF)

**Total: 66** | Stubs: 7 | High-priority: 9

### Stubs (need implementation)

- [ ] `0xe73a` - helper_e73a (12 calls)
- [ ] `0xe1c6` - FUN_CODE_e1c6 (9 calls)
- [ ] `0xe890` - pcie_handler_e890 (7 calls)
- [ ] `0xe3b7` - helper_e3b7 (5 calls)
- [ ] `0xe06b` - pcie_handler_e06b (3 calls)
- [ ] `0xe7c1` - handler_e7c1 (2 calls)
- [ ] `0xe974` - pcie_handler_e974 (2 calls)

### High Priority (5+ calls)

- [ ] `0xe933` (11 calls)
- [ ] `0xe81b` (9 calls)
- [ ] `0xe054` (7 calls)
- [ ] `0xe461` (6 calls)
- [ ] `0xe8f9` (5 calls)

### Other (54 functions)

- [ ] `0xe2b9` (4 calls)
- [ ] `0xe775` (4 calls)
- [ ] `0xe020` (3 calls)
- [ ] `0xe26a` (3 calls)
- [ ] `0xe726` (3 calls)
- [ ] `0xe7a8` (3 calls)
- [ ] `0xe7e5` (3 calls)
- [ ] `0xe090` (2 calls)
- [ ] `0xe0f4` (2 calls)
- [ ] `0xe19e` (2 calls)
- [ ] `0xe1cb` (2 calls)
- [ ] `0xe5b1` (2 calls)
- [ ] `0xe68f` (2 calls)
- [ ] `0xe6a7` (2 calls)
- [ ] `0xe730` (2 calls)
- [ ] `0xe7f8` (2 calls)
- [ ] `0xe85f` (2 calls)
- [ ] `0xe914` (2 calls)
- [ ] `0xe93a` (2 calls)
- [ ] `0xe00c` (1 calls)
- [ ] `0xe030` (1 calls)
- [ ] `0xe03c` (1 calls)
- [ ] `0xe060` (1 calls)
- [ ] `0xe07d` (1 calls)
- [ ] `0xe0e4` (1 calls)
- ... and 29 more

---

## Notes

### Memory Layout
- Bank 0 low: 0x0000-0x5D2E (~24KB code)
- Bank 0 high: 0x8000-0xE975 (~27KB code)
- Bank 1: 0x10000-0x16EBA (~28KB code, mapped to 0x8000 when active)
- Padding regions: ~19KB (not real code)

### Key Subsystems
- **0x9000-0x9FFF**: NVMe command engine, PCIe config
- **0xA000-0xAFFF**: Admin commands, queue management
- **0xB000-0xBFFF**: PCIe TLP handlers, register helpers
- **0xC000-0xCFFF**: Error logging, event handlers
- **0xD000-0xDFFF**: Power management, PHY config
- **0xE000-0xEFFF**: Bank1 handlers (via dispatch stubs)