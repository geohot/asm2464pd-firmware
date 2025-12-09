# ASM2464PD Firmware Reverse Engineering TODO

## Progress Summary

- **Functions remaining**: ~618
- **Stub functions** (empty placeholder): 13 (7 utility + 6 event/error)
- **High-priority** (called 5+ times): 29
- **Firmware size**: 47,406 / 79,197 bytes (59.9% of actual code)

### Metrics Note

Function count is the primary metric. File size comparison uses dense code only (~79KB, excludes ~19KB padding).
SDCC generates different code than the original compiler (likely Keil C51), so byte-exact matching is not possible.

---

## High Priority Functions (called 10+ times)

These functions are called frequently and should be prioritized:

| Address | Calls | Status | Name |
|---------|-------|--------|------|
| 0x9388 | 48 | TODO | - |
| 0xaa37 | 18 | TODO | - |
| 0xd1e6 | 14 | TODO | - |
| 0xd1f2 | 14 | TODO | - |
| 0xdd12 | 11 | STUB | helper_dd12 |
| 0x9731 | 10 | TODO | - |
| 0xd5da | 10 | TODO | - |

---

## Utility Functions (0x0000-0x0FFF)

**Total: 13** | Stubs: 4 | High-priority: 0

### Implemented

- [x] `0x0412` - helper_0412 - PCIe doorbell trigger with status-based write
- [x] `0x05fc` - pcie_cleanup_05fc - Returns 0xF0
- [x] `0x0633` - pcie_write_reg_0633 - Power state check

### Stubs (need implementation - bank 1 targets)

- [ ] `0x048a` - helper_048a (1 calls) - targets 0xece1 bank 1
- [ ] `0x0557` - dispatch_handler_0557 (1 calls) - targets 0xee94 bank 1
- [ ] `0x05f7` - pcie_cleanup_05f7 (1 calls) - targets 0xcbcc bank 1
- [ ] `0x0638` - pcie_write_reg_0638 (1 calls) - targets 0xeadb bank 1

### Other (6 functions)

- [ ] `0x0110` (1 calls)
- [ ] `0x034d` (1 calls)
- [ ] `0x0555` (1 calls)
- [ ] `0x0810` (1 calls)
- [ ] `0x09e7` (1 calls)
- [ ] `0x0d59` (1 calls)

---

## State Machine Helpers (0x1000-0x1FFF)

**Status: STUBS COMPLETE** ✓

All stub functions in this range are now implemented.

### Stubs (all implemented)

- [x] `0x1564` - xdata_write_load_triple_1564 (stubs.c)
- [x] `0x15d4` - helper_15d4_ptr (stubs.c)
- [x] `0x1659` - helper_1659 / transfer_set_dptr_0464_offset (dma.c, stubs.c)
- [x] `0x1660` - helper_1660 / set_dptr_04xx_1660 (state_helpers.c, stubs.c)
- [x] `0x1677` - helper_1677 / transfer_calc_work53_offset (dma.c, stubs.c)
- [x] `0x173b` - dma_clear_dword_at (dma.c)
- [x] `0x1ce4` - helper_1ce4 / usb_calc_addr_04b7_plus (usb.c, stubs.c)
- [x] `0x159f` - helper_159f (stubs.c)
- [x] `0x165e` - helper_165e / get_ptr_044e_offset_165e (stubs.c, state_helpers.c)
- [x] `0x1755` - helper_1755 (stubs.c)

### DMA/Transfer functions (implemented in dma.c)

- [x] `0x16f3` - dma_clear_status
- [x] `0x16ff` - dma_reg_wait_bit
- [x] `0x1709` - dma_set_scsi_param3
- [x] `0x1713` - dma_set_scsi_param1
- [x] `0x171d` - dma_load_transfer_params
- [x] `0x172c` - dma_check_state_counter
- [x] `0x1743` - dma_get_config_offset_05a8
- [x] `0x1752` - dma_calc_offset_0059
- [x] `0x175d` - dma_init_channel_b8
- [x] `0x176b` - dma_calc_addr_0478
- [x] `0x1779` - dma_calc_addr_0479
- [x] `0x1787` - dma_set_error_flag
- [x] `0x1795` - dma_clear_state_counters
- [x] `0x179d` - dma_calc_addr_00c2
- [x] `0x17a9` - dma_init_ep_queue
- [x] `0x17b5` - scsi_get_tag_count_status
- [x] `0x17c1` - scsi_get_queue_status
- [x] `0x17cd` - dma_shift_and_check
- [x] `0x17f3` - dma_shift_rrc2_mask
- [x] `0x180d` - usb_ep_loop_180d
- [x] `0x1b55` - write_and_set_c412_bit1_1b55 (state_helpers.c)
- [x] `0x1b59` - set_c412_bit1_1b59 (state_helpers.c)

