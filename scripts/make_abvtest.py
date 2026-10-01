"""Build a decisive test image: stock boot_b with ONE harmless byte flipped inside the
cmdline buffer (after the terminating NUL), so the image behaves identically but its
AVB hash descriptor no longer matches.

Purpose: if this boots -> the new ABL does NOT enforce the boot image's AVB hash,
so a repacked/modified boot failing means the kernel content is at fault.
If this fails -> the new ABL enforces boot image verification, which would explain
why every modified boot image bootloops regardless of kernel.
"""
import sys, hashlib

src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src, 'rb').read())
assert d[:8] == b'ANDROID!'
hdr_size = int.from_bytes(d[0x14:0x18], 'little')
hdr_ver = int.from_bytes(d[0x28:0x2C], 'little')
print('header_size=%d header_version=%d' % (hdr_size, hdr_ver))
cmdline_off = 0x2C
# cmdline is 1536 bytes; byte 0 is the NUL terminator, so flip a byte well past it
target = cmdline_off + 0x80
print('flipping byte at offset 0x%X: 0x%02X -> 0x%02X (inside cmdline padding)' % (
    target, d[target], d[target] ^ 0xFF))
assert d[cmdline_off] == 0, 'cmdline does not start with NUL - abort'
assert d[target] == 0, 'expected zero padding at target offset'
d[target] ^= 0xFF
open(dst, 'wb').write(bytes(d))
print('wrote %s' % dst)
print('src sha256: %s' % hashlib.sha256(open(src, 'rb').read()).hexdigest())
print('dst sha256: %s' % hashlib.sha256(bytes(d)).hexdigest())
