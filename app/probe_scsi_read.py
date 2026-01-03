#!/usr/bin/env python3
"""
Probe SCSI READ(16) support in ASM2464PD.

This script tests whether the ASM2464PD firmware supports SCSI READ(16) commands
for reading from the internal SRAM buffer.

Theory:
- SCSI WRITE(16) opcode 0x8A works and writes to PCI addr 0x00200000 + (LBA * 512)
- SCSI READ(16) opcode 0x88 should read from the same address space
- The firmware disassembly shows 0x08 (READ(6)), 0x88 (READ(16)), 0x09 all go to same handler

Usage:
    sudo PYTHONPATH=~/tinygrad python app/probe_scsi_read.py
"""

import sys
import struct
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / "tinygrad"))

try:
    from tinygrad.runtime.support.usb import ASM24Controller, USB3
    from tinygrad.helpers import round_up
except ImportError as e:
    print(f"Error importing tinygrad: {e}")
    sys.exit(1)


def scsi_read_test(usb: ASM24Controller, lba: int = 0, sectors: int = 1) -> bytes | None:
    """
    Attempt a SCSI READ(16) command.
    
    SCSI READ(16) CDB format (10 bytes used):
    Byte 0:    0x88 (opcode)
    Byte 1:    Flags (0x00)
    Bytes 2-9: LBA (big-endian 64-bit)
    Bytes 10-13: Transfer length in sectors (big-endian 32-bit)
    Byte 14:   Group number (0)
    Byte 15:   Control (0)
    """
    size = sectors * 512
    cdb = struct.pack('>BBQIBB', 0x88, 0, lba, sectors, 0, 0)
    
    print(f"  Sending SCSI READ(16): LBA={lba}, sectors={sectors}, size={size}")
    print(f"  CDB: {cdb.hex()}")
    
    try:
        # Use the low-level USB interface to send the command
        # idata = expected read length, odata = data to send (None for read)
        results = usb.usb.send_batch([cdb], [size], [None])
        
        if results and results[0]:
            data = results[0]
            print(f"  SUCCESS! Got {len(data)} bytes")
            print(f"  First 64 bytes: {data[:64].hex()}")
            return data
        else:
            print(f"  No data returned: {results}")
            return None
            
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("=" * 60)
    print("SCSI READ(16) Probe for ASM2464PD")
    print("=" * 60)
    
    # Connect to device
    print("\nConnecting to ASM2464PD...")
    try:
        usb = ASM24Controller()
        print("  Connected!")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)
    
    # First, write a test pattern using SCSI WRITE
    print("\n[1] Writing test pattern via SCSI WRITE...")
    test_pattern = bytes([i & 0xFF for i in range(512)])  # 1 sector
    usb.scsi_write(test_pattern, lba=0)
    print(f"  Wrote {len(test_pattern)} bytes to LBA 0")
    
    # Verify via E4 read
    print("\n[2] Verifying via E4 read (0x8000 = PCI 0x200000)...")
    verify_e4 = usb.read(0x8000, 64)
    print(f"  E4 read: {verify_e4.hex()}")
    
    if verify_e4 == test_pattern[:64]:
        print("  MATCH: E4 read matches written pattern")
    else:
        print("  MISMATCH: E4 read doesn't match!")
    
    # Now try SCSI READ
    print("\n[3] Attempting SCSI READ(16)...")
    result = scsi_read_test(usb, lba=0, sectors=1)
    
    if result:
        if result[:64] == test_pattern[:64]:
            print("\n  *** SUCCESS: SCSI READ matches written pattern! ***")
        else:
            print("\n  Data received but doesn't match pattern")
            print(f"  Expected: {test_pattern[:32].hex()}")
            print(f"  Got:      {result[:32].hex()}")
    else:
        print("\n  SCSI READ failed or returned no data")
    
    # Try with a different pattern to make sure
    print("\n[4] Testing with a different pattern...")
    test_pattern2 = bytes([0xAA, 0x55] * 256)  # 512 bytes alternating
    usb.scsi_write(test_pattern2, lba=1)  # Write to LBA 1
    
    result2 = scsi_read_test(usb, lba=1, sectors=1)
    if result2:
        if result2[:64] == test_pattern2[:64]:
            print("\n  *** SUCCESS: Second SCSI READ also matches! ***")
        else:
            print("\n  Data doesn't match second pattern")
    
    # Try reading 2 sectors
    print("\n[5] Testing multi-sector read (2 sectors = 1024 bytes)...")
    result3 = scsi_read_test(usb, lba=0, sectors=2)
    if result3 and len(result3) >= 1024:
        print(f"  Got {len(result3)} bytes for 2-sector read")
        if result3[:64] == test_pattern[:64]:
            print("  First sector matches!")
        if result3[512:576] == test_pattern2[:64]:
            print("  Second sector matches!")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
