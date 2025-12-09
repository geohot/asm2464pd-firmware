# ASM2464PD Firmware - Remaining Work

## Progress Summary

| Metric | Value |
|--------|-------|
| **Firmware Size** | 50,117 / 98,012 bytes (51.1%) |
| **Total Functions** | ~1,100 identified in fw.bin |
| **Implemented** | ~600 with actual logic |
| **Empty Stubs** | 66 functions needing implementation |
| **Dispatch Stubs** | 162 bank-switching trampolines |

Note: SDCC generates different code than the original Keil C51 compiler, so byte-exact matching is not possible. Function-level correctness is the goal.

---

## 1. Empty Stub Functions (66 total)

These functions exist in stubs.c but have no implementation (just `{}`, `(void)param`, or `return 0`).

### USB/Descriptor Stubs (11 functions)

| Function | Signature | Address | Notes |
|----------|-----------|---------|-------|
| `usb_parse_descriptor` | `(uint8_t p1, uint8_t p2)` | - | DMA/buffer config for descriptor parsing |
| `usb_get_xfer_status` | `(void)` | - | Returns transfer status |
| `usb_event_handler` | `(void)` | - | USB event processing |
| `usb_read_transfer_params_hi` | `(void)` | - | Transfer param extraction |
| `usb_read_transfer_params_lo` | `(void)` | - | Transfer param extraction |
| `usb_get_descriptor_length` | `(uint8_t param)` | - | Descriptor length lookup |
| `usb_convert_speed` | `(uint8_t param)` | - | Speed mode conversion |
| `usb_get_descriptor_ptr` | `(void)` | - | Descriptor pointer fetch |
| `parse_descriptor` | `(uint8_t param)` | - | Descriptor parsing |
| `protocol_compare_32bit` | `(void)` | - | 32-bit protocol comparison |
| `reg_poll` | `(void)` | - | Register polling |

### Memory/State Helpers (0x1xxx range, 22 functions)

| Function | Signature | Address | Notes |
|----------|-----------|---------|-------|
| `helper_15a0` | `(void)` | 0x15a0 | Memory helper |
| `helper_16e9` | `(uint8_t param)` | 0x16e9 | State setup |
| `helper_16eb` | `(uint8_t param)` | 0x16eb | State setup |
| `helper_1aad` | `(uint8_t param)` | 0x1aad | Memory access |
| `helper_1b2e` | `(void)` | 0x1b2e | Memory helper |
| `helper_1b30` | `(void)` | 0x1b30 | Memory helper |
| `helper_1b47` | `(void)` | 0x1b47 | Memory helper |
| `helper_1b77` | `(void)` | 0x1b77 | Memory helper |
| `helper_1ba5` | `(void)` | 0x1ba5 | Memory helper |
| `helper_1bd7` | `(void)` | 0x1bd7 | Memory helper |
| `helper_1c13` | `(void)` | 0x1c13 | State helper |
| `helper_1c56` | `(void)` | 0x1c56 | State helper |
| `helper_1c6d` | `(void)` | 0x1c6d | State helper |
| `helper_1c77` | `(void)` | 0x1c77 | State helper |
| `helper_1c1b` | `(void)` | 0x1c1b | Returns 0 |
| `helper_1cae` | `(void)` | 0x1cae | State helper |
| `helper_1cc1` | `(void)` | 0x1cc1 | State helper |
| `helper_1d39` | `(void)` | 0x1d39 | State helper |
| `helper_1d43` | `(void)` | 0x1d43 | State helper |
| `FUN_CODE_1c9f` | `(void)` | 0x1c9f | Unknown |
| `ep_config_read` | `(uint8_t param)` | - | Endpoint config |
| `nvme_util_get_queue_depth` | `(uint8_t p1, uint8_t p2)` | - | Queue depth |

### Low-Level Init Helpers (0x0xxx range, 7 functions)

