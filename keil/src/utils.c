/*
 * ASM2464PD Firmware - Utility Functions (Keil C51 Version)
 *
 * Helper functions matching original firmware at specific addresses.
 */

#include "types.h"
#include "sfr.h"
#include "globals.h"

/*
 * idata_load_dword - Load 32-bit value from IDATA
 * Address: 0x0d78-0x0d83 (12 bytes)
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
uint32_t idata_load_dword(uint8_t addr)
{
    idata uint8_t *ptr = (idata uint8_t *)addr;
    uint32_t val;

    val = ptr[0];
    val |= ((uint32_t)ptr[1]) << 8;
    val |= ((uint32_t)ptr[2]) << 16;
    val |= ((uint32_t)ptr[3]) << 24;

    return val;
}

/*
 * idata_or_dword - Load 4 bytes from IDATA and OR them together
 *
 * This is the pattern used after idata_load_dword:
 *   ec: mov a, r4
 *   4d: orl a, r5
 *   4e: orl a, r6
 *   4f: orl a, r7
 *
 * By making this a separate function, startup_0016 will generate LCALL.
 */
uint8_t idata_or_dword(uint8_t addr)
{
    uint32_t val = idata_load_dword(addr);
    uint8_t b0 = (uint8_t)(val);
    uint8_t b1 = (uint8_t)(val >> 8);
    uint8_t b2 = (uint8_t)(val >> 16);
    uint8_t b3 = (uint8_t)(val >> 24);

    return b0 | b1 | b2 | b3;
}

/*
 * cmp32_eq - Compare if two 32-bit values are equal
 * Address: 0x0d22-0x0d32 (17 bytes)
 *
 * Original uses SUBB and ORL to check if difference is zero.
 */
uint8_t cmp32_eq(uint32_t a, uint32_t b)
{
    return (a == b) ? 1 : 0;
}

/*
 * load_signatures_and_compare - Load and compare boot/transfer signatures
 * Address: 0x1b7e-0x1b87 (10 bytes)
 *
 * Original disassembly:
 *   1b7e: mov r0, #0x09     ; point to boot sig
 *   1b80: lcall 0x0d78      ; load boot sig into R4-R7
 *   1b83: mov r0, #0x6b     ; point to transfer sig
 *   1b85: ljmp 0x0d90       ; jump to compare helper
 */
uint8_t load_signatures_and_compare(void)
{
    uint32_t boot_sig = idata_load_dword(0x09);
    uint32_t transfer_sig = idata_load_dword(0x6B);

    return cmp32_eq(boot_sig, transfer_sig);
}

/*
 * idata_compare_4bytes - Compare 4 IDATA bytes at two addresses
 *
 * Used by startup_0016 for byte-by-byte signature comparison.
 * Returns 1 if all 4 bytes match, 0 otherwise.
 */
uint8_t idata_compare_4bytes(uint8_t addr1, uint8_t addr2)
{
    idata uint8_t *p1 = (idata uint8_t *)addr1;
    idata uint8_t *p2 = (idata uint8_t *)addr2;

    if (p1[0] != p2[0]) return 0;
    if (p1[1] != p2[1]) return 0;
    if (p1[2] != p2[2]) return 0;
    if (p1[3] != p2[3]) return 0;

    return 1;
}
