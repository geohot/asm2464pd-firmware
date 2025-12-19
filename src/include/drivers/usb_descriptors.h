/*
 * USB Descriptors for ASM2464PD
 *
 * Descriptor tables stored in code ROM and DMA'd to USB buffer
 * when host requests them via GET_DESCRIPTOR control transfer.
 *
 * Descriptor handling flow:
 *   1. Host sends GET_DESCRIPTOR setup packet
 *   2. Hardware writes setup packet to 0x9E00-0x9E07
 *   3. Firmware reads REG_USB_SETUP_VALUE_H (0x9E03) for descriptor type
 *   4. Firmware calls usb_get_descriptor() to get ROM pointer
 *   5. Firmware writes pointer to REG_USB_EP_BUF_HI/LO (0x905B/0x905C)
 *   6. Firmware triggers DMA via REG_USB_DMA_TRIGGER (0x9092)
 *   7. Hardware DMAs descriptor from ROM to USB buffer
 */
#ifndef USB_DESCRIPTORS_H
#define USB_DESCRIPTORS_H

#include "types.h"
#include "registers.h"  /* For USB_DESC_TYPE_*, USB_REQ_* constants */

/* Descriptor arrays in code ROM */
extern __code const uint8_t usb_device_descriptor[18];
extern __code const uint8_t usb_config_descriptor[32];
extern __code const uint8_t usb_string_descriptor_0[4];   /* Language ID (0x0409 = US English) */
extern __code const uint8_t usb_string_descriptor_1[26];  /* Serial number */
extern __code const uint8_t usb_string_descriptor_2[16];  /* Manufacturer */
extern __code const uint8_t usb_string_descriptor_3[20];  /* Product name */
extern __code const uint8_t usb_bos_descriptor[22];       /* BOS descriptor (USB 3.0) */

/*
 * usb_get_descriptor - Get descriptor pointer and length by type and index
 *
 * @type:   Descriptor type (USB_DESC_TYPE_DEVICE, USB_DESC_TYPE_CONFIG, etc.)
 * @index:  Descriptor index (for string descriptors: 0=language, 1=serial, etc.)
 * @length: Output parameter - receives descriptor length in bytes
 *
 * Returns pointer to descriptor in code ROM, or NULL if not found.
 * Sets *length to 0 if descriptor not found.
 */
__code const uint8_t* usb_get_descriptor(uint8_t type, uint8_t index, uint8_t *length);

#endif /* USB_DESCRIPTORS_H */
