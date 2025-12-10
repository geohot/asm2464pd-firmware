/*
 * ASM2464PD Firmware - Global Variables (Keil C51 Version)
 *
 * Global variables in XRAM and IDATA for Keil compiler.
 * Declarations only - definitions are in globals.c
 */

#ifndef __GLOBALS_H__
#define __GLOBALS_H__

#include "types.h"

/*===========================================================================
 * IDATA Work Variables (0x00-0x7F)
 *===========================================================================*/

/* Boot signature bytes (0x09-0x0C) - used in startup_0016 */
extern idata uint8_t I_BOOT_SIG_0;      /* 0x09 - Boot signature byte 0 */
extern idata uint8_t I_BOOT_SIG_1;      /* 0x0A - Boot signature byte 1 */
extern idata uint8_t I_BOOT_SIG_2;      /* 0x0B - Boot signature byte 2 */
extern idata uint8_t I_BOOT_SIG_3;      /* 0x0C - Boot signature byte 3 */

/* State machine variable (0x6A-0x6E) */
extern idata uint8_t I_STATE_6A;        /* 0x6A - State machine variable */
extern idata uint8_t I_TRANSFER_6B;     /* 0x6B - Transfer pending byte 0 */
extern idata uint8_t I_TRANSFER_6C;     /* 0x6C - Transfer pending byte 1 */
extern idata uint8_t I_TRANSFER_6D;     /* 0x6D - Transfer pending byte 2 */
extern idata uint8_t I_TRANSFER_6E;     /* 0x6E - Transfer pending byte 3 */

/*===========================================================================
 * XDATA Variables
 *===========================================================================*/

/* System Work Area - XDATA at 0x0001 */
extern xdata uint8_t G_IO_CMD_TYPE;     /* 0x0001 - I/O command type / boot state */

/* Transfer State - XDATA at 0x0AF3 */
extern xdata uint8_t G_XFER_STATE_0AF3; /* 0x0AF3 - Transfer state / boot mode */

#endif /* __GLOBALS_H__ */
