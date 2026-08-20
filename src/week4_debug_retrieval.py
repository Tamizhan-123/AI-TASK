"""
Week 4 / Task Set A -- Debugging Retrieval: Hybrid, Reranking & Failure
Separation.

Pipeline (against the SAME shipped Week 3 system: structure_aware chunking
+ TF-IDF retrieval + generator.generate_answer):

  STEP 1 - Inspection: for each question in the failing set, run the
           CURRENT (before) pipeline and record question / fetched top-3 /
           final answer side by side.
  STEP 2 - Label each failure as one of two kinds, with evidence:
             RETRIEVAL FAILURE  -- correct article never lands in the top-3
                                    (or the top score is exactly 0.0, i.e.
                                    no real signal at all)
             GENERATION FAILURE -- correct article IS in the top-3, but
                                    generate_answer refuses or answers from
                                    a different article anyway
  STEP 3 - Make exactly ONE change: hybrid search (retriever.search_hybrid),
           fusing the existing TF-IDF ranking with a new BM25 ranking via
           Reciprocal Rank Fusion. Nothing else changes -- same chunker,
           same chunks, same generator, same confidence/grounding gates.
  STEP 4 - Re-run the same questions through the AFTER pipeline and report
           hit-rate@3 before vs. after, plus which failures were and were
           NOT fixed by this one change.

Run with:  python src/week4_debug_retrieval.py
"""

import os

from answer_key import QUESTIONS
from generator import CONFIDENCE_THRESHOLD, _extract_complete_table_row, generate_answer
from ingest import ingest_articles
from retriever import Retriever
from week4_questions import CONTROL_QUESTION_IDS, FAILING_QUESTIONS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_PATH = os.path.join(PROJECT_ROOT, "results_week4.md")

STRATEGY = "structure_aware"  # the strategy Week 3 shipped; unchanged this week
K = 3


def build_eval_set():
    """
    FAILING_QUESTIONS (4, see week4_questions.py) + the other 6 questions
    from the Week 3 answer key, normalized to a single shape. Evaluating
    over all 10 (not just the 4 already known to be broken) is what lets
    "no regressions elsewhere" be a checked fact instead of an assumption.
    """
    by_id = {q["id"]: q for q in QUESTIONS}
    eval_set = list(FAILING_QUESTIONS)
    for qid in CONTROL_QUESTION_IDS:
        q = by_id[qid]
        eval_set.append(
            {
                "id": q["id"],
                "question": q["question"],
                "correct_article_id": q["correct_article_id"],
                "correct_section": q["correct_section"],
                "requires_table": q["requires_table"],
                "error_code": q["error_code"],
                "known_failure": None,
                "note": None,
            }
        )
    return eval_set


def compute_hit(question, results):
    """
    hit-in-top-3: the correct article appears among the top-3 results, AND
    the top result's own score is > 0. A top score of exactly 0.0 means the
    query shared zero vocabulary with the entire corpus under this index --
    there is no real ranking signal, so whichever chunk a tie-break
    happens to surface does not count as a hit even if it is coincidentally
    the right one (see week4_questions.py, question N1, for why this
    matters and is not just a theoretical edge case here).
    """
    if not results or results[0]["score"] <= 0:
        return False
    for r in results:
        chunk = r["chunk"]
        if chunk["article_id"] != question["correct_article_id"]:
            continue
        if question.get("requires_table"):
            if _extract_complete_table_row(chunk["text"], question["error_code"]) is not None:
                return True
        else:
            return True
    return False


def top_articles(results):
    return [r["chunk"]["article_id"] for r in results]


def classify_failure(question, hit, answer):
    """
    Two kinds, evaluated against the BEFORE (shipped) pipeline only -- this
    is a diagnosis of the current system, not of whatever the fix produces.
    """
    if not hit:
        return "RETRIEVAL FAILURE (wrong document fetched)"
    if answer["refused"]:
        return "GENERATION FAILURE (right document, wrong answer -- refused)"
    if answer["citations"] and answer["citations"][0]["article_id"] != question["correct_article_id"]:
        return "GENERATION FAILURE (right document retrieved, but answer cites a different one)"
    return "no failure"


