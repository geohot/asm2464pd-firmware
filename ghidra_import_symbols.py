# Ghidra Python Script for AS2464 USB4/NVMe Firmware
# Imports function names, register labels, and global variables from reverse engineering work
#
# To use: Run in Ghidra's Script Manager on the loaded fw.bin
# The script handles both CODE_BANK0 (0x0000-0xFFFF) and CODE_BANK1 (0x10000-0x17FFF)
#
# Memory Layout:
#   CODE_BANK0: 0x0000-0xFFFF  (first 64KB, always accessible)
#   CODE_BANK1: 0x10000-0x17FFF (second bank, mapped to 0x8000-0xFFFF when DPX=1)
#   EXTMEM: 0x0000-0xFFFF (XDATA space - RAM, MMIO registers)
#
# @author reverse-asm2464 project
# @category ASMedia.AS2464

from ghidra.program.model.symbol import SourceType
from ghidra.program.model.address import AddressSet

def create_function_if_needed(addr, name):
    """Create function at address if it doesn't exist, then set the name"""
    func = getFunctionAt(addr)
    if func is None:
        createFunction(addr, name)
        func = getFunctionAt(addr)
    if func is not None:
        func.setName(name, SourceType.USER_DEFINED)
        print("Added function: {} at {}".format(name, addr))
        return True
    else:
        # Try to just set a label
        createLabel(addr, name, True)
        print("Added label: {} at {}".format(name, addr))
        return True
    return False

def create_label(addr, name):
    """Create a label at the given address"""
    try:
        createLabel(addr, name, True)
        print("Added label: {} at {}".format(name, addr))
        return True
    except:
        print("Failed to add label: {} at {}".format(name, addr))
        return False

