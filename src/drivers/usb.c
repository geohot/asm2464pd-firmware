/*
 * ASM2464PD Firmware - USB Driver
 *
 * USB interface controller for USB4/Thunderbolt to NVMe bridge
 * Handles USB enumeration, endpoint configuration, and data transfers
 *
 * USB registers are at 0x9000-0x91FF
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"
#include "globals.h"

/* External utility functions from utils.c */
extern uint32_t idata_load_dword(__idata uint8_t *ptr);
extern uint32_t idata_load_dword_alt(__idata uint8_t *ptr);

/*
 * usb_enable - Enable USB interface
 * Address: 0x1b7e-0x1b87 (10 bytes)
 *
 * Loads configuration parameters from internal RAM addresses 0x09 and 0x6b.
 * Returns two 32-bit values in R4-R7 and R0-R3 to caller.
 *
 * Original disassembly:
 *   1b7e: mov r0, #0x09
 *   1b80: lcall 0x0d78       ; idata_load_dword (loads IDATA[0x09-0x0c] to R4-R7)
 *   1b83: mov r0, #0x6b
 *   1b85: ljmp 0x0d90        ; idata_load_dword_alt (loads IDATA[0x6b-0x6e] to R0-R3)
 */
void usb_enable(void)
{
    idata_load_dword((__idata uint8_t *)0x09);
    idata_load_dword_alt((__idata uint8_t *)0x6b);
}

/*
 * usb_setup_endpoint - Configure USB endpoint
 * Address: 0x1bd7-0x???? (needs analysis)
 *
 * From ghidra.c usb_setup_endpoint:
 *   Configures endpoint parameters
 */
void usb_setup_endpoint(void)
{
    /* TODO: Implement based on 0x1bd7 disassembly */
}

/*===========================================================================
 * Endpoint Dispatch Tables
 * Address: 0x5a6a, 0x5b6a, 0x5b72 in CODE memory
 *===========================================================================*/

/*
 * Endpoint index mapping table
 * Address: 0x5a6a (256 bytes)
 *
 * Maps USB status byte values to endpoint indices (0-7).
 * Value >= 8 means "no endpoint to process" (exit loop).
 * Pattern repeats: 08 00 01 00 02 00 01 00 03 00 01 00 02 00 01 00
 *                  04 00 01 00 02 00 01 00 03 00 01 00 02 00 01 00
 *                  05 00 01 00 02 00 01 00 03 00 01 00 02 00 01 00
 *                  04 00 01 00 02 00 01 00 03 00 01 00 02 00 01 00
 *                  ... repeats for 256 entries
 */
static const __code uint8_t ep_index_table[256] = {
    /* 0x00-0x0F */
    0x08, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x10-0x1F */
    0x04, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x20-0x2F */
    0x05, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x30-0x3F */
    0x04, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x40-0x4F */
    0x06, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x50-0x5F */
    0x04, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x60-0x6F */
    0x05, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x70-0x7F */
    0x04, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x80-0x8F */
    0x07, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0x90-0x9F */
    0x04, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0xA0-0xAF */
    0x05, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0xB0-0xBF */
    0x04, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0xC0-0xCF */
    0x06, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0xD0-0xDF */
    0x04, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0xE0-0xEF */
    0x05, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    /* 0xF0-0xFF */
    0x04, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x03, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01, 0x00
};

/*
 * Endpoint bit mask table
 * Address: 0x5b6a (8 bytes)
 *
 * Maps endpoint index (0-7) to bit mask for status clear.
 */
static const __code uint8_t ep_bit_mask_table[8] = {
    0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80
};

/*
 * Endpoint offset table
 * Address: 0x5b72 (8 bytes)
 *
 * Maps endpoint index (0-7) to register offset (multiples of 8).
 */
static const __code uint8_t ep_offset_table[8] = {
    0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38
};

/*===========================================================================
 * USB Endpoint XDATA Addresses
 *===========================================================================*/

/* USB endpoint register base at 0x9096 (indexed by endpoint) */
#define REG_USB_EP_BASE     0x9096

/*===========================================================================
 * Endpoint Handler Forward Declaration
 *===========================================================================*/

