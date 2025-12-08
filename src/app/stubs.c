/*
 * ASM2464PD Firmware - Function Stubs
 *
 * Stub implementations for functions that have not been fully reverse-engineered yet.
 * These stubs provide minimal implementations to allow the firmware to build.
 *
 * Each stub should be replaced with the actual implementation as the function is
 * reverse-engineered from the original firmware.
 */

#include "../types.h"
#include "../sfr.h"
#include "../registers.h"
#include "../globals.h"

/*===========================================================================
 * USB Transfer Functions
 *===========================================================================*/

/*
 * helper_1579 - Read PCIe transaction count and set up array access
 * Address: 0x1579-0x157c (4 bytes)
 *
 * Disassembly:
 *   1579: mov dptr, #0x05a6  ; G_PCIE_TXN_COUNT_LO
 *   157c: movx a, @dptr      ; Read value to A
 *   (falls through to helper_157d)
 *
 * This reads G_PCIE_TXN_COUNT_LO then falls through to helper_157d
 * which calculates array index into G_PCIE_DIRECTION (0x05B4) area.
 */
void helper_1579(void)
{
    /* Original just reads 0x05A6 into A and falls through to 0x157d
     * The fall-through behavior can't be directly replicated in C,
     * so we call helper_157d explicitly after reading. */
    uint8_t idx = G_PCIE_TXN_COUNT_LO;
    /* Calculate DPTR = 0x05B4 + (idx * 0x22) - done by helper_157d with A as input */
    (void)idx;  /* Used by subsequent operations via DPTR in original code */
}

/*
 * helper_157d - Set up array access with index calculation
 * Address: 0x157d-0x1585 (9 bytes)
 *
 * Disassembly:
 *   157d: mov dptr, #0x05b4  ; Base address (G_PCIE_DIRECTION area)
 *   1580: mov B, #0x22       ; Element size = 34 bytes
 *   1583: ljmp 0x0dd1        ; Array index calculation helper
 *
 * The 0x0dd1 function calculates: DPTR = DPTR + (A * B)
 * This sets DPTR to point to a 34-byte structure in an array at 0x05B4.
 */
void helper_157d(void)
{
    /* This sets up DPTR for array access - DPTR = 0x05B4 + (A * 0x22)
     * In context, A contains the index from prior call */
}

/*
 * helper_15d4 - Complete DPTR setup with carry handling
 * Address: 0x15d4-0x15db (8 bytes)
 *
 * Disassembly:
 *   15d4: mov DPL, a         ; Set low byte
 *   15d6: clr a
 *   15d7: addc a, #0x00      ; High byte with carry
 *   15d9: mov DPH, a
 *   15db: ret
 *
 * This completes a 16-bit address calculation where A contains the low byte
 * and carry flag may affect the high byte.
 */
void helper_15d4(void)
{
    /* Address calculation helper - sets DPTR from A with carry */
}

/*
 * helper_15ef - Set DPTR to SCSI DMA parameter array element
 * Address: 0x15ef-0x15f9 (11 bytes)
 *
 * Disassembly:
 *   15ef: mov a, #0x40
 *   15f1: add a, r7          ; A = 0x40 + R7 (index)
 *   15f2: mov DPL, a
 *   15f4: clr a
 *   15f5: addc a, #0xce      ; DPH = 0xCE + carry
 *   15f7: mov DPH, a
 *   15f9: ret
 *
 * Sets DPTR = 0xCE40 + R7, pointing to SCSI DMA parameter registers.
 * The second parameter (b) is unused - likely R6 in original calling convention.
 */
void helper_15ef(uint8_t a, uint8_t b)
{
    (void)a; (void)b;
    /* Sets DPTR = 0xCE40 + index */
}

/*
 * helper_15f1 - Set DPTR to SCSI DMA parameter (entry at add instruction)
 * Address: 0x15f1-0x15f9 (9 bytes)
 *
 * This is an alternate entry point into helper_15ef, starting at the 'add' instruction.
 * Param is added to 0x40 to form DPL, with DPH = 0xCE.
 */
void helper_15f1(uint8_t param)
{
    (void)param;
    /* Sets DPTR = 0xCE00 + 0x40 + param */
}

/*
 * transfer_func_1633 - Set bit 0 at specified register address
 * Address: 0x1633-0x1639 (7 bytes)
 *
 * Disassembly:
 *   1633: movx a, @dptr      ; Read current value (DPTR passed as param)
 *   1634: anl a, #0xfe       ; Clear bit 0
 *   1636: orl a, #0x01       ; Set bit 0
 *   1638: movx @dptr, a      ; Write back
 *   1639: ret
 *
 * Sets bit 0 of the register at the specified address.
 */
