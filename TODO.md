# ASM2464PD Firmware Reverse Engineering TODO

## Progress Summary
- Total functions in ghidra.c: ~720
- Functions implemented: ~380 (53%)
- Functions remaining: ~340 (47%)

---

## USB4 eGPU Passthrough Priority

For USB4 eGPU passthrough (PCIe tunneling without NVMe/SCSI translation), the following
subsystems are critical. These should be prioritized if the goal is eGPU support.

### PHY/Link Initialization (Critical)
These functions bring up the USB4 and PCIe links:

- [ ] `0xd436` - PHY configuration (main PHY init) **HIGH PRIORITY**
- [ ] `0xd47f` - PHY handler
- [ ] `0xd4c8` - PHY handler
- [ ] `0xd511` - PHY lane configuration
- [ ] `0xd559` - PHY signal settings
- [ ] `0xd630` - PHY extended config
- [ ] `0xd702` - PHY link training
- [ ] `0xd78a` - PHY status polling
- [ ] `0xd7cd` - PHY completion handler
- [ ] `0xd8d5` - PHY error handler
- [ ] `0xe8a9` - PHY event handler (Bank 1)

### PCIe Passthrough/Tunneling (Critical)
These handle PCIe TLP forwarding - the core of eGPU support:

- [ ] `0x9916` - PCIe config space setup **HIGH PRIORITY**
- [ ] `0x991a` - PCIe BAR configuration
- [ ] `0x9923` - PCIe link config
- [ ] `0x992a` - PCIe capability setup
- [ ] `0x9930` - PCIe extended config
- [ ] `0x99e0` - PCIe write config space **HIGH PRIORITY**
- [ ] `0x9a6c` - PCIe link speed negotiation **HIGH PRIORITY**
- [ ] `0xa522` - PCIe interrupt handler **HIGH PRIORITY**
- [ ] `0xb104` - PCIe TLP handler **HIGH PRIORITY**
- [ ] `0xb28c` - PCIe completion handler
- [ ] `0xb402` - PCIe error handler
- [ ] `0xe00c` - PCIe error recovery (Bank 1)

### Power Management (Important)
USB suspend/resume and PCIe power states:

- [ ] `0xd02a` - Power state machine **HIGH PRIORITY**
- [ ] `0xd118` - Power domain control
- [ ] `0xd17a` - Power sequencing
- [ ] `0xd1f2` - Clock gating
- [ ] `0xd1fe` - Power resume
- [ ] `0xd211` - Power suspend
- [ ] `0xd916` - PHY/power handler **HIGH PRIORITY**
- [ ] `0xda13` - L1 power state
- [ ] `0xda51` - L2 power state
- [ ] `0xdb45` - Power event handler
- [ ] `0xdc2d` - USB suspend handler
- [ ] `0xdc9d` - USB resume handler

### Interrupt/Event Handling (Important)
Link events and error handling:

- [ ] `0xca0d` - System state handler **HIGH PRIORITY**
- [ ] `0xc5ff` - Event dispatcher
- [ ] `0xc6d3` - Link event handler
- [ ] `0xc73c` - PCIe event handler
- [ ] `0xc80d` - USB event handler
- [ ] `0xc874` - Combined event handler
- [ ] `0xc8db` - Error event handler
- [ ] `0xe06b` - Bank 1 event handler
- [ ] `0xe0f4` - Link status event

### Bank Switch Infrastructure (Required)
Core dispatching for Bank 1 functions:

- [ ] `0xbcaf` - Bank switch helper **HIGH PRIORITY**
- [ ] `0xbcde` - Bank switch read helper **HIGH PRIORITY**
- [ ] `0xbc88` - Bank switch read
- [ ] `0xbcc4` - Bank switch write

### NOT Needed for eGPU (Can Skip)
These sections are NVMe/SCSI specific and not needed for eGPU passthrough:

- SCSI/USB Mass Storage (0x4000-0x5800) - CBW/CSW, SCSI commands
- NVMe Command Engine (0x9500-0x9700) - NVMe command building
- NVMe Queue Management (0xa600-0xa800) - Submission/completion queues
- NVMe Admin Commands (0xaa00-0xac00) - Identify, Create IO Queue
- SCSI DMA Control (0xCE00-0xCE9F) - Block transfer state machines

### Estimated Scope
- **Functions needed for eGPU**: ~60 functions (~18% of total)
- **Functions that can be skipped**: ~200+ functions
- **Shared infrastructure**: ~80 functions (init, power, interrupts)

---

## Recent Completions

### Function Renames in main.c (ISR handlers)
- [x] `handler_04d0` → `timer_link_status_handler` (0xCE79)
- [x] `handler_04b2` → `reserved_stub_handler` (0xE971)
- [x] `handler_4fb6` → `main_polling_handler`
- [x] `handler_0327` → `usb_power_init` (0xB1CB)
- [x] `handler_0494` → `event_state_handler` (Bank1:0xE56F)
- [x] `handler_0606` → `error_state_config` (Bank1:0xB230)
- [x] `handler_0589` → `phy_register_config` (0xD894)
- [x] `handler_0525` → `flash_command_handler` (0xBAA0)
- [x] `handler_039a` → `usb_buffer_dispatch` (0xD810)
- [x] `handler_0520` → `system_interrupt_handler` (0xB4BA)
- [x] `handler_052f` → `pcie_nvme_event_handler` (0xAF5E)
- [x] `handler_0570` → `pcie_error_dispatch` (Bank1:0xE911)
- [x] `handler_061a` → `pcie_event_bit5_handler` (Bank1:0xA066)
- [x] `handler_0593` → `pcie_timer_bit4_handler` (0xC105)
- [x] `handler_0642` → `system_timer_handler` (Bank1:0xEF4E)

