#!/usr/bin/env python3
"""
Patch ASM2464PD firmware to add E7 fast read command.

This patch:
1. Changes the E2 vendor command check to E7 at 0x1411c
2. Replaces the E2 handler call with a jump to our fast read handler
3. Adds the E7 fast read handler at 0x7d00 (free space in bank 0)

E7 CDB Format (16 bytes like SCSI):
  Byte 0: 0xE7 (opcode)
  Byte 1: Reserved (0)
  Byte 2-3: Size (big-endian, 16-bit, up to 64KB)
  Byte 4-7: PCI address (big-endian, 32-bit)
  Byte 8-15: Reserved (0)

The handler uses the fast CExx SCSI DMA engine AND sets up
the USB SCSI buffer length registers for large transfers.
"""

import sys
from pathlib import Path

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
ORIG_FW = PROJECT_ROOT / "fw.bin"
OUT_FW = PROJECT_ROOT / "fw_patched.bin"

# Patch locations
# File offset 0x1411c: cjne a, #0xe2 -> cjne a, #0xe7
PATCH_E7_CHECK = (0x1411c + 1, b'\xe2', b'\xe7')

# File offset 0x1411f: lcall 0xd96e -> lcall 0x7d00 (our handler)
PATCH_CALL_HANDLER = (0x1411f, b'\x12\xd9\x6e', b'\x12\x7d\x00')

# E7 Fast Read Handler at 0x7d00
# 
# CDB format at 0x910D-0x911C:
#   910D: 0xE7 (opcode)
#   910E: 0x00 (reserved)
#   910F: size_hi (big-endian)
#   9110: size_lo
#   9111: addr_3 (big-endian, MSB)
#   9112: addr_2
#   9113: addr_1
#   9114: addr_0 (LSB)
#
# Registers to set:
#   0x9007 = size_hi (USB SCSI buffer length low - yes, swapped)
#   0x9008 = size_lo (USB SCSI buffer length high)
#   0xCE73 = 0x20 (buffer control 0)
#   0xCE74 = 0x00 (buffer control 1)
#   0xCE75 = size_lo (transfer length low byte for DMA)
#   0xCE76 = addr_0 (PCI addr LSB)
#   0xCE77 = addr_1
#   0xCE78 = addr_2
#   0xCE79 = addr_3 (PCI addr MSB)
#   0xCE80 = 0x7F (buffer control)
#   0xCE81 = 0xFF (buffer threshold high)
#   0xCE82 = 0x3F (buffer threshold low)
#   0xCE72 = 0x00 (trigger DMA)
#   Poll 0xCE89 bit 2 for completion
#
# IDATA temp vars used:
#   0x28 = size_lo
#   0x29 = size_hi
#   0x2A = addr_0
#   0x2B = addr_1
#   0x2C = addr_2
#   0x2D = addr_3

E7_HANDLER = bytes([
    # Read 16-bit size from CDB[2:4] (0x910F-0x9110, big-endian)
    0x90, 0x91, 0x0F,  # mov dptr, #0x910F  ; size_hi
    0xE0,              # movx a, @dptr
    0xF5, 0x29,        # mov 0x29, a        ; save size_hi
    0xA3,              # inc dptr           ; 0x9110
    0xE0,              # movx a, @dptr
    0xF5, 0x28,        # mov 0x28, a        ; save size_lo
    
    # Read 32-bit address from CDB[4:8] (0x9111-0x9114, big-endian)
    0xA3,              # inc dptr           ; 0x9111 = addr_3 (MSB)
    0xE0,              # movx a, @dptr
    0xF5, 0x2D,        # mov 0x2D, a        ; save addr_3
    0xA3,              # inc dptr           ; 0x9112 = addr_2
    0xE0,              # movx a, @dptr
    0xF5, 0x2C,        # mov 0x2C, a        ; save addr_2
    0xA3,              # inc dptr           ; 0x9113 = addr_1
    0xE0,              # movx a, @dptr
    0xF5, 0x2B,        # mov 0x2B, a        ; save addr_1
    0xA3,              # inc dptr           ; 0x9114 = addr_0 (LSB)
    0xE0,              # movx a, @dptr
    0xF5, 0x2A,        # mov 0x2A, a        ; save addr_0
    
    # Set USB SCSI buffer length (0x9007-0x9008)
    # Note: The registers are swapped - L gets hi, H gets lo
    0x90, 0x90, 0x07,  # mov dptr, #0x9007  ; USB_SCSI_BUF_LEN_L
    0xE5, 0x29,        # mov a, 0x29        ; size_hi
    0xF0,              # movx @dptr, a
    0xA3,              # inc dptr           ; 0x9008 = USB_SCSI_BUF_LEN_H
    0xE5, 0x28,        # mov a, 0x28        ; size_lo
    0xF0,              # movx @dptr, a
    
    # Set up CE73 = 0x20 (buffer control 0)
    0x90, 0xCE, 0x73,  # mov dptr, #0xCE73
    0x74, 0x20,        # mov a, #0x20
    0xF0,              # movx @dptr, a
    
    # CE74 = 0x00 (buffer control 1)
    0xA3,              # inc dptr  ; 0xCE74
    0xE4,              # clr a
    0xF0,              # movx @dptr, a
    
    # CE75 = size_lo (transfer length for DMA - only low byte used here)
    0xA3,              # inc dptr  ; 0xCE75
    0xE5, 0x28,        # mov a, 0x28  ; size_lo
    0xF0,              # movx @dptr, a
    
    # CE76-CE79 = 32-bit PCI address (little-endian in registers)
    0xA3,              # inc dptr  ; 0xCE76 = addr_0 (LSB)
    0xE5, 0x2A,        # mov a, 0x2A
    0xF0,              # movx @dptr, a
    
    0xA3,              # inc dptr  ; 0xCE77 = addr_1
    0xE5, 0x2B,        # mov a, 0x2B
    0xF0,              # movx @dptr, a
    
    0xA3,              # inc dptr  ; 0xCE78 = addr_2
    0xE5, 0x2C,        # mov a, 0x2C
    0xF0,              # movx @dptr, a
    
    0xA3,              # inc dptr  ; 0xCE79 = addr_3 (MSB)
    0xE5, 0x2D,        # mov a, 0x2D
    0xF0,              # movx @dptr, a
    
    # CE80 = 0x7F (buffer control)
    0x90, 0xCE, 0x80,  # mov dptr, #0xCE80
    0x74, 0x7F,        # mov a, #0x7F
    0xF0,              # movx @dptr, a
    
    # CE81 = 0xFF (buffer threshold high)
    0xA3,              # inc dptr  ; 0xCE81
    0x74, 0xFF,        # mov a, #0xFF
    0xF0,              # movx @dptr, a
    
    # CE82 = 0x3F (buffer threshold low)
    0xA3,              # inc dptr  ; 0xCE82
    0x74, 0x3F,        # mov a, #0x3F
    0xF0,              # movx @dptr, a
    
    # CE72 = 0x00 to trigger DMA
    0x90, 0xCE, 0x72,  # mov dptr, #0xCE72
    0xE4,              # clr a
    0xF0,              # movx @dptr, a
    
    # Wait for DMA completion: poll CE89 bit 2 (complete)
    # wait_loop:
    0x90, 0xCE, 0x89,  # mov dptr, #0xCE89
    0xE0,              # movx a, @dptr
    0x30, 0xE2, 0xF9,  # jnb acc.2, wait_loop  ; loop until bit 2 set
    
    # Return success (r7 = 0xFF)
    0x7F, 0xFF,        # mov r7, #0xFF
    0x22,              # ret
])

