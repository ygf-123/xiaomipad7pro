import sys, struct, hashlib

AVB_MAGIC = b'AVBf'

def load(p):
    return open(p, 'rb').read()

def parse_footer(d):
    tail = d[-64:]
    if tail[:4] != AVB_MAGIC:
        return None
    ver_major, ver_minor = struct.unpack_from('>II', tail, 4)
    orig_size, vb_off, vb_size = struct.unpack_from('>QQQ', tail, 12)
    return dict(ver='%d.%d' % (ver_major, ver_minor), original_image_size=orig_size,
                vbmeta_offset=vb_off, vbmeta_size=vb_size)

def parse_vbmeta(d, off):
    if off + 256 > len(d):
        return None
    blob = d[off:off+256]
    magic = blob[:4]
    if magic != b'AVB0':
        return dict(magic=magic, note='no AVB0 magic at footer offset')
    (required_libavb, auth_size, aux_size, algo_type) = struct.unpack_from('>QQQI', blob, 4)
    (hash_off, hash_size, sig_off, sig_size, pub_off, pub_size) = struct.unpack_from('>QQQQQQ', blob, 32)
    return dict(magic=magic, required_libavb=required_libavb, auth_size=auth_size,
                aux_size=aux_size, algorithm=algo_type, hash_off=hash_off, hash_size=hash_size,
                sig_off=sig_off, sig_size=sig_size, pub_off=pub_off, pub_size=pub_size)

for path in sys.argv[1:]:
    d = load(path)
    print('=' * 78)
    print(path)
    print('  size            :', len(d))
    print('  sha256          :', hashlib.sha256(d).hexdigest())
    f = parse_footer(d)
    print('  AVB footer      :', f)
    if f:
        vm = parse_vbmeta(d, f['vbmeta_offset'])
        print('  vbmeta struct   :', vm)
        # how many non-zero bytes after the kernel end (where vbmeta lives)
        ks = struct.unpack_from('<I', d, 8)[0]
        rs = struct.unpack_from('<I', d, 12)[0]
        end = 4096 + ((ks + 4095)//4096)*4096 + ((rs + 4095)//4096)*4096
        print('  kernel ends at  :', end)
        region = d[end:len(d)-64]
        nz = sum(1 for b in region if b != 0)
        print('  bytes between kernel-end and footer: %d, non-zero: %d' % (len(region), nz))
        if nz:
            idx = [i for i, b in enumerate(region) if b != 0]
            print('    first non-zero at +%d, last at +%d' % (idx[0], idx[-1]))
            print('    sample:', region[idx[0]:idx[0]+64])
