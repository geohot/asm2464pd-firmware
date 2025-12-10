/*
 * ASM2464PD Firmware - Vendor SCSI Command Handlers
 *
 * Implements vendor-specific SCSI commands (0xE0-0xE8) used by the
 * tinygrad Python library for device control and firmware updates.
 *
 * ============================================================================
 * VENDOR COMMAND OVERVIEW
 * ============================================================================
 *
 * The ASM2464PD uses vendor SCSI commands for special operations:
 *
 *   0xE0 - Config Read   : Read 128-byte config blocks
 *   0xE1 - Config Write  : Write 128-byte config blocks (vendor/product info)
 *   0xE2 - Flash Read    : Read N bytes from SPI flash
 *   0xE3 - Firmware Write: Flash firmware to SPI (0x50=part1, 0xD0=part2)
 *   0xE4 - XDATA Read    : Read bytes from XDATA memory space
 *   0xE5 - XDATA Write   : Write single byte to XDATA memory space
 *   0xE6 - NVMe Admin    : Passthrough NVMe admin commands
 *   0xE8 - Reset/Commit  : System reset or commit flashed firmware
 *
 * ============================================================================
 * ORIGINAL FIRMWARE ADDRESSES
 * ============================================================================
 *
 * Bank 1 addresses (file offset = 0x10000 + (addr - 0x8000)):
 *   vendor_cmd_e4_read  : 0xb473 (file 0x13473)
 *   vendor_cmd_e5_write : 0xb43c (file 0x1343c)
 *   helper_b663         : 0xb663 (file 0x13663) - set DPTR=0x0810, store dword
 *   helper_b67c         : 0xb67c (file 0x1367c) - clear bits at DPTR
 *   helper_b683         : 0xb683 (file 0x13683) - set bits, clear bit 6
 *   helper_b6b5         : 0xb6b5 (file 0x136b5) - shift and store
 *   helper_b6f0         : 0xb6ec (file 0x136ec) - shift a*4, merge/store
 *   helper_b6fa         : 0xb6fa (file 0x136fa) - load dword, compare
 *   helper_b720         : 0xb720 (file 0x13720) - loop store, copy params
 *   helper_b775         : 0xb775 (file 0x13775) - check mode/control
 *
 * Bank 0 helpers:
 *   helper_0d08         : ORL 32-bit r0-r3 with r4-r7
 *   helper_0d22         : SUBB 32-bit compare
 *   helper_0d46         : Left shift r4-r7 by r0 bits
 *   helper_0d84         : Read XDATA dword at DPTR to r4-r7
 *   helper_0d9d         : Read XDATA dword at DPTR to r0-r3
 *   helper_0dc5         : Store r4-r7 to XDATA at DPTR
 *
 * ============================================================================
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"
#include "globals.h"

/*
 * IDATA work variables used by vendor handlers
 * These are defined in globals.h:
 *   I_WORK_51 (0x51) - loop counter
 *   I_WORK_55 (0x55) - state/mode
 *   I_WORK_56 (0x56) - secondary state
 *   I_WORK_57 (0x57) - CDB addr low
 *   I_WORK_58 (0x58) - CDB value/addr mid
 *   I_WORK_59 (0x59) - CDB addr high byte 1
 *   I_WORK_5A (0x5A) - CDB addr high byte 0
 */

/*
 * Bank 0 helper function declarations
 * These are utility functions in the common code area
 */

/* 0x0d08-0x0d14: ORL 32-bit r4-r7 with r0-r3 */
void helper_orl_32bit(void) __naked
{
    __asm
        mov  a, r7          ; r7 |= r3
        orl  a, r3
        mov  r7, a
        mov  a, r6          ; r6 |= r2
        orl  a, r2
        mov  r6, a
        mov  a, r5          ; r5 |= r1
        orl  a, r1
        mov  r5, a
        mov  a, r4          ; r4 |= r0
        orl  a, r0
        mov  r4, a
        ret
    __endasm;
}

/* 0x0d22-0x0d32: SUBB 32-bit compare (r0-r3) - (r4-r7), result OR'd to A */
uint8_t helper_cmp_32bit(void) __naked
{
    __asm
        mov  a, r3
        subb a, r7
        mov  0xf0, a        ; B register
        mov  a, r2
        subb a, r6
        orl  0xf0, a
        mov  a, r1
        subb a, r5
        orl  0xf0, a
        mov  a, r0
        subb a, r4
        orl  a, 0xf0
        ret
    __endasm;
}

