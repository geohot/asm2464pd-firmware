/*
 * ASM2464PD Firmware - Core Utility Functions
 *
 * Low-level utility functions for memory access and data manipulation.
 * These are called throughout the firmware for loading parameters from
 * internal RAM (IDATA) and external RAM (XDATA).
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"
#include "globals.h"

/*
 * idata_load_dword - Load 32-bit value from IDATA
 * Address: 0x0d78-0x0d83 (12 bytes)
 *
 * Original function loads 4 bytes from IDATA[@R0] into R4-R7.
 * In C, we return a 32-bit value which SDCC places in R4-R7.
 *
 * Original disassembly:
 *   0d78: mov a, @r0        ; read byte 0
 *   0d79: mov r4, a
 *   0d7a: inc r0
 *   0d7b: mov a, @r0        ; read byte 1
 *   0d7c: mov r5, a
 *   0d7d: inc r0
 *   0d7e: mov a, @r0        ; read byte 2
 *   0d7f: mov r6, a
 *   0d80: inc r0
 *   0d81: mov a, @r0        ; read byte 3
 *   0d82: mov r7, a
 *   0d83: ret
 */
uint32_t idata_load_dword(__idata uint8_t *ptr)
{
    uint32_t val;
    val = ptr[0];
    val |= ((uint32_t)ptr[1]) << 8;
    val |= ((uint32_t)ptr[2]) << 16;
    val |= ((uint32_t)ptr[3]) << 24;
    return val;
}

/*
 * xdata_load_dword - Load 32-bit value from XDATA
 * Address: 0x0d84-0x0d8f (12 bytes)
 *
 * Original function loads 4 bytes from XDATA[DPTR] into R4-R7.
 *
 * Original disassembly:
 *   0d84: movx a, @dptr     ; read byte 0
 *   0d85: mov r4, a
 *   0d86: inc dptr
 *   0d87: movx a, @dptr     ; read byte 1
 *   0d88: mov r5, a
 *   0d89: inc dptr
 *   0d8a: movx a, @dptr     ; read byte 2
 *   0d8b: mov r6, a
 *   0d8c: inc dptr
 *   0d8d: movx a, @dptr     ; read byte 3
 *   0d8e: mov r7, a
 *   0d8f: ret
 */
uint32_t xdata_load_dword(__xdata uint8_t *ptr)
{
    uint32_t val;
    val = ptr[0];
    val |= ((uint32_t)ptr[1]) << 8;
    val |= ((uint32_t)ptr[2]) << 16;
    val |= ((uint32_t)ptr[3]) << 24;
    return val;
}

/*
 * idata_load_dword_alt - Load 32-bit value from IDATA (alternate register allocation)
 * Address: 0x0d90-0x0d9c (13 bytes)
 *
 * Original function loads 4 bytes from IDATA[@R0] into R0-R3.
 * Used for loading secondary parameters.
 *
 * Original disassembly:
 *   0d90: mov a, @r0        ; read byte 0
 *   0d91: mov r3, a
 *   0d92: inc r0
 *   0d93: mov a, @r0        ; read byte 1
 *   0d94: mov r1, a
 *   0d95: inc r0
 *   0d96: mov a, @r0        ; read byte 2
 *   0d97: mov r2, a
 *   0d98: inc r0
 *   0d99: mov a, @r0        ; read byte 3
 *   0d9a: xch a, r3
 *   0d9b: mov r0, a
 *   0d9c: ret
 */
uint32_t idata_load_dword_alt(__idata uint8_t *ptr)
{
    uint32_t val;
    val = ptr[0];
    val |= ((uint32_t)ptr[1]) << 8;
    val |= ((uint32_t)ptr[2]) << 16;
    val |= ((uint32_t)ptr[3]) << 24;
    return val;
}

/*
 * xdata_load_dword_alt - Load 32-bit value from XDATA (alternate register allocation)
 * Address: 0x0d9d-0x0da8 (12 bytes)
 *
 * Original function loads 4 bytes from XDATA[DPTR] into R0-R3.
 *
 * Original disassembly:
 *   0d9d: movx a, @dptr     ; read byte 0
 *   0d9e: mov r0, a
 *   0d9f: inc dptr
 *   0da0: movx a, @dptr     ; read byte 1
 *   0da1: mov r1, a
 *   0da2: inc dptr
 *   0da3: movx a, @dptr     ; read byte 2
 *   0da4: mov r2, a
 *   ... continues
 */