void transfer_func_1633(uint16_t addr)
{
    __xdata uint8_t *ptr = (__xdata uint8_t *)addr;
    uint8_t val = *ptr;
    val = (val & 0xFE) | 0x01;  /* Clear and set bit 0 */
    *ptr = val;
}

/*
 * helper_1646 - Get endpoint config value with array index calculation
 * Address: 0x1646-0x1658 (19 bytes)
 *
 * Disassembly:
 *   1646: mov dptr, #0x0465  ; G_SYS_STATUS_SECONDARY
 *   1649: movx a, @dptr      ; Read index value
 *   164a: mov B, #0x14       ; Element size = 20 bytes
 *   164d: mul ab             ; index * 20
 *   164e: add a, #0x4e       ; Add offset 0x4E
 *   1650: mov DPL, a
 *   1652: clr a
 *   1653: addc a, #0x05      ; DPH = 0x05 + carry
 *   1655: mov DPH, a
 *   1657: movx a, @dptr      ; Read value at calculated address
 *   1658: ret
 *
 * Returns: XDATA[0x054E + (G_SYS_STATUS_SECONDARY * 0x14)]
 */
uint8_t helper_1646(void)
{
    uint8_t idx = G_SYS_STATUS_SECONDARY;
    uint16_t addr = 0x054E + ((uint16_t)idx * 0x14);
    return XDATA_REG8(addr);
}

/*
 * helper_166f - Set DPTR based on I_WORK_43
 * Address: 0x166f-0x1676 (8 bytes)
 *
 * Disassembly:
 *   166f: mov DPL, a         ; (A = 0x7C + I_WORK_43 from prior code)
 *   1671: clr a
 *   1672: addc a, #0x00      ; DPH = carry
 *   1674: mov DPH, a
 *   1676: ret
 *
 * This is part of a larger address calculation. Sets DPTR from A value.
 */
void helper_166f(void)
{
    /* DPTR = (I_WORK_43 + 0x7C) with carry to high byte */
}

/*
 * transfer_func_16b0 - Write value to SCSI DMA status register
 * Address: 0x16b0-0x16b6 (7 bytes)
 *
 * Disassembly:
 *   16b0: mov dptr, #0xce6e  ; REG_SCSI_DMA_STATUS
 *   16b3: movx @dptr, a      ; Write param
 *   16b4: inc a              ; param + 1
 *   16b5: movx @dptr, a      ; Write param + 1
 *   16b6: ret
 *
 * Writes param to REG_SCSI_DMA_STATUS_L, then writes param+1 to same location.
 */
void transfer_func_16b0(uint8_t param)
{
    REG_SCSI_DMA_STATUS_L = param;
    REG_SCSI_DMA_STATUS_L = param + 1;
}

/* 0x16e9: Helper with param - address calculation stub */
void helper_16e9(uint8_t param) { (void)param; }

/* 0x16eb: Helper with param - address calculation stub */
void helper_16eb(uint8_t param) { (void)param; }

/*
 * FUN_CODE_1b07 - Read from SCSI control array
 * Address: 0x1b07-0x1b13 (13 bytes)
 *
 * Disassembly:
 *   1b07: mov a, #0x71       ; Base offset
 *   1b09: add a, 0x3e        ; A = 0x71 + I_WORK_3E
 *   1b0b: mov DPL, a         ; (continues to helper_1b0b)
 *   1b0d: clr a
 *   1b0e: addc a, #0x01      ; DPH = 0x01 + carry
 *   1b10: mov DPH, a
 *   1b12: movx a, @dptr      ; Read from XDATA
 *   1b13: ret
 *
 * Returns: XDATA[0x0171 + I_WORK_3E]
 * This reads from G_SCSI_CTRL (0x0171) plus I_WORK_3E offset.
 */
void FUN_CODE_1b07(void)
{
    /* Returns XDATA[0x0171 + I_WORK_3E] */
}

/*
 * helper_1b0b - Set DPTR and read from XDATA
 * Address: 0x1b0b-0x1b13 (9 bytes)
 *
 * Alternate entry point - A already contains low byte.
 */
void helper_1b0b(void)
{
    /* DPTR setup and read */
}

/* 0x1b2e: Helper function - stub */
void helper_1b2e(void) {}

/* 0x1b30: Helper function - stub */
void helper_1b30(void) {}

/* 0x1c13: Helper function - stub */
void helper_1c13(void) {}

/* 0x1c9f: Protocol function - stub */
void FUN_CODE_1c9f(void) {}

/*===========================================================================
 * SCSI/Protocol Functions
 *===========================================================================*/

