# Moon Media Lab 核心功能与操作手册

`moon-media-lab` 是本地优先的媒体与语音处理底座：把文件、在线媒体和文本加工成转录、字幕、知识文档、普通 TTS、音色资产和旁白素材包。

它不负责最终视频渲染。`moon-video-cast` 等下游项目只消费导出的音频与时间轴。

## 1. 核心功能

| 能力 | 输入 | 命令 | 主要输出 |
| --- | --- | --- | --- |
| 环境体检 | 本机环境 | `moon-media doctor` | 引擎、模型、ffmpeg、LLM CLI 状态 |
| 学习媒体 | 音频/视频/URL | `moon-media learn media` | 转录、字幕、知识文档、job |
| 学习音色 | 描述或授权参考音 | `moon-media learn voice` | 版本化候选音色资产 |
| 查看资产 | 本地资产库 | `moon-media assets` | 资产列表、状态与 manifest |
| 创作旁白 | 文本 + 音色资产 | `moon-media create narration` | narration、timings、metrics |
| 断点恢复 | 中断 job | `moon-media resume` | 从 chunk checkpoint 继续 |
| LLM 后处理 | 完成的 job | `moon-media process` | 知识笔记、清理稿、学习材料、SOP |
| 模型管理 | 模型名称 | `moon-media models` | 项目本地模型与缓存 |
| 普通 TTS | 文本 | `moon-media tts` | Edge TTS 音频 |
| 音色资产库 | 已验收音色 | `assets/voices/` | profile、manifest、reference、samples |
| Web UI | 文件、URL、job | `moon-media serve` | 本地网页（beta） |

职责边界：

```text
本地文件 / 在线媒体 → ASR job → transcript + subtitles → 可选 LLM 后处理

文本 / 音色描述 / 授权参考音频
  → TTS / VoiceDesign / VoiceClone
  → assets/voices 音色正本
  → narration + timings + manifest
  → 下游播客、视频或内容项目
```

真人参考音频、私人逐字稿、生成音频和模型文件默认不提交 Git。

## 2. 安装与体检

需要 Python 3.9+ 和 ffmpeg：

```bash
brew install ffmpeg
python3 -m venv .venv
```

按需安装：

```bash
.venv/bin/pip install -e '.[asr-sensevoice]' # 中文 ASR
.venv/bin/pip install -e '.[asr-whisper]'    # 英文/混合 ASR
.venv/bin/pip install -e '.[url]'            # URL/播放列表
.venv/bin/pip install -e '.[tts-edge]'       # Edge TTS
.venv/bin/pip install -e '.[tts-qwen3-mlx]'  # Apple Silicon 音色设计/克隆
.venv/bin/pip install -e '.[web]'             # Web UI
```

常用组合：

```bash
.venv/bin/pip install -e '.[asr-sensevoice,asr-whisper,url,tts-edge,tts-qwen3-mlx]'
```

第一步永远是：

```bash
.venv/bin/moon-media doctor
.venv/bin/moon-media doctor --json
```

不要只看模型目录；模型存在不代表 Python 引擎依赖已经可用。

## 3. 转写本地媒体

中文：

```bash
.venv/bin/moon-media learn media interview.m4a --language zh
```

中文访谈 + 说话人标签：

```bash
.venv/bin/moon-media learn media interview.m4a \
  --language zh --diarization
```

英文逐词时间戳：

```bash
.venv/bin/moon-media learn media podcast.mp3 \
  --language en --word-timestamps
```

中英混合：

```bash
.venv/bin/moon-media learn media meeting.mp4 --language mixed
```

自动路由：`zh → SenseVoice`；中文加 `--diarization → Paraformer + CAM++`；`en/mixed → faster-whisper`。一般不要强制引擎，排查时才加 `--engine`。

## 4. 在线媒体与播放列表

直链：

```bash
.venv/bin/moon-media learn media "https://example.com/audio.mp3" --language zh
```