### Remaining entry points (low priority - likely inline/mid-function entries)

- [ ] `0x121b` (3 calls) - mid-function entry
- [ ] `0x1231` (2 calls) - mid-function entry
- [ ] `0x1295` (2 calls) - mid-function entry
- [ ] `0x16d2` (2 calls)
- [ ] `0x1203` (1 calls)
- [ ] `0x1205` (1 calls)
- [ ] `0x1254` (1 calls)
- [ ] `0x12a6` (1 calls)
- [ ] `0x12ab` (1 calls)
- [ ] `0x12c3` (1 calls)
- [ ] `0x12cb` (1 calls)
- [ ] `0x12ea` (1 calls)
- [ ] `0x1470` (1 calls)

---

## Protocol State Machines (0x2000-0x3FFF)

**Status: COMPLETE** ✓

All protocol state machine functions in this range are implemented in `src/app/protocol.c` and `src/app/stubs.c`.

Key functions:
- [x] helper_313d (0x313d) - 32-bit value check
- [x] nvme_call_and_signal_3219 (0x3219)
- [x] nvme_ep_config_init_3267 (0x3267)
- [x] queue_idx_get_3291 (0x3291)
- [x] protocol_state_dispatcher_32a5 (0x32a5) - Complex state machine
- [x] protocol_state_machine (0x3900-0x39DE)
- [x] Various helper functions (0x3130-0x32a4)

Note: Addresses 0x227f, 0x22ff, 0x2406, 0x2412, 0x24fc are DATA tables (USB strings), not code.
Note: 0x3179 is a mid-function entry point, 0x3978 is a jump table.

---

## SCSI/USB Mass Storage (0x4000-0x5FFF)

**Status: COMPLETE** ✓

All 60 functions in this range are implemented in `src/app/scsi.c`.

Key functions:
- [x] CBW/CSW handling (0x4013-0x4977)
- [x] SCSI command translation (0x4b25-0x4ff2)
- [x] DMA/buffer management (0x5038-0x50ff)
- [x] Queue handlers (0x5112-0x53d4)
- [x] Transfer helpers (0x5426-0x5462)
- [x] Data tables identified: 0x5157, 0x53a4, 0x54fc, 0x5622 (not code)
- [x] `0x573b` - scsi_loop_process_573b (stub, complex loop)

---

## NVMe/PCIe Config (0x8000-0x9FFF)

**Total: 173** | Stubs: 0 | High-priority: 10

### Stubs (need implementation)

(none - all stubs implemented)

### Implemented

- [x] `0x9388` (48 calls) - flash_config_init_9388 in state_helpers.c
- [x] `0x9731` (10 calls) - in nvme.c/cmd.c
- [x] `0x957c` (5 calls) - in nvme.c
- [x] `0x9695` (5 calls) - in nvme.c
- [x] `0x996d` (5 calls) - in pcie.c
- [x] `0x96ae` (3 calls) - in cmd.c
- [x] `0x953d` (4 calls) - in nvme.c
- [x] `0x9630` (4 calls) - in nvme.c
- [x] `0x9641` (4 calls) - in nvme.c
- [x] `0x964d` (4 calls) - in cmd.c
- [x] `0x9661` (4 calls) - in cmd.c
- [x] `0x9668` (4 calls) - in cmd.c
- [x] `0x9670` (4 calls) - in cmd.c
- [x] `0x96e3` (4 calls) - in cmd.c
- [x] `0x9704` (4 calls) - in cmd.c
- [x] `0x9958` (4 calls) - in pcie.c
- [x] `0x99b5` (4 calls) - in pcie.c
- [x] `0x9a3e` (4 calls) - in pcie.c
- [x] `0x95f2` (3 calls) - in cmd.c
- [x] `0x969e` (3 calls) - in cmd.c
- [x] `0x96ec` (3 calls) - in cmd.c

### High Priority (5+ calls) - State Machine Entry Points

**Note:** These addresses are mid-function entry points within complex PCIe config
state machines at 0x9700-0x9901. They use overlapping code optimization where
different entry points share code paths. They will be implemented as part of the
larger state machine functions.

