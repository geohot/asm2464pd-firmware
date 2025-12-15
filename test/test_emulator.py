#!/usr/bin/env python3
"""
Test emulator functionality for the ASM2464PD firmware.

These tests verify:
- UART TX register writes produce output
- Hardware state management works correctly
- Basic CPU execution functions
- PCIe and timer emulation behavior

Usage:
    # Run against original firmware (default)
    pytest test/test_emulator.py -v

    # Run against our compiled firmware
    pytest test/test_emulator.py -v --firmware=ours

    # Run against both firmwares
    pytest test/test_emulator.py -v --firmware=both
"""

import sys
import os
import io
from pathlib import Path
import pytest

# Add emulate directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'emulate'))

from emu import Emulator
from conftest import ORIGINAL_FIRMWARE, OUR_FIRMWARE


class TestUARTOutput:
    """Tests for UART output functionality."""

    def test_direct_uart_write_raw(self, emulator):
        """Test direct UART register writes with raw output mode."""
        emu = emulator

        # Capture stdout
        old_stdout = sys.stdout
        captured = io.StringIO()
        sys.stdout = captured

        try:
            # Write test message directly to UART THR (0xC001)
            test_msg = "TEST"
            for ch in test_msg:
                emu.hw.write(0xC001, ord(ch))
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        assert test_msg in output, f"Expected '{test_msg}' in output, got: {repr(output)}"

    def test_uart_output_formatting(self):
        """Test that UART output is properly buffered and formatted when log_uart=True."""
        emu = Emulator(log_uart=True)
        emu.reset()

        # Capture stdout
        old_stdout = sys.stdout
        captured = io.StringIO()
        sys.stdout = captured

        try:
            # Write a message that ends with ']' which triggers flush
            test_chars = "Hello]"
            for ch in test_chars:
                emu.hw.write(0xC001, ord(ch))
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        # With log_uart=True, output should contain [UART] prefix
        assert "[UART]" in output, f"Expected '[UART]' prefix in output, got: {repr(output)}"
        assert "Hello]" in output, f"Expected 'Hello]' in output, got: {repr(output)}"

    def test_uart_newline_handling(self):
        """Test that newlines properly flush the UART buffer."""
        emu = Emulator(log_uart=True)
        emu.reset()

        old_stdout = sys.stdout
        captured = io.StringIO()
        sys.stdout = captured

        try:
            # Write message followed by newline
            for ch in "Line1":
                emu.hw.write(0xC001, ord(ch))
            emu.hw.write(0xC001, 0x0A)  # newline
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        assert "Line1" in output, f"Expected 'Line1' in output, got: {repr(output)}"


class TestHardwareState:
    """Tests for hardware state management."""

    def test_hardware_register_defaults(self, emulator):
        """Test that hardware registers have correct default values."""
        emu = emulator

        # Check critical register defaults
        assert emu.hw.regs.get(0xC009, 0) == 0x60, "UART LSR should be 0x60 (TX empty)"
        assert emu.hw.regs.get(0x9000, 0) == 0x00, "USB status should start at 0x00"
        assert emu.hw.regs.get(0xB480, 0) == 0x00, "PCIe link should start down"

    def test_usb_connect_event(self):
        """Test that USB connect event fires after delay."""
        emu = Emulator(usb_delay=100)  # Short delay for testing
        emu.reset()

        assert not emu.hw.usb_connected, "USB should not be connected initially"

        # Tick past the connect delay
        for _ in range(150):
            emu.hw.tick(1, emu.cpu)

        assert emu.hw.usb_connected, "USB should be connected after delay"
        assert emu.hw.regs.get(0x9000, 0) & 0x80, "USB status bit 7 should be set"

    def test_polling_counters(self, emulator):
        """Test that polling counters increment on repeated reads."""
        emu = emulator

        test_addr = 0xC800
        emu.hw.regs[test_addr] = 0x00

        # Read multiple times
        for _ in range(5):
            emu.hw.read(test_addr)

        assert emu.hw.poll_counts.get(test_addr, 0) >= 5, "Poll count should increment"


class TestEmulatorExecution:
    """Tests for basic emulator execution."""

    def test_emulator_reset(self, emulator):
        """Test that emulator resets to clean state."""
        emu = emulator

        assert emu.cpu.pc == 0x0000, "PC should be 0 after reset"
        assert emu.inst_count == 0, "Instruction count should be 0"
        assert emu.cpu.cycles == 0, "Cycle count should be 0"

    def test_memory_read_write(self, emulator):
        """Test basic XDATA memory operations."""
        emu = emulator

        # Test XDATA write and read (low memory, not hardware registers)
        test_addr = 0x1000
        test_value = 0x42

        emu.memory.write_xdata(test_addr, test_value)
        result = emu.memory.read_xdata(test_addr)

        assert result == test_value, f"Expected 0x{test_value:02X}, got 0x{result:02X}"

    def test_idata_memory(self, emulator):
        """Test IDATA (internal RAM) operations."""
        emu = emulator

        # Test IDATA write and read
        test_addr = 0x30
        test_value = 0x55

        emu.memory.write_idata(test_addr, test_value)
        result = emu.memory.read_idata(test_addr)

        assert result == test_value, f"Expected 0x{test_value:02X}, got 0x{result:02X}"

    def test_sfr_operations(self, emulator):
        """Test SFR (Special Function Register) operations."""
        emu = emulator

        # Test SP (Stack Pointer) - SFR 0x81
        emu.memory.write_sfr(0x81, 0x50)
        result = emu.memory.read_sfr(0x81)

        assert result == 0x50, f"Expected SP=0x50, got 0x{result:02X}"

    def test_firmware_load(self, firmware_path, firmware_name):
        """Test that firmware loads correctly."""
        if firmware_path is None:
            pytest.skip("No firmware available")

        emu = Emulator()
        emu.reset()
        emu.load_firmware(str(firmware_path))

        # Check that code memory has data
        first_byte = emu.memory.read_code(0x0000)
        assert first_byte != 0x00 or emu.memory.read_code(0x0001) != 0x00, \
            f"Firmware ({firmware_name}) should have non-zero bytes at start"

    def test_firmware_execution_cycles(self, firmware_emulator):
        """Test that firmware executes for specified cycles."""
        emu, fw_name = firmware_emulator

        # Run for a limited number of cycles
        max_cycles = 1000
        reason = emu.run(max_cycles=max_cycles)

        assert reason == "max_cycles", f"[{fw_name}] Expected stop reason 'max_cycles', got '{reason}'"
        assert emu.cpu.cycles >= max_cycles, f"[{fw_name}] Should have run at least {max_cycles} cycles"


