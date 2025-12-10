; ASM2464PD Firmware - Startup and Vectors
; Address: 0x0000-0x0103
;
; This file contains the reset vector, interrupt vectors,
; and startup_0016 boot state verification code.
;
; Must be assembled to match fw.bin exactly.

$NOMOD51                    ; Don't include standard 8051 definitions

;--------------------------------------------------------------------
; 0x0000: Reset Vector - LJMP to main at 0x431A
;--------------------------------------------------------------------
        CSEG    AT 0000H
reset_vector:
        LJMP    0431AH          ; 02 43 1A

;--------------------------------------------------------------------
; 0x0003: INT0 Vector - LJMP to INT0 handler at 0x0E5B
;--------------------------------------------------------------------
        CSEG    AT 0003H
int0_vector:
        LJMP    00E5BH          ; 02 0E 5B

;--------------------------------------------------------------------
; 0x0006-0x0011: helper_0006 - Call 0x50DB and decrement counter
;--------------------------------------------------------------------
        CSEG    AT 0006H
helper_0006:
        LCALL   050DBH          ; 12 50 DB
        MOV     DPTR, #000AH    ; 90 00 0A
        MOVX    A, @DPTR        ; E0
        JZ      helper_ret      ; 60 02
        DEC     A               ; 14
        MOVX    @DPTR, A        ; F0
helper_ret:
        RET                     ; 22

;--------------------------------------------------------------------
; 0x0012: Padding NOP
;--------------------------------------------------------------------
        CSEG    AT 0012H
        NOP                     ; 00

;--------------------------------------------------------------------
; 0x0013: INT1 Vector - LJMP to INT1 handler at 0x4486
;--------------------------------------------------------------------
        CSEG    AT 0013H
int1_vector:
        LJMP    04486H          ; 02 44 86

;--------------------------------------------------------------------
; 0x0016-0x0103: startup_0016 - Boot state verification
;
; This boot state machine checks IDATA signatures to determine
; whether this is a warm boot or cold boot.
;
; Boot states written to XDATA[0x0001]:
;   0: Normal boot, signatures zero
;   1: Cold boot, secondary signature non-zero
;   2: Boot mode == 5
;   3: Signature mismatch (setb c path)
;   4: Boot mode == 2 or 4
;   5: Boot mode == 5 (alt path)
;   6: Signature mismatch (clr c path)
;   7: Signature mismatch (second compare)
;--------------------------------------------------------------------
        CSEG    AT 0016H
startup_0016:
        ; Clear boot state at XDATA[0x0001]
        CLR     A               ; E4
        MOV     DPTR, #0001H    ; 90 00 01
        MOVX    @DPTR, A        ; F0

        ; Load transfer signature from IDATA[0x6B-0x6E]
        MOV     R0, #06BH       ; 78 6B
        LCALL   00D78H          ; 12 0D 78 - load_idata_32 -> R4:R5:R6:R7

        ; Check if transfer signature is zero
        MOV     A, R4           ; EC
        ORL     A, R5           ; 4D
        ORL     A, R6           ; 4E
        ORL     A, R7           ; 4F
        JNZ     check_mode      ; 70 17 - if non-zero, check mode

        ; Transfer signature is zero - check boot signature
        MOV     R0, #009H       ; 78 09
        LCALL   00D78H          ; 12 0D 78 - load_idata_32
        MOV     A, R4           ; EC
        ORL     A, R5           ; 4D
        ORL     A, R6           ; 4E
        ORL     A, R7           ; 4F
        JNZ     set_state_1     ; 70 03
        LJMP    boot_dispatch   ; 02 01 04 - both zero, dispatch

set_state_1:
        MOV     DPTR, #0001H    ; 90 00 01
        MOV     A, #01H         ; 74 01
        MOVX    @DPTR, A        ; F0
        LJMP    boot_dispatch   ; 02 01 04

check_mode:
        ; At 0x003D: Transfer sig non-zero, check boot mode at 0x0AF3
        MOV     DPTR, #0AF3H    ; 90 0A F3
        MOVX    A, @DPTR        ; E0
        XRL     A, #80H         ; 64 80 - compare with 0x80
        JNZ     mode_not_80     ; 70 64 - if != 0x80, different path

        ; Mode == 0x80: Check I_STATE_6A
        MOV     R0, #06AH       ; 78 6A
        MOV     A, @R0          ; E6
        DEC     A               ; 14 - state - 1
        JZ      compare_sigs_80 ; 60 1D - state 1
        DEC     A               ; 14
        JZ      state_4_path    ; 60 53 - state 2
        DEC     A               ; 14
        JZ      compare_sigs_80 ; 60 17 - state 3
        DEC     A               ; 14
        JZ      state_4_path    ; 60 4D - state 4
        ADD     A, #0FCH        ; 24 FC - check for state 8
        JZ      compare_sigs_80 ; 60 10 - state 8
        ADD     A, #03H         ; 24 03 - check for state 5
        JZ      state_2_path    ; 60 03
        LJMP    boot_dispatch   ; 02 01 04

state_2_path:
        ; At 0x005F: Set state 2
        MOV     DPTR, #0001H    ; 90 00 01
        MOV     A, #02H         ; 74 02
        MOVX    @DPTR, A        ; F0
        LJMP    boot_dispatch   ; 02 01 04

