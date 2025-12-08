/*
 * ASM2464PD Firmware - Main Entry Point
 *
 * This is the main entry point for the ASM2464PD USB4/Thunderbolt NVMe controller.
 * The firmware is designed for the 8051-compatible CPU core running at ~114MHz.
 *
 * Each function corresponds to a function in the original firmware with its
 * address range documented in the comment header.
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"
#include "globals.h"

/*===========================================================================
 * IDATA Work Variable Definitions
 * These are the actual storage for the extern declarations in globals.h
 *===========================================================================*/
__idata __at(0x0D) uint8_t I_QUEUE_IDX;
__idata __at(0x12) uint8_t I_WORK_12;
__idata __at(0x16) uint8_t I_CORE_STATE_L;
__idata __at(0x17) uint8_t I_CORE_STATE_H;
__idata __at(0x18) uint8_t I_WORK_18;
__idata __at(0x19) uint8_t I_WORK_19;
__idata __at(0x21) uint8_t I_LOG_INDEX;
__idata __at(0x23) uint8_t I_WORK_23;
__idata __at(0x38) uint8_t I_WORK_38;
__idata __at(0x39) uint8_t I_WORK_39;
__idata __at(0x3A) uint8_t I_WORK_3A;
__idata __at(0x3B) uint8_t I_WORK_3B;
__idata __at(0x3C) uint8_t I_WORK_3C;
__idata __at(0x3D) uint8_t I_WORK_3D;
__idata __at(0x3E) uint8_t I_WORK_3E;
__idata __at(0x40) uint8_t I_WORK_40;
__idata __at(0x41) uint8_t I_WORK_41;
__idata __at(0x43) uint8_t I_WORK_43;
__idata __at(0x47) uint8_t I_WORK_47;
__idata __at(0x51) uint8_t I_WORK_51;
__idata __at(0x52) uint8_t I_WORK_52;
__idata __at(0x53) uint8_t I_WORK_53;
__idata __at(0x55) uint8_t I_WORK_55;
__idata __at(0x65) uint8_t I_WORK_65;
__idata __at(0x6A) uint8_t I_STATE_6A;
__idata __at(0x6B) uint8_t I_TRANSFER_6B;
__idata __at(0x6C) uint8_t I_TRANSFER_6C;
__idata __at(0x6D) uint8_t I_TRANSFER_6D;
__idata __at(0x6E) uint8_t I_TRANSFER_6E;
__idata __at(0x6F) uint8_t I_BUF_FLOW_CTRL;
__idata __at(0x70) uint8_t I_BUF_THRESH_LO;
__idata __at(0x71) uint8_t I_BUF_THRESH_HI;
__idata __at(0x72) uint8_t I_BUF_CTRL_GLOBAL;

/*===========================================================================
 * Forward declarations
 *===========================================================================*/

/* Main loop */
void main_loop(void);

/* Initialization */
void process_init_table(void);

/* Dispatch/utility functions */
extern void jump_bank_0(uint16_t reg_addr);    /* app/dispatch.c - 0x0300-0x0310 */
extern void jump_bank_1(uint16_t reg_addr);    /* app/dispatch.c - 0x0311-0x0321 */
void reg_set_bit_0(uint16_t reg_addr);
void reg_set_bit_0_cpu_exec(void);