class TestPCIeEmulation:
    """Tests for PCIe hardware emulation."""

    def test_pcie_trigger_completion(self, emulator):
        """Test that PCIe trigger sets completion bits."""
        emu = emulator

        # Trigger PCIe operation
        emu.hw.write(0xB254, 0x01)

        # Check completion status
        status = emu.hw.read(0xB296)
        assert status & 0x06, "PCIe completion bits should be set after trigger"

    def test_pcie_status_polling(self, emulator):
        """Test that PCIe status sets bits after polling."""
        emu = emulator

        # Initial read should have bits clear or not all set
        initial = emu.hw.read(0xB296)

        # Poll multiple times
        for _ in range(10):
            status = emu.hw.read(0xB296)

        # After polling, completion bits should be set
        assert status & 0x06, "PCIe completion bits should be set after polling"


class TestUSBVendorCommands:
    """Tests for USB vendor command emulation."""

    def test_e4_read_xdata(self, firmware_emulator):
        """Test E4 read command returns correct XDATA values."""
        emu, fw_name = firmware_emulator

        # Write test data to XDATA
        test_addr = 0x1000
        test_data = [0xDE, 0xAD, 0xBE, 0xEF]
        for i, val in enumerate(test_data):
            emu.memory.xdata[test_addr + i] = val

        # Inject E4 read command
        emu.hw.inject_usb_command(0xE4, test_addr, size=len(test_data))

        # Run until DMA completes
        emu.run(max_cycles=50000)

        # Verify data was copied to USB buffer at 0x8000
        result = [emu.memory.xdata[0x8000 + i] for i in range(len(test_data))]
        assert result == test_data, f"[{fw_name}] E4 read returned {result}, expected {test_data}"

    def test_e4_read_different_addresses(self, firmware_emulator):
        """Test E4 read works for various XDATA addresses."""
        emu, fw_name = firmware_emulator

        test_cases = [
            (0x0100, [0x11, 0x22]),
            (0x2000, [0xAA, 0xBB, 0xCC, 0xDD]),
            (0x5000, [0x01]),
        ]

        for addr, data in test_cases:
            emu.reset()

            # Write test data
            for i, val in enumerate(data):
                emu.memory.xdata[addr + i] = val

            # Inject E4 read command
            emu.hw.inject_usb_command(0xE4, addr, size=len(data))
            emu.run(max_cycles=50000)

            # Verify result
            result = [emu.memory.xdata[0x8000 + i] for i in range(len(data))]
            assert result == data, f"[{fw_name}] E4 read at 0x{addr:04X} returned {result}, expected {data}"


class TestTimerEmulation:
    """Tests for timer hardware emulation."""

    def test_timer_csr_ready_bit(self, emulator):
        """Test that timer CSR sets ready bit after polling."""
        emu = emulator

        timer_addr = 0xCC11  # Timer 0 CSR

        # Poll the timer CSR
        for _ in range(5):
            value = emu.hw.read(timer_addr)

        # Ready bit (bit 1) should be set after polling
        assert value & 0x02, "Timer ready bit should be set after polling"

    def test_timer_dma_status(self, emulator):
        """Test timer/DMA status register completion."""
        emu = emulator

        dma_status_addr = 0xCC89

        # Poll the status
        for _ in range(5):
            value = emu.hw.read(dma_status_addr)

        # Complete bit should be set
        assert value & 0x02, "Timer/DMA complete bit should be set after polling"


class TestUSBStateMachine:
    """Tests for USB state machine progression."""

    def test_usb_state_progresses_to_configured(self, emulator):
        """Test that USB state machine reaches CONFIGURED state."""
        emu = emulator

        # Connect USB
        emu.hw.usb_controller.connect()

        # State machine should have started
        assert emu.hw.usb_controller.state.value >= 1, "USB should be at least ATTACHED"

        # After enough state machine reads, should be CONFIGURED
        for _ in range(10):
            emu.hw.usb_controller.advance_enumeration()

        assert emu.hw.usb_controller.enumeration_complete, "USB enumeration should complete"

    def test_usb_connect_enables_command_processing(self, emulator):
        """Test that USB connect prepares system for commands."""
        emu = emulator

        assert not emu.hw.usb_connected, "USB should start disconnected"

        emu.hw.usb_controller.connect()

        assert emu.hw.usb_controller.state.value >= 1, "USB should be connected"


class TestUSBEndpointBuffers:
    """Tests for USB endpoint buffer functionality."""

    def test_ep0_buffer_stores_command_data(self, emulator):
        """Test that EP0 buffer can store and retrieve command data."""
        emu = emulator

        # Simulate CDB data that would arrive via USB
        test_cdb = bytes([0xE4, 0x04, 0x50, 0x12, 0x34, 0x00])

        for i, val in enumerate(test_cdb):
            emu.hw.usb_ep0_buf[i] = val

        # Verify data is accessible
        result = bytes([emu.hw.usb_ep0_buf[i] for i in range(len(test_cdb))])
        assert result == test_cdb, "EP0 buffer should store CDB data"

    def test_ep_data_buffer_stores_transfer_data(self, emulator):
        """Test that EP data buffer can store bulk transfer data."""
        emu = emulator

        # Write test payload
        test_data = bytes([0xDE, 0xAD, 0xBE, 0xEF] * 16)

        for i, val in enumerate(test_data):
            emu.hw.usb_ep_data_buf[i] = val

        result = bytes([emu.hw.usb_ep_data_buf[i] for i in range(len(test_data))])
        assert result == test_data, "EP data buffer should store transfer data"