/*
 * usb_ep_init_handler - USB endpoint initialization sub-handler
 * Address: 0x5409-0x5417 (15 bytes)
 *
 * Clears various state flags and dispatches to buffer handler at 0xD810.
 *
 * Original disassembly:
 *   5409: clr a               ; A = 0
 *   540a: mov dptr, #0x0b2e
 *   540d: movx @dptr, a       ; XDATA[0x0B2E] = 0
 *   540e: mov r0, #0x6a
 *   5410: mov @r0, a          ; IDATA[0x6A] = 0
 *   5411: mov dptr, #0x06e6
 *   5414: movx @dptr, a       ; XDATA[0x06E6] = 0
 *   5415: ljmp 0x039a         ; dispatch to 0xD810
 */
static void usb_ep_init_handler(void)
{
    /* Clear state variables in work area */
    G_USB_TRANSFER_FLAG = 0;

    /* Clear IDATA[0x6A] */
    *(__idata uint8_t *)0x6A = 0;

    /* Clear processing complete flag in work area */
    G_STATE_FLAG_06E6 = 0;

    /* Original jumps to 0x039a which dispatches to 0xD810 (buffer handler) */
    /* TODO: Call buffer handler */
}

/*
 * usb_ep_handler - Process single USB endpoint
 * Address: 0x5442-0x544b (10 bytes)
 *
 * Called from endpoint dispatch loop to process a single endpoint.
 * Checks XDATA[0x000A] and conditionally calls 0x5409.
 *
 * Original disassembly:
 *   5442: mov dptr, #0x000a
 *   5445: movx a, @dptr
 *   5446: jnz 0x544b          ; if non-zero, return
 *   5448: lcall 0x5409
 *   544b: ret
 */
static void usb_ep_handler(void)
{
    if (G_EP_CHECK_FLAG == 0) {
        usb_ep_init_handler();
    }
}

/*===========================================================================
 * Table-Driven Endpoint Dispatch
 *===========================================================================*/

/*
 * usb_ep_dispatch_loop - USB endpoint processing loop
 * Address: 0x0e96-0x0efb (101 bytes)
 *
 * Main USB endpoint dispatch loop that iterates up to 32 times,
 * reading endpoint status and dispatching to handlers.
 *
 * Algorithm:
 * 1. For counter = 0 to 31:
 *    a. Read USB status from 0x9118
 *    b. Look up endpoint index via ep_index_table
 *    c. If index >= 8, exit loop (no more endpoints to process)
 *    d. Read secondary status from 0x9096 + first_index
 *    e. Look up second endpoint index
 *    f. If second_index >= 8, exit loop
 *    g. Calculate combined offset and store to 0x0AF5
 *    h. Call endpoint handler at 0x5442
 *    i. Write bit mask to clear endpoint status
 *
 * Original disassembly:
 *   0e96: mov 0x37, #0x00     ; counter = 0
 *   0e99: mov dptr, #0x9118   ; USB status
 *   0e9c: movx a, @dptr       ; read status
 *   0e9d: mov dptr, #0x5a6a   ; index table
 *   0ea0: movc a, @a+dptr     ; lookup
 *   0ea1: mov dptr, #0x0a7b
 *   0ea4: movx @dptr, a       ; store index1
 *   ... (see full analysis above)
 *   0ef9: jc 0x0e99           ; loop if counter < 32
 */
/*===========================================================================
 * Buffer Handler (0xD810)
 *===========================================================================*/

/*
 * usb_buffer_handler - Buffer transfer dispatch handler
 * Address: 0xd810-0xd851 (66 bytes)
 *
 * Complex handler that checks various status flags and configures
 * timer registers for buffer operations.
 *
 * Original disassembly:
 *   d810: mov dptr, #0x0b41
 *   d813: movx a, @dptr
 *   d814: jz 0xd851           ; if 0, return
 *   d816: mov dptr, #0x9091
 *   d819: movx a, @dptr
 *   d81a: jb 0xe0.0, 0xd851   ; if bit 0 set, return
 *   d81d: mov dptr, #0x07e4
 *   d820: movx a, @dptr
 *   d821: xrl a, #0x01
 *   d823: jnz 0xd851          ; if != 1, return
 *   d825: mov dptr, #0x9000
 *   d828: movx a, @dptr
 *   d829: jnb 0xe0.0, 0xd83a  ; if bit 0 clear, skip to 0xd83a
 *   d82c: mov dptr, #0xc471
 *   d82f: movx a, @dptr
 *   d830: jb 0xe0.0, 0xd851   ; if bit 0 set, return
 *   d833: mov dptr, #0x000a
 *   d836: movx a, @dptr
 *   d837: jz 0xd846           ; if 0, skip to 0xd846
 *   d839: ret                 ; early return
 *   d83a: mov dptr, #0x9101
 *   d83d: movx a, @dptr
 *   d83e: jb 0xe0.6, 0xd851   ; if bit 6 set, return
 *   d841: mov r0, #0x6a
 *   d843: mov a, @r0
 *   d844: jnz 0xd851          ; if IDATA[0x6A] != 0, return
 *   d846: mov dptr, #0xcc17   ; Timer 1 CSR
 *   d849: mov a, #0x04
 *   d84b: movx @dptr, a       ; Write 0x04
 *   d84c: mov a, #0x02
 *   d84e: movx @dptr, a       ; Write 0x02
 *   d84f: dec a               ; A = 0x01
 *   d850: movx @dptr, a       ; Write 0x01
 *   d851: ret
 */
