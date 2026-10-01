#!/system/bin/sh
set -e
MB=/data/adb/magisk/magiskboot
cd /data/local/tmp/vb

echo "===== swap in patched ramdisk ====="
ls -l /data/local/tmp/ramdisk_patched.cpio
cp /data/local/tmp/ramdisk_patched.cpio vendor_ramdisk/ramdisk.cpio
ls -l vendor_ramdisk/ramdisk.cpio

echo ""
echo "===== repack vendor_boot ====="
rm -f new_vendor_boot.img
$MB repack vendor_boot.img new_vendor_boot.img
ls -l new_vendor_boot.img
sha256sum new_vendor_boot.img

echo ""
echo "===== sanity: unpack the repacked image ====="
rm -rf /data/local/tmp/vb_check; mkdir -p /data/local/tmp/vb_check; cd /data/local/tmp/vb_check
cp /data/local/tmp/vb/new_vendor_boot.img vendor_boot.img
$MB unpack vendor_boot.img 2>&1 | head -12
ls -l
echo "REPACK_OK"
