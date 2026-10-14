# Visible native drilling demo

2026-10-13，Windows x64 Shapr3D **26.180.11926.0** 实测。全程没有鼠标点击、键盘 UI 输入或项目数据库写入。

## 实际结果

49 秒连续 DXGI 录屏：空模型 → 矩形和两圆草图 → 原生拉伸 4 mm → 厚度改为 6 mm → 两孔各移动 5 mm，孔距从 50 改为 60 mm → 中心圆 → 2 mm 浅孔 → 4 mm 深孔 → 贯穿孔 → 原生导出。

最终固定板为 **80 × 40 × 6 mm**，原安装孔 Ø6 mm、孔距 60 mm，新增中心孔 Ø8 mm。STL 独立检查 **78/78** 通过：单实体、闭合流形、三个贯穿孔、Euler −4、原孔保留、体积减少量与新增孔网格截面积一致。两次实际钻孔的 STL SHA-256 完全相同：`c9a350af5941ecd2e3618d67f7462c1d9b0474bb540162725d529df82e0c467f`。

本机文件位于 `outputs/full-build-visible-20261013/`，输出不随源码发布：

- `full-build.mp4`：49 秒，1026 × 802，15 fps，连续录屏，完整解码成功。
- `01-empty.png`、`03-native-solid.png`、`05-shallow-hole.png`、`07-final.png`：录屏原帧。
- `drill/after.shapr`、`drill/after.stl`：原生项目和打印网格。
- `verification-final.json`：独立几何检查。
- `previous-demo.shapr`：重新演示前的成品备份；`job.json`：调用回执和录屏阶段时间。

## 给当前打开的双孔固定板钻孔

先在正常前台打开可编辑的项目，然后启动公共桥接。新会话可以直接操作当前项目，不要求先由桥接创建项目或截获项目访问对象。

```powershell
python -B .\shapr3d-cli\pilot.py start --pid <实际Shapr3D进程ID>

python -B .\shapr3d-cli\drill.py run `
  --session D:\路径\返回的会话目录 `
  --output D:\新的输出目录 `
  --x 0 --y 0 --top 6 --diameter 8 --depth 8 --pause-seconds 3
```

`run` 会备份当前原生项目和 STL，校验现有双孔板，导入中心圆、选择其区域、逐步切除并导出。每阶段也可单独调用 `prepare`、`preview`、`cut --depth 2/4/8`、`finish`，后四者使用 `--job <prepare返回的job.json>`。已有同名输出被拒绝。发生失败时保留 `pending` 和回执，不能盲目重放。

这版钻孔工具限定：板外形 80 × 40 mm，原孔 Ø6 mm、孔距 60 mm；板位于世界 XY，底面 Z=0。`top` 是厚度，`depth` 必须大于厚度；新孔须位于板内且避开原孔。此次独立验收器只验收中心圆孔。已有第三孔的成品不能再次作为输入。

## 完整建模录制

`full_demo.py --help` 列出参数。它只用于已经备份的本例三孔演示项目，并要求显式 `--replace-current-demo` 及 `--baseline-two-hole <原双孔板STL>`。脚本先导出当前原生备份、核验三孔板，再通过原生历史接口清理演示模型。此后启动录制，从空模型重建；不会通过增加未授权项目数来绕开账号限制。

录制区域必须先确认：使用 DXGI Desktop Duplication 裁取实际 Shapr3D 窗口区域。窗口位置及 DPI 会影响坐标，不能照搬本机值。录制期间保持该窗口可见。第一次 GDI 窗口录制出现黑屏，已明确判为失败，未作为交付录像。

## 实现与证据边界

- 草图：生成二维 DXF，交给原生导入器；未由外部 CAD 内核生成实体。
- 建模：REA 恢复的 WinRT 接口和版本固定的原生调用，经应用 UI 线程执行。可见项目沿自己的 EditorPage 生命周期刷新。
- 选区：射线在圆内、圆外取候选差集，再按精确 ID 选择；不按内存 ID 的高位猜测类型。
- 首次切除使用工具距离标注；后续深度修改使用已提交特征的原生历史参数，因为工具会重建标注 ID。
- 正常 `CanPerform`、`IsBlocked` 和编辑权限检查保留；未修改许可或付费导出设置。
- STL 使用账号可用的 Low 分辨率。孔径拟合顶点满足期望，轮廓仍有离散化误差；新孔最大弦高误差约 0.116 mm。不能将网格体积与理想圆柱体积之差误报为建模失败。
- 录屏证明前台过程，原生回执证明调用完成，独立 STL 检查证明几何；本轮未额外宣称冷启动重开验收。

`verify_drilled_plate.py` 的 14 个合成正/负测试全部通过，包含拒绝盲孔、未改变模型、独立圆柱、损坏网格和错误孔径；合成测试文件与实际原生导出明确分开。
