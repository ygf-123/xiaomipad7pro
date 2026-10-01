"""Parse an Android AVB vbmeta image (or a dumped vbmeta partition) and list descriptors."""
import struct, sys, hashlib, re

def u32(b, o): return struct.unpack_from('>I', b, o)[0]
def u64(b, o): return struct.unpack_from('>Q', b, o)[0]

def parse(path):
    d = open(path, 'rb').read()
    print('=' * 78)
    print('file: %s (%d bytes)' % (path, len(d)))
    off = d.find(b'AVB0')
    print('AVB0 magic at offset %d' % off)
    if off < 0:
        return
    b = d[off:]
    (ver_major, ver_minor, auth_size, aux_size, algo) = struct.unpack_from('>IIQQI', b, 4)
    hash_off, hash_size = u32(b, 32), u32(b, 36)
    sig_off, sig_size = u32(b, 40), u32(b, 44)
    pub_off, pub_size = u32(b, 48), u32(b, 52)
    desc_off, desc_size = u32(b, 64), u32(b, 68)
    rollback_index = u64(b, 72)
    flags = u32(b, 80)
    release = b[88:88+48].split(b'\x00')[0].decode('utf-8', 'replace')
    print('  libavb version : %d.%d' % (ver_major, ver_minor))
    print('  algorithm_type : %d (0=none,1=sha256_rsa4096,2=sha256_rsa2048,3=sha256_rsa8192,4=sha512_rsa4096)' % algo)
    print('  auth block     : %d, aux block: %d' % (auth_size, aux_size))
    print('  hash  off/size : %d/%d' % (hash_off, hash_size))
    print('  sig   off/size : %d/%d' % (sig_off, sig_size))
    print('  pubkey off/size: %d/%d' % (pub_off, pub_size))
    print('  descriptors    : off=%d size=%d' % (desc_off, desc_size))
    print('  rollback_index : %d' % rollback_index)
    print('  flags          : 0x%08x  (bit0 HASHTREE_DISABLED=%s, bit1 VERIFICATION_DISABLED=%s)'
          % (flags, bool(flags & 1), bool(flags & 2)))
    print('  release string : %r' % release)

    pos = desc_off
    end = desc_off + desc_size
    n = 0
    while pos + 16 <= end and n < 64:
        tag = u64(b, pos)
        num = u64(b, pos + 8)
        data = b[pos+16:pos+16+num]
        name = 'unknown'
        extra = ''
        if tag == 2:  # hash descriptor
            name = 'HASH'
            strs = re.findall(rb'[ -~]{3,}', data)
            parts = [s.decode() for s in strs]
            # digest is the longest binary blob; report printable strings
            image_size = u64(data, 4) if len(data) >= 12 else -1
            extra = 'image_size=%d strings=%s' % (image_size, parts)
        elif tag == 3:
            name = 'HASHTREE'
            strs = re.findall(rb'[ -~]{3,}', data)
            extra = 'strings=%s' % [s.decode() for s in strs]
        elif tag == 0:
            name = 'PROPERTY'
            strs = re.findall(rb'[ -~]{3,}', data)
            extra = 'strings=%s' % [s.decode() for s in strs]
        elif tag == 1:
            name = 'HASHTREE'  # 1 = hashtree descriptor
            strs = re.findall(rb'[ -~]{3,}', data)
            extra = 'strings=%s' % [s.decode() for s in strs]
        print('  [desc %2d] tag=%d (%s) bytes=%d  %s' % (n, tag, name, num, extra))
        pos += 16 + num
        n += 1
    if n == 0:
        print('  (no descriptors)')

    # also report the digest of a partition image if given
    for img in sys.argv[2:]:
        dd = open(img, 'rb').read()
        print('  image %s sha256=%s (size %d)' % (img, hashlib.sha256(dd).hexdigest(), len(dd)))

parse(sys.argv[1])
