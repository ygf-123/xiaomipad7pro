#!/system/bin/sh
echo "===== KERNEL ====="
uname -a
echo ""
echo "===== namespace / droidspaces config ====="
zcat /proc/config.gz | grep -E '^CONFIG_(PID_NS|IPC_NS|USER_NS|SYSVIPC|POSIX_MQUEUE|DEVTMPFS)='
echo ""
echo "===== unshare tests ====="
unshare -p -f true && echo "PID_NS OK" || echo "PID_NS FAIL"
unshare -i true && echo "IPC_NS OK" || echo "IPC_NS FAIL"
echo ""
echo "===== root ====="
id
echo ""
echo "===== re-enable droidspaces module ====="
rm -f /data/adb/modules/droidspaces/disable
ls -la /data/adb/modules/droidspaces/
echo ""
echo "===== loaded modules (vendor) ====="
lsmod | wc -l
echo ""
echo "===== cleanup diagnostic hooks ====="
rm -f /data/adb/post-fs-data.d/00-bootlog.sh /data/adb/service.d/00-bootlog-late.sh
ls /data/adb/post-fs-data.d/ /data/adb/service.d/ 2>/dev/null
echo ""
echo "===== droidspaces check ====="
/data/local/Droidspaces/bin/droidspaces check 2>&1 | head -50
echo ""
echo "===== start debian container ====="
/data/local/Droidspaces/bin/droidspaces --config=/data/local/Droidspaces/Containers/debian/container.config start 2>&1 | tail -25
echo ""
echo "===== container pid/status ====="
/data/local/Droidspaces/bin/droidspaces --config=/data/local/Droidspaces/Containers/debian/container.config pid 2>&1
echo ""
echo "===== run a command inside the container ====="
/data/local/Droidspaces/bin/droidspaces --config=/data/local/Droidspaces/Containers/debian/container.config run "cat /etc/os-release; uname -a; echo CONTAINER_OK" 2>&1 | tail -15