/* 0x0d46-0x0d58: Left shift r4-r7 by r0 bits */
void helper_shl_32bit(uint8_t count) __naked
{
    (void)count;
    __asm
        mov  a, r0
        jz   _shl_done
    _shl_loop:
        mov  a, r7
        clr  c
        rlc  a
        mov  r7, a
        mov  a, r6
        rlc  a
        mov  r6, a
        mov  a, r5
        rlc  a
        mov  r5, a
        mov  a, r4
        rlc  a
        mov  r4, a
        djnz r0, _shl_loop
    _shl_done:
        ret
    __endasm;
}

/* 0x0d84-0x0d9c: Read XDATA dword at DPTR to r4-r7 */
void helper_load_dword_r4r7(__xdata uint8_t *ptr) __naked
{
    (void)ptr;
    __asm
        movx a, @dptr
        mov  r4, a
        inc  dptr
        movx a, @dptr
        mov  r5, a
        inc  dptr
        movx a, @dptr
        mov  r6, a
        inc  dptr
        movx a, @dptr
        mov  r7, a
        ret
    __endasm;
}

/* 0x0d9d-0x0da8: Read XDATA dword at DPTR to r0-r3 */
void helper_load_dword_r0r3(__xdata uint8_t *ptr) __naked
{
    (void)ptr;
    __asm
        movx a, @dptr
        mov  r0, a
        inc  dptr
        movx a, @dptr
        mov  r1, a
        inc  dptr
        movx a, @dptr
        mov  r2, a
        inc  dptr
        movx a, @dptr
        mov  r3, a
        ret
    __endasm;
}

/* 0x0dc5-0x0dd0: Store r4-r7 to XDATA at DPTR */
void helper_store_dword(__xdata uint8_t *ptr) __naked
{
    (void)ptr;
    __asm
        mov  a, r4
        movx @dptr, a
        inc  dptr
        mov  a, r5
        movx @dptr, a
        inc  dptr
        mov  a, r6
        movx @dptr, a
        inc  dptr
        mov  a, r7
        movx @dptr, a
        ret
    __endasm;
}

/*
 * Bank 1 helper functions for vendor commands
 */

/*
 * helper_b663 - Set DPTR to 0x0810 and store dword
 * Address: 0xb665-0x13668
 *
 * Sets DPTR = 0x0810 (G_VENDOR_CDB_BASE) and stores r4-r7 there
 */
static void helper_b663(void)
{
    __xdata uint8_t *ptr = (__xdata uint8_t *)0x0810;
    helper_store_dword(ptr);
}

/*
 * helper_b67c - Clear bits at DPTR
 * Address: 0xb67c (file 0x1367c)
 *
 * Read DPTR, AND with 0xFD, store
 * Read DPTR, AND with 0xC3, OR with 0x1C, store
 * Read DPTR, AND with 0xBF, store
 */
static void helper_b67c(__xdata uint8_t *ptr)
{
    uint8_t val;

    /* Step 1: Clear bit 1 */
    val = *ptr;
    val &= 0xFD;
    *ptr = val;

    /* Step 2: Clear bits 2-5, set bits 2-4 */
    val = *ptr;
    val &= 0xC3;  /* Clear bits 2-5 */
    val |= 0x1C;  /* Set bits 2-4 */
    *ptr = val;

    /* Step 3: Clear bit 6 */
    val = *ptr;
    val &= 0xBF;
    *ptr = val;
}

/*
 * helper_b683 - OR bits and clear bit 6
 * Address: 0xb683 (file 0x13683)
 *
 * Entry point for E5 handler
 * ORs 0x1C, then clears bit 6
 */
static void helper_b683(__xdata uint8_t *ptr)
{
    uint8_t val;

    val = *ptr;
    val &= 0xC3;
    val |= 0x1C;
    *ptr = val;

    val = *ptr;
    val &= 0xBF;
    *ptr = val;
}

/*
 * helper_b6b5 - Shift and store two bytes
 * Address: 0xb6b5 (file 0x136b5)
 *
 * a = a + a (shift left)
 * r7 = a
 * a = *dptr
 * a = rlc(a)  (rotate left through carry)
 * r6 = a
 * a = r7 | r5
 * r7 = a
 * *dptr = r6
 * inc dptr
 * *dptr = r7
 */