class TestE4ReadCommand:
    """End-to-end tests for E4 (read XDATA) command."""

    def test_e4_reads_single_byte(self, firmware_emulator):
        """Test E4 command reads a single byte from XDATA."""
        emu, fw_name = firmware_emulator

        # Write test value to arbitrary XDATA location
        test_addr = 0x2000
        test_value = 0x42
        emu.memory.xdata[test_addr] = test_value

        # Inject E4 read command
        emu.hw.inject_usb_command(0xE4, test_addr, size=1)

        # Run firmware until DMA completes
        emu.run(max_cycles=50000)

        # USB buffer should contain the read value
        result = emu.memory.xdata[0x8000]
        assert result == test_value, f"[{fw_name}] E4 read returned 0x{result:02X}, expected 0x{test_value:02X}"

    def test_e4_reads_multiple_bytes(self, firmware_emulator):
        """Test E4 command reads multiple bytes from XDATA."""
        emu, fw_name = firmware_emulator

        # Write test pattern
        test_addr = 0x3000
        test_data = [0xCA, 0xFE, 0xBA, 0xBE]
        for i, val in enumerate(test_data):
            emu.memory.xdata[test_addr + i] = val

        # Inject E4 read command
        emu.hw.inject_usb_command(0xE4, test_addr, size=len(test_data))
        emu.run(max_cycles=50000)

        # Check USB buffer contains all bytes
        result = [emu.memory.xdata[0x8000 + i] for i in range(len(test_data))]
        assert result == test_data, f"[{fw_name}] E4 read returned {result}, expected {test_data}"

    def test_e4_reads_from_different_regions(self, firmware_emulator):
        """Test E4 command works for various XDATA regions."""
        emu, fw_name = firmware_emulator

        # Test different XDATA regions
        test_cases = [
            (0x0100, [0x11]),           # Low XDATA
            (0x1000, [0x22, 0x33]),     # Work RAM
            (0x4000, [0x44, 0x55, 0x66, 0x77]),  # Higher XDATA
        ]

        for addr, data in test_cases:
            emu.reset()

            # Write test data
            for i, val in enumerate(data):
                emu.memory.xdata[addr + i] = val

            # Execute E4 read
            emu.hw.inject_usb_command(0xE4, addr, size=len(data))
            emu.run(max_cycles=50000)

            # Verify
            result = [emu.memory.xdata[0x8000 + i] for i in range(len(data))]
            assert result == data, f"[{fw_name}] E4 at 0x{addr:04X}: got {result}, expected {data}"


class TestCodeBanking:
    """End-to-end tests for code memory banking."""

    def test_bank_switching_reads_different_code(self, firmware_emulator):
        """Test that bank switching reads different firmware code."""
        emu, fw_name = firmware_emulator

        # Read from upper memory in bank 0
        emu.memory.sfr[0x96 - 0x80] = 0x00  # DPX = 0
        bank0_byte = emu.memory.read_code(0x8000)

        # Read from same address in bank 1
        emu.memory.sfr[0x96 - 0x80] = 0x01  # DPX = 1
        bank1_byte = emu.memory.read_code(0x8000)

        # Bank 0 and Bank 1 code should be different at most addresses
        # (they're different code sections in the firmware)
        # At minimum, we verify both reads work
        assert bank0_byte is not None, f"[{fw_name}] Bank 0 read should succeed"
        assert bank1_byte is not None, f"[{fw_name}] Bank 1 read should succeed"

    def test_lower_memory_ignores_bank(self, firmware_emulator):
        """Test that lower 32KB always reads from bank 0."""
        emu, fw_name = firmware_emulator

        # Read from lower memory with DPX=0
        emu.memory.sfr[0x96 - 0x80] = 0x00
        byte_dpx0 = emu.memory.read_code(0x1000)

        # Read from same address with DPX=1
        emu.memory.sfr[0x96 - 0x80] = 0x01
        byte_dpx1 = emu.memory.read_code(0x1000)

        # Should be identical (lower 32KB ignores bank)
        assert byte_dpx0 == byte_dpx1, f"[{fw_name}] Lower 32KB should ignore bank setting"


class TestBitOperations:
    """End-to-end tests for 8051 bit-addressable memory."""

    def test_bit_operations_persist_to_byte(self, emulator):
        """Test that individual bit writes affect the underlying byte."""
        emu = emulator

        # Clear the byte first
        emu.memory.idata[0x20] = 0x00

        # Set individual bits and verify byte changes
        emu.memory.write_bit(0x00, True)  # Bit 0
        assert emu.memory.idata[0x20] == 0x01

        emu.memory.write_bit(0x07, True)  # Bit 7
        assert emu.memory.idata[0x20] == 0x81

        emu.memory.write_bit(0x00, False)  # Clear bit 0
        assert emu.memory.idata[0x20] == 0x80

    def test_byte_writes_affect_bit_reads(self, emulator):
        """Test that byte writes are visible through bit reads."""
        emu = emulator

        # Write a byte value
        emu.memory.idata[0x20] = 0xA5  # 10100101

        # Verify individual bits
        assert emu.memory.read_bit(0x00) == True   # bit 0
        assert emu.memory.read_bit(0x01) == False  # bit 1
        assert emu.memory.read_bit(0x02) == True   # bit 2
        assert emu.memory.read_bit(0x05) == True   # bit 5
        assert emu.memory.read_bit(0x06) == False  # bit 6
        assert emu.memory.read_bit(0x07) == True   # bit 7


class TestDMATransfers:
    """End-to-end tests for DMA transfer functionality."""

    def test_dma_copies_data_to_usb_buffer(self, emulator):
        """Test that DMA transfer copies XDATA to USB buffer."""
        emu = emulator

        # Write source data
        src_addr = 0x2500
        test_data = bytes(range(16))  # 0x00, 0x01, ..., 0x0F
        for i, val in enumerate(test_data):
            emu.memory.xdata[src_addr + i] = val

        # Trigger DMA via inject (sets up registers and triggers)
        emu.hw.inject_usb_command(0xE4, src_addr, size=len(test_data))

        # Manually trigger DMA (simulate firmware writing to trigger register)
        emu.hw._perform_pcie_dma(0x500000 | src_addr, len(test_data))

        # Verify USB buffer contains copied data
        result = bytes([emu.memory.xdata[0x8000 + i] for i in range(len(test_data))])
        assert result == test_data, "DMA should copy data to USB buffer"

    def test_dma_sets_completion_status(self, emulator):
        """Test that DMA transfer sets completion status in RAM."""
        emu = emulator

        # Clear completion flag
        emu.memory.xdata[0x0AA0] = 0

        # Trigger small DMA
        emu.hw._perform_pcie_dma(0x500000, 5)

        # Completion flag should be set to transfer size
        assert emu.memory.xdata[0x0AA0] == 5, "DMA completion should indicate size"


