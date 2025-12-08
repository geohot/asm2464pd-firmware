/*
 * ASM2464PD Firmware - 32-bit Math Functions
 *
 * Low-level arithmetic operations that match the original firmware.
 * These functions operate directly on registers R0-R7 using the
 * original firmware's calling convention:
 *   - First operand:  R4:R5:R6:R7 (MSB:...:LSB)
 *   - Second operand: R0:R1:R2:R3 (MSB:...:LSB)
 *   - Result: R4:R5:R6:R7
 */

#include "types.h"

/*
 * add32 - 32-bit addition
 * Address: 0x0c9e-0x0caa (13 bytes)
 *
 * R4:R5:R6:R7 = R4:R5:R6:R7 + R0:R1:R2:R3
 *
 * Original disassembly:
 *   0c9e: mov a, r7    ; Start with LSB
 *   0c9f: add a, r3    ; Add without carry
 *   0ca0: mov r7, a
 *   0ca1: mov a, r6
 *   0ca2: addc a, r2   ; Add with carry
 *   0ca3: mov r6, a
 *   0ca4: mov a, r5
 *   0ca5: addc a, r1
 *   0ca6: mov r5, a
 *   0ca7: mov a, r4
 *   0ca8: addc a, r0   ; MSB with carry
 *   0ca9: mov r4, a
 *   0caa: ret
 */
void add32(void) __naked
{
    __asm
        mov a, r7
        add a, r3
        mov r7, a
        mov a, r6
        addc a, r2
        mov r6, a
        mov a, r5
        addc a, r1
        mov r5, a
        mov a, r4
        addc a, r0
        mov r4, a
        ret
    __endasm;
}

/*
 * sub32 - 32-bit subtraction
 * Address: 0x0cab-0x0cb8 (14 bytes)
 *
 * R4:R5:R6:R7 = R4:R5:R6:R7 - R0:R1:R2:R3
 *
 * Original disassembly:
 *   0cab: clr c        ; Clear carry for subtraction
 *   0cac: mov a, r7
 *   0cad: subb a, r3   ; Subtract with borrow
 *   0cae: mov r7, a
 *   0caf: mov a, r6
 *   0cb0: subb a, r2
 *   0cb1: mov r6, a
 *   0cb2: mov a, r5
 *   0cb3: subb a, r1
 *   0cb4: mov r5, a
 *   0cb5: mov a, r4
 *   0cb6: subb a, r0
 *   0cb7: mov r4, a
 *   0cb8: ret
 */
void sub32(void) __naked
{
    __asm
        clr c
        mov a, r7
        subb a, r3
        mov r7, a
        mov a, r6
        subb a, r2
        mov r6, a
        mov a, r5
        subb a, r1
        mov r5, a
        mov a, r4
        subb a, r0
        mov r4, a
        ret
    __endasm;
}

/*
 * mul32 - 32-bit multiplication
 * Address: 0x0cb9-0x0d07 (79 bytes)
 *
 * R4:R5:R6:R7 = R4:R5:R6:R7 * R0:R1:R2:R3 (lower 32 bits of result)
 *
 * This implements a full 32x32->32 bit multiplication using
 * repeated 8x8->16 multiplications (mul ab).
 *
 * Note: 0xf0 is the B register in 8051.
 */
void mul32(void) __naked
{
    __asm
        ; R0*R7 -> partial product
        mov a, r0
        mov b, r7           ; B = R7
        mul ab              ; A = low, B = high
        xch a, r4           ; Save low in R4, get R4 for later

        ; R3*R4_orig -> add to partial
        mov b, r3           ; B = R3
        mul ab              ; A = low(R3*R4), B = high
        add a, r4           ; Add low bytes
        mov r4, a           ; R4 = accumulated

        ; R1*R6 -> add to partial
        mov a, r1
        mov b, r6           ; B = R6
        mul ab
        add a, r4
        mov r4, a

        ; R2*R5 -> add to partial
        mov b, r2           ; B = R2
        mov a, r5
        mul ab
        add a, r4
        mov r4, a

        ; R2*R6 -> next byte
        mov a, r2
        mov b, r6           ; B = R6
        mul ab
        xch a, r5           ; Save, get R5
        mov r0, b           ; Save high byte

        ; R3*R5_orig
        mov b, r3           ; B = R3
        mul ab
        add a, r5
        xch a, r4
        addc a, r0
        add a, b            ; Add high byte
        mov r5, a

        ; R1*R7
        mov a, r1
        mov b, r7           ; B = R7
        mul ab
        add a, r4
        xch a, r5
        addc a, b
        mov r4, a

        ; R3*R6 -> final byte
        mov a, r3
        mov b, r6           ; B = R6
        mul ab
        mov r6, a
        mov r1, b           ; Save high

        ; R3*R7
        mov a, r3
        mov b, r7           ; B = R7
        mul ab
        xch a, r7           ; R7 = low byte result
        xch a, b            ; A = high, B = orig
        add a, r6
        xch a, r5
        addc a, r1
        mov r6, a
        clr a
        addc a, r4
        mov r4, a

        ; R2*B (R2*R7_orig)
        mov a, r2
        mul ab
        add a, r5
        xch a, r6
        addc a, b
        mov r5, a
        clr a
        addc a, r4
        mov r4, a

        ret
    __endasm;
}

