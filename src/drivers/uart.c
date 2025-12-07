/*
 * ASM2464PD Firmware - UART Driver
 *
 * Dedicated UART controller for debug output on ASM2464PD USB4/Thunderbolt
 * to NVMe bridge controller. Used for firmware debug tracing.
 *
 *===========================================================================
 * UART CONTROLLER ARCHITECTURE
 *===========================================================================
 *
 * Hardware Configuration:
 * - Fixed 921600 baud, 8N1 (no configuration registers)
 * - TX pin: B21, RX pin: A21
 * - Dedicated UART (NOT standard 8051 SBUF/TI/RI)
 * - Based on ASMedia USB host controller UART design
 * - 16-byte transmit FIFO
 *
 * Register Map (0xC000-0xC00F):
 * ┌──────────┬──────────────────────────────────────────────────────────┐
 * │ Address  │ Description                                              │
 * ├──────────┼──────────────────────────────────────────────────────────┤
 * │ 0xC000   │ UART base / control                                      │
 * │ 0xC001   │ THR (WO) - Transmit Holding Register                     │
 * │          │ RBR (RO) - Receive Buffer Register                       │
 * │ 0xC002   │ IER - Interrupt Enable Register                          │
 * │ 0xC004   │ FCR (WO) - FIFO Control Register                         │
 * │          │ IIR (RO) - Interrupt Identification Register             │
 * │ 0xC006   │ TFBF - Transmit FIFO Buffer Full                         │
 * │ 0xC007   │ LCR - Line Control Register                              │
 * │ 0xC008   │ MCR - Modem Control Register                             │
 * │ 0xC009   │ LSR - Line Status Register                               │
 * │ 0xC00A   │ MSR - Modem Status Register                              │
 * └──────────┴──────────────────────────────────────────────────────────┘
 *
 * Data Flow:
 * ┌─────────────────────────────────────────────────────────────────────┐
 * │                        UART SUBSYSTEM                              │
 * ├─────────────────────────────────────────────────────────────────────┤
 * │                                                                     │
 * │  8051 Core ──write──> THR ──> TX FIFO ──> TX Shift Reg ──> TX Pin  │
 * │                       │         (16 bytes)                         │
 * │                       └─> Check TFBF for full                      │
 * │                                                                     │
 * │  RX Pin ──> RX Shift Reg ──> RX FIFO ──> RBR ──read──> 8051 Core   │
 * │                              (16 bytes)                            │
 * │                                                                     │
 * │  Note: No flow control, transmit is fire-and-forget                │
 * │                                                                     │
 * └─────────────────────────────────────────────────────────────────────┘
 *
 * Usage Pattern:
 * - Debug output only (no receive processing in stock firmware)
 * - uart_puthex() for hex byte output (most common)
 * - uart_putdigit() for single decimal digit
 * - uart_puts() for string output from code memory
 * - uart_putc() for single character output
 * - uart_newline() for CR+LF sequence
 *
 * Debug Output Format:
 * - Trace messages: "\nXX:YY]" where XX:YY are hex register values
 * - Used for PCIe/NVMe command tracing
 * - Called from bank 1 debug routines (0xAF5E+)
 *
 *===========================================================================
 * IMPLEMENTATION STATUS
 *===========================================================================
 * uart_puthex        [DONE] 0x51c7-0x51e5 - Print byte as hex
 * uart_putdigit      [DONE] 0x51e6-0x51ee - Print single digit
 * uart_putc          [DONE] 0x5398-0x53a0 - Print single character (inline)
 * uart_puts          [DONE] 0x538d-0x53a6 - Print string from code memory
 * uart_newline       [DONE] 0xaf5e-0xaf66 - Print CR+LF (bank 1)
 *
 * Total: 5 functions implemented
 *===========================================================================
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"

/*
 * uart_putc - Print a single character
 * Address: 0x5398-0x53a0 (inline in uart_puts loop)
 *
 * Writes a single character to the UART transmit register.
 * No FIFO check - relies on baud rate being fast enough.
 *
 * Original disassembly (inline in uart_puts):
 *   5398: mov dptr, #0xc001   ; UART THR
 *   539b: mov a, r7           ; get character
 *   539c: movx @dptr, a       ; write to THR
 */
void uart_putc(uint8_t ch)
{
    REG_UART_THR = ch;
}