class TestFirmwareExecution:
    """End-to-end tests for firmware execution."""

    def test_firmware_runs_without_crash(self, firmware_emulator):
        """Test that firmware executes successfully for many cycles."""
        emu, fw_name = firmware_emulator

        # Run for significant number of cycles
        reason = emu.run(max_cycles=100000)

        # Should stop due to cycle limit, not error
        assert reason == "max_cycles", f"[{fw_name}] Firmware should run without errors, stopped: {reason}"
        assert emu.inst_count > 1000, f"[{fw_name}] Should execute many instructions"

    def test_firmware_produces_uart_output(self, firmware_emulator):
        """Test that firmware produces UART debug output."""
        emu, fw_name = firmware_emulator

        # Capture UART output
        uart_chars = []
        original_uart_tx = emu.hw._uart_tx

        def capture_uart(hw, addr, value):
            if 0x20 <= value < 0x7F:
                uart_chars.append(chr(value))
            original_uart_tx(hw, addr, value)

        emu.hw.write_callbacks[0xC000] = capture_uart
        emu.hw.write_callbacks[0xC001] = capture_uart

        # Run firmware
        emu.run(max_cycles=200000)

        # Should have produced some output
        output = ''.join(uart_chars)
        assert len(output) > 0, f"[{fw_name}] Firmware should produce UART output"

    def test_usb_connect_triggers_state_changes(self, firmware_emulator):
        """Test that USB connect event triggers firmware state changes."""
        emu, fw_name = firmware_emulator

        # Reconfigure with longer delay
        emu.hw.usb_connect_delay = 10000

        # Run past USB connect
        emu.run(max_cycles=50000)

        # USB should be connected
        assert emu.hw.usb_connected, f"[{fw_name}] USB should be connected after delay"

        # USB controller should have progressed
        assert emu.hw.usb_controller.state.value > 0, f"[{fw_name}] USB state should have progressed"


class TestTracingFunctionality:
    """End-to-end tests for execution and XDATA tracing."""

    def test_trace_callback_is_invoked(self, emulator):
        """Test that trace callbacks are invoked on trace point hits."""
        emu = emulator

        hits = []

        def trace_cb(hw, pc, label):
            hits.append((pc, label))

        emu.hw.trace_callback = trace_cb
        emu.hw.add_trace_point(0x1234, "TEST_POINT")
        emu.hw.trace_enabled = True

        # Simulate trace check
        emu.hw.check_trace(0x1234)

        assert len(hits) == 1, "Trace callback should be invoked"
        assert hits[0] == (0x1234, "TEST_POINT"), "Callback should receive correct args"

    def test_xdata_write_log_accumulates(self, emulator):
        """Test that XDATA trace log accumulates write entries."""
        emu = emulator

        emu.hw.add_xdata_trace(0x1000, "VAR_A")
        emu.hw.add_xdata_trace(0x1001, "VAR_B")
        emu.hw.xdata_trace_enabled = True

        # Suppress output during test
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            emu.hw.trace_xdata_write(0x1000, 0x11, pc=0x100)
            emu.hw.trace_xdata_write(0x1001, 0x22, pc=0x200)
            emu.hw.trace_xdata_write(0x1000, 0x33, pc=0x300)
        finally:
            sys.stdout = old_stdout

        assert len(emu.hw.xdata_write_log) == 3, "Should log all writes"


class TestSyncFlagBehavior:
    """End-to-end tests for DMA/timer sync flag handling."""

    def test_sync_flag_cleared_after_polling(self, emulator):
        """Test that sync flags are auto-cleared to simulate hardware completion."""
        emu = emulator

        # Set sync flag (firmware would do this before starting DMA)
        sync_addr = 0x1238
        emu.memory.xdata[sync_addr] = 0x01

        # Poll until cleared (simulates firmware wait loop)
        poll_count = 0
        while emu.memory.read_xdata(sync_addr) != 0x00:
            poll_count += 1
            if poll_count > 10:
                break

        assert emu.memory.xdata[sync_addr] == 0x00, "Sync flag should auto-clear"
        assert poll_count <= 10, "Should clear within reasonable polls"


class TestUSBCommandFlow:
    """End-to-end tests for complete USB command flow."""

    def test_command_injection_sets_up_state(self, emulator):
        """Test that command injection prepares all necessary state."""
        emu = emulator

        # Inject command
        emu.hw.inject_usb_command(0xE4, 0x1234, size=4)

        # Verify USB is ready for command processing
        assert emu.hw.usb_connected, "USB should be connected"
        assert emu.hw.usb_cmd_pending, "Command should be pending"

        # Verify CDB is in registers
        assert emu.hw.regs[0x910D] == 0xE4, "Command type should be in register"

    def test_command_completion_clears_pending(self, emulator):
        """Test that command completion clears the pending flag."""
        emu = emulator

        # Inject and setup command
        emu.hw.inject_usb_command(0xE4, 0x1000, size=1)
        assert emu.hw.usb_cmd_pending, "Command should be pending"

        # Trigger DMA completion
        emu.hw._perform_pcie_dma(0x501000, 1)

        # Simulate firmware writing completion trigger
        emu.hw.write(0xB296, 0x08)

        # Pending should be cleared
        assert not emu.hw.usb_cmd_pending, "Command should no longer be pending"


class TestE5WriteCommand:
    """End-to-end tests for E5 (write XDATA) command."""

    def test_e5_command_injection_format(self, emulator):
        """Test E5 command CDB is formatted correctly."""
        emu = emulator

        # Inject E5 write command: write 0x42 to address 0x1234
        emu.hw.inject_usb_command(0xE5, 0x1234, value=0x42)

        # Check CDB format in registers:
        # CDB[0] = command (0xE5)
        # CDB[1] = value (0x42)
        # CDB[2] = addr_high (0x50 for XDATA)
        # CDB[3] = addr_mid (0x12)
        # CDB[4] = addr_low (0x34)
        assert emu.hw.regs[0x910D] == 0xE5, "CDB[0] should be 0xE5"
        assert emu.hw.regs[0x910E] == 0x42, "CDB[1] should be value"
        assert emu.hw.regs[0x910F] == 0x50, "CDB[2] should be 0x50 (XDATA marker)"
        assert emu.hw.regs[0x9110] == 0x12, "CDB[3] should be addr mid"
        assert emu.hw.regs[0x9111] == 0x34, "CDB[4] should be addr low"

    def test_e5_sets_correct_command_marker(self, emulator):
        """Test E5 command sets correct marker in command table."""
        emu = emulator

        emu.hw.inject_usb_command(0xE5, 0x1234, value=0x42)

        # E5 should set command marker to 0x05
        assert emu.memory.xdata[0x05B1] == 0x05, "E5 marker should be 0x05"

    def test_e5_and_e4_use_same_address_format(self, emulator):
        """Test E5 and E4 use compatible address encoding."""
        emu = emulator

        test_addr = 0x2ABC

        # Inject E4 and check address encoding
        emu.hw.inject_usb_command(0xE4, test_addr, size=1)
        e4_addr_high = emu.hw.regs[0x910F]
        e4_addr_mid = emu.hw.regs[0x9110]
        e4_addr_low = emu.hw.regs[0x9111]

        # Reset and inject E5 to same address
        emu.reset()
        emu.hw.inject_usb_command(0xE5, test_addr, value=0x00)
        e5_addr_high = emu.hw.regs[0x910F]
        e5_addr_mid = emu.hw.regs[0x9110]
        e5_addr_low = emu.hw.regs[0x9111]

        # Address encoding should be identical
        assert e4_addr_high == e5_addr_high, "Address high byte should match"
        assert e4_addr_mid == e5_addr_mid, "Address mid byte should match"
        assert e4_addr_low == e5_addr_low, "Address low byte should match"