uint32_t xdata_load_dword_alt(__xdata uint8_t *ptr)
{
    uint32_t val;
    val = ptr[0];
    val |= ((uint32_t)ptr[1]) << 8;
    val |= ((uint32_t)ptr[2]) << 16;
    val |= ((uint32_t)ptr[3]) << 24;
    return val;
}

/*
 * idata_store_dword - Store 32-bit value to IDATA
 * Address: 0x0db9-0x0dc4 (12 bytes)
 *
 * Stores R4-R7 (32-bit value) to IDATA[@R0].
 *
 * Original disassembly:
 *   0db9: mov a, r4
 *   0dba: mov @r0, a
 *   0dbb: inc r0
 *   0dbc: mov a, r5
 *   0dbd: mov @r0, a
 *   0dbe: inc r0
 *   0dbf: mov a, r6
 *   0dc0: mov @r0, a
 *   0dc1: inc r0
 *   0dc2: mov a, r7
 *   0dc3: mov @r0, a
 *   0dc4: ret
 */
void idata_store_dword(__idata uint8_t *ptr, uint32_t val)
{
    ptr[0] = (uint8_t)(val & 0xFF);
    ptr[1] = (uint8_t)((val >> 8) & 0xFF);
    ptr[2] = (uint8_t)((val >> 16) & 0xFF);
    ptr[3] = (uint8_t)((val >> 24) & 0xFF);
}

/*
 * xdata_store_dword - Store 32-bit value to XDATA
 * Address: 0x0dc5-0x0dd0 (12 bytes)
 *
 * Stores R4-R7 (32-bit value) to XDATA[DPTR].
 *
 * Original disassembly:
 *   0dc5: mov a, r4
 *   0dc6: movx @dptr, a
 *   0dc7: inc dptr
 *   0dc8: mov a, r5
 *   0dc9: movx @dptr, a
 *   0dca: inc dptr
 *   0dcb: mov a, r6
 *   0dcc: movx @dptr, a
 *   0dcd: inc dptr
 *   0dce: mov a, r7
 *   0dcf: movx @dptr, a
 *   0dd0: ret
 */
void xdata_store_dword(__xdata uint8_t *ptr, uint32_t val)
{
    ptr[0] = (uint8_t)(val & 0xFF);
    ptr[1] = (uint8_t)((val >> 8) & 0xFF);
    ptr[2] = (uint8_t)((val >> 16) & 0xFF);
    ptr[3] = (uint8_t)((val >> 24) & 0xFF);
}

/*
 * xdata_load_triple - Load 3 bytes from XDATA
 * Address: 0x0ddd-0x0de5 (9 bytes)
 *
 * Loads 3 bytes from XDATA[DPTR] into R3, R2, R1 (24-bit value).
 *
 * Original disassembly:
 *   0ddd: movx a, @dptr     ; read byte 0
 *   0dde: mov r3, a
 *   0ddf: inc dptr
 *   0de0: movx a, @dptr     ; read byte 1
 *   0de1: mov r2, a
 *   0de2: inc dptr
 *   0de3: movx a, @dptr     ; read byte 2
 *   0de4: mov r1, a
 *   0de5: ret
 */
uint32_t xdata_load_triple(__xdata uint8_t *ptr)
{
    uint32_t val;
    val = ptr[0];
    val |= ((uint32_t)ptr[1]) << 8;
    val |= ((uint32_t)ptr[2]) << 16;
    return val;
}

/*
 * xdata_store_triple - Store 3 bytes to XDATA
 * Address: 0x0de6-0x0dee (9 bytes)
 *
 * Stores R3, R2, R1 (24-bit value) to XDATA[DPTR].
 *
 * Original disassembly:
 *   0de6: mov a, r3
 *   0de7: movx @dptr, a
 *   0de8: inc dptr
 *   0de9: mov a, r2
 *   0dea: movx @dptr, a
 *   0deb: inc dptr
 *   0dec: mov a, r1
 *   0ded: movx @dptr, a
 *   0dee: ret
 */
void xdata_store_triple(__xdata uint8_t *ptr, uint32_t val)
{
    ptr[0] = (uint8_t)(val & 0xFF);
    ptr[1] = (uint8_t)((val >> 8) & 0xFF);
    ptr[2] = (uint8_t)((val >> 16) & 0xFF);
}

