/*
 * ASM2464PD Firmware - NVMe Driver
 *
 * NVMe controller interface for USB4/Thunderbolt to NVMe bridge.
 * Handles NVMe command submission, completion, and queue management.
 *
 *===========================================================================
 * NVME CONTROLLER ARCHITECTURE
 *===========================================================================
 *
 * The ASM2464PD bridges USB4/Thunderbolt/USB to PCIe NVMe SSDs.
 * This driver manages the NVMe command/completion queues and data transfers.
 *
 * Block Diagram:
 * ┌───────────────────────────────────────────────────────────────────────┐
 * │                        NVMe SUBSYSTEM                                │
 * ├───────────────────────────────────────────────────────────────────────┤
 * │                                                                       │
 * │  USB/PCIe ──> SCSI Cmd ──> NVMe Cmd Builder ──> Submission Queue     │
 * │      │                          │                     │               │
 * │      │                          v                     v               │
 * │      │                    ┌──────────┐          ┌──────────┐          │
 * │      │                    │ NVMe Regs│          │ PCIe DMA │          │
 * │      │                    │ 0xC400+  │          │ Engine   │          │
 * │      │                    └──────────┘          └────┬─────┘          │
 * │      │                                               │               │
 * │      │                                               v               │
 * │      <───── SCSI Status <── NVMe Completion <── Completion Queue     │
 * │                                                                       │
 * └───────────────────────────────────────────────────────────────────────┘
 *
 * Register Map (0xC400-0xC5FF):
 * ┌──────────┬───────────────────────────────────────────────────────────┐
 * │ Address  │ Description                                               │
 * ├──────────┼───────────────────────────────────────────────────────────┤
 * │ 0xC400   │ NVME_CTRL - Control register                              │
 * │ 0xC401   │ NVME_STATUS - Status register                             │
 * │ 0xC412   │ NVME_CTRL_STATUS - Control/status combined                │
 * │ 0xC413   │ NVME_CONFIG - Configuration                               │
 * │ 0xC414   │ NVME_DATA_CTRL - Data transfer control                    │
 * │ 0xC415   │ NVME_DEV_STATUS - Device presence/ready status            │
 * │ 0xC420   │ NVME_CMD - Command register                               │
 * │ 0xC421   │ NVME_CMD_OPCODE - NVMe opcode                              │
 * │ 0xC422-24│ NVME_LBA_0/1/2 - LBA bytes 0-2                            │
 * │ 0xC425-26│ NVME_COUNT - Transfer count                               │
 * │ 0xC427   │ NVME_ERROR - Error code                                   │
 * │ 0xC428   │ NVME_QUEUE_CFG - Queue configuration                      │
 * │ 0xC429   │ NVME_CMD_PARAM - Command parameters                       │
 * │ 0xC42A   │ NVME_DOORBELL - Queue doorbell                            │
 * │ 0xC440-45│ Queue head/tail pointers                                  │
 * │ 0xC446   │ NVME_LBA_3 - LBA byte 3                                   │
 * │ 0xC462   │ DMA_ENTRY - DMA entry point                               │
 * │ 0xC470-7F│ Command queue directory                                   │
 * └──────────┴───────────────────────────────────────────────────────────┘
 *
 * NVMe Event Registers (0xEC00-0xEC0F):
 * ┌──────────┬───────────────────────────────────────────────────────────┐
 * │ 0xEC04   │ NVME_EVENT_ACK - Event acknowledge                        │
 * │ 0xEC06   │ NVME_EVENT_STATUS - Event status                          │
 * └──────────┴───────────────────────────────────────────────────────────┘
 *
 * Queue Management:
 * - Submission Queue (SQ): Commands sent to NVMe device
 * - Completion Queue (CQ): Status returned from NVMe device
 * - Circular buffer with head/tail pointers
 * - Phase bit for completion tracking
 * - Maximum 32 outstanding commands (5-bit counter)
 *
 * SCSI DMA Registers (0xCE40-0xCEFF):
 * - Used for NVMe data transfers
 * - 0xCE88-CE89: SCSI DMA control/status
 * - 0xCEB0: Transfer status
 *
 *===========================================================================
 * IMPLEMENTATION STATUS
 *===========================================================================
 * nvme_set_usb_mode_bit      [DONE] 0x1bde-0x1be7 - Set USB mode bit
 * nvme_get_config_offset     [DONE] 0x1be8-0x1bf5 - Get config offset
 * nvme_calc_buffer_offset    [DONE] 0x1bf6-0x1c0e - Calculate buffer offset
 * nvme_load_transfer_data    [DONE] 0x1bcb-0x1bd4 - Load transfer data
 * nvme_calc_idata_offset     [DONE] 0x1c0f-0x1c1a - Calculate IDATA offset
 * nvme_check_scsi_ctrl       [DONE] 0x1c22-0x1c29 - Check SCSI control
 * nvme_get_cmd_param_upper   [DONE] 0x1c77-0x1c7d - Get cmd param upper bits
 * nvme_subtract_idata_16     [DONE] 0x1c6d-0x1c76 - Subtract 16-bit value
 * nvme_calc_addr_01xx        [DONE] 0x1c88-0x1c8f - Calculate 0x01XX addr
 * nvme_inc_circular_counter  [DONE] 0x1cae-0x1cb6 - Increment circular counter
 * nvme_calc_addr_012b        [DONE] 0x1cb7-0x1cc0 - Calculate 0x012B+ addr
 * nvme_set_ep_queue_ctrl_84  [DONE] 0x1cc1-0x1cc7 - Set EP queue ctrl
 * nvme_get_dev_status_upper  [DONE] 0x1c56-0x1c5c - Get device status upper
 * nvme_get_data_ctrl_upper   [DONE] 0x1d24-0x1d2a - Get data ctrl upper bits
 * nvme_clear_status_bit1     [DONE] 0x1cd4-0x1cdb - Clear status bit 1
 * nvme_set_data_ctrl_bit7    [DONE] 0x1d2b-0x1d31 - Set data ctrl bit 7
 * nvme_store_idata_16        [DONE] 0x1d32-0x1d38 - Store 16-bit to IDATA
 * nvme_calc_addr_04b7        [DONE] 0x1ce4-0x1cef - Calculate 0x04B7+ addr
 * nvme_add_to_global_053a    [DONE] 0x1cdc-0x1ce3 - Add 0x20 to global 0x053A
 *
 * Total: 19 functions implemented
 *===========================================================================
 *
 * NOTE: Core dispatch functions (jump_bank_0, jump_bank_1)
 * are defined in main.c as they are part of the core dispatch mechanism.
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"
#include "globals.h"

/*
 * nvme_set_usb_mode_bit - Set USB mode bit 0 of register 0x9006
 * Address: 0x1bde-0x1be7 (10 bytes)
 *
 * Reads 0x9006, clears bit 0, sets bit 0, writes back.
 *
 * Original disassembly:
 *   1bde: mov dptr, #0x9006
 *   1be1: movx a, @dptr
 *   1be2: anl a, #0xfe        ; clear bit 0
 *   1be4: orl a, #0x01        ; set bit 0
 *   1be6: movx @dptr, a
 *   1be7: ret
 */
