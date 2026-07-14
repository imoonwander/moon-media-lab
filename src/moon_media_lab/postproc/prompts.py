from __future__ import annotations

SYSTEM = (
    "You are the post-processing step of a media transcription pipeline. "
    "You receive machine-transcribed text that may contain homophone errors, "
    "filler words, and missing punctuation. Always respond in the same "
    "language as the transcript content. Output plain Markdown only, "
    "no preamble and no code fences around the whole document."
)

STRUCTURED_SYSTEM = (
    "You are the structured knowledge extraction step of a media transcription pipeline. "
    "Return one valid JSON object only. Do not use Markdown fences or add facts that are not "
    "grounded in the timestamped transcript."
)

KNOWLEDGE = """\
Below is a timestamped transcript. Produce a knowledge document with these sections
(use the transcript's language for all headings and content):

1. 摘要 / Summary — 5-10 sentences covering the core content.
2. 大纲 / Outline — bullet outline with the [hh:mm:ss] timestamp where each topic starts.
3. 知识卡片 / Knowledge cards — 3-8 cards; each card has a title, a 2-4 sentence
   explanation grounded in the transcript, and the source timestamp.
4. 金句 / Notable quotes — up to 5 direct quotes with timestamps (fix obvious
   transcription errors but keep the speaker's wording).
5. 待办与线索 / Follow-ups — open questions or action items mentioned, if any.

Transcript:

{transcript}
"""

ENGLISH_STUDY = """\
Below is a timestamped transcript of English learning material. Produce an English
study document with these sections:

1. Summary — what the material teaches, in simple English.
2. Key vocabulary — 10-20 items: word/phrase, meaning (bilingual if the learner
   context suggests it), and the sentence from the transcript where it appears.
3. Useful expressions — idioms, collocations, or sentence patterns worth reusing.
4. Grammar notes — 2-5 points observed in the material.
5. Practice — 5 short exercises (fill-in or translation) based on the material.

Transcript:

{transcript}
"""

SKILL_DRAFT = """\
Below is a timestamped transcript. Extract reusable know-how and produce a
Skill/SOP draft with these sections (use the transcript's language):

1. 目标 / Goal — what this skill accomplishes and when to use it.
2. 前置条件 / Prerequisites — tools, access, or knowledge required.
3. 步骤 / Steps — numbered, actionable steps distilled from the transcript;
   cite the source timestamp for each step.
4. 注意事项 / Pitfalls — mistakes or warnings mentioned.
5. 未覆盖问题 / Gaps — things the transcript does not explain that an operator
   would still need to figure out.

Transcript:

{transcript}
"""

SPEAKER_NOTES = """\
Below is a timestamped multi-speaker transcript. Produce a role-oriented transcript asset in
the transcript's language:

1. Speaker index — each observed speaker label/name, inferred role, and confidence.
2. Position by speaker — the speaker's main claims, with source timestamps.
3. Questions and answers — attribute each question and answer to a speaker.
4. Agreements and disagreements — show which speakers align or conflict, with timestamps.
5. Quote candidates — short attributable excerpts with timestamps.

Do not invent identities. If a real name is not supported, keep a neutral role label.

Transcript:

{transcript}
"""

ENGLISH_TRANSCRIPT = """\
Below is a timestamped English transcript. Produce a polished English transcript, not a summary:

- preserve every supported idea and the original order
- fix obvious recognition, punctuation, capitalization, and paragraph errors
- remove only filler and stutter that does not change meaning
- keep [hh:mm:ss] timestamps at each paragraph
- do not translate or add teaching notes

Transcript:

{transcript}
"""

STRUCTURED_KNOWLEDGE = """\
Convert the timestamped transcript into a strict JSON knowledge object. Respond with JSON only,
without Markdown fences. Use this exact top-level shape:

{{
  "summary": "...",
  "concepts": [{{"id":"concept-slug","name":"...","definition":"...","timestamps":["00:00:00"]}}],
  "claims": [{{"id":"claim-001","text":"...","speaker":"...","timestamps":["00:00:00"],"confidence":"high|medium|low"}}],
  "evidence": [{{"id":"evidence-001","claimId":"claim-001","text":"...","timestamps":["00:00:00"],"kind":"example|data|experience|citation|reasoning"}}],
  "entities": [{{"id":"entity-slug","name":"...","type":"person|organization|product|place|work|other","timestamps":["00:00:00"]}}],
  "relations": [{{"from":"concept-slug","to":"entity-slug","type":"mentions|supports|contradicts|depends-on|related-to","timestamps":["00:00:00"]}}],
  "openQuestions": [{{"text":"...","timestamps":["00:00:00"]}}]
}}

Every claim, evidence item, entity and relation must be grounded in the transcript and include a
source timestamp. Use empty arrays when the transcript does not support a field. Do not infer
external facts.

Transcript:

{transcript}
"""

RECOMMENDATIONS = """\
Produce an evidence-bound recommendation report from the timestamped transcript. Use the
transcript's language and these sections:

1. Scope — intended audience, objective, and what this report cannot decide.
2. Recommendations — for each item include recommendation, reason, source timestamps,
   applicable audience, conditions, risks, confidence (high/medium/low), and origin
   (source-stated or model-inferred).
3. Decision options — alternatives and trade-offs when the transcript supports them.
4. Content reuse — article, diagram, short-video, SOP, Wiki, or learning assets worth creating.
5. Verification needed — unsupported assumptions and facts that must be checked externally.

Never present model inference as the speaker's recommendation. A recommendation without source
evidence must be marked model-inferred and low confidence.

Transcript:

{transcript}
"""

CLEANUP = """\
Below is a fragment of a machine transcript. Clean it for reading:

- fix homophone/mis-recognition errors from context
- remove filler words and stutters
- add natural punctuation and paragraph breaks
- do NOT summarize, translate, reorder, or drop content
- output only the cleaned text, nothing else

Fragment:

{text}
"""

SPEAKER_NAMING = """\
Below are sample utterances from a diarized transcript, grouped by speaker label.
Infer who each speaker is from context: use a real name if it is mentioned or
strongly implied, otherwise a role (e.g. 主持人 / 嘉宾 / 记者 / interviewer).
Use the transcript's language for the names.

Respond with ONLY a JSON object mapping each label to a short name, e.g.
{{"SPEAKER_00": "主持人", "SPEAKER_01": "向佐"}}
No markdown fences, no explanations.

Samples:

{samples}
"""

MODE_PROMPTS = {
    "knowledge": KNOWLEDGE,
    "english-study": ENGLISH_STUDY,
    "skill": SKILL_DRAFT,
    "speaker-notes": SPEAKER_NOTES,
    "english-transcript": ENGLISH_TRANSCRIPT,
    "structured-knowledge": STRUCTURED_KNOWLEDGE,
    "recommendations": RECOMMENDATIONS,
}
