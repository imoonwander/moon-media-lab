# Moon Media Lab 核心功能与操作手册

`moon-media-lab` 是本地优先的媒体知识提炼底座：把文件和在线媒体加工成源文稿、整理稿、角色稿、英文稿、结构化知识、推荐报告、信息图和可导入 Wiki 的资产包。声音命令在迁移期兼容保留，长期实现归 `moon-voice-lab`。

它不负责最终视频渲染。`moon-video-cast` 等下游项目只消费导出的音频与时间轴。

## 1. 核心功能

| 能力 | 输入 | 命令 | 主要输出 |
| --- | --- | --- | --- |
| 环境体检 | 本机环境 | `moon-media doctor` | 引擎、模型、ffmpeg、LLM CLI 状态 |
| 处理媒体 | 音频/视频/URL/job | `moon-media process` | 按 preset 生成转录、知识、报告或 Wiki 包 |
| 仅下载 | 在线 URL | `moon-media download` | 原始视频/音频和来源 sidecar |
| 学习音色 | 描述或授权参考音 | `moon-media learn voice` | 版本化候选音色资产 |
| 查看资产 | 本地资产库 | `moon-media assets` | 资产列表、状态与 manifest |
| 创作旁白 | 文本 + 音色资产 | `moon-media create narration` | narration、timings、metrics |
| 断点恢复 | 中断 job | `moon-media resume` | 从 chunk checkpoint 继续 |
| 底层转录 | 音频/视频/URL | `moon-media transcribe` | 只创建转录 job，供脚本和排障使用 |
| 知识可视化 | `knowledge.md` | Codex `imagegen` / gpt-image-2 | 信息结构图、prompt、provenance |
| 知识资产化 | 完成的 job | `moon-media package` | 四层 manifest、hash、provenance |
| Wiki 导出 | 知识 job | `moon-media export wiki` | Markdown + JSON 可移植资产包 |
| 模型管理 | 模型名称 | `moon-media models` | 项目本地模型与缓存 |
| 普通 TTS | 文本 | `moon-media tts` | Edge TTS 音频 |
| 音色资产库 | 已验收音色 | `assets/voices/` | profile、manifest、reference、samples |
| Web UI | 文件、URL、job | `moon-media serve` | 本地网页（beta） |

职责边界：

```text
本地文件 / 在线媒体 → ASR job → transcript + subtitles → 可选 LLM 后处理
  → knowledge.md → 可选 Codex gpt-image-2 信息结构图

兼容期可选声音插件：文本 / 音色描述 / 授权参考音频
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

## 3. 处理本地媒体

中文：

```bash
.venv/bin/moon-media process interview.m4a --preset knowledge --language zh
```

中文访谈 + 说话人标签：

```bash
.venv/bin/moon-media process interview.m4a --preset interview --language zh
```

英文逐词时间戳：

```bash
.venv/bin/moon-media process podcast.mp3 \
  --preset english --language en --word-timestamps
```

中英混合：

```bash
.venv/bin/moon-media process meeting.mp4 --preset knowledge --language mixed
```

自动路由：`zh → SenseVoice`；中文加 `--diarization → Paraformer + CAM++`；`en/mixed → faster-whisper`。一般不要强制引擎，排查时才加 `--engine`。

## 4. 在线媒体与播放列表

平台能力会随站点策略变化。先看带图标、日期、验证层级和失败条件的
[`platform-support.md`](platform-support.md)，再选择命令；没有验证记录的平台不作支持承诺。

直接处理 URL：

```bash
.venv/bin/moon-media process "https://example.com/audio.mp3" --preset knowledge --language zh
```

YouTube / Bilibili：

```bash
MOON_MEDIA_LAB_COOKIES_BROWSER=chrome \
  .venv/bin/moon-media process "<URL>" --preset knowledge --language zh
```

抖音：

```bash
.venv/bin/moon-media process "https://v.douyin.com/..." --preset knowledge --language zh
```

只下载、不转录或总结：

```bash
.venv/bin/moon-media download "<URL>" --format video
.venv/bin/moon-media download "<URL>" --format audio
```

下载结果带 `.source.json` sidecar，记录来源 URL、格式和 SHA-256。播放列表暂时使用兼容入口：

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
.venv/bin/moon-media process long.mp3 --preset knowledge --language zh --chunk-sec 600
```

中断后继续：

```bash
.venv/bin/moon-media resume jobs/transcribe-YYYYMMDD-HHMMSS
```

判断成功要看本次 `state.json`、`run.log` 和真实产物，不能只看同日期文件名。

## 6. preset 与已有 job 增量处理

新来源用 preset 表达目标：

| preset | 主要产物 |
| --- | --- |
| `transcript` | 源文稿与字幕 |
| `knowledge` | 整理稿、知识稿、结构化知识 |
| `interview` | 说话人识别、角色稿、知识资产 |
| `english` | 英文整理稿、学习稿、结构化知识 |
| `research` | 知识稿、结构化知识、推荐报告 |
| `wiki` | 完整知识层、推荐报告、manifest、Wiki export |

已有 job 用 `--add` 增量生成，不重新跑 ASR：

```bash
.venv/bin/moon-media process jobs/transcribe-... \
  --add recommendations --llm codex-cli
```