### Function Renames in state_helpers.c
- [x] `handler_d07f` → `usb_mode_config_d07f`
- [x] `handler_e214` → `nvme_queue_config_e214`
- [x] `handler_e8ef` → `power_init_complete_e8ef`
- [x] `handler_2608` → `dma_queue_state_handler`

### Function Renames in error_log.c
- [x] `error_handler_system_unused` → `error_handler_system_timer`

### Dispatch Function Direct Call Replacements
- [x] `dispatch_039f` → `handler_d916` (0xD916)
- [x] `dispatch_04fd` → `handler_e96c` (0xE96C)
- [x] `dispatch_04ee` → `handler_e6fc` (0xE6FC)
- [x] `dispatch_04e9` → `handler_e8e4` (0xE8E4)
- [x] `dispatch_044e` → `handler_e91d` (0xE91D)
- [x] `dispatch_032c` → `phy_power_config_handler` (0x92C5)
- [x] `dispatch_0340` → `handler_bf8e` (0xBF8E)
- [x] `dispatch_0534` → `handler_d6bc` (0xD6BC)
- [x] `dispatch_0638` → `handler_e478` (Bank1:0xE478)

### Code Organization
- [x] bank1.c removed - functions moved to appropriate files
- [x] All register definitions in registers.h
- [x] All global definitions in globals.h

---

## Dispatch/Jump Table Functions (0x0300-0x0650)

These are dispatch stubs that route to various handlers via bank switching.

### Bank Switch Dispatch (0x0300-0x0400)
- [ ] `0x0322` - Bank dispatch stub
- [ ] `0x032c` - Bank dispatch stub
- [ ] `0x0331` - Bank dispatch stub
- [ ] `0x0336` - Bank dispatch stub
- [ ] `0x033b` - Bank dispatch stub
- [ ] `0x0340` - Bank dispatch stub
- [ ] `0x0345` - Bank dispatch stub
- [ ] `0x034a` - Bank dispatch stub
- [ ] `0x034f` - Bank dispatch stub
- [ ] `0x0354` - Bank dispatch stub
- [ ] `0x0359` - Bank dispatch stub
- [ ] `0x035e` - Bank dispatch stub
- [ ] `0x0363` - Bank dispatch stub
- [ ] `0x0368` - Bank dispatch stub
- [ ] `0x036d` - Bank dispatch stub
- [ ] `0x0372` - Bank dispatch stub
- [ ] `0x0377` - Bank dispatch stub
- [ ] `0x037c` - Bank dispatch stub
- [ ] `0x0381` - Bank dispatch stub
- [ ] `0x0386` - Bank dispatch stub
- [ ] `0x038b` - Bank dispatch stub
- [ ] `0x0395` - Bank dispatch stub
- [ ] `0x039f` - Bank dispatch stub
- [ ] `0x03a4` - Bank dispatch stub
- [ ] `0x03a9` - Bank dispatch stub

### Handler Dispatch (0x0400-0x0500)
- [ ] `0x0412` - Handler dispatch
- [ ] `0x0426` - Handler dispatch
- [ ] `0x042b` - Handler dispatch
- [ ] `0x0430` - Handler dispatch
- [ ] `0x0435` - Handler dispatch
- [ ] `0x043a` - Handler dispatch
- [ ] `0x043f` - Handler dispatch
- [ ] `0x0449` - Handler dispatch
- [ ] `0x044e` - Handler dispatch
- [ ] `0x0453` - Handler dispatch
- [ ] `0x045d` - Handler dispatch
- [ ] `0x0462` - Handler dispatch
- [ ] `0x0471` - Handler dispatch
- [ ] `0x047b` - Handler dispatch
- [ ] `0x048a` - Handler dispatch
- [ ] `0x048f` - Handler dispatch
- [ ] `0x04a3` - Handler dispatch
- [ ] `0x04b7` - Handler dispatch
- [ ] `0x04bc` - Handler dispatch
- [ ] `0x04e4` - Handler dispatch
- [ ] `0x04e9` - Handler dispatch
- [ ] `0x04ee` - Handler dispatch
- [ ] `0x04f8` - Handler dispatch
- [ ] `0x04fd` - Handler dispatch

### Event/Interrupt Dispatch (0x0500-0x0650)
- [ ] `0x0507` - Event dispatch
- [ ] `0x050c` - Event dispatch
- [ ] `0x0511` - Event dispatch
- [ ] `0x0516` - Event dispatch
- [ ] `0x052a` - Event dispatch
- [ ] `0x0534` - Event dispatch
- [ ] `0x0539` - Event dispatch
- [ ] `0x053e` - Event dispatch
- [ ] `0x0543` - Event dispatch
- [ ] `0x0548` - Event dispatch
- [ ] `0x054d` - Event dispatch
- [ ] `0x0552` - Event dispatch
- [ ] `0x0557` - Event dispatch
- [ ] `0x055c` - Event dispatch
- [ ] `0x0561` - Event dispatch
- [ ] `0x0566` - Event dispatch
- [ ] `0x056b` - Event dispatch
- [ ] `0x057a` - Event dispatch
- [ ] `0x057f` - Event dispatch
- [ ] `0x0584` - Event dispatch
- [ ] `0x05e8` - Handler stub
- [ ] `0x05ed` - Handler stub
- [ ] `0x05f2` - Handler stub
- [ ] `0x05f7` - Handler stub
- [ ] `0x0601` - Handler stub
- [ ] `0x060b` - Handler stub
- [ ] `0x0615` - Handler stub
- [ ] `0x061f` - Handler stub
- [ ] `0x0624` - Handler stub
- [ ] `0x0629` - Handler stub
- [ ] `0x0633` - Handler stub
- [ ] `0x0638` - Handler stub