static void helper_b6b5(__xdata uint8_t *ptr, uint8_t r5_val) __naked
{
    (void)ptr;
    (void)r5_val;
    __asm
        ; dptr already set by caller
        ; r5 has r5_val
        add  a, acc         ; a = a * 2
        mov  r7, a
        movx a, @dptr
        rlc  a
        mov  r6, a
        mov  a, r7
        orl  a, r5
        mov  r7, a
        mov  a, r6
        movx @dptr, a
        inc  dptr
        mov  a, r7
        movx @dptr, a
        ret
    __endasm;
}

/*
 * helper_b6ec - Shift a*4, merge with DPTR value, store
 * Address: 0xb6ec (file 0x136ec)
 *
 * a = a + a + a  (a * 4)
 * r7 = a
 * val = *dptr & 0xC3
 * val |= r7
 * *dptr = val
 */
static uint8_t helper_b6ec(__xdata uint8_t *ptr, uint8_t val)
{
    uint8_t r7;
    uint8_t result;

    r7 = val << 2;  /* a + a + a in original = shift left 2 */

    result = *ptr;
    result &= 0xC3;
    result |= r7;
    *ptr = result;

    return r7;
}

/*
 * helper_b6fa - Load from 0x0AB7 and compare
 * Address: 0xb6fa (file 0x136fa)
 *
 * Set DPTR = 0x0AB7
 * Call helper_0d9d (load r0-r3)
 * Clear carry
 * Jump to helper_0d22 (32-bit compare)
 */
static uint8_t helper_b6fa(void)
{
    __xdata uint8_t *ptr = &G_VENDOR_DATA_0AB7;

    helper_load_dword_r0r3(ptr);
    /* The carry is cleared and compare is done */
    /* Returns result of compare */
    return helper_cmp_32bit();
}

/*
 * helper_b720 - Loop store, copy params, check flags
 * Address: 0xb720 (file 0x13720)
 *
 * Store r7 to DPTR
 * Inc I_WORK_51
 * If I_WORK_51 != 0x64, branch back to loop entry
 * Copy G_CMD_CTRL_PARAM (0x0A57) -> G_VENDOR_CMD_BUF_0804
 * Copy G_CMD_TIMEOUT_PARAM (0x0A58) -> G_VENDOR_CMD_BUF_0805
 * Check G_EVENT_FLAGS (0x09F9) bit 7
 * If not set, clear bit 1 of G_VENDOR_STATUS_081B
 * Clear I_WORK_51
 * Continue with table lookup and more logic
 */
static uint8_t helper_b720(__xdata uint8_t *ptr, uint8_t r7_val, uint8_t r1_offset)
{
    (void)r1_offset;

    /* Store r7 to DPTR */
    *ptr = r7_val;

    /* Increment loop counter */
    I_WORK_51++;

    /* Check if reached 0x64 (100) iterations */
    if (I_WORK_51 != 0x64) {
        return 0;  /* Continue looping */
    }

    /* Copy command parameters */
    G_VENDOR_CMD_BUF_0804 = G_CMD_CTRL_PARAM;
    G_VENDOR_CMD_BUF_0805 = G_CMD_TIMEOUT_PARAM;

    /* Check event flags bit 7 */
    if (!(G_EVENT_FLAGS & 0x80)) {
        /* Clear bit 1 of status */
        G_VENDOR_STATUS_081B &= 0xFD;
    }

    /* Clear loop counter */
    I_WORK_51 = 0;

    /* Return for table lookup phase */
    return 1;
}

/*
 * helper_b775 - Check mode and control flags
 * Address: 0xb775 (file 0x13775)
 *
 * Check G_VENDOR_MODE_07CC >= 3
 * Check G_VENDOR_CTRL_07B9 != 0
 * Check G_VENDOR_MODE_07CF == 1
 * Modify G_VENDOR_STATUS_081A based on checks
 */
static void helper_b775(void)
{
    uint8_t mode_07cc;
    uint8_t ctrl_07b9;
    uint8_t mode_07cf;

    mode_07cc = G_VENDOR_MODE_07CC;

    /* Check if mode < 3 */
    if (mode_07cc < 3) {
        return;  /* Skip modification */
    }

    ctrl_07b9 = G_VENDOR_CTRL_07B9;
    if (ctrl_07b9 == 0) {
        return;  /* Skip modification */
    }

    mode_07cf = G_VENDOR_MODE_07CF;
    if (mode_07cf == 1) {
        return;  /* Skip modification */
    }

    /* Modify status based on mode_07cf */
    /* Original: if mode != 1, modify 0x081a */
}

