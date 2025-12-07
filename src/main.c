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
 * Forward declarations
 *===========================================================================*/

/* Main loop */
void main_loop(void);

/* Dispatch/utility functions */
void jump_bank_0(uint16_t reg_addr);
void jump_bank_1(uint16_t reg_addr);
void reg_set_bit_0(uint16_t reg_addr);
void reg_set_bit_0_cpu_exec(void);

/* Main loop handler stubs */
void handler_04d0(void);
void phy_config_link_params(void);
void handler_04b2(void);
void handler_4fb6(void);
void handler_0327(void);
void handler_0494(void);
void handler_0606(void);
void handler_0589(void);
void handler_0525(void);

/* External functions */
extern void uart_init(void);
extern void usb_ep_dispatch_loop(void);

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

    /* TODO: Process initialization data table at 0x0648 */
    /* The original firmware iterates over a compressed data table
     * that contains register addresses and values to initialize.
     * For now, we do basic initialization directly. */

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
    REG_NVME_LBA_0 = 0x02;

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
        handler_04d0();
        phy_config_link_params();
        handler_04b2();
        handler_4fb6();
        handler_0327();

        /* Check event flags */
        events = G_EVENT_FLAGS;
        if (events & 0x83) {
            if (events & 0x81) {
                handler_0494();
            }
            handler_0606();
            handler_0589();
            handler_0525();
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
 *   handler_0570 calls jump_bank_1(0xE911)
 *   -> DPX=1, execution jumps to 0xE911 in bank 1
 *   -> File offset = 0xE911 + 0x8000 = 0x16911
 */

/*
 * jump_bank_0 - Bank 0 dispatch function
 * Address: 0x0300-0x0310 (17 bytes)
 *
 * Sets DPX=0 (bank 0) and dispatches to target address.
 * R0 is set to 0x0A which may be used by target functions.
 *
 * Original disassembly:
 *   0300: push 0x08      ; push R0
 *   0302: mov a, #0x03
 *   0304: push 0xe0      ; push ACC
 *   0306: push 0x82      ; push DPL
 *   0308: push 0x83      ; push DPH
 *   030a: mov 0x08, #0x0a  ; R0 = 0x0A
 *   030d: mov 0x96, #0x00  ; DPX = 0x00 (bank 0)
 *   0310: ret              ; pops DPH:DPL from stack, jumps there
 */
void jump_bank_0(uint16_t reg_addr)
{
    /* Bank 0 dispatch - target address is in bank 0 (file 0x0000-0xFFFF) */
    (void)reg_addr;
    DPX = 0x00;
}

/*
 * jump_bank_1 - Bank 1 dispatch function
 * Address: 0x0311-0x0321 (17 bytes)
 *
 * Sets DPX=1 (bank 1) and dispatches to target address.
 * R0 is set to 0x1B which may be used by target functions.
 *
 * Bank 1 functions handle error conditions and are at file offset
 * 0x10000-0x17F0C (CPU addresses 0x8000-0xFFFF with DPX=1).
 *
 * Original disassembly:
 *   0311: push 0x08
 *   0313: mov a, #0x03
 *   0315: push 0xe0
 *   0317: push 0x82
 *   0319: push 0x83
 *   031b: mov 0x08, #0x1b  ; R0 = 0x1B
 *   031e: mov 0x96, #0x01  ; DPX = 0x01 (bank 1)
 *   0321: ret
 */
void jump_bank_1(uint16_t reg_addr)
{
    /* Bank 1 dispatch - target address is in bank 1 (file 0x10000+) */
    (void)reg_addr;
    DPX = 0x01;
}

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
    REG_CPU_EXEC_STATUS = (REG_CPU_EXEC_STATUS & 0xFE) | 0x01;
}

/*===========================================================================
 * Main Loop Handler Stubs
 * These are dispatch stubs that set DPTR and call jump_bank_0
 * or jump_bank_1
 *===========================================================================*/

/*
 * Handler at 0x04d0 - Timer/Link status handler
 * Address: 0x04d0-0x04d4 (5 bytes) -> dispatches to 0xCE79
 *
 * Function at 0xCE79 (94 bytes):
 * Handles timer and link status checks:
 * 1. Checks REG_LINK_STATUS_CC3F bits 1,2 and calls helper if set
 * 2. Configures timer/link registers (0xCC30, 0xCC33, 0xCC3B, etc.)
 * 3. Clears bits in PHY_CONFIG (0xC233)
 * 4. Performs timing delays with polling
 * 5. Polls status registers until link ready
 *
 * Original disassembly:
 *   ce79: mov dptr, #0xcc3f
 *   ce7c: movx a, @dptr       ; read REG_LINK_STATUS_CC3F
 *   ce7d: jb 0xe0.1, 0xce84   ; if bit 1 set, call helper
 *   ce80: movx a, @dptr
 *   ce81: jnb 0xe0.2, 0xce87  ; if bit 2 not set, skip helper
 *   ce84: lcall 0xd0d3        ; clear bits in CC3F, set flags
 *   ce87: lcall 0xcf28        ; configure timer regs
 *   ce8a: lcall 0x0610        ; dispatch to bank 1 0xED02
 *   ce8d: mov dptr, #0xc233
 *   ce90: movx a, @dptr
 *   ce91: anl a, #0xfc        ; clear bits 0-1
 *   ce93: movx @dptr, a
 *   ce94: lcall 0xbd5e        ; set bit 2, clear bit 2 of @DPTR
 *   ce97-cea6: timing delay loop
 *   cea7-ceab: more timing delay
 *   ceb0-cec5: poll 0xE712 and 0xCC11 until ready
 *   cec6: lcall 0xe8ef
 *   cecb: lcall 0xdd42
 *   cece: ljmp 0xd996
 */
