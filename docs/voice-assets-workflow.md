# Voice Assets Workflow

这份 SOP 定义 `moon-media-lab` 的 TTS、音色设计、授权音色克隆、资产沉淀和对外导出流程。未来如果单独建立 voice skill，skill 应编排这里的能力，而不是把模型和资产迁入下游项目。

## 职责边界

```text
moon-media-lab
  参考音视频检查 → 取音 → VoiceDesign/Clone → A/B 试听
  → 音色资产入库 → 旁白生成 → timings → 导出素材包

moon-video-cast 等消费者
  接收 narration.wav + timings.json + voice-manifest.json
  → 混音、字幕卡点、画面渲染、视频 QC
```

`moon-media-lab` 拥有模型适配器和音色资产正本。消费者只拥有某期使用的素材副本，不负责学习、设计或管理音色。

## 1. 音色来源与授权

支持两种来源：

- **VoiceDesign**：用文字描述创造不存在于真人来源中的音色。
- **VoiceClone**：使用本人声音，或已取得声音所有者明确授权的参考录音。

当前克隆是 zero-shot conditioning，不训练、不微调模型。未经授权的真人或公众人物声音不得克隆、入库或导出。

## 2. 参考素材检查

推荐参考素材：

- 10-30 秒、单人、普通话、自然语气。
- 无背景音乐、强混响和明显降噪伪影。
- WAV 最佳；MP4、M4A、MP3 可以先提取。
- 必须有与实际语音完全一致的逐字稿。

```bash
ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=index,codec_type,codec_name,sample_rate,channels,duration \
  -of json reference.mp4

ffmpeg -hide_banner -i reference.mp4 \
  -map 0:a:0 -af volumedetect -f null -
```

多人重叠、音乐盖住人声、严重削波、逐字稿不确定时，应换素材而不是继续克隆。

## 3. 提取标准参考 WAV

```bash
mkdir -p assets/voices/<voice-id>/samples

ffmpeg -y -i reference.mp4 \
  -vn -ac 1 -ar 24000 -c:a pcm_s16le \
  assets/voices/<voice-id>/reference.wav
```

只裁掉明确的无声头尾，不破坏呼吸、尾音和自然停顿。

## 4. Profile 与 Manifest

`profile.json` 保存模型输入：

```json
{
  "id": "voice-id-v1",
  "description": "",
  "referenceText": "与参考录音完全一致的逐字稿。",
  "language": "Chinese",
  "cloneModel": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-6bit",
  "seed": 42,
  "temperature": 0.65,
  "pauseMs": 180
}
```

`manifest.json` 保存资产治理信息：

```json
{
  "id": "voice-id-v1",
  "version": 1,
  "sourceType": "voice-design-or-authorized-clone",
  "authorization": "confirmed",
  "referenceSha256": "...",
  "status": "candidate",
  "createdAt": "YYYY-MM-DD"
}
```

真人姓名、原始下载路径和账号信息不写进可公开文件。资产目录本身也默认忽略 Git。

## 5. 短句 A/B 验收

先用与参考台词不同的 15-35 字文本生成试听：

```bash
moon-media create narration assets/voices/<voice-id>/sample.txt \
  --voice <voice-id> \
  --output-dir output/voice-runs/<voice-id>-sample
```

检查音色年龄感、声线、语速、停顿、句尾、可懂度，以及是否复制了背景音乐或混响。未通过时优先更换更干净的参考录音。

通过人工试听后：

- 把验收样本复制到 `assets/voices/<voice-id>/samples/`。
- 把 manifest 的 `status` 改为 `approved`。
- 冻结 reference、profile 和 SHA-256。更换任一核心输入时升版本。

## 6. 生成项目旁白

使用已批准的音色资产生成任意项目旁白：

```bash
moon-media create narration path/to/narration.txt \
  --voice <voice-id> \
  --output-dir output/voice-runs/<run-id>
```

输出至少包含：

```text
<voice-id>.narration.wav # 完整旁白
<voice-id>.timings.json  # 真实采样数计算的逐句 start/end
<voice-id>.run.json      # 模型、耗时、内存和复现参数
```

## 7. 导出给消费者

导出包只提供消费所需内容：

```text
exports/<run-id>/
  narration.wav
  timings.json
  voice-manifest.json
```

`voice-manifest.json` 只保留 `voiceId`、版本、引擎、采样率、时长和音频 SHA-256；不带参考逐字稿、授权文件、真人身份或 reference WAV。

下游项目可以复制导出包，但不得把副本当作音色资产正本，也不应实现克隆模型调用。

## 8. 音频 QC

```bash
ffprobe -v error \
  -show_entries stream=codec_name,sample_rate,channels,duration \
  -show_entries format=duration,size \
  -of json output/voice-runs/<run-id>/narration.wav

ffmpeg -hide_banner \
  -i output/voice-runs/<run-id>/narration.wav \
  -af volumedetect -f null -
```

验收要求：

- 文本完整，无吞字、错读、重复或截断。
- 峰值低于 0dB，建议保留至少 1dB 余量。
- 同一音色不同批次的声线和整体响度接近。
- `timings.json` 的最终 `end` 与 WAV 时长一致。
- reference SHA-256、profile、seed 和模型版本可追溯。

## 9. 未来 Skill 边界

未来独立 Skill 可以用自然语言收集参数，再编排已经统一的 lifecycle 命令：

```text
moon-media learn voice design ...
moon-media learn voice clone ...
moon-media assets voices list|show
moon-media create narration ...
```

Skill 只做参数收集、授权确认、命令编排、试听和资产登记；底层实现仍调用 `moon-media-lab`，音色资产仍存放在本项目的 `assets/voices/`。
