# Moon Media Lab · 月亮媒体实验室

**[English](README.md) · 简体中文**

本地优先的媒体实验室：把音频、视频、在线媒体转成转录稿、字幕、
知识笔记、学习材料——以及语音。

```text
本地文件 / YouTube / Bilibili / 抖音 / 直链
        │
        ▼
  transcribe（SenseVoice · Paraformer+CAM++ · faster-whisper）
        │
        ▼
  transcript.md + segments.srt/vtt （带时间戳、说话人）
        │
        ▼
  process（用你已有的任意 LLM 命令行）
        │
        ▼
  knowledge.md · english-study.md · skill-draft.md · transcript.clean.md
```

**语音识别全程在你自己的电脑上运行。** LLM 后处理是可选的，走你本来
就在用的命令行（`claude`、`codex`、`gemini`）；每份产物都会在
`postproc/provenance.json` 里记录是哪个提供方处理的数据。

## 功能

- **中文 ASR** —— SenseVoice（快）或 Paraformer + CAM++，配
  `--diarization` 做带说话人标签的访谈转录
- **英文 ASR** —— faster-whisper `large-v3-turbo`，逐段时间戳与置信度
- **说话人命名** —— `process --name-speakers` 把 `SPEAKER_00` 换成
  推断出的真名/角色，并重渲染转录稿和字幕
- **在线媒体** —— `transcribe <链接>` 用 yt-dlp 下载
  （YouTube/Bilibili 需浏览器 cookies）；抖音用内置的免 cookies 直连下载
- **长音频** —— 静音对齐切块、逐块 checkpoint、`resume <job目录>`
  断点续传、进度/ETA、运行中的 `transcript.partial.md`
- **播放列表** —— `--playlist [--playlist-items 1-5]`，一集一个 job
- **字幕** —— 每个 job 都产出 `segments.srt` / `segments.vtt`
- **LLM 后处理** —— 摘要/大纲/知识卡片、英语学习笔记、SOP 草稿、
  分批并发的转录稿清理
- **TTS 语音合成** —— `moon-media tts`，基于 Edge 神经语音
- **自包含模型** —— `models list|download|prune`，断点续传下载，
  `--mirror` 走 hf-mirror.com；绝不写入 `~/.cache`
- **Web 界面（beta 预览）** —— `moon-media serve` 启动本地网页应用
  （提交文件/链接、实时进度、点时间戳跳播、内联预览、一键后处理）；
  每个 job 还会写机器可读的 `state.json`，job 目录即 API。
  Web 的活跃开发在 `web-ui` 分支（0.2.x 线）

## 安装