void handler_04d0(void)
{
    uint8_t status;
    uint8_t val;

    /* Read link status register 0xCC3F */
    status = XDATA8(0xCC3F);

    /* Check if bit 1 or bit 2 is set - if so, call helper to clear flags */
    if ((status & 0x02) || (status & 0x04)) {
        /* Helper at 0xD0D3:
         * - Calls 0xBD2A (set bit 2, clear bit 2)
         * - Delay loop with R4:R5=0x0009
         * - Reads 0xCC3F, clears bit 1
         * - Modifies register, sets bit 5, clears bit 6
         * - More delay loops
         * - Clears bit 7 of 0xCC3D
         */
        XDATA8(0xCC3F) = (XDATA8(0xCC3F) & 0xFB) | 0x04;  /* Set bit 2 */
        /* Note: Full helper implementation would include delays */
        XDATA8(0xCC3F) = XDATA8(0xCC3F) & 0xFD;  /* Clear bit 1 */
        XDATA8(0xCC3D) = XDATA8(0xCC3D) & 0x7F;  /* Clear bit 7 */
    }

    /* Helper at 0xCF28: Configure timer/link registers
     * - Reads 0xCC30, calls 0xBCEB, 0xBD49, sets bit 2
     * - Writes 0x04 to 0xCC33
     * - Clears bit 2 of 0xE324
     * - Clears bit 0 of 0xCC3B
     * - Sets bits in 0xCC39, 0xCC3A
     * - Clears bit 0 of 0xCC3E
     * - Configures 0xCA81
     */
    val = XDATA8(0xCC30);
    val = (val & 0xFB) | 0x04;  /* Set bit 2 */
    XDATA8(0xCC30) = val;

    XDATA8(0xCC33) = 0x04;

    XDATA8(0xE324) = XDATA8(0xE324) & 0xFB;  /* Clear bit 2 */
    XDATA8(0xCC3B) = XDATA8(0xCC3B) & 0xFE;  /* Clear bit 0 */

    /* Set bits 5,6 in 0xCC3A */
    XDATA8(0xCC3A) = (XDATA8(0xCC3A) & 0x9F) | 0x60;

    XDATA8(0xCC3E) = XDATA8(0xCC3E) & 0xFE;  /* Clear bit 0 */

    /* Dispatch to bank 1 handler at 0xED02 via 0x0610 */
    jump_bank_1(0xED02);

    /* Clear bits 0-1 of PHY config register 0xC233 */
    REG_PHY_CONFIG = REG_PHY_CONFIG & 0xFC;

    /* Helper at 0xBD5E: read @DPTR, clear bit 2, set bit 2 */
    val = XDATA8(0xC233);
    val = (val & 0xFB) | 0x04;  /* Set bit 2 */
    XDATA8(0xC233) = val;

    /* Timing delay - R4:R5=0x0014, R7=0x02 */
    /* In original firmware this calls 0xE80A delay function */

    /* Clear bit 2 of PHY config */
    REG_PHY_CONFIG = REG_PHY_CONFIG & 0xFB;

    /* More timing delay - R4:R5=0x000A, R7=0x03 */

    /* Polling loop: wait for status bits in 0xE712 and 0xCC11 */
    do {
        status = XDATA8(0xE712);
        /* Check bit 0 - if set, call helper and exit */
        if (status & 0x01) {
            break;
        }
        /* Check bit 1 (from value ANDed with 0x02, shifted right) */
        if ((status & 0x02) != 0) {
            break;
        }
        /* Check bit 1 of timer CSR 0xCC11 - if not set, continue polling */
    } while ((REG_TIMER0_CSR & 0x02) == 0);

    /* Final handlers - would call 0xE8EF, 0xDD42, then jump to 0xD996 */
    /* These handle completion of the timer/link setup */
}

