/*
 * ASM2464PD Firmware - Utility Functions (Keil C51 Version)
 *
 * Helper functions used throughout the firmware.
 * These are called from startup_0016 and other functions.
 */

#ifndef __UTILS_H__
#define __UTILS_H__

#include "types.h"

/*
 * idata_load_dword - Load 32-bit value from IDATA
 * Address: 0x0d78-0x0d83 (12 bytes)
 *
 * Loads 4 consecutive bytes from IDATA starting at given address.
 * Returns value in R4-R7 (standard Keil uint32_t return).
 *
 * Parameter: addr - IDATA address (0x00-0x7F)
 * Returns: 32-bit value (byte0 | byte1<<8 | byte2<<16 | byte3<<24)
 */
uint32_t idata_load_dword(uint8_t addr);

/*
 * idata_or_dword - Load 4 bytes from IDATA and OR them together
 * Address: inline helper
 *
 * This mimics the pattern:
 *   lcall idata_load_dword
 *   mov a, r4
 *   orl a, r5
 *   orl a, r6
 *   orl a, r7
 *
 * Returns: OR of all 4 bytes (0 if all zero)
 */
uint8_t idata_or_dword(uint8_t addr);

/*
 * cmp32_eq - Compare if two 32-bit values are equal
 * Address: 0x0d22-0x0d32 (17 bytes)
 *
 * Returns: 1 if equal, 0 if not equal
 */
uint8_t cmp32_eq(uint32_t a, uint32_t b);

/*
 * load_signatures_and_compare - Load and compare boot/transfer signatures
 * Address: 0x1b7e-0x1b87 (10 bytes)
 *
 * Loads IDATA[0x09-0x0c] and IDATA[0x6b-0x6e] and compares them.
 * Returns: 1 if signatures match, 0 if different
 */
uint8_t load_signatures_and_compare(void);

#endif /* __UTILS_H__ */