void usb_buffer_handler(void)
{
    uint8_t status;

    /* Check XDATA[0x0B41] */
    if (XDATA8(0x0B41) == 0) {
        return;
    }

    /* Check USB interrupt flags bit 0 */
    status = REG_INT_FLAGS_EX0;
    if (status & 0x01) {
        return;
    }

    /* Check flags base - must be 1 */
    if (G_SYS_FLAGS_BASE != 1) {
        return;
    }

    /* Check USB status bit 0 */
    status = REG_USB_STATUS;
    if (status & 0x01) {
        /* USB status bit 0 set - check NVMe queue pointer */
        status = XDATA8(0xC471);  /* REG_NVME_QUEUE_PTR area */
        if (status & 0x01) {
            return;
        }

        /* Check endpoint check flag */
        if (G_EP_CHECK_FLAG != 0) {
            return;  /* Early return */
        }
    } else {
        /* USB status bit 0 clear - check USB peripheral status */
        status = REG_USB_PERIPH_STATUS;
        if (status & 0x40) {  /* Bit 6 */
            return;
        }

        /* Check IDATA[0x6A] */
        if (*(__idata uint8_t *)0x6A != 0) {
            return;
        }
    }

    /* Configure Timer 1 CSR with sequence: 0x04, 0x02, 0x01 */
    REG_TIMER1_CSR = 0x04;
    REG_TIMER1_CSR = 0x02;
    REG_TIMER1_CSR = 0x01;
}

/*===========================================================================
 * USB Endpoint Configuration Functions
 *===========================================================================*/

/*
 * usb_ep_config_bulk - Configure endpoint for bulk transfer
 * Address: 0x1cfc-0x1d06 (11 bytes)
 *
 * Sets USB endpoint registers 0x9093 and 0x9094 for bulk transfer config.
 *
 * Original disassembly:
 *   1cfc: mov dptr, #0x9093
 *   1cff: mov a, #0x08
 *   1d01: movx @dptr, a      ; XDATA[0x9093] = 0x08
 *   1d02: inc dptr
 *   1d03: mov a, #0x02
 *   1d05: movx @dptr, a      ; XDATA[0x9094] = 0x02
 *   1d06: ret
 */
void usb_ep_config_bulk(void)
{
    REG_USB_EP_CFG1 = 0x08;
    REG_USB_EP_CFG2 = 0x02;
}

/*
 * usb_ep_config_int - Configure endpoint for interrupt transfer
 * Address: 0x1d07-0x1d11 (11 bytes)
 *
 * Sets USB endpoint registers 0x9093 and 0x9094 for interrupt transfer config.
 *
 * Original disassembly:
 *   1d07: mov dptr, #0x9093
 *   1d0a: mov a, #0x02
 *   1d0c: movx @dptr, a      ; XDATA[0x9093] = 0x02
 *   1d0d: inc dptr
 *   1d0e: mov a, #0x10
 *   1d10: movx @dptr, a      ; XDATA[0x9094] = 0x10
 *   1d11: ret
 */
void usb_ep_config_int(void)
{
    REG_USB_EP_CFG1 = 0x02;
    REG_USB_EP_CFG2 = 0x10;
}

