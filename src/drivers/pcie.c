/*
 * ASM2464PD Firmware - PCIe Driver
 *
 * PCIe interface controller for USB4/Thunderbolt to NVMe bridge
 * Handles PCIe TLP transactions, configuration space access, and link management
 *
 * PCIe registers are at 0xB200-0xB4FF
 */

#include "../types.h"
#include "../sfr.h"
#include "../registers.h"
#include "../globals.h"

/*
 * pcie_clear_and_trigger - Clear status flags and trigger transaction
 * Address: 0x999d-0x99ae (18 bytes)
 *
 * Sequence:
 *   1. Write 1 to status (clear error flag)
 *   2. Write 2 to status (clear complete flag)
 *   3. Write 4 to status (clear busy flag)
 *   4. Write 0x0F to trigger register to start transaction
 *
 * Original disassembly:
 *   999d: mov dptr, #0xb296     ; REG_PCIE_STATUS
 *   99a0: mov a, #0x01
 *   99a2: movx @dptr, a         ; write 1
 *   99a3: inc a                 ; a = 2
 *   99a4: movx @dptr, a         ; write 2
 *   99a5: mov a, #0x04
 *   99a7: movx @dptr, a         ; write 4
 *   99a8: mov dptr, #0xb254     ; REG_PCIE_TRIGGER
 *   99ab: mov a, #0x0f
 *   99ad: movx @dptr, a         ; write 0x0F
 *   99ae: ret
 */
void pcie_clear_and_trigger(void)
{
    REG_PCIE_STATUS = 0x01;  /* Clear error flag */
    REG_PCIE_STATUS = 0x02;  /* Clear complete flag */
    REG_PCIE_STATUS = 0x04;  /* Clear busy flag */
    REG_PCIE_TRIGGER = 0x0F; /* Trigger all lanes */
}

/*
 * pcie_get_completion_status - Check if transaction completed
 * Address: 0x99eb-0x99f5 (11 bytes)
 *
 * Returns bit 2 of status register shifted to position 0.
 * Returns 1 if busy/complete, 0 otherwise.
 *
 * Original disassembly:
 *   99eb: mov dptr, #0xb296     ; REG_PCIE_STATUS
 *   99ee: movx a, @dptr         ; read status
 *   99ef: anl a, #0x04          ; mask bit 2
 *   99f1: rrc a                 ; rotate right
 *   99f2: rrc a                 ; rotate right (now bit 0)
 *   99f3: anl a, #0x3f          ; mask upper bits
 *   99f5: ret
 */
uint8_t pcie_get_completion_status(void)
{
    return (REG_PCIE_STATUS & 0x04) >> 2;
}

/*
 * pcie_get_link_speed - Get PCIe link speed from status
 * Address: 0x9a60-0x9a6b (12 bytes)
 *
 * Extracts bits 7:5 from link status register.
 * Returns link speed encoding (0-7).
 *
 * Original disassembly:
 *   9a60: mov dptr, #0xb22a     ; REG_PCIE_LINK_STATUS
 *   9a63: movx a, @dptr         ; read link status
 *   9a64: anl a, #0xe0          ; mask bits 7:5
 *   9a66: swap a                ; swap nibbles
 *   9a67: rrc a                 ; rotate right
 *   9a68: anl a, #0x07          ; mask to 3 bits
 *   9a6a: mov r7, a             ; return value
 *   9a6b: ret
 */
uint8_t pcie_get_link_speed(void)
{
    return (REG_PCIE_LINK_STATUS >> 5) & 0x07;
}

/*
 * pcie_set_byte_enables - Set TLP byte enables and length mode
 * Address: 0x9a30-0x9a3a (11 bytes)
 *
 * Sets byte enable mask for TLP and configures length to 0x20.
 *
 * Original disassembly:
 *   9a30: mov dptr, #0xb217     ; REG_PCIE_BYTE_EN
 *   9a33: movx @dptr, a         ; write byte enables from A
 *   9a34: mov dptr, #0xb216     ; REG_PCIE_TLP_LENGTH
 *   9a37: mov a, #0x20
 *   9a39: movx @dptr, a         ; write 0x20 (32 dwords)
 *   9a3a: ret
 */
void pcie_set_byte_enables(uint8_t byte_en)
{
    REG_PCIE_BYTE_EN = byte_en;
    REG_PCIE_TLP_LENGTH = 0x20;
}

/*
 * pcie_read_completion_data - Write status and read completion data
 * Address: 0x9a74-0x9a7e (11 bytes)
 *
 * Sets status to 0x02 (complete) then reads completion data register.
 *
 * Original disassembly:
 *   9a74: mov dptr, #0xb296     ; REG_PCIE_STATUS
 *   9a77: mov a, #0x02
 *   9a79: movx @dptr, a         ; write 2 to status
 *   9a7a: mov dptr, #0xb22c     ; REG_PCIE_CPL_DATA
 *   9a7d: movx a, @dptr         ; read completion data
 *   9a7e: ret
 */
uint8_t pcie_read_completion_data(void)
{
    REG_PCIE_STATUS = 0x02;
    return REG_PCIE_CPL_DATA;
}

/*
 * pcie_write_status_complete - Write completion status flag
 * Address: 0x9a95-0x9a9b (7 bytes)
 *
 * Writes 0x04 to status register to indicate completion/busy clear.
 *
 * Original disassembly:
 *   9a95: mov dptr, #0xb296     ; REG_PCIE_STATUS
 *   9a98: mov a, #0x04
 *   9a9a: movx @dptr, a         ; write 4
 *   9a9b: ret
 */
void pcie_write_status_complete(void)
{
    REG_PCIE_STATUS = 0x04;
}

