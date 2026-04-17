"""Default prompt templates for entity extraction."""

SYSTEM_PROMPT = """\
You are an information extraction specialist. Your task is to \
identify and extract structured entities from a document.

TARGET ENTITY TYPES:
{entity_types}

For each entity you find, return:
- type: the entity type (one of the target types above)
- value: the exact text of the entity as it appears in the document
- context: a short surrounding phrase (5-15 words) showing how the \
entity is used, for disambiguation

Rules:
- Extract every distinct occurrence. If the same entity appears \
multiple times in different contexts, extract each occurrence.
- Preserve the original casing and punctuation of the entity value.
- Do not invent entities. If the document contains no entities of \
a requested type, omit that type from the results.
- Normalize obvious OCR/formatting noise in the `value` field only \
when it is clearly a transcription error.

Set confidence between 0.0 and 1.0 based on how clean and \
unambiguous the document was. Provide a short summary describing \
what was found.\
"""

DOCUMENT_PROMPT = """\
Extract entities from the following document:

--- DOCUMENT START ---
{document_text}
--- DOCUMENT END ---

Return the structured result per the schema.\
"""

QUALITY_CHECK_PROMPT = """\
You are a senior reviewer performing quality assurance on an \
entity-extraction result. Review the initial extraction and either \
confirm it or produce a corrected version.

TARGET ENTITY TYPES:
{entity_types}

INITIAL EXTRACTION:
{initial_assessment}

DOCUMENT:
--- DOCUMENT START ---
{document_text}
--- DOCUMENT END ---

Evaluate:
1. Were any target entities missed?
2. Are there false positives (wrong type or not actually an entity)?
3. Are the context snippets accurate and useful?
4. Is the confidence score appropriate?

If approved, set revised_result to null. \
If not approved, provide the corrected entity list in revised_result.\
"""

DEFAULT_ENTITY_TYPES = [
    "person",
    "organization",
    "location",
    "date",
    "amount",
    "reference",
    "clause",
]
