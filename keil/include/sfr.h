/*
 * ASM2464PD Firmware - 8051 Special Function Registers (Keil C51 Version)
 *
 * Standard 8051 SFR definitions plus ASM2464PD-specific registers
 */

#ifndef __SFR_H__
#define __SFR_H__

#include "types.h"

/*===========================================================================
 * Standard 8051 SFRs
 *===========================================================================*/

/* Port registers */
sfr P0   = 0x80;    /* Port 0 */
sfr SP   = 0x81;    /* Stack Pointer */
sfr DPL  = 0x82;    /* Data Pointer Low */
sfr DPH  = 0x83;    /* Data Pointer High */
sfr PCON = 0x87;    /* Power Control */
sfr TCON = 0x88;    /* Timer Control */
sfr TMOD = 0x89;    /* Timer Mode */
sfr TL0  = 0x8A;    /* Timer 0 Low */
sfr TL1  = 0x8B;    /* Timer 1 Low */
sfr TH0  = 0x8C;    /* Timer 0 High */
sfr TH1  = 0x8D;    /* Timer 1 High */
sfr P1   = 0x90;    /* Port 1 */
sfr SCON = 0x98;    /* Serial Control */
sfr SBUF = 0x99;    /* Serial Buffer */
sfr P2   = 0xA0;    /* Port 2 */
sfr IE   = 0xA8;    /* Interrupt Enable */
sfr P3   = 0xB0;    /* Port 3 */
sfr IP   = 0xB8;    /* Interrupt Priority */
sfr PSW  = 0xD0;    /* Program Status Word */
sfr ACC  = 0xE0;    /* Accumulator */
sfr B    = 0xF0;    /* B Register */

/*===========================================================================
 * PSW Bits
 *===========================================================================*/
sbit P_   = PSW^0;   /* Parity flag */
sbit F1   = PSW^1;   /* User flag 1 */
sbit OV   = PSW^2;   /* Overflow flag */
sbit RS0  = PSW^3;   /* Register bank select bit 0 */
sbit RS1  = PSW^4;   /* Register bank select bit 1 */
sbit F0   = PSW^5;   /* User flag 0 */
sbit AC   = PSW^6;   /* Auxiliary carry */
sbit CY   = PSW^7;   /* Carry flag */

/*===========================================================================
 * IE Bits (Interrupt Enable)
 *===========================================================================*/
sbit EX0  = IE^0;   /* External interrupt 0 enable */
sbit ET0  = IE^1;   /* Timer 0 interrupt enable */
sbit EX1  = IE^2;   /* External interrupt 1 enable */
sbit ET1  = IE^3;   /* Timer 1 interrupt enable */
sbit ES   = IE^4;   /* Serial interrupt enable */
sbit EA   = IE^7;   /* Global interrupt enable */

/*===========================================================================
 * TCON Bits
 *===========================================================================*/
sbit IT0  = TCON^0; /* Interrupt 0 type */
sbit IE0  = TCON^1; /* External interrupt 0 flag */
sbit IT1  = TCON^2; /* Interrupt 1 type */
sbit IE1  = TCON^3; /* External interrupt 1 flag */
sbit TR0  = TCON^4; /* Timer 0 run */
sbit TF0  = TCON^5; /* Timer 0 overflow flag */
sbit TR1  = TCON^6; /* Timer 1 run */
sbit TF1  = TCON^7; /* Timer 1 overflow flag */

/*===========================================================================
 * ASM2464PD Extended SFRs
 *===========================================================================*/

/*
 * DPX - Data Pointer Extended / Code Bank Select Register
 *
 * Memory Map:
 *   0x0000-0x7FFF: Always visible (32KB shared)
 *   0x8000-0xFFFF with DPX=0: Bank 0 upper (file offset 0x08000-0x0FFFF)
 *   0x8000-0xFFFF with DPX=1: Bank 1 upper (file offset 0x10000-0x17F0C)
 */
sfr DPX = 0x96;     /* Data pointer extended / Code bank select */

/*===========================================================================
 * Interrupt Vector Numbers
 *===========================================================================*/
#define INT_EXT0            0   /* External Interrupt 0 */
#define INT_TIMER0          1   /* Timer 0 Overflow */
#define INT_EXT1            2   /* External Interrupt 1 */
#define INT_TIMER1          3   /* Timer 1 Overflow */
#define INT_SERIAL          4   /* Serial Port */

/* Extended interrupts (ASM2464PD specific) */
#define INT_VEC_USB         5   /* USB interrupt vector */
#define INT_VEC_NVME        6   /* NVMe interrupt vector */
#define INT_VEC_DMA         7   /* DMA interrupt vector */

/*===========================================================================
 * Helper Macros
 *===========================================================================*/

/* Enable/disable all interrupts */
#define ENABLE_INTERRUPTS()     (EA = 1)
#define DISABLE_INTERRUPTS()    (EA = 0)

/* Set register bank (0-3) */
#define SET_REGBANK(n)          (PSW = (PSW & 0xE7) | ((n) << 3))

#endif /* __SFR_H__ */
