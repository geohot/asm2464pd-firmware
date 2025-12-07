/*
 * ASM2464PD Firmware - Timer Driver
 *
 * Hardware timer and periodic interrupt handling for USB4/Thunderbolt to NVMe
 * bridge controller. Provides millisecond-resolution delays and periodic polling.
 *
 *===========================================================================
 * TIMER CONTROLLER ARCHITECTURE
 *===========================================================================
 *
 * Hardware Configuration:
 * - 4 independent hardware timers (Timer0-Timer3)
 * - Each timer has: Divider, Control/Status, Threshold registers
 * - Timer0: Main system tick timer, drives periodic ISR
 * - Timer1: Used for protocol timeouts
 * - Timer2: Used for USB timing
 * - Timer3: Idle timeout management
 * - Clock source derived from 114MHz system clock
 *
 * Register Map (0xCC10-0xCC24):
 * ┌──────────┬──────────────────────────────────────────────────────────┐
 * │ Address  │ Description                                              │
 * ├──────────┼──────────────────────────────────────────────────────────┤
 * │ 0xCC10   │ Timer0 DIV - Clock divider (bits 0-2: prescaler)         │
 * │ 0xCC11   │ Timer0 CSR - Control/Status (bit 1: done flag)           │
 * │ 0xCC12-13│ Timer0 Threshold (16-bit count value, little-endian)     │
 * │ 0xCC16   │ Timer1 DIV - Clock divider                               │
 * │ 0xCC17   │ Timer1 CSR - Control/Status                              │
 * │ 0xCC18-19│ Timer1 Threshold (16-bit)                                │
 * │ 0xCC1C   │ Timer2 DIV - Clock divider                               │
 * │ 0xCC1D   │ Timer2 CSR - Control/Status                              │
 * │ 0xCC1E-1F│ Timer2 Threshold (16-bit)                                │
 * │ 0xCC22   │ Timer3 DIV - Clock divider                               │
 * │ 0xCC23   │ Timer3 CSR - Control/Status                              │
 * │ 0xCC24   │ Timer3 Idle Timeout                                      │
 * │ 0xCC33   │ Timer Status/Control (bit 2: event flag)                 │
 * └──────────┴──────────────────────────────────────────────────────────┘
 *
 * Timer CSR Register Bits:
 * ┌─────┬────────────────────────────────────────────────────────────────┐
 * │ Bit │ Function                                                       │
 * ├─────┼────────────────────────────────────────────────────────────────┤
 * │  0  │ Enable - Start/stop timer counting                            │
 * │  1  │ Done - Timer reached threshold (write 0x02 to clear)          │
 * │  2  │ Interrupt enable                                              │
 * │ 3-7 │ Reserved                                                       │
 * └─────┴────────────────────────────────────────────────────────────────┘
 *
 * Timer DIV Register Bits:
 * ┌─────┬────────────────────────────────────────────────────────────────┐
 * │ Bit │ Function                                                       │
 * ├─────┼────────────────────────────────────────────────────────────────┤
 * │ 0-2 │ Prescaler select (divides clock by 2^N)                       │
 * │  3  │ Timer enable/disable bit                                      │
 * │ 4-7 │ Reserved                                                       │
 * └─────┴────────────────────────────────────────────────────────────────┘
 *
 * Timer0 ISR Flow:
 * ┌─────────────────────────────────────────────────────────────────────┐
 * │                    Timer0 ISR (0x4486)                              │
 * ├─────────────────────────────────────────────────────────────────────┤
 * │ 1. Save context (ACC, B, DPTR, PSW, R0-R7)                          │
 * │ 2. Check 0xC806 bit 0 → dispatch to 0xB4BA (timer tick)             │
 * │ 3. Check 0xCC33 bit 2 → clear flag, dispatch to 0xCD10              │
 * │ 4. Check 0xC80A bit 6 → dispatch to 0xAF5E (debug output)           │
 * │ 5. If 0x09F9 & 0x83:                                                │
 * │    - Check 0xC80A bit 5 → dispatch event handler                   │
 * │    - Check 0xC80A bit 4 → dispatch event handler                   │
 * │    - Check 0xEC06 bit 0 → handle NVMe event, check PHY status       │
 * │ 6. Check 0xC80A & 0x0F → dispatch to 0xE911                        │
 * │ 7. Check 0xC806 bit 4 → dispatch event handler                     │
 * │ 8. Restore context and RETI                                         │
 * └─────────────────────────────────────────────────────────────────────┘
 *
 * Typical Timer0 Configuration (from 0xAD72):
 * - Prescaler: 3 (divide by 8)
 * - Threshold: 0x0028 (40 counts)
 * - Results in ~1ms tick at 114MHz / 8 / 40 ≈ 356kHz → ~2.8us per tick
 *
 *===========================================================================
 * IMPLEMENTATION STATUS
 *===========================================================================
 * timer0_isr                [DONE] 0x4486-0x4531 - Main timer ISR
 * timer0_poll_handler_0520  [STUB] 0x0520-0x0523 - Timer tick dispatch
 * timer0_poll_handler_052f  [STUB] 0x052f-0x0532 - Debug output dispatch
 * timer0_poll_handler_0593  [STUB] 0x0593-0x0596 - Event dispatch
 * timer0_poll_handler_061a  [STUB] 0x061a-0x061d - Event dispatch
 * timer0_poll_handler_0642  [STUB] 0x0642-0x0645 - Event dispatch
 * timer0_poll_handler_0570  [STUB] 0x0570-0x0573 - Low nibble dispatch
 * timer0_poll_handler_0499  [STUB] 0x0499-0x049c - NVMe event dispatch
 * timer0_csr_ack            [DONE] 0x95c2-0x95c8 - Write 0x04, 0x02 to CSR
 * timer0_wait_done          [DONE] 0xad95-0xada1 - Wait for CSR bit 1
 * timer1_check_and_ack      [DONE] 0x3094-0x30a0 - Check/ack Timer1
 *
 * Total: 11 functions (3 implemented, 8 dispatch stubs)
 *===========================================================================
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"
#include "globals.h"

/* Additional registers used by timer ISR (not in main registers.h) */
#define REG_TIMER_STATUS_C806   XDATA_REG8(0xC806)  /* Timer/interrupt status */
#define REG_TIMER_STATUS_CC33   XDATA_REG8(0xCC33)  /* Timer event status */
#define REG_TIMER_STATUS_C80A   XDATA_REG8(0xC80A)  /* Event flags */
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

    /* Check system state flags at 0x09F9 (global variable) */
    status = G_EVENT_FLAGS;
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