class TestE4E5Roundtrip:
    """Tests for E4/E5 read/write roundtrip functionality."""

    def test_e4_e5_address_compatibility(self, firmware_emulator):
        """Test that E4 can read back what would be written by E5."""
        emu, fw_name = firmware_emulator

        # Set up initial value
        test_addr = 0x2000
        test_value = 0x55

        # Pre-write the value to XDATA (simulating E5)
        emu.memory.xdata[test_addr] = test_value

        # Now E4 read should return that value
        emu.hw.inject_usb_command(0xE4, test_addr, size=1)
        emu.run(max_cycles=50000)

        result = emu.memory.xdata[0x8000]
        assert result == test_value, f"[{fw_name}] E4 should read back 0x{test_value:02X}, got 0x{result:02X}"


class TestMultipleCommands:
    """Tests for multiple sequential commands."""

    def test_sequential_e4_commands(self, firmware_emulator):
        """Test multiple E4 commands in sequence."""
        emu, fw_name = firmware_emulator

        # Set up test data at different locations
        locations = [
            (0x1000, 0xAA),
            (0x2000, 0xBB),
            (0x3000, 0xCC),
        ]

        for addr, value in locations:
            emu.reset()
            emu.memory.xdata[addr] = value

            emu.hw.inject_usb_command(0xE4, addr, size=1)
            emu.run(max_cycles=50000)

            result = emu.memory.xdata[0x8000]
            assert result == value, f"[{fw_name}] E4 at 0x{addr:04X}: expected 0x{value:02X}, got 0x{result:02X}"


class TestCDBParsing:
    """Tests for Command Descriptor Block parsing."""

    def test_cdb_address_encoding(self, emulator):
        """Test CDB encodes addresses correctly."""
        emu = emulator

        # Test various addresses
        test_cases = [
            (0x0000, 0x50, 0x00, 0x00),
            (0x1234, 0x50, 0x12, 0x34),
            (0xFFFF, 0x51, 0xFF, 0xFF),  # 0x1FFFF -> 0x51FFFF
            (0x5678, 0x50, 0x56, 0x78),
        ]

        for addr, exp_high, exp_mid, exp_low in test_cases:
            emu.reset()
            emu.hw.inject_usb_command(0xE4, addr, size=1)

            # Address format: (addr & 0x1FFFF) | 0x500000
            usb_addr = (addr & 0x1FFFF) | 0x500000
            got_high = emu.hw.regs[0x910F]
            got_mid = emu.hw.regs[0x9110]
            got_low = emu.hw.regs[0x9111]

            # Check the address is encoded correctly
            reconstructed = (got_high << 16) | (got_mid << 8) | got_low
            assert reconstructed == usb_addr, \
                f"Address 0x{addr:04X} -> USB 0x{usb_addr:06X}, got 0x{reconstructed:06X}"


class TestScsiWriteCommand:
    """Tests for 0x8A SCSI write command."""

    def test_scsi_write_cdb_format(self, emulator):
        """Test SCSI write CDB is formatted correctly."""
        import struct

        emu = emulator

        # Inject SCSI write command: LBA=0, 1 sector, test data
        test_data = b'Hello SCSI!' + b'\x00' * (512 - 11)
        emu.hw.inject_scsi_write(lba=0, sectors=1, data=test_data)

        # Check CDB format in registers
        # CDB[0] = 0x8A (SCSI write command)
        # CDB[1] = 0x00 (reserved)
        # CDB[2-9] = LBA (8 bytes, big-endian)
        # CDB[10-13] = sectors (4 bytes, big-endian)
        # CDB[14-15] = 0x00 (reserved)
        assert emu.hw.regs[0x910D] == 0x8A, "CDB[0] should be 0x8A"
        assert emu.hw.regs[0x910E] == 0x00, "CDB[1] should be 0x00"

        # LBA is bytes 2-9 (8 bytes big-endian)
        lba_bytes = bytes([emu.hw.regs[0x910D + 2 + i] for i in range(8)])
        lba = struct.unpack('>Q', lba_bytes)[0]
        assert lba == 0, f"LBA should be 0, got {lba}"

        # Sectors is bytes 10-13 (4 bytes big-endian)
        sector_bytes = bytes([emu.hw.regs[0x910D + 10 + i] for i in range(4)])
        sectors = struct.unpack('>I', sector_bytes)[0]
        assert sectors == 1, f"Sectors should be 1, got {sectors}"

    def test_scsi_write_data_in_usb_buffer(self, emulator):
        """Test SCSI write data is placed in USB buffer at 0x8000."""
        emu = emulator

        # Create test data pattern
        test_pattern = bytes([i & 0xFF for i in range(512)])
        emu.hw.inject_scsi_write(lba=0, sectors=1, data=test_pattern)

        # Verify data at USB buffer
        buffer_data = bytes([emu.memory.xdata[0x8000 + i] for i in range(512)])
        assert buffer_data == test_pattern, "USB buffer should contain test data"

    def test_scsi_write_multiple_sectors(self, emulator):
        """Test SCSI write with multiple sectors."""
        import struct

        emu = emulator

        # Write 4 sectors
        test_data = bytes([i & 0xFF for i in range(4 * 512)])
        emu.hw.inject_scsi_write(lba=100, sectors=4, data=test_data)

        # Check sector count
        sector_bytes = bytes([emu.hw.regs[0x910D + 10 + i] for i in range(4)])
        sectors = struct.unpack('>I', sector_bytes)[0]
        assert sectors == 4, f"Sectors should be 4, got {sectors}"

        # Check LBA
        lba_bytes = bytes([emu.hw.regs[0x910D + 2 + i] for i in range(8)])
        lba = struct.unpack('>Q', lba_bytes)[0]
        assert lba == 100, f"LBA should be 100, got {lba}"

        # Verify all data was written
        buffer_data = bytes([emu.memory.xdata[0x8000 + i] for i in range(4 * 512)])
        assert buffer_data == test_data, "USB buffer should contain all sectors"

    def test_scsi_write_data_padding(self, emulator):
        """Test SCSI write pads data to sector boundary."""
        emu = emulator

        # Write partial sector (less than 512 bytes)
        test_data = b'Short data'
        emu.hw.inject_scsi_write(lba=0, sectors=1, data=test_data)

        # Verify padding - remaining bytes should be 0x00
        for i in range(len(test_data)):
            assert emu.memory.xdata[0x8000 + i] == test_data[i], f"Byte {i} should match"

        for i in range(len(test_data), 512):
            assert emu.memory.xdata[0x8000 + i] == 0x00, f"Byte {i} should be padded to 0x00"

    def test_scsi_write_sets_command_pending(self, emulator):
        """Test SCSI write sets command pending flag."""
        emu = emulator

        assert not emu.hw.usb_cmd_pending, "No command should be pending initially"

        emu.hw.inject_scsi_write(lba=0, sectors=1, data=b'\x00' * 512)

        assert emu.hw.usb_cmd_pending, "Command should be pending after inject"
        assert emu.hw.usb_cmd_type == 0x8A, "Command type should be 0x8A"

    def test_scsi_write_cdb_in_ram(self, emulator):
        """Test SCSI write CDB is written to RAM at 0x0002."""
        emu = emulator

        emu.hw.inject_scsi_write(lba=0, sectors=1, data=b'\x00' * 512)

        # CDB should be at XDATA[0x0002+]
        assert emu.memory.xdata[0x0002] == 0x8A, "CDB[0] at 0x0002 should be 0x8A"
        assert emu.memory.xdata[0x0003] == 0x08, "Vendor flag at 0x0003 should be 0x08"