YouTube / Bilibili：

```bash
MOON_MEDIA_LAB_COOKIES_BROWSER=chrome \
  .venv/bin/moon-media learn media "<URL>" --language zh
```

抖音：

```bash
.venv/bin/moon-media learn media "https://v.douyin.com/..." --language zh
```

播放列表：

```bash
.venv/bin/moon-media learn media "<playlist-url>" \
  --language zh --playlist --playlist-items 1-5
```

一集一个 job；单集失败不会抹掉已完成的集数。

## 5. job 与断点恢复

每次转写创建：

```text
jobs/transcribe-YYYYMMDD-HHMMSS/
  input.json            # 请求参数
  state.json            # 状态、进度、ETA
  media.json            # 媒体信息
  audio.wav             # 归一化音频
  transcript.raw.json   # 规范 segments
  transcript.md         # 可读转录稿
  transcript.partial.md # 运行中部分结果
  segments.srt/.vtt     # 字幕
  run.log               # 事件与错误
  chunks/               # 长音频 checkpoint
  postproc/             # 后处理记录
```

长音频切块：

```bash
.venv/bin/moon-media learn media long.mp3 --language zh --chunk-sec 600
```

中断后继续：

```bash
.venv/bin/moon-media resume jobs/transcribe-YYYYMMDD-HHMMSS
```

判断成功要看本次 `state.json`、`run.log` 和真实产物，不能只看同日期文件名。

## 6. LLM 后处理

后处理读取已有转录，不重新跑 ASR：

```bash
.venv/bin/moon-media process jobs/transcribe-... \
  --mode knowledge --llm codex-cli
```

| 操作 | 参数 | 输出 |
| --- | --- | --- |
| 知识整理 | `--mode knowledge` | `knowledge.md` |
| 英语学习 | `--mode english-study` | `english-study.md` |
| 提炼 SOP | `--mode skill` | `skill-draft.md` |
| 清理转录 | `--clean` | `transcript.clean.md` |
| 说话人命名 | `--name-speakers` | 重写 transcript 和字幕 |

组合示例：

```bash
.venv/bin/moon-media process jobs/transcribe-... \
  --mode knowledge --clean --name-speakers --llm claude-cli
```

可用 adapter：`claude-cli`、`codex-cli`、`gemini-cli`、`mock`。处理来源写入 `postproc/provenance.json`。

## 7. 普通 TTS

适合快速旁白，不建立长期独特音色：

```bash
.venv/bin/moon-media tts "今天分享一个新的想法。" \
  --engine edge-tts \
  --voice zh-CN-XiaoxiaoNeural \
  --output output/quick-voice.mp3
```

也可以把文本文件路径作为第一个参数。Edge TTS 依赖网络；需要长期统一声线时使用音色资产流程。

## 8. 音色设计、克隆与资产

当前推荐 Apple Silicon。主入口统一在 `moon-media` 下：

```bash
.venv/bin/moon-media learn voice --help
.venv/bin/moon-media assets voices list
.venv/bin/moon-media create narration --help
```

音色正本：

```text
assets/voices/<voice-id>/
  manifest.json
  profile.json
  reference.wav
  samples/
```

用文字描述学习并沉淀一个合成音色：

```bash
.venv/bin/moon-media learn voice design \
  --id moon-reader-v1 \
  --description "温暖、清醒、克制的中文旁白" \
  --reference-text "你好，愿每一次阅读都让你更靠近自己。"
```

从本人或明确授权的参考音频学习音色：

```bash
.venv/bin/moon-media learn voice clone reference.mp4 \
  --id authorized-reader-v1 \
  --transcript "参考音频的准确逐字稿" \
  --authorization-confirmed
```

查看已经沉淀的音色：

```bash
.venv/bin/moon-media assets voices list
.venv/bin/moon-media assets voices show authorized-reader-v1
```

审核可对外展示的试听样本并生成静态预览页：