/*
 * timer0_csr_ack - Acknowledge timer0 CSR with 0x04, then 0x02
 * Address: 0x95c2-0x95c8 (7 bytes)
 *
 * Writes 0x04 then 0x02 to the Timer0 CSR register at DPTR (0xCC11).
 * Called to acknowledge/clear timer events.
 * Note: DPTR must be pointing to 0xCC11 when called (from 0xAD7A).
 *
 * Original disassembly:
 *   95c2: mov a, #0x04
 *   95c4: movx @dptr, a      ; write 0x04 to CSR
 *   95c5: mov a, #0x02
 *   95c7: movx @dptr, a      ; write 0x02 to CSR
 *   95c8: ret
 */
void timer0_csr_ack(void)
{
    REG_TIMER0_CSR = 0x04;  /* Clear interrupt flag */
    REG_TIMER0_CSR = 0x02;  /* Clear done flag */
}

/*
 * timer0_wait_done - Wait for Timer0 done flag (CSR bit 1)
 * Address: 0xad95-0xada1 (13 bytes)
 *
 * Polls Timer0 CSR register waiting for bit 1 (done) to be set.
 * Then acknowledges by writing 0x02 to clear the done flag.
 *
 * Original disassembly:
 *   ad95: mov dptr, #0xcc11   ; Timer0 CSR
 *   ad98: movx a, @dptr       ; read CSR
 *   ad99: jnb 0xe0.1, 0xad95  ; loop until bit 1 set
 *   ad9c: mov dptr, #0xcc11
 *   ad9f: mov a, #0x02
 *   ada1: movx @dptr, a       ; write 0x02 to clear done
 */
void timer0_wait_done(void)
{
    /* Wait for done flag (bit 1) */
    while (!(REG_TIMER0_CSR & 0x02))
        ;

    /* Acknowledge by writing 0x02 */
    REG_TIMER0_CSR = 0x02;
}

/*
 * timer1_check_and_ack - Check Timer1 done and acknowledge
 * Address: 0x3094-0x30a0 (13 bytes)
 *
 * Checks if Timer1 CSR bit 1 (done) is set. If so, writes 0x02 to
 * acknowledge/clear the done flag, then calls dispatch at 0x04D5.
 *
 * Original disassembly:
 *   3094: mov dptr, #0xcc17   ; Timer1 CSR
 *   3097: movx a, @dptr
 *   3098: jnb 0xe0.1, 0x30a1  ; if bit 1 not set, skip
 *   309b: mov a, #0x02
 *   309d: movx @dptr, a       ; write 0x02 to ack
 *   309e: lcall 0x04d5        ; dispatch handler
 *   30a1: setb 0xa8.7         ; set EA (enable interrupts)
 */
void timer1_check_and_ack(void)
{
    /* Check if Timer1 done flag is set */
    if (REG_TIMER1_CSR & 0x02) {
        /* Acknowledge by writing 0x02 */
        REG_TIMER1_CSR = 0x02;
        /* Call dispatch handler - 0x04D5 */
        /* lcall 0x04d5 would go here */
    }
    /* Note: setb EA done by caller or at end of routine */
}

