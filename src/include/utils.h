/*
 * utils.h - Utility function declarations
 *
 * Generic utility functions for memory access, data manipulation,
 * and 32-bit math operations.
 */
#ifndef _UTILS_H_
#define _UTILS_H_

#include "types.h"

/* Stub functions (TODO: implement) */
uint8_t pcie_short_delay(void);                 /* 0xbefb - returns PHY mode bits 4-5 */
void cmd_engine_wait_idle(void);                /* 0xb8c3 */
void link_state_init_stub(void);                /* 0x9536 */

/* IDATA dword operations */
uint32_t idata_load_dword(__idata uint8_t *ptr);            /* 0x0d78-0x0d83 */
uint32_t idata_load_dword_alt(__idata uint8_t *ptr);        /* 0x0d90-0x0d9c */
void idata_store_dword(__idata uint8_t *ptr, uint32_t val); /* 0x0db9-0x0dc4 */

/* XDATA dword operations */
uint32_t xdata_load_dword(__xdata uint8_t *ptr);            /* 0x0d84-0x0d8f */
uint32_t xdata_load_dword_alt(__xdata uint8_t *ptr);        /* 0x0d9d-0x0da8 */
void xdata_store_dword(__xdata uint8_t *ptr, uint32_t val); /* 0x0dc5-0x0dd0 */

/* Triple byte operations */
uint32_t xdata_load_triple(__xdata uint8_t *ptr);           /* 0x0ddd-0x0de5 */
void xdata_store_triple(__xdata uint8_t *ptr, uint32_t val);/* 0x0de6-0x0dee */

/* Pointer math */
__xdata uint8_t *dptr_index_mul(__xdata uint8_t *base, uint8_t index, uint8_t element_size);  /* 0x0dd1-0x0ddc */

/* 32-bit math operations (register calling convention) */
void mul16x16(void) __naked;                    /* 0x0bfd-0x0c0e */
void add32(void) __naked;                       /* 0x0c9e-0x0caa */
void sub32(void) __naked;                       /* 0x0cab-0x0cb8 */
void mul32(void) __naked;                       /* 0x0cb9-0x0d07 */
void or32(void) __naked;                        /* 0x0d08-0x0d14 */
void xor32(void) __naked;                       /* 0x0d15-0x0d21 */
void shl32(void) __naked;                       /* 0x0d46-0x0d58 */
uint8_t cmp32(void) __naked;                    /* 0x0d22-0x0d32 - returns 0 if equal */

/* Naked load/store for inline assembly (DPTR already set) */
void load_dword_r4r7(void) __naked;             /* 0x0d84-0x0d8f: load XDATA[DPTR] to R4-R7 */
void load_dword_r0r3(void) __naked;             /* 0x0d9d-0x0da8: load XDATA[DPTR] to R0-R3 */
void store_dword_r4r7(void) __naked;            /* 0x0dc5-0x0dd0: store R4-R7 to XDATA[DPTR] */

/* Generic register bit operations */
uint8_t reg_read_indexed_0a84(uint8_t offset, uint8_t base);/* 0xbb4f-0xbb5d */
uint8_t reg_extract_bit6(__xdata uint8_t *dest, uint8_t val);/* 0xbb5e-0xbb67 */
void reg_set_bits_1_2(__xdata uint8_t *reg);                /* 0xbb68-0xbb74 */
uint8_t reg_extract_bit7(__xdata uint8_t *dest, uint8_t val);/* 0xbb75-0xbb7d */
uint8_t reg_write_indexed(uint8_t dph, uint8_t dpl, uint8_t val);/* 0xbb8f-0xbb95 */
uint8_t reg_extract_bits_6_7(__xdata uint8_t *dest, uint8_t val);/* 0xbb96-0xbb9f */
uint8_t reg_extract_bit0(__xdata uint8_t *dest, uint8_t val);/* 0xbba0-0xbba7 */
void reg_set_bit6(__xdata uint8_t *reg);                    /* 0xbba8-0xbbae */
void reg_set_bit1(__xdata uint8_t *reg);                    /* 0xbbaf-0xbbb5 */
__xdata uint8_t *reg_set_event_flag(void);                  /* 0xbbb6-0xbbbf */
void reg_set_bit3(__xdata uint8_t *reg);                    /* 0xbbc0-0xbbc6 */
uint8_t reg_nibble_swap_store(__xdata uint8_t *reg);        /* 0xbc70-0xbc87 */
uint8_t reg_nibble_extract(__xdata uint8_t *reg);           /* 0xbcb8-0xbcc3 */
void reg_set_bit5(__xdata uint8_t *reg);                    /* 0xbd23-0xbd29 */
void reg_clear_bits_5_6(__xdata uint8_t *reg);              /* 0xbd2a-0xbd32 */
uint8_t reg_read_cc3e_clear_bit1(void);                     /* 0xbd33-0xbd39 */
void reg_set_bit6_generic(__xdata uint8_t *reg);            /* 0xbd3a-0xbd40 */
void reg_set_bit2(__xdata uint8_t *reg);                    /* 0xbd5e-0xbd64 */
void reg_set_bit7(__xdata uint8_t *reg);                    /* 0xbd65-0xbd6b */
void reg_clear_state_flags(void);                           /* 0xbf8e-0xbfa2 */

