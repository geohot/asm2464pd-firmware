/*
 * nvme.h - NVMe Command and Queue Management
 *
 * NVMe controller interface for the ASM2464PD USB4/Thunderbolt to NVMe bridge.
 * Handles NVMe command submission, completion, and queue management for
 * downstream NVMe SSDs connected via PCIe.
 *
 * BLOCK DIAGRAM
 *   USB/PCIe ──> SCSI Cmd ──> NVMe Cmd Builder ──> Submission Queue
 *       │                          │                     │
 *       │                          v                     v
 *       │                    ┌──────────┐          ┌──────────┐
 *       │                    │ NVMe Regs│          │ PCIe DMA │
 *       │                    │ 0xC400+  │          │ Engine   │
 *       │                    └──────────┘          └────┬─────┘
 *       │                                               │
 *       <───── SCSI Status <── NVMe Completion <── Completion Queue
 *
 * ===========================================================================
 * QUEUE ARCHITECTURE
 * ===========================================================================
 *
 * NVMe uses paired Submission Queues (SQ) and Completion Queues (CQ):
 *
 *   Admin Queue Pair (QID 0):
 *   - For controller management: Identify, Create I/O Queue, Set Features
 *   - Single pair, always exists
 *   - Queue depth from flash config (G_FLASH_NVME_QDEPTH)
 *
 *   I/O Queue Pairs (QID 1+):
 *   - For Read/Write/Flush commands to NVMe namespace
 *   - Created during initialization via Admin Create I/O Queue command
 *   - Support up to 32 outstanding commands (5-bit CID counter)
 *
 * QUEUE ENTRY STRUCTURES:
 *
 *   Submission Queue Entry (SQE) - 64 bytes:
 *   +--------+--------+--------+--------+
 *   | Opcode | Flags  | CID    | NSID   |  Bytes 0-7
 *   +--------+--------+--------+--------+
 *   | MPTR (metadata pointer)           |  Bytes 8-15
 *   +--------+--------+--------+--------+
 *   | PRP1 (data buffer address)        |  Bytes 16-23
 *   +--------+--------+--------+--------+
 *   | PRP2 (continued or PRP list)      |  Bytes 24-31
 *   +--------+--------+--------+--------+
 *   | Command-specific dwords           |  Bytes 32-63
 *   +--------+--------+--------+--------+
 *
 *   Completion Queue Entry (CQE) - 16 bytes:
 *   +--------+--------+--------+--------+
 *   | Command Specific Result           |  Bytes 0-3
 *   +--------+--------+--------+--------+
 *   | Reserved                          |  Bytes 4-7
 *   +--------+--------+--------+--------+
 *   | SQ Head | SQ ID  | CID    | Status |  Bytes 8-15
 *   +--------+--------+--------+--------+
 *
 * QUEUE POINTERS (stored in XDATA):
 *   - G_NVME_SQ_HEAD: Submission Queue head (consumer, updated by controller)
 *   - G_NVME_SQ_TAIL: Submission Queue tail (producer, updated by firmware)
 *   - G_NVME_CQ_HEAD: Completion Queue head (consumer, updated by firmware)
 *   - G_NVME_CQ_TAIL: Completion Queue tail (producer, updated by controller)
 *
 * PHASE BIT:
 *   - Used to detect new completion entries
 *   - Toggles when queue wraps around
 *   - Stored in CQE status field (bit 0)
 *
 * COMMAND ID (CID) TRACKING:
 *   - 16-bit unique ID per outstanding command
 *   - Low 5 bits used as slot index (max 32 commands)
 *   - Tracked in I_TRANSFER_6B-6E (queue state variables)
 *
 * ===========================================================================
 * SCSI-TO-NVME TRANSLATION
 * ===========================================================================
 *
 *   SCSI READ(10/12/16)  → NVMe Read (opcode 0x02)
 *   SCSI WRITE(10/12/16) → NVMe Write (opcode 0x01)
 *   SCSI SYNC CACHE      → NVMe Flush (opcode 0x00)
 *   SCSI INQUIRY         → NVMe Identify (cached)
 *   SCSI READ CAPACITY   → From Identify Namespace data
 *   SCSI TEST UNIT READY → Check controller status
 *
 * ===========================================================================
 * REGISTER MAP
 * ===========================================================================
 *
 * NVMe Command Registers (0xC400-0xC47F):
 *   0xC400  NVME_CTRL         Control register
 *   0xC401  NVME_STATUS       Status register
 *   0xC412  NVME_CTRL_STATUS  Control/status combined
 *   0xC413  NVME_CONFIG       Configuration
 *   0xC414  NVME_DATA_CTRL    Data transfer control
 *   0xC415  NVME_DEV_STATUS   Device presence/ready status
 *   0xC420  NVME_CMD          Command register
 *   0xC421  NVME_CMD_OPCODE   NVMe opcode
 *   0xC422  NVME_LBA_0        LBA byte 0 (bits 0-7)
 *   0xC423  NVME_LBA_1        LBA byte 1 (bits 8-15)
 *   0xC424  NVME_LBA_2        LBA byte 2 (bits 16-23)
 *   0xC425  NVME_COUNT_LO     Transfer count low
 *   0xC426  NVME_COUNT_HI     Transfer count high
 *   0xC427  NVME_ERROR        Error code
 *   0xC428  NVME_QUEUE_CFG    Queue configuration
 *   0xC429  NVME_CMD_PARAM    Command parameters
 *   0xC42A  NVME_DOORBELL     Queue doorbell
 *   0xC440  NVME_SQ_HEAD_LO   Submission queue head low
 *   0xC441  NVME_SQ_HEAD_HI   Submission queue head high
 *   0xC442  NVME_SQ_TAIL_LO   Submission queue tail low
 *   0xC443  NVME_SQ_TAIL_HI   Submission queue tail high
 *   0xC444  NVME_CQ_HEAD_LO   Completion queue head low
 *   0xC445  NVME_CQ_HEAD_HI   Completion queue head high
 *   0xC446  NVME_LBA_3        LBA byte 3 (bits 24-31)
 *   0xC462  DMA_ENTRY         DMA entry point
 *   0xC470-7F                 Command queue directory (16 entries)
 *
 * NVMe Event Registers (0xEC00-0xEC0F):
 *   0xEC04  NVME_EVENT_ACK    Event acknowledge
 *   0xEC06  NVME_EVENT_STATUS Event status
 *
 * Command Engine Registers (0xCC88-0xCC8A):
 *   0xCC88  CMD_ENGINE_CTRL   Command engine control
 *   0xCC89  CMD_ENGINE_STATE  Command state (bit patterns control flow)
 *   0xCC8A  CMD_ENGINE_PARAM  Command parameter
 *
 * SCSI DMA Registers (0xCE40-0xCEFF):
 *   0xCE88  SCSI_DMA_CTRL     DMA control register
 *   0xCE89  SCSI_DMA_STATUS   DMA status (REG_USB_DMA_STATE)
 *   0xCEB0  XFER_STATUS       Transfer status
 *
 * NVMe Command Configuration (0xE400-0xE42F):
 *   0xE400  NVME_CFG_FLAGS    NVMe configuration flags
 *   0xE405  NVME_CFG_CTRL     NVMe control configuration
 *   0xE41C  NVME_CFG_STATUS   NVMe status configuration
 *
 * ===========================================================================
 * KEY DATA STRUCTURES
 * ===========================================================================
 *
 * IDATA Queue Variables:
 *   0x09-0x0D: Current command parameters (boot sig reused as cmd buf)
 *   0x16-0x17: Transfer length (16-bit, I_CORE_STATE_L/H)
 *   0x6B-0x6F: Queue state variables (I_TRANSFER_6B-6E, I_BUF_FLOW_CTRL)
 *
 * XDATA Command Table (0x05B1-0x06CF):
 *   - 10 entries × 34 bytes = 340 bytes
 *   - Tracks pending commands for vendor E4/E5 and NVMe
 *   - See G_CMD_TABLE_BASE in globals.h
 *
 * ===========================================================================
 * COMMAND FLOW
 * ===========================================================================
 *
 *   1. SCSI command received via USB bulk endpoint
 *   2. scsi_dispatch() translates to NVMe command
 *   3. nvme_build_cmd() constructs SQE in XDATA buffer
 *   4. nvme_submit_cmd() writes SQE to submission queue
 *   5. Doorbell write triggers NVMe controller
 *   6. Controller processes command, writes CQE
 *   7. Interrupt signals completion
 *   8. nvme_check_completion() reads CQE, updates status
 *   9. SCSI status returned to host via CSW
 */
