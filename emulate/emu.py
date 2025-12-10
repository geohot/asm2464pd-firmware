#!/usr/bin/env python3
"""
ASM2464PD Firmware Emulator

Main entry point for emulating the ASM2464PD firmware.
Loads fw.bin and executes it with full peripheral emulation.

Usage:
    python emulate/emu.py [fw.bin] [options]

Options:
    --trace         Enable instruction tracing
    --break ADDR    Set breakpoint at address (hex)
    --max-cycles N  Stop after N cycles
    --help          Show this help
"""

import sys
import os
import argparse
from pathlib import Path

# Add emulate directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cpu import CPU8051
from memory import Memory, MemoryMap
from peripherals import Peripherals
from hardware import HardwareState, create_hardware_hooks


class Emulator:
    """ASM2464PD Firmware Emulator."""

    def __init__(self, trace: bool = False, log_hw: bool = False):
        self.memory = Memory()
        self.cpu = CPU8051(
            read_code=self.memory.read_code,
            read_xdata=self.memory.read_xdata,
            write_xdata=self.memory.write_xdata,
            read_idata=self.memory.read_idata,
            write_idata=self.memory.write_idata,
            read_sfr=self.memory.read_sfr,
            write_sfr=self.memory.write_sfr,
            read_bit=self.memory.read_bit,
            write_bit=self.memory.write_bit,
            trace=trace,
        )

        # Hardware emulation (replaces simple stubs)
        self.hw = HardwareState(log_reads=log_hw, log_writes=log_hw)
        create_hardware_hooks(self.memory, self.hw)

        # Statistics
        self.inst_count = 0
        self.last_pc = 0

    def load_firmware(self, path: str):
        """Load firmware binary."""
        with open(path, 'rb') as f:
            data = f.read()
        print(f"Loaded {len(data)} bytes from {path}")
        self.memory.load_firmware(data)

    def reset(self):
        """Reset emulator to initial state."""
        self.memory.reset()
        self.cpu.reset()
        self.inst_count = 0

        # Initialize SP to default
        self.memory.write_sfr(0x81, 0x07)

    def step(self) -> bool:
        """Execute one instruction. Returns False if halted."""
        if self.cpu.halted:
            return False

        self.last_pc = self.cpu.pc

        if self.cpu.trace:
            self._trace_instruction()

        cycles = self.cpu.step()
        self.inst_count += 1
        self.hw.tick(cycles)

        return not self.cpu.halted

    def run(self, max_cycles: int = None, max_instructions: int = None) -> str:
        """
        Run emulator until halt, breakpoint, or limit reached.

        Returns reason for stopping.
        """
        while True:
            if max_cycles and self.cpu.cycles >= max_cycles:
                return "max_cycles"
            if max_instructions and self.inst_count >= max_instructions:
                return "max_instructions"

            if not self.step():
                if self.cpu.pc in self.cpu.breakpoints:
                    return "breakpoint"
                return "halted"

    def _trace_instruction(self):
        """Print trace of current instruction."""
        pc = self.cpu.pc
        bank = self.memory.read_sfr(0x96) & 1
        opcode = self.memory.read_code(pc)

        # Get instruction bytes
        inst_bytes = [opcode]
        inst_len = self._get_inst_length(opcode)
        for i in range(1, inst_len):
            inst_bytes.append(self.memory.read_code((pc + i) & 0xFFFF))

        # Format instruction
        hex_bytes = ' '.join(f'{b:02X}' for b in inst_bytes)
        mnemonic = self._disassemble(inst_bytes)

        # CPU state
        a = self.cpu.A
        psw = self.cpu.PSW
        sp = self.cpu.SP
        dptr = self.cpu.DPTR

        print(f"[{bank}] {pc:04X}: {hex_bytes:12s} {mnemonic:20s} "
              f"A={a:02X} PSW={psw:02X} SP={sp:02X} DPTR={dptr:04X}")

    def _get_inst_length(self, opcode: int) -> int:
        """Get instruction length in bytes."""
        # 1-byte instructions
        if opcode in (0x00, 0x03, 0x04, 0x06, 0x07, 0x13, 0x14, 0x16, 0x17,
                      0x22, 0x23, 0x32, 0x33, 0x73, 0x83, 0x84, 0x93, 0xA3,
                      0xA4, 0xA5, 0xC3, 0xC4, 0xD3, 0xD4, 0xE4, 0xE6, 0xE7,
                      0xF6, 0xF7) or (0x08 <= opcode <= 0x0F) or \
           (0x18 <= opcode <= 0x1F) or (0x28 <= opcode <= 0x2F) or \
           (0x38 <= opcode <= 0x3F) or (0x48 <= opcode <= 0x4F) or \
           (0x58 <= opcode <= 0x5F) or (0x68 <= opcode <= 0x6F) or \
           (0xC6 <= opcode <= 0xCF) or (0xE0 == opcode) or (0xE2 <= opcode <= 0xE3) or \
           (0xE8 <= opcode <= 0xEF) or (0xF0 == opcode) or (0xF2 <= opcode <= 0xFF):
            return 1

        # 3-byte instructions
        if opcode in (0x02, 0x12, 0x43, 0x53, 0x63, 0x75, 0x85, 0x90) or \
           (0xB4 <= opcode <= 0xBF and opcode not in (0xB2, 0xB3)):
            return 3

        # All others are 2 bytes
        return 2

    def _disassemble(self, inst_bytes: list) -> str:
        """Simple disassembler for trace output."""
        opcode = inst_bytes[0]

        # Just show opcode name for now
        opcodes = {
            0x00: "NOP", 0x02: "LJMP", 0x03: "RR A", 0x04: "INC A",
            0x05: "INC dir", 0x06: "INC @R0", 0x07: "INC @R1",
            0x12: "LCALL", 0x13: "RRC A", 0x14: "DEC A",
            0x15: "DEC dir", 0x16: "DEC @R0", 0x17: "DEC @R1",
            0x22: "RET", 0x23: "RL A", 0x32: "RETI", 0x33: "RLC A",
            0x40: "JC", 0x50: "JNC", 0x60: "JZ", 0x70: "JNZ",
            0x73: "JMP @A+DPTR", 0x74: "MOV A,#",
            0x76: "MOV @R0,#", 0x77: "MOV @R1,#",
            0x80: "SJMP", 0x83: "MOVC A,@A+PC", 0x84: "DIV AB",
            0x90: "MOV DPTR,#", 0x93: "MOVC A,@A+DPTR",
            0xA3: "INC DPTR", 0xA4: "MUL AB",
            0xB3: "CPL C", 0xC3: "CLR C", 0xC4: "SWAP A",
            0xC5: "XCH A,dir", 0xC6: "XCH A,@R0", 0xC7: "XCH A,@R1",
            0xD3: "SETB C", 0xD4: "DA A", 0xD6: "XCHD @R0", 0xD7: "XCHD @R1",
            0xE0: "MOVX A,@DPTR", 0xE4: "CLR A",
            0xE6: "MOV A,@R0", 0xE7: "MOV A,@R1",
            0xF0: "MOVX @DPTR,A", 0xF6: "MOV @R0,A", 0xF7: "MOV @R1,A",
        }

        if opcode in opcodes:
            return opcodes[opcode]

        # AJMP/ACALL
        if opcode & 0x1F == 0x01:
            return f"AJMP {((opcode & 0xE0) << 3) | inst_bytes[1]:03X}"
        if opcode & 0x1F == 0x11:
            return f"ACALL {((opcode & 0xE0) << 3) | inst_bytes[1]:03X}"

        # Register operations
        if 0x08 <= opcode <= 0x0F:
            return f"INC R{opcode & 7}"
        if 0x18 <= opcode <= 0x1F:
            return f"DEC R{opcode & 7}"
        if 0x28 <= opcode <= 0x2F:
            return f"ADD A,R{opcode & 7}"
        if 0x38 <= opcode <= 0x3F:
            return f"ADDC A,R{opcode & 7}"
        if 0x48 <= opcode <= 0x4F:
            return f"ORL A,R{opcode & 7}"
        if 0x58 <= opcode <= 0x5F:
            return f"ANL A,R{opcode & 7}"
        if 0x68 <= opcode <= 0x6F:
            return f"XRL A,R{opcode & 7}"
        if 0x78 <= opcode <= 0x7F:
            return f"MOV R{opcode & 7},#{inst_bytes[1]:02X}"
        if 0x88 <= opcode <= 0x8F:
            return f"MOV {inst_bytes[1]:02X},R{opcode & 7}"
        if 0x98 <= opcode <= 0x9F:
            return f"SUBB A,R{opcode & 7}"
        if 0xA8 <= opcode <= 0xAF:
            return f"MOV R{opcode & 7},{inst_bytes[1]:02X}"
        if 0xB8 <= opcode <= 0xBF:
            return f"CJNE R{opcode & 7},#{inst_bytes[1]:02X},{inst_bytes[2]:02X}"
        if 0xC8 <= opcode <= 0xCF:
            return f"XCH A,R{opcode & 7}"
        if 0xD8 <= opcode <= 0xDF:
            return f"DJNZ R{opcode & 7},{inst_bytes[1]:02X}"
        if 0xE8 <= opcode <= 0xEF:
            return f"MOV A,R{opcode & 7}"
        if 0xF8 <= opcode <= 0xFF:
            return f"MOV R{opcode & 7},A"

        return f"??? ({opcode:02X})"

    def dump_state(self):
        """Print current CPU and memory state."""
        print("\n=== CPU State ===")
        print(f"PC: 0x{self.cpu.pc:04X}  Bank: {self.memory.read_sfr(0x96) & 1}")
        print(f"A:  0x{self.cpu.A:02X}  B: 0x{self.cpu.B:02X}")
        print(f"PSW: 0x{self.cpu.PSW:02X} (CY={int(self.cpu.CY)} AC={int(self.cpu.AC)} OV={int(self.cpu.OV)})")
        print(f"SP: 0x{self.cpu.SP:02X}  DPTR: 0x{self.cpu.DPTR:04X}")
        print(f"Cycles: {self.cpu.cycles}  Instructions: {self.inst_count}")

        # Register banks
        print("\nRegisters:")
        for bank in range(4):
            regs = [self.memory.read_idata(bank * 8 + i) for i in range(8)]
            print(f"  Bank {bank}: " + ' '.join(f'{r:02X}' for r in regs))

        # Stack
        sp = self.cpu.SP
        if sp > 0x07:
            print(f"\nStack (SP=0x{sp:02X}):")
            for i in range(min(8, sp - 0x07)):
                addr = sp - i
                print(f"  0x{addr:02X}: 0x{self.memory.read_idata(addr):02X}")


