import sys, struct, hashlib

def load(p):
    return open(p, 'rb').read()

def hdr(d):
    magic = d[0:8]
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from('<IIII', d, 8)
    header_version = struct.unpack_from('<I', d, 0x28)[0]
    cmdline = d[0x2C:0x2C+1536].split(b'\x00')[0]
    return dict(magic=magic, kernel_size=kernel_size, ramdisk_size=ramdisk_size,
                os_version=hex(os_version), header_size=header_size,
                header_version=header_version, cmdline=cmdline)

def avb_footer(d):
    # AVB footer is the last 64 bytes of the partition
    tail = d[-64:]
    if tail[:4] == b'AVBf':
        ver, orig_size, vb_off, vb_size = struct.unpack_from('>IIQQ', tail, 4)
        return dict(present=True, version=ver, original_image_size=orig_size,
                    vbmeta_offset=vb_off, vbmeta_size=vb_size, tail_hex=tail[:32].hex())
    return dict(present=False, tail_hex=tail[:32].hex())

def diff_ranges(a, b, maxranges=12):
    if len(a) != len(b):
        print('  SIZE MISMATCH: %d vs %d' % (len(a), len(b)))
        return
    ranges = []
    start = None
    for i in range(len(a)):
        if a[i] != b[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                ranges.append((start, i))
                start = None
                if len(ranges) > 200:
                    break
    if start is not None:
        ranges.append((start, len(a)))
    total = sum(e - s for s, e in ranges)
    print('  differing ranges: %d, total differing bytes: %d (%.2f%%)' % (len(ranges), total, 100.0*total/len(a)))
    for s, e in ranges[:maxranges]:
        print('    [%d .. %d)  len=%d' % (s, e, e - s))
    if len(ranges) > maxranges:
        print('    ... (%d more ranges)' % (len(ranges) - maxranges))
    return ranges

stock = load(sys.argv[1])
cust = load(sys.argv[2])
print('=' * 72)
print('STOCK :', sys.argv[1])
print('CUSTOM:', sys.argv[2])
print('-' * 72)
print('STOCK  header:', hdr(stock))
print('CUSTOM header:', hdr(cust))
print('-' * 72)
print('STOCK  avb footer:', avb_footer(stock))
print('CUSTOM avb footer:', avb_footer(cust))
print('-' * 72)
print('AVBf magic found at offsets:')
for name, d in (('stock', stock), ('custom', cust)):
    offs = []
    i = d.find(b'AVBf')
    while i != -1 and len(offs) < 8:
        offs.append(i)
        i = d.find(b'AVBf', i + 1)
    print('  %s: %s' % (name, offs))
print('-' * 72)
print('BYTE DIFF:')
diff_ranges(stock, cust)
print('-' * 72)
print('sha256 stock :', hashlib.sha256(stock).hexdigest())
print('sha256 custom:', hashlib.sha256(cust).hexdigest())
