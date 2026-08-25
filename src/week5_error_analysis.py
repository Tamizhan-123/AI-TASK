"""
Week 5 / Module 3 -- Error Analysis (Track A: Customer support tickets).

Collects traces from the SHIPPED pipeline (hybrid TF-IDF+BM25 retrieval,
structure_aware chunking, k=3 -- the same defaults api.py serves at
POST /ask with no overrides) over a fair random sample of ~20 questions,
and writes each one out as a complete, replayable trace.

Sampling discipline (the point of this script, not an afterthought):
  - QUESTION_POOL below has 39 candidate questions, written BEFORE running
    anything, spanning all 6 articles and a deliberate mix of phrasing
    styles a real support inbox would contain: exact error-code lookups,
    colloquial paraphrases, vague one-line tickets, a typo, a compound
    question, an ambiguous question, and out-of-corpus questions that
    should be refused.
  - SAMPLE_SIZE of them are then chosen with random.sample() under a fixed,
    recorded seed -- not hand-picked. That is what "fair sample, not
    cherry-picked" means in practice: the script never sees the pipeline's
    output before it decides which questions to run.

A "complete trace" here = the question, every retrieved chunk (article_id,
chunk_id, section, fused score, component scores, text), and the final
answer/refusal with its reason -- enough to replay the exact same request
later without re-deriving anything.

Run with:  python src/week5_error_analysis.py
Writes:    traces_week5.md
"""

import os
import random

from api import _for_confidence_gate
from generator import CONFIDENCE_THRESHOLD, generate_answer
from ingest import ingest_articles
from retriever import Retriever

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACES_PATH = os.path.join(PROJECT_ROOT, "traces_week5.md")

SEED = 20260822  # fixed so the sample is reproducible; not chosen post-hoc
SAMPLE_SIZE = 20
STRATEGY = "structure_aware"
MODE = "hybrid"
K = 3

QUESTION_POOL = [
    # -- HC-BIL-101 (migration timeline / what to do) --
    {"id": "T01", "q": "What is the overall timeline for the billing system migration?"},
    {"id": "T02", "q": "When does my account actually switch over to the new billing system?"},
    {"id": "T03", "q": "Is my subscription price going to change because of this migration?"},
    {"id": "T04", "q": "What should I do to get ready before my account migrates?"},
    {"id": "T05", "q": "Can support roll my account back if something breaks during cutover?"},
    {"id": "T06", "q": "How do I check what migration phase my account is currently in?"},
    {"id": "T32", "q": "What should I do before my account gets migrated?"},

    # -- HC-BIL-102 (invoice errors) --
    {"id": "T07", "q": "What does ERR-4032 mean and what's the fix?"},
    {"id": "T08", "q": "Customer's invoice shows ERR-4001, what should I tell them?"},
    {"id": "T09", "q": "What causes ERR-4044 and how do we resolve it?"},
    {"id": "T10", "q": "Why did my invoice come out with the wrong total after the migration?"},
    {"id": "T11", "q": "waht does ERR-4099 mean"},
    {"id": "T12", "q": "A customer has an invoice error code I don't recognize, what do I do?"},

    # -- HC-ACC-302 (billing permission roles) --
    {"id": "T13", "q": "Why can't I edit billing details anymore after the migration?"},
    {"id": "T14", "q": "What's the fix for ERR-8021?"},
    {"id": "T15", "q": "What causes ERR-8033?"},
    {"id": "T16", "q": "How can I personally fix a missing Billing Owner on my account?"},
    {"id": "T17", "q": "Is there overlap between account sync errors and billing permission changes?"},

    # -- HC-ACC-301 (account sync errors) --
    {"id": "T18", "q": "What causes ERR-6210 and what is the fix?"},
    {"id": "T19", "q": "What's ERR-6055 about?"},
    {"id": "T20", "q": "How do we resolve ERR-6233?"},
    {"id": "T21", "q": "My account has a sync error banner that won't go away, what's wrong?"},
    {"id": "T22", "q": "What causes sync errors after the billing migration?"},

    # -- HC-PAY-201 (payment sync errors) --
    {"id": "T23", "q": "What causes ERR-5107 and how do I resolve it?"},
    {"id": "T24", "q": "What's the deal with ERR-5040?"},
    {"id": "T25", "q": "What causes ERR-5112?"},
    {"id": "T26", "q": "Customer says their payment sync error won't clear, should I be worried?"},

    # -- HC-PAY-202 (webhooks) --
    {"id": "T27", "q": "What does ERR-7300 mean and how do we fix it?"},
    {"id": "T28", "q": "Why are we getting ERR-7311?"},
    {"id": "T29", "q": "What causes ERR-7325?"},
    {"id": "T30", "q": "Our webhooks stopped working right after the migration, why?"},

    # -- compound / cross-cutting --
    {"id": "T31", "q": "What should users do to prepare before their billing migration cutover, and also what is ERR-6210?"},

    # -- out-of-corpus (should refuse) --
    {"id": "T33", "q": "What is the refund SLA for billing disputes?"},
    {"id": "T34", "q": "Do you support multi-currency invoicing after the migration?"},
    {"id": "T35", "q": "How do I cancel my subscription entirely?"},
    {"id": "T36", "q": "What's the phone number for urgent billing support?"},
    {"id": "T37", "q": "Can I get a discount for the inconvenience caused by the migration?"},
    {"id": "T38", "q": "Does this migration affect how we handle GDPR data deletion requests?"},
    {"id": "T39", "q": "What does ERR-9999 mean and how do I fix it?"},
]