- [x] `0x994c` (9 calls) - pcie_write_data_reg_with_val in pcie.c
- [ ] `0x984d` (7 calls) - Mid-loop entry: subb a,r1; xrl a,r2; jnc (overlapping)
- [ ] `0x9854` (7 calls) - Mid-loop entry: read DPTR, add 3, call 0x99b5
- [ ] `0x9777` (6 calls) - Entry: mask A to 0x0F, call helpers, compare
- [ ] `0x976e` (5 calls) - Entry: inc r2; anl a,r4; read @dptr; check bit 4
- [ ] `0x97bd` (5 calls) - Within 0x9700-0x9900 state machine
- [ ] `0x97c9` (5 calls) - Within 0x9700-0x9900 state machine
- [ ] `0x97fc` (5 calls) - Within 0x9700-0x9900 state machine
- [ ] `0x9874` (5 calls) - Within 0x9800-0x9900 state machine
- [ ] `0x9887` (5 calls) - Within 0x9800-0x9900 state machine

### Additional Implemented (in pcie.c 0x99xx range)

- [x] `0x9902-0x990b` - pcie_trigger_helper
- [x] `0x990c-0x9915` - pcie_config_write
- [x] `0x9916-0x9922` - pcie_store_txn_idx
- [x] `0x9923-0x992f` - pcie_lookup_config_05c0
- [x] `0x994e-0x9953` - pcie_write_data_reg
- [x] `0x9954-0x9961` - pcie_calc_queue_idx
- [x] `0x996a-0x9976` - pcie_check_txn_count
- [x] `0x9977-0x997f` - pcie_lookup_05b6
- [x] `0x99c6-0x99cd` - pcie_cfg_set_flag
- [x] `0x99ce-0x99d4` - pcie_cfg_inc_flag
- [x] Many more 0x99xx helpers in pcie.c

### Other (163 functions)

- [ ] `0x900a` (4 calls)
- [ ] `0x9386` (4 calls)
- [ ] `0x9789` (4 calls) - within state machine
- [ ] `0x97d5` (4 calls) - within state machine
- [ ] `0x9803` (4 calls) - within state machine
- [ ] `0x98b7` (4 calls) - within state machine
- [ ] `0x98bf` (4 calls) - within state machine
- [ ] `0x98c7` (4 calls) - within state machine
- [ ] `0x9070` (3 calls)
- [ ] `0x925a` (3 calls)
- ... and 153 more

---

## Queue/Handler Functions (0xA000-0xBFFF)

**Total: 142** | Stubs: 0 | High-priority: 1

### High Priority (5+ calls)

- [ ] `0xaa37` (18 calls)

### Other (141 functions)

- [ ] `0xa2f8` (4 calls)
- [ ] `0xa2f9` (4 calls)
- [ ] `0xa3db` (3 calls)
- [ ] `0xa3f5` (3 calls)
- [ ] `0xa647` (3 calls)
- [ ] `0xaadf` (3 calls)
- [ ] `0xaae1` (3 calls)
- [ ] `0xab44` (3 calls)
- [ ] `0xab63` (3 calls)
- [ ] `0xab87` (3 calls)
- [ ] `0xab97` (3 calls)
- [ ] `0xabc2` (3 calls)
- [ ] `0xb763` (3 calls)
- [ ] `0xb76c` (3 calls)
- [ ] `0xb796` (3 calls)
- [ ] `0xb79d` (3 calls)
- [ ] `0xbfa7` (3 calls)
- [ ] `0xbfab` (3 calls)
- [ ] `0xbfb5` (3 calls)
- [ ] `0xbfcb` (3 calls)
- [ ] `0xa2c1` (2 calls)
- [ ] `0xa30c` (2 calls)
- [ ] `0xa394` (2 calls)
- [ ] `0xa3a4` (2 calls)
- [ ] `0xa3b4` (2 calls)
- ... and 116 more

---

## Event/Error Handlers (0xC000-0xDFFF)

**Total: 211** | Stubs: 6 | High-priority: 12

### Stubs (need implementation)

- [ ] `0xdd12` - helper_dd12 (11 calls)
- [ ] `0xce23` - transfer_handler_ce23 (5 calls)
- [ ] `0xcb05` - helper_cb05 (3 calls)
- [ ] `0xd17a` - helper_d17a (1 calls)
- [ ] `0xd8d5` - pcie_handler_d8d5 (1 calls)
- [ ] `0xdbbb` - helper_dbbb (1 calls)

### High Priority (5+ calls)

