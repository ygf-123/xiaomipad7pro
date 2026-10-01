#!/system/bin/sh
set -e
MB=/data/adb/magisk/magiskboot

echo "===== 1. unpack boot_a (should hold custom 6.1.141 kernel) ====="
rm -rf /data/local/tmp/wa; mkdir -p /data/local/tmp/wa; cd /data/local/tmp/wa
cp /data/local/tmp/boot_a_307.img boot.img
$MB unpack boot.img 2>&1 | head -12
echo "--- files ---"
ls -l
echo "--- kernel version ---"
strings -a kernel | grep -m1 'Linux version' || echo "(no version string)"
echo "--- kernel sha256 ---"
sha256sum kernel

echo ""
echo "===== 2. repack boot_b with boot_a kernel ====="
rm -rf /data/local/tmp/wb; mkdir -p /data/local/tmp/wb; cd /data/local/tmp/wb
cp /data/local/tmp/boot_b_307.img boot.img
$MB unpack boot.img 2>&1 | head -12
cp /data/local/tmp/wa/kernel kernel
$MB repack boot.img boot_new.img
cp /data/local/tmp/boot_b_307.img boot_new_full.img
dd if=boot_new.img of=boot_new_full.img conv=notrunc 2>/dev/null

echo ""
echo "===== 3. verify repacked boot_b ====="
$MB unpack boot_new_full.img 2>&1 | head -12
echo "--- kernel inside new boot ---"
strings -a kernel | grep -m1 'Linux version'
sha256sum boot_new.img boot_new_full.img
ls -l boot_new.img boot_new_full.img
echo ""
echo "ALL_STEPS_OK"
