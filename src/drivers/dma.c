/*
 * ASM2464PD Firmware - DMA Driver
 *
 * DMA engine control for USB4/Thunderbolt to NVMe bridge.
 * Handles DMA transfers between USB, NVMe, and internal buffers.
 *
 * DMA Engine Registers: 0xC800-0xC9FF
 * SCSI/Mass Storage DMA: 0xCE40-0xCE6E
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"

/*
 * dma_clear_status - Clear DMA status flags
 * Address: 0x16f3-0x16fe (12 bytes)
 *
 * Clears bits 3 and 2 of DMA status register at 0xC8D6.
 * Bit 3 (0x08) and bit 2 (0x04) are error/done flags.
 *
 * Original disassembly:
 *   16f3: mov dptr, #0xc8d6
 *   16f6: movx a, @dptr
 *   16f7: anl a, #0xf7      ; clear bit 3
 *   16f9: movx @dptr, a
 *   16fa: movx a, @dptr
 *   16fb: anl a, #0xfb      ; clear bit 2
 *   16fd: movx @dptr, a
 *   16fe: ret
 */
void dma_clear_status(void)
{
    uint8_t val;

    val = REG_DMA_STATUS;
    val &= 0xF7;  /* Clear bit 3 */
    REG_DMA_STATUS = val;

    val = REG_DMA_STATUS;
    val &= 0xFB;  /* Clear bit 2 */
    REG_DMA_STATUS = val;
}

/*
 * dma_set_scsi_param3 - Set SCSI DMA parameter 3 to 0xFF
 * Address: 0x1709-0x1712 (10 bytes)
 *
 * Writes 0xFF to SCSI DMA parameter 3 register at 0xCE43,
 * then sets DPTR to 0xCE42 for subsequent operation.
 *
 * Original disassembly:
 *   1709: mov dptr, #0xce43
 *   170c: mov a, #0xff
 *   170e: movx @dptr, a
 *   170f: mov dptr, #0xce42
 *   1712: ret
 */
void dma_set_scsi_param3(void)
{
    REG_SCSI_DMA_PARAM3 = 0xFF;
    /* Note: Original also sets DPTR to 0xCE42 before return
     * for caller's use, but in C this is handled differently */
}

/*
 * dma_set_scsi_param1 - Set SCSI DMA parameter 1 to 0xFF
 * Address: 0x1713-0x171c (10 bytes)
 *
 * Writes 0xFF to SCSI DMA parameter 1 register at 0xCE41,
 * then sets DPTR to 0xCE40 for subsequent operation.
 *
 * Original disassembly:
 *   1713: mov dptr, #0xce41
 *   1716: mov a, #0xff
 *   1718: movx @dptr, a
 *   1719: mov dptr, #0xce40
 *   171c: ret
 */
void dma_set_scsi_param1(void)
{
    REG_SCSI_DMA_PARAM1 = 0xFF;
    /* Note: Original also sets DPTR to 0xCE40 before return */
}

/*
 * dma_reg_wait_bit - Wait for DMA register bit to be set
 * Address: 0x16ff-0x1708 (10 bytes)
 *
 * Reads value from DPTR, stores in R7, then calls reg_wait_bit_set
 * at 0x0ddd with address 0x045E and the read value.
 *
 * Original disassembly:
 *   16ff: movx a, @dptr     ; read value from caller's DPTR
 *   1700: mov r7, a         ; save to R7
 *   1701: mov dptr, #0x045e
 *   1704: lcall 0x0ddd      ; reg_wait_bit_set
 *   1707: mov a, r7
 *   1708: ret
 */
uint8_t dma_reg_wait_bit(__xdata uint8_t *ptr)
{
    uint8_t val;

    val = *ptr;
    /* Call reg_wait_bit_set(0x045E, val) */
    /* TODO: Implement reg_wait_bit_set */
    return val;
}

/*
 * dma_load_transfer_params - Load DMA transfer parameters from XDATA
 * Address: 0x171d-0x172b (15 bytes)
 *
 * Loads parameters from 0x0472-0x0473 and calls flash_func_0c0f.
 *
 * Original disassembly:
 *   171d: mov dptr, #0x0472
 *   1720: movx a, @dptr     ; read param from 0x0472
 *   1721: mov r6, a
 *   1722: inc dptr
 *   1723: movx a, @dptr     ; read param from 0x0473
 *   1724: mov r7, a
 *   1725: ljmp 0x0c0f       ; flash_func_0c0f(0, R3, R6, R7)
 */
void dma_load_transfer_params(void)
{
    uint8_t param1, param2;

    param1 = XDATA8(0x0472);
    param2 = XDATA8(0x0473);

    /* TODO: Call flash_func_0c0f(0, BANK0_R3, param1, param2) */
    (void)param1;
    (void)param2;
}

/* Additional DMA functions will be added as they are reversed */