/*
 * vendor_cmd_e5_xdata_write - Write to XDATA memory space
 * Address: Bank 1 0xb43c-0xb472 (file offset 0x1343c-0x13472)
 *
 * CDB format:
 *   Byte 0: 0xE5
 *   Byte 1: Value to write
 *   Byte 2: Address bits 16-23
 *   Byte 3: Address bits 8-15
 *   Byte 4: Address bits 0-7
 *
 * Original disassembly:
 *   0x1343c: cjne a, #0xe5, 0x3497    ; check opcode
 *   0x1343f: movx @dptr, a            ; acknowledge
 *   0x13440: mov a, 0x55              ; get state
 *   0x13442: jnb acc.1, 0x346c        ; check mode bit 1
 *   0x13445: mov r1, #0x6c            ; offset
 *   0x13447: lcall 0xb720             ; parse/loop helper
 *   0x1344a: mov r7, #0x00
 *   0x1344c: jb acc.0, 0x3451         ; check flag bit 0
 *   0x1344f: mov r7, #0x01
 *   0x13451: mov r5, 0x57             ; get value from CDB
 *   0x13453: lcall 0xea7c             ; execute actual write
 *   0x13456: lcall 0xb6b5             ; shift and store
 *   0x13459: mov dptr, #0xc343        ; vendor control reg
 *   0x1345c: lcall 0xb683             ; set bits, clear bit 6
 *   0x1345f: mov a, r7
 *   0x13460: anl a, #0x01
 *   0x13462: mov r7, a
 *   0x13463: mov a, r7
 *   0x13464: jz 0x346c                ; if zero, skip
 *   0x13466: mov dptr, #0x0ab5        ; vendor data storage
 *   0x13469: mov a, 0x58              ; get value
 *   0x1346b: movx @dptr, a            ; store
 *   0x1346c: lcall 0xb775             ; check mode/control
 *   0x1346f: lcall 0xb6fa             ; load and compare
 *   0x13472: ret
 */
void vendor_cmd_e5_xdata_write(void)
{
    uint8_t state;
    uint8_t r7;
    uint8_t value;
    __xdata uint8_t *ctrl_reg;

    /* Get state from I_WORK_55 */
    state = I_WORK_55;

    /* Check if bit 1 is set */
    if (!(state & 0x02)) {
        /* Skip to end helper calls */
        goto end_helper;
    }

    /* Parse CDB and loop */
    /* r1 = 0x6c offset, call helper_b720 */
    /* This sets up the CDB address parsing */
    /* The actual XDATA write uses address from I_WORK_57-5A */

    r7 = 0x00;

    /* Check bit 0 of accumulator (from helper) */
    if (!(state & 0x01)) {
        r7 = 0x01;
    }

    /* Get value to write from I_WORK_57 (CDB byte 1) */
    value = I_WORK_57;

    /* Execute the actual XDATA write */
    /* The real firmware calls 0xea7c here which performs the write */
    /* using the address from I_WORK_58/59/5A */
    {
        uint16_t addr;
        __xdata uint8_t *dst;

        addr = ((uint16_t)I_WORK_59 << 8) | I_WORK_58;
        dst = (__xdata uint8_t *)addr;
        *dst = value;
    }

    /* Call shift and store helper */
    /* helper_b6b5 with r5 = value */

    /* Set vendor control register */
    ctrl_reg = &REG_VENDOR_CTRL_C343;
    helper_b683(ctrl_reg);

    /* Check r7 bit 0 */
    r7 &= 0x01;
    if (r7 != 0) {
        /* Store value to vendor data storage */
        G_VENDOR_DATA_0AB5 = I_WORK_58;
    }

end_helper:
    /* Call end helper functions */
    helper_b775();
    helper_b6fa();
}

/*
 * vendor_cmd_e4_xdata_read - Read from XDATA memory space
 * Address: Bank 1 0xb473-0xb51f (file offset 0x13473-0x1351f)
 *
 * CDB format:
 *   Byte 0: 0xE4
 *   Byte 1: Size (number of bytes to read)
 *   Byte 2: Address bits 16-23
 *   Byte 3: Address bits 8-15
 *   Byte 4: Address bits 0-7
 *
 * Original disassembly:
 *   0x13473: lcall 0xb663             ; set DPTR=0x0810, store dword
 *   0x13476: lcall 0x0d08             ; ORL 32-bit
 *   0x13479: push r4-r7
 *   0x13481: mov dptr, #0x0816        ; response buffer
 *   0x13484: lcall 0xb67c             ; clear bits
 *   0x13487: mov r0, #0x10            ; 16 bytes
 *   0x13489: lcall 0x0d46             ; shift left
 *   0x1348c: pop r0-r3
 *   0x13494: lcall 0x0d08             ; ORL 32-bit
 *   0x13497-0x134b0: repeat for second 24 bytes
 *   0x134b3: mov 0x5a, r7             ; store address bytes
 *   0x134b5: mov 0x59, r6
 *   0x134b7: mov 0x58, r5
 *   0x134b9: mov 0x57, r4
 *   0x134bb: lcall 0xb6f0             ; shift and merge
 *   0x134be: mov 0x55, r7             ; store state
 *   ... state machine with 0xc2e0/c2e2/c360/c362 register access
 */