| Function | Signature | Address | Notes |
|----------|-----------|---------|-------|
| `helper_03a4` | `(void)` | 0x03a4 | Init helper |
| `helper_041c` | `(void)` | 0x041c | Init helper |
| `helper_048f` | `(void)` | 0x048f | Init helper |
| `helper_053e` | `(void)` | 0x053e | Init helper |
| `helper_0584` | `(void)` | 0x0584 | Init helper |
| `helper_0be6` | `(void)` | 0x0be6 | Init helper |
| `FUN_CODE_050c` | `(void)` | 0x050c | Startup code |
| `FUN_CODE_0511` | `(uint8_t p1, uint8_t p2, uint8_t p3)` | 0x0511 | Startup code |

### SCSI/Protocol Helpers (0x3xxx-0x5xxx range, 11 functions)

| Function | Signature | Address | Notes |
|----------|-----------|---------|-------|
| `helper_3578` | `(uint8_t param)` | 0x3578 | Protocol helper |
| `helper_3adb` | `(uint8_t param)` | 0x3adb | Protocol helper |
| `helper_3e81` | `(void)` | 0x3e81 | Protocol helper |
| `helper_4784` | `(void)` | 0x4784 | SCSI helper |
| `helper_488f` | `(void)` | 0x488f | SCSI helper |
| `helper_49e9` | `(void)` | 0x49e9 | SCSI helper |
| `FUN_CODE_5038` | `(void)` | 0x5038 | SCSI command |
| `FUN_CODE_5046` | `(void)` | 0x5046 | SCSI command |
| `FUN_CODE_504f` | `(void)` | 0x504f | SCSI command |
| `FUN_CODE_505d` | `(void)` | 0x505d | SCSI command |
| `FUN_CODE_5359` | `(void)` | 0x5359 | SCSI command |

### Config/State Machine Helpers (0x9xxx range, 3 functions)

| Function | Signature | Address | Notes |
|----------|-----------|---------|-------|
| `helper_9980` | `(void)` | 0x9980 | Config helper |
| `helper_99bc` | `(void)` | 0x99bc | Config helper |
| `helper_9983` | `(void)` | 0x9983 | Config helper |

### Admin/Queue Helpers (0xAxxx-0xBxxx range, 3 functions)

| Function | Signature | Address | Notes |
|----------|-----------|---------|-------|
| `helper_a2ff` | `(void)` | 0xa2ff | Admin helper |
| `helper_a33d` | `(uint8_t reg_offset)` | 0xa33d | Register read |
| `helper_be8b` | `(void)` | 0xbe8b | Buffer helper |

### Event/Power Handlers (0xDxxx range, 4 functions)

| Function | Signature | Address | Notes |
|----------|-----------|---------|-------|
| `FUN_CODE_dd0e` | `(void)` | 0xdd0e | Event handler |
| `FUN_CODE_dd12` | `(uint8_t p1, uint8_t p2)` | 0xdd12 | Command trigger |
| `FUN_CODE_df79` | `(void)` | 0xdf79 | Event handler |
| `handler_db09` | `(void)` | 0xdb09 | Event dispatch |

### PCIe/Timer Helpers (0xExxx range, 6 functions)

| Function | Signature | Address | Notes |
|----------|-----------|---------|-------|
| `FUN_CODE_e120` | `(uint8_t p1, uint8_t p2)` | 0xe120 | PCIe helper |
| `FUN_CODE_e7ae` | `(void)` | 0xe7ae | Timer helper |
| `FUN_CODE_e883` | `(void)` | 0xe883 | Timer helper |
| `helper_e762` | `(uint8_t param)` | 0xe762 | PCIe config |
| `pcie_bank1_helper_e902` | `(void)` | 0xe902 | Bank1 PCIe |
| `handler_2608` | `(void)` | 0x2608 | Handler |
| `handler_9d90` | `(void)` | 0x9d90 | Handler |

---

## 2. Dispatch Table Targets (162 addresses)

These are target addresses that dispatch.c jumps to via bank switching. The actual implementations need to be at these addresses in the firmware.

### Bank 0 Targets (addresses accessed directly)

