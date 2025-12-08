/*
 * ASM2464PD Firmware - Interrupt Service Routines and Controller
 *
 * This file contains all interrupt service routines (ISRs) and interrupt
 * controller helper functions for the ASM2464PD USB4/Thunderbolt NVMe bridge.
 *
 *===========================================================================
 * INTERRUPT CONTROLLER ARCHITECTURE
 *===========================================================================
 *
 * Hardware Configuration:
 * - Custom interrupt controller (not standard 8051 interrupts)
 * - Multiple interrupt status registers for different domains
 * - Level-triggered interrupts with status polling
 *
 * Register Map (0xC800-0xC80F):
 * +-----------+----------------------------------------------------------+
 * | Address   | Description                                              |
 * +-----------+----------------------------------------------------------+
 * | 0xC801    | Interrupt control register                               |
 * | 0xC802    | USB master interrupt status                              |
 * |           |   bit 0: USB interrupt pending                           |
 * | 0xC805    | Auxiliary interrupt status                               |
 * | 0xC806    | System interrupt status                                  |
 * |           |   bit 0: System event interrupt                          |
 * |           |   bit 4: Timer/timeout interrupt                         |
 * |           |   bit 5: Link state change interrupt                     |
 * | 0xC809    | Interrupt control 2                                      |
 * | 0xC80A    | PCIe/NVMe interrupt status                               |
 * |           |   bit 4: NVMe command completion                         |
 * |           |   bit 5: PCIe link event                                 |
 * |           |   bit 6: NVMe queue interrupt                            |
 * +-----------+----------------------------------------------------------+
 *
 * Interrupt Dispatch Flow (from 0x44a3):
 * +----------------------------------------------------------------------+
 * |                    INTERRUPT DISPATCH                                |
 * +----------------------------------------------------------------------+
 * |  1. Check 0xC806 bit 0 -> call system event handler (0x0520)        |
 * |  2. Check 0xCC33 bit 2 -> call state handler (0x0390)               |
 * |  3. Check 0xC80A bit 6 -> call NVMe queue handler (0x052f)          |
 * |  4. Check event flags in 0x09F9                                     |
 * |  5. Check 0xC80A bit 5 -> call PCIe handler (0x061a)                |
 * |  6. Check 0xC80A bit 4 -> call NVMe handler (0x0593)                |
 * |  7. Check 0xC806 bit 4 -> call timer handler (0x0642)               |
 * +----------------------------------------------------------------------+
 *
 *===========================================================================
 * IMPLEMENTATION STATUS
 *===========================================================================
 * ISRs:
 *   ext0_isr            [DONE] External interrupt 0 - USB/peripheral
 *   ext1_isr            [DONE] External interrupt 1 - NVMe/PCIe/system
 *   timer1_isr          [STUB] Timer 1 interrupt
 *   serial_isr          [STUB] Serial interrupt (likely unused)
 *
 * Helper functions:
 *   int_get_system_status       [DONE] Read system interrupt status
 *   int_get_pcie_nvme_status    [DONE] Read PCIe/NVMe interrupt status
 *   int_get_usb_status          [DONE] Read USB interrupt status
 *   int_check_system_event      [DONE] Check system event bit
 *   int_check_nvme_queue        [DONE] Check NVMe queue interrupt
 *   int_check_pcie_event        [DONE] Check PCIe link event
 *   int_check_nvme_complete     [DONE] Check NVMe command completion
 *   int_check_timer             [DONE] Check timer interrupt
 *===========================================================================
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"
#include "globals.h"

/*===========================================================================
 * External handler function declarations
 *===========================================================================*/

/* USB handlers */
extern void usb_ep_dispatch_loop(void);              /* drivers/usb.c */
extern void usb_buffer_dispatch(void);               /* drivers/usb.c - 0x039a -> 0xD810 */

