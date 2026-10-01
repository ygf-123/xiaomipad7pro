#!/system/bin/sh
echo "===== /proc/kallsyms: __crc_ symbols available? ====="
grep -c '__crc_' /proc/kallsyms 2>/dev/null
echo "--- sample ---"
grep '__crc_' /proc/kallsyms 2>/dev/null | head -8
echo ""
echo "===== nsproxy-related exported symbols + their CRC on the STOCK kernel ====="
for s in switch_task_namespaces task_nsproxy copy_namespaces free_nsproxy get_net_ns_by_pid; do
  echo "--- $s ---"
  grep -E "(__crc_${s}\$|__ksymtab_${s}\$| [tT] ${s}\$)" /proc/kallsyms 2>/dev/null | head -3
done
echo ""
echo "===== which vendor modules reference nsproxy-ish symbols? ====="
for m in /vendor/lib/modules/*.ko; do
  if strings -a "$m" 2>/dev/null | grep -qE '^(switch_task_namespaces|copy_namespaces|task_nsproxy|free_nsproxy)$'; then
    echo "HIT: $(basename $m)"
  fi
done | head -20
echo ""
echo "===== total vendor modules ====="
ls /vendor/lib/modules/*.ko 2>/dev/null | wc -l