def run_trace(retriever, item):
    question = item["q"]
    results = retriever.search_hybrid(STRATEGY, question, k=K, product_area_filter=None)
    answer = generate_answer(question, _for_confidence_gate(results, MODE))
    return {
        "id": item["id"],
        "question": question,
        "retrieved": results,
        "answer": answer,
    }


def format_trace_md(trace):
    lines = []
    lines.append(f"### {trace['id']}. {trace['question']}")
    lines.append("")
    lines.append(f"mode={MODE} strategy={STRATEGY} k={K}")
    lines.append("")
    lines.append("Retrieved:")
    lines.append("```")
    if not trace["retrieved"]:
        lines.append("  (no results)")
    for rank, r in enumerate(trace["retrieved"], start=1):
        c = r["chunk"]
        snippet = " ".join(c["text"].split())[:140]
        comp = r.get("component_scores", {})
        lines.append(
            f"  {rank}. score={r['score']:.4f}  article_id={c['article_id']}  "
            f"chunk_id={c['chunk_id']}  section={c['section']!r}  components={comp}"
        )
        lines.append(f"     text: {snippet!r}")
    lines.append("```")
    lines.append("")
    a = trace["answer"]
    lines.append(f"refused: {a['refused']}")
    lines.append(f"answer: {a['answer']}")
    if a.get("reason"):
        lines.append(f"reason: {a['reason']}")
    lines.append(f"citations: {a.get('citations')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    records, failures = ingest_articles()
    if failures:
        raise RuntimeError(f"Ingest reported {len(failures)} failure(s)")
    retriever = Retriever(records)

    pool_ids = [item["id"] for item in QUESTION_POOL]
    assert len(pool_ids) == len(set(pool_ids)), "duplicate ids in pool"

    rng = random.Random(SEED)
    sample = rng.sample(QUESTION_POOL, SAMPLE_SIZE)
    sampled_ids = [s["id"] for s in sample]

    out = []
    out.append("# Week 5 -- Complete Traces (Track A: Customer Support Tickets)")
    out.append("")
    out.append(
        f"Pool size: {len(QUESTION_POOL)} candidate questions, written before any "
        f"pipeline run. Sampled {SAMPLE_SIZE} of them with `random.Random({SEED}).sample()` "
        f"-- a fixed, recorded seed, not a hand pick after seeing results."
    )
    out.append("")
    out.append(f"Sampled IDs: {', '.join(sampled_ids)}")
    out.append("")
    out.append(f"Not sampled this round: {', '.join(i for i in pool_ids if i not in sampled_ids)}")
    out.append("")
    out.append(
        f"Pipeline: mode={MODE} (production default per api.py), strategy={STRATEGY}, "
        f"k={K}, confidence_threshold={CONFIDENCE_THRESHOLD}."
    )
    out.append("")
    out.append("---")
    out.append("")

    # Preserve pool order for readability, but the SET sampled is what matters.
    sample_by_id = {s["id"]: s for s in sample}
    for item in QUESTION_POOL:
        if item["id"] in sample_by_id:
            trace = run_trace(retriever, item)
            out.append(format_trace_md(trace))
            print(f"{item['id']}: refused={trace['answer']['refused']}  q={item['q']!r}")

    with open(TRACES_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")

    print(f"\nWrote {TRACES_PATH}")


if __name__ == "__main__":
    main()