/*
 * usb_set_transfer_flag - Set USB transfer in-progress flag
 * Address: 0x1d1d-0x1d23 (7 bytes)
 *
 * Sets XDATA[0x0B2E] = 1 to indicate transfer in progress.
 *
 * Original disassembly:
 *   1d1d: mov dptr, #0x0b2e
 *   1d20: mov a, #0x01
 *   1d22: movx @dptr, a
 *   1d23: ret
 */
void usb_set_transfer_flag(void)
{
    G_USB_TRANSFER_FLAG = 1;
}

/*
 * usb_get_nvme_data_ctrl - Get NVMe data control status
 * Address: 0x1d24-0x1d2a (7 bytes)
 *
 * Reads NVMe data control register and masks upper 2 bits.
 *
 * Original disassembly:
 *   1d24: mov dptr, #0xc414
 *   1d27: movx a, @dptr
 *   1d28: anl a, #0xc0       ; mask bits 7-6
 *   1d2a: ret
 */
uint8_t usb_get_nvme_data_ctrl(void)
{
    return REG_NVME_DATA_CTRL & 0xC0;
}

/*
 * usb_set_nvme_ctrl_bit7 - Set bit 7 of NVMe control register
 * Address: 0x1d2b-0x1d31 (7 bytes)
 *
 * Reads current value, clears bit 7, sets bit 7, writes back.
 *
 * Original disassembly:
 *   1d2b: movx a, @dptr      ; read from DPTR (caller sets)
 *   1d2c: anl a, #0x7f       ; clear bit 7
 *   1d2e: orl a, #0x80       ; set bit 7
 *   1d30: movx @dptr, a
 *   1d31: ret
 */
void usb_set_nvme_ctrl_bit7(__xdata uint8_t *ptr)
{
    uint8_t val = *ptr;
    val = (val & 0x7F) | 0x80;
    *ptr = val;
}

/*===========================================================================
 * DMA/Transfer Utility Functions
 *===========================================================================*/

/*
 * dma_clear_dword - Clear 32-bit value at XDATA address
 * Address: 0x173b-0x1742 (8 bytes)
 *
 * Clears R4-R7 to 0 and calls xdata_store_dword (0x0dc5).
 *
 * Original disassembly:
 *   173b: clr a
 *   173c: mov r7, a
 *   173d: mov r6, a
 *   173e: mov r5, a
 *   173f: mov r4, a
 *   1740: ljmp 0x0dc5        ; xdata_store_dword
 */
void dma_clear_dword(__xdata uint8_t *ptr)
{
    ptr[0] = 0;
    ptr[1] = 0;
    ptr[2] = 0;
    ptr[3] = 0;
}

/*
 * usb_get_sys_status_offset - Get system status with offset
 * Address: 0x1743-0x1751 (15 bytes)
 *
 * Reads status from 0x0464, adds 0xA8 to form address in 0x05XX region,
 * and reads from that address.
 *
 * Original disassembly:
 *   1743: mov dptr, #0x0464
 *   1746: movx a, @dptr       ; read status
 *   1747: add a, #0xa8        ; offset = status + 0xA8
 *   1749: mov 0x82, a         ; DPL = offset
 *   174b: clr a
 *   174c: addc a, #0x05       ; DPH = 0x05
 *   174e: mov 0x83, a
 *   1750: movx a, @dptr       ; read from 0x05XX
 *   1751: ret
 */
uint8_t usb_get_sys_status_offset(void)
{
    uint8_t status = G_SYS_STATUS_PRIMARY;
    uint16_t addr = 0x0500 + status + 0xA8;
    return XDATA8(addr);
}

/*
 * usb_calc_addr_with_r7 - Calculate address with R7 offset
 * Address: 0x1752-0x175c (11 bytes)
 *
 * Calculates address 0x0059 + R7 and returns DPTR pointing there.
 *
 * Original disassembly:
 *   1752: mov a, #0x59
 *   1754: add a, r7          ; A = 0x59 + R7
 *   1755: mov 0x82, a        ; DPL = result
 *   1757: clr a
 *   1758: addc a, #0x00      ; DPH = carry
 *   175a: mov 0x83, a
 *   175c: ret
 */
__xdata uint8_t *usb_calc_addr_with_offset(uint8_t offset)
{
    return (__xdata uint8_t *)(0x0059 + offset);
}

