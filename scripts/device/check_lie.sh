#!/system/bin/sh
echo "===== /proc/config.gz now says (should show the LIE: CONFIG_SYSVIPC=y) ====="
zcat /proc/config.gz | grep -E 'SYSVIPC'
echo ""
echo "===== sanity: a few other entries ====="
zcat /proc/config.gz | grep -E '^CONFIG_(IPC_NS|PID_NS|USER_NS|DEVTMPFS)' || echo "(none of those set - expected for stock)"
echo ""
echo "===== is the running kernel still the stock one? ====="
uname -r
echo ""
echo "===== config blob still readable/decompressible? ====="
zcat /proc/config.gz | wc -l
