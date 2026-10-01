#!/system/bin/sh
echo "===== module vermagic (vendor modules) ====="
for m in binder_prio.ko camera.ko aw882xx_dlkm.ko; do
  f=/vendor/lib/modules/$m
  [ -f "$f" ] && { echo "--- $m ---"; strings -a "$f" | grep -m2 'vermagic='; }
done
echo ""
echo "===== module signing / force load config ====="
zcat /proc/config.gz | grep -E 'MODULE_FORCE_LOAD|MODULE_SIG|MODVERSIONS|MODULE_SIG_PROTECT' || true
echo ""
echo "===== loaded modules count ====="
lsmod 2>/dev/null | wc -l
echo "--- first 5 ---"
lsmod 2>/dev/null | head -6
echo ""
echo "===== boot properties ====="
getprop ro.boot.bootreason
getprop ro.boot.verifiedbootstate
getprop ro.boot.flash.locked
getprop ro.boot.vbmeta.device_state
getprop ro.boot.veritymode
getprop ro.boot.kmi 2>/dev/null
echo ""
echo "===== where are modules mounted from ====="
mount | grep -E 'vendor|dlkm' | head -10
echo ""
echo "===== vendor_boot ramdisk has modules? ====="
ls /lib/modules 2>/dev/null | head -5
echo ""
echo "===== slot state via bootctl ====="
bootctl get-current-slot 2>/dev/null
bootctl get-slot-suffix 2>/dev/null
echo ""
echo "===== last boot time ====="
uptime