/*
 * usb_set_done_flag - Set processing done flag
 * Address: 0x1787-0x178d (7 bytes)
 *
 * Sets XDATA[0x06E6] = 1 to indicate processing complete.
 *
 * Original disassembly:
 *   1787: mov dptr, #0x06e6
 *   178a: mov a, #0x01
 *   178c: movx @dptr, a
 *   178d: ret
 */
void usb_set_done_flag(void)
{
    G_STATE_FLAG_06E6 = 1;
}

/*
 * usb_set_transfer_active_flag - Set transfer flag and USB mode bit
 * Address: 0x312a-0x3139 (16 bytes)
 *
 * Sets transfer flag at 0x0AF2 to 1, then sets bit 0 of USB EP0 config.
 *
 * Original disassembly:
 *   312a: mov dptr, #0x0af2
 *   312d: mov a, #0x01
 *   312f: movx @dptr, a       ; XDATA[0x0AF2] = 1
 *   3130: mov dptr, #0x9006
 *   3133: movx a, @dptr
 *   3134: anl a, #0xfe        ; clear bit 0
 *   3136: orl a, #0x01        ; set bit 0
 *   3138: movx @dptr, a
 *   3139: ret
 */
void usb_set_transfer_active_flag(void)
{
    uint8_t val;

    G_TRANSFER_FLAG_0AF2 = 1;

    val = REG_USB_EP0_CONFIG;
    val = (val & 0xFE) | 0x01;
    REG_USB_EP0_CONFIG = val;
}

/*
 * usb_copy_status_to_buffer - Copy USB status regs to buffer area
 * Address: 0x3147-0x3167 (33 bytes)
 *
 * Copies 4 bytes from USB status registers 0x911F-0x9122 to buffer
 * area 0xD804-0xD807.
 *
 * Original disassembly:
 *   3147: mov dptr, #0x911f
 *   314a: movx a, @dptr
 *   314b: mov dptr, #0xd804
 *   314e: movx @dptr, a       ; D804 = [911F]
 *   314f: mov dptr, #0x9120
 *   3152: movx a, @dptr
 *   3153: mov dptr, #0xd805
 *   3156: movx @dptr, a       ; D805 = [9120]
 *   3157: mov dptr, #0x9121
 *   315a: movx a, @dptr
 *   315b: mov dptr, #0xd806
 *   315e: movx @dptr, a       ; D806 = [9121]
 *   315f: mov dptr, #0x9122
 *   3162: movx a, @dptr
 *   3163: mov dptr, #0xd807
 *   3166: movx @dptr, a       ; D807 = [9122]
 *   3167: ret
 */
void usb_copy_status_to_buffer(void)
{
    XDATA8(0xD804) = REG_USB_STATUS_1F;
    XDATA8(0xD805) = REG_USB_STATUS_20;
    XDATA8(0xD806) = REG_USB_STATUS_21;
    XDATA8(0xD807) = REG_USB_STATUS_22;
}

/*
 * usb_clear_idata_indexed - Clear indexed IDATA location
 * Address: 0x3168-0x3180 (25 bytes)
 *
 * Calculates address 0x00C2 + IDATA[0x38] and clears that XDATA location,
 * then returns pointer to 0x00E5 + IDATA[0x38].
 *
 * Original disassembly:
 *   3168: mov a, #0xc2
 *   316a: add a, 0x38         ; A = 0xC2 + IDATA[0x38]
 *   316c: mov 0x82, a         ; DPL = A
 *   316e: clr a
 *   316f: addc a, #0x00       ; DPH = carry
 *   3171: mov 0x83, a
 *   3173: clr a
 *   3174: movx @dptr, a       ; clear XDATA[0x00C2 + offset]
 *   3175: mov a, #0xe5
 *   3177: add a, 0x38         ; A = 0xE5 + IDATA[0x38]
 *   3179: mov 0x82, a
 *   317b: clr a
 *   317c: addc a, #0x00
 *   317e: mov 0x83, a
 *   3180: ret
 */
__xdata uint8_t *usb_clear_idata_indexed(void)
{
    uint8_t offset = *(__idata uint8_t *)0x38;

    /* Clear at 0x00C2 + offset */
    XDATA8(0x00C2 + offset) = 0;

    /* Return pointer to 0x00E5 + offset */
    return (__xdata uint8_t *)(0x00E5 + offset);
}

/*===========================================================================
 * USB Status Read Functions
 *===========================================================================*/

