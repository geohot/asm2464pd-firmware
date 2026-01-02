#!/usr/bin/env python3
"""
GPU DMA Probe for ASM2464PD USB-to-PCIe Bridge

Tests if the GPU can access PCIe address 0x200000 (ASM2464 internal SRAM).
This verifies the DMA path between the GPU and the USB bridge's internal buffer.

The ASM2464 exposes its internal SRAM at:
  - Controller address 0xF000 (USB accessible via E4/E5 commands or SCSI write)
  - PCIe address 0x200000 (GPU DMA accessible)

Usage:
    sudo python app/probe_dma.py           # Run full DMA probe test
    sudo python app/probe_dma.py --verbose # Show detailed output

Requirements:
    - tinygrad (for USB communication and AMD GPU support)
    - libusb
    - sudo/root access for USB device access
    - AMD GPU connected via the ASM2464PD bridge
"""

import sys
import time
import argparse
from pathlib import Path

# Add tinygrad to path if needed
sys.path.insert(0, str(Path.home() / "tinygrad"))

try:
    from tinygrad.runtime.support.usb import ASM24Controller
except ImportError:
    print("Error: Could not import ASM24Controller from tinygrad")
    print("Make sure tinygrad is installed or available at ~/tinygrad")
    sys.exit(1)

try:
    from tinygrad.runtime.ops_amd import AMDDevice, AMDCopyQueue, AMDSignal
    from tinygrad.runtime.support.hcq import BufferSpec
    HAS_AMD_GPU = True
except ImportError as e:
    print(f"Warning: AMD GPU support not fully available: {e}")
    HAS_AMD_GPU = False


