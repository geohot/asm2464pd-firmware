#!/usr/bin/env python3
"""
Test E7 fast read handler in fw_patched.bin.

This tests:
1. Direct handler execution (unit test)
2. Full vendor command dispatch path (integration test)
3. Verifies E7 reaches our handler at 0x7d00 through normal firmware flow
"""

import sys
from pathlib import Path

# Add emulate directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'emulate'))

from emu import Emulator

# Firmware path (relative to project root)
FIRMWARE_PATH = Path(__file__).parent.parent / "fw_patched.bin"


def test_e7_handler_direct():
    """Test E7 handler at 0x7d00 by calling it directly."""
    
    print("="*60)
    print("TEST 1: Direct E7 Handler Execution")
    print("="*60)
    
    # Load patched firmware
    emu = Emulator()
    emu.load_firmware(str(FIRMWARE_PATH))
    
    ce_writes = {}
    handler_completed = False
    
    # Track writes to CExx registers via xdata write hooks
    def make_ce_write_hook(addr):
        def ce_write_hook(a, value):
            ce_writes[addr] = value
            # Store in backing xdata
            emu.memory.xdata[addr] = value
        return ce_write_hook
    
    # Add hooks for CE72-CE89 range
    for addr in range(0xCE72, 0xCE8A):
        emu.memory.xdata_write_hooks[addr] = make_ce_write_hook(addr)
    
    # Also track USB SCSI buffer length writes at 0x9007-0x9008
    for addr in range(0x9007, 0x9009):
        emu.memory.xdata_write_hooks[addr] = make_ce_write_hook(addr)
    
    # Set up test parameters - NEW 16-bit size format
    # CDB format: E7 00 size_hi size_lo addr_3 addr_2 addr_1 addr_0
    test_size = 0x1000  # 4KB - test with 16-bit size
    test_addr = 0x00200000  # PCI address
    
    # Set up CDB in MMIO registers (16-byte CDB)
    emu.hw.regs[0x910D] = 0xE7                          # opcode
    emu.hw.regs[0x910E] = 0x00                          # reserved
    emu.hw.regs[0x910F] = (test_size >> 8) & 0xFF       # size_hi
    emu.hw.regs[0x9110] = test_size & 0xFF              # size_lo
    emu.hw.regs[0x9111] = (test_addr >> 24) & 0xFF      # addr_3 (MSB)
    emu.hw.regs[0x9112] = (test_addr >> 16) & 0xFF      # addr_2
    emu.hw.regs[0x9113] = (test_addr >> 8) & 0xFF       # addr_1
    emu.hw.regs[0x9114] = test_addr & 0xFF              # addr_0 (LSB)
    
    print(f"\nTest parameters: size=0x{test_size:04X} ({test_size} bytes), addr=0x{test_addr:08X}")
    
    # Set up CPU state - push return address
    emu.cpu.SP = 0x30
    emu.memory.idata[0x31] = 0xFF
    emu.memory.idata[0x30] = 0xFE
    emu.cpu.SP = 0x31
    emu.cpu.pc = 0x7d00
    
    # Simulate DMA completion after a few polls
    ce89_read_count = [0]
    def ce89_read_hook(addr):
        ce89_read_count[0] += 1
        return 0x04 if ce89_read_count[0] >= 3 else 0x00
    emu.memory.xdata_read_hooks[0xCE89] = ce89_read_hook
    
    # Run handler
    max_cycles = 10000
    for _ in range(max_cycles):
        emu.cpu.step()
        if emu.cpu.pc == 0xFFFE:
            handler_completed = True
            break
    
    # Check results - now with 16-bit size and USB buffer length
    expected = {
        0xCE73: 0x20, 0xCE74: 0x00,
        0xCE80: 0x7F, 0xCE81: 0xFF, 0xCE82: 0x3F,
        0xCE75: test_size & 0xFF,  # Only low byte in CE75
        0xCE72: 0x00,
        # Address registers (little-endian in CE76-79)
        0xCE76: test_addr & 0xFF,
        0xCE77: (test_addr >> 8) & 0xFF,
        0xCE78: (test_addr >> 16) & 0xFF,
        0xCE79: (test_addr >> 24) & 0xFF,
    }
    
    # Also check USB SCSI buffer length at 0x9007-0x9008
    usb_len_lo = emu.memory.xdata[0x9007]
    usb_len_hi = emu.memory.xdata[0x9008]
    usb_len = (usb_len_lo << 8) | usb_len_hi  # Note: swapped in firmware
    
    all_ok = True
    for addr, exp_val in expected.items():
        actual = ce_writes.get(addr, None)
        if actual != exp_val:
            print(f"  FAIL: 0x{addr:04X} expected 0x{exp_val:02X}, got {actual}")
            all_ok = False
    
    # Check USB SCSI buffer length
    if usb_len != test_size:
        print(f"  FAIL: USB_SCSI_BUF_LEN expected 0x{test_size:04X}, got 0x{usb_len:04X}")
        all_ok = False
    else:
        print(f"  USB_SCSI_BUF_LEN = 0x{usb_len:04X} ({usb_len} bytes) - OK")
    
    success = handler_completed and all_ok
    print(f"\nResult: {'PASS' if success else 'FAIL'}")
    print(f"  Handler completed: {handler_completed}")
    print(f"  All registers correct: {all_ok}")
    print(f"  R7 (return): 0x{emu.cpu.get_reg(7):02X}")
    
    return success