/*
 * phy_config_link_params - Configure PHY/link control registers
 * Address: 0x5284-0x52a6 (35 bytes)
 *
 * Configures PHY link parameters by manipulating registers in 0xC6xx region.
 * Sets specific bit patterns for link training/configuration.
 *
 * From ghidra.c FUN_CODE_5284:
 *   DAT_EXTMEM_c65b = DAT_EXTMEM_c65b & 0xf7 | 8;   // set bit 3
 *   DAT_EXTMEM_c656 = DAT_EXTMEM_c656 & 0xdf;       // clear bit 5
 *   DAT_EXTMEM_c65b = DAT_EXTMEM_c65b & 0xdf | 0x20; // set bit 5
 *   DAT_EXTMEM_c62d = DAT_EXTMEM_c62d & 0xe0 | 7;   // set low 3 bits to 7
 *
 * Original disassembly:
 *   5284: mov dptr, #0xc65b
 *   5287: movx a, @dptr
 *   5288: anl a, #0xf7
 *   528a: orl a, #0x08
 *   528c: movx @dptr, a
 *   528d: mov dptr, #0xc656
 *   5290: movx a, @dptr
 *   5291: anl a, #0xdf
 *   5293: movx @dptr, a
 *   5294: mov dptr, #0xc65b
 *   5297: movx a, @dptr
 *   5298: anl a, #0xdf
 *   529a: orl a, #0x20
 *   529c: movx @dptr, a
 *   529d: mov dptr, #0xc62d
 *   52a0: movx a, @dptr
 *   52a1: anl a, #0xe0
 *   52a3: orl a, #0x07
 *   52a5: movx @dptr, a
 *   52a6: ret
 */
void phy_config_link_params(void)
{
    REG_PHY_EXT_5B = (REG_PHY_EXT_5B & 0xF7) | 0x08;
    REG_PHY_EXT_56 = REG_PHY_EXT_56 & 0xDF;
    REG_PHY_EXT_5B = (REG_PHY_EXT_5B & 0xDF) | 0x20;
    REG_PHY_EXT_2D = (REG_PHY_EXT_2D & 0xE0) | 0x07;
}

/*
 * Handler at 0x04b2 - Placeholder/Reserved handler
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
void handler_04b2(void)
{
    /* Stub function - reserved for future functionality */
    /* Original firmware at 0xE971 just returns immediately */
}

/*
 * Handler at 0x4fb6 - Core polling and dispatch handler
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
void handler_4fb6(void)
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
    while ((REG_PHY_EXT_B3 & 0x30) == 0);

    /* 0x0462 -> dispatches to some handler */

    /* Set flag indicating processing complete */
    G_STATE_FLAG_06E6 = 1;

    /* 0x0435 -> dispatches to some handler */
    /* 0x0340 -> dispatches to 0xBF8E (bank 0) - final tail call */
}

/*
 * Handler at 0x0327 - USB/Power Initialization
 * Address: 0x0327-0x032a (5 bytes) -> dispatches to 0xB1CB
 *
 * Function at 0xB1CB (142 bytes):
 * Initializes USB and power management registers:
 * - Sets power control registers (0x92C0 - set bit 7)
 * - Configures USB peripheral registers (0x91D1, 0x9300-0x9305)
 * - Sets up USB interrupt flags (0x9091, 0x9093)
 * - Configures USB control registers (0x91C1, 0x9002, 0x9005)
 * - Sets up NVMe command register (0xC42C)
 * - Calls delay helpers and configuration routines
 *
 * Original disassembly:
 *   b1cb: mov dptr, #0x92c0    ; Power control
 *   b1ce: movx a, @dptr
 *   b1cf: anl a, #0x7f         ; clear bit 7
 *   b1d1: orl a, #0x80         ; set bit 7
 *   b1d3: movx @dptr, a
 *   b1d4: mov dptr, #0x91d1
 *   b1d7: mov a, #0x0f
 *   b1d9: movx @dptr, a
 *   ... (continues with USB/power init)
 */