/*
 * helper_0cab - 32-bit subtraction: R4-R7 = R4-R7 - R0-R3
 * Address: 0x0cab-0x0cb8 (14 bytes)
 *
 * Disassembly:
 *   0cab: clr c            ; Clear carry for subtraction
 *   0cac: mov a, r7        ; Start with LSB
 *   0cad: subb a, r3       ; R7 - R3
 *   0cae: mov r7, a
 *   0caf: mov a, r6
 *   0cb0: subb a, r2       ; R6 - R2 - borrow
 *   0cb1: mov r6, a
 *   0cb2: mov a, r5
 *   0cb3: subb a, r1       ; R5 - R1 - borrow
 *   0cb4: mov r5, a
 *   0cb5: mov a, r4
 *   0cb6: subb a, r0       ; R4 - R0 - borrow (MSB)
 *   0cb7: mov r4, a
 *   0cb8: ret
 *
 * This performs 32-bit subtraction where:
 *   R4:R5:R6:R7 = R4:R5:R6:R7 - R0:R1:R2:R3
 * Result returned in R4:R5:R6:R7 (R4=MSB, R7=LSB)
 *
 * In C, this is called with SDCC convention where params are passed differently.
 * The function subtracts minuend (r4-r7) from subtrahend (r0-r3).
 */
uint8_t helper_0cab(uint8_t r0, uint8_t r1, uint8_t r6, uint8_t r7) {
    /* This is a 32-bit subtraction helper used by calling code
     * The actual implementation manipulates R4-R7 registers directly
     * In C, we return a dummy value as the real work is done via registers */
    (void)r0; (void)r1; (void)r6; (void)r7;
    return 0;  /* Actual result is in R4-R7 registers */
}

/*
 * helper_328a - Get USB link status (low 2 bits)
 * Address: 0x328a-0x3290 (7 bytes)
 *
 * Disassembly:
 *   328a: mov dptr, #0x9100  ; REG_USB_LINK_STATUS
 *   328d: movx a, @dptr      ; Read register
 *   328e: anl a, #0x03       ; Mask bits 0-1
 *   3290: ret
 *
 * Returns: REG_USB_LINK_STATUS & 0x03
 * These bits typically indicate USB link speed/state.
 */
uint8_t helper_328a(void)
{
    return REG_USB_LINK_STATUS & 0x03;
}

/*
 * helper_3298 - Get DMA status high bits
 * Address: 0x3298-0x329e (7 bytes)
 *
 * Disassembly:
 *   3298: mov dptr, #0xc8d9  ; REG_DMA_STATUS3
 *   329b: movx a, @dptr      ; Read register
 *   329c: anl a, #0xf8       ; Mask bits 3-7
 *   329e: ret
 *
 * Returns: REG_DMA_STATUS3 & 0xF8
 * These are the upper 5 bits of DMA status register 3.
 */
uint8_t helper_3298(void)
{
    return REG_DMA_STATUS3 & 0xF8;
}

/* 0x3578: Helper with param */
void helper_3578(uint8_t param) { (void)param; }

/* SCSI send CSW - stub */
void scsi_send_csw(uint8_t status, uint8_t param) { (void)status; (void)param; }

/* Interface ready check */
void interface_ready_check(uint8_t p1, uint8_t p2, uint8_t p3) {
    (void)p1; (void)p2; (void)p3;
}

/* Protocol compare 32-bit */
uint8_t protocol_compare_32bit(void) { return 0; }

/* Register poll stub */
void reg_poll(void) {}

/*===========================================================================
 * USB Descriptor Helpers
 *===========================================================================*/

/*
 * usb_descriptor_helper_a637 - Initialize USB descriptor state
 * Address: 0xa637-0xa643 (13 bytes)
 *
 * Disassembly:
 *   a637: mov a, #0x01
 *   a639: mov dptr, #0x0ad7   ; G_USB_DESC_STATE
 *   a63c: movx @dptr, a       ; Write 1
 *   a63d: mov dptr, #0x0ade   ; G_USB_DESC_INDEX
 *   a640: clr a
 *   a641: movx @dptr, a       ; Write 0
 *   a642: inc dptr            ; 0x0adf
 *   a643: ret
 *
 * Sets G_USB_DESC_STATE = 1, G_USB_DESC_INDEX = 0
 */
void usb_descriptor_helper_a637(void)
{
    XDATA_REG8(0x0ad7) = 0x01;  /* G_USB_DESC_STATE */
    XDATA_REG8(0x0ade) = 0x00;  /* G_USB_DESC_INDEX */
}