def main():
    parser = argparse.ArgumentParser(description='ASM2464PD Firmware Emulator')
    parser.add_argument('firmware', nargs='?', default='fw.bin',
                        help='Firmware binary to load (default: fw.bin)')
    parser.add_argument('--trace', '-t', action='store_true',
                        help='Enable instruction tracing')
    parser.add_argument('--break', '-b', dest='breakpoints', action='append',
                        default=[], help='Set breakpoint at address (hex)')
    parser.add_argument('--max-cycles', '-c', type=int, default=10000000,
                        help='Maximum cycles to run (default: 10M)')
    parser.add_argument('--max-inst', '-i', type=int, default=None,
                        help='Maximum instructions to run')
    parser.add_argument('--dump', '-d', action='store_true',
                        help='Dump state on exit')
    parser.add_argument('--log-hw', '-l', action='store_true',
                        help='Log hardware MMIO access')

    args = parser.parse_args()

    # Find firmware file
    fw_path = args.firmware
    if not os.path.exists(fw_path):
        # Try relative to script directory
        script_dir = Path(__file__).parent.parent
        fw_path = script_dir / args.firmware
        if not fw_path.exists():
            print(f"Error: Cannot find firmware file: {args.firmware}")
            sys.exit(1)

    # Create emulator
    emu = Emulator(trace=args.trace, log_hw=args.log_hw)

    # Load firmware
    emu.load_firmware(str(fw_path))

    # Set breakpoints
    for bp in args.breakpoints:
        addr = int(bp, 16)
        emu.cpu.breakpoints.add(addr)
        print(f"Breakpoint set at 0x{addr:04X}")

    # Reset and run
    emu.reset()
    print(f"Starting execution at PC=0x{emu.cpu.pc:04X}")
    print("-" * 60)

    try:
        reason = emu.run(max_cycles=args.max_cycles, max_instructions=args.max_inst)
        print("-" * 60)
        print(f"Stopped: {reason} at PC=0x{emu.cpu.pc:04X}")
    except KeyboardInterrupt:
        print("\n" + "-" * 60)
        print(f"Interrupted at PC=0x{emu.cpu.pc:04X}")
    except Exception as e:
        print(f"\nError at PC=0x{emu.cpu.pc:04X}: {e}")
        raise

    if args.dump:
        emu.dump_state()

    print(f"\nTotal: {emu.inst_count} instructions, {emu.cpu.cycles} cycles")


if __name__ == '__main__':
    main()