/* Main loop handler stubs - some moved to driver files */
extern void timer_link_status_handler(void);   /* drivers/timer.c - 0x04d0 -> 0xCE79 */
extern void phy_config_link_params(void);      /* drivers/phy.c */
void reserved_stub_handler(void);              /* 0x04b2 -> 0xE971 - Reserved/unused */
void main_polling_handler(void);               /* 0x4fb6 - Core polling and dispatch */
void usb_power_init(void);                     /* 0x0327 -> 0xB1CB - USB/power init */
extern void event_state_handler(void);         /* app/state_helpers.c - 0x0494 -> Bank1:0xE56F */
extern void error_state_config(void);          /* app/state_helpers.c - 0x0606 -> Bank1:0xB230 */
extern void phy_register_config(void);         /* drivers/phy.c - 0x0589 -> 0xD894 */
extern void flash_command_handler(void);       /* drivers/flash.c - 0x0525 -> 0xBAA0 */
extern void system_init_from_flash(void);      /* drivers/flash.c - Bank 1: 0x8d77 */
extern void usb_buffer_dispatch(void);         /* drivers/usb.c - 0x039a -> 0xD810 */
extern void system_interrupt_handler(void);    /* drivers/timer.c - 0x0520 -> 0xB4BA */
extern void pcie_nvme_event_handler(void);     /* drivers/pcie.c - 0x052f -> 0xAF5E */
extern void pcie_error_dispatch(void);         /* drivers/pcie.c - 0x0570 -> Bank1:0xE911 */
extern void pcie_event_bit5_handler(void);     /* drivers/pcie.c - 0x061a -> Bank1:0xA066 */
extern void pcie_timer_bit4_handler(void);     /* drivers/pcie.c - 0x0593 -> 0xC105 */
extern void system_timer_handler(void);        /* drivers/timer.c - 0x0642 -> 0xEF4E */

/* External functions */
extern void uart_init(void);
extern void usb_ep_dispatch_loop(void);

/*===========================================================================
 * Initialization Data Table Processor
 *===========================================================================*/

/*
 * write_xdata_reg - Write value to XDATA register
 * Address: 0x0be6 (helper function)
 *
 * Writes the value in A to the XDATA address specified by R3:R2 (high:low).
 * Uses R1 as loop counter for sequential writes.
 *
 * Original disassembly:
 *   0be6: push 0x82        ; push DPL
 *   0be8: push 0x83        ; push DPH
 *   0bea: mov dph, r3
 *   0bec: mov dpl, r2
 *   0bee: movx @dptr, a    ; write to XDATA
 *   0bef: pop 0x83
 *   0bf1: pop 0x82
 *   0bf3: ret
 */
static void write_xdata_reg(uint8_t addr_h, uint8_t addr_l, uint8_t value)
{
    uint16_t addr = ((uint16_t)addr_h << 8) | addr_l;
    XDATA8(addr) = value;
}

/*
 * process_init_table - Process initialization data table
 * Address: 0x4352-0x43d1 (128 bytes)
 *
 * Processes a compressed initialization table at code address 0x0648.
 * The table contains register addresses and values to initialize hardware.
 *
 * Table format:
 *   Byte 0: Command byte
 *     - If 0x00: End of table, exit
 *     - Bits 7:6 = Type: 0xE0=write XDATA, 0x40/0x80/0xC0=other operations
 *     - Bits 5:0 = Count or flags
 *
 *   For type 0xE0 (write to XDATA):
 *     Next 3 bytes: addr_high, addr_low, count
 *     Following bytes: values to write sequentially
 *
 *   For other types:
 *     Handle IDATA bit operations
 *
 * Original disassembly:
 *   4352: mov dptr, #0x0648    ; point to init table
 *   4355: clr a
 *   4356: mov r6, #0x01
 *   4358: movc a, @a+dptr      ; read command byte
 *   4359: jz 0x4329            ; if zero, jump to main_loop
 *   435b: inc dptr
 *   435c: mov r7, a            ; save command
 *   435d: anl a, #0x3f         ; get count/flags
 *   ...
 */
