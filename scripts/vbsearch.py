"""Decisive check: is the boot partition hash-covered by vbmeta, and does the stock
boot image match that hash? Also list which partitions appear in the descriptors."""
import hashlib, re, struct, sys

vb = open(sys.argv[1], 'rb').read()
print('vbmeta: %s (%d bytes)' % (sys.argv[1], len(vb)))

# --- header hexdump to locate fields ---
print('\n--- header words (offset: u32) ---')
for o in range(0, 96, 4):
    print('  %3d: 0x%08x  (%d)' % (o, struct.unpack_from('>I', vb, o)[0], struct.unpack_from('>I', vb, o)[0]))

# --- strings in vbmeta (partition names etc.) ---
print('\n--- printable strings (>=4 chars) ---')
for m in re.finditer(rb'[ -~]{4,}', vb):
    s = m.group(0).decode()
    if len(s) >= 4:
        print('  @%-7d %r' % (m.start(), s))

# --- does the stock boot image digest appear? ---
for img in sys.argv[2:]:
    d = open(img, 'rb').read()
    print('\n--- searching digests of %s (size %d) ---' % (img, len(d)))
    cands = {
        'full-file': len(d),
        'kernel-end(36487168)': 36487168,
    }
    for name, size in cands.items():
        if size > len(d):
            continue
        h = hashlib.sha256(d[:size]).digest()
        pos = vb.find(h)
        print('  sha256(first %d bytes) = %s  -> %s' % (size, h.hex(), ('FOUND at %d' % pos) if pos >= 0 else 'not found'))
