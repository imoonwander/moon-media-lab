# Voice Assets

`assets/voices/` 是 `moon-media-lab` 的本地音色资产库正本。每个通过试听确认的设计音色或授权克隆音色占一个版本化目录：

```text
assets/voices/<voice-id>/
  manifest.json       # 资产身份、版本、来源类型、授权状态、模型和校验值
  profile.json        # 参考逐字稿与生成参数
  reference.wav       # 24kHz mono PCM 参考音色
  samples/            # A/B 测试与验收样本
```

规则：

- `<voice-id>` 必须带版本，例如 `moon-reader-v1`；更换 reference 或显著改参数时升版本。
- 真人或外部来源音色必须记录授权状态；未授权音色不得进入资产库。
- 本地学习授权不等于公开展示授权。只有执行 `assets voices approve` 并确认
  `--public-release-confirmed` 的资产才可进入对外预览目录。
- 整个资产目录默认被 Git 忽略。本 README 只定义公开方法，不提交真人音频、逐字稿或身份信息。
- 具体项目不拥有音色正本。需要使用时，由 media-lab 导出 `narration.wav`、`timings.json` 和去身份化的 `voice-manifest.json`。
- 合成旁白属于某次任务输出，可放在 `output/voice-runs/`；只有通过人工试听的 reference 与样本才晋升为长期音色资产。
- 对外预览仅复制 `samples/` 中显式指定的试听 WAV；不复制 reference、参考逐字稿和内部参数。

完整操作见 [`docs/voice-assets-workflow.md`](../../docs/voice-assets-workflow.md)。