/* Timer handlers */
extern void system_interrupt_handler(void);          /* drivers/timer.c - 0x0520 -> 0xB4BA */
extern void system_timer_handler(void);              /* drivers/timer.c - 0x0642 -> 0xEF4E */

/* PCIe handlers */
extern void pcie_nvme_event_handler(void);           /* drivers/pcie.c - 0x052f -> 0xAF5E */
extern void pcie_error_dispatch(void);               /* drivers/pcie.c - 0x0570 -> Bank1:0xE911 */
extern void pcie_event_bit5_handler(void);           /* drivers/pcie.c - 0x061a -> Bank1:0xA066 */
extern void pcie_timer_bit4_handler(void);           /* drivers/pcie.c - 0x0593 -> 0xC105 */

/*===========================================================================
 * Interrupt Status Helper Functions
 *===========================================================================*/

/*
 * int_get_system_status - Read system interrupt status register
 * Address: 0x44a3-0x44a6
 *
 * Reads the system interrupt status register (0xC806).
 *
 * Returns: Current value of system interrupt status
 *
 * Original disassembly:
 *   44a3: mov dptr, #0xc806   ; System interrupt status
 *   44a6: movx a, @dptr       ; Read status
 */
uint8_t int_get_system_status(void)
{
    return REG_INT_SYSTEM;
}

/*
 * int_get_pcie_nvme_status - Read PCIe/NVMe interrupt status register
 * Address: 0x44ba-0x44bd
 *
 * Reads the PCIe/NVMe interrupt status register (0xC80A).
 *
 * Returns: Current value of PCIe/NVMe interrupt status
 *
 * Original disassembly:
 *   44ba: mov dptr, #0xc80a   ; PCIe/NVMe interrupt status
 *   44bd: movx a, @dptr       ; Read status
 */
uint8_t int_get_pcie_nvme_status(void)
{
    return REG_INT_PCIE_NVME;
}

/*
 * int_get_usb_status - Read USB master interrupt status register
 * Address: 0x0e78-0x0e7b
 *
 * Reads the USB master interrupt status register (0xC802).
 *
 * Returns: Current value of USB interrupt status
 *
 * Original disassembly:
 *   0e78: mov dptr, #0xc802   ; USB master interrupt status
 *   0e7b: movx a, @dptr       ; Read status
 */
uint8_t int_get_usb_status(void)
{
    return REG_INT_USB_MASTER;
}

/*
 * int_check_system_event - Check if system event interrupt is pending
 * Address: 0x44a7-0x44aa
 *
 * Checks bit 0 of system interrupt status register.
 * If set, calls the system event handler.
 *
 * Returns: Non-zero if system event interrupt pending
 *
 * Original disassembly:
 *   44a7: jnb 0xe0.0, 0x44ad  ; Check bit 0
 *   44aa: lcall 0x0520        ; Call system event handler
 */
uint8_t int_check_system_event(void)
{
    return (REG_INT_SYSTEM & 0x01);
}

/*
 * int_check_nvme_queue - Check if NVMe queue interrupt is pending
 * Address: 0x44be-0x44c1
 *
 * Checks bit 6 of PCIe/NVMe interrupt status register.
 * This indicates an NVMe queue event.
 *
 * Returns: Non-zero if NVMe queue interrupt pending
 *
 * Original disassembly:
 *   44be: jnb 0xe0.6, 0x44c4  ; Check bit 6
 *   44c1: lcall 0x052f        ; Call NVMe queue handler
 */
uint8_t int_check_nvme_queue(void)
{
    return (REG_INT_PCIE_NVME & INT_PCIE_NVME_STATUS);
}

/*
 * int_check_pcie_event - Check if PCIe link event interrupt is pending
 * Address: 0x44d0-0x44d3
 *
 * Checks bit 5 of PCIe/NVMe interrupt status register.
 * This indicates a PCIe link state change.
 *
 * Returns: Non-zero if PCIe event interrupt pending
 *
 * Original disassembly:
 *   44d0: jnb 0xe0.5, 0x44d6  ; Check bit 5
 *   44d3: lcall 0x061a        ; Call PCIe handler
 */
