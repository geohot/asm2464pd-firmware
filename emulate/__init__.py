"""
ASM2464PD Firmware Emulator Package

This package provides 8051 emulation for the ASM2464PD USB4/Thunderbolt
NVMe bridge controller firmware.

Modules:
    cpu.py - 8051 CPU core emulator
    memory.py - Memory subsystem (CODE, XDATA, IDATA, SFR)
    peripherals.py - MMIO peripheral emulators
    emu.py - Main emulator driver

Usage:
    python -m emulate.emu fw.bin [options]
"""

from .cpu import CPU8051
from .memory import Memory, MemoryMap
from .peripherals import Peripherals
from .emu import Emulator

__all__ = ['CPU8051', 'Memory', 'MemoryMap', 'Peripherals', 'Emulator']
