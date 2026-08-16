"""
Answer key for the 8-question evaluation set (Week 3, Task Set A, STEP 5).

IMPORTANT: this file was written by reading the 6 articles only. No retrieval
or search code had been run yet when these entries were authored. The
`correct_article_id` / `correct_section` fields are the ground truth this
script is graded against later — do not edit them after seeing search
results.

requires_table=True means the question can only be fully answered from a
specific row inside a troubleshooting table (error_code identifies the row).
"""

QUESTIONS = [
    {
        "id": "Q1",
        "question": "What does ERR-4032 mean and what's the fix?",
        "correct_article_id": "HC-BIL-102",
        "correct_section": "Error Code Reference",
        "requires_table": True,
        "error_code": "ERR-4032",
    },
    {
        "id": "Q2",
        "question": "What causes ERR-5107 and how do I resolve it?",
        "correct_article_id": "HC-PAY-201",
        "correct_section": "Payment Sync Error Codes",
        "requires_table": True,
        "error_code": "ERR-5107",
    },
    {
        "id": "Q3",
        "question": "What does error code ERR-6210 indicate and what is the fix?",
        "correct_article_id": "HC-ACC-301",
        "correct_section": "Account Sync Error Codes",
        "requires_table": True,
        "error_code": "ERR-6210",
    },
    {
        "id": "Q4",
        "question": "What causes sync errors after the billing migration?",
        "correct_article_id": "HC-PAY-201",
        "correct_section": "Why Syncs Fail During Migration",
        "requires_table": False,
        "error_code": None,
        "note": "Deliberately ambiguous: HC-ACC-301 (account) covers a "
        "topically overlapping 'sync error' concept. Used as the "
        "metadata-filter demo query in STEP 7.",
    },
    {
        "id": "Q5",
        "question": "What should account admins expect regarding billing "
        "permission roles after the migration cutover?",
        "correct_article_id": "HC-ACC-302",
        "correct_section": "Overview",
        "requires_table": False,
        "error_code": None,
    },
    {
        "id": "Q6",
        "question": "What is the overall timeline for the billing system migration?",
        "correct_article_id": "HC-BIL-101",
        "correct_section": "Timeline",
        "requires_table": False,
        "error_code": None,
    },
    {
        "id": "Q7",
        "question": "What should users do to prepare before their billing "
        "migration cutover?",
        "correct_article_id": "HC-BIL-101",
        "correct_section": "What You Need To Do",
        "requires_table": False,
        "error_code": None,
    },
    {
        "id": "Q8",
        "question": "What causes ERR-8021 and how is it fixed?",
        "correct_article_id": "HC-ACC-302",
        "correct_section": "Permission Error Codes",
        "requires_table": True,
        "error_code": "ERR-8021",
    },
]

# 3 answerable questions to run through generation (STEP 8) — a mix of
# table-dependent and prose-dependent, picked from QUESTIONS above. Q6 is
# deliberately excluded here: it is used in the bonus section (STEP 9)
# instead, where naive answers it but structure_aware refuses -- see
# results.md section 8/9 for why.
GENERATION_ANSWERABLE_IDS = ["Q1", "Q3", "Q5"]

# 3 deliberately out-of-corpus questions — nothing in any of the 6 articles
# answers these. Must be refused by generate_answer(), not guessed.
OUT_OF_CORPUS_QUESTIONS = [
    "What is the refund SLA for billing disputes?",
    "Do you support multi-currency invoicing after the migration?",
    "What is the phone number for urgent billing support?",
]