uint8_t int_check_pcie_event(void)
{
    return (REG_INT_PCIE_NVME & INT_PCIE_NVME_EVENT);
}

/*
 * int_check_nvme_complete - Check if NVMe command completion interrupt
 * Address: 0x44da-0x44dd
 *
 * Checks bit 4 of PCIe/NVMe interrupt status register.
 * This indicates NVMe command completion.
 *
 * Returns: Non-zero if NVMe completion interrupt pending
 *
 * Original disassembly:
 *   44da: jnb 0xe0.4, 0x44e0  ; Check bit 4
 *   44dd: lcall 0x0593        ; Call NVMe handler
 */
uint8_t int_check_nvme_complete(void)
{
    return (REG_INT_PCIE_NVME & INT_PCIE_NVME_TIMER);
}

/*
 * int_check_timer - Check if timer interrupt is pending
 * Address: 0x4511-0x4514
 *
 * Checks bit 4 of system interrupt status register.
 * This indicates a timer event.
 *
 * Returns: Non-zero if timer interrupt pending
 *
 * Original disassembly:
 *   450d: mov dptr, #0xc806   ; System interrupt status
 *   4510: movx a, @dptr       ; Read status
 *   4511: jnb 0xe0.4, 0x4517  ; Check bit 4
 *   4514: lcall 0x0642        ; Call timer handler
 */
uint8_t int_check_timer(void)
{
    return (REG_INT_SYSTEM & 0x10);
}

/*===========================================================================
 * Interrupt Service Routines
 *===========================================================================*/

/*
 * External Interrupt 0 Handler
 * Address: 0x0e5b-0x1195 (826 bytes)
 *
 * This is the main USB/peripheral interrupt handler. It dispatches to various
 * sub-handlers based on interrupt status registers:
 *
 * Entry:
 *   0e5b-0e76: Push ACC, B, DPH, DPL, PSW, R0-R7
 *   0e65: Set PSW=0 (register bank 0)
 *
 * Dispatch checks:
 *   0e78: Read 0xC802, if bit 0 set -> ljmp 0x10e0
 *   0e82: Read 0x9101, if bit 5 set -> ljmp 0x0f2f
 *   0e8c: Read 0x9000, if bit 0 set -> ljmp 0x0f1c
 *   0e96-0efb: USB endpoint processing loop (0x37 < 0x20)
 *              Uses tables at 0x5a6a, 0x5b72
 *              Writes to 0x0a7b, 0x0a7c, 0x0af5
 *              Calls 0x5442
 *
 * Sub-handlers at various addresses (0x0f1c, 0x0f2f, 0x10e0, etc.)
 *
 * Exit:
 *   117b-1193: Pop R7-R0, PSW, DPL, DPH, B, ACC
 *   1195: RETI
 */