void process_init_table(void)
{
    __code uint8_t *table_ptr = (__code uint8_t *)0x0648;
    uint8_t cmd;
    uint8_t count;
    uint8_t addr_h, addr_l;
    uint8_t type;
    uint8_t r6;  /* outer loop counter */

    while (1) {
        r6 = 1;

        /* Read command byte */
        cmd = *table_ptr;

        /* End of table? */
        if (cmd == 0x00) {
            return;
        }

        table_ptr++;

        /* Extract type (bits 7:6) and flags (bits 5:0) */
        type = cmd & 0xE0;
        count = cmd & 0x3F;

        /* Check if bit 5 is set - extended count follows */
        if (cmd & 0x20) {
            count = cmd & 0x1F;  /* Use only bits 4:0 */
            r6 = *table_ptr;
            table_ptr++;
            if (r6 != 0) {
                r6++;  /* Increment if non-zero */
            }
        }

        /* Process based on type */
        if (type == 0xE0) {
            /* Type 0xE0: Write values to sequential XDATA addresses */
            /* Read address high and low */
            addr_h = *table_ptr++;
            addr_l = *table_ptr++;
            count = *table_ptr++;  /* Count of bytes to write */

            /* Write loop */
            do {
                do {
                    uint8_t value = *table_ptr++;
                    write_xdata_reg(addr_h, addr_l, value);

                    /* Increment address */
                    addr_l++;
                    if (addr_l == 0) {
                        addr_h++;
                    }

                    count--;
                } while (count != 0);

                r6--;
            } while (r6 != 0);
        } else if (type == 0x00) {
            /* Type 0x00: Bit operations on IDATA */
            /* Read address from table */
            uint8_t idata_addr = *table_ptr++;
            uint8_t mask_index = (cmd & 0x07) + 0x0C;  /* Calculate mask table offset */

            /* Read mask from a lookup table embedded in code at 0x433e */
            /* Simplified: just skip this complex bit manipulation for now */
            /* The original uses: movc a, @a+pc at address 0x433d */

            /* Original: reads idata[addr], applies mask, writes back */
            /* This involves either ORing or ANDing based on carry flag */
            count--;
            while (count != 0) {
                table_ptr++;
                count--;
            }
        } else {
            /* Other types (0x40, 0x80, 0xC0) */
            /* Read address */
            addr_h = *table_ptr++;
            addr_l = *table_ptr++;

            /* For 0x40/0x80: direct register operations */
            /* Skip the data bytes */
            while (count != 0) {
                table_ptr++;
                count--;
            }
        }
    }
}

/*===========================================================================
 * Main Entry Point
 *===========================================================================*/

/*
 * Main entry point
 * Address: 0x431a-0x43d2 (184 bytes)
 *
 * Called from reset vector at address 0x0000
 *
 * The firmware entry performs:
 * 1. Clear all internal RAM (256 bytes)
 * 2. Initialize stack pointer to 0x72
 * 3. Call cmd_dispatch (0x0300 via 0x030a)
 * 4. Process initialization data table at 0x0648
 * 5. Enter main processing loop at 0x2f80
 *
 * Original disassembly:
 *   431a: mov r0, #0xff
 *   431c: clr a
 *   431d: mov @r0, a
 *   431e: djnz r0, 0x431d
 *   4320: mov SP, #0x72
 *   4323: lcall 0x030a
 *   4326: ljmp 0x4352   ; continue initialization
 */
void main(void)
{
    __asm
        ; Clear all internal RAM (0x00-0xFF)
        mov     r0, #0xFF
        clr     a
    _clear_ram:
        mov     @r0, a
        djnz    r0, _clear_ram

        ; Initialize stack pointer (leaves room for 256-0x72 = 142 bytes of stack)
        mov     SP, #0x72
    __endasm;

    /* Call initialization dispatcher at 0x030a */
    /* This sets up DPX register and dispatches based on parameter */
    DPX = 0x00;

    /* Process initialization data table at 0x0648 */
    process_init_table();

    /* Basic system initialization */
    G_SYSTEM_CTRL = 0x33;

    /* Initialize USB endpoint configuration */
    G_EP_CONFIG_BASE = 0x20;
    G_EP_CONFIG_ARRAY = 0x04;
    G_EP_CONFIG_05A8 = 0x02;
    G_EP_CONFIG_05F8 = 0x04;

    /* Initialize system flags */
    G_SYS_FLAGS_07EC = 0x01;
    G_SYS_FLAGS_07ED = 0x00;
    G_SYS_FLAGS_07EE = 0x00;
    G_SYS_FLAGS_07EF = 0x00;

    /* Initialize NVMe */
    REG_NVME_LBA_LOW = 0x02;

    /* Enter main processing loop (never returns) */
    main_loop();
}

