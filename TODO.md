# ASM2464PD Firmware - TODO

## Progress Summary

| Metric | Value |
|--------|-------|
| **Firmware Size** | 51,904 / 98,012 bytes (53.0%) |
| **Build Status** | Compiles successfully |

---

## Stub Functions in protocol.c

These stub functions need to be implemented:

| Address | Function | Signature |
|---------|----------|-----------|
| 0x1bec | FUN_CODE_1bec | `void (void)` |
| 0x1b30 | FUN_CODE_1b30 | `void (uint8_t param)` |
| 0x1b8d | FUN_CODE_1b8d | `uint8_t (uint8_t param)` |
| 0x1b0b | FUN_CODE_1b0b | `uint8_t (uint8_t param)` |
| 0x1b3f | FUN_CODE_1b3f | `void (uint8_t param)` |
| 0x1c43 | FUN_CODE_1c43 | `void (uint8_t param)` |

---

## TODO Comments by File

### utils.c (4 items)
- Line 26: `pcie_short_delay` - implement 0xbefb
- Line 27: `cmd_engine_wait_idle` - implement 0xb8c3
- Line 28: `link_state_init_stub` - implement 0x9536
- Line 1616: Helper 0x173b behavior

### timer.c (1 item)
- Line 792: `delay_wait_e80a` - timer-based delay implementation

### dma.c (3 items)
- Line 1733: Full DMA logic implementation
- Line 1831: `dma_buffer_store_result_e68f` - requires inline assembly
- Line 1845: Complex DPTR manipulation

### power.c (1 item)
- Line 220: Actual power status check implementation

### usb.c (3 items)
- Line 289, 295: Full logic for USB helpers
- Line 2753: Link dispatch_helper_0534

### nvme.c (18 items)
- Line 1722: Call nvme_helper_4b25(trigger_val)
- Line 1729: Call nvme_helper_3da1(*queue_idx)
- Line 1794: Call 0x0206
- Line 1797: Call 0x3219
- Line 1801: Call 0x312a, 0x31ce
- Line 1813: Call nvme_link_restart
- Line 1839: Call 0x312a, 0x31ce
- Line 1846: Call 0x0206
- Line 1849: Call 0x3219
- Line 1924: Call protocol_setup_params(0x03, 0x47, 0x0B)
- Line 1933: Call dma_interrupt_handler()
- Line 1938: Result = call_0395()
- Line 1958: Call helper_4eb3(0, *queue_idx)
- Line 1961: Call helper_46f8(0, *queue_idx)
- Line 2033: Call protocol_setup_params(0x03, 0x47, 0x0B)
- Line 2054: Call dma_interrupt_handler()
- Line 2089: Alternate path at 0x19FA
- Line 2101: Implement helper_04da

### flash.c (4 items)
- Line 629: Reverse engineer address
- Line 651: Reverse engineer address
- Line 678: Reverse engineer address
- Line 704: Reverse engineer address

### protocol.c (10 items)
- Line 980: Table copy loop at 0x0296-0x02b0
- Line 988: Calls to 0x3133, 0x31c5, 0x3249
- Line 1021: Full implementation requirements
- Line 1361: Transfer logic from 0x11a2
- Line 1374: Buffer setup from 0x5359
- Line 1385: Status check from 0x1cd4
- Line 1397: Register setup from 0x1cc8
- Line 1619: Callback check from 0x043f
- Line 1632: Transfer setup from 0x36ab
- Line 1675: Compare logic from 0x322e

### scsi.c (3 items)
- Line 577: dptr_setup_stub() call
- Line 2503: Detailed reverse engineering needed
- Line 2891: SCSI command state machine

### pcie.c (7 items)
- Line 2200-2222: NVMe command setup functions
- Line 2268-2286: Queue helper functions
- Line 2327-2358: Queue increment and NVMe handlers
- Line 2748: Call to 0x05C5
- Line 3700, 3707: Helper_bd14/bcf2 calls
- Line 4047: Completion handler stub
- Line 4160: Simplified stub

### cmd.c (2 items)
- Line 520: Full implementation requires cmd_param_setup
- Line 1585: Bank 1 function at 0xe77a

### error_log.c (3 items)
- Line 322: Original calls helper at 0xd1a8
- Line 397: Complex error handler stub
- Line 417: Complex error handler stub

### queue_handlers.c (1 item)
- Line 910: Simplified stub using DPTR directly

---

## Extern Declarations in .c Files

~410 extern declarations in .c files that should ideally be in headers:

### High-traffic externs (used by multiple files)

**From cmd.c:**
- `cmd_param_setup(uint8_t, uint8_t)` - 0xe120
- `cmd_trigger_params(uint8_t, uint8_t)`
- `cmd_engine_clear(void)`

**From usb.c:**
- `usb_buffer_dispatch(void)`
- `nvme_func_04da(uint8_t param)`
- `protocol_setup_params(uint8_t, uint8_t, uint8_t)` - 0x523c
- `scsi_core_dispatch(uint8_t param)` - 0x4ff2
- `dma_queue_state_handler(void)` - 0x2608

**From flash.c:**
- `flash_func_0bc8(uint8_t param)` - 0x0bc8
- `uart_write_byte_daeb(void)`
- `uart_read_byte_dace(uint8_t offset)`

**From power.c:**
- `usb_mode_config_d07f(uint8_t param)`
- `nvme_queue_config_e214(void)`
- `pcie_clear_address_regs(void)` - 0x9a9c
- `helper_e3b7(uint8_t param)` - 0xe3b7

---

## Build Warnings to Address

- `helper_95af` implicit declaration (cmd.c:2104)
- `reg_timer_clear_bits` and `reg_timer_setup_and_set_bits` implicit declarations (pcie.c:4276, 4282)

---

## Notes

- SDCC generates different code than the original Keil C51 compiler
- Byte-exact matching is not possible; function-level correctness is the goal
- Registers >= 0x6000 use REG_* prefix in registers.h
- Globals < 0x6000 use G_* prefix in globals.h