| Address | Dispatch Entry | Purpose |
|---------|----------------|---------|
| 0x9037 | dispatch_0430 | NVMe init |
| 0x905B | - | NVMe helper |
| 0x92C5 | phy_power_config_handler | PHY power config |
| 0x9C2B | dispatch_0345 | State machine |
| 0xB031 | dispatch_05d4 | Buffer ops |
| 0xB1CB | dispatch_0327 | USB buffer |
| 0xB4BA | dispatch_0520 | Buffer helper |
| 0xB8DB | dispatch_057f | DMA buffer |
| 0xBE02 | dispatch_04c1 | Buffer complete |
| 0xBF0F | dispatch_0336 | Config helper |
| 0xBF8E | handler_bf8e | Handler |
| 0xC00D | dispatch_045d | PCIe tunnel init |
| 0xC089 | dispatch_0606 | PCIe config |
| 0xC105 | dispatch_0593 | Config helper |
| 0xC17F | dispatch_05cf | Config helper |
| 0xC4B3 | dispatch_0331 | Queue helper |
| 0xC523 | dispatch_05a2 | Queue helper |
| 0xC593 | dispatch_05c0 | Queue helper |
| 0xC66A | dispatch_034a | Transfer helper |
| 0xCA0D | dispatch_0322 | Command handler |
| 0xCB37 | dispatch_03a4 | Completion handler |
| 0xCD10 | dispatch_0390 | Command dispatch |
| 0xCDC6 | dispatch_046c | Command helper |
| 0xCE79 | dispatch_04d0 | Transfer handler |
| 0xCF7F | dispatch_033b | Config helper |
| 0xD127 | dispatch_0435 | Event dispatch |
| 0xD1CC | dispatch_05a7 | Event handler |
| 0xD2BD | dispatch_038b | DMA handler |
| 0xD30B | dispatch_05b1 | DMA helper |
| 0xD3A2 | dispatch_04d5 | Power handler |
| 0xD436 | dispatch_047b | Power helper |
| 0xD5A1 | dispatch_05bb | Power state |
| 0xD6BC | handler_d6bc | PHY handler |
| 0xD7CD | dispatch_0502 | PHY config |
| 0xD810 | dispatch_039a | DMA dispatch |
| 0xD894 | dispatch_0589 | DMA helper |
| 0xD916 | handler_d916 | DMA handler |
| 0xDA51 | dispatch_0557 | Event helper |
| 0xDA8F | dispatch_0395 | Event handler |
| 0xDB80 | dispatch_05e3 | State handler |
| 0xDBBB | dispatch_05f2 | State flag |
| 0xDBF5 | dispatch_04c6 | State helper |
| 0xDD78 | dispatch_0449 | Command trigger |
| 0xDE16 | dispatch_04f8 | Event handler |
| 0xDEE3 | dispatch_0359 | Event dispatch |
| 0xDF15 | dispatch_0368 | Event helper |
| 0xE0C7 | dispatch_058e | PCIe handler |
| 0xE14B | dispatch_04bc | PCIe config |
| 0xE1C6 | dispatch_051b | PCIe state |
| 0xE2A6 | dispatch_043f | Link handler |
| 0xE2EC | dispatch_04e4 | Link helper |
| 0xE3B7 | dispatch_04da | Timer handler |
| 0xE4F0 | dispatch_042b | Timer helper |
| 0xE50D | dispatch_0507 | Timer config |
| 0xE57D | dispatch_0467 | Interrupt handler |
| 0xE597 | dispatch_04b7 | Interrupt helper |
| 0xE617 | dispatch_0412 | PCIe doorbell |
| 0xE62F | dispatch_0417 | PCIe helper |
| 0xE647 | dispatch_041c | PCIe helper |
| 0xE65F | dispatch_0421 | PCIe helper |
| 0xE677 | dispatch_043a | Link config |
| 0xE6BD | dispatch_035e | Link helper |
| 0xE6FC | handler_e6fc | Link handler |
| 0xE762 | dispatch_0426 | PCIe config |
| 0xE77A | dispatch_0458 | PCIe helper |
| 0xE79B | dispatch_04a8 | PCIe helper |
| 0xE7AE | dispatch_04ad | Timer helper |
| 0xE7C1 | dispatch_04cb | Timer handler |
| 0xE84D | dispatch_0480 | DMA trigger |
| 0xE85C | dispatch_0485 | DMA helper |
| 0xE8A9 | dispatch_0471 | DMA handler |
| 0xE8D9 | dispatch_0476 | DMA helper |
| 0xE8E4 | dispatch_04e9 | DMA complete |
| 0xE902 | dispatch_0453 | Bank1 call |
| 0xE91D | handler_e91d | Init handler |
| 0xE925 | dispatch_0354 | Init helper |
| 0xE92C | dispatch_0386 | Init helper |
| 0xE941 | dispatch_037c | Stub |
| 0xE947 | dispatch_0381 | Stub |
| 0xE94D | dispatch_034f | Stub |
| 0xE952 | dispatch_0377 | Stub |
| 0xE953 | dispatch_0543 | Stub |
| 0xE955 | dispatch_0548 | Stub |
| 0xE957 | dispatch_049e | Timer handler |
| 0xE95B | dispatch_04a3 | Timer helper |
| 0xE95D | dispatch_0511 | Stub |
| 0xE95F | dispatch_04df | Call bd05 |
| 0xE961 | dispatch_052a | Stub |
| 0xE962 | dispatch_056b | Stub |
| 0xE963 | dispatch_0539 | Stub |
| 0xE964 | dispatch_0566 | Stub |
| 0xE965 | dispatch_050c | Stub |
| 0xE966 | dispatch_0561 | Stub |
| 0xE967 | dispatch_053e | Stub |
| 0xE968 | dispatch_055c | Stub |
| 0xE969 | dispatch_0363 | Stub |
| 0xE96A | dispatch_054d | Stub |
| 0xE96B | dispatch_0552 | Stub |
| 0xE96C | handler_e96c | Stub |
| 0xE96E | dispatch_0516 | Stub |
| 0xE96F | dispatch_036d | Stub |
| 0xE970 | dispatch_0372 | Stub |
| 0xE971 | dispatch_04b2 | Stub |
| 0xEA7C | dispatch_0601 | Completion |
| 0x8A89 | dispatch_04f3 | Bank0 code |
| 0x8D77 | dispatch_0525 | Bank0 code |

