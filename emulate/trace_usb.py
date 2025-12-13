#!/usr/bin/env python3
"""
Trace USB command processing path.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from cpu import CPU8051
from memory import Memory
from hardware import HardwareState, create_hardware_hooks

def main():
    # Create emulator components
    memory = Memory()
    hw = HardwareState(log_reads=False, log_writes=False, log_uart=True)
    hw.usb_connect_delay = 500000
    hw.usb_inject_delay = 100  # Inject shortly after connect

    cpu = CPU8051(
        read_code=memory.read_code,
        read_xdata=memory.read_xdata,
        write_xdata=memory.write_xdata,
        read_idata=memory.read_idata,
        write_idata=memory.write_idata,
        read_sfr=memory.read_sfr,
        write_sfr=memory.write_sfr,
        read_bit=memory.read_bit,
        write_bit=memory.write_bit,
        trace=False,
    )

    create_hardware_hooks(memory, hw)

    # Load firmware
    fw_path = Path(__file__).parent.parent / 'fw.bin'
    with open(fw_path, 'rb') as f:
        data = f.read()
    print(f"Loaded {len(data)} bytes from {fw_path}")
    memory.load_firmware(data)

    # Reset
    memory.reset()
    cpu.reset()
    memory.write_sfr(0x81, 0x07)  # SP

    print(f"Starting execution at PC=0x{cpu.pc:04X}")
    print("-" * 60)

    # Track key addresses
    int_handler_0e33 = 0x0E33
    usb_ep_loop_start = 0x180D
    usb_ep_loop_call = 0x116E  # Where usb_ep_loop(1) is called
    usb_ep_check_10ef = 0x10EF  # Decision point

    key_addrs = {
        0x0003: "IE0 vector",
        0x0E33: "INT handler (EX0/IE0)",
        0x0E5A: "INT USB path start",
        0x0E5E: "Check 0x9101 bit 5",
        0x10B8: "After JNB check",
        0x10E9: "Check 0xC802 bit 2",
        0x10EF: "After C802 check",
        0x10F3: "Check 0xC471 bit 0",
        0x10F9: "After C471 check",
        0x10FF: "Check 0xC520 bit 1",
        0x1106: "Call usb_ep_loop(1)",
        0x116E: "usb_ep_loop entry",
        0x180D: "usb_ep_loop_180d",
        0x18A0: "usb_ep_check",
    }

    # Run well past USB connect and inject
    max_cycles = 1200000
    connect_pc_trace = []
    inject_pc_trace = []
    in_int_handler = False

    while cpu.cycles < max_cycles:
        # Don't stop on halt - just track it
        if cpu.halted:
            print(f"[{hw.cycles:8d}] CPU halted at PC=0x{cpu.pc:04X}, resuming...")
            cpu.halted = False

        pc = cpu.pc

        # Track when we hit key addresses
        if pc in key_addrs:
            print(f"[{hw.cycles:8d}] PC=0x{pc:04X} -> {key_addrs[pc]}")

        # If we're at the interrupt handler, trace more
        if pc == int_handler_0e33:
            in_int_handler = True
            print(f"[{hw.cycles:8d}] === INTERRUPT HANDLER ENTERED ===")
            # Dump relevant registers
            print(f"    C802=0x{hw.regs.get(0xC802, 0):02X}")
            print(f"    C471=0x{hw.regs.get(0xC471, 0):02X}")
            print(f"    C520=0x{hw.regs.get(0xC520, 0):02X}")
            print(f"    9101=0x{hw.regs.get(0x9101, 0):02X}")
            print(f"    CA0D=0x{hw.regs.get(0xCA0D, 0):02X}")

        # Check what happens at the EP ID comparison at 0x18C4
        if pc == 0x18C4:
            # Check R6 and R7 values (IDATA 0x06/0x07 in bank 0)
            psw = memory.read_sfr(0xD0)  # PSW
            bank = (psw >> 3) & 0x03
            r2_addr = bank * 8 + 2
            r6_addr = bank * 8 + 6
            r7_addr = bank * 8 + 7
            r2_val = memory.read_idata(r2_addr)
            r6_val = memory.read_idata(r6_addr)
            r7_val = memory.read_idata(r7_addr)
            a_val = cpu.A
            print(f"[{hw.cycles:8d}] EP ID cmp1: A=0x{a_val:02X} vs R7=0x{r7_val:02X}")
            print(f"               R2=0x{r2_val:02X}, R6=0x{r6_val:02X}, R7=0x{r7_val:02X}")

        # Check second comparison at 0x18C8
        if pc == 0x18C8:
            psw = memory.read_sfr(0xD0)
            bank = (psw >> 3) & 0x03
            r6_addr = bank * 8 + 6
            r6_val = memory.read_idata(r6_addr)
            a_val = cpu.A
            print(f"[{hw.cycles:8d}] EP ID cmp2: A=0x{a_val:02X} vs R6=0x{r6_val:02X}")

        # Check if we reach command processing at 0x18CB
        if pc == 0x18CB:
            print(f"[{hw.cycles:8d}] *** EP ID MATCH - PROCESSING COMMAND ***")

        # Check at 0x18F6 - after reading from 0x9096
        if pc == 0x18F6:
            a_val = cpu.A
            reg_9096 = hw.regs.get(0x9096, 0)
            print(f"[{hw.cycles:8d}] Check 0x18F6: A=0x{a_val:02X} (from ~0x9096={reg_9096:02X}), jz if A==0")

        # Check at 0x1927 - after reading from 0x90A1
        if pc == 0x1927:
            a_val = cpu.A
            reg_90a1 = hw.regs.get(0x90A1, 0)
            print(f"[{hw.cycles:8d}] Check 0x1927: A=0x{a_val:02X} (from ~0x90A1={reg_90a1:02X}), jnb if bit0==0")

        # Check at 0x192A - the lcall 0x4e6a (command processing)
        if pc == 0x192A:
            print(f"[{hw.cycles:8d}] *** REACHED COMMAND HANDLER lcall 0x4E6A ***")

        # Trace when near USB connect (500000)
        if 499000 <= hw.cycles <= 502000:
            connect_pc_trace.append(pc)

        # Trace when near USB inject (1000000)
        if 999000 <= hw.cycles <= 1002000:
            inject_pc_trace.append(pc)

        cpu.step()
        hw.tick(1, cpu)

    print("-" * 60)
    print(f"Stopped at PC=0x{cpu.pc:04X} after {hw.cycles} cycles")

    # Show unique PCs around connect
    if connect_pc_trace:
        unique_pcs = []
        prev = None
        for pc in connect_pc_trace:
            if pc != prev:
                unique_pcs.append(pc)
                prev = pc
        print(f"\nPCs around USB connect ({len(unique_pcs)} unique):")
        for i, pc in enumerate(unique_pcs[:50]):
            name = key_addrs.get(pc, "")
            print(f"  {i}: 0x{pc:04X} {name}")

    # Show unique PCs around inject
    if inject_pc_trace:
        unique_pcs = []
        prev = None
        for pc in inject_pc_trace:
            if pc != prev:
                unique_pcs.append(pc)
                prev = pc
        print(f"\nPCs around USB inject ({len(unique_pcs)} unique):")
        for i, pc in enumerate(unique_pcs[:50]):
            name = key_addrs.get(pc, "")
            print(f"  {i}: 0x{pc:04X} {name}")

if __name__ == '__main__':
    main()