---

## Utility Functions (0x0c00-0x0e00)

- [ ] `0x0c9e` - Utility function
- [ ] `0x0cab` - Utility function (computation helper)
- [ ] `0x0cb9` - Utility function

---

## State Machine Helpers (0x1100-0x1800)

### Transfer/State Functions
- [ ] `0x11a2` - Transfer helper (helper_11a2)
- [ ] `0x14e5` - State function with params
- [ ] `0x1564` - State load triple
- [ ] `0x157d` - State function
- [ ] `0x1580` - State function
- [ ] `0x159f` - State address calc
- [ ] `0x15a0` - State function
- [ ] `0x15af` - State helper entry point
- [ ] `0x15b7` - Store and calc address
- [ ] `0x15d4` - Address computation
- [ ] `0x15f1` - CE40 address calc

### Transfer Helpers (0x1600-0x1800)
- [ ] `0x165e` - Store DPTR calc
- [ ] `0x1660` - Address calc
- [ ] `0x166a` - Address calc
- [ ] `0x166f` - Flash func
- [ ] `0x168c` - Queue entry calc
- [ ] `0x168e` - Queue entry calc
- [ ] `0x169a` - Address calc 04B7
- [ ] `0x16a4` - Read and calc
- [ ] `0x16a6` - Read and calc
- [ ] `0x16b8` - Write and calc 046x
- [ ] `0x16d3` - Compute helper
- [ ] `0x16eb` - Address calc
- [ ] `0x1755` - Complex computation

---

## USB Functions (0x1b00-0x1c80)

- [ ] `0x1b2d` - USB function
- [ ] `0x1b2e` - USB function
- [ ] `0x1b30` - USB function
- [ ] `0x1b3b` - USB function
- [ ] `0x1b3f` - USB function
- [ ] `0x1b89` - USB function
- [ ] `0x1b8d` - USB function
- [ ] `0x1bec` - USB setup endpoint
- [ ] `0x1c13` - USB data handler
- [ ] `0x1c30` - USB calc buffer
- [ ] `0x1c80` - NVME subtract idata

---

## Protocol State Machines (0x2300-0x3200)

- [ ] `0x23f7` - Complex state helper (893 bytes) - **PRIORITY**
- [ ] `0x2814` - Queue processing
- [ ] `0x2a10` - State machine
- [ ] `0x2db7` - State machine
- [ ] `0x2f67` - State machine
- [ ] `0x313f` - Protocol handler
- [ ] `0x3179` - Protocol handler
- [ ] `0x31c3` - Protocol handler
- [ ] `0x322e` - Protocol handler (compare helper)
- [ ] `0x3578` - Protocol handler
- [ ] `0x36ab` - Protocol handler
- [ ] `0x39e4` - Protocol handler
- [ ] `0x3bcd` - Protocol handler
- [ ] `0x3cb8` - Protocol handler
- [ ] `0x3da1` - Protocol handler

---

## SCSI/USB Mass Storage (0x4000-0x5800)

### SCSI Command Handlers
- [ ] `0x4013` - SCSI handler
- [ ] `0x4042` - SCSI handler
- [ ] `0x40d9` - SCSI handler
- [ ] `0x419d` - SCSI handler
- [ ] `0x425f` - SCSI handler
- [ ] `0x43d3` - SCSI handler
- [ ] `0x4469` - SCSI handler
- [ ] `0x466b` - SCSI handler
- [ ] `0x480c` - SCSI handler
- [ ] `0x4977` - CSW/CBW handler
- [ ] `0x4b25` - SCSI handler
- [ ] `0x4b8b` - SCSI handler
- [ ] `0x4c40` - SCSI handler
- [ ] `0x4c98` - SCSI handler
- [ ] `0x4d92` - SCSI handler
- [ ] `0x4eb3` - SCSI handler
- [ ] `0x4f37` - SCSI handler

### USB Endpoint Handlers
- [ ] `0x502e` - USB endpoint
- [ ] `0x5038` - USB endpoint
- [ ] `0x5043` - USB endpoint
- [ ] `0x5046` - USB endpoint
- [ ] `0x504f` - USB endpoint
- [ ] `0x5058` - USB endpoint
- [ ] `0x505d` - USB endpoint
- [ ] `0x5061` - USB endpoint
- [ ] `0x5069` - USB endpoint
- [ ] `0x50ff` - USB endpoint
- [ ] `0x5112` - USB endpoint
- [ ] `0x5157` - USB endpoint
- [ ] `0x519e` - USB endpoint
- [ ] `0x51ef` - USB handler
- [ ] `0x51f9` - USB handler
- [ ] `0x52b1` - USB handler
- [ ] `0x52c7` - USB handler
- [ ] `0x5373` - USB handler
- [ ] `0x53a4` - DMA/buffer setup
- [ ] `0x54fc` - USB handler
- [ ] `0x5622` - USB handler
- [ ] `0x573b` - USB handler
- [ ] `0x5765` - USB handler