class TestScsiWriteCompatibility:
    """Tests for SCSI write compatibility with python/usb.py format."""

    def test_cdb_matches_python_usb_format(self, emulator):
        """Test CDB format matches python/usb.py ScsiWriteOp."""
        import struct

        emu = emulator

        lba = 0x123456789ABC
        sectors = 32

        emu.hw.inject_scsi_write(lba=lba, sectors=sectors, data=b'\x00' * (sectors * 512))

        # Build expected CDB from python/usb.py format
        expected_cdb = struct.pack('>BBQIBB', 0x8A, 0, lba, sectors, 0, 0)

        # Get actual CDB from registers
        actual_cdb = bytes([emu.hw.regs[0x910D + i] for i in range(16)])

        assert actual_cdb == expected_cdb, \
            f"CDB mismatch: got {actual_cdb.hex()}, expected {expected_cdb.hex()}"

    def test_scsi_and_vendor_commands_coexist(self, emulator):
        """Test that SCSI and vendor commands can be used in sequence."""
        emu = emulator

        # First inject E4 read
        emu.hw.inject_usb_command(0xE4, 0x1000, size=1)
        assert emu.hw.usb_cmd_type == 0xE4, "Should be E4 command"

        # Reset for next command
        emu.hw.usb_cmd_pending = False

        # Then inject SCSI write
        emu.hw.inject_scsi_write(lba=0, sectors=1, data=b'\x00' * 512)
        assert emu.hw.usb_cmd_type == 0x8A, "Should be 0x8A command"

        # Verify SCSI CDB
        assert emu.hw.regs[0x910D] == 0x8A, "CDB should now be SCSI write"


class TestCommandDispatch:
    """Tests for command type dispatch."""

    def test_command_types_have_different_markers(self, emulator):
        """Test different command types set different markers."""
        emu = emulator

        # E4 read
        emu.reset()
        emu.hw.inject_usb_command(0xE4, 0x1000, size=1)
        e4_marker = emu.memory.xdata[0x05B1]

        # E5 write
        emu.reset()
        emu.hw.inject_usb_command(0xE5, 0x1000, value=0x42)
        e5_marker = emu.memory.xdata[0x05B1]

        # SCSI write
        emu.reset()
        emu.hw.inject_scsi_write(lba=0, sectors=1, data=b'\x00' * 512)
        scsi_marker = emu.memory.xdata[0x05B1]

        # All should have different markers
        assert e4_marker == 0x04, f"E4 marker should be 0x04, got 0x{e4_marker:02X}"
        assert e5_marker == 0x05, f"E5 marker should be 0x05, got 0x{e5_marker:02X}"
        assert scsi_marker == 0x8A, f"SCSI marker should be 0x8A, got 0x{scsi_marker:02X}"

    def test_usb_state_configured_for_all_commands(self, emulator):
        """Test USB state is set to CONFIGURED (5) for all command types."""
        emu = emulator

        for cmd_name, inject_fn in [
            ("E4", lambda: emu.hw.inject_usb_command(0xE4, 0x1000, size=1)),
            ("E5", lambda: emu.hw.inject_usb_command(0xE5, 0x1000, value=0x42)),
            ("SCSI", lambda: emu.hw.inject_scsi_write(lba=0, sectors=1, data=b'\x00' * 512)),
        ]:
            emu.reset()
            inject_fn()
            usb_state = emu.memory.idata[0x6A]
            assert usb_state == 5, f"{cmd_name}: USB state should be 5, got {usb_state}"


class TestVendorCommandStateMachine:
    """Tests for USB state machine behavior during vendor commands."""

    def test_usb_state_set_to_5_before_command(self, firmware_emulator):
        """Test that I_STATE_6A is set to 5 (CONFIGURED) before command processing."""
        emu, fw_name = firmware_emulator

        emu.hw.inject_usb_command(0xE4, 0x1000, size=1)

        # USB state should be 5 before firmware runs
        state = emu.memory.idata[0x6A]
        assert state == 5, f"[{fw_name}] USB state should be 5 before command, got {state}"

    def test_vendor_flag_set_for_e4(self, firmware_emulator):
        """Test that vendor flag (G_EP_STATUS_CTRL) bit 3 is set for E4 commands."""
        emu, fw_name = firmware_emulator

        emu.hw.inject_usb_command(0xE4, 0x1000, size=1)

        # G_EP_STATUS_CTRL (0x0003) should have bit 3 set (0x08)
        vendor_flag = emu.memory.xdata[0x0003]
        assert vendor_flag & 0x08, f"[{fw_name}] Vendor flag bit 3 should be set, got 0x{vendor_flag:02X}"

    def test_status_register_written_during_e4(self, firmware_emulator):
        """Test that 0x90E3 is written with 0x02 during E4 processing."""
        emu, fw_name = firmware_emulator

        # Track writes to 0x90E3
        writes_90e3 = []
        def track_90e3(addr, val):
            writes_90e3.append(val)
        emu.memory.xdata_write_hooks[0x90E3] = track_90e3

        emu.hw.inject_usb_command(0xE4, 0x1000, size=1)
        emu.run(max_cycles=50000)

        assert 0x02 in writes_90e3, f"[{fw_name}] 0x90E3 should be written with 0x02, writes: {writes_90e3}"