void handler_0327(void)
{
    uint8_t val;

    /* Set bit 7 of power control register 0x92C0 */
    val = REG_POWER_CTRL_92C0;
    val = (val & 0x7F) | 0x80;
    REG_POWER_CTRL_92C0 = val;

    /* Configure USB peripheral register 0x91D1 */
    XDATA8(0x91D1) = 0x0F;

    /* Configure registers 0x9300-0x9302 */
    XDATA8(0x9300) = 0x0C;
    XDATA8(0x9301) = 0xC0;
    XDATA8(0x9302) = 0xBF;  /* 0xC0 - 1 = 0xBF */

    /* Configure USB interrupt flags register 0x9091 */
    REG_INT_FLAGS_EX0 = 0x1F;

    /* Configure USB endpoint config 0x9093 */
    REG_USB_EP_CFG1 = 0x0F;

    /* Configure USB peripheral register 0x91C1 */
    XDATA8(0x91C1) = 0xF0;

    /* Configure registers 0x9303-0x9305 */
    XDATA8(0x9303) = 0x33;
    XDATA8(0x9304) = 0x3F;
    XDATA8(0x9305) = 0x40;  /* 0x3F + 1 = 0x40 */

    /* Configure USB control register 0x9002 */
    REG_USB_CONFIG = 0xE0;

    /* Configure USB register 0x9005 */
    XDATA8(0x9005) = 0xF0;

    /* Configure USB register 0x90E2 */
    XDATA8(0x90E2) = 0x01;

    /* Clear bit 0 of USB register 0x905E */
    XDATA8(0x905E) = XDATA8(0x905E) & 0xFE;

    /* Configure NVMe command NSID register 0xC42C */
    REG_NVME_CMD_NSID = 0x01;

    /* Clear bit 0 of register 0xC42D */
    XDATA8(0xC42D) = XDATA8(0xC42D) & 0xFE;

    /* Call helper functions at 0xD07F, 0xE214 for additional setup */
    /* These would be implemented as separate functions */

    /* Clear bit 5 of register 0x91C3 */
    XDATA8(0x91C3) = XDATA8(0x91C3) & 0xDF;

    /* Configure register 0x91C0: set bit 0, then clear bit 0 */
    val = XDATA8(0x91C0);
    val = (val & 0xFE) | 0x01;
    XDATA8(0x91C0) = val;
    XDATA8(0x91C0) = XDATA8(0x91C0) & 0xFE;

    /* Additional timing delay with R4:R5=0x018F, R7=0x04 would follow */
}

/*
 * Handler at 0x0494 - Event handler
 * Address: 0x0494-0x0498 (5 bytes) -> dispatches to bank 1 0xE56F
 *
 * Function at 0xE56F (file offset 0x1656F):
 * Event state machine handler called when events & 0x81 is set.
 *
 * Algorithm:
 *   1. Read XDATA[0x0AEE], check bit 3
 *   2. If bit 3 set: R7=1, call 0xE6F0
 *   3. Read XDATA[0x09EF], check bit 0
 *   4. If bit 0 not set, check XDATA[0x0991]
 *   5. If 0x0991 == 0, ljmp to 0xEE11
 *   6. If 0x098E == 1, R7=0x0A, call 0xABC9
 *   7. Write 0x84 to 0x097A
 *   8. Continue with helper calls for state processing
 *
 * Original disassembly:
 *   e56f: movx a, @dptr         ; read from DPTR (0x0AEE set earlier)
 *   e570: jnb 0xe0.3, 0xe578    ; if bit 3 not set, skip
 *   e573: mov r7, #0x01
 *   e575: lcall 0xe6f0          ; helper call
 *   e578: mov dptr, #0x09ef
 *   e57b: movx a, @dptr
 *   e57c: jnb 0xe0.0, 0xe596    ; if bit 0 not set, skip to check
 *   e57f: sjmp 0xe587           ; else skip
 *   e581-e596: branch logic for 0x0991 check
 *   e596: mov dptr, #0x097a
 *   e599: mov a, #0x84
 *   e59b: movx @dptr, a         ; write 0x84 to 0x097A
 *   e59c: ret
 */
void handler_0494(void)
{
    uint8_t val;
    uint8_t r7;

    /* Read state flag at 0x0AEE and check bit 3 */
    val = XDATA8(0x0AEE);
    if (val & 0x08) {
        /* Call helper at 0xE6F0 with R7=1 */
        r7 = 0x01;
        /* Helper function would be called here */
        (void)r7;
    }

    /* Read event state at 0x09EF */
    val = XDATA8(0x09EF);
    if ((val & 0x01) == 0) {
        /* Check 0x0991 state */
        val = XDATA8(0x0991);
        if (val != 0) {
            /* Check 0x098E for state 1 */
            val = XDATA8(0x098E);
            if (val == 0x01) {
                /* Call helper 0xABC9 with R7=0x0A */
                r7 = 0x0A;
                (void)r7;
            }
        } else {
            /* State 0: ljmp to 0xEE11 */
            /* This would dispatch to another handler */
        }
    }

    /* Write final state 0x84 to 0x097A */
    XDATA8(0x097A) = 0x84;
}

/*
 * Handler at 0x0606 - Error/State handler
 * Address: 0x0606-0x060a (5 bytes) -> dispatches to bank 1 0xB230
 *
 * Function at 0xB230 (file offset 0x13230):
 * Error and state management handler. Configures various control registers
 * for error handling and link state management.
 *
 * Algorithm:
 *   1. Call helper 0x96B7 to get value, modify bits, call 0x980D
 *   2. Read 0xE7FC, clear bits 0-1 and write back
 *   3. Call helpers 0x968E, 0x99E0 for state setup
 *   4. Write 0xA0 to register via 0x0BE6 helper
 *   5. Clear 0x06EC, set up R4:R5=0x0271 for transfer params
 *   6. Configure 0x0C7A with value 0x3E and mask 0x80
 *   7. Call 0x97EF, then configure 0xCCD8, 0xC801, 0xCCDA
 *
 * Original disassembly:
 *   b230: anl a, #0xef           ; clear bit 4
 *   b232: orl a, #0x10           ; set bit 4
 *   b234: lcall 0x96b7           ; helper
 *   b237: lcall 0x980d           ; helper
 *   b23a: mov dptr, #0xe7fc
 *   b23d: movx a, @dptr
 *   b23e: anl a, #0xfc           ; clear bits 0-1
 *   b240: movx @dptr, a
 *   ... (continues with state configuration)
 */