### Bank 1 Targets (addresses in 0x10000-0x18000 range, mapped at 0x8000)

| Address | Dispatch Entry | Purpose |
|---------|----------------|---------|
| 0x89DB | dispatch_03a9 | Bank1 init |
| 0x9D90 | dispatch_05e8 | Event dispatch |
| 0xA066 | dispatch_061a | Admin handler |
| 0xA327 | dispatch_03b3 | Admin helper |
| 0xBC5E | dispatch_0403 | Buffer handler |
| 0xBD76 | dispatch_03b8 | Buffer helper |
| 0xC0A5 | dispatch_0499 | Config handler |
| 0xC65F | dispatch_03d6 | Transfer handler |
| 0xC98D | dispatch_03ef | Completion handler |
| 0xCA52 | dispatch_03e5 | Command handler |
| 0xD440 | dispatch_03d1 | Power handler |
| 0xD556 | dispatch_05ed | Power helper |
| 0xD8D5 | dispatch_05f7 | PCIe handler |
| 0xDA30 | dispatch_03fe | Event handler |
| 0xDAD9 | dispatch_05fc | Event helper |
| 0xDBE7 | dispatch_040d | State handler |
| 0xDD1A | dispatch_03f4 | Command handler |
| 0xDD7E | dispatch_03f9 | Command helper |
| 0xDDE0 | dispatch_03bd | Event dispatch |
| 0xE01F | dispatch_03e0 | PCIe handler |
| 0xE06B | dispatch_0598 | PCIe helper |
| 0xE0D9 | dispatch_057a | PCIe config |
| 0xE12B | dispatch_03c2 | Link handler |
| 0xE175 | dispatch_05d9 | Link helper |
| 0xE1EE | dispatch_060b | Link config |
| 0xE25E | dispatch_061f | Link state |
| 0xE282 | dispatch_05de | PHY handler |
| 0xE2C9 | dispatch_0624 | PHY helper |
| 0xE352 | dispatch_0629 | PHY config |
| 0xE374 | dispatch_062e | PHY state |
| 0xE396 | dispatch_0633 | Timer handler |
| 0xE478 | handler_e478 | Timer helper |
| 0xE496 | dispatch_063d | Timer config |
| 0xE4D2 | dispatch_0647 | Interrupt handler |
| 0xE545 | dispatch_059d | Interrupt helper |
| 0xE561 | dispatch_05b6 | Interrupt config |
| 0xE56F | dispatch_0494 | DMA handler |
| 0xE5CB | dispatch_064c | DMA helper |
| 0xE632 | dispatch_03cc | DMA config |
| 0xE74E | dispatch_05ac | Buffer handler |
| 0xE7FB | dispatch_05c5 | Buffer helper |
| 0xE890 | dispatch_05ca | Buffer config |
| 0xE89B | dispatch_0408 | Completion handler |
| 0xE911 | dispatch_0570 | Init handler |
| 0xEC9B | dispatch_03ea | Queue handler |
| 0xECE1 | dispatch_048a | Queue helper |
| 0xED02 | dispatch_0610 | Queue config |
| 0xEDBD | dispatch_0575 | Admin handler |
| 0xEEF9 | dispatch_0615 | Admin helper |
| 0xEF1E | dispatch_048f | Admin config |
| 0xEF24 | dispatch_0584 | System handler |
| 0xEF3E | dispatch_03ae | System helper |
| 0xEF42 | dispatch_03c7 | System config |
| 0xEF46 | dispatch_03db | Init helper |
| 0xEF4E | dispatch_0642 | Init config |