void nvme_set_usb_mode_bit(void)
{
    uint8_t val;

    val = REG_USB_EP0_CONFIG;
    val = (val & 0xFE) | 0x01;
    REG_USB_EP0_CONFIG = val;
}

/*
 * nvme_get_config_offset - Get configuration offset address
 * Address: 0x1be8-0x1bf5 (14 bytes)
 *
 * Reads from 0x0464, adds 0x56 to form address in 0x04XX region,
 * and returns that address.
 *
 * Original disassembly:
 *   1be8: mov dptr, #0x0464
 *   1beb: movx a, @dptr       ; A = XDATA[0x0464]
 *   1bec: add a, #0x56        ; A = A + 0x56
 *   1bee: mov 0x82, a         ; DPL = A
 *   1bf0: clr a
 *   1bf1: addc a, #0x04       ; DPH = 0x04 + carry
 *   1bf3: mov 0x83, a
 *   1bf5: ret                 ; returns with DPTR = 0x04XX
 */
__xdata uint8_t *nvme_get_config_offset(void)
{
    uint8_t val = G_SYS_STATUS_PRIMARY;
    uint16_t addr = 0x0400 + val + 0x56;
    return (__xdata uint8_t *)addr;
}

/*
 * nvme_calc_buffer_offset - Calculate buffer offset with multiplier
 * Address: 0x1bf6-0x1c0e (25 bytes)
 *
 * Multiplies input by 0x40, adds to values from 0x021A-0x021B,
 * and stores result to 0x0568-0x0569.
 *
 * Original disassembly:
 *   1bf6: mov 0xf0, #0x40     ; B = 0x40
 *   1bf9: mul ab              ; A*B, result in B:A
 *   1bfa: mov r7, a           ; R7 = low byte
 *   1bfb: mov dptr, #0x021b
 *   1bfe: movx a, @dptr       ; A = XDATA[0x021B]
 *   1bff: add a, r7           ; A = A + R7
 *   1c00: mov r6, a           ; R6 = low result
 *   1c01: mov dptr, #0x021a
 *   1c04: movx a, @dptr       ; A = XDATA[0x021A]
 *   1c05: addc a, 0xf0        ; A = A + B + carry
 *   1c07: mov dptr, #0x0568
 *   1c0a: movx @dptr, a       ; XDATA[0x0568] = high byte
 *   1c0b: inc dptr
 *   1c0c: xch a, r6
 *   1c0d: movx @dptr, a       ; XDATA[0x0569] = low byte
 *   1c0e: ret
 */
