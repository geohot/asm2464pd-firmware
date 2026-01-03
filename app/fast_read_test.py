#!/usr/bin/env python3
"""
Fast Read Test for ASM2464PD

Tests bypassing the E4 255-byte limit by directly configuring USB DMA registers.

Theory:
- E4 is slow because it processes 255 bytes at a time through firmware
- USB DMA hardware can transfer larger amounts
- If we set up DMA registers directly via E5 writes, we might get fast bulk IN

Registers discovered from firmware disassembly:
- 0xD802-0xD803: DMA source address (16-bit)
- 0x9007-0x9008: USB SCSI buffer length (16-bit)
- 0x9093: EP config 1 (write 0x08)
- 0x9094: EP config 2 (write 0x02)
- 0xD80C: Trigger (write 0x01)

Usage:
    sudo PYTHONPATH=~/tinygrad python app/fast_read_test.py
"""

import sys
import time
import struct
from pathlib import Path

sys.path.insert(0, str(Path.home() / "tinygrad"))

try:
    from tinygrad.runtime.support.usb import ASM24Controller
except ImportError:
    print("Error: Could not import ASM24Controller from tinygrad")
    sys.exit(1)


def test_e4_baseline(usb, addr=0x8000, size=255):
    """Baseline: Read using standard E4 command."""
    start = time.perf_counter()
    data = usb.read(addr, size)
    elapsed = time.perf_counter() - start
    return data, elapsed


def test_e4_large(usb, addr=0x8000, size=4096):
    """Baseline: Read large amount using multiple E4 commands."""
    start = time.perf_counter()
    data = usb.read(addr, size)
    elapsed = time.perf_counter() - start
    return data, elapsed


def attempt_fast_read_v1(usb, addr=0x8000, size=4096):
    """
    Attempt 1: Set DMA registers and trigger bulk IN.
    
    Based on firmware code at 0x0210-0x0267 and 0x5290-0x52A6.
    """
    print(f"\n[V1] Attempting fast read: addr=0x{addr:04X}, size={size}")
    
    try:
        # Step 1: Set source address in DMA registers
        print(f"  Setting source addr 0x{addr:04X} at 0xD802-0xD803...")
        usb.write(0xD802, bytes([addr & 0xFF]))
        usb.write(0xD803, bytes([(addr >> 8) & 0xFF]))
        
        # Step 2: Set length in USB SCSI buffer registers
        print(f"  Setting length {size} at 0x9007-0x9008...")
        usb.write(0x9007, bytes([size & 0xFF]))
        usb.write(0x9008, bytes([(size >> 8) & 0xFF]))
        
        # Step 3: Configure EP (from 0x529C-0x52A5)
        print("  Configuring EP: 0x9093=0x08, 0x9094=0x02...")
        usb.write(0x9093, bytes([0x08]))
        usb.write(0x9094, bytes([0x02]))
        
        # Step 4: Try trigger at 0xD80C
        print("  Triggering at 0xD80C=0x01...")
        usb.write(0xD80C, bytes([0x01]))
        
        # Step 5: Try to read from bulk IN
        # Note: This might not work - need to figure out proper bulk read
        print("  Attempting bulk read...")
        
        # Try reading back via E4 to see if data appeared at 0x8000
        time.sleep(0.01)  # Small delay
        verify = usb.read(0x8000, min(size, 64))
        print(f"  Verify read (first 64 bytes): {verify[:32].hex()}...")
        
        return verify, True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def attempt_fast_read_v2(usb, addr=0x8000, size=4096):
    """
    Attempt 2: Different register sequence based on 0x52A7-0x52CA.
    
    This path writes to 0x0203, 0x020D-0x020E, 0x07E2, then 0xD80C.
    """
    print(f"\n[V2] Attempting fast read variant 2: addr=0x{addr:04X}, size={size}")
    
    try:
        # From 0x52A7-0x52B9
        print("  Setting up control registers...")
        usb.write(0x0203, bytes([0x05]))  # Some control byte
        usb.write(0x020D, bytes([addr & 0xFF]))  # Addr low?
        usb.write(0x020E, bytes([(addr >> 8) & 0xFF]))  # Addr high?
        usb.write(0x07E2, bytes([0x01]))  # Trigger flag
        
        # From 0x52C1-0x52C7
        print("  Triggering at 0xD80C...")
        usb.write(0xD80C, bytes([0x01]))
        
        # Small delay
        time.sleep(0.01)
        
        # Verify
        verify = usb.read(0x8000, min(size, 64))
        print(f"  Verify read: {verify[:32].hex()}...")
        
        return verify, True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return None, False