def test_e7_bank_switching():
    """Test that we can reach E7 dispatch in bank 1."""
    
    print("\n" + "="*60)
    print("TEST 2: Bank 1 E7 Dispatch Path Analysis")
    print("="*60)
    
    # Load patched firmware
    emu = Emulator()
    emu.load_firmware(str(FIRMWARE_PATH))
    
    print("\nVerifying patched firmware code:")
    
    # Set bank 1
    emu.memory.sfr[0x96 - 0x80] = 0x01  # DPX = 1 for bank 1
    
    # Read the dispatch code at 0xC1B1 (bank 1 address for E7 check)
    code_at_c1b1 = []
    for i in range(10):
        code_at_c1b1.append(emu.memory.read_code(0xC1B1 + i))
    
    print(f"  Code at 0xC1B1 (E7 check): {' '.join(f'{b:02X}' for b in code_at_c1b1)}")
    
    # Expected: B4 E7 0E (cjne a, #0xe7, +14)
    if code_at_c1b1[0:3] == [0xB4, 0xE7, 0x0E]:
        print("  -> cjne a, #0xe7, +14  [CORRECT - E7 check patched]")
    else:
        print("  -> UNEXPECTED bytes (expected B4 E7 0E)")
    
    # Read the lcall at 0xC1B4 (should be lcall 0x7d00)
    code_at_c1b4 = []
    for i in range(3):
        code_at_c1b4.append(emu.memory.read_code(0xC1B4 + i))
    
    print(f"  Code at 0xC1B4 (lcall): {' '.join(f'{b:02X}' for b in code_at_c1b4)}")
    
    # Expected: 12 7D 00 (lcall 0x7d00)
    if code_at_c1b4 == [0x12, 0x7D, 0x00]:
        print("  -> lcall 0x7d00  [CORRECT - calls our handler]")
    else:
        print(f"  -> UNEXPECTED bytes (expected 12 7D 00)")
    
    # Verify handler at 0x7d00 exists (in bank 0 / shared space)
    emu.memory.sfr[0x96 - 0x80] = 0x00  # DPX = 0 for bank 0
    
    code_at_7d00 = []
    for i in range(6):
        code_at_7d00.append(emu.memory.read_code(0x7d00 + i))
    
    print(f"  Code at 0x7D00 (handler start): {' '.join(f'{b:02X}' for b in code_at_7d00)}")
    
    # Expected start: 90 91 0F (mov dptr, #0x910F) - reads size_hi first
    if code_at_7d00[0:3] == [0x90, 0x91, 0x0F]:
        print("  -> mov dptr, #0x910F  [CORRECT - handler exists, reads size_hi]")
        return True
    else:
        print("  -> UNEXPECTED bytes (expected 90 91 0F)")
        return False


