#!/system/bin/sh
set -e
W=/data/local/tmp/wc
cd "$W"
echo "===== repacked image ====="
ls -l boot_new.img
sha256sum boot_new.img

echo ""
echo "===== flash boot_b ====="
dd if=boot_new.img of=/dev/block/by-name/boot_b
sync
echo "flashed"

echo ""
echo "===== readback ====="
dd if=/dev/block/by-name/boot_b of=/data/local/tmp/boot_b_rb3.img
sha256sum boot_new.img /data/local/tmp/boot_b_rb3.img
echo ""
echo "FLASH_OK"