#ifndef _NVME_H_
#define _NVME_H_

#include "../types.h"

/* NVMe initialization */
void nvme_set_usb_mode_bit(void);               /* 0x1bde-0x1be7 */
void nvme_init_step(void);                      /* 0x1be8-0x1bf5 */
void nvme_init_registers(void);                 /* 0x1bf6-0x1c0e */
void nvme_wait_for_ready(void);                 /* 0x1bcb-0x1bd4 */
void nvme_initialize(__xdata uint8_t *ptr);     /* 0x1c0f-0x1c1a */

/* NVMe configuration */
__xdata uint8_t *nvme_get_config_offset(void);  /* 0x1c22-0x1c29 */
void nvme_calc_buffer_offset(uint8_t index);    /* 0x1c77-0x1c7d */
void nvme_load_transfer_data(void);             /* 0x1c6d-0x1c76 */
__xdata uint8_t *nvme_calc_idata_offset(void);  /* 0x1c88-0x1c8f */

/* NVMe status */
void nvme_status_update(void);                  /* 0x1b47-0x1b5f */
uint8_t nvme_check_scsi_ctrl(void);             /* 0x1cae-0x1cb6 */
uint8_t nvme_get_cmd_param_upper(void);         /* 0x1cb7-0x1cc0 */
uint8_t nvme_get_dev_status_upper(void);        /* 0x1cc1-0x1cc7 */
uint8_t nvme_get_data_ctrl_upper(void);         /* 0x1c56-0x1c5c */
uint8_t nvme_get_link_status_masked(void);      /* 0x1d24-0x1d2a */
uint8_t nvme_get_idata_0d_r7(void);             /* 0x1cd4-0x1cdb */
uint8_t nvme_get_dma_status_masked(void);       /* 0x1d2b-0x1d31 */
uint8_t nvme_get_pcie_count_config(void);       /* 0x1d32-0x1d38 */
uint8_t nvme_get_idata_009f(void);              /* 0x1ce4-0x1cef */