---

## Bank 1 Functions (0x8000+)

### Low Bank 1 (0x8000-0x9000)
- [x] `0x839c` - pcie_addr_store_839c (in pcie.c)
- [x] `0x83b9` - pcie_addr_store_83b9 (in pcie.c)
- [ ] `0x873a` - Bank 1 function
- [ ] `0x8743` - Bank 1 function
- [ ] `0x874c` - Bank 1 function
- [ ] `0x897d` - Bank 1 function
- [ ] `0x8992` - Bank 1 function
- [ ] `0x89ad` - Bank 1 function
- [ ] `0x89bd` - Bank 1 function
- [ ] `0x89c6` - Bank 1 function
- [ ] `0x8a3a` - Bank 1 function
- [ ] `0x8a3d` - Bank 1 function
- [ ] `0x8a4e` - Bank 1 function
- [ ] `0x8a67` - Bank 1 function
- [ ] `0x8a72` - Bank 1 function
- [ ] `0x8a7e` - Bank 1 function
- [ ] `0x8a89` - Bank 1 function
- [ ] `0x8d6e` - Bank 1 function
- [x] `0x8d77` - system_init_from_flash (in main.c)

---

## NVMe/Command Engine (0x9500-0x9b00)

### Command Helpers (0x9500-0x9700)
- [ ] `0x955d` - Command helper
- [ ] `0x955e` - Command helper
- [ ] `0x957b` - Command helper
- [ ] `0x9580` - Command helper
- [ ] `0x95a0` - Command helper
- [ ] `0x95a2` - Command helper
- [ ] `0x95a5` - Command helper
- [ ] `0x95ab` - Command setup
- [ ] `0x95af` - Command setup
- [ ] `0x95bf` - Command setup
- [ ] `0x95c5` - Command setup
- [ ] `0x95c9` - Command setup
- [ ] `0x95ca` - Command setup
- [ ] `0x95d1` - Command setup
- [ ] `0x95d7` - Command setup
- [ ] `0x95da` - Command setup
- [ ] `0x95df` - Command setup
- [ ] `0x95e1` - Command setup
- [ ] `0x95e4` - Command setup
- [ ] `0x95f2` - Command setup
- [ ] `0x95f9` - Command setup
- [ ] `0x9608` - Command trigger
- [ ] `0x9617` - Command write
- [ ] `0x9621` - Command helper
- [ ] `0x9627` - Command helper
- [ ] `0x962e` - Command helper
- [ ] `0x9635` - Command helper
- [ ] `0x9647` - Command helper
- [ ] `0x964f` - Command helper
- [ ] `0x9656` - Command helper
- [ ] `0x9657` - Command helper
- [ ] `0x9664` - Command helper
- [ ] `0x9677` - LBA combine
- [ ] `0x9684` - LBA helper
- [ ] `0x9687` - LBA helper
- [ ] `0x968c` - LBA helper
- [ ] `0x969d` - LBA helper
- [ ] `0x96a7` - LBA helper
- [ ] `0x96a9` - LBA helper
- [ ] `0x96ae` - Command engine
- [ ] `0x96b8` - Command engine
- [ ] `0x96bf` - Command engine
- [ ] `0x96d4` - Command engine
- [ ] `0x96d6` - Command engine
- [ ] `0x96d7` - Command engine
- [ ] `0x96ee` - Command engine
- [ ] `0x96f0` - Command engine
- [ ] `0x96f7` - Command engine
- [ ] `0x9703` - Command engine
- [ ] `0x9713` - Command engine
- [ ] `0x971e` - Command engine
- [ ] `0x9729` - Command engine
- [ ] `0x9741` - Command engine
- [ ] `0x977c` - Command engine
- [ ] `0x97bd` - Command engine
- [ ] `0x97d5` - Command engine
- [ ] `0x983f` - Command engine
- [ ] `0x9887` - Command engine

### PCIe/Config Functions (0x9900-0x9b00)
- [ ] `0x9916` - PCIe config
- [ ] `0x991a` - PCIe config
- [ ] `0x9923` - PCIe config
- [ ] `0x992a` - PCIe config
- [ ] `0x9930` - PCIe config
- [ ] `0x994b` - PCIe helper
- [ ] `0x994c` - PCIe helper
- [ ] `0x994d` - PCIe helper
- [ ] `0x994e` - PCIe helper
- [ ] `0x9954` - PCIe helper
- [ ] `0x995a` - PCIe helper
- [ ] `0x9962` - PCIe helper
- [ ] `0x9964` - PCIe helper
- [ ] `0x996a` - PCIe helper
- [ ] `0x9977` - PCIe helper
- [ ] `0x997a` - PCIe helper
- [ ] `0x9980` - PCIe helper
- [ ] `0x9983` - PCIe helper
- [ ] `0x9984` - PCIe helper
- [ ] `0x998a` - PCIe helper
- [ ] `0x998b` - PCIe helper
- [ ] `0x998e` - PCIe helper
- [ ] `0x998f` - PCIe helper
- [ ] `0x9996` - PCIe helper
- [ ] `0x9997` - PCIe clear/trigger
- [ ] `0x99b5` - PCIe helper
- [ ] `0x99bc` - PCIe helper
- [ ] `0x99bf` - PCIe helper
- [ ] `0x99c0` - PCIe helper
- [ ] `0x99c6` - PCIe helper
- [ ] `0x99c7` - PCIe helper
- [ ] `0x99ce` - PCIe helper
- [ ] `0x99d1` - PCIe helper
- [ ] `0x99d5` - PCIe helper
- [ ] `0x99d8` - PCIe helper
- [ ] `0x99d9` - PCIe helper
- [ ] `0x99e0` - PCIe write config
- [ ] `0x99f8` - PCIe IDATA params
- [ ] `0x9a00` - PCIe helper
- [ ] `0x9a02` - PCIe helper
- [ ] `0x9a09` - PCIe helper
- [ ] `0x9a10` - PCIe helper
- [ ] `0x9a20` - PCIe helper
- [ ] `0x9a3b` - PCIe byte enables
- [ ] `0x9a3e` - PCIe helper
- [ ] `0x9a46` - PCIe buffer params
- [ ] `0x9a6c` - PCIe link speed
- [ ] `0x9aa3` - PCIe clear address
- [ ] `0x9ab3` - PCIe txn count
- [ ] `0x9aba` - PCIe helper