void nvme_calc_buffer_offset(uint8_t index)
{
    uint16_t offset;
    uint16_t base;
    uint16_t result;

    /* Calculate offset = index * 0x40 */
    offset = (uint16_t)index * 0x40;

    /* Read base address (big-endian) */
    base = G_BUF_BASE_HI;
    base = (base << 8) | G_BUF_BASE_LO;

    /* Calculate result = base + offset */
    result = base + offset;

    /* Store result (big-endian) */
    G_BUF_OFFSET_HI = (uint8_t)(result >> 8);
    G_BUF_OFFSET_LO = (uint8_t)(result & 0xFF);
}

/*
 * nvme_load_transfer_data - Load transfer data from IDATA
 * Address: 0x1bcb-0x1bd4 (10 bytes)
 *
 * Loads 32-bit value from IDATA[0x6B] and stores to IDATA[0x6F].
 *
 * Original disassembly:
 *   1bcb: mov r0, #0x6b
 *   1bcd: lcall 0x0d78        ; idata_load_dword
 *   1bd0: mov r0, #0x6f
 *   1bd2: ljmp 0x0db9         ; idata_store_dword
 */
void nvme_load_transfer_data(void)
{
    uint32_t val;

    /* Load from IDATA[0x6B] */
    val = ((__idata uint8_t *)0x6B)[0];
    val |= ((uint32_t)((__idata uint8_t *)0x6B)[1]) << 8;
    val |= ((uint32_t)((__idata uint8_t *)0x6B)[2]) << 16;
    val |= ((uint32_t)((__idata uint8_t *)0x6B)[3]) << 24;

    /* Store to IDATA[0x6F] */
    ((__idata uint8_t *)0x6F)[0] = (uint8_t)(val & 0xFF);
    ((__idata uint8_t *)0x6F)[1] = (uint8_t)((val >> 8) & 0xFF);
    ((__idata uint8_t *)0x6F)[2] = (uint8_t)((val >> 16) & 0xFF);
    ((__idata uint8_t *)0x6F)[3] = (uint8_t)((val >> 24) & 0xFF);
}