/*===========================================================================
 * Main Processing Loop
 *===========================================================================*/

/*
 * Main processing loop
 * Address: 0x2f80-0x3129 (937 bytes)
 *
 * This is the main polling loop that handles:
 * - Timer/system events
 * - USB events
 * - NVMe events
 * - Power management
 *
 * Original start:
 *   2f80: clr a
 *   2f81: mov dptr, #0x0a59
 *   2f84: movx @dptr, a
 *   2f85: mov dptr, #0xcc32
 *   2f88: lcall 0x5418
 *   2f8b: lcall 0x04d0
 *   ...
 */
void main_loop(void)
{
    uint8_t events;
    uint8_t state;

    /* Clear loop state flag */
    G_LOOP_STATE = 0x00;

    while (1) {
        /* Set bit 0 of REG_CPU_EXEC_STATUS - timer/system handler */
        reg_set_bit_0_cpu_exec();

        /* Call dispatch stubs and handlers */
        timer_link_status_handler();
        phy_config_link_params();
        reserved_stub_handler();
        main_polling_handler();
        usb_power_init();

        /* Check event flags */
        events = G_EVENT_FLAGS;
        if (events & EVENT_FLAGS_ANY) {
            if (events & (EVENT_FLAG_ACTIVE | EVENT_FLAG_PENDING)) {
                event_state_handler();
            }
            error_state_config();
            phy_register_config();
            flash_command_handler();
        }

        /* Clear interrupt priority for EXT0 and EXT1 */
        IP &= ~0x05;    /* Clear PX0, PX1 */

        /* Enable external interrupts */
        EX0 = 1;
        EX1 = 1;
        EA = 1;

        /* Temporarily disable interrupts for critical section */
        EA = 0;

        /* Check system state at 0x0AE2 */
        state = G_SYSTEM_STATE_0AE2;
        if (state != 0 && state != 0x10) {
            /* Process based on state - see firmware at 0x2fc5 */
            if (G_LOOP_STATE == 0) {
                /* Additional state machine processing */
            }
        }

        /* Re-enable interrupts */
        EA = 1;
    }
}

/*===========================================================================
 * Code Banking and Dispatch System
 *===========================================================================*/

/*
 * ASM2464PD CODE BANKING MECHANISM
 * =================================
 *
 * The ASM2464PD has ~98KB of firmware but the 8051 can only address 64KB.
 * A code banking scheme using the DPX register (0x96) provides access to
 * all code.
 *
 * MEMORY MAP:
 *   CPU Address   | DPX=0 (Bank 0)      | DPX=1 (Bank 1)
 *   --------------|---------------------|---------------------
 *   0x0000-0x7FFF | File 0x0000-0x7FFF  | File 0x0000-0x7FFF (shared)
 *   0x8000-0xFFFF | File 0x8000-0xFFFF  | File 0x10000-0x17F0C
 *
 * The lower 32KB (0x0000-0x7FFF) is always visible regardless of DPX.
 * This contains interrupt vectors, dispatch routines, and common code.
 *
 * The upper 32KB (0x8000-0xFFFF) is bank-switched:
 *   - DPX=0: Maps to file offset 0x08000-0x0FFFF (bank 0)
 *   - DPX=1: Maps to file offset 0x10000-0x17F0C (bank 1)
 *
 * DISPATCH MECHANISM:
 *   The handlers use a clever trampoline system:
 *   1. Caller loads DPTR with target function address (e.g., 0xE911)
 *   2. Caller jumps to dispatch function (0x0300 or 0x0311)
 *   3. Dispatch saves context, sets DPX, then RET pops the DPTR
 *   4. Execution continues at the target address in the selected bank
 *
 * FILE OFFSET CALCULATION:
 *   For bank 0 (DPX=0): file_offset = addr
 *   For bank 1 (DPX=1): file_offset = addr + 0x8000
 *
 * EXAMPLE:
 *   pcie_error_dispatch calls jump_bank_1(0xE911)
 *   -> DPX=1, execution jumps to 0xE911 in bank 1
 *   -> File offset = 0xE911 + 0x8000 = 0x16911
 */