---

## NVMe Handlers (0x9e00-0xb900)

### NVMe Event Handlers (0x9e00-0xa600)
- [ ] `0x9ee5` - NVMe event
- [ ] `0xa0f0` - NVMe handler
- [ ] `0xa153` - NVMe handler
- [ ] `0xa183` - NVMe handler
- [ ] `0xa2c1` - NVMe handler
- [ ] `0xa2c2` - NVMe handler
- [ ] `0xa2de` - NVMe handler
- [ ] `0xa2eb` - NVMe handler
- [ ] `0xa2f8` - NVMe handler
- [ ] `0xa2ff` - NVMe handler
- [ ] `0xa301` - NVMe handler
- [ ] `0xa308` - NVMe handler
- [ ] `0xa334` - NVMe handler
- [ ] `0xa336` - NVMe handler
- [ ] `0xa33d` - NVMe handler
- [ ] `0xa344` - NVMe handler
- [ ] `0xa34f` - NVMe handler
- [ ] `0xa351` - NVMe handler
- [ ] `0xa365` - NVMe handler
- [ ] `0xa367` - NVMe handler
- [ ] `0xa372` - NVMe handler
- [ ] `0xa374` - NVMe handler
- [ ] `0xa37b` - NVMe handler
- [ ] `0xa384` - NVMe handler
- [ ] `0xa38b` - NVMe handler
- [ ] `0xa3c4` - NVMe handler
- [ ] `0xa3cb` - NVMe handler
- [ ] `0xa3d2` - NVMe handler
- [ ] `0xa3db` - NVMe handler
- [ ] `0xa3eb` - NVMe handler
- [ ] `0xa522` - PCIe interrupt handler - **PRIORITY**

### NVMe Queue Management (0xa600-0xa800)
- [ ] `0xa62d` - Queue management
- [ ] `0xa637` - Queue management
- [ ] `0xa639` - Queue management
- [ ] `0xa63c` - Queue management
- [ ] `0xa63d` - Queue management
- [ ] `0xa644` - Queue management
- [ ] `0xa646` - Queue management
- [ ] `0xa647` - Queue management
- [ ] `0xa648` - Queue management
- [ ] `0xa651` - Queue management
- [ ] `0xa655` - Queue management
- [ ] `0xa660` - Queue management
- [ ] `0xa666` - Queue management
- [ ] `0xa66d` - Queue management
- [ ] `0xa679` - Queue management
- [ ] `0xa67f` - Queue management
- [ ] `0xa687` - Queue management
- [ ] `0xa692` - Queue management
- [ ] `0xa69a` - Queue management
- [ ] `0xa6ad` - Queue management
- [ ] `0xa6c6` - Queue management
- [ ] `0xa6dc` - Queue management
- [ ] `0xa6ef` - Queue management
- [ ] `0xa6f6` - Queue management
- [ ] `0xa6fd` - Queue management
- [ ] `0xa704` - Queue management
- [ ] `0xa714` - Queue management
- [ ] `0xa715` - Queue management
- [ ] `0xa71b` - Queue management
- [ ] `0xa722` - Queue management
- [ ] `0xa723` - Queue management
- [ ] `0xa72b` - Queue management
- [ ] `0xa732` - Queue management
- [ ] `0xa739` - Queue management
- [ ] `0xa740` - Queue management
- [ ] `0xa77d` - Queue management
- [ ] `0xa840` - Queue management

### Admin Commands (0xaa00-0xac00)
- [ ] `0xaa2a` - Admin command
- [ ] `0xaa30` - Admin command
- [ ] `0xaa33` - Admin command
- [ ] `0xaa36` - Admin command
- [ ] `0xaa4f` - Admin command
- [ ] `0xaa56` - Admin command
- [ ] `0xaa60` - Admin command
- [ ] `0xaa63` - Admin command
- [ ] `0xaafb` - Admin command
- [ ] `0xab0d` - Admin command
- [ ] `0xab16` - Admin command
- [ ] `0xab4e` - Admin command
- [ ] `0xab7a` - Admin command
- [ ] `0xabc2` - Admin command
- [ ] `0xabd4` - Admin command
- [ ] `0xabd7` - Admin command
- [ ] `0xabe9` - Admin command