/*
 * usb_descriptor_helper_a644 - Calculate descriptor buffer address (base 0x58)
 * Address: 0xa644-0xa650 (13 bytes)
 *
 * Disassembly:
 *   a644: subb a, #0x58       ; A = A - 0x58 (entry A from prior code)
 *   a646: mov r6, a           ; Save high adjustment
 *   a647: clr a
 *   a648: add a, r7           ; A = 0 + R7 (offset param)
 *   a649: mov 0x82, a         ; DPL = R7
 *   a64b: mov a, #0x9e        ; Base high = 0x9E
 *   a64d: addc a, r6          ; DPH = 0x9E + R6 + carry
 *   a64e: mov 0x83, a
 *   a650: ret
 *
 * Sets DPTR = 0x9E00 + R7 + adjustment from prior A-0x58
 * Used for USB descriptor buffer access.
 */
void usb_descriptor_helper_a644(uint8_t p1, uint8_t p2)
{
    /* Address calculation helper - sets DPTR to descriptor buffer */
    (void)p1; (void)p2;
}

/*
 * usb_descriptor_helper_a648 - Calculate descriptor buffer address (entry at add)
 * Address: 0xa648-0xa650 (9 bytes)
 *
 * Alternate entry point into a644.
 * DPTR = 0x9E00 + R7, with R6 as high byte adjustment.
 */
void usb_descriptor_helper_a648(void)
{
    /* Address calculation helper */
}

/*
 * usb_descriptor_helper_a651 - Write to descriptor buffer (base 0x59)
 * Address: 0xa651-0xa65f (15 bytes)
 *
 * Disassembly:
 *   a651: subb a, #0x59       ; A = A - 0x59
 *   a653: mov r4, a           ; Save high adjustment
 *   a654: clr a
 *   a655: add a, r5           ; A = 0 + R5 (param)
 *   a656: mov 0x82, a         ; DPL = R5
 *   a658: mov a, #0x9e        ; Base high = 0x9E
 *   a65a: addc a, r4          ; DPH = 0x9E + R4 + carry
 *   a65b: mov 0x83, a
 *   a65d: mov a, r7           ; Value to write
 *   a65e: movx @dptr, a       ; Write R7 to buffer
 *   a65f: ret
 *
 * Writes R7 to descriptor buffer at 0x9E00 + R5 + adjustment.
 */
void usb_descriptor_helper_a651(uint8_t p1, uint8_t p2, uint8_t p3)
{
    /* Writes value to USB descriptor buffer */
    (void)p1; (void)p2; (void)p3;
}

/*
 * usb_descriptor_helper_a655 - Calculate buffer address and write (entry at add)
 * Address: 0xa655-0xa65f (11 bytes)
 *
 * Alternate entry point into a651.
 */
void usb_descriptor_helper_a655(uint8_t p1, uint8_t p2)
{
    (void)p1; (void)p2;
}

/* USB descriptor parsing - stub */
void usb_parse_descriptor(uint8_t p1, uint8_t p2) { (void)p1; (void)p2; }

/* USB transfer status check - stub */
uint8_t usb_get_xfer_status(void) { return 0; }

/* USB event handler - stub */
void usb_event_handler(void) {}

/* USB transfer parameter reads - stubs */
uint8_t usb_read_transfer_params_hi(void) { return 0; }
uint8_t usb_read_transfer_params_lo(void) { return 0; }

/*===========================================================================
 * Handler Functions
 *===========================================================================*/

/*
 * Note: handler_0327 and handler_039a are NOT standalone functions.
 * They are entries in a dispatch table at 0x0300+ that loads DPTR
 * with a target address and jumps to the common dispatcher.
 * The actual handlers are the addresses loaded into DPTR.
 */

/* 0x0327: Dispatch entry - loads DPTR=0xB1CB, jumps to 0x0300 */
void handler_0327_usb_power_init(void) {}

/* 0x039a: Dispatch entry - loads DPTR=0xD810, jumps to 0x0300 */
void handler_039a_buffer_dispatch(void) {}

/*
 * handler_d676 - Initialize PCIe/DMA with timeout value
 * Address: 0xd676-... (complex function)
 *
 * Disassembly snippet:
 *   d676: mov r3, #0xff      ; Timeout value R3:R2:R1 = 0xFF234B
 *   d678: mov r2, #0x23
 *   d67a: mov r1, #0x4b
 *   d67c: lcall 0x538d       ; Delay function
 *   d67f: mov dptr, #0xcc32  ; REG_PCIE_CONFIG
 *   d682: lcall 0x9608       ; Read/setup
 *   ... continues with PCIe configuration
 *
 * This function initializes PCIe with specific timing parameters.
 */
void handler_d676(void) {}