/*
 * dptr_index_mul - Calculate DPTR offset with multiplication
 * Address: 0x0dd1-0x0ddc (12 bytes)
 *
 * Multiplies A by B (index * element_size) and adds to DPTR.
 * Used for array indexing: DPTR = base + (index * element_size)
 *
 * Original disassembly:
 *   0dd1: mul ab           ; A = A * B (low), B = high
 *   0dd2: add a, 0x82      ; DPL += A
 *   0dd4: mov 0x82, a
 *   0dd6: mov a, 0xf0      ; A = B (high byte)
 *   0dd8: addc a, 0x83     ; DPH += carry + high
 *   0dda: mov 0x83, a
 *   0ddc: ret (falls through to next function)
 */
__xdata uint8_t *dptr_index_mul(__xdata uint8_t *base, uint8_t index, uint8_t element_size)
{
    uint16_t offset = (uint16_t)index * element_size;
    return base + offset;
}

//=============================================================================
// Register Helper Functions (0xbb00-0xbf00)
// These functions manipulate hardware registers with bit operations
//=============================================================================

#include "globals.h"

/*
 * reg_clear_bits_and_init - Clear bit 4 in DPTR reg, clear bit 2 in 0xC472, write 0xFF to init regs
 * Address: 0xbb37-0xbb4e (24 bytes)
 *
 * Clears bit 4 in register pointed by DPTR, clears bit 2 in REG_NVME_LINK_CTRL,
 * then writes 0xFF to 4 consecutive registers at 0xC438-0xC43B.
 *
 * Original disassembly:
 *   bb37: movx a, @dptr     ; read from DPTR
 *   bb38: anl a, #0xef      ; clear bit 4
 *   bb3a: movx @dptr, a     ; write back
 *   bb3b: mov dptr, #0xc472
 *   bb3e: movx a, @dptr
 *   bb3f: anl a, #0xfb      ; clear bit 2
 *   bb41: movx @dptr, a
 *   bb42: mov a, #0xff
 *   bb44: mov dptr, #0xc438
 *   bb47: movx @dptr, a     ; write 0xFF
 *   bb48-bb4d: inc dptr, movx @dptr, a (repeat 3x)
 *   bb4e: ret
 */
void reg_clear_bits_and_init(__xdata uint8_t *reg)
{
    uint8_t val;

    /* Clear bit 4 in the input register */
    val = *reg;
    *reg = val & 0xEF;

    /* Clear bit 2 in REG_NVME_LINK_CTRL (0xC472) */
    val = REG_NVME_LINK_CTRL;
    REG_NVME_LINK_CTRL = val & 0xFB;

    /* Write 0xFF to 4 consecutive registers at 0xC438-0xC43B */
    REG_NVME_INIT_CTRL = 0xFF;
    XDATA_REG8(0xC439) = 0xFF;
    XDATA_REG8(0xC43A) = 0xFF;
    XDATA_REG8(0xC43B) = 0xFF;
}

/*
 * reg_read_indexed_0a84 - Read from indexed register and store to 0x0A84
 * Address: 0xbb4f-0xbb5d (15 bytes)
 *
 * Calculates address 0x70XX where XX = R6 + A, reads that register,
 * stores result to G_STATE_WORK_0A84, reads back and returns.
 *
 * Original disassembly:
 *   bb4f: add a, r6
 *   bb50: mov dpl, a
 *   bb52: clr a
 *   bb53: addc a, #0x70
 *   bb55: mov dph, a       ; DPTR = 0x7000 + R6 + A
 *   bb57: movx a, @dptr    ; read register
 *   bb58: mov dptr, #0x0a84
 *   bb5b: movx @dptr, a    ; store to 0x0A84
 *   bb5c: movx a, @dptr    ; read back
 *   bb5d: ret
 */
uint8_t reg_read_indexed_0a84(uint8_t offset, uint8_t base)
{
    __xdata uint8_t *ptr;
    uint8_t val;

    ptr = (__xdata uint8_t *)(0x7000 + base + offset);
    val = *ptr;
    G_STATE_WORK_0A84 = val;
    return G_STATE_WORK_0A84;
}

/*
 * reg_extract_bit6 - Right rotate and extract bit 6 (becomes bit 0)
 * Address: 0xbb5e-0xbb67 (10 bytes)
 *
 * Rotates A right twice through carry, masks with 0x01, writes to DPTR,
 * reads from 0x707D and returns.
 *
 * Original disassembly:
 *   bb5e: rrc a
 *   bb5f: rrc a
 *   bb60: anl a, #0x01     ; extract what was bit 6
 *   bb62: movx @dptr, a    ; store result
 *   bb63: mov dptr, #0x707d
 *   bb66: movx a, @dptr    ; read from 0x707D
 *   bb67: ret
 */