void handler_0606(void)
{
    uint8_t val;

    /* Configure REG_LINK_MODE_CTRL - clear bits 0-1 */
    val = REG_LINK_MODE_CTRL;
    val = val & 0xFC;
    REG_LINK_MODE_CTRL = val;

    /* Clear error counter at 0x06EC */
    XDATA8(0x06EC) = 0x00;

    /* Configure 0xCCD8 - clear bit 4 */
    val = XDATA8(0xCCD8);
    val = val & 0xEF;
    XDATA8(0xCCD8) = val;

    /* Configure 0xC801 - clear bit 4, set bit 4 */
    val = XDATA8(0xC801);
    val = (val & 0xEF) | 0x10;
    XDATA8(0xC801) = val;

    /* Configure 0xCCD8 - clear bits 0-2, set bits 0-2 to 4 */
    val = XDATA8(0xCCD8);
    val = (val & 0xF8) | 0x04;
    XDATA8(0xCCD8) = val;

    /* Write 0x00 to 0xCCDA, 0xC8 to 0xCCDB */
    XDATA8(0xCCDA) = 0x00;
    XDATA8(0xCCDB) = 0xC8;
}

/*
 * Handler at 0x0589 - PHY/Register Configuration
 * Address: 0x0589-0x058d (5 bytes) -> dispatches to bank 0 0xD894
 *
 * Function at 0xD894:
 * PHY and system register configuration handler.
 * Configures PCIe/USB interface registers.
 *
 * Algorithm:
 *   1. Call 0xBC8F, mask with 0xFD, call 0x0BE6 (write)
 *   2. Read 0xC809, clear bit 1, set bit 1, write back
 *   3. Call 0xB031 helper
 *   4. R1=0x02, call 0xBCB1, mask with 0xFE, call 0x0BE6
 *   5. Inc R1, write 0x01 via 0x0BE6
 *   6. Dec R1, call 0x0BC8, mask with 0xFD, call 0x0BE6
 *   7. Inc R1, write 0x02 via 0x0BE6
 *   8. R2=0x12, R1=0x1E, call 0x0BC8
 *   9. Mask with 0xFE, set bit 0, ljmp 0x0BE6
 *
 * Original disassembly:
 *   d894: lcall 0xbc8f
 *   d897: anl a, #0xfd           ; clear bit 1
 *   d899: lcall 0x0be6           ; write register
 *   d89c: mov dptr, #0xc809
 *   d89f: movx a, @dptr
 *   d8a0: anl a, #0xfd           ; clear bit 1
 *   d8a2: orl a, #0x02           ; set bit 1
 *   d8a4: movx @dptr, a
 *   d8a5: lcall 0xb031           ; helper
 *   ... (continues with register configuration)
 */
void handler_0589(void)
{
    uint8_t val;

    /* Configure register 0xC809 - clear bit 1, set bit 1 */
    val = XDATA8(0xC809);
    val = (val & 0xFD) | 0x02;
    XDATA8(0xC809) = val;

    /* Read 0x0AF1 and check bit 1 */
    val = XDATA8(0x0AF1);
    if (val & 0x02) {
        /* If bit 1 set, call handler 0x057A with R7=0x03 */
        /* This would handle a specific condition */
    }

    /* Configure register 0xB402 if needed */
    val = XDATA8(0xB402);
    val = val & 0xFE;  /* Clear bit 0 */
    XDATA8(0xB402) = val;
    val = XDATA8(0xB402);
    val = val & 0xFD;  /* Clear bit 1 */
    XDATA8(0xB402) = val;
}

/*
 * Handler at 0x0525 - Flash Command Handler
 * Address: 0x0525-0x0529 (5 bytes) -> dispatches to bank 0 0xBAA0
 *
 * Function at 0xBAA0:
 * Flash command processor. Reads commands from SPI flash buffer at 0x7000
 * and dispatches to appropriate handlers.
 *
 * Command types (from 0x7000):
 *   0x3A: Command type 1 - set flag 0x07BC=1, 0x07B8=1, call 0xE4B4, 0x538D
 *   0x3B: Command type 2 - set flag 0x07BC=2, call 0x538D
 *   0x3C: Command type 3 - set flag 0x07BC=3, call 0x538D
 *   Other: Configure 0xCC98 with (val & 0xF8) | 0x06, call 0x95B6
 *
 * Original disassembly:
 *   baa0: mov dptr, #0xe795
 *   baa3: movx a, @dptr
 *   baa4: jb 0xe0.5, 0xbaaa       ; if bit 5 set, continue
 *   baa7: ljmp 0xbb36             ; else exit
 *   baaa: lcall 0xae87            ; helper
 *   baad: lcall 0xb8c3            ; helper
 *   bab0: clr a
 *   bab1: mov r7, a
 *   bab2: lcall 0xdd42            ; helper
 *   bab5: lcall 0xe6e7            ; helper
 *   bab8: mov dptr, #0x7000       ; SPI flash buffer
 *   babb: movx a, @dptr           ; read command byte
 *   babc: cjne a, #0x3a, 0xbada   ; check for command 0x3A
 *   ... (command dispatch logic)
 */
