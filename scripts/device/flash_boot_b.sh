#!/system/bin/sh
set -e
MB=/data/adb/magisk/magiskboot
IMG=/data/local/tmp/wb/boot_new_full.img

echo "===== 0. sanity ====="
test -f "$IMG" || { echo "MISSING $IMG"; exit 1; }
ls -l "$IMG"
sha256sum "$IMG"

echo ""
echo "===== 1. fresh backup of current boot_b ====="
dd if=/dev/block/by-name/boot_b of=/data/local/tmp/boot_b_preflash.img
sha256sum /data/local/tmp/boot_b_preflash.img

echo ""
echo "===== 2. FLASH boot_b ====="
dd if="$IMG" of=/dev/block/by-name/boot_b
sync
echo "flashed."

echo ""
echo "===== 3. readback verify ====="
dd if=/dev/block/by-name/boot_b of=/data/local/tmp/boot_b_readback.img
sha256sum "$IMG" /data/local/tmp/boot_b_readback.img

echo ""
echo "===== 4. parse readback kernel ====="
rm -rf /data/local/tmp/rb; mkdir -p /data/local/tmp/rb; cd /data/local/tmp/rb
cp /data/local/tmp/boot_b_readback.img rb.img
$MB unpack rb.img 2>&1 | head -10
echo "--- kernel version in flashed boot_b ---"
strings -a kernel | grep -m1 'Linux version'
echo ""
echo "FLASH_OK"