uint8_t reg_extract_bit6(__xdata uint8_t *dest, uint8_t val)
{
    /* Extract bit 6 by shifting right twice (with carry) and masking */
    val = (val >> 6) & 0x01;
    *dest = val;
    return G_FLASH_BUF_707D;
}

/*
 * reg_set_bits_1_2 - Set bits 1 and 2 in register
 * Address: 0xbb68-0xbb74 (13 bytes)
 *
 * Reads from DPTR, clears bit 1, sets bit 1, writes back.
 * Then reads again, clears bit 2, sets bit 2, writes back.
 *
 * Original disassembly:
 *   bb68: movx a, @dptr
 *   bb69: anl a, #0xfd     ; clear bit 1
 *   bb6b: orl a, #0x02     ; set bit 1
 *   bb6d: movx @dptr, a
 *   bb6e: movx a, @dptr
 *   bb6f: anl a, #0xfb     ; clear bit 2
 *   bb71: orl a, #0x04     ; set bit 2
 *   bb73: movx @dptr, a
 *   bb74: ret
 */
void reg_set_bits_1_2(__xdata uint8_t *reg)
{
    uint8_t val;

    /* Set bit 1 */
    val = *reg;
    val = (val & 0xFD) | 0x02;
    *reg = val;

    /* Set bit 2 */
    val = *reg;
    val = (val & 0xFB) | 0x04;
    *reg = val;
}

/*
 * reg_extract_bit7 - Right rotate and extract bit 7 (becomes bit 0)
 * Address: 0xbb75-0xbb7d (9 bytes)
 *
 * Rotates A right once, masks with 0x01, writes to DPTR,
 * reads from 0x707D and returns.
 */
uint8_t reg_extract_bit7(__xdata uint8_t *dest, uint8_t val)
{
    val = (val >> 7) & 0x01;
    *dest = val;
    return G_FLASH_BUF_707D;
}

/*
 * reg_clear_bit3_link_ctrl - Clear bit 3 in DPTR reg, clear bit 1 in 0xC472, return 0xFF
 * Address: 0xbb7e-0xbb8e (17 bytes)
 *
 * Clears bit 3 in register pointed by DPTR, clears bit 1 in REG_NVME_LINK_CTRL,
 * returns 0xFF and sets DPTR to 0xC448.
 */
uint8_t reg_clear_bit3_link_ctrl(__xdata uint8_t *reg)
{
    uint8_t val;

    /* Clear bit 3 in the input register */
    val = *reg;
    *reg = val & 0xF7;

    /* Clear bit 1 in REG_NVME_LINK_CTRL (0xC472) */
    val = REG_NVME_LINK_CTRL;
    REG_NVME_LINK_CTRL = val & 0xFD;

    return 0xFF;
}

/*
 * reg_write_dph_r7 - Write R7 to XDATA at address formed from A (high) and R6 (low)
 * Address: 0xbb8f-0xbb95 (7 bytes)
 *
 * Forms address from A (DPH) and R6 (stored from previous call), writes R7 there.
 */
uint8_t reg_write_indexed(uint8_t dph, uint8_t dpl, uint8_t val)
{
    __xdata uint8_t *ptr = (__xdata uint8_t *)((dph << 8) | dpl);
    *ptr = val;
    return dpl + 1;
}

/*
 * reg_extract_bits_6_7 - Extract bits 6-7 (shift right 6, mask with 0x03)
 * Address: 0xbb96-0xbb9f (10 bytes)
 *
 * Rotates A right twice, masks with 0x03, writes to DPTR,
 * reads from 0x707B and returns.
 */
uint8_t reg_extract_bits_6_7(__xdata uint8_t *dest, uint8_t val)
{
    val = (val >> 6) & 0x03;
    *dest = val;
    return G_FLASH_BUF_707B;
}

/*
 * reg_extract_bit0 - Extract bit 0 and store
 * Address: 0xbba0-0xbba7 (8 bytes)
 *
 * Masks A with 0x01, writes to DPTR, reads from 0x707D and returns.
 */
uint8_t reg_extract_bit0(__xdata uint8_t *dest, uint8_t val)
{
    *dest = val & 0x01;
    return G_FLASH_BUF_707D;
}