/* Bank read functions */
uint8_t reg_read_bank_1235(void);               /* 0xbc88-0xbc8e */
uint8_t reg_read_bank_0200(void);               /* 0xbc8f-0xbc97 */
uint8_t reg_read_bank_1200(void);               /* 0xbc98-0xbc9e */
uint8_t reg_read_and_clear_bit3(uint8_t offset);/* 0xbca5-0xbcae */
uint8_t reg_read_bank_1603(void);               /* 0xbcaf-0xbcb7 */
uint8_t reg_read_bank_1504_clear(void);         /* 0xbcc4-0xbccf */
uint8_t reg_read_bank_1200_alt(void);           /* 0xbcd0-0xbcd6 */
uint8_t reg_read_event_mask(void);              /* 0xbcd7-0xbcdd */
uint8_t reg_read_bank_1407(void);               /* 0xbcde-0xbce6 */
uint8_t reg_read_cpu_mode_next(void);           /* 0xbd57-0xbd5d */
uint8_t reg_delay_param_setup(void);            /* 0xbefb-0xbf04 */

/* System initialization */
void init_sys_flags_07f0(void);                 /* 0x4be6-0x4c03 */

/* Code/PDATA memory operations */
uint32_t code_load_dword(__code uint8_t *ptr);              /* 0x0da9-0x0db8 */
void pdata_store_dword(__pdata uint8_t *ptr, uint32_t val); /* 0x0e4f-0x0e5a */

/* Banked memory operations */
void banked_store_dword(uint8_t dpl, uint8_t dph, uint8_t bank, uint32_t val);  /* 0x0ba9-0x0bc7 */
uint8_t banked_load_byte(uint8_t addrlo, uint8_t addrhi, uint8_t memtype);      /* 0x0bc8-0x0bd4 */
void banked_store_byte(uint8_t addrlo, uint8_t addrhi, uint8_t memtype, uint8_t val);  /* 0x0be6-0x0bfc */

/* Banked register helper functions */
void banked_store_and_load_bc9f(uint8_t val);          /* 0xbc9f-0xbca4: store val, then load */
void banked_multi_store_bc63(uint8_t val);             /* 0xbc63-0xbc6f: multi-byte store sequence */

/* Table search */
void table_search_dispatch_alt(void) __naked;   /* 0x0def-0x0e14 */
void table_search_dispatch(void) __naked;       /* 0x0e15-0x0e4e */

/* Helper functions */
void dptr_setup_stub(void);
void dptr_calc_ce40_indexed(uint8_t a, uint8_t b);
void dptr_calc_ce40_param(uint8_t param);
uint8_t get_ep_config_indexed(void);            /* 0x1646-0x1658 */
uint8_t addr_setup_0059(uint8_t offset);        /* 0x1752-0x175c */
void mem_write_via_ptr(uint8_t value);          /* 0x159f */
void dptr_calc_work43(void);
void dma_queue_ptr_setup(void);                 /* 0x173b */

/* System status pointers */
__xdata uint8_t *get_sys_status_ptr_0456(uint8_t param);   /* 0x16e9-0x16f2 */
__xdata uint8_t *get_sys_status_ptr_0400(uint8_t param);   /* 0x16eb-0x16f2 */

/* USB buffer pointers */
__xdata uint8_t *usb_buf_ptr_0108(uint8_t param);          /* 0x1b2e-0x1b37 */
__xdata uint8_t *usb_buf_ptr_0100(uint8_t param);          /* 0x1b30-0x1b37 */
__xdata uint8_t *xdata_ptr_from_param(uint8_t param);      /* 0x1c13-0x1c1a */

/* Misc helpers */
uint8_t xdata_read_0100(uint8_t low_byte, uint8_t carry);  /* 0x1b0b-0x1b13 */
uint8_t xdata_write_load_triple_1564(uint8_t value, uint8_t r1_addr, uint8_t r2_addr, uint8_t r3_mode);  /* 0x1564-0x156e */
uint8_t load_triple_1564_read(void);                       /* 0x1b77 */

#endif /* _UTILS_H_ */