### PCIe TLP Handlers (0xb100-0xba00)
- [ ] `0xb104` - PCIe TLP handler
- [ ] `0xb28c` - PCIe handler
- [ ] `0xb402` - PCIe handler
- [ ] `0xb624` - NVMe command setup
- [ ] `0xb6cf` - NVMe command setup
- [ ] `0xb779` - NVMe command setup
- [ ] `0xb820` - NVMe queue
- [ ] `0xb825` - NVMe queue
- [ ] `0xb833` - NVMe queue
- [ ] `0xb838` - NVMe queue
- [ ] `0xb848` - NVMe queue
- [ ] `0xb850` - NVMe queue
- [ ] `0xb851` - NVMe queue
- [ ] `0xb881` - NVMe handler
- [ ] `0xb8a2` - NVMe handler
- [ ] `0xb8b9` - NVMe handler
- [ ] `0xba06` - NVMe handler

---

## Register Helper Functions (0xbb00-0xbe00)

- [ ] `0xbb37` - Register helper
- [ ] `0xbb44` - Register helper
- [ ] `0xbb47` - Register helper
- [ ] `0xbb48` - Register helper
- [ ] `0xbb4f` - Register helper
- [ ] `0xbb5e` - Register helper
- [ ] `0xbb68` - Register helper
- [ ] `0xbb6d` - Register helper
- [ ] `0xbb6e` - Register helper
- [ ] `0xbb75` - Register helper
- [ ] `0xbb7e` - Register helper
- [ ] `0xbb8f` - Register helper
- [ ] `0xbb96` - Register helper
- [ ] `0xbba0` - Register helper
- [ ] `0xbba8` - Register helper
- [ ] `0xbbaf` - Register helper
- [ ] `0xbbc0` - Register helper
- [ ] `0xbbc7` - Register helper
- [ ] `0xbc63` - Register helper
- [ ] `0xbc70` - Register helper
- [ ] `0xbc88` - Register helper (bank switch read)
- [ ] `0xbc98` - Register helper
- [ ] `0xbca5` - Register helper
- [ ] `0xbcaf` - Register helper (bank switch) - **PRIORITY**
- [ ] `0xbcb8` - Register helper
- [ ] `0xbcc4` - Register helper
- [ ] `0xbcd0` - Register helper
- [ ] `0xbcd7` - Register helper
- [ ] `0xbcde` - Register helper (bank switch read) - **PRIORITY**
- [ ] `0xbce7` - Register helper
- [ ] `0xbcf2` - Register helper
- [ ] `0xbcfe` - Register helper
- [ ] `0xbd05` - Register helper
- [ ] `0xbd09` - Register helper
- [ ] `0xbd0d` - Register helper
- [ ] `0xbd14` - Register helper
- [ ] `0xbd17` - Register helper
- [ ] `0xbd23` - Register helper
- [ ] `0xbd33` - Register helper
- [ ] `0xbd3a` - Register helper
- [ ] `0xbd41` - Register helper
- [ ] `0xbd50` - Register helper
- [ ] `0xbd57` - Register helper
- [ ] `0xbd65` - Register helper
- [ ] `0xbd6c` - Register helper
- [ ] `0xbe02` - Register helper
- [ ] `0xbe8b` - Register helper
- [ ] `0xbefb` - Register helper
- [ ] `0xbf0f` - Register helper

---

## Error Log Functions (0xc000-0xc500)

- [ ] `0xc089` - Error log
- [ ] `0xc17f` - Error handler
- [ ] `0xc1f9` - Error log
- [ ] `0xc270` - Error log
- [ ] `0xc2e6` - Error log
- [ ] `0xc2f1` - Error log
- [ ] `0xc2f8` - Error log (max entries)
- [ ] `0xc2ff` - Error log
- [ ] `0xc30e` - Error log
- [ ] `0xc335` - Error log
- [ ] `0xc351` - Error log
- [ ] `0xc358` - Error log
- [ ] `0xc35b` - Error log
- [ ] `0xc3ce` - Error log
- [ ] `0xc441` - Error log array ptr
- [ ] `0xc444` - Error log array ptr
- [ ] `0xc448` - Error log array ptr
- [ ] `0xc44e` - Error log calc entry
- [ ] `0xc451` - Error log
- [ ] `0xc472` - Error log
- [ ] `0xc479` - Error log
- [ ] `0xc4a3` - Error log
- [ ] `0xc4a9` - Error log
- [ ] `0xc4b3` - Error log status

---

## Event Handlers (0xc500-0xd000)

- [ ] `0xc5ff` - Event handler
- [ ] `0xc6d3` - Event handler
- [ ] `0xc73c` - Event handler
- [ ] `0xc80d` - Event handler
- [ ] `0xc874` - Event handler
- [ ] `0xc8db` - Event handler
- [ ] `0xc942` - Event handler
- [ ] `0xc9a8` - Event handler
- [ ] `0xca0d` - System state handler - **PRIORITY**
- [ ] `0xcad5` - Event handler
- [ ] `0xcad6` - Event handler
- [ ] `0xcadf` - Event handler
- [ ] `0xcae6` - Event handler
- [ ] `0xcaec` - Event handler
- [ ] `0xcaed` - Event handler
- [ ] `0xcafb` - Event handler
- [ ] `0xcafe` - Event handler
- [ ] `0xcb05` - Event handler
- [ ] `0xcb08` - Event handler
- [ ] `0xcb0f` - Event handler
- [ ] `0xcb19` - Event handler
- [ ] `0xcb1c` - Event handler
- [ ] `0xcb26` - Event handler
- [ ] `0xcb98` - Event handler
- [ ] `0xcbf8` - Event handler
- [ ] `0xcc56` - Event handler
- [ ] `0xcc60` - Event handler
- [ ] `0xcc69` - Event handler
- [ ] `0xcc75` - Event handler
- [ ] `0xcc80` - Event handler
- [ ] `0xcc8b` - Event handler
- [ ] `0xcc92` - Event handler
- [ ] `0xcc9b` - Event handler
- [ ] `0xcca2` - Event handler
- [ ] `0xccac` - Event handler
- [ ] `0xccb3` - Event handler
- [ ] `0xcd6c` - Event handler
- [ ] `0xcdc6` - Event handler
- [ ] `0xce20` - Event handler
- [ ] `0xce23` - Event handler
- [ ] `0xced1` - Event handler
- [ ] `0xcfd5` - Event handler