def attempt_fast_read_v3(usb, src_addr=0xF000, size=4096):
    """
    Attempt 3: Try CE register path (SCSI DMA).
    
    Based on 0x3812-0x386D - the SCSI WRITE DMA setup.
    Maybe we can reverse it for reads?
    """
    print(f"\n[V3] Attempting SCSI DMA path: src=0x{src_addr:04X}, size={size}")
    
    try:
        # From 0x3812-0x382C - buffer control setup
        print("  Setting buffer control registers...")
        usb.write(0xCE73, bytes([0x20]))  # Buffer control 0
        usb.write(0xCE74, bytes([0x00]))  # Buffer control 1
        usb.write(0xCE81, bytes([0xFF]))  # Threshold high
        usb.write(0xCE80, bytes([0x7F]))  # Buffer control
        usb.write(0xCE82, bytes([0x3F]))  # Threshold
        
        # Set length at CE75
        print(f"  Setting length at 0xCE75...")
        usb.write(0xCE75, bytes([size & 0xFF]))
        
        # Set address at CE76-CE79
        print(f"  Setting address 0x{src_addr:04X} at 0xCE76-0xCE79...")
        usb.write(0xCE76, bytes([src_addr & 0xFF]))
        usb.write(0xCE77, bytes([(src_addr >> 8) & 0xFF]))
        usb.write(0xCE78, bytes([0x00]))  # High bytes
        usb.write(0xCE79, bytes([0x00]))
        
        # Try trigger at CE00
        print("  Triggering DMA at 0xCE00=0x03...")
        usb.write(0xCE00, bytes([0x03]))
        
        # Poll CE00 for completion
        print("  Polling for completion...")
        for i in range(100):
            status = usb.read(0xCE00, 1)[0]
            if status == 0:
                print(f"  DMA complete after {i} polls")
                break
            time.sleep(0.001)
        else:
            print("  DMA timeout!")
        
        # Check CE89 status
        state = usb.read(0xCE89, 1)[0]
        print(f"  CE89 state: 0x{state:02X}")
        
        # Try reading result from 0x8000
        verify = usb.read(0x8000, min(size, 64))
        print(f"  Data at 0x8000: {verify[:32].hex()}...")
        
        return verify, True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def attempt_fast_read_v4(usb, size=4096):
    """
    Attempt 4: PCIe DMA path (like E4 uses internally).
    
    E4 writes to B455, B2D5, B296 to trigger PCIe DMA.
    """
    print(f"\n[V4] Attempting PCIe DMA trigger: size={size}")
    
    try:
        # First, let's see current state
        b296 = usb.read(0xB296, 1)[0]
        b455 = usb.read(0xB455, 1)[0]
        print(f"  Initial: B296=0x{b296:02X}, B455=0x{b455:02X}")
        
        # From E4 handler 0x35E2-0x35F6:
        # Write 0x02 then 0x04 to B455
        # Write 0x01 to B2D5
        # Write 0x08 to B296 (trigger)
        
        print("  Setting up PCIe DMA...")
        usb.write(0xB455, bytes([0x02]))
        usb.write(0xB455, bytes([0x04]))
        usb.write(0xB2D5, bytes([0x01]))
        
        print("  Triggering at B296=0x08...")
        usb.write(0xB296, bytes([0x08]))
        
        # Poll B455 for bit 1 (from 0x366B-0x3673)
        print("  Polling B455 bit 1...")
        for i in range(100):
            status = usb.read(0xB455, 1)[0]
            if status & 0x02:
                print(f"  Complete after {i} polls, status=0x{status:02X}")
                break
            time.sleep(0.001)
        else:
            print(f"  Timeout, final status=0x{status:02X}")
        
        # Clear completion
        usb.write(0xB455, bytes([0x02]))
        
        # Check result at 0x8000
        verify = usb.read(0x8000, min(size, 64))
        print(f"  Data at 0x8000: {verify[:32].hex()}...")
        
        return verify, True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def attempt_fast_read_v5(usb, src_addr=0xF000, size=4096):
    """
    Attempt 5: SCSI DMA with CE00=0x01 (read mode).
    
    Key insight: CE00=0x03 is for writes, CE00=0x01 might be for reads!
    Based on firmware code at 0x2fed where CE00=0x01 is used.
    """
    print(f"\n[V5] SCSI DMA with CE00=0x01: src=0x{src_addr:04X}, size={size}")
    
    try:
        # First restore test pattern at source
        print("  Restoring test pattern at source...")
        test_pattern = bytes([(0xFF - i) & 0xFF for i in range(min(size, 256))])
        usb.write(src_addr, test_pattern)
        
        # Verify source has data
        verify_src = usb.read(src_addr, 32)
        print(f"  Source data: {verify_src.hex()}")
        
        # Clear destination
        usb.write(0x8000, bytes([0xAA] * 64))
        
        # Set source address for DMA
        print(f"  Setting DMA source address 0x{src_addr:04X}...")
        usb.write(0xCE76, bytes([src_addr & 0xFF]))
        usb.write(0xCE77, bytes([(src_addr >> 8) & 0xFF]))
        usb.write(0xCE78, bytes([0x00]))
        usb.write(0xCE79, bytes([0x00]))
        
        # Set DMA length
        usb.write(0xCE75, bytes([size & 0xFF]))
        
        # Configure buffer control (same as write path for now)
        usb.write(0xCE73, bytes([0x20]))
        usb.write(0xCE74, bytes([0x00]))
        
        # Trigger DMA with 0x01 (read mode?)
        print("  Triggering DMA with CE00=0x01...")
        usb.write(0xCE00, bytes([0x01]))
        
        # Small delay
        time.sleep(0.01)
        
        # Check state
        ce00 = usb.read(0xCE00, 1)[0]
        state = usb.read(0xCE89, 1)[0]
        print(f"  CE00=0x{ce00:02X}, CE89=0x{state:02X}")
        
        # Read result - try from 0x8000 (USB buffer)
        result = usb.read(0x8000, min(size, 64))
        print(f"  Data at 0x8000: {result[:32].hex()}...")
        
        # Compare with expected
        if result[:32] == test_pattern[:32]:
            print("  SUCCESS: Data matches!")
        elif result[:32] == bytes([0xAA] * 32):
            print("  No change - 0x01 didn't do a copy")
        else:
            print("  Different data - something happened")
        
        return result, True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def attempt_fast_read_v6(usb, size=4096):
    """
    Attempt 6: Try using the USB SCSI buffer length registers directly.
    
    Theory: Set up length at 0x9007-0x9008, then trigger bulk IN somehow.
    """
    print(f"\n[V6] Direct USB buffer setup: size={size}")
    
    try:
        # First write test data to USB buffer (0x8000)
        print("  Writing test pattern to 0x8000...")
        test_pattern = bytes([i & 0xFF for i in range(min(size, 256))])
        usb.write(0x8000, test_pattern)
        
        # Verify it's there
        verify = usb.read(0x8000, 32)
        print(f"  Verify: {verify.hex()}")
        
        # Now try to set up a bulk IN transfer
        print(f"  Setting USB SCSI buffer length to {size}...")
        usb.write(0x9007, bytes([size & 0xFF]))
        usb.write(0x9008, bytes([(size >> 8) & 0xFF]))
        
        # Read back to verify
        buf_len = usb.read(0x9007, 2)
        print(f"  Buffer length readback: 0x{int.from_bytes(buf_len, 'little'):04X}")
        
        # Try triggering the USB state machine
        print("  Setting USB DMA state...")
        usb.write(0xCE89, bytes([0x01]))  # Set ready bit
        
        # Check if anything happens
        time.sleep(0.01)
        state = usb.read(0xCE89, 1)[0]
        print(f"  CE89 after trigger: 0x{state:02X}")
        
        # Try reading from the device using a raw bulk transfer
        # This would require libusb access which we don't have directly
        # For now, just verify the state
        
        return None, True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def dump_registers(usb):
    """Dump relevant registers for debugging."""
    print("\n=== Register Dump ===")
    
    regs = [
        (0x9007, 2, "USB_SCSI_BUF_LEN"),
        (0x9093, 1, "USB_EP_CFG1"),
        (0x9094, 1, "USB_EP_CFG2"),
        (0xB296, 1, "PCIE_STATUS"),
        (0xB455, 1, "POWER_CTRL"),
        (0xB2D5, 1, "PCIE_CTRL"),
        (0xCE00, 1, "SCSI_DMA_CTRL"),
        (0xCE75, 1, "SCSI_BUF_LEN"),
        (0xCE89, 1, "USB_DMA_STATE"),
        (0xD800, 1, "USB_EP_BUF_CTRL"),
        (0xD802, 2, "USB_EP_BUF_ADDR"),
        (0xD805, 1, "USB_EP_BUF_LEN_LO"),
        (0xD807, 1, "USB_EP_BUF_LEN_HI"),
        (0xD80C, 1, "USB_EP_TRIGGER"),
    ]
    
    for addr, size, name in regs:
        try:
            data = usb.read(addr, size)
            if size == 1:
                print(f"  0x{addr:04X} {name}: 0x{data[0]:02X}")
            else:
                val = int.from_bytes(data, 'little')
                print(f"  0x{addr:04X} {name}: 0x{val:04X}")
        except Exception as e:
            print(f"  0x{addr:04X} {name}: ERROR {e}")