def add_bank0_functions():
    """Add all known Bank 0 function names (0x0000-0xFFFF)"""

    # Bank 0 Function mappings: (address, name)
    # These are verified addresses from our C reimplementation
    functions = [
        # =========================================================================
        # Reset/Entry Vectors (0x0000-0x00FF)
        # =========================================================================
        (0x0000, "reset_vector"),

        # =========================================================================
        # Bank Switching / Dispatch (0x0300-0x064F)
        # =========================================================================
        (0x0300, "jump_bank_0"),
        (0x030a, "jump_bank_0_entry"),
        (0x0311, "jump_bank_1"),
        (0x0322, "dispatch_0322"),
        (0x0327, "dispatch_0327_usb_power_init"),
        (0x032c, "dispatch_032c"),
        (0x0331, "dispatch_0331"),
        (0x0336, "dispatch_0336"),
        (0x033b, "dispatch_033b"),
        (0x0340, "dispatch_0340"),
        (0x0345, "dispatch_0345"),
        (0x034a, "dispatch_034a"),
        (0x034f, "dispatch_034f"),
        (0x0354, "dispatch_0354"),
        (0x0359, "dispatch_0359"),
        (0x035e, "dispatch_035e"),
        (0x0363, "dispatch_0363"),
        (0x0368, "dispatch_0368"),
        (0x036d, "dispatch_036d"),
        (0x0372, "dispatch_0372"),
        (0x0377, "dispatch_0377"),
        (0x037c, "dispatch_037c"),
        (0x0381, "dispatch_0381"),
        (0x0386, "dispatch_0386"),
        (0x038b, "dispatch_038b"),
        (0x0390, "dispatch_0390"),
        (0x0395, "dispatch_0395"),
        (0x039a, "dispatch_039a_buffer"),
        (0x039f, "dispatch_039f"),
        (0x03a4, "dispatch_03a4"),
        (0x03a9, "dispatch_03a9_bank1"),
        (0x03ae, "dispatch_03ae_bank1"),
        (0x03b3, "dispatch_03b3_bank1"),
        (0x03b8, "dispatch_03b8_bank1"),
        (0x03bd, "dispatch_03bd_bank1"),
        (0x03c2, "dispatch_03c2_bank1"),
        (0x03c7, "dispatch_03c7_bank1"),
        (0x03cc, "dispatch_03cc_bank1"),
        (0x03d1, "dispatch_03d1_bank1"),
        (0x03d6, "dispatch_03d6_bank1"),
        (0x03db, "dispatch_03db_bank1"),
        (0x03e0, "dispatch_03e0_bank1"),
        (0x03e5, "dispatch_03e5_bank1"),
        (0x03ea, "dispatch_03ea_bank1"),
        (0x03ef, "dispatch_03ef_bank1"),
        (0x03f4, "dispatch_03f4_bank1"),
        (0x03f9, "dispatch_03f9_bank1"),
        (0x03fe, "dispatch_03fe_bank1"),
        (0x0403, "dispatch_0403_bank1"),
        (0x0408, "dispatch_0408_bank1"),
        (0x040d, "dispatch_040d_bank1"),
        (0x0412, "dispatch_0412"),
        (0x0417, "dispatch_0417"),
        (0x041c, "dispatch_041c"),
        (0x0421, "dispatch_0421"),
        (0x0426, "dispatch_0426"),
        (0x042b, "dispatch_042b"),
        (0x0430, "dispatch_0430"),
        (0x0435, "dispatch_0435"),
        (0x043a, "dispatch_043a"),
        (0x043f, "dispatch_043f"),
        (0x0444, "dispatch_0444"),
        (0x0449, "dispatch_0449"),
        (0x044e, "dispatch_044e"),
        (0x0453, "dispatch_0453"),
        (0x0458, "dispatch_0458"),
        (0x045d, "dispatch_045d"),
        (0x0462, "dispatch_0462"),
        (0x0467, "dispatch_0467"),
        (0x046c, "dispatch_046c"),
        (0x0471, "dispatch_0471"),
        (0x0476, "dispatch_0476"),
        (0x047b, "dispatch_047b"),
        (0x0480, "dispatch_0480"),
        (0x0485, "dispatch_0485"),
        (0x048a, "dispatch_048a_bank1"),
        (0x048f, "dispatch_048f_bank1"),
        (0x0494, "handler_0494_event"),
        (0x0499, "dispatch_0499_bank1"),
        (0x049e, "dispatch_049e"),
        (0x04a3, "dispatch_04a3"),
        (0x04a8, "dispatch_04a8"),
        (0x04ad, "dispatch_04ad"),
        (0x04b2, "handler_04b2_reserved"),
        (0x04b7, "dispatch_04b7"),
        (0x04bc, "dispatch_04bc"),
        (0x04c1, "dispatch_04c1"),
        (0x04c6, "dispatch_04c6"),
        (0x04cb, "dispatch_04cb"),
        (0x04d0, "handler_04d0_timer_link"),
        (0x04d5, "dispatch_04d5"),
        (0x04da, "dispatch_04da"),
        (0x04df, "dispatch_04df"),
        (0x04e4, "dispatch_04e4"),
        (0x04e9, "dispatch_04e9"),
        (0x04ee, "dispatch_04ee"),
        (0x04f3, "dispatch_04f3"),
        (0x04f8, "dispatch_04f8"),
        (0x04fd, "dispatch_04fd"),
        (0x0502, "dispatch_0502"),
        (0x0507, "dispatch_0507"),
        (0x050c, "dispatch_050c"),
        (0x0511, "dispatch_0511"),
        (0x0516, "dispatch_0516"),
        (0x051b, "dispatch_051b"),
        (0x0520, "handler_0520_system_int"),
        (0x0525, "handler_0525_flash_cmd"),
        (0x052a, "dispatch_052a"),
        (0x052f, "handler_052f_pcie_nvme_event"),
        (0x0534, "dispatch_0534"),
        (0x0539, "dispatch_0539"),
        (0x053e, "dispatch_053e"),
        (0x0543, "dispatch_0543"),
        (0x0548, "dispatch_0548"),
        (0x054d, "dispatch_054d"),
        (0x0552, "dispatch_0552"),
        (0x0557, "dispatch_0557"),
        (0x055c, "dispatch_055c"),
        (0x0561, "dispatch_0561"),
        (0x0566, "dispatch_0566"),
        (0x056b, "dispatch_056b"),
        (0x0570, "handler_0570_bank1_e911"),
        (0x0575, "dispatch_0575_bank1"),
        (0x057a, "dispatch_057a_bank1"),
        (0x057f, "dispatch_057f"),
        (0x0584, "dispatch_0584_bank1"),
        (0x0589, "handler_0589_phy_config"),
        (0x058e, "dispatch_058e"),
        (0x0593, "handler_0593_bank0_c105"),
        (0x0598, "dispatch_0598_bank1"),
        (0x059d, "dispatch_059d_bank1"),
        (0x05a2, "dispatch_05a2"),
        (0x05a7, "dispatch_05a7"),
        (0x05ac, "dispatch_05ac_bank1"),
        (0x05b1, "dispatch_05b1"),
        (0x05b6, "dispatch_05b6_bank1"),
        (0x05bb, "dispatch_05bb"),
        (0x05c0, "dispatch_05c0"),
        (0x05c5, "dispatch_05c5_bank1"),
        (0x05ca, "dispatch_05ca_bank1"),
        (0x05cf, "dispatch_05cf"),
        (0x05d4, "dispatch_05d4"),
        (0x05d9, "dispatch_05d9_bank1"),
        (0x05de, "dispatch_05de_bank1"),
        (0x05e3, "dispatch_05e3"),
        (0x05e8, "dispatch_05e8_bank1"),
        (0x05ed, "dispatch_05ed_bank1"),
        (0x05f2, "dispatch_05f2"),
        (0x05f7, "dispatch_05f7_bank1"),
        (0x05fc, "dispatch_05fc_bank1"),
        (0x0601, "dispatch_0601"),
        (0x0606, "handler_0606_error_state"),
        (0x060b, "dispatch_060b_bank1"),
        (0x0610, "dispatch_0610_bank1"),
        (0x0615, "dispatch_0615_bank1"),
        (0x061a, "handler_061a_bank1_a066"),
        (0x061f, "dispatch_061f_bank1"),
        (0x0624, "dispatch_0624_bank1"),
        (0x0629, "dispatch_0629_bank1"),
        (0x062e, "dispatch_062e_bank1"),
        (0x0633, "dispatch_0633_bank1"),
        (0x0638, "dispatch_0638_bank1"),
        (0x063d, "handler_063d"),
        (0x0642, "handler_0642_bank1_ef4e"),
        (0x0647, "dispatch_0647_bank1"),
        (0x064c, "dispatch_064c_bank1"),
        (0x0648, "init_data_table"),

        # =========================================================================
        # Flash / I2C / Utility Functions (0x0A00-0x0FFF)
        # =========================================================================
        (0x0be6, "write_xdata_reg"),
        (0x0c0f, "flash_div16"),
        (0x0c64, "flash_add_to_xdata16"),
        (0x0c7a, "flash_write_byte"),
        (0x0c87, "flash_write_idata"),
        (0x0c8f, "flash_write_r1_xdata"),
        (0x0d22, "reg_read_byte"),
        (0x0d33, "reg_read_word"),
        (0x0d46, "reg_read_dword"),
        (0x0d78, "idata_load_dword"),
        (0x0d84, "xdata_load_dword"),
        (0x0d90, "idata_load_dword_alt"),
        (0x0d9d, "xdata_load_triple"),
        (0x0db9, "idata_store_dword"),
        (0x0dc5, "xdata_store_dword"),
        (0x0dd1, "mul_add_index"),
        (0x0ddd, "reg_wait_bit_set"),
        (0x0de6, "reg_wait_bit_clear"),
        (0x0def, "reg_poll"),

        # =========================================================================
        # External Interrupt 0 Handler (0x0E00-0x11FF)
        # =========================================================================
        (0x0e5b, "ext0_isr"),
        (0x0e78, "usb_check_periph_status"),
        (0x0e96, "usb_ep_dispatch_loop"),
        (0x0f1c, "usb_endpoint_handler"),
        (0x0f2f, "usb_peripheral_handler"),
        (0x10e0, "usb_master_handler"),
        (0x11a2, "usb_ep_handler_11a2"),

        # =========================================================================
        # DMA / Transfer Functions (0x1500-0x1DFF)
        # =========================================================================
        (0x1579, "helper_1579"),
        (0x157d, "helper_157d"),
        (0x1580, "scsi_handler_1580"),
        (0x15d4, "helper_15d4"),
        (0x15ef, "helper_15ef"),
        (0x15f1, "helper_15f1"),
        (0x1602, "dma_write_to_scsi_ce6e"),
        (0x161a, "transfer_write_idata41_to_ce6e"),
        (0x163a, "dma_calc_scsi_index"),
        (0x1646, "transfer_calc_scsi_offset"),
        (0x1659, "dma_write_xdata_to_ce6e"),
        (0x1668, "dma_write_idata_to_ce6e"),
        (0x1677, "dma_write_ce86_to_ce6e"),
        (0x1687, "dma_read_xdata_from_ce6e"),
        (0x1696, "dma_wait_ce6c_ready"),
        (0x16ae, "dma_check_ce60_bit6"),
        (0x16b7, "dma_wait_bit0_and_return"),
        (0x16c3, "dma_check_and_clear_ce88"),
        (0x16de, "dma_add_to_counter"),
        (0x16e9, "dma_check_mode_and_param"),
        (0x16f3, "dma_clear_status"),
        (0x16ff, "dma_reg_wait_bit"),
        (0x1709, "dma_set_scsi_param3"),
        (0x1713, "dma_set_scsi_param1"),
        (0x171d, "dma_load_transfer_params"),
        (0x172c, "dma_check_state_counter"),
        (0x173b, "dma_clear_dword"),
        (0x1743, "usb_get_sys_status_offset"),
        (0x1752, "usb_calc_addr_with_offset"),
        (0x175d, "dma_init_channel_b8"),
        (0x176b, "usb_calc_queue_addr"),
        (0x1779, "usb_calc_queue_addr_next"),
        (0x1787, "usb_set_done_flag"),
        (0x178e, "dma_calc_addr_with_carry"),
        (0x1795, "dma_clear_state_counters"),
        (0x179d, "usb_calc_indexed_addr"),
        (0x17a9, "dma_init_ep_queue"),
        (0x17b5, "scsi_get_tag_count_status"),
        (0x17c1, "usb_read_queue_status_masked"),
        (0x17cd, "usb_shift_right_3"),
        (0x17d8, "dma_store_with_offset"),
        (0x17e3, "dma_load_with_offset"),
        (0x17ed, "dma_return_queue_value"),
        (0x17f3, "dma_shift_rrc2_mask"),
        (0x17fd, "dma_get_queue_index"),
        (0x180d, "dma_store_to_0a7d"),
        (0x1b07, "FUN_CODE_1b07"),
        (0x1b0b, "helper_1b0b"),
        (0x1b2e, "helper_1b2e"),
        (0x1b30, "helper_1b30"),
        (0x1b7e, "usb_enable"),
        (0x1b88, "usb_calc_addr_009f"),
        (0x1b96, "usb_get_ep_config_indexed"),
        (0x1b9a, "usb_read_buf_addr_pair"),
        (0x1ba5, "usb_read_buf_addr_pair_alt"),
        (0x1bae, "usb_get_idata_0x12_field"),
        (0x1bcb, "nvme_load_transfer_data"),
        (0x1bd7, "usb_setup_endpoint"),
        (0x1bde, "nvme_set_usb_mode_bit"),
        (0x1be8, "nvme_get_config_offset"),
        (0x1bf6, "nvme_calc_buffer_offset"),
        (0x1c0f, "nvme_calc_idata_offset"),
        (0x1c13, "helper_1c13"),
        (0x1c22, "nvme_check_scsi_ctrl"),
        (0x1c56, "nvme_get_dev_status_upper"),
        (0x1c6d, "nvme_subtract_idata_16"),
        (0x1c77, "nvme_get_cmd_param_upper"),
        (0x1c88, "nvme_calc_addr_01xx"),
        (0x1c9f, "nvme_get_cmd_length"),
        (0x1cae, "nvme_inc_circular_counter"),
        (0x1cb7, "nvme_calc_addr_012b"),
        (0x1cc1, "nvme_set_ep_queue_ctrl_84"),
        (0x1cc8, "helper_1cc8"),
        (0x1cd4, "nvme_clear_status_bit1"),
        (0x1cdc, "nvme_add_to_global_053a"),
        (0x1ce4, "nvme_calc_addr_04b7"),
        (0x1cfc, "usb_ep_config_bulk"),
        (0x1d07, "usb_ep_config_int"),
        (0x1d1d, "usb_set_transfer_flag"),
        (0x1d24, "nvme_get_data_ctrl_upper"),
        (0x1d2b, "nvme_set_data_ctrl_bit7"),
        (0x1d32, "nvme_store_idata_16"),
        (0x1d39, "usb_add_masked_counter"),
        (0x1d43, "usb_init_pcie_txn_state"),

        # =========================================================================
        # Protocol / State Machine Functions (0x2000-0x3FFF)
        # =========================================================================
        (0x2608, "handler_2608"),
        (0x23f7, "FUN_CODE_23f7"),
        (0x2814, "FUN_CODE_2814"),
        (0x2a10, "FUN_CODE_2a10"),
        (0x2db7, "FUN_CODE_2db7"),
        (0x2f67, "FUN_CODE_2f67"),
        (0x2f80, "main_loop"),
        (0x3023, "power_check_status"),
        (0x3031, "phy_poll_link_status"),
        (0x3094, "timer1_check_and_ack"),
        (0x312a, "usb_set_transfer_active_flag"),
        (0x313d, "usb_buffer_init"),
        (0x313f, "usb_buffer_setup"),
        (0x3147, "usb_copy_status_to_buffer"),
        (0x3168, "usb_clear_idata_indexed"),
        (0x3181, "usb_read_status_pair"),
        (0x31a5, "usb_read_transfer_params"),
        (0x31ad, "helper_31ad"),
        (0x31c3, "usb_setup_ep_params"),
        (0x31ce, "helper_31ce"),
        (0x31d5, "usb_status_helper_31d5"),
        (0x31e0, "usb_status_helper_31e0"),
        (0x31e2, "usb_status_helper_31e2"),
        (0x31ea, "usb_config_params"),
        (0x322e, "helper_322e"),
        (0x325f, "usb_status_helper_325f"),
        (0x328a, "helper_328a"),
        (0x3298, "helper_3298"),
        (0x3578, "helper_3578"),
        (0x36ab, "helper_36ab"),
        (0x3adb, "handler_3adb"),
        (0x3f4a, "protocol_state_machine"),

        # =========================================================================
        # SCSI / USB Mass Storage Functions (0x4000-0x55FF)
        # =========================================================================
        (0x4013, "scsi_setup_transfer_result"),
        (0x4042, "scsi_process_transfer"),
        (0x40d9, "scsi_state_handler_40d9"),
        (0x419d, "scsi_action_handler_419d"),
        (0x425f, "scsi_mode_setup_425f"),
        (0x431a, "main"),
        (0x4352, "process_init_table"),
        (0x43d3, "scsi_dma_handler_43d3"),
        (0x4469, "scsi_dma_start_4469"),
        (0x4486, "timer0_isr"),
        (0x44a3, "int_disable_ext0"),
        (0x44a7, "int_enable_system"),
        (0x44ba, "int_disable_ext1"),
        (0x44be, "int_enable_pcie"),
        (0x44d0, "int_enable_timer"),
        (0x44da, "int_disable_timer"),
        (0x4511, "int_ack_ext0"),
        (0x4532, "scsi_buffer_setup"),
        (0x45d0, "scsi_buffer_handler_45d0"),
        (0x466b, "scsi_transfer_check_466b"),
        (0x480c, "scsi_queue_handler_480c"),
        (0x4904, "scsi_csw_handler_4904"),
        (0x4977, "scsi_send_csw_4977"),
        (0x4a57, "dma_config_channel"),
        (0x4a94, "dma_start_transfer"),
        (0x4be6, "handler_4be6"),
        (0x4c40, "scsi_transfer_setup_4c40"),
        (0x4c98, "scsi_dma_setup_4c98"),
        (0x4d92, "scsi_dma_control_4d92"),
        (0x4e6d, "helper_4e6d"),
        (0x4f77, "helper_4f77"),
        (0x4fb6, "handler_4fb6"),
        (0x4fdb, "phy_poll_loop"),
        (0x4ff2, "core_handler_4ff2"),
        (0x5038, "FUN_CODE_5038"),
        (0x5043, "FUN_CODE_5043"),
        (0x5046, "FUN_CODE_5046"),
        (0x504f, "FUN_CODE_504f"),
        (0x505d, "FUN_CODE_505d"),
        (0x5069, "scsi_transfer_handler_5069"),
        (0x50db, "protocol_dispatch"),
        (0x5112, "scsi_copy_cbw_data_5112"),
        (0x519e, "scsi_uart_output_hex"),
        (0x51c7, "scsi_uart_hex_51c7"),
        (0x51ef, "scsi_uart_send"),
        (0x5216, "scsi_dma_ctrl_5216"),
        (0x523c, "dma_setup_transfer"),
        (0x5256, "buf_start_xfer_mode1"),
        (0x5260, "dma_check_scsi_status"),
        (0x5284, "phy_config_link_params"),
        (0x52a7, "usb_ep_process"),
        (0x52c7, "scsi_queue_dispatch_52c7"),
        (0x5305, "scsi_handler_5305"),
        (0x5321, "scsi_dma_param_5321"),
        (0x533d, "scsi_dma_status_533d"),
        (0x5359, "scsi_status_update_5359"),
        (0x5373, "scsi_transfer_check_5373"),
        (0x53a7, "helper_53a7"),
        (0x53c0, "scsi_write_residue_53c0"),
        (0x53e6, "scsi_ep_init_handler"),
        (0x5409, "usb_ep_init_handler"),
        (0x5418, "reg_set_bit_0"),
        (0x541f, "scsi_ep_check_541f"),
        (0x5442, "usb_ep_handler"),
        (0x545c, "power_phy_enable"),

        # =========================================================================
        # Lookup Tables (0x5A00-0x5CFF)
        # =========================================================================
        (0x5a6a, "ep_index_table"),
        (0x5b6a, "ep_bit_mask_table"),
        (0x5b72, "ep_offset_table"),
        (0x5c9d, "event_dispatch_table"),

        # =========================================================================
        # NVMe Functions (0x9500-0x9AFF)
        # =========================================================================
        (0x95ab, "nvme_queue_init_95ab"),
        (0x95af, "nvme_queue_setup_95af"),
        (0x95b6, "handler_95b6"),
        (0x95bf, "nvme_queue_config_95bf"),
        (0x95c2, "timer0_csr_ack"),
        (0x95c5, "nvme_queue_validate_95c5"),
        (0x95f9, "nvme_queue_handler_95f9"),
        (0x9605, "nvme_queue_ready_9605"),
        (0x9608, "nvme_queue_check_9608"),
        (0x960f, "nvme_queue_status_960f"),
        (0x9617, "nvme_queue_process_9617"),
        (0x9621, "nvme_queue_complete_9621"),
        (0x9627, "nvme_queue_advance_9627"),
        (0x962e, "nvme_queue_update_962e"),
        (0x9635, "nvme_queue_dispatch_9635"),
        (0x9647, "nvme_queue_handler_9647"),
        (0x964f, "nvme_queue_check_964f"),
        (0x9656, "nvme_queue_single_9656"),
        (0x9657, "nvme_queue_status_9657"),
        (0x965d, "nvme_queue_advance_965d"),
        (0x9664, "nvme_queue_process_9664"),
        (0x9677, "nvme_queue_validate_9677"),
        (0x9684, "nvme_queue_ready_9684"),
        (0x9687, "nvme_queue_config_9687"),
        (0x968c, "nvme_queue_single_968c"),
        (0x968f, "nvme_queue_handler_968f"),
        (0x969d, "nvme_queue_dispatch_969d"),
        (0x96a7, "nvme_queue_pair_96a7"),
        (0x96a9, "nvme_queue_status_96a9"),
        (0x96ae, "nvme_queue_check_96ae"),
        (0x96b8, "nvme_queue_complete_96b8"),
        (0x96bf, "nvme_queue_advance_96bf"),
        (0x96d4, "nvme_queue_pair_96d4"),
        (0x96d6, "nvme_queue_single_96d6"),
        (0x96d7, "nvme_queue_process_96d7"),
        (0x96ee, "nvme_queue_pair_96ee"),
        (0x96f7, "nvme_queue_handler_96f7"),
        (0x9703, "nvme_queue_dispatch_9703"),
        (0x9713, "nvme_queue_validate_9713"),
        (0x971e, "nvme_queue_config_971e"),
        (0x9729, "nvme_queue_complete_9729"),
        (0x9902, "pcie_init"),
        (0x990c, "pcie_init_alt"),
        (0x9916, "pcie_config_addr_9916"),
        (0x9923, "pcie_config_data_9923"),
        (0x9930, "pcie_config_setup_9930"),
        (0x9954, "pcie_config_read_9954"),
        (0x9962, "pcie_config_write_9962"),
        (0x996a, "pcie_config_wait_996a"),
        (0x9977, "pcie_config_done_9977"),
        (0x9980, "pcie_config_check_9980"),
        (0x998a, "pcie_config_status_998a"),
        (0x9996, "pcie_config_validate_9996"),
        (0x999d, "pcie_clear_and_trigger"),
        (0x99af, "pcie_trigger_and_wait"),
        (0x99bc, "pcie_wait_completion"),
        (0x99c6, "pcie_check_status"),
        (0x99eb, "pcie_get_completion_status"),
        (0x99f6, "pcie_set_idata_params"),
        (0x9a18, "pcie_setup_buffer_params"),
        (0x9a30, "pcie_set_byte_enables"),
        (0x9a33, "pcie_set_byte_enables_alt"),
        (0x9a53, "pcie_clear_reg_at_offset"),
        (0x9a60, "pcie_get_link_speed"),
        (0x9a74, "pcie_read_completion_data"),
        (0x9a7f, "pcie_wait_complete"),
        (0x9a8a, "pcie_inc_txn_counters"),
        (0x9a95, "pcie_write_status_complete"),
        (0x9a9c, "pcie_clear_address_regs"),
        (0x9aa9, "pcie_get_txn_count_hi"),

        # =========================================================================
        # Timer Functions (0xAD00-0xADFF)
        # =========================================================================
        (0xad72, "timer0_setup"),
        (0xad95, "timer0_wait_done"),
        (0xadb0, "pcie_set_address"),
        (0xadc3, "pcie_setup_config_tlp"),
        (0xae87, "pcie_check_completion"),
        (0xaf5e, "debug_output_handler"),

        # =========================================================================
        # Link/PHY Handlers (0xB000-0xBFFF)
        # =========================================================================
        (0xb031, "handler_b031"),
        (0xb10f, "flash_error_handler"),
        (0xb1a4, "flash_wait_and_poll"),
        (0xb1cb, "usb_power_init"),
        (0xb230, "error_state_handler"),
        (0xb4ba, "timer_tick_handler"),
        (0xb845, "flash_set_cmd"),
        (0xb85b, "flash_set_mode_bit4"),
        (0xb865, "flash_set_addr_md"),
        (0xb873, "flash_set_addr_hi"),
        (0xb888, "flash_set_data_len"),
        (0xb895, "flash_read_buffer_and_status"),
        (0xb8ae, "flash_set_mode_enable"),
        (0xb8c3, "handler_b8c3"),
        (0xbaa0, "flash_cmd_handler"),
        (0xbb37, "reg_clear_bits_and_init"),
        (0xbb4f, "reg_clear_bits_and_set_55"),
        (0xbb5e, "reg_read_and_xor"),
        (0xbb68, "reg_clear_and_set_bit0"),
        (0xbb75, "reg_clear_and_set_bit1"),
        (0xbb7e, "reg_set_bits_1_2"),
        (0xbb8f, "reg_read_masked"),
        (0xbb96, "reg_write_masked"),
        (0xbba0, "reg_set_bit5"),
        (0xbba8, "reg_set_bit6"),
        (0xbbaf, "reg_set_bit1"),
        (0xbbb6, "reg_clear_state_flags"),
        (0xbbc0, "reg_set_bit3"),
        (0xbbc7, "sys_init_helper_bbc7"),
        (0xbc70, "reg_clear_and_init_multi"),
        (0xbc88, "reg_set_indexed"),
        (0xbc8f, "handler_bc8f"),
        (0xbc98, "reg_clear_bit"),
        (0xbca5, "reg_set_bit"),
        (0xbcaf, "reg_toggle_bit"),
        (0xbcb1, "handler_bcb1"),
        (0xbcb8, "reg_read_triple"),
        (0xbcc4, "reg_write_triple"),
        (0xbcd0, "reg_inc_counter"),
        (0xbcd7, "reg_dec_counter"),
        (0xbcde, "reg_add_to_counter"),
        (0xbce7, "reg_sub_from_counter"),
        (0xbceb, "handler_bceb"),
        (0xbcf2, "reg_write_and_set_link_bit0"),
        (0xbd05, "reg_timer_setup_and_set_bits"),
        (0xbd14, "reg_timer_init_and_start"),
        (0xbd23, "reg_timer_clear_bits"),
        (0xbd2a, "handler_bd2a"),
        (0xbd33, "reg_set_bit5_generic"),
        (0xbd3a, "reg_clear_bits_5_6"),
        (0xbd41, "reg_set_bit6_generic"),
        (0xbd49, "handler_bd49"),
        (0xbd50, "reg_clear_bit1_cc3b"),
        (0xbd57, "reg_set_bit2"),
        (0xbd5e, "handler_bd5e"),
        (0xbd65, "reg_set_bit7"),
        (0xbe02, "dma_handler_be02"),
        (0xbe36, "flash_run_transaction"),
        (0xbe6a, "flash_txn_wait_status"),
        (0xbe70, "flash_poll_busy"),
        (0xbe77, "flash_txn_check_error"),
        (0xbe82, "flash_txn_complete"),
        (0xbe8b, "reg_init_and_set_bits"),
        (0xbefb, "reg_clear_state_flags_alt"),
        (0xbf04, "reg_restore_and_clear"),
        (0xbf8e, "handler_bf8e"),

        # =========================================================================
        # PCIe TLP Functions (0xC000-0xC2FF)
        # =========================================================================
        (0xc00d, "pcie_error_handler"),
        (0xc089, "pcie_handler_c089"),
        (0xc105, "handler_c105"),
        (0xc17f, "pcie_handler_c17f"),
        (0xc20c, "pcie_setup_memory_tlp"),
        (0xc244, "pcie_helper_c244"),
        (0xc245, "pcie_poll_and_read_completion"),
        (0xc247, "pcie_helper_c247"),
        (0xc2f4, "error_log_process"),
        (0xc32d, "error_status_update"),
        (0xc343, "error_log_and_process"),

        # =========================================================================
        # Error Log Functions (0xC400-0xC4FF)
        # =========================================================================
        (0xc445, "error_log_set_entry"),
        (0xc44f, "error_log_get_entry"),
        (0xc47f, "error_log_get_array_ptr"),
        (0xc48f, "error_log_get_array_ptr_2"),
        (0xc496, "error_log_check_counter"),
        (0xc4b3, "error_log_handler_c4b3"),
        (0xc523, "pcie_handler_c523"),
        (0xc593, "pcie_handler_c593"),
        (0xc66a, "phy_handler_c66a"),

        # =========================================================================
        # PHY Configuration Functions (0xCB00-0xCBFF)
        # =========================================================================
        (0xcb23, "power_ctrl_cb23"),
        (0xcb2d, "power_ctrl_cb2d"),
        (0xcb37, "power_ctrl_cb37"),
        (0xcb4b, "power_ctrl_cb4b"),
        (0xcb54, "phy_init_sequence"),
        (0xcb6f, "power_ctrl_cb6f"),
        (0xcb88, "power_ctrl_cb88"),

        # =========================================================================
        # Timer/Link Handlers (0xCE00-0xDFFF)
        # =========================================================================
        (0xcd10, "handler_cd10"),
        (0xcd6c, "handler_cd6c"),
        (0xcdc6, "handler_cdc6"),
        (0xce79, "timer_link_handler"),
        (0xcf28, "timer_config_handler"),
        (0xcf7f, "handler_cf7f"),
        (0xd07f, "handler_d07f"),
        (0xd0d3, "link_status_clear_handler"),
        (0xd127, "handler_d127"),
        (0xd1a8, "dma_poll_timeout_handler"),
        (0xd1cc, "handler_d1cc"),
        (0xd2bd, "handler_d2bd"),
        (0xd30b, "handler_d30b"),
        (0xd3a2, "handler_d3a2"),
        (0xd436, "handler_d436"),
        (0xd440, "handler_d440"),
        (0xd556, "handler_d556"),
        (0xd5a1, "handler_d5a1"),
        (0xd676, "handler_d676"),
        (0xd6bc, "handler_d6bc"),
        (0xd7cd, "handler_d7cd"),
        (0xd810, "usb_buffer_handler"),
        (0xd894, "phy_register_config"),
        (0xd916, "handler_d916"),
        (0xd996, "handler_d996"),
        (0xda30, "handler_da30"),
        (0xda51, "handler_da51"),
        (0xda8f, "handler_da8f"),
        (0xdace, "uart_read_byte_dace"),
        (0xdae2, "uart_read_status_dae2"),
        (0xdaeb, "uart_write_byte_daeb"),
        (0xdaf5, "uart_check_status_daf5"),
        (0xdaff, "uart_write_daff"),
        (0xdb80, "handler_db80"),
        (0xdbbb, "handler_dbbb"),
        (0xdbe7, "handler_dbe7"),
        (0xdbf5, "handler_dbf5"),
        (0xdd0e, "FUN_CODE_dd0e"),
        (0xdd12, "FUN_CODE_dd12"),
        (0xdd42, "handler_dd42"),
        (0xdd78, "handler_dd78"),
        (0xdd7e, "handler_dd7e"),
        (0xdde0, "handler_dde0"),
        (0xde16, "handler_de16"),
        (0xde7e, "pcie_init_internal"),
        (0xdea1, "handler_dea1"),
        (0xdee3, "handler_dee3"),
        (0xdf15, "handler_df15"),
        (0xdf79, "FUN_CODE_df79"),
        (0xdfdc, "handler_dfdc"),

        # =========================================================================
        # USB/Link Functions (0xE000-0xEFFF)
        # =========================================================================
        (0xe0c7, "handler_e0c7"),
        (0xe120, "FUN_CODE_e120"),
        (0xe14b, "handler_e14b"),
        (0xe1c6, "FUN_CODE_e1c6"),
        (0xe214, "handler_e214"),
        (0xe2a6, "handler_e2a6"),
        (0xe2ec, "handler_e2ec"),
        (0xe3b7, "handler_e3b7"),
        (0xe3d8, "handler_e3d8"),
        (0xe3f9, "flash_read_status"),
        (0xe4b4, "handler_e4b4"),
        (0xe4f0, "handler_e4f0"),
        (0xe50d, "handler_e50d"),
        (0xe529, "handler_e529"),
        (0xe56f, "event_state_handler"),
        (0xe57d, "handler_e57d"),
        (0xe597, "handler_e597"),
        (0xe617, "handler_e617"),
        (0xe62f, "handler_e62f"),
        (0xe647, "handler_e647"),
        (0xe65f, "handler_e65f"),
        (0xe677, "handler_e677"),
        (0xe6bd, "handler_e6bd"),
        (0xe6e7, "handler_e6e7"),
        (0xe6f0, "handler_e6f0"),
        (0xe6fc, "handler_e6fc"),
        (0xe73a, "FUN_CODE_e73a"),
        (0xe74e, "handler_e74e"),
        (0xe762, "handler_e762"),
        (0xe77a, "handler_e77a"),
        (0xe79b, "handler_e79b"),
        (0xe7ae, "FUN_CODE_e7ae"),
        (0xe7c1, "handler_e7c1"),
        (0xe80a, "delay_function"),
        (0xe84d, "handler_e84d"),
        (0xe85c, "handler_e85c"),
        (0xe883, "FUN_CODE_e883"),
        (0xe89b, "handler_e89b"),
        (0xe8a9, "handler_e8a9"),
        (0xe8d9, "handler_e8d9"),
        (0xe8e4, "handler_e8e4"),
        (0xe8ef, "handler_e8ef"),
        (0xe90b, "handler_e90b"),
        (0xe902, "handler_e902"),
        (0xe91d, "handler_e91d"),
        (0xe925, "handler_e925"),
        (0xe92c, "handler_e92c"),
        (0xe941, "handler_e941"),
        (0xe947, "handler_e947"),
        (0xe94d, "handler_e94d"),
        (0xe952, "handler_e952"),
        (0xe953, "handler_e953"),
        (0xe955, "handler_e955"),
        (0xe957, "sys_timer_handler_e957"),
        (0xe95b, "handler_e95b"),
        (0xe95d, "handler_e95d"),
        (0xe95f, "handler_e95f"),
        (0xe961, "handler_e961"),
        (0xe962, "handler_e962"),
        (0xe963, "handler_e963"),
        (0xe964, "handler_e964"),
        (0xe965, "handler_e965"),
        (0xe966, "handler_e966"),
        (0xe967, "handler_e967"),
        (0xe968, "handler_e968"),
        (0xe969, "handler_e969"),
        (0xe96a, "handler_e96a"),
        (0xe96b, "handler_e96b"),
        (0xe96c, "handler_e96c"),
        (0xe96e, "handler_e96e"),
        (0xe96f, "handler_e96f"),
        (0xe970, "handler_e970"),
        (0xe971, "reserved_stub"),
        (0xea19, "event_process_ea19"),
        (0xea7c, "handler_ea7c"),
    ]

    count = 0
    for addr_int, name in functions:
        try:
            # Bank 0 functions are in CODE space at their actual address
            addr = toAddr("CODE:{:04X}".format(addr_int))
            if create_function_if_needed(addr, name):
                count += 1
        except:
            try:
                addr = toAddr(addr_int)
                if create_function_if_needed(addr, name):
                    count += 1
            except Exception as e:
                print("Error adding Bank 0 function {} at 0x{:04X}: {}".format(name, addr_int, e))

    return count