/*
 * nvme_calc_idata_offset - Calculate address from IDATA offset
 * Address: 0x1c0f-0x1c1a (12 bytes)
 *
 * Returns pointer to 0x000C + IDATA[0x3C].
 *
 * Original disassembly:
 *   1c0f: mov a, #0x0c
 *   1c11: add a, 0x3c         ; A = 0x0C + IDATA[0x3C]
 *   1c13: mov 0x82, a         ; DPL
 *   1c15: clr a
 *   1c16: addc a, #0x00       ; DPH = carry
 *   1c18: mov 0x83, a
 *   1c1a: ret
 */
__xdata uint8_t *nvme_calc_idata_offset(void)
{
    uint8_t offset = *(__idata uint8_t *)0x3C;
    return (__xdata uint8_t *)(0x000C + offset);
}

/*
 * nvme_check_scsi_ctrl - Check SCSI control status
 * Address: 0x1c22-0x1c29 (8 bytes, after store)
 *
 * Reads SCSI control from 0x0171 and checks if non-zero.
 * Returns with carry set if value is zero.
 *
 * Original disassembly:
 *   1c22: mov dptr, #0x0171
 *   1c25: movx a, @dptr       ; A = G_SCSI_CTRL
 *   1c26: setb c
 *   1c27: subb a, #0x00       ; compare with 0
 *   1c29: ret
 */
uint8_t nvme_check_scsi_ctrl(void)
{
    return (G_SCSI_CTRL != 0) ? 1 : 0;
}

/*
 * nvme_get_cmd_param_upper - Get upper 3 bits of NVMe command param
 * Address: 0x1c77-0x1c7d (7 bytes)
 *
 * Reads NVMe command parameter and masks to upper 3 bits.
 *
 * Original disassembly:
 *   1c77: mov dptr, #0xc429
 *   1c7a: movx a, @dptr       ; A = REG_NVME_CMD_PARAM
 *   1c7b: anl a, #0xe0        ; mask bits 7-5
 *   1c7d: ret
 */
uint8_t nvme_get_cmd_param_upper(void)
{
    return REG_NVME_CMD_PARAM & 0xE0;
}

/*
 * nvme_subtract_idata_16 - Subtract 16-bit value from IDATA[0x16:0x17]
 * Address: 0x1c6d-0x1c76 (10 bytes)
 *
 * Subtracts R6:R7 from the 16-bit value at IDATA[0x16:0x17].
 *
 * Original disassembly:
 *   1c6d: mov r0, #0x17
 *   1c6f: mov a, @r0          ; A = IDATA[0x17]
 *   1c70: subb a, r7          ; A = A - R7 - C
 *   1c71: mov @r0, a          ; IDATA[0x17] = A
 *   1c72: dec r0
 *   1c73: mov a, @r0          ; A = IDATA[0x16]
 *   1c74: subb a, r6          ; A = A - R6 - C
 *   1c75: mov @r0, a          ; IDATA[0x16] = A
 *   1c76: ret
 */
void nvme_subtract_idata_16(uint8_t hi, uint8_t lo)
{
    uint16_t val = ((*(__idata uint8_t *)0x16) << 8) | (*(__idata uint8_t *)0x17);
    uint16_t sub = ((uint16_t)hi << 8) | lo;
    val -= sub;
    *(__idata uint8_t *)0x16 = (uint8_t)(val >> 8);
    *(__idata uint8_t *)0x17 = (uint8_t)(val & 0xFF);
}

/*
 * nvme_calc_addr_01xx - Calculate address in 0x01XX region
 * Address: 0x1c88-0x1c8f (8 bytes)
 *
 * Returns pointer to 0x0100 + input value.
 *
 * Original disassembly:
 *   1c88: mov 0x82, a         ; DPL = A
 *   1c8a: clr a
 *   1c8b: addc a, #0x01       ; DPH = 0x01 + carry
 *   1c8d: mov 0x83, a
 *   1c8f: ret
 */