需要 Python 3.9+（推荐 3.10+）和 [ffmpeg](https://ffmpeg.org)。

```bash
git clone <仓库地址> && cd moon-media-lab
python3 -m venv .venv
.venv/bin/pip install -e '.[asr-sensevoice,asr-whisper,url,tts-edge]'
.venv/bin/moon-media doctor   # 体检报告：什么已就绪、下一步做什么
```

`moon-media doctor` 会打印 ffmpeg、引擎、LLM 命令行、已下载模型的
✓/○/✗ 清单，最后给出裁决——你现在能不能转录，或者差哪一步。
第一件事就跑它。

只装你需要的 extra——基础 CLI 零依赖。

**全局安装**（任何目录都能用 `moon-media`）：

```bash
pipx install 'moon-media-lab[asr-sensevoice,asr-whisper,url,tts-edge]'
# 或从克隆目录：ln -s "$(pwd)/.venv/bin/moon-media" ~/.local/bin/moon-media
```

在线媒体建议在 PATH 上放一个独立的 `yt-dlp` 二进制（站点提取器
更新很快，pip 版会被你的 Python 版本锁死）。

## 快速上手

```bash
# 自带的 8 秒中文样例
.venv/bin/moon-media transcribe examples/hello-zh.wav --language zh

# 带说话人标签的中文访谈（首次会下载约 1.2 GB 模型）
.venv/bin/moon-media transcribe interview.m4a --language zh --diarization

# YouTube 英文播客（首次下载约 1.6 GB；国内加 --mirror）
.venv/bin/moon-media models download large-v3-turbo --mirror
MOON_MEDIA_LAB_COOKIES_BROWSER=chrome \
  .venv/bin/moon-media transcribe "https://youtu.be/..." --language en

# 用你已有的 LLM 命令行后处理一个完成的 job
.venv/bin/moon-media process jobs/transcribe-... --mode knowledge --clean --llm codex-cli

# 或者用浏览器完成上述一切
.venv/bin/pip install -e '.[web]'
.venv/bin/moon-media serve        # → http://127.0.0.1:8765
```

每次运行会创建 `jobs/<job-id>/`，内含 `transcript.md`、
`transcript.raw.json`、`segments.srt/vtt`、`run.log` 以及各种后处理
产物。**job 目录就是 API——不需要学别的。**

## 命令

| 命令 | 用途 |
|------|------|
| `doctor` | 体检报告：ffmpeg、引擎、LLM 命令行、模型、裁决 |
| `transcribe <源>` | 把文件/链接转成转录 job |
| `resume <job目录>` | 续跑一个被中断的转录 job |
| `process <job目录>` | 对完成的 job 做 LLM 后处理 |
| `models list\|download\|prune` | 管理本地 ASR 模型 |
| `tts <文本>` | 文字转语音（edge-tts） |
| `moon-media-voice-case` | 本地设计并克隆 Qwen3 音色，产出视频时间轴 |
| `serve` | 本地 Web 界面（beta） |

### transcribe

```bash
moon-media transcribe <源> [选项]
```

| 选项 | 取值 / 默认 | 含义 |
|------|-------------|------|
| `--language` | `auto` `zh` `en` `mixed` | 语言；决定引擎路由 |
| `--engine` | `auto` `sensevoice` `paraformer` `faster-whisper` `mock` | 强制指定引擎（一般留 `auto`） |
| `--mode` | `transcript`（默认）`knowledge` `english-study` `skill` | 转录后额外生成该文档 |
| `--diarization` | 开关 | 标注说话人（中文；路由到 paraformer+CAM++） |
| `--kind` | `file` `url` `text` | 源类型（http(s) 会自动识别） |
| `--chunk-sec` | `600` | 长音频切块长度（秒） |
| `--llm` | `auto` `claude-cli` `codex-cli` `gemini-cli` | `--mode` 后处理用的提供方 |
| `--playlist` | 开关 | 转录播放列表/多 P 的每一集 |
| `--playlist-items` | `1-5` 或 `1,3,7` | 选哪几集 |
| `--word-timestamps` | 开关 | 逐词时间戳（faster-whisper） |
| `--job-dir` / `--model-dir` | 路径 | 覆盖 jobs 根目录 / 模型路径 |

`--engine auto` 时的语言路由：`zh → sensevoice`（带 `--diarization`
则 `paraformer`），`en`/`mixed → faster-whisper`。

### process

对完成的 job 做后处理，**无需重新转录**——转录产物已在磁盘上，
所以可以廉价地重跑和重试。

```bash
moon-media process <job目录> [--mode ...] [--clean] [--name-speakers] [--llm ...]
```

| 选项 | 产物 | 作用 |
|------|------|------|
| `--mode knowledge` | `knowledge.md` | 摘要、带时间戳大纲、知识卡片、金句 |
| `--mode english-study` | `english-study.md` | 生词、表达、语法点、练习 |
| `--mode skill` | `skill-draft.md` | 从内容提炼可复用的 SOP/操作指南 |
| `--clean` | `transcript.clean.md` | 修同音字、去语气词、加标点（分批、并发、有 checkpoint） |
| `--name-speakers` | 重写 `transcript.md` + 字幕 | 根据上下文推断 `SPEAKER_NN` 的真名/角色 |

LLM 提供方就是你已有的命令行——`claude`、`codex`、`gemini`——作为
可互换的 adapter（不用额外 API key）。每份产物都会在
`postproc/provenance.json` 记录是哪个提供方看过数据。

### models

```bash
moon-media models list                          # 已下载模型 + 体积
moon-media models download sensevoice           # 中文 ASR（走 ModelScope）
moon-media models download paraformer           # 说话人分离全家桶（约 1.2 GB）
moon-media models download large-v3-turbo        # 英文 ASR（约 1.6 GB）
moon-media models download large-v3-turbo --mirror   # 走 hf-mirror.com（国内更快）
moon-media models prune                         # 清理中断的 .part/.incomplete
```

模型按文件下载，支持 HTTP-Range 断点续传——中断后重跑会接着下。
一切落在项目的 `models/` 和 `cache/`；绝不写入 `~/.cache`。

### 本地音色设计 + 视频旁白（Apple Silicon）

可选的 Qwen3-TTS MLX 工作流会先用文字描述设计一段可复用的参考音色，
再逐句克隆该音色。最终同时写出 WAV 和按真实采样数计算的逐句时间轴，
视频渲染器可以用同一份产物驱动旁白、字幕和场景切换。

```bash
pip install -e '.[tts-qwen3-mlx]'

moon-media-voice-case \
  --text-file /path/to/narration.txt \
  --profile /path/to/voice-profile.json \
  --output-dir output/voice-case
```

首次运行会下载 profile 指定的 VoiceDesign 与 Base/clone 模型，模型文件遵循
项目本地缓存设置。音色确定后可加 `--reuse-reference`，保留参考音色，只重做
旁白。音频仍是本地实例产物；可复现的正本是 JSON 音色 profile。

如果模型已通过 ModelScope 或 Hugging Face 下载到本地，可用
`MOON_MEDIA_LAB_QWEN3_DESIGN_MODEL` 和 `MOON_MEDIA_LAB_QWEN3_CLONE_MODEL`
覆盖 profile 中的远程模型 ID。

## 输入源

| 源 | 命令 | 说明 |
|----|------|------|
| 本地文件 | `transcribe audio.m4a` | mp3/m4a/wav/mp4/mov… ffmpeg 能读的都行 |
| 直链 | `transcribe https://…/a.mp3` | 无需配置 |
| YouTube | `MOON_MEDIA_LAB_COOKIES_BROWSER=chrome transcribe "https://youtu.be/…"` | 需浏览器 cookies + JS 运行时（node）过 n-challenge，均自动检测 |
| Bilibili | `MOON_MEDIA_LAB_COOKIES_BROWSER=chrome transcribe "https://www.bilibili.com/video/BV…"` | 需 cookies；瞬时 412 自动重试 |
| 抖音 | `transcribe "https://v.douyin.com/…"` | **免 cookies**——内置直连 CDN 下载 |
| 播放列表 | `transcribe "<链接>" --playlist --playlist-items 1-10` | 一集一个 job，失败跳过继续 |

在线媒体先下载到 `downloads/`（用 `yt-dlp`；优先用 PATH 上的独立
二进制）。有反爬的站点设 `MOON_MEDIA_LAB_COOKIES_BROWSER`
（chrome/firefox/edge…）或 `MOON_MEDIA_LAB_COOKIES_FILE`。

## job 目录

```text
jobs/transcribe-YYYYMMDD-HHMMSS/
  input.json            请求参数
  state.json            状态/进度/ETA（机器可读）
  media.json            探测到的时长、编码、采样率
  audio.wav             归一化的 16 kHz 单声道（真实引擎用）
  transcript.raw.json   归一化 segments（规范输出）
  transcript.md         带时间戳+说话人的可读转录稿
  segments.srt/.vtt     字幕
  run.log               人类可读的事件日志
  chunks/               逐块 checkpoint（长音频）
  postproc/             清理 checkpoint、speakers.json、provenance.json
  knowledge.md · english-study.md · skill-draft.md · transcript.clean.md
```

job 目录**就是** API——任何工具（或 Web 界面）都能轮询
`state.json` 并读取产物；没有数据库。

## 配置

一切都用环境变量，默认值指向项目本地；见 [.env.example](.env.example)。
主要几个：

```text
MOON_MEDIA_LAB_HOME              models/cache/jobs/downloads/output 的根
MOON_MEDIA_LAB_DEVICE            cpu（默认）或 cuda
MOON_MEDIA_LAB_WHISPER_MODEL     large-v3-turbo（默认）| small | medium | ...
MOON_MEDIA_LAB_WHISPER_COMPUTE   int8（默认）| float16 | ...
MOON_MEDIA_LAB_LLM_PROVIDER      claude-cli | codex-cli | gemini-cli | mock
MOON_MEDIA_LAB_LLM_CONCURRENCY   并发清理调用数（默认 3）
MOON_MEDIA_LAB_COOKIES_BROWSER   chrome | firefox | ... 用于反爬站点
MOON_MEDIA_LAB_COOKIES_FILE      cookies.txt 路径（替代浏览器方式）
MOON_MEDIA_LAB_HF_ENDPOINT       如 https://hf-mirror.com
MOON_MEDIA_LAB_FFMPEG            ffmpeg 不在 PATH 时的显式路径
MOON_MEDIA_LAB_TTS_VOICE         edge-tts 默认语音
```

默认都是项目本地的，所以新克隆开箱即自包含。复制 `.env.example`
并 `source`，或只 export 你要的。

## 疑难排查

| 现象 | 解决 |
|------|------|
| `ffmpeg not found` | `brew install ffmpeg`（或设 `MOON_MEDIA_LAB_FFMPEG`） |
| 模型下载卡住/很慢 | 加 `--mirror`，或设 `MOON_MEDIA_LAB_HF_ENDPOINT=https://hf-mirror.com`；重跑会续传 |
| 中断的下载残留 | `moon-media models prune` |
| YouTube "Requested format is not available" | 装 JS 运行时（`node`）过 n-challenge；确保 PATH 上有较新的独立 `yt-dlp` |
| Bilibili `HTTP 412` | 加 `MOON_MEDIA_LAB_COOKIES_BROWSER=chrome`；瞬时 412 会自动重试 |
| 任何站点提示 "needs cookies" | `MOON_MEDIA_LAB_COOKIES_BROWSER=<浏览器>`（须在该浏览器登录过） |
| 后处理卡住 | 检查所选 `--llm` 命令行能否单独跑通；调用超时为 300s ×2 |
| 长 job 被中断 | `moon-media resume <job目录>`——已完成的块会保留 |

任何时候都可以 `moon-media doctor` 看完整状态。

## 退出码

```text
0 成功            3 引擎未安装        6 转录失败
1 通用失败        4 媒体探测/提取失败  7 后处理失败
2 参数错误        5 模型下载/加载失败
```

## 版本线与分支

每个 minor 系列对应一个产品主题；主题内的小步走用 patch 位。

| 系列 | 主题 | 分支 |
|------|------|------|
| 0.1.x | **CLI 核心**——优秀的音视频转换、开源就绪、全局安装（当前重点） | `main` |
| 0.2.x | **Web 体验**——UI/UX 重建到达标；从 `web-ui` 分支合入 | `web-ui` |
| 0.3.x | **语音及更多**——TTS 产品化、阅读器深化、集成 | 未来 |

`main` 保持稳定并发布所有版本；大主题在各自分支孵化，成熟后作为
新系列落地。见 [Roadmap](docs/roadmap.md)。

## 文档

- [CLI 参考](docs/cli-v1-spec.md)
- [架构](docs/architecture.md)
- [引擎 adapter 规范](docs/engine-adapter-spec.md) —— 添加你自己的引擎
- [运行时与模型](docs/runtime-and-models.md)
- [Roadmap](docs/roadmap.md)
- [贡献指南](CONTRIBUTING.md)

## 致谢

- [FunASR](https://github.com/modelscope/FunASR) —— SenseVoice、Paraformer、CAM++
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- 抖音直连下载技巧来自
  [vangie/douyin-transcriber](https://github.com/vangie/douyin-transcriber)（MIT）

## 许可

[MIT](LICENSE)