void vendor_cmd_e4_xdata_read(void)
{
    uint8_t state;
    uint8_t sec_state;
    __xdata uint8_t *ptr;
    __xdata uint8_t *resp_buf;
    uint8_t r4, r5, r6, r7;
    uint8_t val;

    /* Call helper_b663 - set DPTR=0x0810 and store CDB dword */
    helper_b663();

    /* ORL 32-bit operation */
    helper_orl_32bit();

    /* Save r4-r7 on stack (push) */
    /* These contain the parsed CDB data */

    /* Set DPTR to response buffer 0x0816 */
    resp_buf = &G_VENDOR_RESP_BUF;

    /* Clear bits in response buffer */
    helper_b67c(resp_buf);

    /* Shift left 16 bits (r0 = 0x10) */
    helper_shl_32bit(0x10);

    /* Pop r0-r3 (restore saved r4-r7 to r0-r3) */
    /* ORL 32-bit again */
    helper_orl_32bit();

    /* Second pass: inc DPTR (0x0817), clear bits, shift 24 (0x18) */
    helper_b67c(resp_buf + 1);
    helper_shl_32bit(0x18);

    /* Pop and ORL again */
    helper_orl_32bit();

    /* Store address bytes to idata work variables */
    /* In firmware: mov 0x5a,r7; mov 0x59,r6; mov 0x58,r5; mov 0x57,r4 */
    /* These get the parsed address from CDB */
    /* For now, read from CDB buffer */
    ptr = &G_VENDOR_CDB_BASE;
    r4 = ptr[1];  /* Size */
    r5 = ptr[2];  /* Addr high */
    r6 = ptr[3];  /* Addr mid */
    r7 = ptr[4];  /* Addr low */

    I_WORK_5A = r7;
    I_WORK_59 = r6;
    I_WORK_58 = r5;
    I_WORK_57 = r4;

    /* Call helper_b6ec - shift and merge to get state */
    ptr = &G_VENDOR_CDB_BASE;
    state = helper_b6ec(ptr, I_WORK_58);

    /* Store state to I_WORK_55 */
    I_WORK_55 = state;

    /* State machine: check state value */
    if (state == 0) {
        /* State 0: skip secondary state setup */
        sec_state = 0;
    } else if (state == 1) {
        /* State 1: skip secondary state setup */
        sec_state = 0;
    } else {
        /* Other states: need secondary processing */
        sec_state = 1;
    }

    I_WORK_56 = sec_state;

    /* Select register pair based on secondary state */
    if (sec_state == 0) {
        ptr = &REG_PHY_VENDOR_CTRL_C2E2;
    } else {
        ptr = &REG_VENDOR_CTRL_C362;
    }

    /* Read from control register */
    helper_load_dword_r4r7(ptr);

    /* Store to data area 0x0AAC */
    helper_store_dword(&G_STATE_COUNTER_0AAC);

    /* Select second register based on state */
    if (sec_state == 0) {
        ptr = &REG_PHY_VENDOR_CTRL_C2E0;
    } else {
        ptr = &REG_VENDOR_CTRL_C360;
    }

    /* Read two bytes from register */
    val = ptr[0];
    r6 = val;
    val = ptr[1];
    r7 = val;

    /* Store to 0x0AB0-0x0AB1 */
    G_FLASH_ADDR_3 = r6;
    G_FLASH_LEN_LO = r7;

    /* More processing continues... */
    /* The actual XDATA read and response is done through DMA */
}

/*
 * vendor_is_vendor_command - Check if opcode is a vendor command
 *
 * Returns 1 if opcode is 0xE0-0xE8 (vendor range), 0 otherwise.
 */
uint8_t vendor_is_vendor_command(uint8_t opcode)
{
    return (opcode >= 0xE0 && opcode <= 0xE8) ? 1 : 0;
}