/*
 * handler_e3d8 - Event handler with conditional processing
 * Address: 0xe3d8-0xe3f8 (33 bytes)
 *
 * Disassembly:
 *   e3d8: mov dptr, #0x0b41  ; G_EVENT_FLAGS
 *   e3db: movx a, @dptr      ; Read flags
 *   e3dc: jz 0xe3e3          ; Skip if zero
 *   e3de: mov r7, #0x03      ; Param = 3
 *   e3e0: lcall 0xe3b7       ; Call sub-handler
 *   e3e3: mov dptr, #0x0aee  ; G_PROTOCOL_STATE
 *   e3e6: movx a, @dptr      ; Read state
 *   e3e7: mov r7, a          ; R7 = state
 *   e3e8: lcall 0x3578       ; helper_3578
 *   e3eb: lcall 0xd810       ; DMA handler
 *   e3ee: clr a
 *   e3ef: mov dptr, #0x07e8  ; G_TRANSFER_STATUS
 *   e3f2: movx @dptr, a      ; Clear status
 *   e3f3: mov dptr, #0x0b2f  ; G_PROTOCOL_FLAGS
 *   e3f6: inc a              ; A = 1
 *   e3f7: movx @dptr, a      ; Set flags
 *   e3f8: ret
 */
void handler_e3d8(void) {}

/*
 * helper_dd42 - State update based on param and 0x0af1 flag
 * Address: 0xdd42-0xdd77 (54 bytes)
 *
 * Disassembly:
 *   dd42: mov dptr, #0x0af1  ; G_STATE_FLAG_0AF1
 *   dd45: movx a, @dptr      ; Read flag
 *   dd46: jnb 0xe0.5, 0xdd72 ; If bit 5 clear, goto default
 *   dd49: mov a, r7          ; Get param
 *   dd4a: jz 0xdd72          ; If param == 0, goto default
 *   dd4c: cjne a, #0x02, dd51; If param != 2, check next
 *   dd4f: sjmp 0xdd72        ; Default case
 *   dd51: mov a, r7
 *   dd52: cjne a, #0x04, dd5c; If param != 4, check next
 *   dd55: mov dptr, #0xe7e3  ; Write 0x30
 *   dd58: mov a, #0x30
 *   dd5a: movx @dptr, a
 *   dd5b: ret
 *   dd5c: mov a, r7
 *   dd5d: cjne a, #0x01, dd67; If param != 1, check next
 *   dd60: mov dptr, #0xe7e3  ; Write 0xcc
 *   dd63: mov a, #0xcc
 *   dd65: movx @dptr, a
 *   dd66: ret
 *   dd67: mov a, r7
 *   dd68: cjne a, #0xff, dd77; If param != 0xff, return
 *   dd6b: mov dptr, #0xe7e3  ; Write 0xfc
 *   dd6e: mov a, #0xfc
 *   dd70: movx @dptr, a
 *   dd71: ret
 *   dd72: mov dptr, #0xe7e3  ; Default: write 0
 *   dd75: clr a
 *   dd76: movx @dptr, a
 *   dd77: ret
 *
 * Based on param value, writes specific values to REG 0xe7e3
 * if bit 5 of G_STATE_FLAG_0AF1 is set.
 */
void helper_dd42(uint8_t param)
{
    uint8_t flag = G_STATE_FLAG_0AF1;

    /* If bit 5 is clear, write 0 to 0xe7e3 */
    if (!(flag & 0x20)) {
        XDATA8(0xe7e3) = 0;
        return;
    }

    /* If param == 0 or param == 2, write 0 */
    if (param == 0 || param == 2) {
        XDATA8(0xe7e3) = 0;
        return;
    }

    /* Handle specific param values */
    if (param == 4) {
        XDATA8(0xe7e3) = 0x30;
        return;
    }

    if (param == 1) {
        XDATA8(0xe7e3) = 0xcc;
        return;
    }

    if (param == 0xff) {
        XDATA8(0xe7e3) = 0xfc;
        return;
    }

    /* Default: do nothing (return without writing) */
}

/* Forward declaration for helper_e6d2 dependencies */
extern void helper_e396(void);
extern uint8_t helper_0dc5(uint32_t val);
extern void helper_d17a(void);
extern void handler_e478(void);  /* was: dispatch_0638, Bank1:0xE478 */

/*
 * helper_e6d2 - Protocol setup with 32-bit parameter
 * Address: 0xe6d2-0xe6e6 (21 bytes)
 *
 * Disassembly:
 *   e6d2: lcall 0xe396       ; Call helper
 *   e6d5: mov r7, #0x00      ; 32-bit value = 0x00010080
 *   e6d7: mov r6, #0x80
 *   e6d9: mov r5, #0x01
 *   e6db: mov r4, #0x00
 *   e6dd: mov dptr, #0x0b1d
 *   e6e0: lcall 0x0dc5       ; Store 32-bit value
 *   e6e3: lcall 0xd17a       ; Finalize
 *   e6e6: ret
 *
 * Calls helper_e396, then stores 0x00010080 to 0x0b1d, then calls d17a.
 */
