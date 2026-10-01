#!/system/bin/sh
echo "===== VINTF dirs ====="
ls -la /vendor/etc/vintf/ 2>/dev/null
echo "--- /system/etc/vintf ---"
ls -la /system/etc/vintf/ 2>/dev/null
echo ""
echo "===== kernel entries in compatibility matrices ====="
for f in /vendor/etc/vintf/*.xml /system/etc/vintf/*.xml; do
  [ -f "$f" ] || continue
  echo "### $f"
  grep -i -B1 -A3 'kernel' "$f" 2>/dev/null | head -40
done
echo ""
echo "===== kernel-related properties ====="
getprop | grep -iE 'kernel|kmi|api_level|vendor.api' | head -30
echo ""
echo "===== vendor build.prop kernel lines ====="
grep -iE 'kernel|kmi' /vendor/build.prop /vendor/etc/build.prop /system/build.prop 2>/dev/null | head -20
echo ""
echo "===== /proc/version ====="
cat /proc/version
echo ""
echo "===== does init binary mention kernel version checks? ====="
strings -a /system/bin/init 2>/dev/null | grep -iE 'kernel version|KernelVersion|kernel.*too old|requires kernel' | head -20
echo ""
echo "===== vendor_boot bootconfig (kernel version requirement?) ====="
ls -la /proc/bootconfig 2>/dev/null && head -60 /proc/bootconfig
