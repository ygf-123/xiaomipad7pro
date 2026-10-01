#!/system/bin/sh
echo "===== BUILD ====="
getprop ro.build.display.id
getprop ro.build.version.incremental
getprop ro.build.version.release
getprop ro.build.version.security_patch
getprop ro.product.device
getprop ro.product.model
echo "===== BOOT STATE ====="
getprop ro.boot.slot_suffix
getprop ro.boot.verifiedbootstate
getprop ro.boot.flash.locked
getprop ro.boot.hardware
echo "===== KERNEL ====="
uname -a
cat /proc/version
echo "===== KERNEL CONFIG (namespaces) ====="
if [ -r /proc/config.gz ]; then
  zcat /proc/config.gz | grep -E 'CONFIG_(PID_NS|IPC_NS|USER_NS|SYSVIPC|NET_NS|UTS_NS|POSIX_MQUEUE|IKCONFIG|DEVTMPFS|TMPFS_XATTR)='
else
  echo "NO /proc/config.gz"
fi
echo "===== UNSHARE TEST ====="
command -v unshare || echo "no unshare binary"
unshare -p -f true 2>&1 || echo "pid-ns unshare FAILED"
unshare -i true 2>&1 || echo "ipc-ns unshare FAILED"
echo "===== ROOT ====="
id
command -v magisk ksud apd 2>/dev/null
magisk -v 2>/dev/null
magisk -V 2>/dev/null
echo "--- modules ---"
ls /data/adb/modules 2>/dev/null
echo "===== PARTITIONS ====="
ls -l /dev/block/by-name/ | grep -Ei 'boot|vbmeta|dtbo|super'
echo "===== DMESG KERNEL BANNER ====="
dmesg 2>/dev/null | head -20
