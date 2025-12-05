/*
 * ASM2464PD Firmware - Timer Driver
 *
 * Timer and periodic interrupt handling for USB4/Thunderbolt to NVMe bridge.
 * The Timer0 ISR is the main periodic interrupt handler that polls various
 * hardware status registers and dispatches to appropriate handlers.
 *
 * Timer0 ISR at 0x4486-0x4531 (172 bytes)
 * Timer0 vector at 0x000B jumps to 0x4486
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"

/* Register addresses used by timer ISR */
#define REG_TIMER_STATUS_C806   XDATA_REG8(0xC806)  /* Timer/interrupt status */
#define REG_TIMER_STATUS_CC33   XDATA_REG8(0xCC33)  /* Additional status */
#define REG_TIMER_STATUS_C80A   XDATA_REG8(0xC80A)  /* Event flags */
#define REG_TIMER_STATUS_09F9   XDATA_REG8(0x09F9)  /* System state flags */
#define REG_NVME_EVENT_EC06     XDATA_REG8(0xEC06)  /* NVMe event status */
#define REG_NVME_EVENT_EC04     XDATA_REG8(0xEC04)  /* NVMe event control */
#define REG_PHY_STATUS_0AF1     XDATA_REG8(0x0AF1)  /* PHY link status */
#define REG_PHY_CTRL_E7E3       XDATA_REG8(0xE7E3)  /* PHY control */

/*
 * timer0_poll_handler_0520 - Dispatch stub for timer handler
 * Address: 0x0520-0x0523 (4 bytes)
 *
 * Sets DPTR to 0xB4BA and jumps to cmd_dispatch at 0x0300.
 * Called when bit 0 of 0xC806 is set.
 *
 * Original disassembly:
 *   0520: mov dptr, #0xb4ba
 *   0523: ajmp 0x0300
 */
void timer0_poll_handler_0520(void)
{
    /* Dispatch stub - sets DPTR and jumps to dispatch */
    /* Target function at 0xB4BA handles timer tick */
}

/*
 * timer0_poll_handler_052f - Dispatch stub for timer event
 * Address: 0x052f-0x0532 (4 bytes)
 *
 * Sets DPTR to 0xAF5E and jumps to cmd_dispatch at 0x0300.
 * Called when bit 6 of 0xC80A is set.
 *
 * Original disassembly:
 *   052f: mov dptr, #0xaf5e
 *   0532: ajmp 0x0300
 */
void timer0_poll_handler_052f(void)
{
    /* Dispatch stub - target at 0xAF5E */
}

/*
 * timer0_poll_handler_0593 - Dispatch stub for timer event
 * Address: 0x0593-0x0596 (4 bytes)
 *
 * Sets DPTR to target and jumps to cmd_dispatch.
 * Called when bit 4 of 0xC80A is set (when 0x09F9 & 0x83 != 0).
 *
 * Original disassembly:
 *   0593: mov dptr, #0x????
 *   0596: ajmp 0x0300
 */
void timer0_poll_handler_0593(void)
{
    /* Dispatch stub */
}

/*
 * timer0_poll_handler_061a - Dispatch stub for timer event
 * Address: 0x061a-0x061d (4 bytes)
 *
 * Called when bit 5 of 0xC80A is set (when 0x09F9 & 0x83 != 0).
 *
 * Original disassembly:
 *   061a: mov dptr, #0x????
 *   061d: ajmp 0x0300
 */
void timer0_poll_handler_061a(void)
{
    /* Dispatch stub */
}

/*
 * timer0_poll_handler_0642 - Dispatch stub for timer event
 * Address: 0x0642-0x0645 (4 bytes)
 *
 * Called when bit 4 of 0xC806 is set.
 *
 * Original disassembly:
 *   0642: mov dptr, #0x????
 *   0645: ajmp 0x0300
 */
void timer0_poll_handler_0642(void)
{
    /* Dispatch stub */
}

/*
 * timer0_poll_handler_0570 - Dispatch stub for timer event
 * Address: 0x0570-0x0573 (4 bytes)
 *
 * Sets DPTR to 0xE911 and jumps to cmd_dispatch at 0x0311.
 * Called when 0xC80A & 0x0F is non-zero.
 *
 * Original disassembly:
 *   0570: mov dptr, #0xe911
 *   0573: ajmp 0x0311
 */
void timer0_poll_handler_0570(void)
{
    /* Dispatch stub - target at 0xE911 */
}