/*
 * uart_newline - Print carriage return and line feed
 * Address: 0xaf5e-0xaf66 (9 bytes, in bank 1)
 *
 * Outputs standard CR+LF sequence for newline.
 *
 * Original disassembly:
 *   af5e: mov dptr, #0xc001   ; UART THR
 *   af61: mov a, #0x0a        ; LF
 *   af63: movx @dptr, a       ; write LF
 *   af64: mov a, #0x0d        ; CR
 *   af66: movx @dptr, a       ; write CR
 */
void uart_newline(void)
{
    REG_UART_THR = '\n';  /* LF = 0x0A */
    REG_UART_THR = '\r';  /* CR = 0x0D */
}

/*
 * uart_puthex - Print a byte as two hex characters
 * Address: 0x51c7-0x51e5 (31 bytes)
 *
 * From ghidra.c FUN_CODE_51c7:
 *   Prints high nibble then low nibble, using '0'-'9' for 0-9 and 'A'-'F' for 10-15.
 *   Actually uses '7' + value for A-F (since 'A' - 10 = '7')
 *
 * Original disassembly:
 *   51c7: mov a, r7           ; get param
 *   51c8: swap a              ; get high nibble
 *   51c9: anl a, #0x0f        ; mask to 4 bits
 *   51cb: mov r6, a           ; save
 *   51cc: clr c
 *   51cd: subb a, #0x0a       ; compare to 10
 *   51cf: mov r5, #0x37       ; assume >= 10, use '7' as base
 *   51d1: jnc 51d5            ; if >= 10, skip
 *   51d3: mov r5, #0x30       ; < 10, use '0' as base
 *   51d5: mov a, r5           ; get base char
 *   51d6: add a, r6           ; add nibble value
 *   51d7: mov dptr, #0xc001   ; UART THR
 *   51da: movx @dptr, a       ; write char
 *   ... repeat for low nibble ...
 */
void uart_puthex(uint8_t val)
{
    uint8_t nibble;
    uint8_t base;

    /* Print high nibble */
    nibble = (val >> 4) & 0x0F;
    base = (nibble >= 10) ? '7' : '0';  /* '7' + 10 = 'A' */
    REG_UART_THR = base + nibble;

    /* Print low nibble */
    nibble = val & 0x0F;
    base = (nibble >= 10) ? '7' : '0';
    REG_UART_THR = base + nibble;
}

/*
 * uart_putdigit - Print a single digit character
 * Address: 0x51e6-0x51ee (9 bytes)
 *
 * From ghidra.c FUN_CODE_51e6:
 *   REG_UART_THR_RBR = param_1 + '0';
 *
 * Original disassembly:
 *   51e6: ef             mov a, r7
 *   51e7: 24 30          add a, #0x30     ; add '0'
 *   51e9: 90 c0 01       mov dptr, #0xc001
 *   51ec: f0             movx @dptr, a
 *   51ed: 22             ret
 */
void uart_putdigit(uint8_t digit)
{
    REG_UART_THR = digit + '0';
}

/*
 * uart_puts - Print a null-terminated string from code memory
 * Address: 0x538d-0x53a6 (26 bytes)
 *
 * Outputs characters from a code memory pointer until null terminator.
 * Uses generic memory read helper at 0x0bc8 to read from code space.
 *
 * Parameters:
 *   str - pointer to string in code memory (__code)
 *
 * Original disassembly:
 *   538d: lcall 0x0bc8       ; read byte from code memory (R3:R2:R1 = ptr)
 *   5390: mov r7, a          ; save character
 *   5391: mov r5, a          ; copy for zero check
 *   5392: rlc a              ; get sign bit
 *   5393: subb a, 0xe0       ; compare with ACC (trick for zero check)
 *   5395: orl a, r5          ; combine
 *   5396: jz 53a6            ; if zero, done
 *   5398: mov dptr, #0xc001  ; UART THR
 *   539b: mov a, r7          ; get character
 *   539c: movx @dptr, a      ; write to THR
 *   539d: mov a, #0x01       ; increment pointer
 *   539f: add a, r1          ; low byte
 *   53a0: mov r1, a
 *   53a1: clr a
 *   53a2: addc a, r2         ; high byte
 *   53a3: mov r2, a
 *   53a4: sjmp 538d          ; loop
 *   53a6: ret
 */
void uart_puts(__code const char *str)
{
    char ch;

    while ((ch = *str++) != '\0') {
        REG_UART_THR = ch;
    }
}