/*
 * usb_read_status_pair - Read 16-bit status from USB registers
 * Address: 0x3181-0x3188 (8 bytes)
 *
 * Reads USB status registers 0x910D and 0x910E as a 16-bit value.
 * Returns high byte in R6, low byte in A.
 *
 * Original disassembly:
 *   3181: mov dptr, #0x910d
 *   3184: movx a, @dptr       ; R6 = [0x910D]
 *   3185: mov r6, a
 *   3186: inc dptr
 *   3187: movx a, @dptr       ; A = [0x910E]
 *   3188: ret
 */
uint16_t usb_read_status_pair(void)
{
    uint8_t hi = REG_USB_STATUS_0D;
    uint8_t lo = REG_USB_STATUS_0E;
    return ((uint16_t)hi << 8) | lo;
}

/*
 * usb_read_transfer_params - Read transfer parameters
 * Address: 0x31a5-0x31ac (8 bytes)
 *
 * Reads 16-bit value from transfer params at 0x0AFA-0x0AFB.
 * Returns high byte in R6, low byte in A.
 *
 * Original disassembly:
 *   31a5: mov dptr, #0x0afa
 *   31a8: movx a, @dptr       ; R6 = [0x0AFA]
 *   31a9: mov r6, a
 *   31aa: inc dptr
 *   31ab: movx a, @dptr       ; A = [0x0AFB]
 *   31ac: ret
 */
uint16_t usb_read_transfer_params(void)
{
    uint8_t hi = G_TRANSFER_PARAMS_HI;
    uint8_t lo = G_TRANSFER_PARAMS_LO;
    return ((uint16_t)hi << 8) | lo;
}

/*===========================================================================
 * Address Calculation Functions
 *===========================================================================*/

/*
 * usb_calc_queue_addr - Calculate queue element address
 * Address: 0x176b-0x1778 (14 bytes)
 *
 * Calculates DPTR = 0x0478 + (A * 4) where A is input.
 * Used for accessing 4-byte queue elements.
 *
 * Original disassembly:
 *   176b: add a, 0xe0         ; A = A * 2 (add A to itself via ACC register)
 *   176d: add a, 0xe0         ; A = A * 2 again (so A * 4)
 *   176f: add a, #0x78
 *   1771: mov 0x82, a         ; DPL = result
 *   1773: clr a
 *   1774: addc a, #0x04       ; DPH = 0x04 + carry
 *   1776: mov 0x83, a
 *   1778: ret
 */
__xdata uint8_t *usb_calc_queue_addr(uint8_t index)
{
    uint16_t offset = (uint16_t)index * 4;
    return (__xdata uint8_t *)(0x0478 + offset);
}

/*
 * usb_calc_queue_addr_next - Calculate next queue element address
 * Address: 0x1779-0x1786 (14 bytes)
 *
 * Calculates DPTR = 0x0479 + (A * 4) where A is input.
 * Similar to usb_calc_queue_addr but starts at 0x0479.
 *
 * Original disassembly:
 *   1779: add a, 0xe0         ; A = A * 2
 *   177b: add a, 0xe0         ; A = A * 4
 *   177d: add a, #0x79
 *   177f: mov 0x82, a         ; DPL
 *   1781: clr a
 *   1782: addc a, #0x04       ; DPH = 0x04 + carry
 *   1784: mov 0x83, a
 *   1786: ret
 */
__xdata uint8_t *usb_calc_queue_addr_next(uint8_t index)
{
    uint16_t offset = (uint16_t)index * 4;
    return (__xdata uint8_t *)(0x0479 + offset);
}

/*
 * usb_store_idata_16 - Store 16-bit value to IDATA
 * Address: 0x1d32-0x1d38 (7 bytes)
 *
 * Stores 16-bit value (R6:A) to IDATA[0x16:0x17].
 * High byte to [0x16], low byte to [0x17].
 *
 * Original disassembly:
 *   1d32: mov r1, #0x17
 *   1d34: mov @r1, a          ; IDATA[0x17] = A (low)
 *   1d35: mov a, r6
 *   1d36: dec r1
 *   1d37: mov @r1, a          ; IDATA[0x16] = R6 (high)
 *   1d38: ret
 */
void usb_store_idata_16(uint8_t hi, uint8_t lo)
{
    *(__idata uint8_t *)0x17 = lo;
    *(__idata uint8_t *)0x16 = hi;
}