def add_bank1_functions():
    """Add all known Bank 1 function names (file offset 0x10000-0x17FFF, CPU addr 0x8000-0xFFFF)"""

    # Bank 1 Function mappings: (file_offset, name)
    # File offset = CPU address + 0x8000 for addresses >= 0x8000
    # CPU addresses in Bank 1 are 0x8000-0xFFFF but mapped from file 0x10000-0x17FFF
    #
    # In Ghidra with CODE_BANK1 overlay:
    #   - Use file offset directly (0x10000+) OR
    #   - Use CPU addr + CODE_BANK1 overlay
    functions = [
        # =========================================================================
        # Bank 1 Entry Point
        # =========================================================================
        (0x10000, "bank1_entry"),  # File offset 0x10000 = CPU 0x8000

        # =========================================================================
        # Bank 1 Initialization (0x8D00-0x8FFF range, file 0x10D00-0x10FFF)
        # =========================================================================
        (0x10d77, "system_init_from_flash_8d77"),  # CPU 0x8D77

        # =========================================================================
        # Bank 1 Dispatch Handlers (0x89xx-0x9Dxx)
        # =========================================================================
        (0x109db, "handler_89db"),  # CPU 0x89DB
        (0x11d90, "handler_9d90"),  # CPU 0x9D90

        # =========================================================================
        # Bank 1 Error Handlers (0xA0xx-0xAFxx)
        # =========================================================================
        (0x12066, "error_handler_a066"),  # CPU 0xA066, called by handler_061a
        (0x12327, "handler_a327"),  # CPU 0xA327
        (0x1262d, "nvme_admin_handler_a62d"),  # CPU 0xA62D
        (0x12637, "nvme_admin_a637"),
        (0x12639, "nvme_admin_a639"),
        (0x1263c, "nvme_admin_a63c"),
        (0x1263d, "nvme_admin_a63d"),
        (0x12660, "nvme_admin_a660"),
        (0x12666, "nvme_admin_a666"),
        (0x1266d, "nvme_admin_a66d"),
        (0x12679, "nvme_admin_a679"),
        (0x12687, "nvme_admin_a687"),
        (0x12692, "nvme_admin_a692"),
        (0x1269a, "nvme_admin_a69a"),
        (0x126ad, "nvme_admin_a6ad"),
        (0x126c6, "nvme_admin_a6c6"),
        (0x126dc, "nvme_admin_a6dc"),
        (0x126ef, "nvme_admin_a6ef"),
        (0x126f6, "nvme_admin_a6f6"),
        (0x126fd, "nvme_admin_a6fd"),
        (0x1271b, "nvme_admin_a71b"),
        (0x1272b, "nvme_admin_a72b"),
        (0x12732, "nvme_admin_a732"),
        (0x12739, "nvme_admin_a739"),
        (0x12840, "handler_a840"),
        (0x12a2a, "nvme_queue_aa2a"),
        (0x12a30, "nvme_queue_aa30"),
        (0x12a33, "nvme_queue_aa33"),
        (0x12afb, "nvme_queue_aafb"),
        (0x12b0d, "nvme_queue_ab0d"),
        (0x12bc9, "handler_abc9"),  # CPU 0xABC9
        (0x12bd4, "nvme_setup_abd4"),
        (0x12bd7, "nvme_setup_abd7"),
        (0x12be9, "nvme_setup_abe9"),

        # =========================================================================
        # Bank 1 PCIe/Config Handlers (0xADxx-0xAFxx)
        # =========================================================================
        (0x12db0, "pcie_set_address_b1"),  # CPU 0xADB0
        (0x12dc3, "pcie_setup_config_tlp_b1"),  # CPU 0xADC3
        (0x12e87, "pcie_check_completion_b1"),  # CPU 0xAE87
        (0x12f5e, "debug_output_handler_b1"),  # CPU 0xAF5E

        # =========================================================================
        # Bank 1 Error State Handlers (0xB0xx-0xBFxx)
        # =========================================================================
        (0x13031, "handler_b031_b1"),
        (0x13230, "error_handler_b230"),  # CPU 0xB230, called by handler_0606
        (0x13349, "vendor_cmd_handler_b349"),
        (0x1343c, "vendor_info_handler_b43c"),
        (0x13473, "vendor_flash_handler_b473"),
        (0x13820, "nvme_init_b820"),
        (0x13825, "nvme_init_b825"),
        (0x13833, "nvme_init_b833"),
        (0x13838, "nvme_init_b838"),
        (0x13848, "nvme_init_b848"),
        (0x13850, "nvme_init_b850"),
        (0x13851, "nvme_init_b851"),
        (0x138b9, "nvme_init_b8b9"),
        (0x13c5e, "handler_bc5e"),
        (0x13d76, "handler_bd76"),

        # =========================================================================
        # Bank 1 Config/Status Handlers (0xC0xx-0xCFxx)
        # =========================================================================
        (0x140a5, "handler_c0a5"),  # CPU 0xC0A5
        (0x14440, "handler_d440_b1"),  # Note: this is file offset 0x14440
        (0x14556, "handler_d556_b1"),
        (0x1465f, "handler_c65f"),
        (0x148d5, "handler_d8d5"),
        (0x14ad9, "handler_dad9"),
        (0x14a52, "handler_ca52"),
        (0x14c9b, "handler_ec9b"),
        (0x1498d, "handler_c98d"),
        (0x14d1a, "handler_dd1a"),
        (0x14d7e, "handler_dd7e"),
        (0x14f5d, "vendor_dispatch_cf5d"),

        # =========================================================================
        # Bank 1 DMA/Transfer Handlers (0xD0xx-0xDFxx)
        # =========================================================================
        (0x15de0, "handler_dde0_b1"),
        (0x15e0d, "handler_e00d"),
        (0x15e1f, "handler_e01f"),
        (0x15e6b, "handler_e06b"),
        (0x15ed9, "handler_e0d9"),
        (0x1512b, "handler_e12b"),
        (0x15175, "handler_e175"),
        (0x151ee, "handler_e1ee"),
        (0x1525e, "handler_e25e"),
        (0x15282, "handler_e282"),
        (0x152c9, "handler_e2c9"),
        (0x15352, "handler_e352"),
        (0x15374, "handler_e374"),
        (0x15396, "handler_e396"),
        (0x15478, "handler_e478"),
        (0x15496, "handler_e496"),
        (0x154d2, "handler_e4d2"),
        (0x15545, "handler_e545"),
        (0x15561, "handler_e561"),
        (0x155cb, "handler_e5cb"),
        (0x15632, "handler_e632"),
        (0x1574e, "handler_e74e_b1"),
        (0x157fb, "handler_e7fb"),
        (0x15890, "handler_e890"),
        (0x1589b, "handler_e89b_b1"),

        # =========================================================================
        # Bank 1 Event Handlers (0xE5xx-0xEFxx)
        # =========================================================================
        (0x1656f, "event_handler_e56f"),  # CPU 0xE56F, called by handler_0494
        (0x16677, "handler_e677_b1"),
        (0x166f0, "handler_e6f0"),
        (0x16762, "handler_e762_b1"),
        (0x16911, "error_handler_e911"),  # CPU 0xE911, called by handler_0570
        (0x16920, "error_clear_e760_flags"),  # CPU 0xE920
        (0x16ce1, "handler_ece1"),
        (0x16d02, "handler_ed02"),  # CPU 0xED02
        (0x16d06, "handler_ed06"),
        (0x16d0b, "handler_ed0b"),
        (0x16d19, "handler_ed19"),
        (0x16dbd, "handler_edbd"),
        (0x16e11, "handler_ee11"),
        (0x16ed6, "handler_eed6"),
        (0x16ef9, "handler_eef9"),  # CPU 0xEEF9
        (0x16f1e, "handler_ef1e"),
        (0x16f24, "handler_ef24"),
        (0x16f3e, "handler_ef3e"),
        (0x16f42, "handler_ef42"),
        (0x16f46, "handler_ef46"),
        (0x16f4e, "error_handler_ef4e"),  # CPU 0xEF4E, called by handler_0642 (NOPs)

        # =========================================================================
        # Bank 1 UART/Debug (0xDA00-0xDAFF)
        # =========================================================================
        (0x15acc, "uart_read_dacc"),
        (0x15ace, "uart_read_byte_dace_b1"),
        (0x15ae2, "uart_read_status_dae2_b1"),
        (0x15aeb, "uart_write_byte_daeb_b1"),
        (0x15af5, "uart_check_status_daf5_b1"),
        (0x15aff, "uart_write_daff_b1"),
        (0x1621b, "vendor_status_e21b"),
    ]

    count = 0
    for file_offset, name in functions:
        try:
            # Try CODE_BANK1 overlay first (file offset directly)
            addr = toAddr("CODE_BANK1:{:04X}".format(file_offset & 0xFFFF))
            if create_function_if_needed(addr, name):
                count += 1
        except:
            try:
                # Try direct file offset
                addr = toAddr(file_offset)
                if create_function_if_needed(addr, name):
                    count += 1
            except Exception as e:
                print("Error adding Bank 1 function {} at file offset 0x{:05X}: {}".format(name, file_offset, e))

    return count