void ext0_isr(void) __interrupt(INT_EXT0) __using(1)
{
    uint8_t status;

    /* Check USB master interrupt status - 0xC802 bit 0 */
    status = REG_INT_USB_MASTER;
    if (status & 0x01) {
        /* USB master interrupt - handle at 0x10e0 path */
        goto usb_master_handler;
    }

    /* Check USB peripheral status - 0x9101 bit 5 */
    status = REG_USB_PERIPH_STATUS;
    if (status & 0x20) {
        /* Peripheral interrupt - handle at 0x0f2f path */
        goto peripheral_handler;
    }

    /* Check USB endpoint status - 0x9000 bit 0 */
    status = REG_USB_STATUS;
    if (status & 0x01) {
        /* USB endpoint interrupt - handle at 0x0f1c path */
        goto endpoint_handler;
    }

    /* USB endpoint processing loop (0x0e96-0x0efb) */
    usb_ep_dispatch_loop();
    return;

usb_master_handler:
    /* Handle USB master events (0x10e0 path)
     * Reads 0xC806 bit 5: if set, checks 0xCEF3 bit 3
     * Reads 0xCEF3 bit 3: if set, clears 0x0464, writes 0x08 to 0xCEF3, calls 0x2608
     * Reads 0xCEF2 bit 7: if set, writes 0x80 to 0xCEF2, clears A, calls 0x3ADB
     * Then checks 0xC802 bit 2 for NVMe queue processing loop
     */
    status = REG_INT_SYSTEM;
    if (status & 0x20) {
        /* Check 0xCEF3 bit 3 */
        status = REG_CPU_LINK_CEF3;
        if (status & 0x08) {
            G_SYS_STATUS_PRIMARY = 0x00;
            REG_CPU_LINK_CEF3 = 0x08;
            /* Would call handler at 0x2608 */
        }
    }
    /* Check 0xCEF2 bit 7 */
    status = REG_CPU_LINK_CEF2;
    if (status & 0x80) {
        REG_CPU_LINK_CEF2 = 0x80;
        /* Would call handler at 0x3ADB with R7=0 */
    }

    /* Check 0xC802 bit 2 - NVMe queue processing */
    status = REG_INT_USB_MASTER;
    if (status & 0x04) {
        /* NVMe queue processing loop - iterates 0x20 times (0x1114-0x1138) */
        /* Checks 0xC471, 0x0055, 0xC520 bits */
    }
    return;

peripheral_handler:
    /* Handle peripheral events (0x0f2f path)
     * Checks 0x9101 bit 3: if set, checks 0x9301 bit 6
     * If bit 6 set: calls 0x035E, writes 0x40 to 0x9301, jumps to master handler
     * If bit 7 set: writes 0x80, modifies 0x92E0, calls 0x0363
     * Checks 0x9302 bit 7: if not set, jumps to master handler
     * Checks 0x9101 bit 0: if set, complex state machine for PHY init
     */
    status = REG_USB_PERIPH_STATUS;
    if (status & 0x08) {
        status = REG_BUF_CFG_9301;
        if (status & 0x40) {
            /* Call 0x035E dispatch */
            REG_BUF_CFG_9301 = 0x40;
            goto usb_master_handler;
        }
        if (status & 0x80) {
            REG_BUF_CFG_9301 = 0x80;
            /* Modify 0x92E0: set bit 1 */
            REG_POWER_DOMAIN = (REG_POWER_DOMAIN & ~POWER_DOMAIN_BIT1) | POWER_DOMAIN_BIT1;
            /* Call 0x0363 dispatch */
            goto usb_master_handler;
        }
        /* Check 0x9302 bit 7 */
        status = REG_BUF_CFG_9302;
        if ((status & 0x80) == 0) {
            goto usb_master_handler;
        }
        REG_BUF_CFG_9302 = 0x80;
        goto usb_master_handler;
    }

    /* Check 0x9101 bit 0 - USB PHY handling */
    status = REG_USB_PERIPH_STATUS;
    if (status & 0x01) {
        /* USB PHY state machine - checks 0x91D1 bits */
        status = REG_USB_PHY_CTRL_91D1;
        if (status & 0x08) {
            REG_USB_PHY_CTRL_91D1 = 0x08;
            /* Call 0x0345 dispatch */
        }
        if (status & 0x01) {
            REG_USB_PHY_CTRL_91D1 = 0x01;
            /* Call 0x034A dispatch */
            goto usb_master_handler;
        }
        if (status & 0x02) {
            REG_USB_PHY_CTRL_91D1 = 0x02;
            /* Call 0x034F dispatch */
            goto usb_master_handler;
        }
        if ((status & 0x04) == 0) {
            goto usb_master_handler;
        }
        /* Call 0x0354 dispatch */
    }
    return;

endpoint_handler:
    /* Handle USB endpoint events (0x0f1c path)
     * Reads 0x9096 bit 0: if not set, jumps to master handler
     * Calls 0x52A7 for endpoint processing
     * Then jumps to 0x1035 for additional processing
     */
    status = REG_USB_EP_READY;
    if ((status & 0x01) == 0) {
        goto usb_master_handler;
    }
    /* Call 0x52A7 for endpoint processing */
    /* Then continue to NVMe queue check at 0x1035 */
    return;
}