/* NVMe data operations */
void nvme_subtract_idata_16(uint8_t hi, uint8_t lo);    /* 0x1cdc-0x1ce3 */
void nvme_inc_circular_counter(void);           /* 0x3244-0x3248 */
void nvme_set_ep_queue_ctrl_84(void);           /* 0x3249-0x3256 */
void nvme_clear_status_bit1(void);              /* 0x1c3a-0x1c49 */
void nvme_set_data_ctrl_bit7(void);             /* 0x1c4a-0x1c54 */
void nvme_store_idata_16(uint8_t hi, uint8_t lo);       /* 0x1c5d-0x1c6c */
void nvme_add_to_global_053a(void);             /* 0x1cc8-0x1cd3 */
void nvme_set_int_aux_bit1(void);               /* 0x1c90-0x1c9e */
void nvme_set_ep_ctrl_bits(__xdata uint8_t *ptr);       /* 0x3257-0x325e */
void nvme_set_usb_ep_ctrl_bit2(__xdata uint8_t *ptr);   /* 0x325f-0x3266 */
void nvme_set_buffer_flags(void);               /* 0x3279-0x327f */

/* NVMe address calculation */
__xdata uint8_t *nvme_calc_addr_01xx(uint8_t offset);   /* 0x3267-0x3271 */
__xdata uint8_t *nvme_calc_addr_012b(uint8_t offset);   /* 0x3272-0x3278 */
__xdata uint8_t *nvme_calc_addr_04b7(void);             /* 0x3280-0x3289 */
__xdata uint8_t *nvme_calc_dptr_0500_base(uint8_t val); /* 0x328a-0x3290 */
__xdata uint8_t *nvme_calc_dptr_direct_with_carry(uint8_t val);  /* 0x320c-0x3218 */
__xdata uint8_t *nvme_add_8_to_addr(uint8_t addr_lo, uint8_t addr_hi);  /* 0x3212-0x3218 */
__xdata uint8_t *nvme_get_addr_012b(void);              /* 0x3219-0x3222 */
__xdata uint8_t *nvme_calc_dptr_0100_base(uint8_t val); /* 0x3223-0x322d */