__xdata uint8_t *nvme_calc_addr_01xx(uint8_t offset)
{
    return (__xdata uint8_t *)(0x0100 + offset);
}

/*
 * nvme_inc_circular_counter - Increment circular counter at 0x0B00
 * Address: 0x1cae-0x1cb6 (9 bytes)
 *
 * Reads counter, increments, masks to 5 bits (0-31 range), writes back.
 *
 * Original disassembly:
 *   1cae: mov dptr, #0x0b00
 *   1cb1: movx a, @dptr       ; read counter
 *   1cb2: inc a               ; increment
 *   1cb3: anl a, #0x1f        ; mask to 5 bits
 *   1cb5: movx @dptr, a       ; write back
 *   1cb6: ret
 */
void nvme_inc_circular_counter(void)
{
    uint8_t val = XDATA8(0x0B00);
    val = (val + 1) & 0x1F;
    XDATA8(0x0B00) = val;
}

/*
 * nvme_calc_addr_012b - Calculate address in 0x012B+ region
 * Address: 0x1cb7-0x1cc0 (10 bytes)
 *
 * Returns pointer to 0x012B + input value.
 *
 * Original disassembly:
 *   1cb7: add a, #0x2b
 *   1cb9: mov 0x82, a         ; DPL
 *   1cbb: clr a
 *   1cbc: addc a, #0x01       ; DPH = 0x01 + carry
 *   1cbe: mov 0x83, a
 *   1cc0: ret
 */
__xdata uint8_t *nvme_calc_addr_012b(uint8_t offset)
{
    return (__xdata uint8_t *)(0x012B + offset);
}

/*
 * nvme_set_ep_queue_ctrl_84 - Set endpoint queue control to 0x84
 * Address: 0x1cc1-0x1cc7 (7 bytes)
 *
 * Sets G_EP_QUEUE_CTRL to 0x84 (busy flag set).
 *
 * Original disassembly:
 *   1cc1: mov dptr, #0x0564
 *   1cc4: mov a, #0x84
 *   1cc6: movx @dptr, a       ; G_EP_QUEUE_CTRL = 0x84
 *   1cc7: ret
 */
void nvme_set_ep_queue_ctrl_84(void)
{
    G_EP_QUEUE_CTRL = 0x84;
}

/*
 * nvme_get_dev_status_upper - Get upper 2 bits of device status
 * Address: 0x1c56-0x1c5c (7 bytes)
 *
 * Reads NVMe device status register and masks to upper 2 bits.
 * These bits indicate device presence and ready state.
 *
 * Original disassembly:
 *   1c56: mov dptr, #0xc415   ; REG_NVME_DEV_STATUS
 *   1c59: movx a, @dptr       ; read status
 *   1c5a: anl a, #0xc0        ; mask bits 7-6
 *   1c5c: ret
 */
uint8_t nvme_get_dev_status_upper(void)
{
    return REG_NVME_DEV_STATUS & 0xC0;
}

/*
 * nvme_get_data_ctrl_upper - Get upper 2 bits of data control
 * Address: 0x1d24-0x1d2a (7 bytes)
 *
 * Reads NVMe data control register and masks to upper 2 bits.
 *
 * Original disassembly:
 *   1d24: mov dptr, #0xc414   ; REG_NVME_DATA_CTRL
 *   1d27: movx a, @dptr       ; read control
 *   1d28: anl a, #0xc0        ; mask bits 7-6
 *   1d2a: ret
 */
uint8_t nvme_get_data_ctrl_upper(void)
{
    return REG_NVME_DATA_CTRL & 0xC0;
}

