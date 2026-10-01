import gzip, sys, os

KEYS = ['CONFIG_PID_NS','CONFIG_IPC_NS','CONFIG_USER_NS','CONFIG_SYSVIPC','CONFIG_NET_NS',
        'CONFIG_UTS_NS','CONFIG_POSIX_MQUEUE','CONFIG_DEVTMPFS','CONFIG_TMPFS_XATTR',
        'CONFIG_TMPFS_POSIX_ACL','CONFIG_IKCONFIG','CONFIG_LOCALVERSION','CONFIG_IP_SET',
        'CONFIG_NETFILTER_XT_MATCH_ADDRTYPE','CONFIG_NETFILTER_XT_TARGET_LOG']

def extract(path):
    data = open(path,'rb').read()
    i = data.find(b'IKCFG_ST')
    j = data.find(b'IKCFG_ED')
    print('=' * 70)
    print('FILE :', path, '(%d bytes)' % len(data))
    if i < 0 or j < 0:
        print('  -> no embedded IKCONFIG found (IKCFG_ST=%d IKCFG_ED=%d)' % (i, j))
        return None
    blob = data[i+8:j]
    cfg = None
    try:
        cfg = gzip.decompress(blob).decode('utf-8', 'replace')
    except Exception as e:
        print('  -> gzip failed (%s), trying raw' % e)
        try:
            cfg = blob.decode('utf-8', 'replace')
        except Exception as e2:
            print('  -> raw decode failed (%s)' % e2)
            return None
    lines = cfg.splitlines()
    print('  -> config extracted, %d lines' % len(lines))
    # kernel version string
    for l in lines:
        if l.startswith('CONFIG_LOCALVERSION=') or l.startswith('# Linux/') :
            print('  ', l)
    print('  --- droidspaces related ---')
    for k in KEYS:
        hit = [l for l in lines if l.startswith(k + '=') or l == ('# %s is not set' % k)]
        print('   %-42s %s' % (k, hit[0] if hit else '(absent)'))
    return cfg

if __name__ == '__main__':
    for p in sys.argv[1:]:
        if os.path.exists(p):
            c = extract(p)
            if c and len(sys.argv) > 2:
                out = os.path.splitext(p)[0] + '.config'
                open(out, 'w', encoding='utf-8').write(c)
                print('  -> saved', out)
        else:
            print('MISSING:', p)