/* jump_bank_0() and jump_bank_1() moved to app/dispatch.c */

/*
 * reg_set_bit_0 - Set bit 0 of a register
 * Address: 0x5418-0x541e (7 bytes)
 *
 * Reads the byte at the given XDATA address, clears bit 0,
 * sets bit 0, and writes back. Essentially: reg |= 0x01
 *
 * From ghidra.c: *param_1 = *param_1 & 0xfe | 1;
 *
 * Original disassembly:
 *   5418: movx a, @dptr    ; read from XDATA[DPTR]
 *   5419: anl a, #0xfe     ; clear bit 0
 *   541b: orl a, #0x01     ; set bit 0
 *   541d: movx @dptr, a    ; write back
 *   541e: ret
 */
void reg_set_bit_0(uint16_t reg_addr)
{
    uint8_t val = XDATA8(reg_addr);
    val = (val & 0xFE) | 0x01;
    XDATA8(reg_addr) = val;
}

/*
 * reg_set_bit_0_cpu_exec - Set bit 0 of REG_CPU_EXEC_STATUS
 * Address: Inline of 0x5418 call pattern
 *
 * Called from main_loop at 0x2f85-0x2f88:
 *   2f85: mov dptr, #0xcc32
 *   2f88: lcall 0x5418
 */
void reg_set_bit_0_cpu_exec(void)
{
    REG_CPU_EXEC_STATUS = (REG_CPU_EXEC_STATUS & ~CPU_EXEC_STATUS_ACTIVE) | CPU_EXEC_STATUS_ACTIVE;
}

/*===========================================================================
 * Main Loop Handler Stubs
 * These are dispatch stubs that set DPTR and call jump_bank_0
 * or jump_bank_1
 *===========================================================================*/

/* timer_link_status_handler() moved to drivers/timer.c */

/* phy_config_link_params() moved to drivers/phy.c */

/*
 * reserved_stub_handler - Placeholder/Reserved handler
 * Address: 0x04b2-0x04b6 (5 bytes) -> dispatches to 0xE971
 *
 * Function at 0xE971 is a stub that just returns immediately (ret).
 * The area 0xE971-0xE9A2 contains RET instructions followed by NOPs,
 * indicating this is reserved space for future functionality.
 *
 * Original disassembly:
 *   e971: ret
 *   e972: ret
 *   e973: ret
 *   ... (NOPs follow)
 */
void reserved_stub_handler(void)
{
    /* Stub function - reserved for future functionality */
    /* Original firmware at 0xE971 just returns immediately */
}

/*
 * main_polling_handler - Core polling and dispatch handler
 * Address: 0x4fb6-0x50da (292 bytes)
 *
 * This is the main polling handler called from the main loop.
 * It dispatches to multiple sub-handlers and polls for PHY status.
 *
 * Original disassembly:
 *   4fb6: lcall 0x5305        ; dispatch stub
 *   4fb9: lcall 0x04b7        ; dispatch stub
 *   4fbc: lcall 0x04bc        ; dispatch stub
 *   4fbf: lcall 0x4be6        ; dispatch stub
 *   4fc2: lcall 0x032c        ; dispatch stub
 *   4fc5: lcall 0x0539        ; dispatch stub
 *   4fc8: lcall 0x04f8        ; dispatch stub
 *   4fcb: lcall 0x063d        ; dispatch stub
 *   4fce: mov dptr, #0x0ae3   ; G_STATE_FLAG_0AE3
 *   4fd1: movx a, @dptr
 *   4fd2: jz 0x4fdb           ; if zero, skip
 *   4fd4: mov dptr, #0xcc32   ; REG_CPU_EXEC_STATUS
 *   4fd7: movx a, @dptr
 *   4fd8: anl a, #0xfe        ; clear bit 0
 *   4fda: movx @dptr, a
 *   4fdb: mov dptr, #0xc6b3   ; REG_PHY_EXT_B3
 *   4fde: movx a, @dptr
 *   4fdf: anl a, #0x30        ; check bits 4,5
 *   4fe1: jz 0x4fdb           ; loop until set
 *   4fe3: lcall 0x0462        ; dispatch stub
 *   4fe6: mov dptr, #0x06e6   ; G_STATE_FLAG_06E6
 *   4fe9: mov a, #0x01
 *   4feb: movx @dptr, a       ; set to 1
 *   4fec: lcall 0x0435        ; dispatch stub
 *   4fef: ljmp 0x0340         ; final dispatch (tail call)
 */
