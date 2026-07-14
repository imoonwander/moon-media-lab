# 平台支持与验证记录

平台网页、反爬策略和 `yt-dlp` 提取器都会变化。本页只把有证据的能力写成“已验证”，并记录验证层级与日期。

## 状态含义

- ✅ **已验证**：表格中声明的能力已真实运行成功；是否跑到转录以“验证结果”为准。
- 🟡 **条件支持**：解析或历史端到端成功，但当前运行需要 Cookie、登录或其他前置条件。
- 🧪 **流解析已验证**：本次能解析到可用媒体流，尚未跑完整下载与转录。
- ⚪ **未验证**：实现可能由 `yt-dlp` 覆盖，但项目不作支持承诺。

## 当前矩阵

| 输入源 | 状态 | 2026-07-14 验证结果 | 使用方式 | 条件与边界 |
| --- | --- | --- | --- | --- |
| <img src="assets/platforms/local-file.svg" width="22" alt="Local file"> 本地文件 | ✅ 端到端已验证 | 多个 WAV、MP4、M4A job 已完成转录 | `moon-media process video.mp4 --preset knowledge` | 只要本机 ffmpeg 能读取；文件保持原位引用 |
| <img src="assets/platforms/direct-url.svg" width="22" alt="Direct URL"> HTTP(S) 直链 | ✅ 下载已验证 | 3 秒 MP3 完整下载，sidecar 已生成 | `moon-media download "https://…/audio.mp3"` | URL 必须直接返回公开媒体；本次未重复跑 ASR |
| <img src="assets/platforms/youtube.svg" width="22" alt="YouTube"> YouTube | 🧪 流解析已验证 | 使用 Node JS runtime 成功解析 213 秒 WebM 音频流 | `moon-media process "https://youtu.be/…" --preset english` | 地区、年龄或账号限制视频可能需要 Cookie；本次未完整下载/转录 |
| <img src="assets/platforms/bilibili.svg" width="22" alt="Bilibili"> Bilibili | 🟡 条件支持 | 2026-07-04 有完整下载与转录；本次无 Cookie 探测返回 HTTP 412 | `MOON_MEDIA_LAB_COOKIES_BROWSER=chrome moon-media process "https://www.bilibili.com/video/BV…" --preset knowledge` | 通常需要已登录浏览器 Cookie；本次未读取浏览器凭据复测 |
| <img src="assets/platforms/douyin.svg" width="22" alt="Douyin"> 抖音 | ✅ 端到端已验证 | 短链完整下载成功并生成 SHA-256 sidecar；另有多个成功转录 job | `moon-media process "https://v.douyin.com/…" --preset knowledge` | 当前验证的是公开视频与视频下载；私密/失效链接不支持，音频专用下载未单独验证 |

### 本次结果摘要

- HTTP(S) 直链：退出码 `0`；MP3 与 `.source.json` 均生成；媒体 SHA-256 为 `0244590f…abcb44`。
- YouTube：退出码 `0`；探测输出为 `Youtube | 213 sec | webm`；使用本机 Node `v24.3.0`。
- Bilibili：无 Cookie 探测在网页获取阶段失败，第一失败门槛为 `HTTP 412`；没有继续假设下载或 ASR 成功。
- 抖音：退出码 `0`；MP4 与 `.source.json` 均生成；媒体 SHA-256 为 `4c7513f4…f9cbc0`。
- 本地媒体：已有 2026-07-14 的 MP4 → transcript → structured knowledge → Wiki bundle 完整 job 证据。

## 验证命令

实时验证只使用公开样本，下载文件写入 `/tmp`，不进入 Git。平台视频 ID 可能失效，因此复测时应替换为当前公开且有权处理的短样本。

```bash
# 普通直链：完整下载 + sidecar
moon-media download "https://samplelib.com/lib/preview/mp3/sample-3s.mp3" \
  --format audio --output-dir /tmp/moon-media-platform-verify/direct

# YouTube：流解析探测；项目会在检测到 Node 时传给 yt-dlp
yt-dlp --no-playlist --simulate --js-runtimes node \
  -f 'bestaudio/best' --print '%(extractor_key)s|%(id)s|%(duration)s|%(ext)s' \
  "https://www.youtube.com/watch?v=<video-id>"

# 抖音：完整下载 + sidecar
moon-media download "https://v.douyin.com/<share-id>/" \
  --format video --output-dir /tmp/moon-media-platform-verify/douyin
```

Bilibili 的 Cookie 复测会读取本机浏览器认证状态，只应由用户在明确知情后执行。文档不能因为 `yt-dlp` 理论上有 extractor，就把任意站点列为已支持。

## 更新规则

1. 新增平台前，至少验证“URL 解析 → 媒体下载”；要标 ✅，还需验证 ffmpeg 解音轨与 ASR job。
2. 记录日期、命令、退出码、是否使用 Cookie，以及第一个失败门槛。
3. 连续复测失败的平台从 ✅ 降为 🟡 或 ⚪，不要保留过期承诺。
4. 图标只用于帮助识别输入源，不代表平台官方合作；来源见 [`assets/platforms/README.md`](assets/platforms/README.md)。