def add_registers():
    """Add all known register labels to EXTMEM space"""

    # Register mappings: (address, name)
    # These are hardware registers (>= 0x6000)
    registers = [
        # =========================================================================
        # USB Interface Registers (0x9000-0x93FF)
        # =========================================================================
        (0x9000, "REG_USB_STATUS"),
        (0x9001, "REG_USB_CONTROL"),
        (0x9002, "REG_USB_CONFIG"),
        (0x9003, "REG_USB_EP0_STATUS"),
        (0x9004, "REG_USB_EP0_LEN_L"),
        (0x9005, "REG_USB_EP0_LEN_H"),
        (0x9006, "REG_USB_EP0_CONFIG"),
        (0x9007, "REG_USB_SCSI_BUF_LEN_L"),
        (0x9008, "REG_USB_SCSI_BUF_LEN_H"),
        (0x900B, "REG_USB_MSC_CFG"),
        (0x9010, "REG_USB_DATA_L"),
        (0x9011, "REG_USB_DATA_H"),
        (0x9012, "REG_USB_FIFO_L"),
        (0x9013, "REG_USB_FIFO_H"),
        (0x9018, "REG_USB_MODE_9018"),
        (0x9019, "REG_USB_MODE_VAL_9019"),
        (0x901A, "REG_USB_MSC_LENGTH"),
        (0x905B, "REG_USB_EP_BUF_HI"),
        (0x905C, "REG_USB_EP_BUF_LO"),
        (0x905E, "REG_USB_EP_CTRL_905E"),
        (0x9091, "REG_INT_FLAGS_EX0"),
        (0x9093, "REG_USB_EP_CFG1"),
        (0x9094, "REG_USB_EP_CFG2"),
        (0x9096, "REG_USB_EP_READY"),
        (0x909E, "REG_USB_STATUS_909E"),
        (0x90A1, "REG_USB_SIGNAL_90A1"),
        (0x90E0, "REG_USB_SPEED"),
        (0x90E2, "REG_USB_MODE"),
        (0x90E3, "REG_USB_EP_STATUS_90E3"),
        (0x9100, "REG_USB_LINK_STATUS"),
        (0x9101, "REG_USB_PERIPH_STATUS"),
        (0x910D, "REG_USB_STATUS_0D"),
        (0x910E, "REG_USB_STATUS_0E"),
        (0x9118, "REG_USB_EP_STATUS"),
        (0x911B, "REG_USB_BUFFER_ALT"),
        (0x911D, "REG_USB_DATA_911D"),
        (0x911E, "REG_USB_DATA_911E"),
        (0x911F, "REG_USB_STATUS_1F"),
        (0x9120, "REG_USB_STATUS_20"),
        (0x9121, "REG_USB_STATUS_21"),
        (0x9122, "REG_USB_STATUS_22"),
        (0x9123, "REG_CBW_TAG_3"),
        (0x91C0, "REG_USB_PHY_CTRL_91C0"),
        (0x91C1, "REG_USB_PHY_CTRL_91C1"),
        (0x91C3, "REG_USB_PHY_CTRL_91C3"),
        (0x91D0, "REG_USB_EP_CTRL_91D0"),
        (0x91D1, "REG_USB_PHY_CTRL_91D1"),
        (0x9201, "REG_USB_CTRL_9201"),
        (0x920C, "REG_USB_CTRL_920C"),
        (0x9241, "REG_USB_PHY_CONFIG_9241"),

        # =========================================================================
        # Power Management (0x92C0-0x92E8)
        # =========================================================================
        (0x92C0, "REG_POWER_ENABLE"),
        (0x92C1, "REG_CLOCK_ENABLE"),
        (0x92C2, "REG_POWER_STATUS"),
        (0x92C4, "REG_POWER_CTRL_92C4"),
        (0x92C5, "REG_PHY_POWER"),
        (0x92C6, "REG_POWER_CTRL_92C6"),
        (0x92C7, "REG_POWER_CTRL_92C7"),
        (0x92C8, "REG_POWER_CTRL_92C8"),
        (0x92E0, "REG_POWER_DOMAIN"),

        # =========================================================================
        # Buffer Configuration (0x9300-0x93FF)
        # =========================================================================
        (0x9300, "REG_BUF_CFG_9300"),
        (0x9301, "REG_BUF_CFG_9301"),
        (0x9302, "REG_BUF_CFG_9302"),
        (0x9303, "REG_BUF_CFG_9303"),
        (0x9304, "REG_BUF_CFG_9304"),
        (0x9305, "REG_BUF_CFG_9305"),

        # =========================================================================
        # PCIe Passthrough (0xB200-0xB4FF)
        # =========================================================================
        (0xB210, "REG_PCIE_FMT_TYPE"),
        (0xB213, "REG_PCIE_TLP_CTRL"),
        (0xB216, "REG_PCIE_TLP_LENGTH"),
        (0xB217, "REG_PCIE_BYTE_EN"),
        (0xB218, "REG_PCIE_ADDR_0"),
        (0xB219, "REG_PCIE_ADDR_1"),
        (0xB21A, "REG_PCIE_ADDR_2"),
        (0xB21B, "REG_PCIE_ADDR_3"),
        (0xB21C, "REG_PCIE_ADDR_HIGH"),
        (0xB220, "REG_PCIE_DATA"),
        (0xB224, "REG_PCIE_TLP_CPL_HEADER"),
        (0xB22A, "REG_PCIE_LINK_STATUS"),
        (0xB22B, "REG_PCIE_CPL_STATUS"),
        (0xB22C, "REG_PCIE_CPL_DATA"),
        (0xB22D, "REG_PCIE_CPL_DATA_ALT"),
        (0xB250, "REG_PCIE_NVME_DOORBELL"),
        (0xB254, "REG_PCIE_TRIGGER"),
        (0xB255, "REG_PCIE_PM_ENTER"),
        (0xB284, "REG_PCIE_COMPL_STATUS"),
        (0xB296, "REG_PCIE_STATUS"),
        (0xB402, "REG_PCIE_CTRL_B402"),
        (0xB424, "REG_PCIE_LANE_COUNT"),
        (0xB480, "REG_PCIE_LINK_CTRL"),
        (0xB4AE, "REG_PCIE_LINK_STATUS_ALT"),
        (0xB4C8, "REG_PCIE_LANE_MASK"),
        (0xB80C, "REG_PCIE_QUEUE_INDEX_LO"),
        (0xB80D, "REG_PCIE_QUEUE_INDEX_HI"),
        (0xB80E, "REG_PCIE_QUEUE_FLAGS_LO"),
        (0xB80F, "REG_PCIE_QUEUE_FLAGS_HI"),

        # =========================================================================
        # UART Controller (0xC000-0xC00F)
        # =========================================================================
        (0xC000, "REG_UART_BASE"),
        (0xC001, "REG_UART_THR_RBR"),
        (0xC002, "REG_UART_IER"),
        (0xC004, "REG_UART_FCR_IIR"),
        (0xC006, "REG_UART_TFBF"),
        (0xC007, "REG_UART_LCR"),
        (0xC008, "REG_UART_MCR"),
        (0xC009, "REG_UART_LSR"),
        (0xC00A, "REG_UART_MSR"),

        # =========================================================================
        # Link/PHY Control (0xC200-0xC2FF)
        # =========================================================================
        (0xC202, "REG_LINK_CTRL"),
        (0xC203, "REG_LINK_CONFIG"),
        (0xC204, "REG_LINK_STATUS"),
        (0xC205, "REG_PHY_CTRL"),
        (0xC208, "REG_PHY_LINK_CTRL_C208"),
        (0xC20C, "REG_PHY_LINK_CONFIG_C20C"),
        (0xC233, "REG_PHY_CONFIG"),
        (0xC284, "REG_PHY_STATUS"),

        # =========================================================================
        # NVMe Interface (0xC400-0xC5FF)
        # =========================================================================
        (0xC400, "REG_NVME_CTRL"),
        (0xC401, "REG_NVME_STATUS"),
        (0xC412, "REG_NVME_CTRL_STATUS"),
        (0xC413, "REG_NVME_CONFIG"),
        (0xC414, "REG_NVME_DATA_CTRL"),
        (0xC415, "REG_NVME_DEV_STATUS"),
        (0xC420, "REG_NVME_CMD"),
        (0xC421, "REG_NVME_CMD_OPCODE"),
        (0xC422, "REG_NVME_LBA_LOW"),
        (0xC423, "REG_NVME_LBA_MID"),
        (0xC424, "REG_NVME_LBA_HIGH"),
        (0xC425, "REG_NVME_COUNT_LOW"),
        (0xC426, "REG_NVME_COUNT_HIGH"),
        (0xC427, "REG_NVME_ERROR"),
        (0xC428, "REG_NVME_QUEUE_CFG"),
        (0xC429, "REG_NVME_CMD_PARAM"),
        (0xC42A, "REG_NVME_DOORBELL"),
        (0xC42B, "REG_NVME_CMD_FLAGS"),
        (0xC42C, "REG_USB_MSC_CTRL"),
        (0xC42D, "REG_USB_MSC_STATUS"),
        (0xC431, "REG_NVME_CMD_PRP2"),
        (0xC435, "REG_NVME_CMD_CDW10"),
        (0xC438, "REG_NVME_INIT_CTRL"),
        (0xC439, "REG_NVME_CMD_CDW11"),
        (0xC43D, "REG_NVME_QUEUE_PTR"),
        (0xC43E, "REG_NVME_QUEUE_DEPTH"),
        (0xC43F, "REG_NVME_PHASE"),
        (0xC440, "REG_NVME_QUEUE_CTRL"),
        (0xC441, "REG_NVME_SQ_HEAD"),
        (0xC442, "REG_NVME_SQ_TAIL"),
        (0xC443, "REG_NVME_CQ_HEAD"),
        (0xC444, "REG_NVME_CQ_TAIL"),
        (0xC445, "REG_NVME_CQ_STATUS"),
        (0xC446, "REG_NVME_LBA_3"),
        (0xC448, "REG_NVME_INIT_CTRL2"),
        (0xC450, "REG_NVME_CMD_STATUS_50"),
        (0xC451, "REG_NVME_QUEUE_STATUS_51"),
        (0xC462, "REG_DMA_ENTRY"),
        (0xC470, "REG_CMDQ_DIR_END"),
        (0xC471, "REG_NVME_QUEUE_PTR_C471"),
        (0xC472, "REG_NVME_LINK_CTRL"),
        (0xC4ED, "REG_NVME_DMA_CTRL_ED"),
        (0xC4EE, "REG_NVME_DMA_ADDR_LO"),
        (0xC4EF, "REG_NVME_DMA_ADDR_HI"),
        (0xC508, "REG_NVME_BUF_CFG"),
        (0xC512, "REG_NVME_QUEUE_INDEX"),
        (0xC516, "REG_NVME_QUEUE_C516"),
        (0xC51A, "REG_NVME_QUEUE_TRIGGER"),
        (0xC51E, "REG_NVME_QUEUE_STATUS"),
        (0xC520, "REG_NVME_LINK_STATUS"),

        # =========================================================================
        # PHY Extended (0xC600-0xC6FF)
        # =========================================================================
        (0xC62D, "REG_PHY_EXT_2D"),
        (0xC656, "REG_PHY_EXT_56"),
        (0xC65B, "REG_PHY_EXT_5B"),
        (0xC6B3, "REG_PHY_EXT_B3"),

        # =========================================================================
        # Interrupt Controller (0xC800-0xC80F)
        # =========================================================================
        (0xC801, "REG_INT_CTRL_C801"),
        (0xC802, "REG_INT_USB_MASTER"),
        (0xC805, "REG_INT_AUX_C805"),
        (0xC806, "REG_INT_SYSTEM"),
        (0xC809, "REG_INT_CTRL_C809"),
        (0xC80A, "REG_INT_PCIE_NVME"),

        # =========================================================================
        # I2C Controller (0xC870-0xC87F)
        # =========================================================================
        (0xC870, "REG_I2C_ADDR"),
        (0xC871, "REG_I2C_MODE"),
        (0xC873, "REG_I2C_LEN"),
        (0xC875, "REG_I2C_CSR"),
        (0xC878, "REG_I2C_SRC"),
        (0xC87C, "REG_I2C_DST"),
        (0xC87F, "REG_I2C_CSR_ALT"),

        # =========================================================================
        # SPI Flash Controller (0xC89F-0xC8AF)
        # =========================================================================
        (0xC89F, "REG_FLASH_CON"),
        (0xC8A1, "REG_FLASH_ADDR_LO"),
        (0xC8A2, "REG_FLASH_ADDR_MD"),
        (0xC8A3, "REG_FLASH_DATA_LEN"),
        (0xC8A4, "REG_FLASH_DATA_LEN_HI"),
        (0xC8A6, "REG_FLASH_DIV"),
        (0xC8A9, "REG_FLASH_CSR"),
        (0xC8AA, "REG_FLASH_CMD"),
        (0xC8AB, "REG_FLASH_ADDR_HI"),
        (0xC8AC, "REG_FLASH_ADDR_LEN"),
        (0xC8AD, "REG_FLASH_MODE"),
        (0xC8AE, "REG_FLASH_BUF_OFFSET"),

        # =========================================================================
        # DMA Engine (0xC8B0-0xC8D9)
        # =========================================================================
        (0xC8B0, "REG_DMA_MODE"),
        (0xC8B2, "REG_DMA_CHAN_AUX"),
        (0xC8B3, "REG_DMA_CHAN_AUX1"),
        (0xC8B4, "REG_DMA_XFER_CNT_HI"),
        (0xC8B5, "REG_DMA_XFER_CNT_LO"),
        (0xC8B6, "REG_DMA_CHAN_CTRL2"),
        (0xC8B7, "REG_DMA_CHAN_STATUS2"),
        (0xC8B8, "REG_DMA_TRIGGER"),
        (0xC8D4, "REG_DMA_CONFIG"),
        (0xC8D5, "REG_DMA_QUEUE_IDX"),
        (0xC8D6, "REG_DMA_STATUS"),
        (0xC8D7, "REG_DMA_CTRL"),
        (0xC8D8, "REG_DMA_STATUS2"),
        (0xC8D9, "REG_DMA_STATUS3"),

        # =========================================================================
        # CPU Mode/Control (0xCA00-0xCAFF)
        # =========================================================================
        (0xCA06, "REG_CPU_MODE_NEXT"),
        (0xCA81, "REG_CA81"),

        # =========================================================================
        # Timer Registers (0xCC10-0xCC24)
        # =========================================================================
        (0xCC10, "REG_TIMER0_DIV"),
        (0xCC11, "REG_TIMER0_CSR"),
        (0xCC12, "REG_TIMER0_THRESHOLD"),
        (0xCC16, "REG_TIMER1_DIV"),
        (0xCC17, "REG_TIMER1_CSR"),
        (0xCC18, "REG_TIMER1_THRESHOLD"),
        (0xCC1C, "REG_TIMER2_DIV"),
        (0xCC1D, "REG_TIMER2_CSR"),
        (0xCC1E, "REG_TIMER2_THRESHOLD"),
        (0xCC22, "REG_TIMER3_DIV"),
        (0xCC23, "REG_TIMER3_CSR"),
        (0xCC24, "REG_TIMER3_IDLE_TIMEOUT"),

        # =========================================================================
        # CPU Control Extended (0xCC30-0xCCFF)
        # =========================================================================
        (0xCC30, "REG_CPU_CTRL_CC30"),
        (0xCC31, "REG_CPU_EXEC_CTRL"),
        (0xCC32, "REG_CPU_EXEC_STATUS"),
        (0xCC33, "REG_CPU_EXEC_STATUS_2"),
        (0xCC38, "REG_CPU_CTRL_CC38"),
        (0xCC3A, "REG_CPU_CTRL_CC3A"),
        (0xCC3B, "REG_CPU_CTRL_CC3B"),
        (0xCC3D, "REG_CPU_CTRL_CC3D"),
        (0xCC3E, "REG_CPU_CTRL_CC3E"),
        (0xCC3F, "REG_CPU_CTRL_CC3F"),
        (0xCC81, "REG_CPU_STATUS_CC81"),
        (0xCC91, "REG_CPU_STATUS_CC91"),
        (0xCC98, "REG_CPU_STATUS_CC98"),
        (0xCCD8, "REG_CPU_DMA_CCD8"),
        (0xCCDA, "REG_CPU_DMA_CCDA"),
        (0xCCDB, "REG_CPU_DMA_CCDB"),

        # =========================================================================
        # SCSI DMA Control (0xCE00-0xCE97)
        # =========================================================================
        (0xCE00, "REG_SCSI_DMA_CTRL"),
        (0xCE01, "REG_SCSI_DMA_PARAM"),
        (0xCE36, "REG_SCSI_DMA_CFG_CE36"),
        (0xCE3A, "REG_SCSI_DMA_TAG_CE3A"),
        (0xCE40, "REG_SCSI_DMA_PARAM0"),
        (0xCE41, "REG_SCSI_DMA_PARAM1"),
        (0xCE42, "REG_SCSI_DMA_PARAM2"),
        (0xCE43, "REG_SCSI_DMA_PARAM3"),
        (0xCE44, "REG_SCSI_DMA_PARAM4"),
        (0xCE45, "REG_SCSI_DMA_PARAM5"),
        (0xCE5C, "REG_SCSI_DMA_COMPL"),
        (0xCE60, "REG_XFER_STATUS_CE60"),
        (0xCE65, "REG_XFER_CTRL_CE65"),
        (0xCE66, "REG_SCSI_DMA_TAG_COUNT"),
        (0xCE67, "REG_SCSI_DMA_QUEUE_STAT"),
        (0xCE6C, "REG_XFER_STATUS_CE6C"),
        (0xCE6E, "REG_SCSI_DMA_STATUS"),
        (0xCE70, "REG_SCSI_TRANSFER_CTRL"),
        (0xCE72, "REG_SCSI_TRANSFER_MODE"),
        (0xCE73, "REG_SCSI_BUF_CTRL0"),
        (0xCE74, "REG_SCSI_BUF_CTRL1"),
        (0xCE75, "REG_SCSI_BUF_LEN_LO"),
        (0xCE76, "REG_SCSI_BUF_ADDR0"),
        (0xCE77, "REG_SCSI_BUF_ADDR1"),
        (0xCE78, "REG_SCSI_BUF_ADDR2"),
        (0xCE79, "REG_SCSI_BUF_ADDR3"),
        (0xCE80, "REG_SCSI_CMD_LIMIT_LO"),
        (0xCE81, "REG_SCSI_CMD_LIMIT_HI"),
        (0xCE82, "REG_SCSI_CMD_MODE"),
        (0xCE83, "REG_SCSI_CMD_FLAGS"),
        (0xCE86, "REG_XFER_STATUS_CE86"),
        (0xCE88, "REG_XFER_CTRL_CE88"),
        (0xCE89, "REG_XFER_READY"),
        (0xCE95, "REG_XFER_MODE_CE95"),
        (0xCE96, "REG_SCSI_DMA_CMD_REG"),
        (0xCE97, "REG_SCSI_DMA_RESP_REG"),

        # =========================================================================
        # USB Descriptor Validation (0xCEB0-0xCEB3)
        # =========================================================================
        (0xCEB2, "REG_USB_DESC_VAL_CEB2"),
        (0xCEB3, "REG_USB_DESC_VAL_CEB3"),

        # =========================================================================
        # CPU Link Control (0xCEF0-0xCEFF)
        # =========================================================================
        (0xCEF2, "REG_CPU_LINK_CEF2"),
        (0xCEF3, "REG_CPU_LINK_CEF3"),

        # =========================================================================
        # USB Endpoint Buffer (0xD800-0xD810)
        # =========================================================================
        (0xD800, "REG_USB_EP_BUF_CTRL"),
        (0xD801, "REG_USB_EP_BUF_SEL"),
        (0xD802, "REG_USB_EP_BUF_DATA"),
        (0xD803, "REG_USB_EP_BUF_PTR_LO"),
        (0xD804, "REG_USB_EP_BUF_PTR_HI"),
        (0xD805, "REG_USB_EP_BUF_LEN_LO"),
        (0xD806, "REG_USB_EP_BUF_STATUS"),
        (0xD807, "REG_USB_EP_BUF_LEN_HI"),
        (0xD808, "REG_USB_EP_RESIDUE0"),
        (0xD809, "REG_USB_EP_RESIDUE1"),
        (0xD80A, "REG_USB_EP_RESIDUE2"),
        (0xD80B, "REG_USB_EP_RESIDUE3"),
        (0xD80C, "REG_USB_EP_CSW_STATUS"),
        (0xD80D, "REG_USB_EP_CTRL_0D"),
        (0xD80E, "REG_USB_EP_CTRL_0E"),
        (0xD80F, "REG_USB_EP_CTRL_0F"),
        (0xD810, "REG_USB_EP_CTRL_10"),

        # =========================================================================
        # PHY Completion / Debug (0xE300-0xE3FF)
        # =========================================================================
        (0xE302, "REG_PHY_MODE_E302"),
        (0xE314, "REG_DEBUG_STATUS_E314"),
        (0xE318, "REG_PHY_COMPLETION_E318"),
        (0xE324, "REG_LINK_CTRL_E324"),

        # =========================================================================
        # Command Engine (0xE400-0xE4FF)
        # =========================================================================
        (0xE402, "REG_CMD_STATUS_E402"),
        (0xE403, "REG_CMD_CTRL_E403"),
        (0xE40B, "REG_CMD_CONFIG"),
        (0xE40F, "REG_CMD_CTRL_E40F"),
        (0xE410, "REG_CMD_CTRL_E410"),
        (0xE41C, "REG_CMD_BUSY_STATUS"),
        (0xE420, "REG_CMD_TRIGGER"),
        (0xE422, "REG_CMD_PARAM"),
        (0xE423, "REG_CMD_STATUS"),
        (0xE424, "REG_CMD_ISSUE"),
        (0xE425, "REG_CMD_TAG"),
        (0xE426, "REG_CMD_LBA_0"),
        (0xE427, "REG_CMD_LBA_1"),
        (0xE428, "REG_CMD_LBA_2"),
        (0xE429, "REG_CMD_LBA_3"),
        (0xE42A, "REG_CMD_COUNT_LOW"),
        (0xE42B, "REG_CMD_COUNT_HIGH"),
        (0xE42C, "REG_CMD_LENGTH_LOW"),
        (0xE42D, "REG_CMD_LENGTH_HIGH"),
        (0xE42E, "REG_CMD_RESP_TAG"),
        (0xE42F, "REG_CMD_RESP_STATUS"),
        (0xE430, "REG_CMD_CTRL"),
        (0xE431, "REG_CMD_TIMEOUT"),
        (0xE432, "REG_CMD_PARAM_L"),
        (0xE433, "REG_CMD_PARAM_H"),

        # =========================================================================
        # Debug/Interrupt (0xE600-0xE6FF)
        # =========================================================================
        (0xE62F, "REG_DEBUG_INT_E62F"),
        (0xE65F, "REG_DEBUG_INT_E65F"),
        (0xE661, "REG_DEBUG_INT_E661"),

        # =========================================================================
        # System Status / Link Control (0xE700-0xE7FF)
        # =========================================================================
        (0xE710, "REG_LINK_WIDTH_E710"),
        (0xE712, "REG_LINK_STATUS_E712"),
        (0xE716, "REG_LINK_STATUS_E716"),
        (0xE717, "REG_LINK_CTRL_E717"),
        (0xE760, "REG_SYS_CTRL_E760"),
        (0xE761, "REG_SYS_CTRL_E761"),
        (0xE763, "REG_SYS_CTRL_E763"),
        (0xE795, "REG_FLASH_READY_STATUS"),
        (0xE7E3, "REG_PHY_LINK_CTRL"),
        (0xE7FC, "REG_LINK_MODE_CTRL"),

        # =========================================================================
        # NVMe Event (0xEC00-0xEC0F)
        # =========================================================================
        (0xEC04, "REG_NVME_EVENT_ACK"),
        (0xEC06, "REG_NVME_EVENT_STATUS"),

        # =========================================================================
        # System Control (0xEF00-0xEFFF)
        # =========================================================================
        (0xEF4E, "REG_CRITICAL_CTRL"),
    ]

    count = 0
    for addr_int, name in registers:
        try:
            # Try EXTMEM space first
            addr = toAddr("EXTMEM:{:04X}".format(addr_int))
            if create_label(addr, name):
                count += 1
        except:
            try:
                # Fall back to direct address
                addr = toAddr(addr_int)
                if create_label(addr, name):
                    count += 1
            except Exception as e:
                print("Error adding register {} at 0x{:04X}: {}".format(name, addr_int, e))

    return count

