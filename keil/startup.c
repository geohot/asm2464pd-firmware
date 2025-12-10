/*
 * ASM2464PD Firmware - Startup Code (Keil C51 Version)
 *
 * startup_0016 - Boot state verification
 * Address: 0x0016-0x0103 (238 bytes)
 */

#include "types.h"
#include "sfr.h"
#include "globals.h"

/*
 * startup_0016 - Boot state verification and initialization
 * Address: 0x0016-0x0103 (238 bytes)
 *
 * Boot states written to XDATA[0x0001]:
 *   0: Normal boot, signatures zero
 *   1: Cold boot, secondary signature non-zero
 *   2: Boot mode == 5 (state 5 with mode 0x80)
 *   3: Signature mismatch
 *   4: Boot mode == 2 or 4
 *   5: Boot mode == 5 (alt path)
 *   6: Signature mismatch (clr c path)
 *   7: Signature mismatch (mode != 0x80)
 */
void startup_0016(void)
{
    uint8_t boot_mode;
    uint8_t state_6a;

    /* Clear boot state */
    G_IO_CMD_TYPE = 0;

    /* Check transfer signature at IDATA[0x6B-0x6E] */
    if ((I_TRANSFER_6B | I_TRANSFER_6C | I_TRANSFER_6D | I_TRANSFER_6E) == 0) {
        /* Transfer signature is zero - check boot signature */
        if ((I_BOOT_SIG_0 | I_BOOT_SIG_1 | I_BOOT_SIG_2 | I_BOOT_SIG_3) == 0) {
            /* Both zero - normal boot */
            return;
        }
        /* Boot signature non-zero - set state 1 */
        G_IO_CMD_TYPE = 1;
        return;
    }

    /* Transfer signature non-zero - check boot mode */
    boot_mode = G_XFER_STATE_0AF3;

    if (boot_mode == 0x80) {
        /* Mode 0x80 */
        state_6a = I_STATE_6A;

        if (state_6a == 1 || state_6a == 3 || state_6a == 8) {
            goto compare_sigs_80;
        }
        if (state_6a == 2 || state_6a == 4) {
            G_IO_CMD_TYPE = 4;
            return;
        }
        if (state_6a == 5) {
            G_IO_CMD_TYPE = 2;
            return;
        }
        return;
    } else {
        /* Mode != 0x80 */
        state_6a = I_STATE_6A;

        if (state_6a == 1 || state_6a == 3 || state_6a == 8) {
            goto compare_sigs_alt;
        }
        if (state_6a == 2 || state_6a == 4) {
            goto compare_sigs_alt;
        }
        if (state_6a == 5) {
            G_IO_CMD_TYPE = 5;
            return;
        }
        return;
    }

compare_sigs_80:
    /* Compare signatures byte-by-byte */
    if (I_TRANSFER_6B == I_BOOT_SIG_0 &&
        I_TRANSFER_6C == I_BOOT_SIG_1 &&
        I_TRANSFER_6D == I_BOOT_SIG_2 &&
        I_TRANSFER_6E == I_BOOT_SIG_3) {
        return;  /* Match - normal boot */
    }
    /* Mismatch - set state 3 or 4 based on comparison */
    /* Simplified: set state 3 */
    G_IO_CMD_TYPE = 3;
    return;

compare_sigs_alt:
    /* Compare signatures byte-by-byte */
    if (I_TRANSFER_6B == I_BOOT_SIG_0 &&
        I_TRANSFER_6C == I_BOOT_SIG_1 &&
        I_TRANSFER_6D == I_BOOT_SIG_2 &&
        I_TRANSFER_6E == I_BOOT_SIG_3) {
        return;  /* Match */
    }
    /* Mismatch */
    G_IO_CMD_TYPE = 7;
    return;
}
