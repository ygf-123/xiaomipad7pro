#!/system/bin/sh
echo "===== /proc/kcore available? ====="
ls -l /proc/kcore 2>/dev/null || echo "NO /proc/kcore"
echo ""
echo "===== head of kcore (for ELF headers) ====="
dd if=/proc/kcore of=/data/local/tmp/kcore_head.bin bs=1024 count=16 2>/dev/null
ls -l /data/local/tmp/kcore_head.bin 2>/dev/null
echo ""
echo "===== vmallocinfo: ramoops mapping ====="
grep -i 'ramoops' /proc/vmallocinfo 2>/dev/null || echo "(not found in vmallocinfo)"
echo ""
echo "===== /proc/iomem ====="
head -40 /proc/iomem 2>/dev/null
echo ""
echo "===== device-tree ramoops node ====="
for d in /proc/device-tree/reserved-memory/*ramoops*; do
  echo "### $d"
  ls "$d" 2>/dev/null
  for p in "$d"/*; do
    [ -f "$p" ] && { printf '%s = ' "$(basename $p)"; cat "$p" 2>/dev/null | tr -d '\0' | head -c 200; echo; }
  done
done
echo ""
echo "===== /proc/kallsyms address visibility (PAGE_OFFSET hint) ====="
grep -m3 -E ' (T|t) _text$| (T|t) startup_' /proc/kallsyms 2>/dev/null
head -3 /proc/kallsyms
