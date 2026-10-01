#!/system/bin/sh
echo "===== 1. our bootlog hooks: did they run during the failed boot? ====="
ls -la /data/local/tmp/bootlog/ 2>/dev/null
echo ""
echo "===== 2. magisk logs (did magiskinit/magiskd run in the failed boot?) ====="
ls -la /cache/magisk.log /data/adb/magisk.log 2>/dev/null
echo "--- tail of magisk log ---"
tail -50 /cache/magisk.log 2>/dev/null || tail -50 /data/adb/magisk.log 2>/dev/null || echo "(none)"
echo ""
echo "===== 3. pstore ====="
ls -la /sys/fs/pstore/ 2>/dev/null
echo ""
echo "===== 4. is Magisk really in init_boot? ====="
MB=/data/adb/magisk/magiskboot
rm -rf /data/local/tmp/ib; mkdir -p /data/local/tmp/ib; cd /data/local/tmp/ib
dd if=/dev/block/by-name/init_boot_b of=init_boot.img 2>/dev/null
$MB unpack init_boot.img 2>&1 | head -8
ls -l
echo "--- ramdisk entries (looking for magisk) ---"
$MB cpio ramdisk.cpio ls 2>&1 | head -25
echo ""
echo "===== 5. /cache listing (timestamps) ====="
ls -la /cache/ 2>/dev/null | head -20
echo ""
echo "===== 6. current kernel ====="
uname -r
