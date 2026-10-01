"""Compare vendor module expected CRCs (__versions) with our GKI kernel's CRCs
(kernel_crcs.json extracted from the Image)."""
import struct, sys, tarfile, json, collections

MODULE_NAME_LEN = 56
ENTRY = 8 + MODULE_NAME_LEN


def parse_elf_sections(data):
    e_shoff = struct.unpack_from('<Q', data, 0x28)[0]
    e_shentsize = struct.unpack_from('<H', data, 0x3A)[0]
    e_shnum = struct.unpack_from('<H', data, 0x3C)[0]
    e_shstrndx = struct.unpack_from('<H', data, 0x3E)[0]
    secs = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, sh_type = struct.unpack_from('<II', data, off)
        sh_offset, sh_size = struct.unpack_from('<QQ', data, off + 0x18)
        secs.append((sh_name, sh_type, sh_offset, sh_size))
    _, _, stroff, strsize = secs[e_shstrndx]
    strtab = data[stroff:stroff + strsize]

    def nm(x):
        e = strtab.find(b'\x00', x)
        return strtab[x:e].decode('utf-8', 'replace')
    return [(nm(n), t, o, s) for (n, t, o, s) in secs]


def module_versions(data):
    out = {}
    for secname, shtype, off, size in parse_elf_sections(data):
        if secname == '__versions':
            for i in range(size // ENTRY):
                base = off + i * ENTRY
                crc = struct.unpack_from('<Q', data, base)[0]
                sname = data[base + 8:base + 8 + MODULE_NAME_LEN].split(b'\x00')[0].decode('utf-8', 'replace')
                if sname:
                    out[sname] = crc & 0xffffffff
    return out


def module_defined(data):
    """names defined (not undefined) in this module's symtab"""
    out = set()
    for secname, shtype, off, size in parse_elf_sections(data):
        if secname == '.symtab':
            n = size // 24
            for i in range(n):
                base = off + i * 24
                st_name = struct.unpack_from('<I', data, base)[0]
                st_shndx = struct.unpack_from('<H', data, base + 6)[0]
                if st_shndx != 0:  # not SHN_UNDEF
                    for sn, t2, o2, s2 in parse_elf_sections(data):
                        pass
    return out


def main():
    tar_path, crcs_path = sys.argv[1], sys.argv[2]
    kernel = json.load(open(crcs_path))
    print('our kernel exports: %d symbols' % len(kernel))

    tf = tarfile.open(tar_path)
    members = [m for m in tf.getmembers() if m.name.endswith('.ko')]
    print('vendor modules: %d' % len(members))

    need = collections.defaultdict(set)
    per_mod = {}
    mod_defined_syms = set()
    for m in members:
        data = tf.extractfile(m).read()
        vers = module_versions(data)
        per_mod[m.name] = vers
        for k, v in vers.items():
            need[k].add(v)
        # collect names this module defines (for "missing" filtering)
        for secname, shtype, off, size in parse_elf_sections(data):
            if secname == '.symtab':
                strtab_off = strtab_size = None
                # find linked strtab
                for sn, t2, o2, s2 in parse_elf_sections(data):
                    if sn == '.strtab':
                        strtab_off, strtab_size = o2, s2
                if strtab_off is None:
                    continue
                strtab = data[strtab_off:strtab_off + strtab_size]
                for i in range(size // 24):
                    base = off + i * 24
                    st_name = struct.unpack_from('<I', data, base)[0]
                    st_shndx = struct.unpack_from('<H', data, base + 6)[0]
                    if st_shndx != 0:
                        e = strtab.find(b'\x00', st_name)
                        mod_defined_syms.add(strtab[st_name:e].decode('utf-8', 'replace'))

    print('distinct symbols required by vendor modules: %d' % len(need))
    print('symbols defined by vendor modules themselves: %d' % len(mod_defined_syms))

    missing_kernel, missing_but_module, mismatch, ok, zero = [], [], [], 0, 0
    for sym, crcs in sorted(need.items()):
        want = sorted(crcs)
        if all(c == 0 for c in crcs):
            zero += 1
            continue
        if sym in kernel:
            if kernel[sym] in crcs:
                ok += 1
            else:
                mismatch.append((sym, want, kernel[sym]))
        else:
            if sym in mod_defined_syms:
                missing_but_module.append(sym)
            else:
                missing_kernel.append((sym, want))

    print('\n=== RESULT ===')
    print('  CRC match with our kernel          : %d' % ok)
    print('  CRC MISMATCH with our kernel       : %d' % len(mismatch))
    print('  NOT in our kernel, provided by other modules: %d' % len(missing_but_module))
    print('  NOT in our kernel and not in modules (REAL missing): %d' % len(missing_kernel))
    print('  crc==0 (unversioned)               : %d' % zero)

    if mismatch:
        print('\n--- CRC MISMATCHES (first 50) ---')
        for sym, want, have in mismatch[:50]:
            print('  %-50s modules_expect=%s our_kernel=0x%08x' % (sym, ['0x%08x' % w for w in want], have))
    if missing_kernel:
        print('\n--- REALLY MISSING SYMBOLS (first 50) ---')
        for sym, want in missing_kernel[:50]:
            print('  %-50s modules_expect=%s' % (sym, ['0x%08x' % w for w in want]))

    bad = {s for s, _, _ in mismatch} | {s for s, _ in missing_kernel}
    if bad:
        print('\n--- affected modules (first 30) ---')
        n = 0
        for mod, vers in sorted(per_mod.items()):
            hit = bad & set(vers)
            if hit:
                print('  %-42s %d bad: %s' % (mod, len(hit), sorted(hit)[:3]))
                n += 1
                if n >= 30:
                    break


main()
