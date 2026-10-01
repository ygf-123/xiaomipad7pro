#!/system/bin/sh
echo "===== KERNEL ====="
uname -a
echo ""
echo "===== EXPORT COUNT (should be ~20000+ if whitelist kept) ====="
grep -c '__ksymtab_' /proc/kallsyms 2>/dev/null
echo ""
echo "===== VINTF-relevant config (SYSVIPC must look disabled) ====="
zcat /proc/config.gz 2>/dev/null | grep -E '^CONFIG_SYSVIPC|^# CONFIG_SYSVIPC|^CONFIG_IPC_NS|^CONFIG_PID_NS|^CONFIG_USER_NS|^CONFIG_POSIX_MQUEUE'
echo ""
echo "===== TRIM setting ====="
zcat /proc/config.gz 2>/dev/null | grep -E 'TRIM_UNUSED_KSYMS|UNUSED_KSYMS_WHITELIST'
echo ""
echo "===== loaded modules count ====="
lsmod 2>/dev/null | wc -l
echo ""
echo "===== unshare / namespace test ====="
unshare -p -f true && echo "PID_NS OK" || echo "PID_NS FAIL"
unshare -i true && echo "IPC_NS OK" || echo "IPC_NS FAIL"
echo ""
echo "===== droidspaces check ====="
/data/local/Droidspaces/bin/droidspaces check 2>&1 | head -40
echo ""
echo "===== try starting the debian container ====="
/data/local/Droidspaces/bin/droidspaces --config=/data/local/Droidspaces/Containers/debian/container.config start 2>&1 | tail -20
