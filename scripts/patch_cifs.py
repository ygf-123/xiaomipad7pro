"""Patch the vendor-ramdisk cpio in place: rewrite cifs.ko's expected symbol CRCs so they
match our kernel's kcrctab values (the ABI-relevant call signatures are identical between
6.1.138 and 6.1.141; only struct-derived CRCs changed).

The cpio is modified byte-for-byte in place, so its layout/size never change.
"""
import struct, json, sys, hashlib

CPIO = 'backup/ramdisk.cpio'
OUT = 'ramdisk_patched.cpio'
KERNEL_CRCS = 'kernel_crcs.json'
TARGET = 'cifs.ko'
MODULE_NAME_LEN = 56
ENTRY = 8 + MODULE_NAME_LEN


def cpio_entries(data):
    pos = 0
    n = len(data)
    while pos + 110 <= n:
        if data[pos:pos + 6] != b'070701':
            nxt = data.find(b'070701', pos + 1)
            if nxt < 0:
                break
            pos = nxt
            continue
        hdr = data[pos:pos + 110]

        def f(o):
            return int(hdr[o:o + 8], 16)
        filesize = f(54)
        namesize = f(94)
        name = data[pos + 110:pos + 110 + namesize - 1].decode('utf-8', 'replace')
        data_off = pos + 110 + ((namesize + 3) // 4) * 4
        if name.endswith('.ko'):
            for adj in (0, 2, -2, 1, -1, 3, -3):
                if data[data_off + adj:data_off + adj + 4] == b'\x7fELF':
                    data_off += adj
                    break
        yield name, data_off, filesize
        pos = data_off + ((filesize + 3) // 4) * 4


def elf_sections(data, base, size):
    e_shoff = struct.unpack_from('<Q', data, base + 0x28)[0]
    e_shentsize = struct.unpack_from('<H', data, base + 0x3A)[0]
    e_shnum = struct.unpack_from('<H', data, base + 0x3C)[0]
    e_shstrndx = struct.unpack_from('<H', data, base + 0x3E)[0]
    secs = []
    for i in range(e_shnum):
        off = base + e_shoff + i * e_shentsize
        sh_name, sh_type = struct.unpack_from('<II', data, off)
        sh_offset, sh_size = struct.unpack_from('<QQ', data, off + 0x18)
        secs.append((sh_name, sh_type, sh_offset, sh_size))
    _, _, stroff, strsize = secs[e_shstrndx]
    strtab = bytes(data[base + stroff:base + stroff + strsize])

    def nm(x):
        e = strtab.find(b'\x00', x)
        return strtab[x:e].decode('utf-8', 'replace')
    return [(nm(n), t, o, s) for (n, t, o, s) in secs]


def main():
    kernel = json.load(open(KERNEL_CRCS))
    data = bytearray(open(CPIO, 'rb').read())
    print('cpio: %d bytes, sha256=%s' % (len(data), hashlib.sha256(bytes(data)).hexdigest()[:16]))

    hit = None
    for name, off, size in cpio_entries(data):
        if name.split('/')[-1] == TARGET:
            hit = (name, off, size)
            break
    if not hit:
        print('ERROR: %s not found in cpio' % TARGET)
        return 1
    name, base, size = hit
    print('found %s at cpio offset %d, size %d' % (name, base, size))
    assert data[base:base + 4] == b'\x7fELF'

    patched = []
    for secname, shtype, shoff, shsize in elf_sections(data, base, size):
        if secname != '__versions':
            continue
        print('__versions section: file offset %d, size %d (%d entries)' % (shoff, shsize, shsize // ENTRY))
        for i in range(shsize // ENTRY):
            ent = base + shoff + i * ENTRY
            crc = struct.unpack_from('<Q', data, ent)[0]
            sym = bytes(data[ent + 8:ent + 8 + MODULE_NAME_LEN]).split(b'\x00')[0].decode('utf-8', 'replace')
            if sym in kernel and (crc & 0xffffffff) != kernel[sym]:
                old = crc & 0xffffffff
                struct.pack_into('<Q', data, ent, kernel[sym])
                patched.append((sym, old, kernel[sym]))
    if not patched:
        print('nothing to patch')
    for sym, old, new in patched:
        print('  patched %-24s 0x%08x -> 0x%08x' % (sym, old, new))

    open(OUT, 'wb').write(bytes(data))
    print('wrote %s (size %d, unchanged=%s)' % (OUT, len(data), len(data) == len(open(CPIO, 'rb').read())))

    # verify
    d2 = bytearray(open(OUT, 'rb').read())
    for name, off, size in cpio_entries(d2):
        if name.split('/')[-1] != TARGET:
            continue
        ok = True
        for secname, shtype, shoff, shsize in elf_sections(d2, off, size):
            if secname != '__versions':
                continue
            for i in range(shsize // ENTRY):
                ent = off + shoff + i * ENTRY
                crc = struct.unpack_from('<Q', d2, ent)[0] & 0xffffffff
                sym = bytes(d2[ent + 8:ent + 8 + MODULE_NAME_LEN]).split(b'\x00')[0].decode('utf-8', 'replace')
                if sym in kernel and crc != kernel[sym]:
                    print('  STILL MISMATCHED: %s 0x%08x vs 0x%08x' % (sym, crc, kernel[sym]))
                    ok = False
        print('verify: %s' % ('OK - all shared symbols now match our kernel' if ok else 'FAILED'))
    return 0


sys.exit(main())