/*
 * reg_set_bit6 - Set bit 6 in register (clear first, then set)
 * Address: 0xbba8-0xbbae (7 bytes)
 */
void reg_set_bit6(__xdata uint8_t *reg)
{
    uint8_t val = *reg;
    val = (val & 0xBF) | 0x40;
    *reg = val;
}

/*
 * reg_set_bit1 - Set bit 1 in register (clear first, then set)
 * Address: 0xbbaf-0xbbb5 (7 bytes)
 */
void reg_set_bit1(__xdata uint8_t *reg)
{
    uint8_t val = *reg;
    val = (val & 0xFD) | 0x02;
    *reg = val;
}

/*
 * reg_set_event_flag - Set event control to 4, return with DPTR at 0x0AE2
 * Address: 0xbbb6-0xbbbf (10 bytes)
 */
__xdata uint8_t *reg_set_event_flag(void)
{
    G_EVENT_CTRL_09FA = 0x04;
    return (__xdata uint8_t *)0x0AE2;
}

/*
 * reg_set_bit3 - Set bit 3 in register (clear first, then set)
 * Address: 0xbbc0-0xbbc6 (7 bytes)
 */
void reg_set_bit3(__xdata uint8_t *reg)
{
    uint8_t val = *reg;
    val = (val & 0xF7) | 0x08;
    *reg = val;
}

/*
 * reg_nibble_swap_store - Read from DPTR, store to 0x0A5C, swap nibbles and store to 0x0A5B
 * Address: 0xbc70-0xbc87 (24 bytes)
 *
 * Reads value from DPTR, stores to G_NIBBLE_SWAP_0A5C, then swaps nibbles
 * and combines with value at G_NIBBLE_SWAP_0A5C, storing result to G_NIBBLE_SWAP_0A5B.
 * Returns the combined value.
 */
uint8_t reg_nibble_swap_store(__xdata uint8_t *reg)
{
    uint8_t val, swapped, low_nibble;

    /* Read from register and store to 0x0A5C */
    val = *reg;
    G_NIBBLE_SWAP_0A5C = val;

    /* Read back, swap nibbles, extract low nibble */
    val = G_NIBBLE_SWAP_0A5C;
    swapped = (val >> 4) | (val << 4);  /* swap a */
    low_nibble = swapped & 0x0F;

    /* XOR with original swapped value (extracts high nibble as low) */
    swapped = swapped ^ low_nibble;  /* Now swapped has original low nibble in high position */
    G_NIBBLE_SWAP_0A5C = swapped;

    /* Read 0x0A5B, swap, keep high nibble, OR with low_nibble */
    val = G_NIBBLE_SWAP_0A5B;
    val = (val >> 4) | (val << 4);
    val = (val & 0xF0) | low_nibble;
    G_NIBBLE_SWAP_0A5B = val;

    return G_NIBBLE_SWAP_0A5B;
}

/*
 * reg_read_bank_1235 - Read from bank 0x1235
 * Address: 0xbc88-0xbc8e (7 bytes)
 *
 * Sets R2=0x12, R1=0x35 and jumps to read routine at 0x0bc8.
 * Returns byte read from address 0x1235.
 */
uint8_t reg_read_bank_1235(void)
{
    return XDATA_REG8(0x1235);
}

/*
 * reg_read_bank_0200 - Read from bank with R3=2, R2=0, R1=0
 * Address: 0xbc8f-0xbc97 (9 bytes)
 */
uint8_t reg_read_bank_0200(void)
{
    return XDATA_REG8(0x0200);
}

/*
 * reg_read_bank_1200 - Read from bank with R3=2, R2=0x12
 * Address: 0xbc98-0xbc9e (7 bytes)
 */
uint8_t reg_read_bank_1200(void)
{
    return XDATA_REG8(0x1200);
}

/*
 * reg_read_and_clear_bit3 - Read from bank 0x28xx and clear bit 3
 * Address: 0xbca5-0xbcae (10 bytes)
 */
uint8_t reg_read_and_clear_bit3(uint8_t offset)
{
    __xdata uint8_t *ptr = (__xdata uint8_t *)(0x2800 | offset);
    return *ptr & 0xF7;
}

/*
 * reg_read_bank_1603 - Read from bank 0x1603
 * Address: 0xbcaf-0xbcb7 (9 bytes)
 */
uint8_t reg_read_bank_1603(void)
{
    return XDATA_REG8(0x1603);
}

