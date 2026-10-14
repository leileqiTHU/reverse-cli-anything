# 测试与现场验收

从仓库根目录执行：

```powershell
python -B -m unittest discover -s capcut-cli/tests -v
```

当前本机复用既有 Python、CapCut DLL、FFmpeg 和测试素材。新检出按适配器 README 安装 `.native-tools` 后，可执行 `python -B capcut-cli/tools/create-fixtures.py` 准备纯合成的离线测试素材；脚本另需 Pillow。

| 测试类型 | 依赖与含义 |
| --- | --- |
| 字幕/属性/状态/边界/恢复单元测试 | Python；不操作 CapCut；状态样例为去本机路径的原生保存数据 |
| `test_media_preview.py` | 实际 FFmpeg 合成/解码，依赖 `.native-tools` |
| `test_capcut_cli.py` | 实际加载受支持 CapCut 原生 DLL 并探测/转换测试媒体 |
| `test_capcut_editor.py` | 需要显式 `CAPCUT_TEST_PID/PROJECT`；默认跳过，可能修改专用测试项目 |
| `verify_cli_workflow.py` | 主动创建独立测试工程并执行完整写入；独立运行，不纳入无条件回归 |

原生测试缺少依赖意味着未验证，不把跳过项算作通过。现场写入测试只用于明确的测试项目。

目录整理后的实际结果在 [layout-migration-20261013.json](../evidence/layout-migration-20261013.json)；此前真实素材验收在 [real-media-20261013.json](../evidence/real-media-20261013.json)。