```bash
.venv/bin/moon-media assets voices approve authorized-reader-v1 \
  --name "Moon Reader" \
  --summary "温暖、清醒、克制的中文旁白" \
  --sample public-preview.wav \
  --usage-note "公开试听；第三方复用需另行授权" \
  --public-release-confirmed

.venv/bin/moon-media assets voices preview
open output/voice-catalog/index.html
```

预览页只收录明确确认公开权利的音色，不会带出参考音、逐字稿和内部参数。

使用音色资产创作旁白：

```bash
.venv/bin/moon-media create narration path/to/narration.txt \
  --voice authorized-reader-v1 \
  --output-dir output/voice-runs/<run-id>
```

输出：

```text
<voice-id>.narration.wav
<voice-id>.timings.json
<voice-id>.run.json
```

先用 `create narration` 做不同文案的短句 A/B，人工确认后再生成完整内容。音色克隆是 zero-shot conditioning，不是训练或微调。

`moon-media-voice-case` 暂时保留为底层兼容入口；新操作不再以它作为主命令。

详细规则：

- [`assets/voices/README.md`](../assets/voices/README.md)
- [`voice-assets-workflow.md`](voice-assets-workflow.md)

## 9. 模型管理

```bash
.venv/bin/moon-media models list
.venv/bin/moon-media models download sensevoice
.venv/bin/moon-media models download paraformer
.venv/bin/moon-media models download large-v3-turbo
.venv/bin/moon-media models download large-v3-turbo --mirror
.venv/bin/moon-media models prune
```

模型和缓存都在项目的 `models/`、`cache/`；中断后直接重跑。`prune` 清理残留的 `.part` / `.incomplete`。

## 10. Web UI

```bash
.venv/bin/pip install -e '.[web]'
.venv/bin/moon-media serve --host 127.0.0.1 --port 8765
```

打开 `http://127.0.0.1:8765`。Web UI 仍是 beta；批处理、精确排障和音色资产管理优先使用 CLI。

## 11. 常见故障

| 现象 | 第一检查点 |
| --- | --- |
| `ffmpeg not found` | `brew install ffmpeg` 或设置 `MOON_MEDIA_LAB_FFMPEG` |
| 模型存在但引擎不可用 | 对应 Python extra 未安装，先看 `doctor` |
| `No Metal device available` | 当前终端/沙箱拿不到 GPU，换到可访问 macOS Metal 的会话 |
| 模型下载慢 | 使用 `--mirror` 或 ModelScope，保留断点后重跑 |
| YouTube/Bilibili 需要登录 | 设置 `MOON_MEDIA_LAB_COOKIES_BROWSER=chrome` |
| 长任务中断 | `moon-media resume <job>` |
| LLM 后处理失败 | 单独确认所选 CLI 可用，再看 `run.log` 和 provenance |
| 音色不像 | 更换 10-30 秒、更干净且逐字稿准确的 reference |
| 音色夹带音乐/混响 | 参考音轨污染；换素材，不要只调 temperature |

排障时报告第一个失败门槛，并附命令、退出码、`run.log`、`state.json` 和相关模型路径。

## 12. 推荐日常顺序

```text
1. doctor
2. 确认输入与目标产物
3. 选择 ASR/TTS 引擎或音色资产
4. 运行 job / voice run
5. 检查 state.json / run.json 和真实输出
6. 人工阅读或试听
7. 必要时 process / export
8. 下游项目只消费已验收产物
```

快速选择：

- 音视频/URL 学习 → `learn media`
- 描述或参考音频学习音色 → `learn voice design|clone`
- 查看、审核与预览音色资产 → `assets voices list|show|approve|preview`
- 用资产生成旁白 → `create narration`
- 中断后继续 → `resume`
- 转录变知识笔记 → `process`
- 快速普通旁白 → `tts`
- 最终视频渲染 → 不在本项目；把 narration/timings 交给视频项目
