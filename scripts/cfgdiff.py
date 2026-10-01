import sys

def parse(path):
    d = {}
    order = []
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('# ') and line.endswith(' is not set'):
            k = line[2:-len(' is not set')]
            d[k] = 'n'
        elif '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            d[k] = v
        # comments/headers ignored
    return d

a_path, b_path = sys.argv[1], sys.argv[2]   # a = stock(reference), b = custom
a = parse(a_path)
b = parse(b_path)

print('=' * 90)
print('STOCK (reference):', a_path, len(a), 'symbols')
print('CUSTOM           :', b_path, len(b), 'symbols')
print('=' * 90)

only_a = sorted(set(a) - set(b))
only_b = sorted(set(b) - set(a))
diff = sorted(k for k in set(a) & set(b) if a[k] != b[k])

print('\n### symbols present only in STOCK (%d) — first 60 ###' % len(only_a))
for k in only_a[:60]:
    print('  %-55s stock=%s' % (k, a[k]))

print('\n### symbols present only in CUSTOM (%d) — first 60 ###' % len(only_b))
for k in only_b[:60]:
    print('  %-55s custom=%s' % (k, b[k]))

print('\n### value differences (%d) ###' % len(diff))
# highlight the dangerous direction: y in stock but not in custom
danger = [k for k in diff if a[k] == 'y' and b[k] != 'y']
gain   = [k for k in diff if b[k] == 'y' and a[k] != 'y']
other  = [k for k in diff if k not in danger and k not in gain]
print('\n--- [A] enabled in STOCK but NOT in custom (%d) <<< most suspicious ---' % len(danger))
for k in danger:
    print('  %-58s stock=%s custom=%s' % (k, a[k], b[k]))
print('\n--- [B] enabled in CUSTOM but NOT in stock (%d) ---' % len(gain))
for k in gain:
    print('  %-58s stock=%s custom=%s' % (k, a[k], b[k]))
print('\n--- [C] other value differences (%d) — first 40 ---' % len(other))
for k in other[:40]:
    print('  %-58s stock=%s custom=%s' % (k, a[k], b[k]))