/*
 * nvme_clear_status_bit1 - Clear bit 1 of NVMe status register
 * Address: 0x1cd4-0x1cdb (8 bytes)
 *
 * Reads status, clears bit 1, writes back.
 * Bit 1 is typically an error/interrupt flag.
 *
 * Original disassembly:
 *   1cd4: mov dptr, #0xc401   ; REG_NVME_STATUS
 *   1cd7: movx a, @dptr       ; read status
 *   1cd8: anl a, #0xfd        ; clear bit 1
 *   1cda: movx @dptr, a       ; write back
 *   1cdb: ret
 */
void nvme_clear_status_bit1(void)
{
    uint8_t val = REG_NVME_STATUS;
    val &= 0xFD;
    REG_NVME_STATUS = val;
}

/*
 * nvme_set_data_ctrl_bit7 - Set bit 7 of data control register
 * Address: 0x1d2b-0x1d31 (7 bytes)
 *
 * Reads from DPTR (caller sets it), clears bit 7, sets bit 7, writes back.
 * This is called after nvme_get_data_ctrl_upper with DPTR still pointing
 * to 0xC414.
 *
 * Original disassembly:
 *   1d2b: movx a, @dptr       ; read current value
 *   1d2c: anl a, #0x7f        ; clear bit 7
 *   1d2e: orl a, #0x80        ; set bit 7
 *   1d30: movx @dptr, a       ; write back
 *   1d31: ret
 */
void nvme_set_data_ctrl_bit7(void)
{
    uint8_t val = REG_NVME_DATA_CTRL;
    val = (val & 0x7F) | 0x80;
    REG_NVME_DATA_CTRL = val;
}

/*
 * nvme_store_idata_16 - Store 16-bit value to IDATA[0x16:0x17]
 * Address: 0x1d32-0x1d38 (7 bytes)
 *
 * Stores R6:R7 (hi:lo) to IDATA[0x16:0x17].
 *
 * Original disassembly:
 *   1d32: mov r1, #0x17
 *   1d34: mov @r1, a          ; store low byte (A = R7)
 *   1d35: mov a, r6           ; get high byte
 *   1d36: dec r1              ; point to 0x16
 *   1d37: mov @r1, a          ; store high byte
 *   1d38: ret
 */
void nvme_store_idata_16(uint8_t hi, uint8_t lo)
{
    *(__idata uint8_t *)0x17 = lo;
    *(__idata uint8_t *)0x16 = hi;
}

/*
 * nvme_calc_addr_04b7 - Calculate address in 0x04B7+ region
 * Address: 0x1ce4-0x1cef (12 bytes)
 *
 * Returns pointer to 0x04B7 + IDATA[0x23].
 *
 * Original disassembly:
 *   1ce4: mov a, #0xb7
 *   1ce6: add a, 0x23         ; A = 0xB7 + IDATA[0x23]
 *   1ce8: mov 0x82, a         ; DPL
 *   1cea: clr a
 *   1ceb: addc a, #0x04       ; DPH = 0x04 + carry
 *   1ced: mov 0x83, a
 *   1cef: ret
 */
__xdata uint8_t *nvme_calc_addr_04b7(void)
{
    uint8_t offset = *(__idata uint8_t *)0x23;
    uint16_t addr = 0x04B7 + offset;
    return (__xdata uint8_t *)addr;
}

/*
 * nvme_add_to_global_053a - Add 0x20 to value at 0x053A
 * Address: 0x1cdc-0x1ce3 (8 bytes)
 *
 * Reads value from 0x053A, adds 0x20, writes back.
 *
 * Original disassembly:
 *   1cdc: mov dptr, #0x053a
 *   1cdf: movx a, @dptr       ; read value
 *   1ce0: add a, #0x20        ; add 0x20
 *   1ce2: movx @dptr, a       ; write back
 *   1ce3: ret
 */
void nvme_add_to_global_053a(void)
{
    uint8_t val = XDATA8(0x053A);
    val += 0x20;
    XDATA8(0x053A) = val;
}