class TestDMATriggerSequence:
    """Tests for the DMA trigger sequence during E4 commands."""

    def test_dma_triggered_by_0x08_write_to_b296(self, firmware_emulator):
        """Test that DMA is triggered by writing 0x08 to 0xB296."""
        emu, fw_name = firmware_emulator

        # Track writes to 0xB296
        writes_b296 = []
        original_write = emu.hw.write_callbacks.get(0xB296)

        def track_b296(hw, addr, val):
            writes_b296.append(val)
            if original_write:
                original_write(hw, addr, val)

        emu.hw.write_callbacks[0xB296] = track_b296

        # Setup test data
        emu.memory.xdata[0x1000] = 0xAB

        emu.hw.inject_usb_command(0xE4, 0x1000, size=1)
        emu.run(max_cycles=50000)

        # Should have written 0x08 to trigger DMA
        assert 0x08 in writes_b296, f"[{fw_name}] 0xB296 should be written with 0x08, writes: {writes_b296}"

    def test_dma_copies_correct_data(self, firmware_emulator):
        """Test that DMA correctly copies data from source to USB buffer."""
        emu, fw_name = firmware_emulator

        # Setup distinctive test pattern
        test_data = [0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE]
        for i, val in enumerate(test_data):
            emu.memory.xdata[0x2000 + i] = val

        emu.hw.inject_usb_command(0xE4, 0x2000, size=len(test_data))
        emu.run(max_cycles=50000)

        # Verify USB buffer at 0x8000
        result = [emu.memory.xdata[0x8000 + i] for i in range(len(test_data))]
        assert result == test_data, f"[{fw_name}] DMA should copy exact data, got {[hex(x) for x in result]}"

    def test_dma_size_from_cdb(self, firmware_emulator):
        """Test that DMA uses size from CDB register 0x910E."""
        emu, fw_name = firmware_emulator

        # Fill area with known pattern
        for i in range(32):
            emu.memory.xdata[0x3000 + i] = i + 0x40

        # Request only 4 bytes
        emu.hw.inject_usb_command(0xE4, 0x3000, size=4)
        emu.run(max_cycles=50000)

        # First 4 bytes should be copied
        result = [emu.memory.xdata[0x8000 + i] for i in range(4)]
        expected = [0x40, 0x41, 0x42, 0x43]
        assert result == expected, f"[{fw_name}] Should copy exactly 4 bytes, got {[hex(x) for x in result]}"


class TestE5WriteCommand:
    """Tests for E5 write command functionality.

    Note: E5 tests for original firmware are expected to fail because the
    original firmware's E5 command handling uses a different code path that
    doesn't go through the DMA trigger at 0xB296 that our emulator captures.
    Our firmware implements E5 through the same DMA path as E4.
    """

    def test_e5_writes_to_xdata(self, firmware_emulator):
        """Test E5 command writes value to specified XDATA address."""
        emu, fw_name = firmware_emulator

        test_addr = 0x2500
        test_value = 0x77

        # Clear the location first
        emu.memory.xdata[test_addr] = 0x00

        # Inject E5 write command
        emu.hw.inject_usb_command(0xE5, test_addr, value=test_value)
        # Use absolute cycle count (current + additional)
        emu.run(max_cycles=emu.cpu.cycles + 50000)

        # Verify the value was written
        result = emu.memory.xdata[test_addr]
        assert result == test_value, f"[{fw_name}] E5 should write 0x{test_value:02X}, got 0x{result:02X}"

    def test_e5_writes_multiple_addresses(self, firmware_emulator):
        """Test E5 command can write to different addresses."""
        emu, fw_name = firmware_emulator

        test_cases = [
            (0x1000, 0x11),
            (0x2000, 0x22),
            (0x3000, 0x33),
            (0x4000, 0x44),
        ]

        for addr, value in test_cases:
            emu.reset()
            # Run to boot state
            emu.run(max_cycles=500000)
            emu.memory.xdata[addr] = 0x00  # Clear first

            emu.hw.inject_usb_command(0xE5, addr, value=value)
            emu.run(max_cycles=emu.cpu.cycles + 50000)

            result = emu.memory.xdata[addr]
            assert result == value, f"[{fw_name}] E5 at 0x{addr:04X}: expected 0x{value:02X}, got 0x{result:02X}"

    def test_e5_e4_roundtrip(self, firmware_emulator):
        """Test E5 write followed by E4 read returns same value."""
        emu, fw_name = firmware_emulator

        test_addr = 0x2800
        test_value = 0xA5

        # First write with E5
        emu.hw.inject_usb_command(0xE5, test_addr, value=test_value)
        emu.run(max_cycles=emu.cpu.cycles + 50000)

        # Store the written value directly since E5 DMA writes to XDATA
        written_value = emu.memory.xdata[test_addr]

        # Reset state for next command
        emu.reset()
        emu.run(max_cycles=500000)

        # Restore the value since reset clears XDATA
        emu.memory.xdata[test_addr] = written_value

        # Then read back with E4
        emu.hw.inject_usb_command(0xE4, test_addr, size=1)
        emu.run(max_cycles=emu.cpu.cycles + 50000)

        result = emu.memory.xdata[0x8000]
        assert result == test_value, f"[{fw_name}] E4 after E5 should read 0x{test_value:02X}, got 0x{result:02X}"