/* NVMe completion and doorbell */
void nvme_check_completion(__xdata uint8_t *ptr);       /* 0x323b-0x3248 */
void nvme_ring_doorbell(__xdata uint8_t *doorbell);     /* 0x31fb-0x320b */
void nvme_read_and_sum_index(__xdata uint8_t *ptr);     /* 0x3291-0x3297 */
void nvme_read_status(__xdata uint8_t *ptr);            /* 0x3298-0x329e */

/* NVMe DMA operations */
void nvme_write_params_to_dma(uint8_t val);     /* 0x31da-0x31e0 */
void nvme_calc_addr_from_dptr(__xdata uint8_t *ptr);    /* 0x31ea-0x31fa */
void nvme_copy_idata_to_dptr(__xdata uint8_t *ptr);     /* 0x32a4-0x3418 */

/* NVMe call and signal */
void nvme_call_and_signal(void);                /* 0x329f-0x32a3 */
void usb_validate_descriptor(void);             /* 0x3419-0x3576 */

/* NVMe commands */
void nvme_process_cmd(uint8_t param);           /* 0x488f-0x48ff */
void nvme_io_request(uint8_t param1, __xdata uint8_t *param2, uint8_t param3, uint8_t param4);  /* 0x4900-0x49ff */
uint8_t nvme_build_cmd(uint8_t param);          /* 0x4a00-0x4aff */
uint8_t nvme_get_ep_table_entry(__xdata uint8_t *index_ptr);  /* 0x4b00-0x4b5f */
void nvme_submit_cmd(void);                     /* 0x4b60-0x4bff */
void nvme_io_handler(uint8_t param);            /* 0x4c00-0x4cff */

/* NVMe helper functions */
uint8_t nvme_func_1b07(void);                   /* 0x1b07-0x1b0a */
uint8_t nvme_func_1b0b(uint8_t param);          /* 0x1b0b-0x1b13 */
uint8_t nvme_check_threshold_r5(uint8_t val);   /* 0x1b2b-0x1b2c */
uint8_t nvme_check_threshold_0x3e(void);        /* 0x1b38-0x1b3d */
uint8_t nvme_func_1c2a(uint8_t param);          /* 0x1c2a-0x1c2f */
void nvme_func_1c43(uint8_t param);             /* 0x1c43-0x1c49 */
uint8_t nvme_func_1c55(void);                   /* 0x1c55-0x1c5c */
void nvme_func_1c7e(void);                      /* 0x1c7e-0x1c87 */
uint8_t nvme_func_1c9f(void);                   /* 0x1c9f-0x1cad */
void nvme_func_1cf0(void);                      /* 0x1cf0-0x1cff */

/* USB check functions (in nvme.c) */
void usb_check_status(uint8_t param_1, __xdata uint8_t *param_2);  /* 0x1b4d-0x1b5c */
void usb_configure(__xdata uint8_t *ptr);       /* 0x1b58-0x1b5f */
void usb_data_handler(__xdata uint8_t *ptr);    /* 0x1b84-0x1b8c */