uint8_t helper_e6d2(void)
{
    helper_e396();

    /* Store 32-bit value 0x00010080 to 0x0b1d using helper_0dc5 */
    /* The DPTR is set to 0x0b1d before calling 0x0dc5 */
    /* r7:r6:r5:r4 = 0x00:0x80:0x01:0x00 = 0x00010080 (little endian read) */
    XDATA8(0x0b1d) = 0x00;  /* r4 */
    XDATA8(0x0b1e) = 0x01;  /* r5 */
    XDATA8(0x0b1f) = 0x80;  /* r6 */
    XDATA8(0x0b20) = 0x00;  /* r7 */

    helper_d17a();

    return 0;  /* Result in r7 */
}

/*
 * handler_e529 - Store param and process transfer
 * Address: 0xe529-0xe544 (28 bytes)
 *
 * Disassembly:
 *   e529: mov dptr, #0x0aa3  ; G_STATE_RESULT_0AA3
 *   e52c: mov a, r7          ; Get param
 *   e52d: movx @dptr, a      ; Store it
 *   e52e: clr a
 *   e52f: mov r7, a          ; R7 = 0
 *   e530: lcall 0xdd42       ; helper_dd42
 *   e533: lcall 0xe6d2       ; helper_e6d2
 *   e536: mov a, r7          ; Check result
 *   e537: jz 0xe544          ; Return if zero
 *   e539: mov dptr, #0x0aa3  ; G_STATE_RESULT_0AA3
 *   e53c: movx a, @dptr      ; Read param
 *   e53d: mov dptr, #0x7000  ; Log buffer base
 *   e540: movx @dptr, a      ; Write to log
 *   e541: lcall 0xe478       ; dispatch_0638 -> handler_e478
 *   e544: ret
 *
 * Stores param, calls helper functions, and if result is non-zero,
 * writes saved param to 0x7000 and dispatches to Bank1 handler.
 */
void handler_e529(uint8_t param)
{
    uint8_t result;

    /* Store param to G_STATE_RESULT_0AA3 */
    G_STATE_RESULT_0AA3 = param;

    /* Call helper_dd42 with param = 0 */
    helper_dd42(0);

    /* Call helper_e6d2 and get result */
    result = helper_e6d2();

    /* If result non-zero, process further */
    if (result != 0) {
        /* Read back saved param and write to 0x7000 */
        XDATA8(0x7000) = G_STATE_RESULT_0AA3;
        /* Dispatch to Bank1 handler_e478 */
        handler_e478();  /* was: dispatch_0638 */
    }
}

/*
 * handler_e90b - Write to PCIe control register
 * Address: 0xe90b-0xe911 (7 bytes)
 *
 * Disassembly:
 *   e90b: mov dptr, #0xcc81  ; REG_PCIE_CTRL_LO
 *   e90e: mov a, #0x04       ; Value = 4
 *   e910: movx @dptr, a      ; Write
 *   e911: ljmp 0xbe8b        ; Jump to FUN_CODE_be8b
 *
 * Writes 0x04 to PCIe control register then jumps to be8b.
 */
void handler_e90b(void) {}

/*===========================================================================
 * NVMe Utility Functions
 *===========================================================================*/

void nvme_util_advance_queue(void) {}
void nvme_util_check_command_ready(void) {}
void nvme_util_clear_completion(void) {}

/*===========================================================================
 * PCIe/System Functions
 *===========================================================================*/

/*
 * helper_e396 - Protocol initialization setup
 * Address: 0xe396-0xe3b6 (33 bytes)
 *
 * Disassembly:
 *   e396: lcall 0xb8b9       ; Call helper
 *   e399: lcall 0xb833       ; Set up base
 *   e39c: mov a, #0x03
 *   e39e: movx @dptr, a      ; Write 0x03
 *   e39f: clr a
 *   e3a0: mov r5, a          ; R5 = 0
 *   e3a1: mov r7, #0x9f      ; R7 = 0x9F
 *   e3a3: lcall 0xbe02       ; Call delay/wait
 *   e3a6: mov dptr, #0x0b21
 *   e3a9: mov a, #0x80
 *   e3ab: movx @dptr, a      ; [0x0b21] = 0x80
 *   e3ac: mov dptr, #0x0b24
 *   e3af: mov a, #0xd8
 *   e3b1: movx @dptr, a      ; [0x0b24] = 0xd8
 *   e3b2: inc dptr           ; dptr = 0x0b25
 *   e3b3: mov a, #0x20
 *   e3b5: movx @dptr, a      ; [0x0b25] = 0x20
 *   e3b6: ret
 */