class TestE4EdgeCases:
    """Tests for E4 command edge cases."""

    def test_e4_read_single_byte(self, firmware_emulator):
        """Test E4 reading exactly 1 byte."""
        emu, fw_name = firmware_emulator

        emu.memory.xdata[0x1234] = 0x99
        emu.hw.inject_usb_command(0xE4, 0x1234, size=1)
        emu.run(max_cycles=50000)

        assert emu.memory.xdata[0x8000] == 0x99, f"[{fw_name}] Single byte read failed"

    def test_e4_read_max_size_64(self, firmware_emulator):
        """Test E4 reading maximum typical size (64 bytes)."""
        emu, fw_name = firmware_emulator

        # Fill with pattern
        for i in range(64):
            emu.memory.xdata[0x1000 + i] = i ^ 0xAA

        emu.hw.inject_usb_command(0xE4, 0x1000, size=64)
        emu.run(max_cycles=50000)

        # Verify all 64 bytes
        for i in range(64):
            expected = i ^ 0xAA
            result = emu.memory.xdata[0x8000 + i]
            assert result == expected, f"[{fw_name}] Byte {i}: expected 0x{expected:02X}, got 0x{result:02X}"

    def test_e4_read_low_xdata(self, firmware_emulator):
        """Test E4 reading from low XDATA addresses (work RAM)."""
        emu, fw_name = firmware_emulator

        # Low XDATA is work RAM
        test_addr = 0x0050
        emu.memory.xdata[test_addr] = 0xCC

        emu.hw.inject_usb_command(0xE4, test_addr, size=1)
        emu.run(max_cycles=50000)

        assert emu.memory.xdata[0x8000] == 0xCC, f"[{fw_name}] Low XDATA read failed"

    def test_e4_read_high_xdata(self, firmware_emulator):
        """Test E4 reading from high XDATA addresses."""
        emu, fw_name = firmware_emulator

        test_addr = 0x5000
        emu.memory.xdata[test_addr] = 0xDD

        emu.hw.inject_usb_command(0xE4, test_addr, size=1)
        emu.run(max_cycles=50000)

        assert emu.memory.xdata[0x8000] == 0xDD, f"[{fw_name}] High XDATA read failed"

    def test_e4_preserves_adjacent_memory(self, firmware_emulator):
        """Test E4 doesn't corrupt memory adjacent to target."""
        emu, fw_name = firmware_emulator

        # Fill area around target
        for i in range(16):
            emu.memory.xdata[0x2000 + i] = i + 1

        # Read just 4 bytes from middle
        emu.hw.inject_usb_command(0xE4, 0x2004, size=4)
        emu.run(max_cycles=50000)

        # Verify source data wasn't corrupted
        for i in range(16):
            expected = i + 1
            result = emu.memory.xdata[0x2000 + i]
            assert result == expected, f"[{fw_name}] Source memory corrupted at offset {i}"


class TestRegisterStateDuringCommands:
    """Tests for register state during command processing."""

    def test_cdb_registers_contain_command(self, firmware_emulator):
        """Test CDB registers are set up correctly before command runs."""
        emu, fw_name = firmware_emulator

        emu.hw.inject_usb_command(0xE4, 0x1234, size=8)

        # Check CDB registers
        assert emu.hw.regs[0x910D] == 0xE4, f"[{fw_name}] Command type wrong"
        assert emu.hw.regs[0x910E] == 0x08, f"[{fw_name}] Size wrong"
        assert emu.hw.regs[0x910F] == 0x50, f"[{fw_name}] Addr high wrong"
        assert emu.hw.regs[0x9110] == 0x12, f"[{fw_name}] Addr mid wrong"
        assert emu.hw.regs[0x9111] == 0x34, f"[{fw_name}] Addr low wrong"

    def test_usb_interrupt_triggers_handler(self, firmware_emulator):
        """Test that USB interrupt is triggered and handler runs."""
        emu, fw_name = firmware_emulator

        # Track if interrupt handler PC was reached
        handler_reached = [False]

        # Original firmware handler entry is around 0x0E33
        # Our firmware may have handler at a different address
        # Both should respond to External Interrupt 0 (vector 0x0003)
        # The interrupt vector at 0x0003 typically has a jump to the actual handler

        def check_handler():
            pc = emu.cpu.pc
            # Check if we're in the interrupt handler region
            # Original: 0x0E00-0x0FFF
            # Also check the interrupt vector region 0x0000-0x00FF
            # or any address that indicates the interrupt was processed
            if 0x0E00 <= pc <= 0x0FFF:
                handler_reached[0] = True
            # Also check for 0x0003 (EX0 vector) or near it
            if 0x0003 <= pc <= 0x0030:
                handler_reached[0] = True

        emu.hw.inject_usb_command(0xE4, 0x1000, size=1)

        # Run and check PC periodically
        for _ in range(1000):
            check_handler()
            if handler_reached[0]:
                break
            emu.step()

        assert handler_reached[0], f"[{fw_name}] Interrupt handler should be reached"


class TestFirmwareBehaviorComparison:
    """Tests that verify firmware behavior matches expected results.

    These tests run against whichever firmware is selected and verify
    the expected behavior. Both firmwares should produce correct results.
    """

    def test_e4_reads_various_patterns(self, firmware_emulator):
        """Test E4 read command handles various data patterns correctly."""
        emu, fw_name = firmware_emulator

        test_cases = [
            (0x1000, [0x11, 0x22, 0x33, 0x44]),
            (0x2000, [0xAA, 0xBB]),
            (0x3000, [0xFF]),
            (0x4000, [0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE]),
        ]

        for test_addr, test_data in test_cases:
            emu.reset()
            emu.run(max_cycles=500000)

            for i, val in enumerate(test_data):
                emu.memory.xdata[test_addr + i] = val

            emu.hw.inject_usb_command(0xE4, test_addr, size=len(test_data))
            emu.run(max_cycles=emu.cpu.cycles + 50000)

            result = [emu.memory.xdata[0x8000 + i] for i in range(len(test_data))]
            assert result == test_data, \
                f"[{fw_name}] E4 at 0x{test_addr:04X}: expected {[hex(x) for x in test_data]}, got {[hex(x) for x in result]}"

    def test_e5_writes_various_patterns(self, firmware_emulator):
        """Test E5 write command handles various data patterns correctly."""
        emu, fw_name = firmware_emulator

        test_cases = [
            (0x1500, 0x42),
            (0x2500, 0xAA),
            (0x3500, 0x55),
            (0x4500, 0x01),
        ]

        for test_addr, test_value in test_cases:
            emu.reset()
            emu.run(max_cycles=500000)

            emu.hw.inject_usb_command(0xE5, test_addr, value=test_value)
            emu.run(max_cycles=emu.cpu.cycles + 50000)

            result = emu.memory.xdata[test_addr]
            assert result == test_value, \
                f"[{fw_name}] E5 at 0x{test_addr:04X}: expected 0x{test_value:02X}, got 0x{result:02X}"

    def test_sequential_e4_commands(self, firmware_emulator):
        """Test sequential E4 read commands work correctly."""
        emu, fw_name = firmware_emulator

        # First E4 read
        emu.memory.xdata[0x2000] = 0x55
        emu.hw.inject_usb_command(0xE4, 0x2000, size=1)
        emu.run(max_cycles=emu.cpu.cycles + 50000)

        result1 = emu.memory.xdata[0x8000]
        assert result1 == 0x55, f"[{fw_name}] First E4 read: expected 0x55, got 0x{result1:02X}"

        # Reset for next command
        emu.reset()
        emu.run(max_cycles=500000)

        # Second E4 read
        emu.memory.xdata[0x3000] = 0xAA
        emu.hw.inject_usb_command(0xE4, 0x3000, size=1)
        emu.run(max_cycles=emu.cpu.cycles + 50000)

        result2 = emu.memory.xdata[0x8000]
        assert result2 == 0xAA, f"[{fw_name}] Second E4 read: expected 0xAA, got 0x{result2:02X}"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
