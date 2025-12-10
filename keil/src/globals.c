/*
 * ASM2464PD Firmware - Global Variable Definitions (Keil C51 Version)
 *
 * Global variables in XRAM and IDATA at fixed addresses.
 * Uses Keil's _at_ syntax for absolute addressing.
 */

#include "types.h"

/*===========================================================================
 * IDATA Work Variables (0x00-0x7F)
 *===========================================================================*/

/* Boot signature bytes (0x09-0x0C) - used in startup_0016 */
idata uint8_t I_BOOT_SIG_0 _at_ 0x09;      /* Boot signature byte 0 */
idata uint8_t I_BOOT_SIG_1 _at_ 0x0A;      /* Boot signature byte 1 */
idata uint8_t I_BOOT_SIG_2 _at_ 0x0B;      /* Boot signature byte 2 */
idata uint8_t I_BOOT_SIG_3 _at_ 0x0C;      /* Boot signature byte 3 */

/* State machine variable (0x6A-0x6E) */
idata uint8_t I_STATE_6A _at_ 0x6A;        /* State machine variable */
idata uint8_t I_TRANSFER_6B _at_ 0x6B;     /* Transfer pending byte 0 */
idata uint8_t I_TRANSFER_6C _at_ 0x6C;     /* Transfer pending byte 1 */
idata uint8_t I_TRANSFER_6D _at_ 0x6D;     /* Transfer pending byte 2 */
idata uint8_t I_TRANSFER_6E _at_ 0x6E;     /* Transfer pending byte 3 */

/*===========================================================================
 * XDATA Variables - Use _at_ for proper MOVX access via DPTR
 *===========================================================================*/

/* System Work Area - XDATA at 0x0001 */
xdata uint8_t G_IO_CMD_TYPE _at_ 0x0001;   /* I/O command type / boot state */

/* Transfer State - XDATA at 0x0AF3 */
xdata uint8_t G_XFER_STATE_0AF3 _at_ 0x0AF3;  /* Transfer state / boot mode */
