"""
Failing-question set for Week 4 / Task Set A (Debugging Retrieval).

Reuses two questions from the Week 3 answer key (answer_key.QUESTIONS) that
are already known to misbehave under the shipped structure_aware + TF-IDF
pipeline, plus two new questions written specifically to probe a bug this
week's inspection view surfaced: structure_aware_chunk (chunkers.py) strips
every markdown heading out of the chunk body and keeps it only as the
`section` metadata field, so a query built from heading vocabulary --
"escalation", "testing", "timeline", "migrated", "overlap" -- has zero
lexical overlap with any indexed chunk body, no matter which article it
belongs to.

Each entry's `known_failure` field records what STEP 1 (inspection +
labeling, before any fix) found by actually running the shipped pipeline --
not a prediction. See week4_debug_retrieval.py for how it was labeled.
"""

FAILING_QUESTIONS = [
    {
        "id": "Q4",
        "question": "What causes sync errors after the billing migration?",
        "correct_article_id": "HC-PAY-201",
        "correct_section": "Why Syncs Fail During Migration",
        "known_failure": "retrieval",
        "note": (
            "Deliberately ambiguous (see Week 3 results.md section 3): "
            "HC-ACC-301 (account) and HC-PAY-201 (payments) both use the "
            "phrase 'sync error' heavily. HC-ACC-301 chunks outscore the "
            "correct HC-PAY-201 chunk on raw term overlap alone."
        ),
    },
    {
        "id": "Q6",
        "question": "What is the overall timeline for the billing system migration?",
        "correct_article_id": "HC-BIL-101",
        "correct_section": "Timeline",
        "known_failure": "generation",
        "note": (
            "Retrieval already finds the correct HC-BIL-101 'Timeline' chunk "
            "in the top 3 (real, non-zero score) under the shipped pipeline. "
            "The chunk body is just 'The migration runs in four phases:' -- "
            "structure_aware_chunk moved the word 'Timeline' out of the body "
            "and into the section metadata, so generator._distinctive_coverage "
            "(which checks the chunk BODY for the question's distinctive "
            "words) finds none of them and refuses. Right document, wrong "
            "(refused) answer."
        ),
    },
    {
        "id": "N1",
        "question": "What should I do before my account gets migrated?",
        "correct_article_id": "HC-BIL-101",
        "correct_section": "What You Need To Do",
        "known_failure": "retrieval",
        "note": (
            "'account' is filtered out of the TF-IDF vocabulary entirely "
            "(max_df=0.5 -- it appears in over half of all chunks). "
            "'migrated' is out-of-vocabulary for the TF-IDF index because "
            "the only place that exact word appears in the whole corpus is "
            "inside a HEADING ('## Fixing a Role That Migrated "
            "Incorrectly', account-billing-permissions.md) -- text "
            "structure_aware_chunk strips out of every chunk body. Net "
            "result: the query vector has zero non-zero terms, so the "
            "TF-IDF cosine score is exactly 0.0 against every chunk in the "
            "corpus -- not a near-miss, a total miss."
        ),
    },
    {
        "id": "N2",
        "question": "Is there overlap between account sync errors and billing permission changes?",
        "correct_article_id": "HC-ACC-302",
        "correct_section": "Note on Overlap With Sync Errors",
        "known_failure": "retrieval",
        "note": (
            "HC-ACC-302 has a section literally titled 'Note on Overlap "
            "With Sync Errors' that answers this exactly -- but the heading "
            "word 'overlap' is stripped from the chunk body by "
            "structure_aware_chunk, and the surrounding body prose repeats "
            "far less of the query's vocabulary than HC-ACC-301's chunks "
            "do. HC-ACC-301 sweeps the entire top-3 on raw TF-IDF score; "
            "the correct HC-ACC-302 chunk sits at rank 4."
        ),
    },
]

# The rest of Week 3's 8-question answer key, included so the before/after
# hit-rate@3 number reported this week is measured against a set wide enough
# to also show hybrid search causes no regressions -- not just cherry-picked
# on the 4 questions we already know are broken.
CONTROL_QUESTION_IDS = ["Q1", "Q2", "Q3", "Q5", "Q7", "Q8"]