void main_polling_handler(void)
{
    /* Call dispatch stubs - these dispatch to various bank 0/1 handlers */
    /* 0x5305 -> dispatches to some handler */
    /* 0x04b7 -> dispatches to 0xE597 (bank 0) */
    /* 0x04bc -> dispatches to 0xE14B (bank 0) */
    /* 0x4be6 -> inline handler */
    /* 0x032c -> dispatches to 0x92C5 (bank 0) */
    /* 0x0539 -> dispatches to some handler */
    /* 0x04f8 -> dispatches to some handler */
    /* 0x063d -> dispatches to 0xEEF9 (bank 1) */

    /* Check state flag and conditionally clear bit 0 of CPU exec status */
    if (G_STATE_FLAG_0AE3 != 0) {
        REG_CPU_EXEC_STATUS = REG_CPU_EXEC_STATUS & 0xFE;
    }

    /* Poll PHY status register until bits 4 or 5 are set */
    /* This waits for PHY link training to complete */
    while ((REG_PHY_EXT_B3 & PHY_EXT_LINK_READY) == 0);

    /* 0x0462 -> dispatches to some handler */

    /* Set flag indicating processing complete */
    G_STATE_FLAG_06E6 = 1;

    /* 0x0435 -> dispatches to some handler */
    /* 0x0340 -> dispatches to 0xBF8E (bank 0) - final tail call */
}


/* event_state_handler() moved to app/state_helpers.c */
/* error_state_config() moved to app/state_helpers.c */

/* phy_register_config() moved to drivers/phy.c */

/* flash_command_handler() moved to drivers/flash.c */

/* usb_buffer_dispatch() moved to drivers/usb.c */

/* system_interrupt_handler() moved to drivers/timer.c */

/* pcie_nvme_event_handler() moved to drivers/pcie.c */
/* pcie_error_dispatch() moved to drivers/pcie.c */
/* pcie_event_bit5_handler() moved to drivers/pcie.c */
/* pcie_timer_bit4_handler() moved to drivers/pcie.c */
/* system_timer_handler() moved to drivers/timer.c */

/* All ISRs (ext0_isr, ext1_isr, timer1_isr, serial_isr) moved to src/interrupt.c */

/*===========================================================================
 * BANK 1 SYSTEM INITIALIZATION
 *
 * This function initializes system configuration from flash storage.
 * It resides in Bank 1 (code offset 0x10000+) and is called during boot.
 *===========================================================================*/

/* External helpers for UART/debug output */
extern uint8_t uart_read_byte_dace(uint8_t offset);  /* 0xdace - Read from UART buffer */
extern void uart_write_byte_daeb(void);              /* 0xdaeb - Write to UART buffer */
extern uint8_t uart_check_status_daf5(void);         /* 0xdaf5 - Check UART status */
extern uint8_t uart_read_status_dae2(void);          /* 0xdae2 - Read UART status */
extern void uart_write_daff(void);                   /* 0xdaff - UART write */
extern uint8_t uart_read_dacc(void);                 /* 0xdacc - UART read */

/* External helpers for system setup */
extern void sys_event_dispatch_05e8(void);           /* 0x05e8 - Event dispatcher */
extern void sys_init_helper_bbc7(void);              /* 0xbbc7 - System init helper */
extern void sys_timer_handler_e957(void);            /* 0xe957 - Timer/watchdog handler */

/* system_init_from_flash() moved to drivers/flash.c */
