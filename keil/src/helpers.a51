; ASM2464PD Firmware - Helper Functions (Assembly)
;
; These helper functions are at fixed addresses in the original firmware.
; They must be linked at their original locations.

NAME    HELPERS

; Public symbols
PUBLIC  idata_load_dword
PUBLIC  cmp32
PUBLIC  load_both_sigs

; Segment at 0x0D78 for idata_load_dword
?PR?idata_load_dword?HELPERS   SEGMENT CODE

    RSEG    ?PR?idata_load_dword?HELPERS

;-----------------------------------------------------------
; idata_load_dword - Load 32-bit from IDATA[@R0] into R4-R7
; Address: 0x0D78-0x0D83 (12 bytes)
;
; Input:  R0 = IDATA address
; Output: R4:R5:R6:R7 = 32-bit value (R4=LSB, R7=MSB)
;-----------------------------------------------------------
idata_load_dword:
    mov     a, @r0          ; 0D78: e6
    mov     r4, a           ; 0D79: fc
    inc     r0              ; 0D7A: 08
    mov     a, @r0          ; 0D7B: e6
    mov     r5, a           ; 0D7C: fd
    inc     r0              ; 0D7D: 08
    mov     a, @r0          ; 0D7E: e6
    mov     r6, a           ; 0D7F: fe
    inc     r0              ; 0D80: 08
    mov     a, @r0          ; 0D81: e6
    mov     r7, a           ; 0D82: ff
    ret                     ; 0D83: 22

;-----------------------------------------------------------
; cmp32 - Compare R0:R1:R2:R3 with R4:R5:R6:R7
; Address: 0x0D22-0x0D32 (17 bytes)
;
; Performs (R0:R1:R2:R3) - (R4:R5:R6:R7) with borrow
; Result: A = OR of all difference bytes (0 if equal)
;         Carry set based on comparison
;-----------------------------------------------------------
cmp32:
    mov     a, r3           ; 0D22: eb
    subb    a, r7           ; 0D23: 9f
    mov     0F0H, a         ; 0D24: f5 f0  (B register)
    mov     a, r2           ; 0D26: ea
    subb    a, r6           ; 0D27: 9e
    orl     0F0H, a         ; 0D28: 42 f0
    mov     a, r1           ; 0D2A: e9
    subb    a, r5           ; 0D2B: 9d
    orl     0F0H, a         ; 0D2C: 42 f0
    mov     a, r0           ; 0D2E: e8
    subb    a, r4           ; 0D2F: 9c
    orl     a, 0F0H         ; 0D30: 45 f0
    ret                     ; 0D32: 22

;-----------------------------------------------------------
; load_both_sigs - Load boot sig to R4-R7, prepare for compare
; Address: 0x1B7E-0x1B87 (10 bytes)
;
; Loads IDATA[0x09-0x0C] into R4-R7 via idata_load_dword,
; then sets R0 to 0x6B for loading transfer sig
;-----------------------------------------------------------
load_both_sigs:
    mov     r0, #009H       ; 1B7E: 78 09
    lcall   idata_load_dword ; 1B80: 12 0d 78
    mov     r0, #06BH       ; 1B83: 78 6b
    ljmp    0D90H           ; 1B85: 02 0d 90  (jump to another helper)

    END