/*
 * pcie_init - Initialize PCIe interface
 * Address: 0x9902-0x990b (10 bytes)
 *
 * Initializes PCIe controller by clearing bit configuration
 * and calling initialization routine.
 *
 * Original disassembly:
 *   9902: mov r0, #0x66
 *   9904: lcall 0x0db9       ; reg_clear_bit type function
 *   9907: lcall 0xde7e       ; initialization
 *   990a: mov a, r7
 *   990b: ret
 */
uint8_t pcie_init(void)
{
    /* Clear configuration at IDATA 0x66 */
    /* Call reg_clear_bit with R0=0x66 via 0x0db9 */
    /* Then call initialization at 0xde7e */
    /* Returns status in R7/A */

    /* TODO: Implement actual initialization sequence */
    return 0;
}

/*
 * pcie_init_alt - Alternative PCIe initialization
 * Address: 0x990c-0x9915 (10 bytes)
 *
 * Same pattern as pcie_init, possibly for different link mode.
 *
 * Original disassembly:
 *   990c: mov r0, #0x66
 *   990e: lcall 0x0db9
 *   9911: lcall 0xde7e
 *   9914: mov a, r7
 *   9915: ret
 */
uint8_t pcie_init_alt(void)
{
    /* Same as pcie_init - may be called in different contexts */
    return 0;
}

/*
 * pcie_set_idata_params - Set IDATA parameters for transaction
 * Address: 0x99f6-0x99ff (10 bytes)
 *
 * Sets IDATA location 0x65 to 0x0F and 0x63 to 0x00.
 * Used to configure byte enables and address offset.
 *
 * Original disassembly:
 *   99f6: mov r0, #0x65
 *   99f8: mov @r0, #0x0f        ; IDATA[0x65] = 0x0F
 *   99fa: mov r0, #0x63
 *   99fc: mov @r0, #0x00        ; IDATA[0x63] = 0x00
 *   99fe: inc r0                ; r0 = 0x64
 *   99ff: ret
 */
void pcie_set_idata_params(void)
{
    __asm
        mov     r0, #0x65
        mov     @r0, #0x0f
        mov     r0, #0x63
        mov     @r0, #0x00
        inc     r0
    __endasm;
}

/*
 * pcie_clear_address_regs - Clear address offset registers
 * Address: 0x9a9c-0x9aa2 (7 bytes)
 *
 * Clears IDATA locations 0x63 and 0x64 (address offset).
 *
 * Original disassembly:
 *   9a9c: clr a
 *   9a9d: mov r0, #0x63
 *   9a9f: mov @r0, a            ; IDATA[0x63] = 0
 *   9aa0: inc r0
 *   9aa1: mov @r0, a            ; IDATA[0x64] = 0
 *   9aa2: ret
 */
void pcie_clear_address_regs(void)
{
    __asm
        clr     a
        mov     r0, #0x63
        mov     @r0, a
        inc     r0
        mov     @r0, a
    __endasm;
}

/*
 * pcie_inc_txn_counters - Increment PCIe transaction counters
 * Address: 0x9a8a-0x9a94 (11 bytes)
 *
 * Increments both transaction count bytes at 0x05a6 and 0x05a7.
 * Used for tracking PCIe transactions for debugging/statistics.
 *
 * Original disassembly:
 *   9a8a: mov dptr, #0x05a6
 *   9a8d: movx a, @dptr         ; read low byte
 *   9a8e: inc a
 *   9a8f: movx @dptr, a         ; write low byte
 *   9a90: inc dptr              ; dptr = 0x05a7
 *   9a91: movx a, @dptr         ; read high byte
 *   9a92: inc a
 *   9a93: movx @dptr, a         ; write high byte
 *   9a94: ret
 */
void pcie_inc_txn_counters(void)
{
    G_PCIE_TXN_COUNT_LO++;
    G_PCIE_TXN_COUNT_HI++;
}

/*
 * pcie_get_txn_count_hi - Get high byte of transaction count
 * Address: 0x9aa9-0x9ab2 (10 bytes)
 *
 * Reads transaction count high byte and compares with IDATA[0x25].
 * Returns difference (used for transaction tracking).
 *
 * Original disassembly:
 *   9aa9: mov dptr, #0x05a7
 *   9aac: movx a, @dptr         ; read high count
 *   9aad: mov r7, a             ; save to r7
 *   9aae: mov a, 0x25           ; get IDATA[0x25]
 *   9ab0: clr c
 *   9ab1: subb a, r7            ; a = IDATA[0x25] - count_hi
 *   9ab2: ret
 */
uint8_t pcie_get_txn_count_hi(void)
{
    return G_PCIE_TXN_COUNT_HI;
}

/*
 * pcie_write_status_error - Clear error status flag
 * Address: inline pattern
 *
 * Writes 0x01 to status register to clear error flag.
 */
void pcie_write_status_error(void)
{
    REG_PCIE_STATUS = 0x01;
}

/*
 * pcie_write_status_done - Clear completion status flag
 * Address: inline pattern
 *
 * Writes 0x02 to status register to clear completion flag.
 */
void pcie_write_status_done(void)
{
    REG_PCIE_STATUS = 0x02;
}

/*
 * pcie_check_status_complete - Check if transaction complete bit set
 * Address: inline from pattern in pcie_set_address
 *
 * Returns non-zero if status bit 1 (complete) is set.
 */
uint8_t pcie_check_status_complete(void)
{
    return REG_PCIE_STATUS & 0x02;
}

/*
 * pcie_check_status_error - Check if error bit set
 * Address: inline from pattern in pcie_set_address
 *
 * Returns non-zero if status bit 0 (error) is set.
 */
uint8_t pcie_check_status_error(void)
{
    return REG_PCIE_STATUS & 0x01;
}