def benchmark_e4_reads(usb):
    """Benchmark E4 read performance at different sizes."""
    print("\n=== E4 Read Benchmark ===")
    
    sizes = [64, 128, 255, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]
    
    for size in sizes:
        # Warm up
        usb.read(0x8000, min(size, 255))
        
        # Time it
        start = time.perf_counter()
        iterations = max(1, 65536 // size)  # More iterations for small sizes
        for _ in range(iterations):
            data = usb.read(0x8000, size)
        elapsed = time.perf_counter() - start
        
        total_bytes = size * iterations
        throughput = total_bytes / elapsed / 1024  # KB/s
        per_read = elapsed / iterations * 1000  # ms
        
        print(f"  {size:5d} bytes: {per_read:6.2f}ms/read, {throughput:7.1f} KB/s")


def attempt_state_poke(usb, size=4096):
    """
    Careful exploration of state machine.
    
    Key finding: Writing to 0x9093 caused OVERFLOW - meaning data was sent!
    Let's explore what triggers data transfers.
    """
    print(f"\n[STATE POKE] Exploring what triggers bulk IN...")
    
    try:
        # Read current state
        print("  Current state:")
        print(f"    0x9000: 0x{usb.read(0x9000, 1)[0]:02X}")
        print(f"    0x9007-08: 0x{int.from_bytes(usb.read(0x9007, 2), 'little'):04X}")
        print(f"    0x9093: 0x{usb.read(0x9093, 1)[0]:02X}")
        print(f"    0x9094: 0x{usb.read(0x9094, 1)[0]:02X}")
        
        # Write 256 bytes of test data to 0x8000
        print("\n  Writing 256-byte test pattern to 0x8000...")
        test_pattern = bytes([i & 0xFF for i in range(256)])
        usb.write(0x8000, test_pattern)
        
        # Verify
        verify = usb.read(0x8000, 64)
        print(f"  First 64 bytes: {verify[:32].hex()}")
        
        # Try setting a larger length
        print(f"\n  Setting length to {size}...")
        # Write as 16-bit value - note: might be rejected
        usb.write(0x9007, bytes([size & 0xFF, (size >> 8) & 0xFF]))
        
        # Read back immediately
        len_val = int.from_bytes(usb.read(0x9007, 2), 'little')
        print(f"  Length readback: {len_val}")
        
        # DON'T write to 0x9093 yet - that triggered overflow before
        # Instead, let's see what other registers affect transfers
        
        print("\n  Reading more USB registers...")
        for addr in [0x9090, 0x9091, 0x9092, 0x9093, 0x9094, 0x9095, 0x9096]:
            val = usb.read(addr, 1)[0]
            print(f"    0x{addr:04X}: 0x{val:02X}")
        
        return verify, True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def attempt_scsi_response_poke(usb, size=512):
    """
    Explore the E4 command internal state.
    
    The E4 response must have internal state tracking the size to return.
    Let's find where that state lives.
    """
    print(f"\n[E4 INTERNALS] Exploring E4 state...")
    
    try:
        # Check vendor command state variables
        print("  Vendor command state variables:")
        vendor_regs = {
            0x0A80: "VENDOR_STATE",
            0x0A81: "CMD_TYPE",
            0x0A82: "CMD_SIZE",
            0x0AA0: "HANDLER_STATE",
            0x0AA1: "HANDLER_RESULT",
            0x05A3: "CMD_SLOT_IDX",
            0x05A5: "CMD_INDEX_SRC",
        }
        
        for addr, name in vendor_regs.items():
            val = usb.read(addr, 1)[0]
            print(f"    0x{addr:04X} {name}: 0x{val:02X}")
        
        # The command table at 0x05B1
        print("\n  Command table entry 0 (0x05B1):")
        entry = usb.read(0x05B1, 16)
        print(f"    {entry.hex()}")
        
        # USB CDB registers
        print("\n  USB CDB registers (0x910D-0x9112):")
        cdb = usb.read(0x910D, 6)
        print(f"    CDB: {cdb.hex()}")
        print(f"    Cmd=0x{cdb[0]:02X}, Size=0x{cdb[1]:02X}, Addr=0x{cdb[2]:02X}{cdb[3]:02X}{cdb[4]:02X}")
        
        return None, True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def investigate_9093(usb):
    """
    Deep investigation of 0x9093 register.
    
    From firmware disassembly at 0x0fa0-0x1046:
    - Bit 0: Calls 0x54b4 -> 0x3169, 0x320d (some cleanup?)
    - Bit 1: Writes 0x02 to clear, calls 0x32e4 (bulk data complete handler)
    - Bit 2: Calls 0x54b4
    - Bit 3: Calls 0x4d3e (state machine handler)
    
    Values written TO 0x9093:
    - 0x08 with 0x9094=0x02: Bulk transfer mode (at 0x529c)
    - 0x02 with 0x9094=0x10: Interrupt transfer mode (at 0x1cd5)
    - 0x04: Event handler default action (at 0x1009)
    - 0x02: Clear bit 1 after ISR (at 0x0fac)
    
    The OVERFLOW happened when we wrote 0x08 - which configures bulk mode!
    This suggests the hardware started sending whatever was in the EP buffer.
    """
    print("\n" + "=" * 60)
    print("INVESTIGATING 0x9093 (REG_USB_EP_CFG1)")
    print("=" * 60)
    
    try:
        # First, read all relevant state
        print("\n[1] Current register state:")
        regs = [
            (0x9000, "USB_CTRL"),
            (0x9004, "EP0_LEN_L"),
            (0x9005, "EP0_LEN_H"),
            (0x9007, "SCSI_BUF_LEN_L"),
            (0x9008, "SCSI_BUF_LEN_H"),
            (0x9090, "USB_REG_9090"),
            (0x9091, "USB_CTRL_PHASE"),
            (0x9092, "USB_DMA_TRIGGER"),
            (0x9093, "USB_EP_CFG1"),
            (0x9094, "USB_EP_CFG2"),
            (0x9095, "USB_REG_9095"),
            (0x9096, "USB_EP_READY"),
            (0x9100, "USB_LINK_STATUS"),
            (0x9101, "USB_PERIPH_STATUS"),
            (0xD80C, "USB_EP_TRIGGER"),
            (0xCE89, "USB_DMA_STATE"),
        ]
        
        for addr, name in regs:
            val = usb.read(addr, 1)[0]
            print(f"    0x{addr:04X} {name:20s}: 0x{val:02X} ({val:3d}) bin={val:08b}")
        
        # Read 0x9007-0x9008 as 16-bit
        scsi_len = int.from_bytes(usb.read(0x9007, 2), 'little')
        print(f"\n    0x9007-08 as 16-bit: {scsi_len} bytes")
        
        # Check USB buffer at 0x8000
        print("\n[2] USB buffer (0x8000) first 64 bytes:")
        buf = usb.read(0x8000, 64)
        print(f"    {buf[:32].hex()}")
        print(f"    {buf[32:64].hex()}")
        
        # Write a distinctive pattern to USB buffer
        print("\n[3] Writing test pattern to 0x8000...")
        pattern = bytes([0xDE, 0xAD, 0xBE, 0xEF] * 64)  # 256 bytes
        usb.write(0x8000, pattern)
        
        # Verify it's there
        verify = usb.read(0x8000, 32)
        print(f"    Verify: {verify.hex()}")
        
        # Now, explore what happens with different 0x9093 values
        # We need to be careful - writing wrong values can cause USB errors
        
        print("\n[4] Testing 0x9093 writes (carefully)...")
        
        # First, save current state
        orig_9093 = usb.read(0x9093, 1)[0]
        orig_9094 = usb.read(0x9094, 1)[0]
        print(f"    Original: 0x9093=0x{orig_9093:02X}, 0x9094=0x{orig_9094:02X}")
        
        # Try setting a specific length first
        test_len = 256
        print(f"\n[5] Setting SCSI buffer length to {test_len}...")
        usb.write(0x9007, bytes([test_len & 0xFF]))
        usb.write(0x9008, bytes([(test_len >> 8) & 0xFF]))
        
        # Read back
        new_len = int.from_bytes(usb.read(0x9007, 2), 'little')
        print(f"    Readback: {new_len} bytes")
        
        # Check 0x0203, 0x020D-0x020E, 0x07E2 (from 0x52a7)
        print("\n[6] Control registers (from 0x52a7):")
        ctrl_regs = [
            (0x0203, "CTRL_0203"),
            (0x020D, "CTRL_020D"),
            (0x020E, "CTRL_020E"),
            (0x07E2, "XFER_FLAG"),
        ]
        for addr, name in ctrl_regs:
            val = usb.read(addr, 1)[0]
            print(f"    0x{addr:04X} {name}: 0x{val:02X}")
        
        # The transfer sequence from firmware:
        # 1. Set length at 0x9007-0x9008
        # 2. Write 0x08 to 0x9093, 0x02 to 0x9094 (bulk mode)
        # 3. Write control byte to 0x0203
        # 4. Write addr to 0x020D-0x020E  
        # 5. Write 0x01 to 0x07E2 (transfer flag)
        # 6. If 0x9000 bit 0 clear, write 0x01 to 0xD80C (trigger)
        
        print("\n[7] Attempting controlled bulk IN trigger...")
        print("    WARNING: This may cause USB errors!")
        
        # Set up the transfer (but don't trigger yet)
        # Step 1: Length already set above
        
        # Step 2: DON'T write 0x08 to 0x9093 yet - that's what caused OVERFLOW
        # Instead, let's see what the OVERFLOW looked like
        
        # First, let's check if there's a pending transfer
        d80c = usb.read(0xD80C, 1)[0]
        print(f"    0xD80C (trigger): 0x{d80c:02X}")
        
        # Check 0xCE89 USB DMA state
        ce89 = usb.read(0xCE89, 1)[0]
        print(f"    0xCE89 (DMA state): 0x{ce89:02X} (ready={ce89&1}, success={ce89&2})")
        
        # The key insight: when we wrote 0x08 to 0x9093, the hardware
        # immediately started a bulk IN transfer with whatever length was set.
        # If the length was larger than what the host expected, we got OVERFLOW.
        
        # To use this for fast reads, we need:
        # 1. Set the data at 0x8000 (or wherever DMA sources from)
        # 2. Set the correct length at 0x9007-0x9008
        # 3. Have the host ready to receive
        # 4. Write 0x08 to 0x9093 to trigger
        
        # But we can't easily coordinate step 3 from Python...
        # Unless we use a SCSI command that expects a data-in phase!
        
        print("\n[8] Current theory:")
        print("    - 0x9093=0x08 triggers bulk IN with length from 0x9007-0x9008")
        print("    - Data comes from USB buffer (0x8000 region)")
        print("    - OVERFLOW = host not expecting data / wrong length")
        print("    - To exploit: need host-side SCSI READ that expects data")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scsi_read(usb):
    """
    Test if SCSI READ(16) command works.
    
    SCSI READ(16) opcode is 0x88.
    The firmware should support it for NVMe drives.
    If we can get it to read from the internal SRAM, we bypass E4 entirely!
    """
    print("\n" + "=" * 60)
    print("TESTING SCSI READ(16) COMMAND")
    print("=" * 60)
    
    # SCSI READ(16) CDB format:
    # Byte 0: 0x88 (opcode)
    # Byte 1: flags (0x00)
    # Bytes 2-9: LBA (big-endian 64-bit)
    # Bytes 10-13: Transfer length in sectors (big-endian 32-bit)
    # Byte 14: group number
    # Byte 15: control
    
    # For SRAM read, LBA maps to PCI address: 0x00200000 + (LBA * 512)
    # So LBA=0 reads from 0x00200000
    
    print("\n[1] First, write test data via E5 to SRAM (0x200000 = USB 0x8000)...")
    pattern = bytes([i & 0xFF for i in range(256)])
    usb.write(0x8000, pattern)
    verify = usb.read(0x8000, 32)
    print(f"    Written: {pattern[:32].hex()}")
    print(f"    Verify:  {verify.hex()}")
    
    print("\n[2] Checking if we can issue raw SCSI commands...")
    # The tinygrad ASM24Controller uses exec_ops for SCSI
    # We need to check if there's a way to issue arbitrary SCSI commands
    
    print("    Need to examine tinygrad usb.py for SCSI interface...")
    
    # For now, let's check what happens with the existing SCSI infrastructure
    # by looking at the device state after a normal E4 read
    
    print("\n[3] State after E4 read:")
    _ = usb.read(0x8000, 64)  # Normal E4 read
    
    for addr, name in [(0x9093, "EP_CFG1"), (0x9094, "EP_CFG2"), 
                       (0x9007, "BUF_LEN_L"), (0x9008, "BUF_LEN_H")]:
        val = usb.read(addr, 1)[0]
        print(f"    0x{addr:04X} {name}: 0x{val:02X}")
    
    return True


def main():
    print("=" * 60)
    print("ASM2464PD Fast Read Test")
    print("=" * 60)
    
    # Connect to device
    print("\nConnecting to ASM2464PD...")
    try:
        usb = ASM24Controller()
        print("  Connected!")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)
    
    # Run focused investigation
    investigate_9093(usb)
    
    # Test SCSI READ
    test_scsi_read(usb)
    
    print("\n" + "=" * 60)
    print("FINDINGS")
    print("=" * 60)
    print("""
0x9093 Register Analysis:
- Writing 0x08 to 0x9093 configures "bulk transfer mode"
- This caused OVERFLOW because USB hardware started sending data
- The data comes from USB buffer region (0x8000)
- Length is taken from 0x9007-0x9008

Transfer trigger sequence (from 0x5294-0x52ca):
1. Set length at 0x9007-0x9008 (16-bit, little-endian)
2. Write 0x08 to 0x9093, 0x02 to 0x9094 (bulk mode config)
3. Write control to 0x0203, address to 0x020D-0x020E
4. Write 0x01 to 0x07E2 (transfer flag)
5. If 0x9000 bit 0 clear, write 0x01 to 0xD80C (trigger)

Key insight: 
- The OVERFLOW proves bulk IN can be triggered externally
- We just need host-side coordination (SCSI READ or similar)
- Implementing ScsiReadOp in tinygrad could give 64KB reads
""")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
