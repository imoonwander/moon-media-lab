from __future__ import annotations

SYSTEM = (
    "You are the post-processing step of a media transcription pipeline. "
    "You receive machine-transcribed text that may contain homophone errors, "
    "filler words, and missing punctuation. Always respond in the same "
    "language as the transcript content. Output plain Markdown only, "
    "no preamble and no code fences around the whole document."
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
}
