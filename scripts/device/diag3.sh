#!/system/bin/sh
echo "===== pstore NOW (previous boot = fastboot boot attempt) ====="
ls -la /sys/fs/pstore/ 2>/dev/null
echo "--- console-ramoops content (last 60 lines) ---"
for f in /sys/fs/pstore/*; do
  [ -f "$f" ] && { echo "### $f"; tail -60 "$f"; }
done
echo ""
echo "===== magisk logs ====="
ls -la --time-style=full-iso /cache/magisk.log /data/adb/magisk.log /data/adb/magisk/*.log 2>/dev/null
echo "--- tail of magisk log ---"
tail -40 /cache/magisk.log 2>/dev/null || tail -40 /data/adb/magisk.log 2>/dev/null || echo "(no magisk log)"
echo ""
echo "===== modules in /data/adb/modules ====="
ls -la --time-style=full-iso /data/adb/modules/
echo ""
echo "===== droidspaces module detail ====="
ls -laR --time-style=full-iso /data/adb/modules/droidspaces/ 2>/dev/null | head -60
echo "--- module.prop ---"
cat /data/adb/modules/droidspaces/module.prop 2>/dev/null
echo "--- post-fs-data.sh ---"
cat /data/adb/modules/droidspaces/post-fs-data.sh 2>/dev/null || echo "(none)"
echo "--- service.sh ---"
cat /data/adb/modules/droidspaces/service.sh 2>/dev/null || echo "(none)"
echo ""
echo "===== /cache timestamps ====="
ls -la --time-style=full-iso /cache/ 2>/dev/null | head -20
echo ""
echo "===== magisk boot loop / safe mode markers ====="
ls -la /data/adb/magisk/ 2>/dev/null | head -30
ls -la /data/adb/ 2>/dev/null
echo ""
echo "===== dmesg: any module load failures in CURRENT boot? ====="
dmesg | grep -iE 'module|vermagic|disagrees|Unknown symbol' | head -20