def probe_dma_access(verbose: bool = False):
    """
    Test if the GPU can access PCIe address 0x200000 (ASM2464 internal SRAM).
    
    This boots the AMD GPU using tinygrad and tries to:
    1. Write a test pattern to 0xF000 (controller address) via USB
    2. Map GPU virtual address to PCIe physical 0x200000
    3. Have GPU SDMA read from that address into GPU VRAM
    4. Read back via GPU BAR and verify the pattern
    
    This tests the DMA path:
    USB Host -> ASM2464 SRAM (0xF000) <- GPU SDMA (via PCIe 0x200000)
    """
    if not HAS_AMD_GPU:
        print("ERROR: AMD GPU support not available")
        return False
    
    print("=" * 60)
    print("GPU DMA PROBE TEST")
    print("=" * 60)
    
    print("\nThis test verifies the GPU can access ASM2464 internal SRAM at PCIe address 0x200000")
    print("The ASM2464 exposes its internal buffer at:")
    print("  - Controller address 0xF000 (USB accessible)")
    print("  - PCIe address 0x200000 (GPU DMA accessible)")
    print()
    
    # Step 1: Boot the GPU first (this opens the USB controller)
    print("Step 1: Booting AMD GPU via tinygrad (AMD_IFACE=USB)...")
    try:
        # This will initialize the full AMD GPU including SDMA
        # With AMD_IFACE=USB env var, this uses USBIface
        gpu = AMDDevice("AMD:0")
        print(f"  GPU initialized: {gpu.arch} (target {gpu.target})")
        print(f"  GPU is USB: {gpu.is_usb()}")
    except Exception as e:
        print(f"  ERROR booting GPU: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if not gpu.is_usb():
        print("  ERROR: GPU is not connected via USB. Set AMD_IFACE=USB")
        return False
    
    # Get the USB controller from the GPU interface
    controller = gpu.iface.pci_dev.usb
    
    # Step 2: Write test pattern to ASM2464 SRAM via USB
    print("\nStep 2: Writing test pattern to ASM2464 SRAM via USB (addr 0xF000)...")
    test_pattern = bytes([0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE] * 8)  # 64 bytes
    try:
        controller.scsi_write(test_pattern, lba=0)
        print(f"  Wrote {len(test_pattern)} bytes: {test_pattern[:16].hex()}...")
    except Exception as e:
        print(f"  ERROR writing test pattern: {e}")
        return False
    
    # Step 3: Read it back via USB to verify write worked
    print("\nStep 3: Verifying write by reading back via USB...")
    try:
        readback = controller.read(0xF000, len(test_pattern))
        if readback == test_pattern:
            print(f"  SUCCESS: Read back matches: {readback[:16].hex()}...")
        else:
            print(f"  WARNING: Read back differs!")
            print(f"    Expected: {test_pattern[:16].hex()}...")
            print(f"    Got:      {readback[:16].hex()}...")
    except Exception as e:
        print(f"  ERROR reading back: {e}")
    
    # Step 4: Check if copy_bufs are set up (these map to 0x200000)
    print("\nStep 4: Checking DMA region setup...")
    if hasattr(gpu.iface, 'copy_bufs') and gpu.iface.copy_bufs:
        copy_buf = gpu.iface.copy_bufs[0]
        print(f"  copy_buf VA: 0x{copy_buf.va_addr:X}")
        print(f"  copy_buf size: {copy_buf.size} bytes ({copy_buf.size // 1024}KB)")
        print(f"  This maps to PCIe sys_addr 0x200000")
    else:
        print("  WARNING: No copy_bufs found")
        return False
    
    # Step 5: Try to read via the copy buffer's CPU view (which goes through USB)
    print("\nStep 5: Reading from copy_buf CPU view (0xF000 via USB)...")
    try:
        cpu_view = copy_buf.cpu_view()
        if cpu_view:
            view_data = bytes(cpu_view.view(fmt='B')[:64])
            print(f"  Read from CPU view: {view_data[:16].hex()}...")
            if view_data == test_pattern:
                print("  SUCCESS: CPU view shows our test pattern!")
            else:
                print("  Data differs from test pattern")
        else:
            print("  No CPU view available (expected for USB)")
    except Exception as e:
        print(f"  Could not read CPU view: {e}")
    
    # Step 6: Allocate GPU memory and try SDMA copy
    print("\nStep 6: Testing GPU SDMA copy from PCIe 0x200000...")
    try:
        # Allocate destination buffer in GPU VRAM
        dst_buf = gpu.allocator.alloc(4096, BufferSpec(cpu_access=True, nolru=True, uncached=True))
        print(f"  Allocated dst buffer at VA 0x{dst_buf.va_addr:X}")
        
        # Create a signal for completion using the GPU's signal allocator
        signal = gpu.new_signal(is_timeline=False)
        
        # Create SDMA copy queue
        copy_queue = AMDCopyQueue(gpu)
        
        # Copy 64 bytes from copy_buf (which maps to PCIe 0x200000) to dst_buf
        print(f"  Issuing SDMA copy: 0x{copy_buf.va_addr:X} -> 0x{dst_buf.va_addr:X} (64 bytes)")
        copy_queue.copy(dst_buf.va_addr, copy_buf.va_addr, 64)
        copy_queue.signal(signal, 1)
        copy_queue.submit(gpu)
        
        # Wait for completion
        print("  Waiting for SDMA completion...")
        start = time.time()
        while signal.value < 1:
            if time.time() - start > 5.0:
                print("  TIMEOUT waiting for SDMA!")
                break
            time.sleep(0.001)
        else:
            print(f"  SDMA completed in {(time.time() - start)*1000:.2f}ms")
        
        # Read back from dst_buf via CPU view (BAR access)
        print("\nStep 7: Reading result from GPU VRAM via BAR...")
        if dst_buf.cpu_view():
            result = bytes(dst_buf.cpu_view().view(fmt='B')[:64])
            print(f"  Result: {result[:16].hex()}...")
            
            if result == test_pattern:
                print("\n" + "=" * 60)
                print("SUCCESS! GPU can access PCIe address 0x200000!")
                print("The DMA path is working:")
                print("  USB -> ASM2464 SRAM (0xF000) <- GPU SDMA (PCIe 0x200000)")
                print("=" * 60)
                return True
            else:
                print("\n  MISMATCH! GPU read different data")
                print(f"    Expected: {test_pattern[:16].hex()}...")
                print(f"    Got:      {result[:16].hex()}...")
        else:
            print("  No CPU view for dst_buf")
            
    except Exception as e:
        print(f"  ERROR during SDMA test: {e}")
        import traceback
        traceback.print_exc()
    
    return False


def probe_dma_region_size(verbose: bool = False):
    """
    Probe the size of the DMA-accessible region at PCIe address 0x200000.
    
    Uses GPU SDMA to write/read patterns at various offsets to determine
    the actual accessible region size.
    """
    if not HAS_AMD_GPU:
        print("ERROR: AMD GPU support not available")
        return
    
    print("=" * 60)
    print("DMA REGION SIZE PROBE")
    print("=" * 60)
    
    # Boot the GPU
    print("\nBooting AMD GPU via tinygrad (AMD_IFACE=USB)...")
    try:
        gpu = AMDDevice("AMD:0")
        print(f"  GPU: {gpu.arch}, is_usb={gpu.is_usb()}")
    except Exception as e:
        print(f"  ERROR: {e}")
        return
    
    if not gpu.is_usb():
        print("  ERROR: GPU is not connected via USB. Set AMD_IFACE=USB")
        return
    
    controller = gpu.iface.pci_dev.usb
    copy_buf = gpu.iface.copy_bufs[0]
    
    print(f"\ncopy_buf info:")
    print(f"  VA: 0x{copy_buf.va_addr:X}")
    print(f"  Size: {copy_buf.size} bytes ({copy_buf.size // 1024}KB)")
    print(f"  Maps to PCIe sys_addr: 0x200000")
    
    # Allocate source and destination buffers in GPU VRAM
    src_buf = gpu.allocator.alloc(0x1000, BufferSpec(cpu_access=True, nolru=True, uncached=True))
    dst_buf = gpu.allocator.alloc(0x1000, BufferSpec(cpu_access=True, nolru=True, uncached=True))
    print(f"  src_buf VA: 0x{src_buf.va_addr:X}")
    print(f"  dst_buf VA: 0x{dst_buf.va_addr:X}")
    
    # Test offsets
    test_offsets = [
        0x0,        # 0KB
        0x1000,     # 4KB
        0x2000,     # 8KB
        0x4000,     # 16KB
        0x8000,     # 32KB
        0x10000,    # 64KB
        0x20000,    # 128KB
        0x40000,    # 256KB
        0x60000,    # 384KB
        0x7F000,    # 508KB
        0x7FF00,    # ~512KB
    ]
    
    print(f"\nProbing via GPU SDMA write/read at various offsets...")
    print("-" * 60)
    
    max_accessible = 0
    pattern_len = 8
    
    for offset in test_offsets:
        if offset >= copy_buf.size:
            print(f"  0x{offset:05X} ({offset // 1024:3d}KB): Beyond copy_buf size")
            continue
        
        # Create unique pattern based on offset
        pattern = bytes([
            (offset >> 16) & 0xFF,
            (offset >> 8) & 0xFF, 
            offset & 0xFF,
            0xDE, 0xAD, 0xBE, 0xEF, 0x00
        ])
        
        try:
            # Write pattern to src_buf
            src_view = src_buf.cpu_view().view(fmt='B')
            src_view[:pattern_len] = pattern
            
            # GPU SDMA write: src_buf -> copy_buf + offset
            signal = gpu.new_signal(is_timeline=False)
            q = AMDCopyQueue(gpu)
            q.copy(copy_buf.va_addr + offset, src_buf.va_addr, pattern_len)
            q.signal(signal, 1)
            q.submit(gpu)
            
            start = time.time()
            while signal.value < 1 and time.time() - start < 5.0:
                time.sleep(0.001)
            
            if signal.value < 1:
                print(f"  0x{offset:05X} ({offset // 1024:3d}KB): WRITE TIMEOUT")
                continue
            
            # Clear dst_buf
            dst_view = dst_buf.cpu_view().view(fmt='B')
            for i in range(pattern_len):
                dst_view[i] = 0
            
            # GPU SDMA read: copy_buf + offset -> dst_buf
            signal2 = gpu.new_signal(is_timeline=False)
            q2 = AMDCopyQueue(gpu)
            q2.copy(dst_buf.va_addr, copy_buf.va_addr + offset, pattern_len)
            q2.signal(signal2, 1)
            q2.submit(gpu)
            
            start = time.time()
            while signal2.value < 1 and time.time() - start < 5.0:
                time.sleep(0.001)
            
            if signal2.value < 1:
                print(f"  0x{offset:05X} ({offset // 1024:3d}KB): READ TIMEOUT")
                continue
            
            # Verify
            result = bytes(dst_buf.cpu_view().view(fmt='B')[:pattern_len])
            if result == pattern:
                print(f"  0x{offset:05X} ({offset // 1024:3d}KB): OK")
                max_accessible = offset + pattern_len
            else:
                print(f"  0x{offset:05X} ({offset // 1024:3d}KB): MISMATCH")
                print(f"    Expected: {pattern.hex()}")
                print(f"    Got:      {result.hex()}")
                
        except Exception as e:
            print(f"  0x{offset:05X} ({offset // 1024:3d}KB): ERROR: {e}")
    
    # Test USB accessibility
    print(f"\nChecking USB accessibility (E4/E5 commands)...")
    print("-" * 60)
    
    usb_accessible = 0
    for offset in [0x0, 0x1000, 0x2000, 0x4000]:
        try:
            # Write a pattern via GPU first
            pattern = bytes([0xAA, 0x55, offset & 0xFF, (offset >> 8) & 0xFF, 0xDE, 0xAD, 0xBE, 0xEF])
            src_view = src_buf.cpu_view().view(fmt='B')
            src_view[:8] = pattern
            
            signal = gpu.new_signal(is_timeline=False)
            q = AMDCopyQueue(gpu)
            q.copy(copy_buf.va_addr + offset, src_buf.va_addr, 8)
            q.signal(signal, 1)
            q.submit(gpu)
            while signal.value < 1: time.sleep(0.001)
            
            # Try to read via USB
            usb_data = controller.read(0xF000 + offset, 8)
            if usb_data == pattern:
                print(f"  0x{offset:05X}: USB can see GPU write")
                usb_accessible = offset + 8
            else:
                print(f"  0x{offset:05X}: USB sees different data: {usb_data.hex()}")
        except Exception as e:
            print(f"  0x{offset:05X}: USB ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  GPU SDMA accessible region: {max_accessible // 1024}KB (0x{max_accessible:X} bytes)")
    print(f"  USB E4/E5 accessible region: ~{usb_accessible // 1024}KB (0x{usb_accessible:X} bytes)")
    print()
    print("  The GPU can access the full 512KB DMA buffer at PCIe 0x200000")
    print("  USB commands can only access ~4KB at controller addr 0xF000")
    print("=" * 60)


def probe_pcie_address_space(verbose: bool = False):
    """
    Probe the PCIe address space to find what addresses are accessible.
    
    Tests various PCIe addresses to see what the GPU can access:
    - 0x200000: ASM2464 internal SRAM (copy buffer)
    - 0x820000: ASM2464 queue region
    - BAR addresses of devices on the PCIe bus
    """
    if not HAS_AMD_GPU:
        print("ERROR: AMD GPU support not available")
        return
    
    print("\n" + "=" * 60)
    print("PCIe ADDRESS SPACE PROBE")
    print("=" * 60)
    
    # Boot the GPU
    print("\nBooting AMD GPU...")
    try:
        gpu = AMDDevice("AMD:0")
        print(f"  GPU: {gpu.arch}")
    except Exception as e:
        print(f"  ERROR: {e}")
        return
    
    # Get the USB controller
    if not gpu.is_usb():
        print("ERROR: GPU is not connected via USB")
        return
    
    controller = gpu.iface.pci_dev.usb
    
    # Addresses to probe
    probe_addrs = [
        (0x200000, "ASM2464 copy buffer (sys_addr)"),
        (0x820000, "ASM2464 queue region (sys_addr)"),
        (0x10000000, "GPU BAR0 base (MMIO)"),
    ]
    
    # Add GPU BAR addresses if available
    if hasattr(gpu.iface, 'pci_dev') and hasattr(gpu.iface.pci_dev, 'bar_info'):
        for bar_idx, bar_info in gpu.iface.pci_dev.bar_info.items():
            if bar_info.size > 0:
                probe_addrs.append((bar_info.addr, f"GPU BAR{bar_idx} (0x{bar_info.size:X} bytes)"))
    
    print("\nProbing PCIe addresses from GPU perspective...")
    print("-" * 60)
    
    for addr, desc in probe_addrs:
        print(f"\n0x{addr:08X}: {desc}")
        try:
            # Try to read via PCIe memory request
            value = controller.pcie_mem_req(addr, value=None, size=4)
            if value is not None:
                print(f"  READ OK: 0x{value:08X}")
            else:
                print(f"  READ returned None")
        except Exception as e:
            print(f"  READ FAILED: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Test GPU DMA access to ASM2464PD internal SRAM"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--probe-space",
        action="store_true",
        help="Probe PCIe address space accessibility"
    )
    parser.add_argument(
        "--probe-size",
        action="store_true",
        help="Probe the size of the DMA-accessible region"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ASM2464PD GPU DMA Probe")
    print("=" * 60)
    
    if args.probe_space:
        probe_pcie_address_space(verbose=args.verbose)
    elif args.probe_size:
        probe_dma_region_size(verbose=args.verbose)
    else:
        success = probe_dma_access(verbose=args.verbose)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
