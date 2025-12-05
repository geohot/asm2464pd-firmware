/*
 * ASM2464PD Firmware - Flash Driver
 *
 * SPI Flash controller interface for USB4/Thunderbolt to NVMe bridge.
 * Handles reading/writing to external SPI flash for firmware storage.
 *
 * Flash Controller Registers: 0xC89F-0xC8AE
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"

/*
 * flash_div16 - Divide 16-bit value by 8-bit divisor
 * Address: 0x0c0f-0x0c1c (14 bytes) - when R4=0, R6=0
 *
 * Simple case: R7/R5 division when upper bytes are zero.
 * Returns quotient in R7, remainder in R5.
 *
 * Original disassembly (simple path):
 *   0c0f: cjne r4, #0x00, 0x0c1d  ; check R4
 *   0c12: cjne r6, #0x00, 0x0c3e  ; check R6
 *   0c15: mov a, r7               ; dividend low
 *   0c16: mov 0xf0, r5            ; divisor to B
 *   0c18: div ab                  ; A = quotient, B = remainder
 *   0c19: mov r7, a               ; store quotient
 *   0c1a: mov r5, 0xf0            ; store remainder
 *   0c1c: ret
 */
uint8_t flash_div8(uint8_t dividend, uint8_t divisor)
{
    if (divisor == 0) return 0;
    return dividend / divisor;
}

/*
 * flash_mod8 - Get remainder of 8-bit division
 * Address: 0x0c0f-0x0c1c (part of div function)
 *
 * Returns remainder from dividend/divisor.
 */
uint8_t flash_mod8(uint8_t dividend, uint8_t divisor)
{
    if (divisor == 0) return 0;
    return dividend % divisor;
}

/*
 * flash_add_to_xdata16 - Add value to 16-bit XDATA location
 * Address: 0x0c64-0x0c79 (22 bytes)
 *
 * Adds a 16-bit value (in A:B) to 16-bit value at DPTR, DPTR+1.
 * With carry propagation.
 *
 * Original disassembly:
 *   0c64: xch a, 0xf0        ; swap A and B
 *   0c66: mov r0, a          ; R0 = low byte of addend
 *   0c67: inc dptr           ; point to high byte
 *   0c68: movx a, @dptr      ; read high byte
 *   0c69: add a, r0          ; add low addend to high
 *   0c6a: movx @dptr, a      ; store
 *   0c6b: xch a, 0xf0        ; restore A (high addend)
 *   0c6d: mov r0, a
 *   0c6e-0c70: dec dptr      ; point back to low byte
 *   0c76: movx a, @dptr      ; read low byte
 *   0c77: addc a, r0         ; add with carry
 *   0c78: movx @dptr, a
 *   0c79: ret
 */
void flash_add_to_xdata16(__xdata uint8_t *ptr, uint16_t val)
{
    uint16_t curr;
    curr = ptr[0] | ((uint16_t)ptr[1] << 8);
    curr += val;
    ptr[0] = (uint8_t)(curr & 0xFF);
    ptr[1] = (uint8_t)(curr >> 8);
}

/*
 * flash_write_byte - Write single byte to flash address
 * Address: 0x0c7a-0x0c86 (13 bytes) - when R3=1
 *
 * Writes byte in A to XDATA address in R2:R1.
 *
 * Original disassembly:
 *   0c7a: cjne r3, #0x01, 0x0c87
 *   0c7d: mov 0x82, r1        ; DPL = R1
 *   0c7f: mov 0x83, r2        ; DPH = R2
 *   0c81: movx @dptr, a       ; write byte
 *   0c82: mov a, 0xf0         ; get high byte from B
 *   0c84: inc dptr
 *   0c85: movx @dptr, a       ; write high byte
 *   0c86: ret
 */
void flash_write_word(__xdata uint8_t *ptr, uint16_t val)
{
    ptr[0] = (uint8_t)(val & 0xFF);
    ptr[1] = (uint8_t)(val >> 8);
}

/*
 * flash_write_idata - Write to IDATA via R1
 * Address: 0x0c87-0x0c8e (8 bytes) - when R3=0
 *
 * Writes word in A:B to IDATA address in R1.
 *
 * Original disassembly (R3 < 1 path):
 *   0c87: jnc 0x0c8f          ; check carry from compare
 *   0c89: mov @r1, a          ; store low byte
 *   0c8a: inc r1
 *   0c8b: mov @r1, 0xf0       ; store high byte from B
 *   0c8d: dec r1
 *   0c8e: ret
 */
void flash_write_idata_word(__idata uint8_t *ptr, uint16_t val)
{
    ptr[0] = (uint8_t)(val & 0xFF);
    ptr[1] = (uint8_t)(val >> 8);
}

/*
 * flash_write_r1_xdata - Write word to XDATA via R1 (indirect)
 * Address: 0x0c8f-0x0c98 (10 bytes) - when R3=0xFE
 *
 * Uses R1 as indirect XDATA pointer.
 *
 * Original disassembly:
 *   0c8f: cjne r3, #0xfe, 0x0c99
 *   0c92: movx @r1, a         ; store low byte via R1
 *   0c93: mov a, 0xf0         ; get high byte
 *   0c95: inc r1
 *   0c96: movx @r1, a         ; store high byte
 *   0c97: dec r1
 *   0c98: ret
 */
void flash_write_r1_xdata_word(uint8_t r1_addr, uint16_t val)
{
    /* Uses R1 as XDATA pointer - specific to 8051 indirect mode */
    __xdata uint8_t *ptr = (__xdata uint8_t *)(uint16_t)r1_addr;
    ptr[0] = (uint8_t)(val & 0xFF);
    ptr[1] = (uint8_t)(val >> 8);
}

/* Additional flash functions will be added as they are reversed */