void handler_0525(void)
{
    uint8_t val;
    uint8_t cmd;

    /* Check bit 5 of REG_FLASH_READY_STATUS - if not set, exit early */
    val = REG_FLASH_READY_STATUS;
    if ((val & 0x20) == 0) {
        return;
    }

    /* Read command from SPI flash buffer at 0x7000 */
    cmd = XDATA8(FLASH_BUFFER_BASE);

    if (cmd == 0x3A) {
        /* Command 0x3A: Set flags and process */
        G_FLASH_CMD_TYPE = 0x01;
        G_FLASH_CMD_FLAG = 0x01;
        /* Call helper 0xE4B4 for flash operation */
        /* Call helper 0x538D with R3=0xFF, R2=0x21, R1=0xFB */
    } else if (cmd == 0x3B) {
        /* Command 0x3B: Set flag and process */
        G_FLASH_CMD_TYPE = 0x02;
        /* Call helper 0x538D with R3=0xFF, R2=0x22, R1=0x0B */
    } else if (cmd == 0x3C) {
        /* Command 0x3C: Set flag and process */
        G_FLASH_CMD_TYPE = 0x03;
        /* Call helper 0x538D with R3=0xFF, R2=0x22, R1=0x25 */
    }

    /* Configure 0xCC98 register - set bits 0-2 to 6 */
    val = XDATA8(0xCC98);
    val = (val & 0xF8) | 0x06;
    XDATA8(0xCC98) = val;

    /* Write state 0x04 to 0x09FA */
    XDATA8(0x09FA) = 0x04;
}

/*
 * Handler at 0x039a - Buffer dispatch handler
 * Address: 0x039a-0x039e (5 bytes) -> dispatches to bank 0 0xD810
 *
 * Function at 0xD810:
 * Buffer transfer and USB endpoint dispatch handler.
 * Checks various status registers and initiates buffer transfers.
 *
 * Algorithm:
 *   1. Read 0x0B41, if zero return
 *   2. Read 0x9091, if bit 0 set return
 *   3. Read 0x07E4, if != 1 return
 *   4. Read 0x9000, check bit 0
 *   5. If bit 0 set, read 0xC471 and check bit 0
 *   6. Read G_EP_CHECK_FLAG (0x000A), if non-zero, exit specific branch
 *   7. Write 0x04, 0x02, 0x01 sequence to 0xCC17
 *
 * Original disassembly:
 *   d810: mov dptr, #0x0b41
 *   d813: movx a, @dptr
 *   d814: jz 0xd851              ; if zero, return
 *   d816: mov dptr, #0x9091
 *   d819: movx a, @dptr
 *   d81a: jb 0xe0.0, 0xd851      ; if bit 0 set, return
 *   ... (complex state checking)
 */
void handler_039a(void)
{
    uint8_t val;

    /* Check 0x0B41 - if zero, exit */
    val = XDATA8(0x0B41);
    if (val == 0) {
        return;
    }

    /* Check 0x9091 bit 0 - if set, exit */
    val = XDATA8(0x9091);
    if (val & 0x01) {
        return;
    }

    /* Check 0x07E4 - must equal 1 */
    val = G_SYS_FLAGS_BASE;  /* 0x07E4 */
    if (val != 0x01) {
        return;
    }

    /* Check 0x9000 bit 0 */
    val = XDATA8(0x9000);
    if (val & 0x01) {
        /* Check 0xC471 bit 0 */
        val = XDATA8(0xC471);
        if (val & 0x01) {
            return;
        }

        /* Check G_EP_CHECK_FLAG */
        val = G_EP_CHECK_FLAG;  /* 0x000A */
        if (val != 0) {
            return;
        }
    } else {
        /* Check 0x9101 bit 6 */
        val = XDATA8(0x9101);
        if (val & 0x40) {
            return;
        }
    }

    /* Initiate buffer transfer - write sequence to 0xCC17 */
    XDATA8(0xCC17) = 0x04;
    XDATA8(0xCC17) = 0x02;
    XDATA8(0xCC17) = 0x01;  /* dec a gives 0x01 */
}

