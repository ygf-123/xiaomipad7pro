"""Extract raw kernel from a boot image (header v4) and/or patch the embedded IKCONFIG blob.

Patching strategy: rewrite the gzip-compressed config so the blob has EXACTLY the same
byte length as the original (auto-tuned via comment padding), so nothing in the kernel
image shifts and no trailing-garbage tolerance is needed from the kernel decompressor.
"""
import struct, gzip, sys

IKCFG_ST = b'IKCFG_ST'
IKCFG_ED = b'IKCFG_ED'


def extract_kernel(boot_path, out_path):
    d = open(boot_path, 'rb').read()
    assert d[:8] == b'ANDROID!', 'not a boot image'
    kernel_size = struct.unpack_from('<I', d, 8)[0]
    hdr_ver = struct.unpack_from('<I', d, 0x28)[0]
    kernel = d[4096:4096 + kernel_size]
    open(out_path, 'wb').write(kernel)
    print('boot=%s header_v=%d kernel_size=%d -> %s' % (boot_path, hdr_ver, kernel_size, out_path))
    return kernel


def find_ikcfg(data):
    i = data.find(IKCFG_ST)
    j = data.find(IKCFG_ED)
    if i < 0 or j < 0 or j < i:
        return None, None, None
    return i, j, data[i + len(IKCFG_ST):j]


def gz(data, level=9):
    return gzip.compress(data, compresslevel=level, mtime=0)


def patch_ikcfg(kernel_path, out_path, edits, verbose=True):
    data = bytearray(open(kernel_path, 'rb').read())
    i, j, blob = find_ikcfg(data)
    if i is None:
        print('ERROR: no IKCFG found in', kernel_path)
        return False
    if verbose:
        print('IKCFG_ST @%d  IKCFG_ED @%d  blob=%d bytes' % (i, j, len(blob)))
    cfg = gzip.decompress(bytes(blob)).decode('utf-8', 'replace')
    lines = cfg.split('\n')
    changed = []
    for old, new in edits:
        for idx, line in enumerate(lines):
            if line == old:
                lines[idx] = new
                changed.append((old, new))
                break
        else:
            print('  note: line not found (already patched?): %r' % old)
    newcfg = ('\n'.join(lines)).encode('utf-8')

    target = len(blob)
    newblob = None
    # Droppable lines: pure comments that are not real config entries
    drop_idx = [idx for idx, l in enumerate(lines)
                if l.startswith('#') and not l.startswith('# CONFIG_')]
    # 1) try to hit the exact size: drop k comment lines, then pad with a comment
    for k in range(0, min(len(drop_idx), 40) + 1):
        kept = [l for idx, l in enumerate(lines) if idx not in set(drop_idx[:k])]
        base = ('\n'.join(kept)).encode('utf-8')
        for pad in range(0, 4000):
            cand_text = base + (b'\n# ' + b'p' * pad + b'\n' if pad else b'')
            for level in (9, 8, 7, 6):
                c = gz(cand_text, level)
                if len(c) == target:
                    newblob = c
                    if verbose:
                        print('exact size match: dropped %d comment line(s), pad=%d level=%d -> %d bytes'
                              % (k, pad, level, len(c)))
                    break
            if newblob:
                break
        if newblob:
            break
    if newblob is None:
        # 2) fall back: shortest candidate, zero-padded
        best = min((gz(newcfg, lv) for lv in (9, 8, 7, 6, 5, 4, 3, 2, 1)), key=len)
        if len(best) > target:
            print('ERROR: cannot fit (new %d > original %d)' % (len(best), target))
            return False
        print('WARNING: no exact match; zero-padding %d -> %d' % (len(best), target))
        newblob = best + b'\x00' * (target - len(best))

    data[i + len(IKCFG_ST):j] = newblob
    open(out_path, 'wb').write(bytes(data))

    # verify round trip
    _, _, blob2 = find_ikcfg(data)
    assert len(blob2) == len(blob), 'blob length changed!'
    cfg2 = gzip.decompress(bytes(blob2)).decode('utf-8', 'replace')
    for old, new in changed:
        assert new in cfg2, 'patch missing after recompress'
        assert old not in cfg2, 'old line still present'
    if verbose:
        print('verified: %d edits applied, blob length unchanged (%d)' % (len(changed), len(blob2)))
        for old, new in changed:
            print('   %r -> %r' % (old, new))
        print('wrote', out_path)
    return True


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'extract':
        extract_kernel(sys.argv[2], sys.argv[3])
    elif cmd == 'patch':
        edits = []
        for spec in sys.argv[4:]:
            old, new = spec.split('||')
            edits.append((old, new))
        sys.exit(0 if patch_ikcfg(sys.argv[2], sys.argv[3], edits) else 1)
    elif cmd == 'show':
        d = open(sys.argv[2], 'rb').read()
        i, j, blob = find_ikcfg(d)
        cfg = gzip.decompress(bytes(blob)).decode('utf-8', 'replace')
        keys = sys.argv[3:]
        for line in cfg.split('\n'):
            if any(line.startswith(k) for k in keys):
                print(line)