/*
 * reg_nibble_extract - Read from DPTR, extract high nibble, OR with 0x0A5C
 * Address: 0xbcb8-0xbcc3 (12 bytes)
 */
uint8_t reg_nibble_extract(__xdata uint8_t *reg)
{
    uint8_t val, high_nibble;

    val = *reg;
    high_nibble = (val >> 4) & 0x0F;
    val = G_NIBBLE_SWAP_0A5C;
    return val | high_nibble;
}

/*
 * reg_read_bank_1504_clear - Read from bank 0x1504 and clear bits 2-3
 * Address: 0xbcc4-0xbccf (12 bytes)
 */
uint8_t reg_read_bank_1504_clear(void)
{
    return XDATA_REG8(0x1504) & 0xF3;
}

/*
 * reg_read_bank_1200_alt - Read from bank 0x1200 (alternate)
 * Address: 0xbcd0-0xbcd6 (7 bytes)
 */
uint8_t reg_read_bank_1200_alt(void)
{
    return XDATA_REG8(0x1200);
}

/*
 * reg_read_event_mask - Read from 0x09FA and mask with 0x81
 * Address: 0xbcd7-0xbcdd (7 bytes)
 *
 * Returns bits 0 and 7 of the event control register.
 */
uint8_t reg_read_event_mask(void)
{
    return G_EVENT_CTRL_09FA & 0x81;
}

/*
 * reg_read_bank_1407 - Read from bank 0x1407
 * Address: 0xbcde-0xbce6 (9 bytes)
 */
uint8_t reg_read_bank_1407(void)
{
    return XDATA_REG8(0x1407);
}

/*
 * reg_write_and_set_link_bit0 - Write to DPTR, then set bit 0 in REG_LINK_CTRL_E717
 * Address: 0xbce7-0xbcf1 (11 bytes)
 *
 * Writes A to register at DPTR, then sets bit 0 in link control register 0xE717.
 */
void reg_write_and_set_link_bit0(__xdata uint8_t *reg, uint8_t val)
{
    uint8_t tmp;

    *reg = val;
    tmp = REG_LINK_CTRL_E717;
    tmp = (tmp & 0xFE) | 0x01;
    REG_LINK_CTRL_E717 = tmp;
}

/*
 * reg_timer_setup_and_set_bits - Setup timer and set bits in 0xCC3A and 0xCC38
 * Address: 0xbcf2-0xbd04 (19 bytes)
 *
 * Sets bit 1 in REG_TIMER_ENABLE_B and REG_TIMER_ENABLE_A.
 */
void reg_timer_setup_and_set_bits(void)
{
    uint8_t val;

    /* Set bit 1 in REG_TIMER_ENABLE_B */
    val = REG_TIMER_ENABLE_B;
    val = (val & ~TIMER_ENABLE_B_BIT) | TIMER_ENABLE_B_BIT;
    REG_TIMER_ENABLE_B = val;

    /* Set bit 1 in REG_TIMER_ENABLE_A */
    val = REG_TIMER_ENABLE_A;
    val = (val & ~TIMER_ENABLE_A_BIT) | TIMER_ENABLE_A_BIT;
    REG_TIMER_ENABLE_A = val;
}

/*
 * reg_timer_init_and_start - Clear timer init flag, write 4 to timer CSR, then 2
 * Address: 0xbd05-0xbd13 (15 bytes)
 *
 * Clears G_TIMER_INIT_0B40, writes 4 to REG_TIMER3_CSR, then writes 2.
 */
void reg_timer_init_and_start(void)
{
    G_TIMER_INIT_0B40 = 0;
    REG_TIMER3_CSR = 0x04;
    REG_TIMER3_CSR = 0x02;
}

/*
 * reg_timer_clear_bits - Clear bit 1 in REG_TIMER_ENABLE_B and REG_TIMER_ENABLE_A
 * Address: 0xbd14-0xbd22 (15 bytes)
 */
void reg_timer_clear_bits(void)
{
    uint8_t val;

    val = REG_TIMER_ENABLE_B;
    REG_TIMER_ENABLE_B = val & ~TIMER_ENABLE_B_BIT;

    val = REG_TIMER_ENABLE_A;
    REG_TIMER_ENABLE_A = val & ~TIMER_ENABLE_A_BIT;
}

/*
 * reg_set_bit5 - Set bit 5 in register at DPTR
 * Address: 0xbd23-0xbd29 (7 bytes)
 */
