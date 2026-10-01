#!/system/bin/sh
set -e
echo "===== 1. flash vendor_boot_b (patched cifs.ko) ====="
dd if=/data/local/tmp/vb/new_vendor_boot.img of=/dev/block/by-name/vendor_boot_b
sync
dd if=/dev/block/by-name/vendor_boot_b of=/data/local/tmp/vb_rb2.img
sha256sum /data/local/tmp/vb/new_vendor_boot.img /data/local/tmp/vb_rb2.img

echo ""
echo "===== 2. flash boot_b (custom 6.1.141 kernel) ====="
dd if=/data/local/tmp/boot_b_custom.img of=/dev/block/by-name/boot_b
sync
dd if=/dev/block/by-name/boot_b of=/data/local/tmp/boot_rb2.img
sha256sum /data/local/tmp/boot_b_custom.img /data/local/tmp/boot_rb2.img

echo ""
echo "===== 3. confirm kernels ====="
rm -rf /data/local/tmp/rbchk; mkdir -p /data/local/tmp/rbchk; cd /data/local/tmp/rbchk
cp /data/local/tmp/boot_rb2.img b.img
/data/adb/magisk/magiskboot unpack b.img >/dev/null 2>&1
strings -a kernel | grep -m1 'Linux version'
echo FLASH_ALL_OK