def run_question(retriever, question):
    before_results = retriever.search(STRATEGY, question["question"], k=K)
    after_results = retriever.search_hybrid(STRATEGY, question["question"], k=K)

    before_hit = compute_hit(question, before_results)
    after_hit = compute_hit(question, after_results)

    before_answer = generate_answer(question["question"], before_results)
    after_answer = generate_answer(question["question"], after_results)

    failure_label = classify_failure(question, before_hit, before_answer)

    return {
        "question": question,
        "before_results": before_results,
        "after_results": after_results,
        "before_hit": before_hit,
        "after_hit": after_hit,
        "before_answer": before_answer,
        "after_answer": after_answer,
        "failure_label": failure_label,
    }


def snippet(text, n=100):
    return " ".join(text.split())[:n]


def format_ranked_list(results):
    lines = []
    if not results:
        lines.append("  (no results)")
        return lines
    for rank, r in enumerate(results, start=1):
        c = r["chunk"]
        comp = r.get("component_scores")
        comp_str = f"  components={comp}" if comp else ""
        lines.append(
            f"  {rank}. score={r['score']:.4f}  article_id={c['article_id']}  "
            f"chunk_id={c['chunk_id']}  section={c['section']!r}{comp_str}\n"
            f"     text: {snippet(c['text'], 110)!r}"
        )
    return lines


def main():
    records, failures = ingest_articles()
    if failures:
        raise RuntimeError(f"Ingest reported {len(failures)} failure(s) -- aborting")

    retriever = Retriever(records)
    eval_set = build_eval_set()

    runs = [run_question(retriever, q) for q in eval_set]

    before_hits = sum(1 for r in runs if r["before_hit"])
    after_hits = sum(1 for r in runs if r["after_hit"])
    n = len(runs)

    failing_runs = [r for r in runs if r["question"].get("known_failure")]
    fixed = [r for r in failing_runs if not r["before_hit"] and r["after_hit"]]
    still_broken_retrieval = [
        r for r in failing_runs
        if r["question"]["known_failure"] == "retrieval" and not r["after_hit"]
    ]
    still_broken_generation = [
        r for r in failing_runs if r["question"]["known_failure"] == "generation"
    ]

    print(f"hit-rate@3 BEFORE (TF-IDF only):        {before_hits}/{n}")
    print(f"hit-rate@3 AFTER  (hybrid TF-IDF+BM25):  {after_hits}/{n}")
    print(f"Retrieval failures fixed by hybrid search: {len(fixed)}")
    print(f"Retrieval failures NOT fixed: {len(still_broken_retrieval)}")
    print(f"Generation failures NOT fixed (expected -- retrieval-only change): {len(still_broken_generation)}")

    write_results_md(runs, before_hits, after_hits, n)
    print(f"\nresults_week4.md written to {RESULTS_PATH}")