/*
 * usb_add_masked_counter - Add to counter with 5-bit mask
 * Address: 0x1d39-0x1d42 (10 bytes)
 *
 * Reads value from 0x014E, adds input, masks to 5 bits, writes back.
 * Used for circular buffer index management.
 *
 * Original disassembly:
 *   1d39: mov r7, a           ; save A
 *   1d3a: mov dptr, #0x014e
 *   1d3d: movx a, @dptr       ; A = [0x014E]
 *   1d3e: add a, r7           ; A += original A
 *   1d3f: anl a, #0x1f        ; mask to 0-31
 *   1d41: movx @dptr, a       ; write back
 *   1d42: ret
 */
void usb_add_masked_counter(uint8_t value)
{
    uint8_t current = XDATA8(0x014E);
    XDATA8(0x014E) = (current + value) & 0x1F;
}

/*===========================================================================
 * Table-Driven Endpoint Dispatch
 *===========================================================================*/

/*
 * usb_ep_dispatch_loop - USB endpoint processing loop
 * Address: 0x0e96-0x0efb (101 bytes)
 *
 * Main USB endpoint dispatch loop that iterates up to 32 times,
 * reading endpoint status and dispatching to handlers.
 *
 * Algorithm:
 * 1. For counter = 0 to 31:
 *    a. Read USB status from 0x9118
 *    b. Look up endpoint index via ep_index_table
 *    c. If index >= 8, exit loop (no more endpoints to process)
 *    d. Read secondary status from 0x9096 + first_index
 *    e. Look up second endpoint index
 *    f. If second_index >= 8, exit loop
 *    g. Calculate combined offset and store to 0x0AF5
 *    h. Call endpoint handler at 0x5442
 *    i. Write bit mask to clear endpoint status
 *
 * Original disassembly:
 *   0e96: mov 0x37, #0x00     ; counter = 0
 *   0e99: mov dptr, #0x9118   ; USB status
 *   0e9c: movx a, @dptr       ; read status
 *   0e9d: mov dptr, #0x5a6a   ; index table
 *   0ea0: movc a, @a+dptr     ; lookup
 *   0ea1: mov dptr, #0x0a7b
 *   0ea4: movx @dptr, a       ; store index1
 *   ... (see full analysis above)
 *   0ef9: jc 0x0e99           ; loop if counter < 32
 */
void usb_ep_dispatch_loop(void)
{
    __idata uint8_t counter;
    uint8_t status;
    uint8_t ep_index1;
    uint8_t ep_index2;
    uint8_t offset;
    uint8_t bit_mask;

    /* Initialize counter at IDATA 0x37 */
    counter = 0;

    do {
        /* Read USB endpoint status */
        status = REG_USB_EP_STATUS;

        /* Look up first endpoint index */
        ep_index1 = ep_index_table[status];

        /* Store to endpoint dispatch value 1 */
        G_EP_DISPATCH_VAL1 = ep_index1;

        /* Re-read (original firmware does this) */
        ep_index1 = G_EP_DISPATCH_VAL1;

        /* If index >= 8, no endpoint to process - exit */
        if (ep_index1 >= 8) {
            break;
        }

        /* Read secondary status from endpoint base + ep_index1 */
        status = XDATA8(REG_USB_EP_BASE + ep_index1);

        /* Look up second endpoint index */
        ep_index2 = ep_index_table[status];

        /* Store to endpoint dispatch value 2 */
        G_EP_DISPATCH_VAL2 = ep_index2;

        /* Re-read */
        ep_index2 = G_EP_DISPATCH_VAL2;

        /* If second index >= 8, exit */
        if (ep_index2 >= 8) {
            break;
        }

        /* Look up offset from first endpoint index */
        offset = ep_offset_table[ep_index1];

        /* Calculate combined offset: offset + ep_index2 */
        G_EP_DISPATCH_OFFSET = offset + ep_index2;

        /* Call endpoint handler */
        usb_ep_handler();

        /* Clear endpoint status by writing bit mask */
        bit_mask = ep_bit_mask_table[ep_index2];

        /* Write bit mask to endpoint base + ep_index1 */
        XDATA8(REG_USB_EP_BASE + ep_index1) = bit_mask;

        /* Increment counter */
        counter++;

    } while (counter < 0x20);
}