| 操作 | 参数 | 输出 |
| --- | --- | --- |
| 知识整理 | `--add knowledge` | `knowledge.md` |
| 结构化知识 | `--add structured-knowledge` | `knowledge.structured.json` |
| 推荐报告 | `--add recommendations` | `recommendations.md` |
| 英语学习 | `--add english-study` | `english-study.md` |
| 提炼 SOP | `--add skill` | `skill-draft.md` |
| 清理转录 | `--add clean` | `transcript.clean.md` |
| 说话人命名 | `--add name-speakers` | 重写 transcript 和字幕 |

组合示例：

```bash
.venv/bin/moon-media process jobs/transcribe-... \
  --add clean --add knowledge --add name-speakers --llm claude-cli
```

可用 adapter：`claude-cli`、`codex-cli`、`gemini-cli`、`mock`。处理来源写入 `postproc/provenance.json`。

## 7. 使用 gpt-image-2 生成信息结构图

知识总结通过人工核对后，可以增加一个 Codex 可视化步骤：

```text
knowledge.md
  → 提炼受控短标签和结构关系
  → Codex imagegen / gpt-image-2
  → 视觉与事实 QC
  → visuals/*.png + provenance.json
```

这个步骤由 Codex 内置 `image_gen` 执行，不是本地 `moon-media` CLI。项目不保存
OpenAI API key，也不把不存在的模型命令写进 shell workflow。

推荐向 Codex 发出：

```text
读取 jobs/<job-id>/knowledge.md，提炼一张中文信息结构图。
使用 imagegen skill 和 gpt-image-2；先锁定所有图中文字，再生成。
最终图片、diagram brief 和 provenance 保存到该 job 的 visuals/。
```

完整输入输出契约、prompt 模板和 QC 见
[`knowledge-visualization-workflow.md`](knowledge-visualization-workflow.md)。

## 8. 普通 TTS

适合快速旁白，不建立长期独特音色：

```bash
.venv/bin/moon-media tts "今天分享一个新的想法。" \
  --engine edge-tts \
  --voice zh-CN-XiaoxiaoNeural \
  --output output/quick-voice.mp3
```

也可以把文本文件路径作为第一个参数。Edge TTS 依赖网络；需要长期统一声线时使用音色资产流程。

## 9. 音色设计、克隆与资产

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

## 10. 模型管理

```bash
.venv/bin/moon-media models list
.venv/bin/moon-media models download sensevoice
.venv/bin/moon-media models download paraformer
.venv/bin/moon-media models download large-v3-turbo
.venv/bin/moon-media models download large-v3-turbo --mirror
.venv/bin/moon-media models prune
```

模型和缓存都在项目的 `models/`、`cache/`；中断后直接重跑。`prune` 清理残留的 `.part` / `.incomplete`。

## 11. Web UI

```bash
.venv/bin/pip install -e '.[web]'
.venv/bin/moon-media serve --host 127.0.0.1 --port 8765
```

打开 `http://127.0.0.1:8765`。Web UI 仍是 beta；批处理、精确排障和音色资产管理优先使用 CLI。

## 12. 常见故障

| 现象 | 第一检查点 |
| --- | --- |
| `ffmpeg not found` | `brew install ffmpeg` 或设置 `MOON_MEDIA_LAB_FFMPEG` |
| 模型存在但引擎不可用 | 对应 Python extra 未安装，先看 `doctor` |
| `No Metal device available` | 当前终端/沙箱拿不到 GPU，换到可访问 macOS Metal 的会话 |
| 模型下载慢 | 使用 `--mirror` 或 ModelScope，保留断点后重跑 |
| YouTube/Bilibili 需要登录 | 设置 `MOON_MEDIA_LAB_COOKIES_BROWSER=chrome` |
| 长任务中断 | `moon-media resume <job>` |
| LLM 后处理失败 | 单独确认所选 CLI 可用，再看 `run.log` 和 provenance |
| 信息结构图文字错误 | 缩短并锁定 `Text (verbatim)`，重新生成，不要发布错误版本 |
| 音色不像 | 更换 10-30 秒、更干净且逐字稿准确的 reference |
| 音色夹带音乐/混响 | 参考音轨污染；换素材，不要只调 temperature |

排障时报告第一个失败门槛，并附命令、退出码、`run.log`、`state.json` 和相关模型路径。

## 13. 推荐日常顺序

```text
1. doctor
2. 确认输入与目标产物
3. 选择 ASR/TTS 引擎或音色资产
4. 运行 job / voice run
5. 检查 state.json / run.json 和真实输出
6. 人工阅读或试听
7. 用 preset 或 `--add` 补齐目标资产
8. 已确认的 knowledge 可用 Codex gpt-image-2 生成结构图并做文字 QC
9. export / 下游项目只消费已验收产物
```

快速选择：

- 音视频/URL/job 加工 → `process --preset ...`
- 只获取在线原始媒体 → `download`
- 播放列表批处理（兼容期）→ `learn media --playlist`
- 描述或参考音频学习音色 → `learn voice design|clone`
- 查看、审核与预览音色资产 → `assets voices list|show|approve|preview`
- 用资产生成旁白 → `create narration`
- 中断后继续 → `resume`
- 底层单次转录与排障 → `transcribe`
- 知识笔记变信息结构图 → Codex `imagegen` / gpt-image-2
- 快速普通旁白 → `tts`
- 最终视频渲染 → 不在本项目；把 narration/timings 交给视频项目
