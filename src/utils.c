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
