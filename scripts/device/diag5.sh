#!/system/bin/sh
echo "===== init: kernel config check strings ====="
strings -a /system/bin/init 2>/dev/null | grep -iE 'config\.gz|kernel config|config is not set|compatible kernel|kernel.*config' | head -30
echo ""
echo "===== libvintf: kernel config checker ====="
for f in /system/lib64/libvintf.so /system/lib64/libvintf-impl.so; do
  [ -f "$f" ] || continue
  echo "### $f"
  strings -a "$f" 2>/dev/null | grep -iE 'config\.gz|CONFIG_|kernel version|KernelConfig' | head -20
done
echo ""
echo "===== /proc/config.gz readability ====="
ls -l /proc/config.gz
zcat /proc/config.gz | grep -E '^CONFIG_SYSVIPC|^CONFIG_IPC_NS|^# CONFIG_SYSVIPC'
echo ""
echo "===== how many CONFIG_ strings does init have ====="
strings -a /system/bin/init 2>/dev/null | grep -c 'CONFIG_'