compare_sigs_80:
        ; At 0x0068: Compare IDATA signatures byte-by-byte
        MOV     R1, #06BH       ; 79 6B - transfer sig
        MOV     A, @R1          ; E7
        MOV     R0, #009H       ; 78 09 - boot sig
        XRL     A, @R0          ; 66 - compare byte 0
        JNZ     sig_mismatch_80 ; 70 15
        INC     R1              ; 09
        MOV     A, @R1          ; E7
        INC     R0              ; 08
        XRL     A, @R0          ; 66
        JNZ     sig_mismatch_80 ; 70 0F
        INC     R1              ; 09
        MOV     A, @R1          ; E7
        INC     R0              ; 08
        XRL     A, @R0          ; 66
        JNZ     sig_mismatch_80 ; 70 09
        INC     R1              ; 09
        MOV     A, @R1          ; E7
        INC     R0              ; 08
        XRL     A, @R0          ; 66
        JNZ     sig_mismatch_80 ; 70 03
        LJMP    boot_dispatch   ; 02 01 04 - sigs match

sig_mismatch_80:
        ; At 0x0085: Signatures don't match - compare with borrow
        LCALL   01B7EH          ; 12 1B 7E - load_both_signatures
        SETB    C               ; D3 - set carry (>= compare)
        LCALL   00D22H          ; 12 0D 22 - cmp32
        JC      state_3_not     ; 40 08 - if carry, skip state 3
        MOV     DPTR, #0001H    ; 90 00 01
        MOV     A, #03H         ; 74 03
        MOVX    @DPTR, A        ; F0
        SJMP    cont_comp_80    ; 80 6E - continue to boot_dispatch

state_3_not:
        LCALL   01B7EH          ; 12 1B 7E
        CLR     C               ; C3 - clear carry (> compare)
        LCALL   00D22H          ; 12 0D 22
        JNC     boot_dispatch   ; 50 65 - if no carry, dispatch
        SJMP    state_4_path    ; 80 00 - fall through (will be sjmp $+2)

state_4_path:
        ; At 0x00A1: Set state 4
        MOV     DPTR, #0001H    ; 90 00 01
        MOV     A, #04H         ; 74 04
        MOVX    @DPTR, A        ; F0
        SJMP    boot_dispatch   ; 80 5B

mode_not_80:
        ; At 0x00A9: Boot mode != 0x80
        MOV     R0, #06AH       ; 78 6A
        MOV     A, @R0          ; E6
        DEC     A               ; 14
        JZ      compare_alt     ; 60 19 - state 1
        DEC     A               ; 14
        JZ      compare_mode_other ; 60 18 - state 2
        DEC     A               ; 14
        JZ      compare_alt     ; 60 13 - state 3
        DEC     A               ; 14
        JZ      compare_mode_other ; 60 12 - state 4
        ADD     A, #0FCH        ; 24 FC
        JZ      compare_alt     ; 60 0C
        ADD     A, #03H         ; 24 03
        JNZ     boot_disp_near  ; 70 44
        ; State 5: set state 5
        MOV     DPTR, #0001H    ; 90 00 01
        MOV     A, #05H         ; 74 05
        MOVX    @DPTR, A        ; F0
        SJMP    boot_disp_near  ; 80 3C

compare_alt:
compare_mode_other:
        ; At 0x00CA: Compare IDATA signatures (alternate path)
        MOV     R1, #06BH       ; 79 6B
        MOV     A, @R1          ; E7
        MOV     R0, #009H       ; 78 09
        XRL     A, @R0          ; 66
        JNZ     sig_mismatch_alt ; 70 12
        INC     R1              ; 09
        MOV     A, @R1          ; E7
        INC     R0              ; 08
        XRL     A, @R0          ; 66
        JNZ     sig_mismatch_alt ; 70 0C
        INC     R1              ; 09
        MOV     A, @R1          ; E7
        INC     R0              ; 08
        XRL     A, @R0          ; 66
        JNZ     sig_mismatch_alt ; 70 06
        INC     R1              ; 09
        MOV     A, @R1          ; E7
        INC     R0              ; 08
        XRL     A, @R0          ; 66
        JZ      boot_disp_near  ; 60 20 - sigs match

sig_mismatch_alt:
        ; At 0x00E5: Compare with 32-bit comparison
        LCALL   01B7EH          ; 12 1B 7E
        SETB    C               ; D3
        LCALL   00D22H          ; 12 0D 22
        JC      state_7_not     ; 40 08
        MOV     DPTR, #0001H    ; 90 00 01
        MOV     A, #07H         ; 74 07
        MOVX    @DPTR, A        ; F0
        SJMP    boot_disp_near  ; 80 0F

state_7_not:
        LCALL   01B7EH          ; 12 1B 7E
        CLR     C               ; C3
        LCALL   00D22H          ; 12 0D 22
        JNC     boot_disp_near  ; 50 06
        MOV     DPTR, #0001H    ; 90 00 01
        MOV     A, #06H         ; 74 06
        MOVX    @DPTR, A        ; F0

boot_disp_near:
cont_comp_80:
        ; Fall through to boot_dispatch at 0x0104

;--------------------------------------------------------------------
; 0x0104: boot_dispatch - Entry point after startup verification
;--------------------------------------------------------------------
        CSEG    AT 0104H
boot_dispatch:
        MOV     DPTR, #0001H    ; 90 00 01
        MOVX    A, @DPTR        ; E0
        ; Continue with table dispatch
        RET                     ; 22 - placeholder

        END
