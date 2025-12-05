/*
 * ASM2464PD Firmware - NVMe Driver
 *
 * NVMe controller interface for USB4/Thunderbolt to NVMe bridge
 * Handles NVMe command submission, completion, and queue management
 *
 * NVMe registers are at 0xC400-0xC4FF
 * NVMe event registers are at 0xEC00-0xEC0F
 *
 * NOTE: Core dispatch functions (nvme_util_get_status_flags, nvme_util_get_error_flags)
 * are defined in main.c as they are part of the core dispatch mechanism.
 */

#include "types.h"
#include "sfr.h"
#include "registers.h"

/* NVMe driver functions will be added here as they are reversed */