/* NVMe queue processing */
void nvme_process_queue_entries(void);          /* 0x488f-0x48ff */
void nvme_state_handler(void);                  /* 0x4784-0x47ff */
void nvme_queue_sync(void);                     /* 0x49e9-0x4a56 */
void nvme_queue_process_pending(void);          /* 0x3e81-0x3eff */
void nvme_queue_state_update(uint8_t param);    /* 0x5359-0x5398 */
/* NOTE: nvme_queue_helper (0x1196) moved to event_handler.c as nvme_cmd_status_init */

/* NVMe command engine */
void nvme_cmd_store_and_trigger(uint8_t param, __xdata uint8_t *ptr);  /* 0x95a8-0x95b5 */
void nvme_cmd_store_direct(uint8_t param, __xdata uint8_t *ptr);       /* 0x9b31-0x9b5a */
uint8_t nvme_cmd_store_and_read(uint8_t param, __xdata uint8_t *ptr);  /* 0x955d-0x9565 */
uint8_t nvme_cmd_read_offset(__xdata uint8_t *ptr);     /* 0x9566-0x9583 */
void nvme_cmd_issue_with_setup(uint8_t param);  /* 0x9584-0x959f */
void nvme_cmd_issue_alternate(uint8_t param);   /* 0x95a0-0x95b5 */
void nvme_cmd_issue_simple(uint8_t param);      /* 0x95b6-0x95c8 */
void nvme_cmd_issue_with_tag(uint8_t param1, uint8_t param2);  /* 0x95c9-0x95d9 */
void nvme_cmd_store_pair_trigger(uint8_t param1, __xdata uint8_t *ptr, uint8_t param2);  /* 0x95da-0x95ea */
void nvme_cmd_set_state_6(void);                /* 0x95eb-0x95f8 */
void nvme_timer_init_95b6(void);                /* 0x95b6-0x95c8 */
void nvme_timer_ack_95bf(void);                 /* 0x95bf-0x95c8 */
void nvme_timer_ack_ptr(__xdata uint8_t *ptr);  /* 0x95f9-0x9604 */
void nvme_cmd_clear_5_bytes(__xdata uint8_t *ptr);      /* 0x9617-0x9620 */
void nvme_cmd_set_bit1_e41c(void);              /* 0x9621-0x962d */
void nvme_cmd_set_bit1_ptr(__xdata uint8_t *ptr);       /* 0x962e-0x9634 */
void nvme_cmd_shift_6(__xdata uint8_t *ptr, uint8_t val);       /* 0x9635-0x9646 */
void nvme_int_ctrl_set_bit4(void);              /* 0x9647-0x964e */
void nvme_cmd_clear_cc88(void);                 /* 0x964f-0x9655 */
void nvme_cmd_store_clear_cc8a(uint8_t param, __xdata uint8_t *ptr);  /* 0x9656-0x965c */
uint8_t nvme_flash_check_xor5(void);            /* 0x9664-0x966a */
void nvme_cmd_clear_e405_setup(void);           /* 0x966b-0x9674 */
uint8_t nvme_cmd_clear_bit4_mask(__xdata uint8_t *ptr); /* 0x9684-0x968e */
void nvme_cmd_set_cc89_2(void);                 /* 0x969d-0x96a5 */
void nvme_cmd_shift_6_store(uint8_t val, __xdata uint8_t *ptr); /* 0x96a6-0x96ad */
void nvme_cmd_shift_2_mask3(uint8_t val, __xdata uint8_t *ptr); /* 0x96ae-0x96b6 */
void nvme_set_flash_counter_5(void);            /* 0x96b7-0x96be */
void nvme_cmd_dd12_0x10(void);                  /* 0xdd12-0xdd41 */
uint8_t nvme_lba_combine(uint8_t val);          /* 0x96bf-0x96cc */

#endif /* _NVME_H_ */
