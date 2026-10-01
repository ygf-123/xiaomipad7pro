"""Full unresolved-symbol analysis across ALL module sets (vendor ramdisk = first stage,
vendor_dlkm, system_dlkm) against our GKI kernel's export list."""
import struct, sys, tarfile, json, collections, io

MODULE_NAME_LEN = 56
ENTRY = 8 + MODULE_NAME_LEN


# ---------- ELF helpers ----------
def elf_sections(data):
    e_shoff = struct.unpack_from('<Q', data, 0x28)[0]
    e_shentsize = struct.unpack_from('<H', data, 0x3A)[0]
    e_shnum = struct.unpack_from('<H', data, 0x3C)[0]
    e_shstrndx = struct.unpack_from('<H', data, 0x3E)[0]
    secs = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, sh_type = struct.unpack_from('<II', data, off)
        sh_offset, sh_size, sh_link = struct.unpack_from('<QQI', data, off + 0x18)
        secs.append((sh_name, sh_type, sh_offset, sh_size, sh_link))
    _, _, stroff, strsize, _ = secs[e_shstrndx]
    strtab = data[stroff:stroff + strsize]

    def nm(x):
        e = strtab.find(b'\x00', x)
        return strtab[x:e].decode('utf-8', 'replace')
    return [(nm(n), t, o, s, l) for (n, t, o, s, l) in secs]


def module_info(data):
    """returns (needs dict sym->crc, defined set, defined_exported set, vermagic)"""
    needs, defined, exported = {}, set(), set()
    vermagic = ''
    secs = elf_sections(data)
    strtab = None
    for sn, t, o, s, l in secs:
        if sn == '.strtab':
            strtab = data[o:o + s]
    for sn, t, o, s, l in secs:
        if sn == '__versions':
            for i in range(s // ENTRY):
                base = o + i * ENTRY
                crc = struct.unpack_from('<Q', data, base)[0] & 0xffffffff
                name = data[base + 8:base + 8 + MODULE_NAME_LEN].split(b'\x00')[0].decode('utf-8', 'replace')
                if name:
                    needs[name] = crc
        elif sn == '.modinfo':
            for m in data[o:o + s].split(b'\x00'):
                if m.startswith(b'vermagic='):
                    vermagic = m[9:].decode('utf-8', 'replace')
        elif sn == '.symtab' and strtab is not None:
            for i in range(s // 24):
                base = o + i * 24
                st_name = struct.unpack_from('<I', data, base)[0]
                st_shndx = struct.unpack_from('<H', data, base + 6)[0]
                if st_shndx != 0:
                    e = strtab.find(b'\x00', st_name)
                    defined.add(strtab[st_name:e].decode('utf-8', 'replace'))
    return needs, defined, vermagic


def cpio_entries(data):
    """Yield (name, filedata) from one or more concatenated newc cpio archives."""
    pos = 0
    n = len(data)
    while pos + 110 <= n:
        if data[pos:pos + 6] != b'070701':
            # realign: look for the next cpio magic (fragments are concatenated)
            nxt = data.find(b'070701', pos)
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
        # tolerate small alignment differences seen in vendor ramdisks
        if name.endswith('.ko'):
            for adj in (0, 2, -2, 1, -1, 3, -3):
                if data[data_off + adj:data_off + adj + 4] == b'\x7fELF':
                    data_off += adj
                    break
        filedata = data[data_off:data_off + filesize]
        pos = data_off + ((filesize + 3) // 4) * 4
        if name == 'TRAILER!!!':
            continue
        yield name, filedata


def main():
    kernel = json.load(open('kernel_crcs.json'))
    print('our kernel exports: %d symbols' % len(kernel))

    modules = {}      # name -> (needs, defined, vermagic, source)
    first_stage = []  # module basenames loaded in first stage
    sources = collections.Counter()

    # --- vendor ramdisk (first stage) ---
    ramdisk = open('backup/ramdisk.cpio', 'rb').read()
    load_list = None
    for name, data in cpio_entries(ramdisk):
        base = name.split('/')[-1]
        if base == 'modules.load':
            load_list = data.decode('utf-8', 'replace').split()
        if name.endswith('.ko'):
            try:
                needs, defined, vm = module_info(data)
                modules[base] = (needs, defined, vm, 'ramdisk')
                sources['ramdisk'] += 1
            except Exception as e:
                print('  parse fail %s: %s' % (base, e))
    print('vendor ramdisk modules: %d ; modules.load entries: %s' % (
        sources['ramdisk'], len(load_list) if load_list else 'n/a'))

    # --- vendor_dlkm ---
    tf = tarfile.open('backup/vendor_modules.tar')
    for m in tf.getmembers():
        if m.name.endswith('.ko'):
            data = tf.extractfile(m).read()
            base = m.name.split('/')[-1]
            needs, defined, vm = module_info(data)
            modules[base] = (needs, defined, vm, 'vendor_dlkm')
            sources['vendor_dlkm'] += 1

    # --- system_dlkm ---
    tf2 = tarfile.open('backup/system_dlkm.tar')
    for m in tf2.getmembers():
        if m.name.endswith('.ko'):
            data = tf2.extractfile(m).read()
            base = m.name.split('/')[-1]
            needs, defined, vm = module_info(data)
            modules[base] = (needs, defined, vm, 'system_dlkm')
            sources['system_dlkm'] += 1

    print('module sources: %s ; total distinct modules: %d' % (dict(sources), len(modules)))

    # symbols provided by any module
    provided_by_modules = set()
    for base, (needs, defined, vm, src) in modules.items():
        provided_by_modules |= defined
    print('symbols defined by modules: %d' % len(provided_by_modules))

    # CRC comparison for kernel-provided symbols
    mismatch = []
    for base, (needs, defined, vm, src) in modules.items():
        for sym, crc in needs.items():
            if sym in kernel and crc and kernel[sym] != crc:
                mismatch.append((base, sym, crc, kernel[sym]))
    print('\nCRC mismatches (module expects != our kernel): %d' % len(mismatch))
    for b, s, w, h in mismatch[:20]:
        print('   %-30s %-40s expect=0x%08x ours=0x%08x' % (b, s, w, h))

    # unresolved symbols per module
    print('\n=== UNRESOLVED SYMBOLS PER MODULE ===')
    failing = {}
    for base, (needs, defined, vm, src) in sorted(modules.items()):
        unres = [s for s in needs if s not in kernel and s not in provided_by_modules]
        if unres:
            failing[base] = unres
    print('modules with unresolved symbols: %d / %d' % (len(failing), len(modules)))

    # which first-stage modules fail?
    print('\n--- FIRST-STAGE modules that would FAIL TO LOAD ---')
    if load_list:
        for entry in load_list:
            base = entry.split('/')[-1]
            if base in failing:
                print('  %-40s %d unresolved, e.g. %s' % (base, len(failing[base]), failing[base][:5]))
        print('  (first-stage list size: %d)' % len(load_list))
    else:
        print('  (no modules.load found)')

    print('\n--- all failing modules (top 30 by unresolved count) ---')
    for base, unres in sorted(failing.items(), key=lambda kv: -len(kv[1]))[:30]:
        src = modules[base][3]
        print('  %-40s [%-11s] %3d unresolved: %s' % (base, src, len(unres), unres[:4]))

    # save
    json.dump({k: v for k, v in failing.items()}, open('unresolved.json', 'w'))


main()