/*
 * or32 - 32-bit bitwise OR
 * Address: 0x0d08-0x0d14 (13 bytes)
 *
 * R4:R5:R6:R7 = R4:R5:R6:R7 | R0:R1:R2:R3
 *
 * Original disassembly:
 *   0d08: mov a, r7
 *   0d09: orl a, r3
 *   0d0a: mov r7, a
 *   0d0b: mov a, r6
 *   0d0c: orl a, r2
 *   0d0d: mov r6, a
 *   0d0e: mov a, r5
 *   0d0f: orl a, r1
 *   0d10: mov r5, a
 *   0d11: mov a, r4
 *   0d12: orl a, r0
 *   0d13: mov r4, a
 *   0d14: ret
 */
void or32(void) __naked
{
    __asm
        mov a, r7
        orl a, r3
        mov r7, a
        mov a, r6
        orl a, r2
        mov r6, a
        mov a, r5
        orl a, r1
        mov r5, a
        mov a, r4
        orl a, r0
        mov r4, a
        ret
    __endasm;
}

/*
 * xor32 - 32-bit bitwise XOR
 * Address: 0x0d15-0x0d21 (13 bytes)
 *
 * R4:R5:R6:R7 = R4:R5:R6:R7 ^ R0:R1:R2:R3
 *
 * Original disassembly:
 *   0d15: mov a, r7
 *   0d16: xrl a, r3
 *   0d17: mov r7, a
 *   0d18: mov a, r6
 *   0d19: xrl a, r2
 *   0d1a: mov r6, a
 *   0d1b: mov a, r5
 *   0d1c: xrl a, r1
 *   0d1d: mov r5, a
 *   0d1e: mov a, r4
 *   0d1f: xrl a, r0
 *   0d20: mov r4, a
 *   0d21: ret
 */
void xor32(void) __naked
{
    __asm
        mov a, r7
        xrl a, r3
        mov r7, a
        mov a, r6
        xrl a, r2
        mov r6, a
        mov a, r5
        xrl a, r1
        mov r5, a
        mov a, r4
        xrl a, r0
        mov r4, a
        ret
    __endasm;
}

/*
 * mul16x16 - 16x16-bit multiplication returning 24-bit result
 * Address: 0x0bfd-0x0c0e (18 bytes)
 *
 * Input: R6:R7 (16-bit multiplicand), R4:R5 (16-bit multiplier)
 * Output: R6:R7 (lower 16 bits), overflow in R0
 *
 * This is a specialized multiply used for index calculations.
 *
 * Original disassembly:
 *   0bfd: mov a, r7    ; A = R7 (low multiplicand)
 *   0bfe: mov b, r5    ; B = R5 (low multiplier)
 *   0c00: mul ab       ; R0 = high, A = low
 *   0c01: mov r0, b    ; Save high byte
 *   0c03: xch a, r7    ; R7 = low result, A = orig R7
 *   0c04: mov b, r4    ; B = R4 (high multiplier)
 *   0c06: mul ab       ; R7_orig * R4
 *   0c07: add a, r0    ; Add to running total
 *   0c08: xch a, r6    ; R6 = mid result, A = orig R6
 *   0c09: mov b, r5    ; B = R5
 *   0c0b: mul ab       ; R6_orig * R5
 *   0c0c: add a, r6    ; Add mid bytes
 *   0c0d: mov r6, a    ; Store result
 *   0c0e: ret
 */
void mul16x16(void) __naked
{
    __asm
        mov a, r7
        mov b, r5
        mul ab
        mov r0, b           ; R0 = high byte of R7*R5
        xch a, r7           ; R7 = low byte, A = orig R7
        mov b, r4           ; B = R4
        mul ab              ; A = low(R7*R4)
        add a, r0           ; Add high byte from first mul
        xch a, r6           ; R6 = mid, A = orig R6
        mov b, r5           ; B = R5
        mul ab              ; A = low(R6*R5)
        add a, r6           ; Add to mid
        mov r6, a           ; Store final mid byte
        ret
    __endasm;
}