/*
 * timer0_poll_handler_0499 - Dispatch stub for NVMe event
 * Address: 0x0499-0x049c (4 bytes)
 *
 * Called after clearing PHY bits when NVMe event is detected.
 *
 * Original disassembly:
 *   0499: mov dptr, #0x????
 *   049c: ajmp 0x0300
 */
void timer0_poll_handler_0499(void)
{
    /* Dispatch stub for NVMe event handling */
}

/*
 * timer0_isr - Timer0 Interrupt Service Routine
 * Address: 0x4486-0x4531 (172 bytes)
 *
 * Main periodic interrupt handler. Polls multiple hardware status registers
 * and dispatches to various handlers based on flags:
 *
 * - 0xC806 bit 0: Call 0x0520 (timer tick)
 * - 0xCC33 bit 2: Write 0x04 to 0xCC33, call 0x0390
 * - 0xC80A bit 6: Call 0x052f
 * - When 0x09F9 & 0x83 != 0:
 *   - 0xC80A bit 5: Call 0x061a
 *   - 0xC80A bit 4: Call 0x0593
 *   - 0xEC06 bit 0: Write 0x01 to 0xEC04, check 0x0AF1
 *     - 0x0AF1 bit 5: Clear bits 6,7 of 0xE7E3
 *     - Call 0x0499
 * - 0xC80A & 0x0F != 0: Call 0x0570
 * - 0xC806 bit 4: Call 0x0642
 *
 * Original disassembly:
 *   4486: push 0xe0      ; save ACC
 *   4488: push 0xf0      ; save B
 *   448a: push 0x83      ; save DPH
 *   448c: push 0x82      ; save DPL
 *   448e: push 0xd0      ; save PSW
 *   4490: mov 0xd0, #0x00 ; select register bank 0
 *   4493: push 0x00-0x07 ; save R0-R7
 *   44a3: mov dptr, #0xc806
 *   44a6: movx a, @dptr
 *   44a7: jnb 0xe0.0, 0x44ad  ; check bit 0
 *   44aa: lcall 0x0520
 *   ...
 *   4517-452f: pop R7-R0, PSW, DPL, DPH, B, ACC
 *   4531: reti
 */
void timer0_isr(void) __interrupt(1) __using(0)
{
    uint8_t status;

    /* Check timer status register 0xC806 bit 0 */
    status = REG_TIMER_STATUS_C806;
    if (status & 0x01) {
        timer0_poll_handler_0520();
    }

    /* Check status register 0xCC33 bit 2 */
    status = REG_TIMER_STATUS_CC33;
    if (status & 0x04) {
        REG_TIMER_STATUS_CC33 = 0x04;  /* Clear/acknowledge */
        /* lcall 0x0390 - dispatch stub */
    }

    /* Check status register 0xC80A bit 6 */
    status = REG_TIMER_STATUS_C80A;
    if (status & 0x40) {
        timer0_poll_handler_052f();
    }

    /* Check system state flags at 0x09F9 */
    status = REG_TIMER_STATUS_09F9;
    if (status & 0x83) {
        /* Check 0xC80A bit 5 */
        if (REG_TIMER_STATUS_C80A & 0x20) {
            timer0_poll_handler_061a();
        }

        /* Check 0xC80A bit 4 */
        if (REG_TIMER_STATUS_C80A & 0x10) {
            timer0_poll_handler_0593();
        }

        /* Check NVMe event at 0xEC06 bit 0 */
        if (REG_NVME_EVENT_EC06 & 0x01) {
            /* Acknowledge NVMe event */
            REG_NVME_EVENT_EC04 = 0x01;

            /* Check PHY status at 0x0AF1 bit 5 */
            if (REG_PHY_STATUS_0AF1 & 0x20) {
                /* Clear bits 6 and 7 of PHY control */
                status = REG_PHY_CTRL_E7E3;
                status &= 0xBF;  /* Clear bit 6 */
                REG_PHY_CTRL_E7E3 = status;
                status = REG_PHY_CTRL_E7E3;
                status &= 0x7F;  /* Clear bit 7 */
                REG_PHY_CTRL_E7E3 = status;
            }

            timer0_poll_handler_0499();
        }
    }

    /* Check 0xC80A low nibble for additional events */
    status = REG_TIMER_STATUS_C80A;
    if (status & 0x0F) {
        timer0_poll_handler_0570();
    }

    /* Check 0xC806 bit 4 */
    status = REG_TIMER_STATUS_C806;
    if (status & 0x10) {
        timer0_poll_handler_0642();
    }
}

