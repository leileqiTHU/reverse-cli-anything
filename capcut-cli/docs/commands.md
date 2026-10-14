# 命令与语义

命令入口：`capcut-agent.ps1` 或 `python -B capcut_agent.py`。最新命令形状以 `help --topic editor`、`help --topic project` 与 `capabilities` 为准。

## 命令组

| 命令 | 实际作用与前置条件 |
| --- | --- |
| `project list/create/open/close` | 原生生命周期；创建要求首页，打开/关闭要求明确项目身份 |
| `project import-media` | 已登记且关闭的项目，导入本地视频素材库；去重；不等于放上时间线 |
| `editor add-timeline/switch-timeline` | 创建独立时间线、等待实际切换就绪 |
| `editor inspect` | 视频 `clips` 和音频/文本/视频 `items`；原生身份/时序与自动保存交叉验证 |
| `editor add-video/add-track` | 添加视频或新增视频视觉层并放入首个片段；不支持单独空轨道 |
| `editor trim/split/move/remove` | 指定片段；普通 speed=1 视频；主轨磁吸限制自由移动 |
| `editor undo/redo` | 使用原生历史栈；不承诺多步操作为单个事务或固定 50 层 |
| `editor add-audio` | 现有时间线内的有限音频源区间，音量和淡入淡出；不循环或自动拉伸 |
| `editor captions-import` | SRT 或 JSON，追加原生文本片段；识别与翻译由上游完成 |
| `editor set-clip` | 视频变换/裁切/透明度/音量；音频音量/淡变；有限的恒速支持 |
| `editor frame/preview/export` | 原生合成帧、原生区间渲染、原生整段导出 |
| `media frame/preview` | FFmpeg 文件帧/区间预览，不读取实时编辑器状态 |
| `probe/convert-image` | 独立进程调用 CapCut 原生媒体模块 |

## 项目到时间线

使用稳定 ID 串行处理：`project create → close → import-media → open → editor add-timeline → switch-timeline → add-video`。每一步解析 JSON 中 `ok`，使用返回的 `projectId/projectPath/timelineId/segmentId`，不要从文件夹名或历史 PID 猜测。

导入素材库当前要求目标项目关闭，因为活动前端会覆盖素材列表；已有项目内容必须先通过正常关闭保存。创建时间线与视频层是不同操作。

## 剪辑时间

- `trim --in-us --out-us`：操作前的**绝对时间线区间**，保留对应源片段；主轨磁吸可消除前部空隙。
- `split --points-us`：**相对片段起点**的递增切点；每段至少一帧。
- `add-audio --source-in-us`：音频源入点；`--start-us`：时间线目标起点。
- 输出中使用规范化 `targetUs/sourceUs`；原生部分 `.ms` 字段实际存微秒，不直接按标签解释。

## 字幕输入

```json
{"timebase":"timeline_us","cues":[
  {"id":"line-1","startUs":0,"endUs":2000000,"text":"你好\nHello"}
]}
```

单批 cue 按时间排序、不重叠，至少一帧且位于现有时间线范围。style 文件示例：

```json
{"size":5.3,"color":"#FFFFFF","outlineColor":"#000000","outlineWidth":0.05,"xRatio":0,"yRatio":-0.74}
```

size 为原生字号，不是像素。保留文本字面内容，支持换行；实际排版应查看原生帧。允许原生 start/duration 字段各自最多 1 微秒舍入。没有自动 ASR/翻译或字体资源选择命令。

## 片段属性

```json
{"transform":{"scaleX":1.08,"scaleY":1.08,"xRatio":0,"yRatio":0},"gainDb":-3}
```

值为绝对设置，未提供的属性保持。坐标从画布中心计算，x 正向右、y 正向上，1 对应半个画布宽/高。`crop` 是源画面边界，和时间裁剪 `trim` 无关。

共享素材的 crop、已有关键帧的片段、曲线变速会拒绝。恒速仅支持专用时间线上起点为 0 的唯一普通视频，不能据此声称复杂工程变速已支持。

## 导出与恢复

`--timeout` 是顶层参数。批量字幕建议 120 秒；导出可按素材复杂度提高，最大 300 秒。原生输出先到专属暂存文件，绑定真实任务、等待完成、独立解码和状态检查后发布。

新增三工具支持 `--request-id`，回执包含已完成步骤、创建对象及恢复文件。多步操作可能部分完成，既不是自动整批回滚，也不是一键重放全部。未知结果保留记录，先核实 worker、原生任务与真实对象状态。

带封面的 MP3 可能被原生 `probe` 判定为视频。已验证的处理方式是先通过 FFmpeg CLI 解码为 WAV，再用 `add-audio`；这不是合成新音乐。