void reg_set_bit5(__xdata uint8_t *reg)
{
    uint8_t val = *reg;
    val = (val & 0xDF) | 0x20;
    *reg = val;
}

/*
 * reg_clear_bits_5_6 - Clear bits 5 and 6 in register at DPTR
 * Address: 0xbd2a-0xbd32 (9 bytes)
 */
void reg_clear_bits_5_6(__xdata uint8_t *reg)
{
    uint8_t val;

    val = *reg;
    *reg = val & 0xDF;  /* Clear bit 5 */

    val = *reg;
    *reg = val & 0xBF;  /* Clear bit 6 */
}

/*
 * reg_read_cc3e_clear_bit1 - Read from REG_CPU_CTRL_CC3E and clear bit 1
 * Address: 0xbd33-0xbd39 (7 bytes)
 */
uint8_t reg_read_cc3e_clear_bit1(void)
{
    return REG_CPU_CTRL_CC3E & 0xFD;
}

/*
 * reg_set_bit6_generic - Set bit 6 in register at DPTR
 * Address: 0xbd3a-0xbd40 (7 bytes)
 */
void reg_set_bit6_generic(__xdata uint8_t *reg)
{
    uint8_t val = *reg;
    val = (val & 0xBF) | 0x40;
    *reg = val;
}

/*
 * reg_clear_bit1_cc3b - Clear bit 1 in REG_TIMER_CTRL_CC3B
 * Address: 0xbd41-0xbd48 (8 bytes)
 */
void reg_clear_bit1_cc3b(void)
{
    uint8_t val = REG_TIMER_CTRL_CC3B;
    REG_TIMER_CTRL_CC3B = val & ~TIMER_CTRL_START;
}

/*
 * reg_read_link_width - Read REG_LINK_WIDTH_E710 and mask bits 5-7
 * Address: 0xbd49-0xbd4f (7 bytes)
 *
 * Returns the link width from bits 5-7 of REG_LINK_WIDTH_E710.
 */
uint8_t reg_read_link_width(void)
{
    return REG_LINK_WIDTH_E710 & 0xE0;
}

/*
 * reg_read_link_status_e716 - Read REG_LINK_STATUS_E716 and mask bits 0-1
 * Address: 0xbd50-0xbd56 (7 bytes)
 */
uint8_t reg_read_link_status_e716(void)
{
    return REG_LINK_STATUS_E716 & 0xFC;
}

/*
 * reg_read_cpu_mode_next - Read REG_CPU_MODE_NEXT and mask bits 0-4
 * Address: 0xbd57-0xbd5d (7 bytes)
 */
uint8_t reg_read_cpu_mode_next(void)
{
    return REG_CPU_MODE_NEXT & 0x1F;
}

/*
 * reg_set_bit2 - Set bit 2 in register at DPTR
 * Address: 0xbd5e-0xbd64 (7 bytes)
 */
void reg_set_bit2(__xdata uint8_t *reg)
{
    uint8_t val = *reg;
    val = (val & 0xFB) | 0x04;
    *reg = val;
}

/*
 * reg_set_bit7 - Set bit 7 in register at DPTR
 * Address: 0xbd65-0xbd6b (7 bytes)
 */
void reg_set_bit7(__xdata uint8_t *reg)
{
    uint8_t val = *reg;
    val = (val & 0x7F) | 0x80;
    *reg = val;
}

/*
 * reg_read_phy_mode_lane_config - Read PHY mode and extract lane configuration
 * Address: 0xbe8b-0xbe96 (12 bytes) / 0xbefb-0xbf0e (also partial)
 *
 * Reads REG_PHY_MODE_E302, masks with 0x30 (bits 4-5), swaps nibbles,
 * masks with 0x0F, and returns the lane configuration.
 */
uint8_t reg_read_phy_mode_lane_config(void)
{
    uint8_t val;

    val = REG_PHY_MODE_E302;
    val = val & 0x30;            /* Keep bits 4-5 */
    val = (val >> 4) | (val << 4);  /* swap nibbles */
    val = val & 0x0F;            /* Keep low nibble */

    return val;
}

/*
 * reg_delay_param_setup - Setup delay parameters for bank read
 * Address: 0xbefb-0xbf04 (10 bytes)
 *
 * Sets R3=0xFF, R2=0x22, R1=0x69 and calls bank read at 0x538d.
 */
