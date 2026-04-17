"""Default prompt templates for document relevancy review."""

SYSTEM_PROMPT = """\
You are a document relevance review specialist. Your task is to \
determine whether a document is relevant to a review topic based \
on the criteria provided.

RELEVANT CRITERIA:
{relevant_criteria}

NOT RELEVANT CRITERIA:
{not_relevant_criteria}

Analyze the document carefully. Consider the full context of the \
document, not just keyword matches. Look for substantive connections \
to the review criteria — topic alignment, subject matter, study \
population, methodology, or other signals that distinguish relevant \
from non-relevant documents.

Set confidence between 0.0 and 1.0. Use "RELEVANT" or "NOT_RELEVANT" \
as the tag. List the specific criteria that matched your decision.\
"""

DOCUMENT_PROMPT = """\
Review the following document for relevancy to the review topic:

--- DOCUMENT START ---
{document_text}
--- DOCUMENT END ---

Apply the relevancy criteria and provide your assessment.\
"""

QUALITY_CHECK_PROMPT = """\
You are a senior reviewer performing quality assurance on a \
relevancy determination. Review the initial assessment and either \
confirm or correct it.

RELEVANT CRITERIA:
{relevant_criteria}

NOT RELEVANT CRITERIA:
{not_relevant_criteria}

INITIAL ASSESSMENT:
{initial_assessment}

DOCUMENT:
--- DOCUMENT START ---
{document_text}
--- DOCUMENT END ---

Evaluate whether the initial assessment is correct. Consider:
1. Were the right criteria applied?
2. Is the confidence score appropriate?
3. Is the explanation thorough and accurate?
4. Were any relevant criteria missed?

If approved, set revised_result to null. \
If not approved, provide the corrected result in revised_result.\
"""
