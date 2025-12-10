/*
 * ASM2464PD Firmware - Type Definitions (Keil C51 Version)
 *
 * 8051 architecture types for Keil C51 compiler
 */

#ifndef __TYPES_H__
#define __TYPES_H__

/* Standard integer types */
typedef unsigned char       uint8_t;
typedef signed char         int8_t;
typedef unsigned short      uint16_t;
typedef signed short        int16_t;
typedef unsigned long       uint32_t;
typedef signed long         int32_t;

/* Boolean type */
typedef uint8_t             bool;
#define true                1
#define false               0

/* NULL definition */
#ifndef NULL
#define NULL                ((void *)0)
#endif

/* Byte access macros */
#define LOBYTE(w)           ((uint8_t)((w) & 0xFF))
#define HIBYTE(w)           ((uint8_t)(((w) >> 8) & 0xFF))
#define MAKEWORD(lo, hi)    ((uint16_t)(((uint16_t)(hi) << 8) | (uint8_t)(lo)))

/* Bit manipulation macros */
#define BIT(n)              (1 << (n))
#define SETBIT(v, n)        ((v) |= BIT(n))
#define CLRBIT(v, n)        ((v) &= ~BIT(n))
#define TSTBIT(v, n)        (((v) & BIT(n)) != 0)

/* Memory access macros (Keil syntax - no underscores) */
#define XDATA8(addr)        (*((xdata uint8_t *)(addr)))
#define XDATA16(addr)       (*((xdata uint16_t *)(addr)))
#define XDATA32(addr)       (*((xdata uint32_t *)(addr)))

#define CODE8(addr)         (*((code uint8_t *)(addr)))
#define CODE16(addr)        (*((code uint16_t *)(addr)))

/* SDCC to Keil compatibility layer */
#define __xdata             xdata
#define __idata             idata
#define __data              data
#define __code              code
#define __pdata             pdata

/* Keil doesn't support __at() the same way - use _at_ */
/* These variables need to be declared differently for Keil */
#define XDATA_VAR8(addr)    (*((xdata uint8_t *)(addr)))

#endif /* __TYPES_H__ */