/*
 * External Interrupt 1 Handler
 * Address: 0x4486-0x4531 (171 bytes)
 *
 * Handles NVMe, PCIe and system events via various status registers:
 *
 * Entry:
 *   4486-44a1: Push ACC, B, DPH, DPL, PSW, R0-R7
 *   4490: Set PSW=0 (register bank 0)
 *
 * Dispatch checks:
 *   44a3: Read 0xC806, if bit 0 set -> call 0x0520
 *   44ad: Read 0xCC33, if bit 2 set -> write 0x04 to 0xCC33, call 0x0390
 *   44ba: Read 0xC80A, if bit 6 set -> call 0x052f
 *   44c4: Read 0x09F9 & 0x83, if != 0:
 *         - if 0xC80A bit 5 set -> call 0x061a
 *         - if 0xC80A bit 4 set -> call 0x0593
 *         - if 0xEC06 bit 0 set -> handle NVMe/PCIe event
 *   450d: Read 0xC80A & 0x0F, if != 0 -> call 0x0570
 *   4510: Read 0xC806, if bit 4 set -> call 0x0642
 *
 * Exit:
 *   4517-452f: Pop R7-R0, PSW, DPL, DPH, B, ACC
 *   4531: RETI
 */
void ext1_isr(void) __interrupt(INT_EXT1) __using(1)
{
    uint8_t status;
    uint8_t events;

    /* Check system interrupt status bit 0 */
    status = REG_INT_SYSTEM;
    if (status & 0x01) {
        system_interrupt_handler();
    }

    /* Check CPU execution status 2 bit 2 */
    status = REG_CPU_EXEC_STATUS_2;
    if (status & 0x04) {
        REG_CPU_EXEC_STATUS_2 = 0x04;  /* Clear interrupt */
        usb_buffer_dispatch();
    }

    /* Check PCIe/NVMe status bit 6 */
    status = REG_INT_PCIE_NVME;
    if (status & INT_PCIE_NVME_STATUS) {
        pcie_nvme_event_handler();
    }

    /* Check event flags */
    events = G_EVENT_FLAGS & EVENT_FLAGS_ANY;
    if (events != 0) {
        status = REG_INT_PCIE_NVME;

        if (status & INT_PCIE_NVME_EVENT) {
            pcie_event_bit5_handler();
        }

        if (status & INT_PCIE_NVME_TIMER) {
            pcie_timer_bit4_handler();
        }

        /* Check NVMe event status */
        if (REG_NVME_EVENT_STATUS & NVME_EVENT_PENDING) {
            REG_NVME_EVENT_ACK = NVME_EVENT_PENDING;  /* Acknowledge */
            /* Additional NVMe processing */
        }

        /* Check for additional PCIe events (inside event flags block) */
        status = REG_INT_PCIE_NVME & INT_PCIE_NVME_EVENTS;
        if (status != 0) {
            pcie_error_dispatch();
        }
    }

    /* Check system status bit 4 */
    status = REG_INT_SYSTEM;
    if (status & INT_SYSTEM_TIMER) {
        system_timer_handler();
    }
}

/*
 * Timer 1 Interrupt Handler
 * Address: needs identification
 */
void timer1_isr(void) __interrupt(INT_TIMER1) __using(1)
{
    /* Placeholder */
}

/*
 * Serial Interrupt Handler
 * Address: needs identification
 *
 * Note: ASM2464PD uses dedicated UART, this may be unused
 */
void serial_isr(void) __interrupt(INT_SERIAL) __using(1)
{
    /* Placeholder - likely unused */
}