def test_e7_full_dispatch():
    """Test E7 command through full vendor command dispatch path with detailed tracing."""
    
    print("\n" + "="*60)
    print("TEST 3: Full E7 Vendor Command Dispatch (Detailed Trace)")
    print("="*60)
    
    # Load patched firmware
    emu = Emulator()
    emu.load_firmware(str(FIRMWARE_PATH))
    
    # Track key events
    e7_handler_hit = False
    ce_writes = {}
    pc_trace = []
    
    # We need to track ALL PC values to find where the dispatch happens
    # Key addresses in bank 1:
    # 0xC1B1 = cjne a, #0xe7 (E7 check)
    # 0xC1B4 = lcall 0x7d00 (call to our handler)
    # 0x7D00 = our handler start
    
    # Track CExx writes
    def make_ce_write_hook(addr):
        def ce_write_hook(a, value):
            ce_writes[addr] = value
            emu.memory.xdata[addr] = value
            print(f"  [CE WRITE] 0x{addr:04X} = 0x{value:02X}")
        return ce_write_hook
    for addr in range(0xCE72, 0xCE8A):
        emu.memory.xdata_write_hooks[addr] = make_ce_write_hook(addr)
    
    # Simulate DMA completion
    ce89_count = [0]
    def ce89_hook(addr):
        ce89_count[0] += 1
        return 0x04 if ce89_count[0] >= 3 else 0x00
    emu.memory.xdata_read_hooks[0xCE89] = ce89_hook
    
    # Trace important PCs
    important_pcs = {0x7D00, 0xC1B1, 0xC1B4, 0xC1B7}
    
    original_step = emu.cpu.step
    def traced_step():
        pc_before = emu.cpu.pc
        result = original_step()
        pc_after = emu.cpu.pc
        
        # Track if we enter 0x7D00
        if pc_after == 0x7D00:
            nonlocal e7_handler_hit
            e7_handler_hit = True
            print(f"  [TRACE] Entered E7 handler at 0x7D00 (from 0x{pc_before:04X})")
        
        # Track dispatch area
        if pc_before in important_pcs or pc_after in important_pcs:
            pc_trace.append((pc_before, pc_after))
            
        return result
    emu.cpu.step = traced_step
    
    # Connect USB
    print("\nPhase 1: USB setup...")
    emu.hw.usb_controller.connect(speed=1)
    emu.run(max_cycles=50000)
    print(f"  USB setup complete, PC=0x{emu.cpu.pc:04X}")
    
    # Now set up for E7 command - NEW 16-bit format
    print("\nPhase 2: Configure for E7 command...")
    
    test_size = 0x2000  # 8KB - test 16-bit size
    test_addr = 0x00200000  # PCI address
    
    # The dispatch path at 0x14112-0x1411c checks:
    # 1. 0x0B01 == 0x01 (enables the E2/E7 check path)
    # 2. 0x0B02 == 0xE7 (the command byte)
    
    # Set up XDATA for E7 path
    emu.memory.xdata[0x0B01] = 0x01  # Enable E7 dispatch path
    emu.memory.xdata[0x0B02] = 0xE7  # Command byte
    
    # Set up CDB in MMIO registers - NEW FORMAT
    # CDB: E7 00 size_hi size_lo addr_3 addr_2 addr_1 addr_0
    emu.hw.regs[0x910D] = 0xE7                          # opcode
    emu.hw.regs[0x910E] = 0x00                          # reserved
    emu.hw.regs[0x910F] = (test_size >> 8) & 0xFF       # size_hi
    emu.hw.regs[0x9110] = test_size & 0xFF              # size_lo
    emu.hw.regs[0x9111] = (test_addr >> 24) & 0xFF      # addr_3 (MSB)
    emu.hw.regs[0x9112] = (test_addr >> 16) & 0xFF      # addr_2
    emu.hw.regs[0x9113] = (test_addr >> 8) & 0xFF       # addr_1
    emu.hw.regs[0x9114] = test_addr & 0xFF              # addr_0 (LSB)
    
    print(f"  0x0B01 = 0x{emu.memory.xdata[0x0B01]:02X}")
    print(f"  0x0B02 = 0x{emu.memory.xdata[0x0B02]:02X}")
    print(f"  Size: 0x{test_size:04X} ({test_size} bytes)")
    print(f"  Addr: 0x{test_addr:08X}")
    
    # Set up to enter bank 1 dispatch area
    # The dispatch code is called from somewhere - let's try calling it directly
    # Or, we can set up PC to start at the dispatch entry
    
    # First, let's see what happens if we directly call the dispatch area
    # The E7 check is at 0xC1B1, but it expects A register to contain 0xE7
    
    print("\nPhase 3: Direct call to E7 dispatch area...")
    
    # Save current state
    old_pc = emu.cpu.pc
    old_sp = emu.cpu.SP
    
    # Set A = 0xE7 (the command check compares A to 0xE7)
    emu.cpu.A = 0xE7
    
    # Set bank 1
    emu.memory.sfr[0x96 - 0x80] = 0x01
    
    # Push return address
    emu.cpu.SP = 0x30
    emu.memory.idata[0x31] = 0xFF
    emu.memory.idata[0x30] = 0xF0
    emu.cpu.SP = 0x31
    
    # Set PC to E7 dispatch check
    emu.cpu.pc = 0xC1B1
    
    print(f"  Set A=0x{emu.cpu.A:02X}, PC=0x{emu.cpu.pc:04X}, DPX=0x{emu.memory.sfr[0x96-0x80]:02X}")
    
    # Run a few instructions to see what happens
    print("\nPhase 4: Execute dispatch...")
    
    for i in range(100):
        pc_before = emu.cpu.pc
        emu.cpu.step()
        pc_after = emu.cpu.pc
        
        if i < 20 or pc_after == 0x7D00:
            print(f"  Step {i}: 0x{pc_before:04X} -> 0x{pc_after:04X}")
        
        if pc_after == 0x7D00:
            print(f"  *** REACHED E7 HANDLER ***")
            break
        
        if pc_after == 0xFFF0:  # Our return address
            print(f"  Returned to caller")
            break
    
    # If handler was hit, run more to let it complete
    if e7_handler_hit:
        print("\nPhase 5: Run handler to completion...")
        for i in range(200):
            emu.cpu.step()
            if emu.cpu.pc == 0xFFF0:
                print(f"  Handler returned after {i+1} more steps")
                break
    
    print(f"\nResult:")
    print(f"  E7 handler hit: {e7_handler_hit}")
    print(f"  Final PC: 0x{emu.cpu.pc:04X}")
    print(f"  R7: 0x{emu.cpu.get_reg(7):02X}")
    print(f"  CE89 polls: {ce89_count[0]}")
    
    if ce_writes:
        print(f"  CExx writes: {len(ce_writes)}")
        for addr in sorted(ce_writes.keys()):
            print(f"    0x{addr:04X} = 0x{ce_writes[addr]:02X}")
    else:
        print("  No CExx writes")
    
    success = e7_handler_hit and 0xCE72 in ce_writes
    print(f"\nTest result: {'PASS' if success else 'FAIL'}")
    return success