void helper_e396(void)
{
    /* Complex initialization - calls multiple sub-helpers */
    /* For now, just set up the values at the known addresses */
    XDATA8(0x0b21) = 0x80;
    XDATA8(0x0b24) = 0xd8;
    XDATA8(0x0b25) = 0x20;
}

/*
 * helper_d17a - Protocol finalization
 * Address: 0xd17a-0xd196 (29 bytes, first return path)
 *
 * Calls multiple sub-helpers and returns a status value in r7.
 * Returns 0 on success, non-zero otherwise.
 */
void helper_d17a(void)
{
    /* Complex finalization - calls multiple sub-helpers */
    /* Stub implementation */
}

void pcie_bank1_helper_e902(void) {}
void startup_init(void) {}
void sys_event_dispatch_05e8(void) {}
void sys_init_helper_bbc7(void) {}
void sys_timer_handler_e957(void) {}

/*===========================================================================
 * UART/Log Buffer Functions
 *===========================================================================*/

/*
 * uart_read_byte_dace - Read byte from log buffer
 * Address: 0xdace-0xdad8 (11 bytes)
 *
 * Disassembly:
 *   dace: add a, 0x21        ; A = A + I_LOG_INDEX
 *   dad0: mov 0x82, a        ; DPL = result
 *   dad2: clr a
 *   dad3: addc a, #0x70      ; DPH = 0x70 + carry
 *   dad5: mov 0x83, a        ; (gives DPTR = 0x7000 + offset)
 *   dad7: movx a, @dptr      ; Read byte
 *   dad8: ret
 *
 * This reads from the log buffer at 0x7000 + I_LOG_INDEX + input_offset.
 * The input A value is added to I_LOG_INDEX to form the offset.
 *
 * Note: Entry expects A to contain offset. In C, we pass as param.
 * Returns: XDATA[0x7000 + I_LOG_INDEX + offset]
 */
uint8_t uart_read_byte_dace(void)
{
    /* Read from log buffer at base 0x7000 + I_LOG_INDEX */
    uint16_t addr = 0x7000 + I_LOG_INDEX;
    return XDATA_REG8(addr);
}

/*
 * uart_write_byte_daeb - Calculate log buffer write address
 * Address: 0xdaeb-0xdaf4 (10 bytes)
 *
 * Disassembly:
 *   daeb: mov a, #0xfc       ; Base offset
 *   daed: add a, 0x21        ; A = 0xFC + I_LOG_INDEX
 *   daef: mov 0x82, a        ; DPL = result
 *   daf1: clr a
 *   daf2: addc a, #0x09      ; DPH = 0x09 + carry
 *   daf4: ret
 *
 * This calculates address 0x09FC + I_LOG_INDEX for writing.
 * Returns: DPTR pointing to 0x09FC + I_LOG_INDEX (in DPH:DPL = 0x83:0x82)
 *
 * Note: This is an address calculation that returns DPTR, used by caller.
 * In C, we just return the high byte; caller uses DPTR afterwards.
 */
uint8_t uart_write_byte_daeb(uint8_t b)
{
    /* This calculates DPTR = 0x09FC + I_LOG_INDEX
     * Original returns with DPTR set up for caller to use
     * The param b is the byte to write (in R7) */
    (void)b;
    /* In original, DPH is returned in A */
    uint8_t low = 0xFC + I_LOG_INDEX;
    uint8_t high = 0x09;
    if (low < 0xFC) high++;  /* Handle carry */
    return high;
}

/*
 * uart_write_daff - Calculate alternate log buffer address
 * Address: 0xdaff-0xdb08 (10 bytes)
 *
 * Disassembly:
 *   daff: mov a, #0x1c       ; Base offset
 *   db01: add a, 0x21        ; A = 0x1C + I_LOG_INDEX
 *   db03: mov 0x82, a        ; DPL = result
 *   db05: clr a
 *   db06: addc a, #0x0a      ; DPH = 0x0A + carry
 *   db08: ret
 *
 * This calculates address 0x0A1C + I_LOG_INDEX.
 * Returns: DPH (0x0A possibly + carry) in A
 */
uint8_t uart_write_daff(void)
{
    /* Calculate DPTR = 0x0A1C + I_LOG_INDEX */
    uint8_t low = 0x1C + I_LOG_INDEX;
    uint8_t high = 0x0A;
    if (low < 0x1C) high++;  /* Handle carry */
    return high;
}

/*===========================================================================
 * Code Functions (FUN_CODE_xxxx)
 *===========================================================================*/

/*
 * Note: FUN_CODE_050c and FUN_CODE_0511 are dispatch table entries,
 * not standalone functions. They load DPTR with target addresses.
 */