---

## Power Management/PHY (0xd000-0xe000)

- [ ] `0xd02a` - Power handler
- [ ] `0xd118` - Power handler
- [ ] `0xd17a` - Power handler
- [ ] `0xd1f2` - Power handler
- [ ] `0xd1fe` - Power handler
- [ ] `0xd211` - Power handler
- [ ] `0xd21d` - Power handler
- [ ] `0xd21e` - Power handler
- [ ] `0xd26f` - Power handler
- [ ] `0xd30b` - Power handler
- [ ] `0xd3ed` - Power handler
- [ ] `0xd436` - PHY config - **PRIORITY**
- [ ] `0xd47f` - PHY handler
- [ ] `0xd4c8` - PHY handler
- [ ] `0xd511` - PHY handler
- [ ] `0xd559` - PHY handler
- [ ] `0xd630` - PHY handler
- [ ] `0xd702` - PHY handler
- [ ] `0xd78a` - PHY handler
- [ ] `0xd7cd` - PHY handler
- [ ] `0xd8d5` - PHY handler
- [ ] `0xd916` - PHY/power handler - **PRIORITY**
- [ ] `0xd956` - Power handler
- [ ] `0xda13` - Power handler
- [ ] `0xda51` - Power handler
- [ ] `0xdacc` - Power handler
- [ ] `0xdace` - Power handler
- [ ] `0xdad9` - Power handler
- [ ] `0xdae2` - Power handler
- [ ] `0xdaeb` - Power handler
- [ ] `0xdaf5` - Power handler
- [ ] `0xdaff` - Power handler
- [ ] `0xdb09` - Power handler
- [ ] `0xdb45` - Power handler
- [ ] `0xdbbb` - Power handler
- [ ] `0xdbf5` - Power handler
- [ ] `0xdc2d` - Power handler
- [ ] `0xdc9d` - Power handler
- [ ] `0xdcd4` - Power handler
- [ ] `0xdd0e` - Power handler
- [ ] `0xdd12` - Power handler
- [ ] `0xdde2` - Power handler
- [ ] `0xde16` - Power handler
- [ ] `0xde4a` - Power handler
- [ ] `0xdeb1` - Power handler
- [ ] `0xdefe` - Power handler
- [ ] `0xdf47` - Power handler
- [ ] `0xdf79` - Power handler
- [ ] `0xdfab` - Power handler

---

## Bank 1 High Address Handlers (0xe000-0xf000)

### Event Handlers (0xe000-0xe200)
- [ ] `0xe00c` - PCIe error handler
- [ ] `0xe06b` - Event handler
- [ ] `0xe0f4` - Event handler
- [ ] `0xe120` - Event handler
- [ ] `0xe19e` - Event handler
- [ ] `0xe1ee` - Command engine

### Transfer Handlers (0xe200-0xe400)
- [ ] `0xe25e` - Transfer handler
- [ ] `0xe2a6` - Transfer handler
- [ ] `0xe2c9` - Transfer handler
- [ ] `0xe352` - Transfer handler
- [ ] `0xe374` - Transfer handler
- [ ] `0xe396` - Transfer handler
- [ ] `0xe3b7` - NVMe event dispatch - **PRIORITY**

### NVMe Events (0xe400-0xe600)
- [ ] `0xe478` - NVMe event
- [ ] `0xe496` - NVMe event
- [ ] `0xe4d2` - NVMe event
- [ ] `0xe50d` - NVMe event handler
- [ ] `0xe5cb` - NVMe event
- [ ] `0xe5fe` - NVMe event
- [x] `0xe56f` - event_state_machine_e56f (in protocol.c)
- [x] `0xe677` - status_update_handler_e677 (in protocol.c)
- [ ] `0xe68f` - NVMe event
- [ ] `0xe6a7` - NVMe event
- [ ] `0xe6d2` - NVMe event
- [ ] `0xe6fc` - NVMe event handler
- [ ] `0xe711` - NVMe event
- [ ] `0xe726` - NVMe event
- [ ] `0xe730` - NVMe event
- [ ] `0xe73a` - NVMe event
- [ ] `0xe74e` - Bank 1 event handler
- [x] `0xe762` - event_queue_process_e762 (in protocol.c)
- [ ] `0xe775` - NVMe event
- [ ] `0xe77a` - NVMe event handler
- [ ] `0xe788` - NVMe event
- [ ] `0xe7ae` - NVMe event
- [ ] `0xe7c1` - NVMe event
- [ ] `0xe7d4` - NVMe event
- [ ] `0xe7e6` - NVMe event
- [ ] `0xe7fb` - Bank 1 handler
- [ ] `0xe81b` - NVMe event
- [ ] `0xe84d` - NVMe event
- [ ] `0xe85c` - NVMe event
- [ ] `0xe869` - NVMe event
- [ ] `0xe883` - NVMe event
- [ ] `0xe890` - Bank 1 handler
- [ ] `0xe89d` - NVMe event
- [ ] `0xe8a9` - PHY event handler
- [ ] `0xe8cd` - NVMe event
- [ ] `0xe8d9` - NVMe event
- [ ] `0xe8e4` - Power init handler
- [ ] `0xe8f9` - NVMe event
- [ ] `0xe902` - NVMe event handler
- [x] `0xe911` - error_handler_pcie_nvme (in error_log.c)
- [x] `0xe920` - error_clear_system_flags (in error_log.c)
- [ ] `0xe91d` - Error handler
- [ ] `0xe933` - Error handler
- [ ] `0xe957` - Error handler
- [ ] `0xe95f` - Error handler
- [ ] `0xe974` - Error handler
- [ ] `0xea7c` - Error handler
- [x] `0xed02` - pcie_state_clear_ed02 (in pcie.c)
- [ ] `0xed23` - Bank 1 handler
- [x] `0xeef9` - pcie_handler_unused_eef9 (in pcie.c)
- [x] `0xef4e` - error_handler_system_timer (in error_log.c)

