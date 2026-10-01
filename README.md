# 小米平板 7 Pro (muyu) —— HyperOS 3.0.307 Droidspaces 修复全记录

> 仓库：[ygf-123/xiaomipad7pro](https://github.com/ygf-123/xiaomipad7pro)
> 本文记录一次**没有日志、没有源码**的排查：从"升级系统后容器跑不起来"一路定位到
> **GKI 非 KMI 符号 CRC 不匹配**，并给出**不重新编译内核**的修复方法。
> 配套工具脚本、原始证据数据都在本仓库里，可直接复现。

> **一句话结论**：新固件的 first-stage 启动模块列表里有 Google 按 **6.1.138** 编译的 GKI 模块 `cifs.ko`，
> 而我们用的自定义内核是 **6.1.141**（GKI 分支 `android14-6.1-2025-07`），两个**非 KMI 符号**的 CRC 不一致
> → `cifs.ko` 加载失败 → **init 视为致命错误** → 无限重启。
> 修复方式：**不重新编译内核**，只把 `cifs.ko` 里期望的 CRC 就地改成内核实际值（vendor_boot 打补丁）。

| 项目 | 值 |
|---|---|
| 设备 | 小米 Pad 7 Pro (muyu, SM8635, 24091RPADC) |
| 系统 | HyperOS 3 `3.0.307.0.WOYCNXM.C11`（Android 16 / API 36） |
| 升级前 | `3.0.301.0.WOYCNXM`（Android 15） |
| 原厂内核（新） | `6.1.138-android14-11-g7b9e94e37cfa-mi`（2026-03-10 构建） |
| 原厂内核（旧） | `6.1.138-android14-11-g614238d0d630-mi` |
| 自定义内核 | `6.1.141-android14-11-g58c358c7a7ea`（GKI `common-android14-6.1-2025-07`） |
| Root | Magisk 30.7（在 `init_boot`，未受影响） |
| 活动槽位 | `_b` |

---

## 1. 现象

OTA 升级后，Droidspaces 启动 Debian 容器时报：

```
[-] PID namespace is not supported by the kernel
[+] This is a REQUIRED feature for process isolation.
[-] IPC namespace is not supported by the kernel
[-] Missing 2 required feature(s) - cannot proceed
```

`unshare -p -f true` / `unshare -i true` 实测失败，`/proc/config.gz` 里只有 `UTS_NS/NET_NS`。

原因很直白：**OTA 把系统装进了 B 槽并切过去，B 槽 boot 是原厂内核；之前编好的自定义内核还躺在 A 槽（`boot_a`）**。
root 之所以还在，是因为 Magisk 装在 `init_boot`（OTA 后重新打过）。

## 2. 关键背景：GKI 内核 / 模块 / KMI

理解本次问题需要三个概念：

1. **GKI 内核**：Google 提供的内核二进制（boot 分区），设备厂商自己编译 **vendor 模块**
   （`vendor_boot` ramdisk 里的 first-stage 模块 + `vendor_dlkm` / `system_dlkm`）。
2. **KMI**：GKI 保证同一 KMI 世代（本机是 `android14-11`）内**符号 CRC 不变**，所以模块能跨内核小版本加载。
3. **非 KMI 符号**：不在 KMI 保护清单里的符号，**CRC 可以随内核小版本变化**。
   当模块里 `__versions` 记录的 CRC 与内核 `__kcrctab` 里的实际值不一致，
   `CONFIG_MODVERSIONS=y` 的内核会拒绝加载该模块（`disagrees about version of symbol`）。

> 这就是"6.1.138 编的模块 + 6.1.141 的内核"会踩雷的地方——**大部分符号没问题，个别非 KMI 符号会变**。

## 3. 排查过程（假设 → 实验 → 结论）

### 3.1 先确认现象：换回带 namespace 的内核

把 A 槽里那个带完整 namespace 的内核（6.1.141）用 `magiskboot` repack 进 B 槽 boot，刷入后：

```
[  0s] state -> none        ← 150 秒内既没有 adb 也没有 fastboot
```

**无限重启**，且 adb 完全抓不到（说明失败发生在 `adbd` 启动之前）。
更糟的是 `slot-unbootable:a = yes`，B 槽失败 6 次后无处可退 → 纯 bootloader 循环，只能手动进 fastboot 救援。

> 教训：A/B 设备上，非活动槽如果被标记 unbootable，就成了"单腿走路"，调试前建议先
> `fastboot set_active a` 再 `set_active b` 把两个槽都重置成可启动。

### 3.2 假设 1：新固件的 ABL 开始拒绝被修改的 boot 镜像（AVB 哈希）

**实验**：把**原厂 boot 镜像只改 1 个字节**（cmdline 缓冲区内、终止 NUL 之后的填充区，功能完全不变），
这样镜像行为与原厂一致但 **AVB 哈希失效**：

```bash
python make_abvtest.py STOCK_boot_b.img test_1byte.img   # 0xAC 处 0x00 -> 0xFF
dd if=test_1byte.img of=/dev/block/by-name/boot_b && reboot
```

**结果**：20 秒正常开机完成。

**结论**：❌ 排除。ABL 不校验 boot 镜像哈希（`verifiedbootstate=orange`，且 Magisk 改过的 `init_boot` 也能启动）。

### 3.3 假设 2：droidspaces Magisk 模块开机自启容器导致内核 panic

该模块的 `service.sh` 会在开机后自动启动 `run_at_boot=1` 的容器——原厂内核下它"优雅失败"，
换上 namespace 内核后容器会**真的开始启动**，可能触发内核 bug。

**实验**：`touch /data/adb/modules/droidspaces/disable` 禁用模块后再刷内核。

**结果**：依然 210 秒无 adb。

**结论**：❌ 排除。

### 3.4 假设 3：Android 16 的 VINTF 要求 `CONFIG_SYSVIPC=n`，init 拒绝启动

从设备拉取框架兼容性矩阵，发现硬性要求：

```xml
<!-- /system/etc/vintf/compatibility_matrix.202404.xml:1620 -->
<config>
    <key>CONFIG_SYSVIPC</key>
    <value type="tristate">n</value>
</config>
```

而 `/system/lib64/libvintf.so` 里确实有 `android::vintf::RuntimeInfo::kernelConfigs()`（读取 `/proc/config.gz` 做比对）。
我们的内核开了 `CONFIG_SYSVIPC=y`（Droidspaces 需要），**这是唯一的配置冲突项**（259 项逐条核对，其余全过）。

**实验（巧妙之处）**：不改内核行为，只**把原厂内核里内嵌的 IKCONFIG 数据改成"谎报" `CONFIG_SYSVIPC=y`**
（原厂内核实际是 `n`），这样内核功能不变、但 init 会看到"违反要求"的配置：

```bash
python ikpatch.py extract STOCK_boot_b.img kernel_stock.img
python ikpatch.py patch   kernel_stock.img kernel_stock_lie.img \
    "# CONFIG_SYSVIPC is not set||CONFIG_SYSVIPC=y"
# 原地改写 gzip 后的 config blob，长度精确不变（丢 2 行注释 + 补填充注释对齐）
```

刷入后：**20 秒正常开机**，且 `zcat /proc/config.gz | grep SYSVIPC` 确实显示 `CONFIG_SYSVIPC=y`（谎言生效）。

**结论**：❌ 排除。VINTF 内核配置校验在 Android 16 上**只是警告，不是致命错误**。
（顺带证明了 IKCONFIG 原地改写技术可用。）

### 3.5 假设 4：GKI 裁剪导出符号导致模块加载失败

你那个 workflow 的默认参数 `remove_abi_gki_protected_exports=true` 会删除
`android/abi_gki_protected_exports_*` 白名单，于是 `TRIM_UNUSED_KSYMS=y` 会把"没被本机构建模块用到"的符号裁掉。

从内核 Image 提取导出符号表（`extract_crcs.py`，用 System.map 定位 `__ksymtab/__kcrctab` 段并校准 vaddr→文件偏移）：

```
导出符号总数: 8166   ← 正常应该 2~3 万
System.map 里没有 __ksymtab_printk（printk 被裁掉了）
```

**实验**：把设备上**全部 508 个模块**（vendor_boot ramdisk 347 + vendor_dlkm 323 + system_dlkm 60）的
`__versions` 需求符号，与"内核导出 ∪ 其它模块定义"求差：

```
无法解析符号的模块: 0 / 508
CRC 不匹配: 2
```

**结论**：❌ 排除（裁剪不影响模块加载）。但这次全量分析**意外抓到了真正的线索**——那 2 个 CRC 不匹配。

### 3.6 假设 5：新旧原厂内核 config 不同

提取两份 IKCONFIG 逐项对比：**6008 个符号，0 差异**。

**结论**：❌ 排除。

### 3.7 假设 6：新固件是否只认"配套内核"？

把 **3.0.301 的原厂内核**（`6.1.138-android14-11-g614238d0d630-mi`）刷到 B 槽 → **同样起不来**。

**结论**：✅ 新固件对内核有"配套性"要求（不是版本号、不是 config、不是签名）。

### 3.8 定位：first-stage 模块列表里的 `cifs.ko`

`vendor_boot` 解包后（magiskboot 原生支持 vendor_boot）：

```
vendor_ramdisk/ramdisk.cpio          ← 68 MB，多段 cpio 拼接
  lib/modules/*.ko                   ← 347 个模块
  lib/modules/modules.load           ← 128 项，first-stage 真正加载的清单
```

清单里有 **`cifs.ko`**（还有 `cifs_md4.ko`、`cifs_arc4.ko`、`clk-qcom.ko`、`qcom_ipc_logging.ko` …）。

而 CRC 对比结果里，**唯一不匹配的模块正是 `cifs.ko`**：

```
cifs.ko 期望  __page_file_index = 0x12d686c5   我们的内核 = 0x39ba4984
cifs.ko 期望  add_swap_extent   = 0x3da4a325   我们的内核 = 0x2a731aba
```

`cifs.ko` 的 vermagic 是 `6.1.138-android14-11-g0c3d559bcd85`（Google GKI 构建），
即**按 6.1.138 编译**；而我们的内核是 6.1.141，这两个非 KMI 符号的声明变了。

## 4. 根因

```
新固件 first-stage 加载 cifs.ko（Google 按 6.1.138 编译的 GKI 模块）
        │
        ├─ 我们的自定义内核是 6.1.141（GKI 2025-07）
        │     └─ __page_file_index / add_swap_extent 的 CRC 与 6.1.138 不同
        │
        ├─ CONFIG_MODVERSIONS=y → 模块 CRC 校验失败 → cifs.ko 拒绝加载
        │
        ├─ Android init 在 first-stage 加载 modules.load 清单，失败即致命
        │
        └─ init 崩溃 → 无限重启
              （早于 adbd / Magisk post-fs-data，所以 adb 抓不到、Magisk 日志空白；
                pstore 也因设备 DT 的 ramoops 压缩配置缺陷而拿不到崩溃日志）
```

**为什么旧固件没事**：旧固件的 `cifs.ko` 期望的 CRC 恰好与 6.1.141 一致，模块正常加载。
**为什么旧原厂内核也不行**：它的 CRC 与旧模块匹配、与新模块不匹配（厂商在内核补丁里动过相关声明）。

## 5. 修复方案（不重新编译内核）

**核心思路**：`add_swap_extent(struct swap_info_struct *, unsigned long, ...)` 的**函数签名在 6.1.138 / 6.1.141 完全一致**
（CRC 变化来自结构体成员，不影响调用约定），因此把模块期望的 CRC 对齐到内核实际值是安全的。

```bash
# ── 0. 备份（务必先做）─────────────────────────────
adb shell "su -c 'dd if=/dev/block/by-name/boot_b        of=/data/local/tmp/boot_b_stock.img'"
adb shell "su -c 'dd if=/dev/block/by-name/vendor_boot_b of=/data/local/tmp/vendor_boot_b_stock.img'"

# ── 1. 解包 vendor_boot ────────────────────────────
adb shell "su -c 'mkdir -p /data/local/tmp/vb && cd /data/local/tmp/vb && \
  dd if=/dev/block/by-name/vendor_boot_b of=vendor_boot.img && \
  /data/adb/magisk/magiskboot unpack vendor_boot.img'"
adb pull /data/local/tmp/vb/vendor_ramdisk/ramdisk.cpio

# ── 2. 提取内核导出符号 CRC 表 ─────────────────────
#    （需要该内核构建的 System.map；从 GitHub Actions artifact 拿）
python extract_crcs.py kernel_Image.img System.map      # → kernel_crcs.json

# ── 3. 就地改写 cifs.ko 的 __versions CRC ──────────
python patch_cifs.py                                    # → ramdisk_patched.cpio（大小不变）

# ── 4. 重打包 vendor_boot 并刷入 ───────────────────
adb push ramdisk_patched.cpio /data/local/tmp/
adb shell "su -c 'cp /data/local/tmp/ramdisk_patched.cpio /data/local/tmp/vb/vendor_ramdisk/ramdisk.cpio && \
  cd /data/local/tmp/vb && /data/adb/magisk/magiskboot repack vendor_boot.img new_vendor_boot.img && \
  dd if=new_vendor_boot.img of=/dev/block/by-name/vendor_boot_b'"

# ── 5. 刷自定义内核到 boot_b ───────────────────────
adb push boot_b_custom_6.1.141.img /data/local/tmp/
adb shell "su -c 'dd if=/data/local/tmp/boot_b_custom_6.1.141.img of=/dev/block/by-name/boot_b; sync'"
adb reboot
```

`patch_cifs.py` 只做一件事：解析 cpio → 定位 `lib/modules/cifs.ko` → 解析 ELF 的 `__versions` 段
→ 把与内核 CRC 不符的条目就地改写成内核值。**cpio 总长度、偏移全部不变**（纯字节改写），因此重打包零风险。

## 6. 验证结果

| 验证项 | 结果 |
|---|---|
| 内核 | `6.1.141-android14-11-g58c358c7a7ea` ✓ |
| config | `PID_NS / IPC_NS / USER_NS / SYSVIPC / POSIX_MQUEUE / DEVTMPFS` 全 `=y` ✓ |
| `unshare -p -f true` / `unshare -i true` | PID_NS OK / IPC_NS OK ✓ |
| vendor 模块加载 | **505 个** ✓（原厂内核同数量） |
| `droidspaces check` | `[✓] All required features found!` ✓ |
| 容器 | Debian GNU/Linux 13 (trixie) 启动成功，PID 6026，NAT `172.28.111.111` ✓ |
| 容器内执行 | `cat /etc/os-release; uname -a` → `CONTAINER_OK` ✓ |

## 7. OTA 之后如何重做

任何 OTA 都会覆盖 `boot` 和 `vendor_boot`，需要重来一遍。两种情况：

**A. 新 OTA 的 GKI 模块基准版本未变**（仍与手上内核匹配）→ 直接刷备份好的镜像：

```bash
fastboot flash boot_b        boot_b_custom_6.1.141.img
fastboot flash vendor_boot_b vendor_boot_b_patched.img
```

**B. 版本变了**（内核或模块更新）→ 重新走第 5 节第 1~4 步（重新对齐 CRC）。
判断方法：解包新固件的 vendor_boot，检查 `modules.load` 里的模块 vermagic 版本，
与手上内核版本比较；不一致就需要重新 `patch_cifs.py`。

**救援（刷完循环时）**：

```bash
# 长按电源 15 秒关机 → 同时按「音量下 + 电源」进 fastboot
fastboot flash boot_b        STOCK_boot_b_307.img
fastboot flash vendor_boot_b STOCK_vendor_boot_b.img
fastboot reboot
```

## 8. 经验与坑

1. **GKI 模块与内核必须"版本配套"**：KMI 只保证 KMI 清单内符号稳定，**非 KMI 符号会随小版本变化**。
   跨版本复用内核时，务必做一次 `__versions` CRC 全量比对。
2. **first-stage 模块加载失败是致命的**，且失败点在 `adbd` 之前 → 没有 adb、没有 Magisk 日志。
   本机 pstore 也因 DT 里 ramoops 压缩配置缺陷（`pstore: Invalid compression size for deflate: 0`）拿不到崩溃日志，
   所以排查基本只能靠"控制变量 + 二进制比对"。
3. **VINTF 的 `<kernel><config>` 校验在 Android 16 上只是警告**，不致命（已用"谎报配置"实验证明）。
4. **A/B 设备的槽位坑**：非活动槽被标记 `unbootable` 时，失败就无处回退。
   调试前 `fastboot set_active a && fastboot set_active b` 重置两槽。
5. **ABL 不校验被修改的 boot 镜像**（1 字节实验证明），`verifiedbootstate=orange` 下 AVB 形同虚设。
6. **`remove_abi_gki_protected_exports=true` 会裁掉大量导出符号**（8166 vs 正常 2~3 万），
   虽然本次不是根因，但建议构建时**取消勾选**，保留白名单。
7. **Google 会删除旧的 GKI 分支**：`android14-6.1-2025-07` 已不存在
   （`repo sync` 报 `couldn't find remote ref refs/heads/android14-6.1-2025-07`），
   所以"照着旧 workflow 重跑一次"这条路会直接失败。
8. **在没有日志的环境里定位问题的方法论**：
   先用"最小改动镜像"排除引导链（签名/结构），再用"配置谎报"排除用户态校验，
   最后用**二进制层面的符号/CRC 全量比对**锁定差异——本次正是靠这个找到 `cifs.ko`。

## 9. 附录

### 9.1 工具脚本

| 脚本 | 用途 |
|---|---|
| `scripts/patch_cifs.py` | **核心修复**：就地改写 vendor ramdisk 里 cifs.ko 的 `__versions` CRC |
| `scripts/extract_crcs.py` | 从内核 Image + System.map 提取「导出符号 → CRC」全表（含 vaddr→文件偏移校准） |
| `scripts/crc_check2.py` | 模块期望 CRC vs 内核 CRC 对比，输出不匹配模块清单 |
| `scripts/unresolved.py` | 全量模块（ramdisk + vendor_dlkm + system_dlkm）符号解析检查 |
| `scripts/ikpatch.py` | 内核镜像内嵌 IKCONFIG 的读写（extract / patch / show，长度精确对齐） |
| `scripts/cfgdiff.py` | 两份内核 config 差异对比 |
| `scripts/cmpboot.py` `scripts/avb.py` `scripts/avbparse.py` `scripts/vbsearch.py` | boot 镜像 / AVB 结构分析 |
| `scripts/make_abvtest.py` | 生成"1 字节改动"判定镜像（证明 ABL 不校验签名） |
| `scripts/device/*.sh` | 设备端操作脚本（解包/重打包/刷写/验证） |
| `scripts/gh/*.ps1` | GitHub Actions 触发与 artifact 下载 |

### 9.2 产物校验值（sha256）

| 文件 | 大小 | sha256 |
|---|---|---|
| `boot_b_custom_6.1.141.img` | 96 MB | `9e94413cb2ebbc6f2c09c8b24813ea26db76a612117ef4c823f878d5fbf77b39` |
| `vendor_boot_b_patched.img` | 96 MB | `a3ef77ea68d24b62d543d87b1b1bdd36dd5c456f22d002c84b6f34bc844cbe82` |
| `STOCK_boot_b_307.img` | 96 MB | `bf68c1be17ecf3dff5087300ef8286ecd86c8c898a59b93cda4ea7be9afd3ce8` |
| `STOCK_vendor_boot_b.img` | 96 MB | `69f1e38c6ab70050ef86e37a36319443c1eddc4355543ab5395b895d0bcb96fd` |
| `kernel_Image_6.1.141.img` | 34 MB | （纯内核，可用于重新 repack） |

> 96 MB 的镜像不进 git（太大），请见 Release 附件或按第 5 节脚本自行生成。

### 9.3 复现本仓库的排查/修复

```bash
# 提取内核导出符号 CRC 表（需要该内核构建的 System.map）
python scripts/extract_crcs.py kernel_Image.img System.map        # → kernel_crcs.json

# 把设备上所有模块（ramdisk + vendor_dlkm + system_dlkm）的 __versions 需求
# 与内核导出 + 模块间定义做全量比对，列出无法解析/CRC 不匹配的模块
python scripts/unresolved.py                                      # 需要 ramdisk.cpio / vendor_modules.tar / system_dlkm.tar
python scripts/crc_check2.py vendor_modules.tar kernel_crcs.json

# 内核 config 差异 / VINTF 要求核对
python scripts/cfgdiff.py stock.config custom.config
python scripts/vintfcheck2.py compatibility_matrix.202404.xml custom.config 6.1.141

# 核心修复：就地改写 vendor ramdisk 里 cifs.ko 的 __versions CRC
python scripts/patch_cifs.py                                      # → ramdisk_patched.cpio
```

设备端脚本见 `scripts/device/`（解包/重打包 vendor_boot、刷写、验证），
GitHub 自动化见 `scripts/gh/`。原始证据输出见 `docs/`。

### 9.4 相关项目

- [buildGKI-6.1.138-android14](https://github.com/ygf-123/buildGKI-6.1.138-android14) — 本次使用的 GKI 编译框架（fork 自 Xieansecn）
- [xiaomi-pad7pro-gki-kernel-namespace](https://github.com/ygf-123/xiaomi-pad7pro-gki-kernel-namespace) — 早期"编译带 namespace 的 GKI 内核"记录（本仓库的前传）
- [MiCode/Xiaomi_Kernel_OpenSource](https://github.com/MiCode/Xiaomi_Kernel_OpenSource) — 小米官方内核源码（muyu 分支停留在 6.1.68，无 3.0.307 时代补丁）

---

*记录日期：2026-10-01。设备最终状态：自定义内核 6.1.141 + 打过 cifs.ko CRC 补丁的 vendor_boot，Debian 容器正常运行。*