uint8_t reg_delay_param_setup(void)
{
    /* This calls into bank read routine - returns value from 0xFF2269 */
    return XDATA_REG8(0x2269);  /* Simplified - actual routine uses banked memory */
}

/*
 * reg_read_phy_lanes - Read PHY mode register and return lane count as nibble
 * Address: 0xbf04-0xbf0e (11 bytes)
 */
uint8_t reg_read_phy_lanes(void)
{
    uint8_t val;

    val = REG_PHY_MODE_E302;
    val = val & 0x30;             /* Mask bits 4-5 */
    val = (val >> 4) | (val << 4);  /* Swap nibbles */
    val = val & 0x0F;             /* Keep low nibble */

    return val;
}

/*
 * reg_clear_state_flags - Clear multiple state work flags to 0
 * Address: 0xbf8e-0xbfa2 (21 bytes)
 *
 * Clears G_STATE_WORK_0B3D, G_STATE_WORK_0B3E, G_XFER_STATE_0AF6,
 * and global at 0x07EE and G_TRANSFER_FLAG_0AF2.
 */
void reg_clear_state_flags(void)
{
    G_STATE_WORK_0B3D = 0;
    G_STATE_WORK_0B3E = 0;
    G_XFER_STATE_0AF6 = 0;
    G_SYS_FLAGS_07EE = 0;
    G_TRANSFER_FLAG_0AF2 = 0;
}

/*
 * init_sys_flags_07f0 - Initialize system flags at 0x07F0
 * Address: 0x4be6-0x4c03 (30 bytes)
 *
 * Initializes system configuration flags and clears bit 0 of REG_CPU_EXEC_STATUS_3.
 *
 * Original disassembly:
 *   4be6: mov dptr, #0x07f0
 *   4be9: mov a, #0x24
 *   4beb: movx @dptr, a
 *   4bec: inc dptr
 *   4bed: mov a, #0x04
 *   4bef: movx @dptr, a
 *   4bf0: inc dptr
 *   4bf1: mov a, #0x17
 *   4bf3: movx @dptr, a
 *   4bf4: inc dptr
 *   4bf5: mov a, #0x85
 *   4bf7: movx @dptr, a
 *   4bf8: inc dptr
 *   4bf9: clr a
 *   4bfa: movx @dptr, a
 *   4bfb: inc dptr
 *   4bfc: movx @dptr, a
 *   4bfd: mov dptr, #0xcc35
 *   4c00: movx a, @dptr
 *   4c01: anl a, #0xfe
 *   4c03: movx @dptr, a
 */
void init_sys_flags_07f0(void)
{
    G_SYS_FLAGS_07F0 = 0x24;
    G_SYS_FLAGS_07F1 = 0x04;
    G_SYS_FLAGS_07F2 = 0x17;
    G_SYS_FLAGS_07F3 = 0x85;
    G_SYS_FLAGS_07F4 = 0x00;
    G_SYS_FLAGS_07F5 = 0x00;
    REG_CPU_EXEC_STATUS_3 = REG_CPU_EXEC_STATUS_3 & 0xFE;
}

/* Forward declaration for loop helper */
extern void delay_loop_adb0(void);

/*
 * delay_short_e89d - Short delay with IDATA setup
 * Address: 0xe89d-0xe8a8 (12 bytes)
 *
 * Sets I_WORK_65 = 0x0F, I_WORK_60 = 0, then calls delay loop at 0xadb0.
 * The result is left in R7 (via I_WORK_65).
 *
 * Original disassembly:
 *   e89d: mov r0, #0x65      ; point to I_WORK_65
 *   e89f: mov @r0, #0x0f     ; I_WORK_65 = 0x0F
 *   e8a1: clr a
 *   e8a2: mov r0, #0x60      ; point to I_WORK_60 area
 *   e8a4: mov @r0, a         ; clear it
 *   e8a5: lcall 0xadb0       ; call delay loop
 *   e8a8: ret
 */
void delay_short_e89d(void)
{
    I_WORK_65 = 0x0F;
    *(__idata uint8_t *)0x60 = 0;
    delay_loop_adb0();
}

/*
 * delay_wait_e80a - Delay with parameters
 * Address: 0xe80a-0xe81x
 *
 * Waits for a specified delay using timer-based polling.
 * Parameters are passed in R4:R5 (delay value) and R7 (flags).
 */
void delay_wait_e80a(uint16_t delay, uint8_t flag)
{
    (void)delay;
    (void)flag;
    /* TODO: Implement timer-based delay */
}

