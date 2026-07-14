# Knowledge Visualization Workflow

这一步把已经完成的 `knowledge.md` 转成一张可发布、可复用的信息结构图。

```text
transcript
  → knowledge.md
  → diagram brief
  → Codex image_gen / gpt-image-2
  → visual QA
  → visuals/*.png + provenance.json
```

## 边界

- `moon-media-lab` 负责知识文档、图稿 brief、文件命名和 provenance。
- 图片由 Codex 内置 `image_gen`（gpt-image-2）生成，不伪装成本地
  `moon-media` 命令，也不要求项目保存 OpenAI API key。
- 如果当前 agent 没有内置图像生成能力，停在 diagram brief，不用占位图冒充产物。
- 信息结构图只使用 `knowledge.md` 中已经确认的结论；不从原视频臆造新数据。

## 输入与输出契约

输入：

```text
jobs/<job-id>/knowledge.md
jobs/<job-id>/transcript.clean.md   # 可选，用于核对术语
```

输出：

```text
jobs/<job-id>/visuals/
  diagram-brief.md
  knowledge-structure-gpt-image2-v1.png
  knowledge-structure-gpt-image2-v1.provenance.json
```

同一知识内容重新生成时增加 `v2`，不要覆盖已验收版本。

## 操作步骤

### 1. 提炼图稿 brief

从 `knowledge.md` 选出：

- 一个标题和一个副标题；
- 3-6 个一级结构；
- 一条 4-8 步的流程；
- 必须原样出现的短标签；
- 禁止出现的敏感信息、推测和额外文字。

尽量使用短标签。长段落应该留在知识文档里，不塞进图中。

### 2. 用受控文本调用 gpt-image-2

在 Codex 中调用 `imagegen` skill / 内置 `image_gen`，使用
`infographic-diagram` 类型。Prompt 至少包含：

```text
Use case: infographic-diagram
Asset type: Chinese knowledge structure diagram
Primary request: 把指定知识结构绘制为清晰的信息图
Text (verbatim): <所有允许出现的文字>
Constraints: 所有文字必须原样；不得添加额外标签或伪文字
Avoid: 小字、长段落、随机字符、无法验证的数据、装饰性 3D 场景
```

### 3. 将图片复制进 job

Codex 内置工具默认把图片保存到 `$CODEX_HOME/generated_images/`。项目需要使用的
最终版本必须复制到 `jobs/<job-id>/visuals/`，不能只引用 Codex 缓存路径。

### 4. 视觉与事实 QC

逐项检查：

- 图中标题、中文、英文缩写与箭头顺序完全正确；
- 所有节点都能在 `knowledge.md` 找到依据；
- 没有把 ASR 低置信度内容、私人路径或身份信息带入图片；
- 结构层级一眼可辨，移动端缩小后主要标签仍可阅读；
- 没有水印、随机 glyph、额外口号或模型自行补充的数字；
- 图片尺寸、SHA-256、来源文档 SHA-256 已写入 provenance。

任何核心文字错误都必须重新生成；不要只在交付说明里口头纠正。

## Provenance 最小字段

```json
{
  "generator": "codex-built-in-image_gen",
  "model": "gpt-image-2",
  "source": "../knowledge.md",
  "sourceSha256": "...",
  "imageSha256": "...",
  "width": 0,
  "height": 0,
  "promptFile": "diagram-brief.md",
  "qa": {
    "textChecked": true,
    "structureChecked": true,
    "privacyChecked": true
  }
}
```

## 完成标准

只有以下文件同时存在，且人工完成文字/结构检查，workflow 才算完成：

1. `knowledge.md`
2. `visuals/diagram-brief.md`
3. `visuals/knowledge-structure-gpt-image2-vN.png`
4. 对应的 `provenance.json`