---

## Poorly Named Functions Still Remaining

Functions using generic names that need better names:

### stubs.c (~52 functions)
- [ ] `helper_1579`, `helper_157d`, `helper_15d4`, `helper_15ef`
- [ ] `helper_15f1`, `helper_1646`, `helper_166f`, `helper_16e9`
- [ ] `helper_16eb`, `helper_1b0b`, `helper_1b2e`, `helper_1b30`
- [ ] `helper_1c13`, `helper_0cab`, `helper_328a`, `helper_3298`
- [ ] `helper_3578`, `handler_d676`, `handler_e3d8`, `helper_dd42`
- [ ] `helper_e6d2`, `handler_e529`, `handler_e90b`, `helper_e3b7`
- [ ] `helper_e396`, `helper_d17a`
- [ ] `FUN_CODE_1b07`, `FUN_CODE_1c9f`, `FUN_CODE_050c`, `FUN_CODE_0511`
- [ ] `FUN_CODE_11a2`, `FUN_CODE_5038`, `FUN_CODE_5043`, `FUN_CODE_5046`
- [ ] `FUN_CODE_504f`, `FUN_CODE_505d`, `FUN_CODE_5359`, `FUN_CODE_be8b`
- [ ] `FUN_CODE_dd0e`, `FUN_CODE_dd12`, `FUN_CODE_df79`, `FUN_CODE_e120`
- [ ] `FUN_CODE_e1c6`, `FUN_CODE_e73a`, `FUN_CODE_e7ae`, `FUN_CODE_e883`

### protocol.c (~103 occurrences)
- [ ] `handler_3adb`, `helper_0d78`, `helper_0db9`, `helper_1bcb`
- [ ] `helper_523c`, `helper_50db`, `helper_5409`, `helper_53a7`
- [ ] `helper_53c0`, `helper_039a`, `helper_0206`, `helper_45d0`
- [ ] `helper_0421`, `helper_0417`, `helper_16f3`, `helper_3f4a`
- [ ] `helper_1d1d`, `helper_1c9f`, `helper_4f77`, `helper_11a2`
- [ ] `helper_5359`, `helper_1cd4`, `helper_1cc8`, `helper_1c22`
- [ ] `helper_1b9a`, `helper_1b9d`, `helper_4e6d`, `helper_466b`
- [ ] `FUN_CODE_1bec`, `FUN_CODE_1b30`, `FUN_CODE_1b8d`, `FUN_CODE_1b0b`
- [ ] `FUN_CODE_1b3f`, `FUN_CODE_1c43`, `FUN_CODE_2a10`

### state_helpers.c (~59 occurrences)
- [ ] `helper_1687`, `helper_16de`, `helper_1633`, `helper_15d0`
- [ ] `helper_179d`, `handler_280a`

### usb.c (~56 occurrences)
- [ ] Various `helper_XXXX` and `handler_XXXX` functions

### scsi.c (~72 occurrences)
- [ ] Various `helper_XXXX` and `handler_XXXX` functions

---

## Priority Functions

Most critical for firmware operation:

1. `0x23f7` - Complex state machine helper (~893 bytes)
2. `0xa522` - PCIe interrupt handler
3. `0xca0d` - System state handler
4. `0xd436` - PHY configuration
5. `0xd916` - PHY/power handler
6. `0xe3b7` - NVMe event dispatch
7. `0xbcde` - Bank switch read helper
8. `0xbcaf` - Bank switch helper

---

## Notes

### Bank Switching
- Bank 0: 0x0000-0xFFFF (default)
- Bank 1: 0x8000-0xFFFF mapped to 0x10000-0x17FFF
- Dispatch stubs at 0x0300-0x0650 handle bank switching

### Register Map
- 0x9000-0x92FF: USB registers
- 0xB200-0xB4FF: PCIe registers
- 0xC400-0xC4FF: NVMe command engine
- 0xCE00-0xCEFF: SCSI/DMA registers

### Global Variables
- 0x0400-0x0700: State variables and buffers
- 0x0A00-0x0B00: System state
- IDATA 0x00-0x7F: Fast local variables