void FUN_CODE_050c(void) {}
void FUN_CODE_0511(uint8_t p1, uint8_t p2, uint8_t p3) { (void)p1; (void)p2; (void)p3; }

/*
 * FUN_CODE_11a2 - Complex SCSI command processing
 * Address: 0x11a2-... (complex function with branches)
 *
 * Reads from I_WORK_0D to I_WORK_43, processes SCSI state at 0xCE51,
 * and handles command setup.
 */
void FUN_CODE_11a2(void) {}

/*
 * FUN_CODE_5038 - Calculate buffer address with 0x17 offset
 * Address: 0x5038-0x5042 (11 bytes)
 *
 * Disassembly:
 *   5038: mov a, #0x17
 *   503a: add a, r7          ; A = 0x17 + R7
 *   503b: mov 0x82, a        ; DPL = result
 *   503d: clr a
 *   503e: addc a, #0x05      ; DPH = 0x05 + carry
 *   5040: mov 0x83, a
 *   5042: ret
 *
 * Sets DPTR = 0x0517 + R7. Used for NVMe queue buffer access.
 */
void FUN_CODE_5038(void) {}

/*
 * FUN_CODE_5043 - Calculate buffer address with 0x08 offset and read
 * Address: 0x5043-0x504e (12 bytes)
 *
 * Disassembly:
 *   5043: mov a, #0x08
 *   5045: add a, r7          ; A = 0x08 + R7
 *   5046: mov 0x82, a        ; DPL = result
 *   5048: clr a
 *   5049: addc a, #0x01      ; DPH = 0x01 + carry
 *   504b: mov 0x83, a
 *   504d: movx a, @dptr      ; Read byte
 *   504e: ret
 *
 * Returns: XDATA[0x0108 + R7]
 */
uint8_t FUN_CODE_5043(uint8_t param)
{
    uint16_t addr = 0x0108 + param;
    return XDATA_REG8(addr);
}

/*
 * FUN_CODE_5046 - Alternate entry into 5043 (at mov DPL instruction)
 * Address: 0x5046-0x504e (9 bytes)
 */
void FUN_CODE_5046(void) {}

/*
 * FUN_CODE_504f - Calculate queue buffer address
 * Address: 0x504f-0x505c (14 bytes)
 *
 * Reads G_QUEUE_INDEX (0x0A84), adds 0x0C, sets DPTR.
 * Sets DPTR = XDATA[0x0A84] + 0x0C
 */
void FUN_CODE_504f(void) {}

/*
 * FUN_CODE_505d - Calculate buffer address with 0xC2 offset
 * Address: 0x505d-0x5066 (10 bytes)
 *
 * A = A + 0xC2, DPTR = A (with carry to high byte)
 */
void FUN_CODE_505d(void) {}

/*
 * FUN_CODE_5359 - NVMe queue state management
 * Address: 0x5359-0x5372 (26 bytes)
 *
 * Reads G_SYS_STATUS (0x0464), calls helper_16e9,
 * stores to I_WORK_51, masks with 0x1F, calls helper_16eb.
 */
void FUN_CODE_5359(void) {}

/*
 * FUN_CODE_be8b - PCIe link status check with state machine
 * Address: 0xbe8b-... (complex function)
 *
 * Reads 0xE302, masks with 0x30, swaps nibbles, compares with 0x03.
 * Part of PCIe link training state machine.
 */
void FUN_CODE_be8b(void) {}

/* 0xdd0e: Simple stub */
void FUN_CODE_dd0e(void) {}

/* 0xdd12: Stub with params */
void FUN_CODE_dd12(uint8_t p1, uint8_t p2) { (void)p1; (void)p2; }

/*
 * FUN_CODE_df79 - Protocol state dispatcher
 * Address: 0xdf79-0xdfaa (50 bytes)
 *
 * Reads 0x0B1B -> 0x0A9D, calls 0xE74E, then switches
 * based on state value (1, 2, 3 cases).
 */
void FUN_CODE_df79(void) {}

/* 0xe120: Stub with params */
void FUN_CODE_e120(uint8_t p1, uint8_t p2) { (void)p1; (void)p2; }

/*
 * FUN_CODE_e1c6 - Wait loop with status check
 * Address: 0xe1c6-0xe1ed (40 bytes)
 *
 * Polling loop: calls 0xE09A until R7 != 0,
 * then reads/writes various state registers.
 */
void FUN_CODE_e1c6(void) {}

/* 0xe73a: PCIe/DMA related - stub */
void FUN_CODE_e73a(void) {}

/* 0xe7ae: PCIe/DMA related - stub */
void FUN_CODE_e7ae(void) {}

/* 0xe883: Handler - stub */
void FUN_CODE_e883(void) {}
