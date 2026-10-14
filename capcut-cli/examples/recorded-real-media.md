# 从空白工程到真实素材成片：录屏重放

本例录下实际 CapCut 窗口和正在执行的命令，从 `project create` 开始，依次完成素材库导入、独立时间线、原生裁剪、缩放、现场生成双语字幕、配乐、原生 MP4 导出及保存重开验收。素材与三段剪辑选择见[真实素材案例](real-media.md)。

字幕不复用该案例的旧字幕：本次粗剪先由 CapCut 导出，再使用本地 `faster-whisper base.en` 识别人声和逐词时间。当前 Agent 阅读新识别结果，现场编写中文译文和分句，`assemble_captions.py` 校验时间并生成 JSON/SRT，最后由 `captions-import` 建立原生可编辑文本。语音识别、翻译、格式转换的职责分别记录，格式转换脚本不声称自己会翻译。

2026-10-14 实际验收通过：原生剪辑与成片 26 项检查；录屏 6 项检查及画面抽查。完整演示长 248.43 秒，前 214.73 秒为实际操作，片尾为有声音的成片播放。[验收摘要与文件校验值](../evidence/recorded-real-media-20261014.json)。本机交付文件为 `exports/capcut-cli-demo-20261014.mp4`、`exports/water-science-fresh-subtitles-20261014.mp4` 和同名 SRT；大体积视频不随源码提交。

## 本地重放

需要受支持的 CapCut、适配器运行环境，以及之前下载的 NASA 视频、Fluidscape 音乐和编辑计划。媒体与模型不随源码分发。录屏新增依赖 `windows-capture==2.0.1`、`opencv-python-headless==5.0.0.93` 安装在 D 盘的 `.native-tools`；Pillow、NumPy 复用现有环境。语音环境在 `D:\Apps\CapCutAgentSpeech`，模型和缓存位于 `D:\Caches\CapCutAgentSpeech`。

```powershell
cd D:\ChatGPT\reverse-cli\capcut-cli
# 使用已配置的 Python 和当前 CapCut 主进程 PID；输出目录必须不存在。
python -B tools/record_real_media.py --pid <PID> --output-dir D:/ChatGPT/reverse-cli/capcut-cli/capcut-analysis/<NEW_RUN>
```

运行到 `AWAITING_FRESH_TRANSLATION` 时，Agent 读取这次输出的 `source-asr.json`，编写新的 `fresh-translations.json`。每条包含 `startSeconds`、`endSeconds`、`english` 和 `chinese`。脚本等待文件出现后继续导入；它不读取旧英文/中文字幕。`sources.json`、`subtitle-provenance.json` 和逐命令回执保留来源说明。

完成后包装录屏：

```powershell
python -B tools/finalize_real_recording.py --run-dir D:/ChatGPT/reverse-cli/capcut-cli/capcut-analysis/<NEW_RUN>
```

`capcut-from-blank-recording.mp4` 是未经加速的完整操作录屏，15 fps；底部命令来自实际 subprocess 参数，完整路径和返回值另存回执。`capcut-cli-complete-demo.mp4` 在其末尾附加明确标记的 33.7 秒成片播放，带原声和音乐。操作录屏本身不采集麦克风或系统音频。`water-science-final.mp4` 是单独保留的原始 CapCut 导出文件。

## 验收与录制方法

验收检查空白工程、3 段视频时序、原生缩放、配乐音量与淡变、现场字幕、保存重开，以及输出的 1011 帧完整解码、1080p30 H.264/AAC、音源拟合、语音识别、源画面和原生帧一致性。另对录屏完整解码并抽查空白工程、剪辑、字幕生成、导出和验收画面。

录屏使用 [Windows Capture 的 Windows Graphics Capture 接口](https://github.com/NiiightmareXD/windows-capture/tree/main/windows-capture-python)，按目标 PID 跟随首页/编辑器 HWND，不需要鼠标或键盘事件。它直接采集窗口合成画面，避免其他会话遮挡窗口时把无关桌面内容录进去。

录屏预检中，旧 GDI BitBlt 方案曾录入遮挡窗口，已判为不合格；PrintWindow 方案随后遇到原生导出调度超时，保留错误回执后停止。交付录屏使用 WGC 从新空白工程重新执行。成功导出和仅仅“录屏文件可解码”必须分别验证，不能用后者代替视觉验收。

完整本地证据存于被忽略的 `capcut-analysis/recorded-real-media-20261014-wgc/`，原始交付视频位于 `exports/`，精选验收摘要在 `evidence/`。新增[统一英文展示版](../assets/capcut-cli-demo.mp4)位于 `assets/`，允许随仓库分发；[来源与署名](../../docs/demos/README.md)。不包含软件安装包、私有二进制或模型文件。