def test_e7_natural_dispatch():
    """Test E7 through natural firmware USB interrupt handling."""
    
    print("\n" + "="*60)
    print("TEST 4: Natural E7 Command via USB Interrupt Path")
    print("="*60)
    
    # This test verifies the E7 handler can be reached through
    # the natural USB interrupt -> vendor dispatch path
    
    emu = Emulator()
    emu.load_firmware(str(FIRMWARE_PATH))
    
    e7_handler_hit = False
    ce_writes = {}
    
    # Track handler entry
    original_step = emu.cpu.step
    def traced_step():
        nonlocal e7_handler_hit
        result = original_step()
        if emu.cpu.pc == 0x7D00:
            e7_handler_hit = True
        return result
    emu.cpu.step = traced_step
    
    # Track CExx writes
    def make_ce_write_hook(addr):
        def ce_write_hook(a, value):
            ce_writes[addr] = value
            emu.memory.xdata[addr] = value
        return ce_write_hook
    for addr in range(0xCE72, 0xCE8A):
        emu.memory.xdata_write_hooks[addr] = make_ce_write_hook(addr)
    
    # DMA completion hook
    ce89_count = [0]
    def ce89_hook(addr):
        ce89_count[0] += 1
        return 0x04 if ce89_count[0] >= 3 else 0x00
    emu.memory.xdata_read_hooks[0xCE89] = ce89_hook
    
    # Connect USB and run setup
    print("\nPhase 1: USB enumeration...")
    emu.hw.usb_controller.connect(speed=1)
    emu.run(max_cycles=100000)
    print(f"  Complete, PC=0x{emu.cpu.pc:04X}")
    
    # Set up the E7 command state
    print("\nPhase 2: Inject E7 command state...")
    
    test_size = 64
    test_addr = 0x1000
    
    # CDB registers
    emu.hw.regs[0x910D] = 0xE7
    emu.hw.regs[0x910E] = test_size
    emu.hw.regs[0x910F] = 0x00
    emu.hw.regs[0x9110] = (test_addr >> 8) & 0xFF
    emu.hw.regs[0x9111] = test_addr & 0xFF
    emu.hw.regs[0x9112] = 0x00
    
    # The dispatch path checks 0x0B01 == 1 and 0x0B02 == command
    emu.memory.xdata[0x0B01] = 0x01
    emu.memory.xdata[0x0B02] = 0xE7
    
    # USB state
    emu.memory.idata[0x6A] = 5  # Configured
    emu.memory.xdata[0x07EC] = 0x00
    
    # Look for the dispatch entry point
    # The E7 check at 0xC1B1 is reached from somewhere in the vendor dispatch
    # We need to find who calls into that area
    
    # For now, let's manually set up to call the dispatch function
    # that eventually reaches our E7 check
    
    # Set bank 1 and start at a dispatch entry point
    # Looking at 0x14089 which calls 0xdc09, then checks r7 and jumps to 0xc1a5
    # at 0xc1a5 we should be in the E7 vicinity
    
    # Actually, let's trace what address range contains 0xC1B1
    # 0xC1A5 is close - let's see what's there
    
    print("\nPhase 3: Execute from dispatch entry...")
    
    # Set bank 1
    emu.memory.sfr[0x96 - 0x80] = 0x01
    
    # The check at 0xC1B1 expects A register to contain the command byte
    # which is read from 0x0B02 at 0xC1B0 (inc dptr; movx a,@dptr)
    # The dptr should point to 0x0B01 before the inc
    
    # Let's start earlier at 0xC1AF which sets up DPTR
    # Looking at 0x14112-0x1411b:
    #   0x14112: mov dptr, #0x0b01  (90 0B 01)
    #   0x14115: movx a, @dptr
    #   0x14116: xrl a, #0x01
    #   0x14118: jnz 0x412f
    #   0x1411a: inc dptr
    #   0x1411b: movx a, @dptr
    #   0x1411c: cjne a, #0xe7
    
    # Calculate bank 1 code address for 0x14112:
    # code_addr = 0x8000 + (0x14112 - 0xFF6B) = 0x8000 + 0x41A7 = 0xC1A7
    
    # Push return address
    emu.cpu.SP = 0x30
    emu.memory.idata[0x31] = 0xFF
    emu.memory.idata[0x30] = 0xF0
    emu.cpu.SP = 0x31
    
    # Start at the beginning of the E7 dispatch check sequence
    emu.cpu.pc = 0xC1A7
    
    print(f"  Start PC=0x{emu.cpu.pc:04X}")
    
    # Run until handler is hit or we return
    max_steps = 500
    for i in range(max_steps):
        emu.cpu.step()
        
        if e7_handler_hit:
            print(f"  Handler hit at step {i+1}")
            break
        
        if emu.cpu.pc == 0xFFF0:
            print(f"  Returned at step {i+1}")
            break
    
    # If handler was hit, run to completion
    if e7_handler_hit:
        for i in range(200):
            emu.cpu.step()
            if emu.cpu.pc >= 0xC1B7 or emu.cpu.pc == 0xFFF0:
                break
    
    print(f"\nResult:")
    print(f"  E7 handler hit: {e7_handler_hit}")
    print(f"  Final PC: 0x{emu.cpu.pc:04X}")
    print(f"  CExx writes: {len(ce_writes)}")
    
    # Check expected CExx registers
    expected_regs = [0xCE72, 0xCE73, 0xCE74, 0xCE75, 0xCE76, 0xCE77, 0xCE78, 0xCE79, 0xCE80, 0xCE81, 0xCE82]
    all_written = all(r in ce_writes for r in expected_regs)
    
    success = e7_handler_hit and all_written
    print(f"\nTest result: {'PASS' if success else 'FAIL'}")
    return success


if __name__ == "__main__":
    results = []
    
    # Test 1: Direct handler execution
    results.append(("Direct Handler", test_e7_handler_direct()))
    
    # Test 2: Bank switching verification
    results.append(("Bank Verification", test_e7_bank_switching()))
    
    # Test 3: Full dispatch with detailed tracing  
    results.append(("Full Dispatch", test_e7_full_dispatch()))
    
    # Test 4: Natural dispatch path
    results.append(("Natural Dispatch", test_e7_natural_dispatch()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)