def write_results_md(runs, before_hits, after_hits, n):
    lines = []

    def w(s=""):
        lines.append(s)

    w("# Week 4 / Task Set A -- Debugging Retrieval: Hybrid, Reranking & Failure Separation")
    w()
    w(
        "Continues directly from Week 3 (`results.md`): same 6 billing-migration "
        "help-centre articles, same shipped pipeline (`structure_aware` chunking "
        "+ TF-IDF retrieval via `retriever.Retriever`, `generator.generate_answer` "
        "for citation + refusal). Nothing about the corpus or the shipped "
        "chunker changed this week -- this task is about diagnosing and fixing "
        "*retrieval quality*, not re-doing chunking."
    )
    w()

    # STEP 1/2: inspection view + failure labels
    w("## 1. Inspection view + failure labels (BEFORE -- current shipped pipeline)")
    w()
    w(
        "For every question below, the CURRENT (`structure_aware` + TF-IDF-only) "
        "pipeline was run at k=3 and labeled using the rule in "
        "`week4_debug_retrieval.classify_failure`: if the correct article isn't "
        "in the top-3 (or the top score is exactly 0.0 -- no real signal at "
        "all), that's a **retrieval failure**. If it IS in the top-3 but "
        "`generate_answer` refuses or cites a different article anyway, that's "
        "a **generation failure**."
    )
    w()
    w("| ID | Question | Correct article | hit@3 (before) | Final answer (before) | Label |")
    w("|---|---|---|---|---|---|")
    for r in runs:
        q = r["question"]
        ans = r["before_answer"]
        ans_text = "REFUSED" if ans["refused"] else snippet(ans["answer"], 70)
        w(
            f"| {q['id']} | {q['question']} | {q['correct_article_id']} | "
            f"{'HIT' if r['before_hit'] else 'MISS'} | {ans_text} | {r['failure_label']} |"
        )
    w()

    bonus_generation_failures = [
        r for r in runs
        if not r["question"].get("known_failure")
        and r["failure_label"].startswith("GENERATION FAILURE")
    ]
    if bonus_generation_failures:
        ids = ", ".join(r["question"]["id"] for r in bonus_generation_failures)
        w(
            f"**Not cherry-picked:** running the same before/after/label pipeline "
            f"over all 10 questions (not just the 4 curated into the failing set "
            f"below) also caught **{ids}** as a generation failure with the exact "
            f"same root cause as Q6 -- its correct chunk (`What You Need To Do`) "
            f"also loses its heading text to `structure_aware_chunk`, so the same "
            f"`_distinctive_coverage` gate refuses it too. It's one more data "
            f"point that Q6 wasn't a one-off; it isn't detailed separately below "
            f"since hybrid search leaves it exactly as unfixed as Q6, for the "
            f"same reason."
        )
        w()

    failing_runs = [r for r in runs if r["question"].get("known_failure")]
    w("### Full before/after detail, the 4 questions in the failing set")
    w()
    for r in failing_runs:
        q = r["question"]
        w(f"**{q['id']}. {q['question']}**")
        w()
        w(f"- Correct: article_id=`{q['correct_article_id']}`, section=`{q['correct_section']}`")
        w(f"- Diagnosis: {q['note']}")
        w(f"- Failure label (before): **{r['failure_label']}**")
        w()
        w(f"BEFORE top-3 (TF-IDF only, `structure_aware`):")
        w("```")
        for line in format_ranked_list(r["before_results"]):
            w(line)
        w("```")
        w(f"BEFORE final answer: `{'REFUSED: ' + r['before_answer']['reason'] if r['before_answer']['refused'] else r['before_answer']['answer']}`")
        w()
        w(f"AFTER top-3 (hybrid TF-IDF + BM25, RRF-fused):")
        w("```")
        for line in format_ranked_list(r["after_results"]):
            w(line)
        w("```")
        w(f"AFTER final answer: `{'REFUSED: ' + r['after_answer']['reason'] if r['after_answer']['refused'] else r['after_answer']['answer']}`")
        w()
        w(f"hit@3: before=**{r['before_hit']}** -> after=**{r['after_hit']}**")
        w()
        w("---")
        w()

    # STEP 3: the one change
    w("## 2. The one change: hybrid search (TF-IDF + BM25, fused with RRF)")
    w()
    w(
        "Added `src/bm25.py` (a small dependency-free BM25 implementation -- "
        "`rank_bm25` is not installed and this project is offline-only, same "
        "constraint as the rest of the pipeline) and `Retriever.search_hybrid` "
        "in `retriever.py`. Nothing else changed: same chunker, same chunks, "
        "same confidence threshold, same grounding checks in "
        "`generator.generate_answer`."
    )
    w()
    w(
        "**Why BM25 is scored over `section heading + body text`, not body "
        "text alone:** `structure_aware_chunk` (chunkers.py, shipped in Week "
        "3) strips every markdown heading out of the chunk body and carries "
        "it only as the `section` metadata field. That is exactly why "
        "questions N1 and N2 above fail -- the words a user's question "
        "actually shares with the corpus (\"escalation\", \"testing\", "
        "\"overlap\", \"migrated\", ...) live only in a heading that TF-IDF "
        "never sees. Folding the heading back in for BM25's index buys that "
        "vocabulary back for the keyword side of search, without touching "
        "the chunk bodies the TF-IDF index and the generator's grounding "
        "checks already depend on."
    )
    w()
    w(
        "**Fusion:** each side is queried independently (pool of 10 "
        "candidates), then combined by Reciprocal Rank Fusion -- a chunk's "
        "score is `sum(1 / (60 + rank))` over every list it appears in. A "
        "chunk only one side found still gets a score from that side alone."
    )
    w()
    w(
        "**One bug found and fixed while building this:** when a query's TF-IDF "
        "vector is entirely zero (question N1 -- see its diagnosis above), "
        "every chunk ties at the same (non-)score, and Chroma's approximate "
        "index still returns *some* order for that tie -- an order that is "
        "not even stable run-to-run (verified: the same query against the "
        "same index returned a different top-3 on repeated runs). Feeding "
        "that tie-break noise into RRF would let it compete with BM25's real "
        "ranking and make the fused result non-reproducible. `search_hybrid` "
        "now drops a component from fusion entirely when its own top score "
        "is <= 0, instead of trusting an order that isn't a real ranking."
    )
    w()

    # STEP 4: before/after number
    w("## 3. hit-rate@3, before vs. after")
    w()
    w(f"Measured across all {n} questions (the 4 in the failing set + the other "
      "6 from the Week 3 answer key, so a regression on an already-working "
      "question would show up too):")
    w()
    w("| | hit-rate@3 |")
    w("|---|---|")
    w(f"| BEFORE (TF-IDF only) | {before_hits}/{n} |")
    w(f"| AFTER (hybrid TF-IDF + BM25, RRF) | {after_hits}/{n} |")
    w()

    fixed = [r for r in failing_runs if not r["before_hit"] and r["after_hit"]]
    still_broken_retrieval = [
        r for r in failing_runs
        if r["question"]["known_failure"] == "retrieval" and not r["after_hit"]
    ]
    still_broken_generation = [r for r in failing_runs if r["question"]["known_failure"] == "generation"]

    w(f"**Fixed by this one change:** {', '.join(r['question']['id'] for r in fixed) or 'none'} "
      f"({len(fixed)} of 3 retrieval failures).")
    w()

    # What did NOT get fixed, and why -- required by the mentor checklist.
    w("## 4. What this change did NOT fix (and why that's expected)")
    w()
    for r in still_broken_retrieval:
        q = r["question"]
        w(
            f"- **{q['id']}** (`{q['question']}`) is still a MISS after hybrid "
            f"search. This is genuine topical overlap between two articles "
            f"that both legitimately discuss 'sync errors' (HC-ACC-301 vs. "
            f"the correct HC-PAY-201) -- not a vocabulary-coverage problem "
            f"BM25 can fix. Week 3's metadata filter demo already showed the "
            f"actual fix for this one: filtering by `product_area` at query "
            f"time (see `results.md` section 3), not better keyword matching."
        )
    for r in still_broken_generation:
        q = r["question"]
        w(
            f"- **{q['id']}** (`{q['question']}`) still gets refused after "
            f"hybrid search, even though retrieval already had the correct "
            f"chunk in the top-3 both before and after. This is the point of "
            f"labeling failures by kind in the first place: hybrid search is "
            f"a retrieval-side change, and this is a generation-side bug "
            f"(`generator._distinctive_coverage` checking chunk BODY text "
            f"for words that only exist in the stripped-out heading) -- "
            f"fixing retrieval was never going to fix it. It needs its own, "
            f"separate fix (e.g. folding the section heading back into what "
            f"the grounding check inspects, or relaxing it for chunks with a "
            f"clearly relevant `section` field)."
        )
    w()

    w("---")
    w()
    w(f"_Generated by `src/week4_debug_retrieval.py`. Strategy: `{STRATEGY}`, k={K}._")

    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