- [ ] `0xd1e6` (14 calls)
- [ ] `0xd1f2` (14 calls)
- [ ] `0xd5da` (10 calls)
- [ ] `0xc2e7` (8 calls)
- [ ] `0xc2f8` (6 calls)
- [ ] `0xd185` (6 calls)
- [ ] `0xc20f` (5 calls)
- [ ] `0xc2bf` (5 calls)
- [ ] `0xc2f1` (5 calls)
- [ ] `0xceab` (5 calls)

### Other (195 functions)

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
- [ ] `0xd172` (4 calls)
- [ ] `0xd17e` (4 calls)
- [ ] `0xd229` (4 calls)
- [ ] `0xd235` (4 calls)
- [ ] `0xd265` (4 calls)
- [ ] `0xc027` (3 calls)
- [ ] `0xc031` (3 calls)
- [ ] `0xc074` (3 calls)
- [ ] `0xc09e` (3 calls)
- [ ] `0xc1af` (3 calls)
- [ ] `0xc261` (3 calls)
- [ ] `0xc29e` (3 calls)
- [ ] `0xc2a5` (3 calls)
- [ ] `0xc2ac` (3 calls)
- ... and 170 more

---

## Bank1 High (0xE000-0xFFFF)

**Status: COMPLETE** ✓

**Total: 48** | Stubs: 0 | High-priority: 0 (mid-function entries)

### Stubs (all implemented)

- [x] `0xe120` - helper_e120 (stubs.c)
- [x] `0xe2b9` - check_link_status_e2b9 (stubs.c)
- [x] `0xe726` - timer_trigger_e726 (stubs.c)
- [x] `0xe68f` - dma_buffer_store_result_e68f (stubs.c)
- [x] `0xe914` - ext_mem_init_address_e914 (stubs.c)
- [x] `0xe93a` - cpu_dma_channel_91_trigger_e93a (stubs.c)
- [x] `0xe974` - pcie_handler_e974 (stubs.c - empty handler)
- [x] `0xe5fe` - pcie_channel_disable_e5fe (stubs.c, pcie.c)

### High Priority (analyzed - mid-function entries)

**Note:** These addresses are mid-function entry points within larger implemented functions.

- [x] `0xe054` (7 calls) - mid-function in check_nvme_ready_e03c (0xe03c-0xe06a)
- [x] `0xe461` (6 calls) - mid-function in cmd_init_and_wait_e459 (0xe459-0xe475)

### Other (analyzed - mid-function entries or implemented)

Most addresses are mid-function entries covered by parent function implementations:

- [x] `0xe020` - mid-function in get_pcie_status_flags_e00c (0xe00c-0xe03b)
- [x] `0xe090` - mid-function in pcie_handler_e06b (0xe06b-0xe093)
- [x] `0xe0f4` - mid-function in pcie_dma_init_e0e4 (0xe0e4-0xe0f3)
- [x] `0xe1cb` - mid-function in cmd_wait_completion (0xe1c6-0xe1ed)
- [x] `0xe85f` - mid-function in pcie_restore_ctrl_state (0xe85c-0xe868)
- [x] `0xe060` - mid-function in check_nvme_ready_e03c
- [x] `0xe07d` - mid-function in pcie_handler_e06b
- [x] `0xe239` - check_pcie_status_e239 (stubs.c)
- [x] `0xe330` - pcie_dma_config_e330 (pcie.c)
- [x] `0xe459` - cmd_init_and_wait_e459 (stubs.c)
- [x] `0xe52d` - mid-function in handler_e529 (0xe529-0xe544)

### Implemented Functions

Key Bank1 High functions implemented across src/:
- cmd.c: cmd_check_busy (0xe09a), cmd_wait_completion (0xe1c6)
- pcie.c: 0xe00c, 0xe19e, 0xe330, 0xe5fe, 0xe711, 0xe74e, 0xe775, 0xe80a, 0xe890, 0xe8cd, 0xe8ef, 0xe8f9, 0xe902
- phy.c: 0xe84d, 0xe85c
- flash.c: 0xe3f9
- power.c: 0xe647
- utils.c: 0xe80a, 0xe89d
- state_helpers.c: 0xe214, 0xe8ef
- stubs.c: 0xe03c, 0xe06b, 0xe0e4, 0xe120, 0xe239, 0xe2b9, 0xe396, 0xe3b7, 0xe3d8, 0xe459, 0xe50d, 0xe529,
           0xe5b1, 0xe677, 0xe68f, 0xe6a7, 0xe6d2, 0xe726, 0xe73a, 0xe762, 0xe7c1, 0xe7f8, 0xe81b, 0xe8f9,
           0xe902, 0xe90b, 0xe914, 0xe933, 0xe93a, 0xe95f, 0xe974

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