# Handler location in file
E7_HANDLER_OFFSET = 0x7d00

def apply_patches(data):
    """Apply all patches to firmware data."""
    data = bytearray(data)
    
    # Patch 1: Change E2 check to E7
    offset, old, new = PATCH_E7_CHECK
    if data[offset:offset+len(old)] != old:
        print(f"WARNING: Patch 1 mismatch at 0x{offset:x}")
        print(f"  Expected: {old.hex()}")
        print(f"  Found:    {data[offset:offset+len(old)].hex()}")
    else:
        data[offset:offset+len(new)] = new
        print(f"Patch 1: Changed E2 to E7 at 0x{offset:x}")
    
    # Patch 2: Change call to flash read to our handler
    offset, old, new = PATCH_CALL_HANDLER
    if data[offset:offset+len(old)] != old:
        print(f"WARNING: Patch 2 mismatch at 0x{offset:x}")
        print(f"  Expected: {old.hex()}")
        print(f"  Found:    {data[offset:offset+len(old)].hex()}")
    else:
        data[offset:offset+len(new)] = new
        print(f"Patch 2: Changed lcall 0xd96e to lcall 0x7d00 at 0x{offset:x}")
    
    # Patch 3: Add E7 handler at 0x7d00
    # Verify space is free (should be zeros)
    if data[E7_HANDLER_OFFSET:E7_HANDLER_OFFSET+len(E7_HANDLER)] != bytes(len(E7_HANDLER)):
        print(f"WARNING: Handler space at 0x{E7_HANDLER_OFFSET:x} not empty")
        print(f"  Found: {data[E7_HANDLER_OFFSET:E7_HANDLER_OFFSET+16].hex()}")
    data[E7_HANDLER_OFFSET:E7_HANDLER_OFFSET+len(E7_HANDLER)] = E7_HANDLER
    print(f"Patch 3: Added E7 handler ({len(E7_HANDLER)} bytes) at 0x{E7_HANDLER_OFFSET:x}")
    
    return bytes(data)

def main():
    # Read original firmware
    with open(ORIG_FW, 'rb') as f:
        data = f.read()
    print(f"Read {len(data)} bytes from {ORIG_FW}")
    
    # Apply patches
    patched = apply_patches(data)
    
    # Write patched firmware
    with open(OUT_FW, 'wb') as f:
        f.write(patched)
    print(f"Wrote {len(patched)} bytes to {OUT_FW}")
    
    print("\nPatch complete! Use fw_patched.bin for testing.")
    print("\nE7 command format (16-byte CDB with 16-bit size):")
    print("  CDB[0]   = 0xE7 (opcode)")
    print("  CDB[1]   = 0x00 (reserved)")
    print("  CDB[2:4] = size (big-endian, 16-bit, up to 64KB)")
    print("  CDB[4:8] = PCI address (big-endian, 32-bit)")
    print("  CDB[8:16] = reserved (0)")

if __name__ == '__main__':
    main()
