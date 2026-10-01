#!/system/bin/sh
# Repack boot_b with the new kernel image and flash it.  Usage: sh apply_new_kernel.sh
set -e
MB=/data/adb/magisk/magiskboot
NEW=/data/local/tmp/kernel_new
W=/data/local/tmp/wn

echo "===== 0. new kernel ====="
ls -l "$NEW"
strings -a "$NEW" | grep -m1 'Linux version'

echo ""
echo "===== 1. repack boot_b ====="
rm -rf "$W"; mkdir -p "$W"; cd "$W"
cp /data/local/tmp/boot_b_307.img boot.img
$MB unpack boot.img
cp "$NEW" kernel
$MB repack boot.img boot_new.img
ls -l boot_new.img
sha256sum boot_new.img

echo ""
echo "===== 2. backup + flash ====="
dd if=/dev/block/by-name/boot_b of=/data/local/tmp/boot_b_preapply.img
sha256sum /data/local/tmp/boot_b_preapply.img
dd if=boot_new.img of=/dev/block/by-name/boot_b
sync
echo flashed

echo ""
echo "===== 3. readback ====="
dd if=/dev/block/by-name/boot_b of=/data/local/tmp/boot_b_rb4.img
sha256sum boot_new.img /data/local/tmp/boot_b_rb4.img
echo ""
echo "APPLY_OK"
