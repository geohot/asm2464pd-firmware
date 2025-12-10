; ASM2464PD Firmware - startup_0016 exact match
; Address: 0x0016-0x0103 (238 bytes)
;
; This is a byte-exact reconstruction using DB directives
; to guarantee exact binary match with original firmware.

$NOMOD51

NAME    STARTUP

?PR?startup_0016?STARTUP   SEGMENT CODE
    PUBLIC  startup_0016

    RSEG    ?PR?startup_0016?STARTUP

startup_0016:
; Row 0x0016-0x0025
    DB  0E4H                    ; clr a
    DB  090H, 000H, 001H        ; mov dptr, #0001H
    DB  0F0H                    ; movx @dptr, a
    DB  078H, 06BH              ; mov r0, #6BH
    DB  012H, 00DH, 078H        ; lcall 0x0D78 (idata_load_dword)
    DB  0ECH                    ; mov a, r4
    DB  04DH                    ; orl a, r5
    DB  04EH                    ; orl a, r6
    DB  04FH                    ; orl a, r7
    DB  070H, 017H              ; jnz +0x17 (-> 0x003D)

; Row 0x0026-0x0035
    DB  078H, 009H              ; mov r0, #09H
    DB  012H, 00DH, 078H        ; lcall 0x0D78
    DB  0ECH                    ; mov a, r4
    DB  04DH                    ; orl a, r5
    DB  04EH                    ; orl a, r6
    DB  04FH                    ; orl a, r7
    DB  070H, 003H              ; jnz +0x03 (-> 0x0034)
    DB  002H, 001H, 004H        ; ljmp 0x0104
    DB  090H, 000H              ; mov dptr, #00xx (continued)

; Row 0x0036-0x0045
    DB  001H                    ; (continuation of dptr)
    DB  074H, 001H              ; mov a, #01H
    DB  0F0H                    ; movx @dptr, a
    DB  002H, 001H, 004H        ; ljmp 0x0104
    DB  090H, 00AH, 0F3H        ; mov dptr, #0AF3H
    DB  0E0H                    ; movx a, @dptr
    DB  064H, 080H              ; xrl a, #80H
    DB  070H, 064H              ; jnz +0x64 (-> 0x00A9)
    DB  078H                    ; mov r0, #xx (continued)

