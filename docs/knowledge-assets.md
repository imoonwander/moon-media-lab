# Media Knowledge Asset Protocol v0.1

`moon-media-lab` turns one online or local media source into a portable, evidence-linked knowledge bundle. A transcript is an intermediate artifact, not the final product.

## Four layers

| Layer | Purpose | Typical artifacts |
| --- | --- | --- |
| Source | Preserve evidence and media facts | `input.json`, `media.json`, raw segments, subtitles, normalized audio |
| Transcript | Produce readable and attributable text | source transcript, clean transcript, speaker notes, polished English transcript |
| Knowledge | Extract reusable semantics | summary, concepts, claims, evidence, entities, relations, recommendations |
| Derivative | Create views and downstream material | information diagrams, Skill drafts, Wiki exports, article/video briefs |

Run:

```bash
moon-media process jobs/<job> --clean
moon-media process jobs/<job> --mode speaker-notes
moon-media process jobs/<job> --mode english-transcript
moon-media process jobs/<job> --mode structured-knowledge
moon-media process jobs/<job> --mode recommendations
moon-media package jobs/<job>
moon-media export wiki jobs/<job>
```

Each LLM-derived artifact is recorded in `postproc/provenance.json`. The bundle command writes `knowledge-bundle.manifest.json` with artifact layer, path, media type, byte size and SHA-256.

## Structured knowledge

`knowledge.structured.json` has these stable top-level collections:

- `concepts`: definitions tied to timestamps.
- `claims`: speaker-attributed propositions with confidence.
- `evidence`: examples, data, experience, citations or reasoning supporting a claim.
- `entities`: people, organizations, products, places and works.
- `relations`: evidence-linked semantic edges.
- `openQuestions`: gaps the source does not answer.

The source transcript remains authoritative. Structured output is a candidate asset until reviewed.

## Recommendation safety

Every recommendation must state its reason, timestamps, audience, conditions, risks, confidence and whether it was source-stated or model-inferred. Model inference is never presented as the speaker's opinion.

## Wiki export

The first export is vendor-neutral Markdown + JSON. It works as a local vault and as input to future Lark, Notion or static-site adapters. SQLite and embeddings are deliberately deferred; files and manifests remain the source of truth.

## Rights defaults

Bundles default to private with `sourceRightsReviewed=false` and `publicReleaseConfirmed=false`. Exporting a Wiki bundle does not grant permission to publish the source transcript, screenshots or clips.

