#!/system/bin/sh
set -e
MB=/data/adb/magisk/magiskboot
echo "===== magiskboot ====="
ls -l $MB
$MB 2>&1 | head -5 || true

echo "===== unpack boot_b ====="
rm -rf /data/local/tmp/work
mkdir -p /data/local/tmp/work
cd /data/local/tmp/work
cp /data/local/tmp/boot_b_307.img boot.img
$MB unpack boot.img 2>&1 || true
echo "--- files ---"
ls -l

echo "===== stock kernel in boot_b ====="
strings -a kernel 2>/dev/null | grep -m2 'Linux version' || echo "(no version string found in raw kernel)"

echo "===== ramdisk: magisk present? ====="
$MB cpio ramdisk.cpio "exists magisk" 2>&1 || true
$MB cpio ramdisk.cpio "exists overlay.d" 2>&1 || true
$MB cpio ramdisk.cpio "exists .backup" 2>&1 || true

echo "===== init_boot_b (where Magisk really lives?) ====="
dd if=/dev/block/by-name/init_boot_b of=/data/local/tmp/init_boot_b.img bs=1M 2>/dev/null
mkdir -p /data/local/tmp/work_ib && cd /data/local/tmp/work_ib
cp /data/local/tmp/init_boot_b.img init_boot.img
$MB unpack init_boot.img 2>&1 || true
ls -l
$MB cpio ramdisk.cpio "exists magisk" 2>&1 || true

echo "===== current slot / bootloader ====="
getprop ro.boot.slot_suffix
