#!/system/bin/sh
echo "===== system_dlkm modules ====="
ls /system_dlkm/lib/modules/ 2>/dev/null | head -20
echo "count: $(ls /system_dlkm/lib/modules/*.ko 2>/dev/null | wc -l)"
echo ""
echo "===== try unpacking vendor_boot with magiskboot ====="
rm -rf /data/local/tmp/vb; mkdir -p /data/local/tmp/vb; cd /data/local/tmp/vb
dd if=/dev/block/by-name/vendor_boot_b of=vendor_boot.img 2>/dev/null
ls -l vendor_boot.img
/data/adb/magisk/magiskboot unpack vendor_boot.img 2>&1 | head -20
echo "--- files ---"
ls -la
echo ""
echo "===== header magic check ====="
head -c 16 vendor_boot.img | od -c | head -2