/*
 * Handler at 0x0520 - System Interrupt Handler
 * Address: 0x0520-0x0524 (5 bytes) -> dispatches to bank 0 0xB4BA
 *
 * Function at 0xB4BA:
 * System interrupt handler called when system status bit 0 is set.
 * Handles link status changes and timer events.
 *
 * Algorithm:
 *   1. Read 0xCC23, check bit 1
 *   2. If bit 1 set: call 0xE3D8, write 0x02 to 0xCC23
 *   3. Read 0xCC81, check bit 1
 *   4. If bit 1 set: read 0x07BD, compare with 0x0E or 0x0D
 *   5. Configure 0xCC81 with value 0x02
 *   6. Check 0x07BC and dispatch accordingly
 *
 * Original disassembly:
 *   b4ba: mov dptr, #0xcc23
 *   b4bd: movx a, @dptr
 *   b4be: jnb 0xe0.1, 0xb4ca     ; if bit 1 not set, skip
 *   b4c1: lcall 0xe3d8           ; helper
 *   b4c4: mov dptr, #0xcc23
 *   b4c7: mov a, #0x02
 *   b4c9: movx @dptr, a          ; write 0x02
 *   ... (continues with state machine)
 */
void handler_0520(void)
{
    uint8_t val;
    uint8_t state;

    /* Read 0xCC23 and check bit 1 */
    val = XDATA8(0xCC23);
    if (val & 0x02) {
        /* Call helper 0xE3D8 */
        /* Write 0x02 to acknowledge */
        XDATA8(0xCC23) = 0x02;
    }

    /* Read 0xCC81 and check bit 1 */
    val = XDATA8(0xCC81);
    if (val & 0x02) {
        /* Read state from G_FLASH_OP_COUNTER */
        state = G_FLASH_OP_COUNTER;

        if (state == 0x0E || state == 0x0D) {
            /* Write 0x02 to 0xCC81 */
            XDATA8(0xCC81) = 0x02;

            /* Check G_FLASH_CMD_TYPE for further dispatch */
            val = G_FLASH_CMD_TYPE;
            if (val != 0) {
                /* Call helper 0xE529 with R7=0x3B */
            }
            /* Call helper 0xD676 */
        } else {
            /* Call 0xE90B for other states */
            XDATA8(0xCC81) = 0x02;
        }
    }

    /* Read 0xCC91 and check bit 1 */
    val = XDATA8(0xCC91);
    if (val & 0x02) {
        XDATA8(0xCC91) = 0x02;  /* Acknowledge */
    }
}

/*
 * Handler at 0x052f - PCIe/NVMe Event Handler
 * Address: 0x052f-0x0533 (5 bytes) -> dispatches to bank 0 0xAF5E
 *
 * Function at 0xAF5E:
 * PCIe/NVMe event handler called when PCIe status bit 6 is set.
 * Handles NVMe command completion and error events.
 *
 * Algorithm:
 *   1. Write 0x0A, 0x0D to 0xC001 (NVMe command register)
 *   2. Call helper 0x538D with R3=0xFF, R2=0x23, R1=0xEE
 *   3. Read 0xE40F, pass to helper 0x51C7
 *   4. Write 0x3A to 0xC001
 *   5. Read 0xE410, pass to helper 0x51C7
 *   6. Write 0x5D to 0xC001
 *   7. Check 0xE40F bits 7, 0, 5 for various dispatch paths
 *
 * Original disassembly:
 *   af5e: mov dptr, #0xc001
 *   af61: mov a, #0x0a
 *   af63: movx @dptr, a
 *   af64: mov a, #0x0d
 *   af66: movx @dptr, a
 *   af67: mov r3, #0xff
 *   af69: mov r2, #0x23
 *   af6b: mov r1, #0xee
 *   af6d: lcall 0x538d
 *   ... (continues with NVMe event processing)
 */
void handler_052f(void)
{
    uint8_t val;

    /* Write NVMe command sequence to 0xC001 */
    XDATA8(0xC001) = 0x0A;
    XDATA8(0xC001) = 0x0D;

    /* Call helper 0x538D with R3=0xFF, R2=0x23, R1=0xEE */
    /* This reads/processes NVMe response data */

    /* Read NVMe status from 0xE40F */
    val = XDATA8(0xE40F);

    /* Call helper 0x51C7 with status in R7 */

    /* Write next command 0x3A */
    XDATA8(0xC001) = 0x3A;

    /* Read 0xE410 and process */
    val = XDATA8(0xE410);

    /* Write command 0x5D */
    XDATA8(0xC001) = 0x5D;

    /* Check status bits in 0xE40F */
    val = XDATA8(0xE40F);

    if (val & 0x80) {
        /* Bit 7 set: call 0xDFDC helper */
    } else if (val & 0x01) {
        /* Bit 0 set: write 0x01 to 0xE40F, call 0x83D6 */
        XDATA8(0xE40F) = 0x01;
    } else if (val & 0x20) {
        /* Bit 5 set: write 0x20 to 0xE40F, call 0xDFDC */
        XDATA8(0xE40F) = 0x20;
    }
}

