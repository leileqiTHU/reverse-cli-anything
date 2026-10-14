# 实现依据与边界

## 逆向结果如何进入 CLI

| 模块 | 作用 |
| --- | --- |
| `capcut_agent.py` | 命令解析、JSON 契约、输入验证、隔离 worker 启动 |
| `capcut_cli_worker.py` | ctypes 加载原生 Lyra client，媒体探测和图像转换；模块哈希 |
| `capcut_store_worker.py` / `capcut_store_agent.js` | 原生项目登记、前端创建/打开/关闭及素材库导入 |
| `capcut_editor_worker.py` / `capcut_editor_agent.js` | 明确 PID 下的原生编辑会话、命令调用及保存核验 |
| `capcut_timeline_agent.js` | 独立时间线的前端切换与就绪确认 |
| `capcut_extensions.py` | 音频、字幕和属性的逐步回执、前后状态与重复请求检查 |
| `capcut_export*` | 原生导出前端与 ExportClient 任务绑定、验证后发布 |
| `capcut_preview*` | 原生帧、区间设置/渲染/恢复 |
| `capcut_media.py` | FFmpeg 文件帧/预览；与原生编辑器接口明确区分 |
| `capcut_state.py` | 规范化草稿对象、属性与无关内容保护 |

REA/Ghidra 实际用于 `lyra::Client::Create`、`ClientImpl::Execute` 等定点反编译。Qt 元数据、ABI 和部分调用链由 PE/Capstone 与 Frida 运行时验证补充。一个 RGB 候选曾被分析，但不是最终取帧路径；大模块全量分析超时不计为成功证据。

原生 `draft export` 在外部 SID 模式下拒绝，因此最终导出走正常前端生命周期和 ExportClient；不能因为发现一个同名内部命令就宣称导出已支持。

## 已知边界

- 限于一个 SHA-256 固定的 build。升级应用必须重新定位并验收，不自动放宽哈希检查。
- 进程内调用依然可能让应用无响应或崩溃；启动独立 Python worker 无法隔离目标进程故障。
- 普通早期编辑命令与后来三工具的回执完备程度不同；不宣称所有接口都已提供一致的幂等事务。
- 导出会正常打开/关闭原生导出面板，但不发送鼠标/键盘事件；有其他模态窗口时可能拒绝。
- `inspect` 中部分属性来自自动保存草稿，并与原生 ID/时序交叉验证，不是所有属性都直接来自实时原生摘要。
- 新增空音轨、指定任意音轨、动画字幕、任意关键帧和复杂变速未验收。

## 实测问题

真实素材验收遇到原生附加停滞、MP3 内嵌封面被视为视频、字幕 1 微秒舍入误报。分别通过备份并重启恢复、WAV 解码准备、收紧到 1 微秒容差的回归修复处理。保留这些记录是为了明确当前成熟度，而非隐藏异常。