---

## 3. Major Address Ranges Needing Implementation

### 0x8000-0x8FFF (Bank 0 high / Bank 1 low overlap)

This range is tricky due to bank switching. Some addresses here are bank 0, others are bank 1 entry points.

**Known functions:**
- 0x8A89 - dispatch_04f3 target
- 0x8D77 - dispatch_0525 target
- 0x89DB - Bank1 dispatch_03a9 target

### 0x9900-0x9FFF (Config/State after PCIe state machine)

**Known functions:**
- 0x9980 - helper_9980 (empty stub)
- 0x99bc - helper_99bc (empty stub)
- 0x9983 - helper_9983 (empty stub)
- 0x9C2B - dispatch_0345 target
- 0x9D90 - dispatch_05e8 target (Bank1)

### 0xC000-0xCFFF (PCIe Config / Transfer Handlers)

**Known implemented:**
- 0xC00D - pcie_tunnel_init (in stubs.c)
- 0xC089, 0xC0A5, 0xC105, 0xC17F - Config helpers

**Needing implementation:**
- 0xC4B3, 0xC523, 0xC593 - Queue helpers
- 0xC66A - Transfer helper
- 0xCA0D, 0xCA52 - Command handlers
- 0xCB37 - Completion handler
- 0xCD10, 0xCDC6 - Command dispatch
- 0xCE79 - Transfer handler
- 0xCF7F - Config helper

### 0xD000-0xDFFF (Event/Power/PHY Handlers)

**Known implemented:**
- 0xD1CC - dispatch_05a7 has implementation
- 0xD5A1 - dispatch_05bb (power state)