/*
 * Handler at 0x0570
 * Address: 0x0570-0x0574 (5 bytes)
 *
 * Dispatches to bank 1 code at 0xE911 (file offset 0x16911)
 * Called from ext1_isr when PCIe/NVMe status & 0x0F != 0.
 *
 * Original disassembly:
 *   0570: mov dptr, #0xe911
 *   0573: ajmp 0x0311
 */
extern void error_handler_e911(void);  /* Bank 1: file 0x16911 */
void handler_0570(void)
{
    error_handler_e911();
}

/*
 * Handler at 0x061a
 * Address: 0x061a-0x061e (5 bytes)
 *
 * Dispatches to bank 1 code at 0xA066 (file offset 0x12066)
 * Called from ext1_isr when event flags & 0x83 and PCIe/NVMe status bit 5 set.
 *
 * Original disassembly:
 *   061a: mov dptr, #0xa066
 *   061d: ajmp 0x0311
 */
extern void error_handler_a066(void);  /* Bank 1: file 0x12066 */
void handler_061a(void)
{
    error_handler_a066();
}

/*
 * Handler at 0x0593
 * Address: 0x0593-0x0597 (5 bytes)
 *
 * Called from ext1_isr when event flags & 0x83 and PCIe/NVMe status bit 4 set.
 *
 * Original disassembly:
 *   0593: mov dptr, #0xc105
 *   0596: ajmp 0x0300
 */
void handler_0593(void)
{
    jump_bank_0(0xC105);
}

/*
 * Handler at 0x0642
 * Address: 0x0642-0x0646 (5 bytes)
 *
 * Dispatches to bank 1 code at 0xEF4E (file offset 0x16F4E)
 * Called from ext1_isr when system status bit 4 is set.
 *
 * Original disassembly:
 *   0642: mov dptr, #0xef4e
 *   0645: ajmp 0x0311
 */
extern void error_handler_ef4e(void);  /* Bank 1: file 0x16F4E */
void handler_0642(void)
{
    error_handler_ef4e();
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

    /* Check USB master interrupt status */
    status = REG_INT_USB_MASTER;
    if (status & 0x01) {
        /* USB master interrupt - handle at 0x10e0 path */
        goto usb_master_handler;
    }

    /* Check USB peripheral status */
    status = REG_USB_PERIPH_STATUS;
    if (status & 0x20) {
        /* Peripheral interrupt - handle at 0x0f2f path */
        goto peripheral_handler;
    }

    /* Check USB endpoint status */
    status = REG_USB_STATUS;
    if (status & 0x01) {
        /* USB endpoint interrupt - handle at 0x0f1c path */
        goto endpoint_handler;
    }

    /* USB endpoint processing loop */
    usb_ep_dispatch_loop();
    return;

usb_master_handler:
    /* Handle USB master events */
    status = REG_INT_SYSTEM;
    /* TODO: Implement USB master handling */
    return;

peripheral_handler:
    /* Handle peripheral events via REG_USB_PERIPH_STATUS */
    /* TODO: Implement peripheral handling */
    return;

endpoint_handler:
    /* Handle USB endpoint events */
    /* TODO: Implement endpoint handling */
    return;
}

/*
 * Timer 0 Interrupt Handler
 * Address: 0x4486-0x4531 (172 bytes)
 * Implemented in src/drivers/timer.c
 */

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
        /* Call handler at 0x0520 */
        /* TODO: Implement handler */
    }

    /* Check CPU execution status 2 bit 2 */
    status = REG_CPU_EXEC_STATUS_2;
    if (status & 0x04) {
        REG_CPU_EXEC_STATUS_2 = 0x04;  /* Clear interrupt */
        /* Call handler at 0x0390 */
        /* TODO: Implement handler */
    }

    /* Check PCIe/NVMe status bit 6 */
    status = REG_INT_PCIE_NVME;
    if (status & 0x40) {
        /* Call handler at 0x052f */
        /* TODO: Implement handler */
    }

    /* Check event flags */
    events = G_EVENT_FLAGS & 0x83;
    if (events != 0) {
        status = REG_INT_PCIE_NVME;

        if (status & 0x20) {
            /* Call handler at 0x061a */
            /* TODO: Implement handler */
        }

        if (status & 0x10) {
            /* Call handler at 0x0593 */
            /* TODO: Implement handler */
        }

        /* Check NVMe event status */
        if (REG_NVME_EVENT_STATUS & 0x01) {
            REG_NVME_EVENT_ACK = 0x01;  /* Acknowledge */
            /* Additional NVMe processing */
        }
    }

    /* Check for additional PCIe events */
    status = REG_INT_PCIE_NVME & 0x0F;
    if (status != 0) {
        /* Call handler at 0x0570 */
        /* TODO: Implement handler */
    }

    /* Check system status bit 4 */
    status = REG_INT_SYSTEM;
    if (status & 0x10) {
        /* Call handler at 0x0642 */
        /* TODO: Implement handler */
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
