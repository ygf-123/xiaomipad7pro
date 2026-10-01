"""Extract (exported symbol -> CRC) from a raw arm64 kernel Image, using addresses taken
from the build's System.map, then compare against the CRCs vendor modules expect
(their __versions sections).

kcrctab arrays are parallel to the ksymtab arrays (same entry counts), so entry i of
__kcrctab is the CRC of entry i of __ksymtab.
"""
import struct, sys, re, collections

SECTIONS = [
    ('__ksymtab', '__kcrctab'),
    ('__ksymtab_gpl', '__kcrctab_gpl'),
]


def load_sysmap_sections(path):
    syms = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        p = line.split()
        if len(p) >= 3:
            syms[p[2]] = int(p[0], 16)
    return syms


def main():
    img_path, sysmap_path = sys.argv[1], sys.argv[2]
    data = open(img_path, 'rb').read()
    syms = load_sysmap_sections(sysmap_path)

    # ---- calibrate vaddr -> file offset ----
    # The embedded IKCONFIG blob sits at a known file offset; kernel_config_data points at
    # (or just after) its IKCFG_ST marker. Validate the mapping with linux_banner.
    ikcfg_off = data.find(b'IKCFG_ST')
    kcd_va = syms['kernel_config_data']
    banner_va = syms['linux_banner']
    delta = None
    for cand_off in (ikcfg_off, ikcfg_off + 8):
        d = cand_off - kcd_va
        o = banner_va + d
        ok = data[o:o+14] == b'Linux version '
        print('  candidate: kernel_config_data@file %d -> delta; linux_banner lands at %d, bytes=%r %s'
              % (cand_off, o, data[o:o+16], 'OK' if ok else 'no'))
        if ok and delta is None:
            delta = d
    if delta is None:
        print('ERROR: calibration failed')
        return {}
    print('calibration OK, delta=%d' % delta)

    def foff(va):
        return va + delta

    def cstr(va):
        o = foff(va)
        e = data.find(b'\x00', o)
        return data[o:e].decode('utf-8', 'replace')

    result = {}
    for ksym_name, kcrc_name in SECTIONS:
        start_name = '__start_' + ksym_name
        stop_name = '__stop_' + ksym_name
        cstart = '__start_' + kcrc_name
        cstop = '__stop_' + kcrc_name
        if start_name not in syms or stop_name not in syms:
            print('  (missing %s/%s in System.map)' % (start_name, stop_name))
            continue
        ks_start, ks_stop = syms[start_name], syms[stop_name]
        kc_start = syms.get(cstart)
        kc_stop = syms.get(cstop)
        n_sym = (ks_stop - ks_start) // 12
        n_crc = ((kc_stop - kc_start) // 4) if (kc_start and kc_stop) else -1
        print('\n%s: 0x%x..0x%x -> %d symbols ; %s: %d crcs' % (ksym_name, ks_start, ks_stop, n_sym, kcrc_name, n_crc))
        for i in range(n_sym):
            ent = ks_start + i * 12
            o = foff(ent)
            val_off, name_off, ns_off = struct.unpack_from('<iii', data, o)
            name = cstr(ent + 4 + name_off)
            crc = None
            if kc_start and i < n_crc:
                crc = struct.unpack_from('<I', data, foff(kc_start + i * 4))[0]
            if name:
                result[name] = crc
    print('\nextracted %d exported symbols with CRC' % len(result))
    return result


if __name__ == '__main__':
    res = main()
    # save for the next step
    import json
    with open('kernel_crcs.json', 'w') as f:
        json.dump({k: v for k, v in res.items()}, f)
    print('saved kernel_crcs.json')
    for probe in ('switch_task_namespaces', 'copy_namespaces', 'free_nsproxy', 'get_net_ns_by_pid', 'task_work_add', 'binder_ioctl'):
        if probe in res:
            print('  %-40s crc=0x%08x' % (probe, res[probe] if res[probe] is not None else -1))