def add_globals():
    """Add all known global variable labels to EXTMEM space"""

    # Global variable mappings: (address, name)
    # These are RAM locations (< 0x6000)
    globals_list = [
        # =========================================================================
        # System Work Area (0x0000-0x01FF)
        # =========================================================================
        (0x0000, "G_SYSTEM_CTRL"),
        (0x0001, "G_IO_CMD_TYPE"),
        (0x0002, "G_IO_CMD_STATE"),
        (0x0003, "G_EP_STATUS_CTRL"),
        (0x0007, "G_WORK_0007"),
        (0x000A, "G_EP_CHECK_FLAG"),
        (0x002D, "G_STATE_WORK_002D"),
        (0x0052, "G_SYS_FLAGS_0052"),
        (0x0054, "G_BUFFER_LENGTH_HIGH"),
        (0x0055, "G_NVME_QUEUE_READY"),
        (0x0056, "G_USB_ADDR_HI_0056"),
        (0x0057, "G_USB_ADDR_LO_0057"),
        (0x00C2, "G_INIT_STATE_00C2"),
        (0x00E5, "G_INIT_STATE_00E5"),
        (0x014E, "G_USB_INDEX_COUNTER"),
        (0x0171, "G_SCSI_CTRL"),
        (0x01B4, "G_USB_WORK_01B4"),

        # =========================================================================
        # DMA Work Area (0x0200-0x02FF)
        # =========================================================================
        (0x0203, "G_DMA_MODE_SELECT"),
        (0x020D, "G_DMA_PARAM1"),
        (0x020E, "G_DMA_PARAM2"),
        (0x0213, "G_FLASH_READ_TRIGGER"),
        (0x0214, "G_EVENT_RETURN_VALUE"),
        (0x0216, "G_DMA_WORK_0216"),
        (0x0217, "G_DMA_OFFSET"),
        (0x0218, "G_BUF_ADDR_HI"),
        (0x0219, "G_BUF_ADDR_LO"),
        (0x021A, "G_BUF_BASE_HI"),
        (0x021B, "G_BUF_BASE_LO"),
        (0x023F, "G_BANK1_STATE_023F"),

        # =========================================================================
        # System Status Work Area (0x0400-0x04FF)
        # =========================================================================
        (0x044B, "G_LOG_COUNTER_044B"),
        (0x044C, "G_LOG_ACTIVE_044C"),
        (0x044D, "G_LOG_INIT_044D"),
        (0x045E, "G_REG_WAIT_BIT"),
        (0x0464, "G_SYS_STATUS_PRIMARY"),
        (0x0465, "G_SYS_STATUS_SECONDARY"),
        (0x0466, "G_SYSTEM_CONFIG"),
        (0x0467, "G_SYSTEM_STATE"),
        (0x0468, "G_DATA_PORT"),
        (0x0469, "G_INT_STATUS"),
        (0x0472, "G_DMA_LOAD_PARAM1"),
        (0x0473, "G_DMA_LOAD_PARAM2"),
        (0x0474, "G_STATE_HELPER_41"),
        (0x0475, "G_STATE_HELPER_42"),

        # =========================================================================
        # Endpoint Configuration Work Area (0x0500-0x05FF)
        # =========================================================================
        (0x0517, "G_EP_INIT_0517"),
        (0x053A, "G_NVME_PARAM_053A"),
        (0x053B, "G_NVME_STATE_053B"),
        (0x053D, "G_SCSI_CMD_TYPE"),
        (0x053E, "G_SCSI_TRANSFER_FLAG"),
        (0x053F, "G_SCSI_BUF_LEN_0"),
        (0x0540, "G_SCSI_BUF_LEN_1"),
        (0x0541, "G_SCSI_BUF_LEN_2"),
        (0x0542, "G_SCSI_BUF_LEN_3"),
        (0x0543, "G_SCSI_LBA_0"),
        (0x0544, "G_SCSI_LBA_1"),
        (0x0545, "G_SCSI_LBA_2"),
        (0x0546, "G_SCSI_LBA_3"),
        (0x0547, "G_SCSI_DEVICE_IDX"),
        (0x054B, "G_EP_CONFIG_BASE"),
        (0x054E, "G_EP_CONFIG_ARRAY"),
        (0x054F, "G_SCSI_MODE_FLAG"),
        (0x0552, "G_SCSI_STATUS_FLAG"),
        (0x0564, "G_EP_QUEUE_CTRL"),
        (0x0565, "G_EP_QUEUE_STATUS"),
        (0x0566, "G_EP_QUEUE_PARAM"),
        (0x0567, "G_EP_QUEUE_IDATA"),
        (0x0568, "G_BUF_OFFSET_HI"),
        (0x0569, "G_BUF_OFFSET_LO"),
        (0x056A, "G_EP_QUEUE_IDATA2"),
        (0x056B, "G_EP_QUEUE_IDATA3"),
        (0x0574, "G_LOG_PROCESS_STATE"),
        (0x0575, "G_LOG_ENTRY_VALUE"),
        (0x0578, "G_DMA_ENDPOINT_0578"),
        (0x057A, "G_EP_LOOKUP_TABLE"),
        (0x05A6, "G_PCIE_TXN_COUNT_LO"),
        (0x05A7, "G_PCIE_TXN_COUNT_HI"),
        (0x05A8, "G_EP_CONFIG_05A8"),
        (0x05AE, "G_PCIE_DIRECTION"),
        (0x05AF, "G_PCIE_ADDR_0"),
        (0x05B0, "G_PCIE_ADDR_1"),
        (0x05B1, "G_PCIE_ADDR_2"),
        (0x05B2, "G_PCIE_ADDR_3"),
        (0x05F8, "G_EP_CONFIG_05F8"),

        # =========================================================================
        # Transfer Work Area (0x0600-0x07FF)
        # =========================================================================
        (0x06E5, "G_MAX_LOG_ENTRIES"),
        (0x06E6, "G_STATE_FLAG_06E6"),
        (0x06E8, "G_WORK_06E8"),
        (0x06EA, "G_ERROR_CODE_06EA"),
        (0x06EC, "G_MISC_FLAG_06EC"),
        (0x0719, "G_STATE_0719"),
        (0x0775, "G_STATE_0775"),
        (0x07B7, "G_CMD_SLOT_INDEX"),
        (0x07B8, "G_FLASH_CMD_FLAG"),
        (0x07BC, "G_FLASH_CMD_TYPE"),
        (0x07BD, "G_FLASH_OP_COUNTER"),
        (0x07C3, "G_CMD_STATE"),
        (0x07C4, "G_CMD_STATUS"),
        (0x07CA, "G_CMD_MODE"),
        (0x07D3, "G_CMD_PARAM_0"),
        (0x07D4, "G_CMD_PARAM_1"),
        (0x07DA, "G_CMD_LBA_0"),
        (0x07DB, "G_CMD_LBA_1"),
        (0x07DC, "G_CMD_LBA_2"),
        (0x07DD, "G_CMD_LBA_3"),
        (0x07E4, "G_SYS_FLAGS_BASE"),
        (0x07E5, "G_TRANSFER_ACTIVE"),
        (0x07E8, "G_SYS_FLAGS_07E8"),
        (0x07EA, "G_XFER_FLAG_07EA"),
        (0x07EC, "G_SYS_FLAGS_07EC"),
        (0x07ED, "G_SYS_FLAGS_07ED"),
        (0x07EE, "G_SYS_FLAGS_07EE"),
        (0x07EF, "G_SYS_FLAGS_07EF"),
        (0x07F6, "G_SYS_FLAGS_07F6"),
        (0x07F7, "G_INIT_FLAGS_07F7"),

        # =========================================================================
        # Event/Loop State Work Area (0x0900-0x09FF)
        # =========================================================================
        (0x097A, "G_EVENT_INIT_097A"),
        (0x098E, "G_LOOP_CHECK_098E"),
        (0x0991, "G_LOOP_STATE_0991"),
        (0x09E5, "G_STATE_09E5"),
        (0x09E8, "G_STATE_09E8"),
        (0x09EF, "G_EVENT_CHECK_09EF"),
        (0x09F4, "G_MODE_CONFIG_1"),
        (0x09F5, "G_MODE_CONFIG_2"),
        (0x09F6, "G_MODE_CONFIG_3"),
        (0x09F7, "G_MODE_CONFIG_4"),
        (0x09F8, "G_MODE_CONFIG_5"),
        (0x09F9, "G_EVENT_FLAGS"),
        (0x09FA, "G_EVENT_CTRL_09FA"),
        (0x09FB, "G_EVENT_MODE_09FB"),

        # =========================================================================
        # Endpoint Dispatch Work Area (0x0A00-0x0BFF)
        # =========================================================================
        (0x0A3C, "G_CONFIG_ARRAY_A3C"),
        (0x0A41, "G_CONFIG_FLAGS_A41"),
        (0x0A42, "G_DEVICE_ID_LO"),
        (0x0A43, "G_DEVICE_ID_HI"),
        (0x0A44, "G_VENDOR_ID_LO"),
        (0x0A45, "G_VENDOR_ID_HI"),
        (0x0A56, "G_FLASH_CONFIG_VALID"),
        (0x0A57, "G_DEFAULT_VENDOR_LO"),
        (0x0A58, "G_DEFAULT_VENDOR_HI"),
        (0x0A59, "G_LOOP_STATE"),
        (0x0A5B, "G_NIBBLE_SWAP_0A5B"),
        (0x0A5C, "G_NIBBLE_SWAP_0A5C"),
        (0x0A7B, "G_EP_DISPATCH_VAL1"),
        (0x0A7C, "G_EP_DISPATCH_VAL2"),
        (0x0A7D, "G_EP_DISPATCH_VAL3"),
        (0x0A7E, "G_EP_DISPATCH_VAL4"),
        (0x0A83, "G_ACTION_CODE_0A83"),
        (0x0A84, "G_STATE_WORK_0A84"),
        (0x0A85, "G_STATE_WORK_0A85"),
        (0x0A86, "G_STATE_WORK_0A86"),
        (0x0A9D, "G_LANE_STATE_0A9D"),
        (0x0AA1, "G_LOG_PROCESSED_INDEX"),
        (0x0AA2, "G_STATE_PARAM_0AA2"),
        (0x0AA3, "G_STATE_COUNTER_HI"),
        (0x0AA4, "G_STATE_COUNTER_LO"),
        (0x0AA5, "G_EVENT_COUNT_0AA5"),
        (0x0AA6, "G_BUFFER_STATE_0AA6"),
        (0x0AA7, "G_BUFFER_STATE_0AA7"),
        (0x0AA8, "G_FLASH_ERROR_0"),
        (0x0AA9, "G_FLASH_ERROR_1"),
        (0x0AAA, "G_FLASH_RESET_0AAA"),
        (0x0AAB, "G_STATE_HELPER_0AAB"),
        (0x0AAC, "G_STATE_COUNTER_0AAC"),
        (0x0AAD, "G_FLASH_ADDR_0"),
        (0x0AAE, "G_FLASH_ADDR_1"),
        (0x0AAF, "G_FLASH_ADDR_2"),
        (0x0AB0, "G_FLASH_ADDR_3"),
        (0x0AB1, "G_FLASH_LEN_LO"),
        (0x0AB2, "G_FLASH_LEN_HI"),
        (0x0AD1, "G_LINK_STATE_0AD1"),
        (0x0AD2, "G_LINK_STATE_0AD2"),
        (0x0AE2, "G_SYSTEM_STATE_0AE2"),
        (0x0AE3, "G_STATE_FLAG_0AE3"),
        (0x0AEE, "G_STATE_CHECK_0AEE"),
        (0x0AF1, "G_STATE_FLAG_0AF1"),
        (0x0AF2, "G_TRANSFER_FLAG_0AF2"),
        (0x0AF3, "G_XFER_STATE_0AF3"),
        (0x0AF5, "G_EP_DISPATCH_OFFSET"),
        (0x0AF6, "G_XFER_STATE_0AF6"),
        (0x0AF7, "G_XFER_CTRL_0AF7"),
        (0x0AF8, "G_POWER_INIT_FLAG"),
        (0x0AF9, "G_XFER_MODE_0AF9"),
        (0x0AFA, "G_TRANSFER_PARAMS_HI"),
        (0x0AFB, "G_TRANSFER_PARAMS_LO"),
        (0x0AFC, "G_XFER_COUNT_LO"),
        (0x0AFD, "G_XFER_COUNT_HI"),
        (0x0AFE, "G_XFER_RETRY_CNT"),
        (0x0B00, "G_USB_PARAM_0B00"),
        (0x0B01, "G_USB_INIT_0B01"),
        (0x0B1D, "G_DMA_POLL_STATE"),
        (0x0B25, "G_DMA_RETRY_STATE"),
        (0x0B2E, "G_USB_TRANSFER_FLAG"),
        (0x0B3B, "G_TRANSFER_BUSY_0B3B"),
        (0x0B3D, "G_STATE_WORK_0B3D"),
        (0x0B3E, "G_STATE_WORK_0B3E"),
        (0x0B3F, "G_STATE_CTRL_0B3F"),
        (0x0B40, "G_TIMER_INIT_0B40"),
        (0x0B41, "G_USB_STATE_0B41"),

        # =========================================================================
        # Flash Buffer Area (0x7000-0x707F)
        # =========================================================================
        (0x7004, "G_FLASH_VENDOR_STRING"),
        (0x702C, "G_FLASH_SERIAL_STRING"),
        (0x7054, "G_FLASH_CONFIG_BYTES"),
        (0x7059, "G_FLASH_MODE_CONFIG"),
        (0x705A, "G_FLASH_MODE_CONFIG_2"),
        (0x705C, "G_FLASH_DEVICE_ID"),
        (0x705E, "G_FLASH_VENDOR_ID"),
        (0x707B, "G_FLASH_BUF_707B"),
        (0x707D, "G_FLASH_BUF_707D"),
        (0x707E, "G_FLASH_HEADER_MARKER"),
        (0x707F, "G_FLASH_CHECKSUM"),

        # =========================================================================
        # Memory Buffers
        # =========================================================================
        (0x7000, "FLASH_BUFFER_BASE"),
        (0x8000, "USB_SCSI_BUF_BASE"),
        (0x9E00, "USB_CTRL_BUF_BASE"),
        (0xA000, "NVME_IOSQ_BASE"),
        (0xB000, "NVME_ASQ_BASE"),
        (0xB100, "NVME_ACQ_BASE"),
        (0xF000, "NVME_DATA_BUF_BASE"),
    ]

    count = 0
    for addr_int, name in globals_list:
        try:
            # Try EXTMEM space first
            addr = toAddr("EXTMEM:{:04X}".format(addr_int))
            if create_label(addr, name):
                count += 1
        except:
            try:
                # Fall back to direct address
                addr = toAddr(addr_int)
                if create_label(addr, name):
                    count += 1
            except Exception as e:
                print("Error adding global {} at 0x{:04X}: {}".format(name, addr_int, e))

    return count

