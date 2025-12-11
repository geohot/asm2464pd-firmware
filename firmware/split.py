#!/usr/bin/env python3
import struct, zlib
data = open("AS_USB4_231204_85_00_00.bin", "rb").read()
sz = struct.unpack("I", data[0:4])[0]
assert sz == len(data)-4-6

flag, checksum, crc32 = struct.unpack("<BBI", data[-6:])
assert flag == 0xA5
assert checksum == sum(data[4:-6]) & 0xff
assert crc32 == zlib.crc32(data[4:-6])

# length, flag, checksum, crc32 explained
dat = data[4:-6]

BANK_LENGTH = 0x7f6b
assert len(dat) == 0x8000 + BANK_LENGTH*2

# split this into
# base @ 0x0 (always mapped)
# bank0 @ 0x8000 (mapped as bank 0)
# bank1 @ 0x8000 (always as bank 1)

with open("../bank0.bin", "wb") as f: f.write(dat[:0xff6b])
with open("../bank1.bin", "wb") as f: f.write(dat[0xff6b:])