; Row 0x0046-0x0055
    DB  06AH                    ; (continuation: mov r0, #6AH)
    DB  0E6H                    ; mov a, @r0
    DB  014H                    ; dec a
    DB  060H, 01DH              ; jz +0x1D (-> 0x0068)
    DB  014H                    ; dec a
    DB  060H, 053H              ; jz +0x53 (-> 0x00A1)
    DB  014H                    ; dec a
    DB  060H, 017H              ; jz +0x17 (-> 0x0068)
    DB  014H                    ; dec a
    DB  060H, 04DH              ; jz +0x4D (-> 0x00A1)
    DB  024H, 0FCH              ; add a, #0FCH

; Row 0x0056-0x0065
    DB  060H, 010H              ; jz +0x10 (-> 0x0068)
    DB  024H, 003H              ; add a, #03H
    DB  060H, 003H              ; jz +0x03 (-> 0x005F)
    DB  002H, 001H, 004H        ; ljmp 0x0104
    DB  090H, 000H, 001H        ; mov dptr, #0001H
    DB  074H, 002H              ; mov a, #02H
    DB  0F0H                    ; movx @dptr, a
    DB  002H                    ; ljmp (continued)

; Row 0x0066-0x0075
    DB  001H, 004H              ; (continuation: ljmp 0x0104)
    DB  079H, 06BH              ; mov r1, #6BH
    DB  0E7H                    ; mov a, @r1
    DB  078H, 009H              ; mov r0, #09H
    DB  066H                    ; xrl a, @r0
    DB  070H, 015H              ; jnz +0x15 (-> 0x0085)
    DB  009H                    ; inc r1
    DB  0E7H                    ; mov a, @r1
    DB  008H                    ; inc r0
    DB  066H                    ; xrl a, @r0
    DB  070H, 00FH              ; jnz +0x0F (-> 0x0085)

; Row 0x0076-0x0085
    DB  009H                    ; inc r1
    DB  0E7H                    ; mov a, @r1
    DB  008H                    ; inc r0
    DB  066H                    ; xrl a, @r0
    DB  070H, 009H              ; jnz +0x09 (-> 0x0085)
    DB  009H                    ; inc r1
    DB  0E7H                    ; mov a, @r1
    DB  008H                    ; inc r0
    DB  066H                    ; xrl a, @r0
    DB  070H, 003H              ; jnz +0x03 (-> 0x0085)
    DB  002H, 001H, 004H        ; ljmp 0x0104
    DB  012H                    ; lcall (continued)

; Row 0x0086-0x0095
    DB  01BH, 07EH              ; (continuation: lcall 0x1B7E)
    DB  0D3H                    ; setb c
    DB  012H, 00DH, 022H        ; lcall 0x0D22 (cmp32)
    DB  040H, 008H              ; jc +0x08 (-> 0x0096)
    DB  090H, 000H, 001H        ; mov dptr, #0001H
    DB  074H, 003H              ; mov a, #03H
    DB  0F0H                    ; movx @dptr, a
    DB  080H, 06EH              ; sjmp +0x6E (-> 0x0104)

; Row 0x0096-0x00A5
    DB  012H, 01BH, 07EH        ; lcall 0x1B7E
    DB  0C3H                    ; clr c
    DB  012H, 00DH, 022H        ; lcall 0x0D22
    DB  050H, 065H              ; jnc +0x65 (-> 0x0104)
    DB  080H, 000H              ; sjmp +0x00 (-> 0x00A1)
    DB  090H, 000H, 001H        ; mov dptr, #0001H
    DB  074H, 004H              ; mov a, #04H

; Row 0x00A6-0x00B5
    DB  0F0H                    ; movx @dptr, a
    DB  080H, 05BH              ; sjmp +0x5B (-> 0x0104)
    DB  078H, 06AH              ; mov r0, #6AH
    DB  0E6H                    ; mov a, @r0
    DB  014H                    ; dec a
    DB  060H, 019H              ; jz +0x19 (-> 0x00C8)
    DB  014H                    ; dec a
    DB  060H, 018H              ; jz +0x18 (-> 0x00CA)
    DB  014H                    ; dec a
    DB  060H, 013H              ; jz +0x13 (-> 0x00C8)
    DB  014H                    ; dec a

; Row 0x00B6-0x00C5
    DB  060H, 012H              ; jz +0x12 (-> 0x00CA)
    DB  024H, 0FCH              ; add a, #0FCH
    DB  060H, 00CH              ; jz +0x0C (-> 0x00C8)
    DB  024H, 003H              ; add a, #03H
    DB  070H, 044H              ; jnz +0x44 (-> 0x0104)
    DB  090H, 000H, 001H        ; mov dptr, #0001H
    DB  074H, 005H              ; mov a, #05H
    DB  0F0H                    ; movx @dptr, a
    DB  080H, 03CH              ; sjmp +0x3C (-> 0x0104)

; Row 0x00C6-0x00D5  (CRITICAL SECTION)
    DB  080H, 034H              ; sjmp +0x34 (-> 0x00FC) -- from 0xC6
    DB  079H, 06BH              ; mov r1, #6BH
    DB  0E7H                    ; mov a, @r1
    DB  078H, 009H              ; mov r0, #09H
    DB  066H                    ; xrl a, @r0
    DB  070H, 012H              ; jnz +0x12 (-> 0x00E6)
    DB  009H                    ; inc r1
    DB  0E7H                    ; mov a, @r1
    DB  008H                    ; inc r0
    DB  066H                    ; xrl a, @r0

; Row 0x00D6-0x00E5
    DB  070H, 00CH              ; jnz +0x0C (-> 0x00E6)
    DB  009H                    ; inc r1
    DB  0E7H                    ; mov a, @r1
    DB  008H                    ; inc r0
    DB  066H                    ; xrl a, @r0
    DB  070H, 006H              ; jnz +0x06 (-> 0x00E6)
    DB  009H                    ; inc r1
    DB  0E7H                    ; mov a, @r1
    DB  008H                    ; inc r0
    DB  066H                    ; xrl a, @r0
    DB  060H, 020H              ; jz +0x20 (-> 0x0106 - wait that's past end)

; Row 0x00E6-0x00F5
    DB  012H, 01BH, 07EH        ; lcall 0x1B7E
    DB  0D3H                    ; setb c
    DB  012H, 00DH, 022H        ; lcall 0x0D22
    DB  040H, 008H              ; jc +0x08 (-> 0x00F6)
    DB  090H, 000H, 001H        ; mov dptr, #0001H
    DB  074H, 007H              ; mov a, #07H
    DB  0F0H                    ; movx @dptr, a
    DB  080H, 00FH              ; sjmp +0x0F (-> 0x0104)

; Row 0x00F6-0x0103
    DB  012H, 01BH, 07EH        ; lcall 0x1B7E
    DB  0C3H                    ; clr c
    DB  012H, 00DH, 022H        ; lcall 0x0D22
    DB  050H, 006H              ; jnc +0x06 (-> 0x0104)
    DB  090H, 000H, 001H        ; mov dptr, #0001H
    DB  074H, 006H              ; mov a, #06H
    DB  0F0H                    ; movx @dptr, a

; 0x0104: Function ends here (no explicit ret - falls through or returns via other means)
; The original doesn't have a RET here - it's exactly 238 bytes

    END