def run():
    """Main entry point"""
    print("=" * 70)
    print("AS2464 USB4/NVMe Firmware Symbol Import Script")
    print("Updated with all function, register, and global names")
    print("from the C reimplementation project")
    print("")
    print("This script handles both CODE_BANK0 and CODE_BANK1 sections:")
    print("  CODE_BANK0: 0x0000-0xFFFF  (always accessible)")
    print("  CODE_BANK1: 0x10000-0x17FFF (file offsets, mapped to 0x8000-0xFFFF)")
    print("=" * 70)

    print("\nAdding Bank 0 function names (0x0000-0xFFFF)...")
    func0_count = add_bank0_functions()
    print("Added {} Bank 0 functions".format(func0_count))

    print("\nAdding Bank 1 function names (file 0x10000-0x17FFF)...")
    func1_count = add_bank1_functions()
    print("Added {} Bank 1 functions".format(func1_count))

    print("\nAdding register labels (EXTMEM)...")
    reg_count = add_registers()
    print("Added {} registers".format(reg_count))

    print("\nAdding global variable labels (EXTMEM)...")
    glob_count = add_globals()
    print("Added {} globals".format(glob_count))

    print("\n" + "=" * 70)
    print("Import complete!")
    print("Total symbols added: {}".format(func0_count + func1_count + reg_count + glob_count))
    print("  Bank 0 functions: {}".format(func0_count))
    print("  Bank 1 functions: {}".format(func1_count))
    print("  Registers: {}".format(reg_count))
    print("  Globals: {}".format(glob_count))
    print("=" * 70)

# Run the script
run()