**Needing implementation:**
- 0xD127 - Event dispatch
- 0xD2BD - DMA handler
- 0xD30B - DMA helper
- 0xD3A2 - Power handler
- 0xD436 - Power helper
- 0xD6BC - PHY handler
- 0xD7CD - PHY config
- 0xD810, 0xD894, 0xD916 - DMA handlers
- 0xD8D5 - PCIe handler (Bank1)
- 0xDA30, 0xDA51, 0xDA8F, 0xDAD9 - Event handlers
- 0xDB80, 0xDBBB, 0xDBE7, 0xDBF5 - State handlers
- 0xDD1A, 0xDD78, 0xDD7E, 0xDDE0 - Command handlers
- 0xDE16, 0xDEE3, 0xDF15 - Event handlers

---

## 4. Recommended Work Order

### Phase 1: High-Impact Empty Stubs
1. `FUN_CODE_dd12` (0xdd12) - Command trigger, referenced by helper_dd12
2. `FUN_CODE_e120` (0xe120) - PCIe helper, referenced by helper_e120
3. `helper_9980`, `helper_99bc` - Config helpers after PCIe state machine
4. USB stubs: `usb_get_xfer_status`, `usb_event_handler`

### Phase 2: SCSI/Protocol Stubs (0x5xxx)
1. `FUN_CODE_5038`, `FUN_CODE_5046`, `FUN_CODE_504f`
2. `FUN_CODE_505d`, `FUN_CODE_5359`
3. Protocol helpers: `helper_3578`, `helper_3adb`

### Phase 3: Memory/State Helpers (0x1xxx)
All 22 functions in this range - these are likely small utility functions.

### Phase 4: Event/DMA Handlers (0xDxxx dispatch targets)
Focus on the 20+ dispatch targets in the 0xD000-0xDFFF range.

### Phase 5: PCIe/Timer Helpers (0xExxx dispatch targets)
Focus on the 40+ dispatch targets in the 0xE000-0xEFFF range.

---

## 5. Files by Function Count

| File | Functions | Notes |
|------|-----------|-------|
| stubs.c | 208 | 66 empty, 142 implemented |
| dispatch.c | 165 | All trampolines to jump_bank |
| usb.c | 150 | Core USB driver |
| nvme.c | 149 | Core NVMe driver |
| pcie.c | 97 | Core PCIe driver |
| scsi.c | 69 | SCSI translation |
| protocol.c | 62 | Protocol state machines |
| queue_handlers.c | 59 | NVMe queue handling |
| cmd.c | 57 | Command processing |
| state_helpers.c | 50 | State machine helpers |
| dma.c | 41 | DMA operations |
| flash.c | 32 | Flash controller |
| power.c | 26 | Power management |
| timer.c | 15 | Timer handling |
| phy.c | 11 | PHY configuration |
| uart.c | 10 | UART/debug |
| error_log.c | 8 | Error logging |
| buffer.c | 7 | Buffer management |

---

## 6. Code Quality Tasks

### Register Naming (Completed ✓)
- All XDATA_REG8 ≥0x6000 now use REG_* names
- All XDATA8 <0x6000 now use G_* names

### Remaining Cleanup
- [ ] Review FUN_CODE_* functions and give proper names once implemented
- [ ] Move implemented stubs to appropriate driver files
- [ ] Consolidate duplicate helper functions

### Build Verification
- Current size: 49,918 / 98,012 bytes (50.9%)
- Target: Match function behavior, not byte-exact matching

---

## Completed Sections ✓

- [x] State Machine Helpers (0x1000-0x1FFF) - mostly done
- [x] Protocol State Machines (0x2000-0x3FFF)
- [x] SCSI/USB Mass Storage (0x4000-0x5FFF) - mostly done
- [x] NVMe Command Engine (0x9000-0x93FF)
- [x] PCIe State Machine Complex (0x9700-0x98FF)
- [x] Queue & Admin Command Handlers (0xA000-0xBFFF) - 97% coverage
- [x] Bank1 High (0xE000-0xFFFF) - mostly done
- [x] Core drivers: pcie.c, nvme.c, usb.c, dma.c, flash.c, phy.c, power.c, timer.c, uart.c
- [x] Utility Functions (0x0000-0x0FFF) - analyzed, none standalone
- [x] Register naming audit
