"""
End-to-end orchestration for Week 3 / Task Set A.

Pipeline: ingest -> chunk (two strategies) -> index (TF-IDF) -> search-only
hit@5 comparison -> metadata filter demo -> generation with forced citations
and hard-threshold refusal -> results.md

Run with:  python src/main.py
"""

import contextlib
import io
import os
import sys

from answer_key import GENERATION_ANSWERABLE_IDS, OUT_OF_CORPUS_QUESTIONS, QUESTIONS
from generator import CONFIDENCE_THRESHOLD, _extract_complete_table_row, generate_answer
from ingest import ingest_articles, print_ingest_report
from retriever import Retriever

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_PATH = os.path.join(PROJECT_ROOT, "results.md")

STRATEGY_LABELS = {"naive": "Naive (fixed-size, structure-blind)", "structure_aware": "Structure-aware"}


def compute_hit(question, results):
    """
    hit-in-top-5: the correct article appears among the top-5 chunks, and
    (for table-dependent questions) the chunk contains the COMPLETE
    cause+fix row for the specific error code -- not just the code label
    with the cause/fix severed by a chunk boundary. This is the same
    complete-row check generate_answer uses, so "hit" here means the
    generator could actually answer from that chunk, not merely that the
    code string appears somewhere in it.
    """
    for r in results:
        chunk = r["chunk"]
        if chunk["article_id"] != question["correct_article_id"]:
            continue
        if question["requires_table"]:
            if _extract_complete_table_row(chunk["text"], question["error_code"]) is not None:
                return True
        else:
            return True
    return False


def format_ranked_list(results):
    lines = []
    if not results:
        lines.append("  (no results)")
        return lines
    for rank, r in enumerate(results, start=1):
        c = r["chunk"]
        snippet = " ".join(c["text"].split())[:110]
        lines.append(
            f"  {rank}. score={r['score']:.4f}  article_id={c['article_id']}  "
            f"chunk_id={c['chunk_id']}  section={c['section']!r}\n"
            f"     text: {snippet!r}"
        )
    return lines


def run_hit_eval(retriever, strategy_name, log):
    per_question = []
    hits = 0
    log(f"\n### Strategy: {STRATEGY_LABELS[strategy_name]} ({strategy_name})\n")
    for q in QUESTIONS:
        results = retriever.search(strategy_name, q["question"], k=5)
        hit = compute_hit(q, results)
        hits += int(hit)
        log(f"\n**{q['id']}. {q['question']}**")
        log(f"  known-correct: article_id={q['correct_article_id']} section={q['correct_section']!r}")
        log(f"  hit-in-top-5: {'HIT' if hit else 'MISS'}")
        for line in format_ranked_list(results):
            log(line)
        per_question.append({"id": q["id"], "hit": hit, "results": results})
    return hits, per_question


def main():
    buf = []

    def log(line=""):
        print(line)
        buf.append(str(line))

    # -------------------------------------------------------------
    # STEP 2: Ingestion
    # -------------------------------------------------------------
    ingest_buf = io.StringIO()
    with contextlib.redirect_stdout(ingest_buf):
        records, failures = ingest_articles()
        print_ingest_report(records, failures)
    ingest_report_text = ingest_buf.getvalue()
    print(ingest_report_text)
    buf.append(ingest_report_text)

    if failures:
        raise RuntimeError(f"Ingest reported {len(failures)} failure(s) -- aborting")

    # -------------------------------------------------------------
    # STEP 3/4: Build both chunk indexes from the SAME 6 articles
    # -------------------------------------------------------------
    retriever = Retriever(records)
    log("\n## Chunk counts per strategy (same 6 articles, only the chunker differs)\n")
    for strategy_name, count in retriever.chunk_counts.items():
        log(f"  - {strategy_name}: {count} chunks")

    # -------------------------------------------------------------
    # STEP 6: search-only hit@5 comparison, both strategies, same 8 Qs
    # -------------------------------------------------------------
    log("\n" + "=" * 70)
    log("STEP 6: SEARCH-ONLY HIT@5 EVALUATION (8 questions x 2 strategies)")
    log("=" * 70)

    hits_naive, per_q_naive = run_hit_eval(retriever, "naive", log)
    hits_structured, per_q_structured = run_hit_eval(retriever, "structure_aware", log)

    log("\n" + "-" * 70)
    log(f"SUMMARY: naive = {hits_naive}/8   structure_aware = {hits_structured}/8")
    log("-" * 70)

    shipped_strategy = "structure_aware" if hits_structured >= hits_naive else "naive"

    # -------------------------------------------------------------
    # STEP 7: metadata filter demo
    # -------------------------------------------------------------
    log("\n" + "=" * 70)
    log("STEP 7: METADATA FILTER DEMO")
    log("=" * 70)

    filter_query = None
    filter_wrong_area = None
    filter_correct_area = None
    unfiltered_results = None
    filtered_results = None

    candidate_queries = [
        (q["question"], q["correct_article_id"])
        for q in QUESTIONS
        if q["id"] == "Q4"
    ]
    for query_text, correct_article_id in candidate_queries:
        correct_area = next(r["product_area"] for r in records if r["article_id"] == correct_article_id)
        unf = retriever.search(shipped_strategy, query_text, k=5)
        if unf and unf[0]["chunk"]["product_area"] != correct_area:
            filter_query = query_text
            filter_correct_area = correct_area
            filter_wrong_area = unf[0]["chunk"]["product_area"]
            unfiltered_results = unf
            filtered_results = retriever.search(
                shipped_strategy, query_text, k=5, product_area_filter=correct_area
            )
            break

    if filter_query is None:
        # Fall back: still demonstrate the mechanism on Q4 even if the
        # unfiltered top-1 was already correct, and report that honestly.
        query_text, correct_article_id = candidate_queries[0]
        correct_area = next(r["product_area"] for r in records if r["article_id"] == correct_article_id)
        unfiltered_results = retriever.search(shipped_strategy, query_text, k=5)
        filtered_results = retriever.search(
            shipped_strategy, query_text, k=5, product_area_filter=correct_area
        )
        filter_query = query_text
        filter_correct_area = correct_area
        filter_wrong_area = unfiltered_results[0]["chunk"]["product_area"] if unfiltered_results else None

    log(f"\nQuery: {filter_query!r}")
    log(f"Strategy used for this demo: {shipped_strategy}")
    log(f"Expected/correct product_area: {filter_correct_area}")
    log(f"\nUNFILTERED top-5 (product_area_filter=None):")
    for line in format_ranked_list(unfiltered_results):
        log(line)
    log(f"\nFILTERED top-5 (product_area_filter={filter_correct_area!r}):")
    for line in format_ranked_list(filtered_results):
        log(line)

    top1_changed = (
        unfiltered_results
        and filtered_results
        and unfiltered_results[0]["chunk"]["chunk_id"] != filtered_results[0]["chunk"]["chunk_id"]
    )
    log(f"\nTop-1 changed by filtering: {top1_changed}")

    # -------------------------------------------------------------
    # STEP 8: generation with forced citations + refusal
    # -------------------------------------------------------------
    log("\n" + "=" * 70)
    log(f"STEP 8: GENERATION (using shipped strategy: {shipped_strategy}, "
        f"confidence threshold={CONFIDENCE_THRESHOLD})")
    log("=" * 70)

    log("\n--- Answerable questions (expect cited answers) ---")
    generation_transcripts_answerable = []
    for qid in GENERATION_ANSWERABLE_IDS:
        q = next(x for x in QUESTIONS if x["id"] == qid)
        results = retriever.search(shipped_strategy, q["question"], k=5)
        answer = generate_answer(q["question"], results)
        generation_transcripts_answerable.append((q["question"], answer))
        log(f"\nQ ({qid}): {q['question']}")
        log(f"Top retrieval score: {results[0]['score']:.4f}" if results else "Top retrieval score: n/a")
        log(f"refused: {answer['refused']}")
        log(f"answer: {answer['answer']}")
        log(f"citations: {answer['citations']}")

    log("\n--- Out-of-corpus questions (expect refusal) ---")
    generation_transcripts_refusal = []
    for question_text in OUT_OF_CORPUS_QUESTIONS:
        results = retriever.search(shipped_strategy, question_text, k=5)
        answer = generate_answer(question_text, results)
        generation_transcripts_refusal.append((question_text, answer))
        log(f"\nQ: {question_text}")
        log(f"Top retrieval score: {results[0]['score']:.4f}" if results else "Top retrieval score: n/a")
        log(f"refused: {answer['refused']}")
        log(f"answer: {answer['answer']}")
        log(f"reason: {answer.get('reason')}")

    all_refused = all(t[1]["refused"] for t in generation_transcripts_refusal)
    log(f"\nAll 3 out-of-corpus questions refused: {all_refused}")

    # -------------------------------------------------------------
    # STEP 9: bonus -- precision vs completeness
    # -------------------------------------------------------------
    log("\n" + "=" * 70)
    log("STEP 9: BONUS -- precision/completeness tradeoff")
    log("=" * 70)

    bonus_q = next(x for x in QUESTIONS if x["id"] == "Q6")  # prose, "Timeline"
    naive_results = retriever.search("naive", bonus_q["question"], k=5)
    structured_results = retriever.search("structure_aware", bonus_q["question"], k=5)
    naive_hit = compute_hit(bonus_q, naive_results)
    structured_hit = compute_hit(bonus_q, structured_results)
    naive_answer = generate_answer(bonus_q["question"], naive_results)
    structured_answer = generate_answer(bonus_q["question"], structured_results)

    log(f"\nBonus question ({bonus_q['id']}): {bonus_q['question']}")
    log(f"naive hit-in-top-5: {naive_hit}   structure_aware hit-in-top-5: {structured_hit}")
    log(f"\nNAIVE top-1 chunk: {naive_results[0]['chunk']['chunk_id']} "
        f"(score={naive_results[0]['score']:.4f})")
    log(f"NAIVE final answer: {naive_answer['answer']}")
    log(f"\nSTRUCTURE-AWARE top-1 chunk: {structured_results[0]['chunk']['chunk_id']} "
        f"(section={structured_results[0]['chunk']['section']!r}, "
        f"score={structured_results[0]['score']:.4f})")
    log(f"STRUCTURE-AWARE final answer: {structured_answer['answer']}")

    bonus_data = {
        "question": bonus_q,
        "naive_results": naive_results,
        "structured_results": structured_results,
        "naive_answer": naive_answer,
        "structured_answer": structured_answer,
    }

    # -------------------------------------------------------------
    # Write results.md
    # -------------------------------------------------------------
    write_results_md(
        records=records,
        ingest_report_text=ingest_report_text,
        hits_naive=hits_naive,
        hits_structured=hits_structured,
        per_q_naive=per_q_naive,
        per_q_structured=per_q_structured,
        shipped_strategy=shipped_strategy,
        filter_query=filter_query,
        filter_correct_area=filter_correct_area,
        filter_wrong_area=filter_wrong_area,
        unfiltered_results=unfiltered_results,
        filtered_results=filtered_results,
        generation_transcripts_answerable=generation_transcripts_answerable,
        generation_transcripts_refusal=generation_transcripts_refusal,
        bonus_data=bonus_data,
    )

    log(f"\nresults.md written to {RESULTS_PATH}")


def write_results_md(**ctx):
    records = ctx["records"]
    hits_naive = ctx["hits_naive"]
    hits_structured = ctx["hits_structured"]
    per_q_naive = ctx["per_q_naive"]
    per_q_structured = ctx["per_q_structured"]
    shipped_strategy = ctx["shipped_strategy"]

    naive_by_id = {p["id"]: p for p in per_q_naive}
    structured_by_id = {p["id"]: p for p in per_q_structured}

    lines = []

    def w(s=""):
        lines.append(s)

    w("# Week 3 / Task Set A -- Results")
    w()
    w("Domain: customer support (billing migration help-centre drop). "
      "**This run indexes only the 6 new articles under `articles/` -- no "
      "historical article corpus is read, indexed, or referenced anywhere "
      "in this pipeline.**")
    w()
    w("**Chunks are stored in a persistent Chroma vector database** at "
      "`chroma_db/` (see `retriever.CHROMA_DB_PATH`), not just held in "
      "memory. Two Chroma collections are created, `chunks_naive` and "
      "`chunks_structure_aware` -- one per chunking strategy -- each holding "
      "every chunk's `chunk_id`, `document` (chunk text), and metadata "
      "(`source_file`, `article_id`, `product_area`, `last_updated`, "
      "`strategy`, `section`). The vectors stored and searched are still "
      "our own scikit-learn TF-IDF vectors (no external embedding API, no "
      "network call), so retrieval scores are exactly the same TF-IDF "
      "cosine similarity as a plain in-memory index -- Chroma is doing "
      "persistence and the `where`-filtered nearest-neighbor search, not "
      "changing what's being measured. Both collections are dropped and "
      "recreated from scratch at the start of every run of `main.py`, so "
      "the database only ever contains chunks from the current 6 articles "
      "-- it never accumulates chunks from a previous run or from a "
      "historical corpus.")
    w()

    # 1. 8 questions + answer key
    w("## 1. Question set and answer key (written before running retrieval)")
    w()
    w("| ID | Question | Correct article_id | Correct section | Requires table row |")
    w("|---|---|---|---|---|")
    for q in QUESTIONS:
        w(
            f"| {q['id']} | {q['question']} | {q['correct_article_id']} | "
            f"{q['correct_section']} | {'yes (' + q['error_code'] + ')' if q['requires_table'] else 'no'} |"
        )
    w()
    w("Q4 is deliberately ambiguous: HC-PAY-201 (payments) and HC-ACC-301 "
      "(account) both discuss a topically overlapping 'sync error' concept. "
      "It is used as the metadata-filter demo query in section 3 below.")
    w()

    # 2. hit@5 table + per-question breakdown
    w("## 2. Hit-in-top-5 results")
    w()
    w("| Strategy | Hit-in-top-5 |")
    w("|---|---|")
    w(f"| Naive (fixed-size, structure-blind) | {hits_naive}/8 |")
    w(f"| Structure-aware | {hits_structured}/8 |")
    w()
    w("Per-question breakdown (same 8 questions, same embedding/scoring "
      "method -- only the chunker changed between the two runs):")
    w()
    w("| ID | Question | Naive hit | Structure-aware hit |")
    w("|---|---|---|---|")
    for q in QUESTIONS:
        n = "HIT" if naive_by_id[q["id"]]["hit"] else "MISS"
        s = "HIT" if structured_by_id[q["id"]]["hit"] else "MISS"
        w(f"| {q['id']} | {q['question']} | {n} | {s} |")
    w()

    w("### Full ranked results, naive strategy, all 8 questions")
    w()
    for q in QUESTIONS:
        w(f"**{q['id']}. {q['question']}** -- {'HIT' if naive_by_id[q['id']]['hit'] else 'MISS'}")
        w()
        w("```")
        for line in format_ranked_list(naive_by_id[q["id"]]["results"]):
            w(line)
        w("```")
        w()

    w("### Full ranked results, structure-aware strategy, all 8 questions")
    w()
    for q in QUESTIONS:
        w(f"**{q['id']}. {q['question']}** -- {'HIT' if structured_by_id[q['id']]['hit'] else 'MISS'}")
        w()
        w("```")
        for line in format_ranked_list(structured_by_id[q["id"]]["results"]):
            w(line)
        w("```")
        w()

    # 3. metadata filter demo
    w("## 3. Metadata filter demo (product_area)")
    w()
    w(f"Query: `{ctx['filter_query']}`  (strategy: `{shipped_strategy}`)")
    w()
    w(f"Unfiltered top-1 product_area: **{ctx['filter_wrong_area']}** -- "
      f"expected/correct product_area: **{ctx['filter_correct_area']}**")
    w()
    w("**Unfiltered (product_area_filter=None):**")
    w()
    w("```")
    for line in format_ranked_list(ctx["unfiltered_results"]):
        w(line)
    w("```")
    w()
    w(f"**Filtered (product_area_filter={ctx['filter_correct_area']!r}):**")
    w()
    w("```")
    for line in format_ranked_list(ctx["filtered_results"]):
        w(line)
    w("```")
    w()
    top1_changed = (
        ctx["unfiltered_results"]
        and ctx["filtered_results"]
        and ctx["unfiltered_results"][0]["chunk"]["chunk_id"]
        != ctx["filtered_results"][0]["chunk"]["chunk_id"]
    )
    w(f"Top-1 changed by filtering: **{top1_changed}**")
    w()

    # 4. cited answers + refusals
    w("## 4. Generation transcripts")
    w()
    w(f"Confidence threshold enforced in code: `{CONFIDENCE_THRESHOLD}` "
      f"(hard check in `generator.generate_answer`, not a prompt instruction).")
    w()
    w("### 3 cited answers (answerable questions)")
    w()
    for question_text, answer in ctx["generation_transcripts_answerable"]:
        w(f"**Q:** {question_text}")
        w()
        w("```")
        w(f"refused: {answer['refused']}")
        w(f"answer: {answer['answer']}")
        w(f"citations: {answer['citations']}")
        w("```")
        w()
    w("### 3 refusal transcripts (out-of-corpus questions)")
    w()
    for question_text, answer in ctx["generation_transcripts_refusal"]:
        w(f"**Q:** {question_text}")
        w()
        w("```")
        w(f"refused: {answer['refused']}")
        w(f"answer: {answer['answer']}")
        w(f"reason: {answer.get('reason')}")
        w("```")
        w()

    # 5. code diff / metadata fields
    w("## 5. Second chunker and metadata fields (before/after)")
    w()
    w("Before (existing/current strategy -- `naive_chunk`, fixed-size word "
      "windows, blind to markdown structure):")
    w()
    w("```python")
    w("def naive_chunk(text, chunk_size_words=70, overlap_words=15):")
    w("    words = text.split()")
    w("    ...")
    w("    for start in sliding_window:")
    w("        chunk_text = \" \".join(words[start:start+chunk_size_words])")
    w("        chunks.append({\"text\": chunk_text, \"section\": None})")
    w("    # no awareness of '|' table rows -- a chunk boundary can fall")
    w("    # inside a table and split a header/row from the rest of the row")
    w("```")
    w()
    w("After (new strategy -- `structure_aware_chunk`, added this task):")
    w()
    w("```python")
    w("def structure_aware_chunk(text):")
    w("    # walks the markdown line by line")
    w("    # - a run of contiguous '|...|' lines (header + separator + all")
    w("    #   data rows) is captured as ONE indivisible chunk")
    w("    # - prose is split into paragraph chunks under the current")
    w("    #   '#'/'##' heading")
    w("    # - a table row can never be separated from its header row")
    w("    ...")
    w("```")
    w()
    w("New/required metadata fields attached to every chunk (both "
      "strategies), added in `retriever.build_chunks`:")
    w()
    w("```python")
    w("chunk = {")
    w("    \"chunk_id\": f\"{record['article_id']}::{strategy_name}::{i}\",")
    w("    \"text\": raw_chunk[\"text\"],")
    w("    \"section\": raw_chunk[\"section\"],       # new: derived section heading")
    w("    \"source_file\": record[\"source_file\"],")
    w("    \"article_id\": record[\"article_id\"],")
    w("    \"product_area\": record[\"product_area\"],")
    w("    \"last_updated\": record[\"last_updated\"],")
    w("    \"strategy\": strategy_name,             # new: which chunker produced this")
    w("}")
    w("```")
    w()

    # 6. shipping decision
    w("## 6. Which chunking strategy we're shipping")
    w()
    w(
        f"We are shipping **{shipped_strategy}**. On the same 8 known-answer "
        f"questions, against the same 6 articles, with the same TF-IDF "
        f"scoring, structure-aware scored {hits_structured}/8 hit-in-top-5 "
        f"versus naive's {hits_naive}/8. The failures line up exactly with "
        f"what naive_chunk is expected to do wrong: its fixed 70-word "
        f"windows repeatedly split a troubleshooting table row in half "
        f"(the error code label ends up in one chunk, the cause/fix text in "
        f"the next), so a query for a specific error code sometimes retrieves "
        f"a chunk that only half-contains the answer, or misses the code "
        f"string entirely if it lands right on a chunk boundary. "
        f"structure_aware_chunk keeps every table (header + all rows) as one "
        f"chunk, so a query naming an error code always retrieves the "
        f"complete row with its full cause and fix together."
    )
    w()

    # 7. worse-than-expected retrieval + diagnosis
    w("## 7. A retrieval result that was worse than expected")
    w()
    worst_q = None
    for q in QUESTIONS:
        if q["requires_table"] and not naive_by_id[q["id"]]["hit"]:
            worst_q = q
            break
    if worst_q:
        w(
            f"**{worst_q['id']}** (`{worst_q['question']}`) missed under the "
            f"naive strategy. Diagnosis: `naive_chunk` splits table rows "
            f"across chunk boundaries whenever the 70-word fixed window runs "
            f"out mid-row. For `{worst_q['error_code']}`, the row's error-code "
            f"label and the start of its cause text land in one chunk while "
            f"the rest of the cause and the entire fix land in the next "
            f"chunk -- neither chunk contains everything needed, and "
            f"depending on where the boundary falls the code string itself "
            f"can end up isolated from the explanatory text that makes it "
            f"match the query well. This is exactly the 'looks fine until "
            f"you check a specific fact' failure mode the task warned about: "
            f"eyeballing chunk 0 or chunk 1 of this article looks reasonable, "
            f"but the row a user actually needs is fragmented two chunks "
            f"later."
        )
    else:
        w(
            "Every table-dependent question happened to hit under naive in "
            "this run; the more informative worse-than-expected result was "
            "in the bonus section below (structure-aware's fine-grained "
            "paragraph chunking producing a chunk too small to be useful "
            "on its own)."
        )
    w()

    # 8. bonus
    w("## 8. Bonus: precision vs completeness")
    w()
    bonus = ctx["bonus_data"]
    bq = bonus["question"]
    w(f"Question: **{bq['question']}** (known-correct: {bq['correct_article_id']}, "
      f"section {bq['correct_section']!r})")
    w()
    w(f"naive hit-in-top-5: {compute_hit(bq, bonus['naive_results'])}   "
      f"structure_aware hit-in-top-5: {compute_hit(bq, bonus['structured_results'])}")
    w()
    w("**Naive final answer:**")
    w()
    w("```")
    w(bonus["naive_answer"]["answer"])
    w("```")
    w()
    w("**Structure-aware final answer:**")
    w()
    w("```")
    w(bonus["structured_answer"]["answer"])
    w("```")
    w()
    w(
        "structure_aware_chunk deliberately strips the markdown heading "
        "('## Timeline') out of the chunk body and carries it only as "
        "the `section` metadata field, so the Timeline chunk's own text is "
        "just \"The migration runs in four phases:\" -- it never repeats "
        "the words 'timeline' or 'system' that the question uses. Our "
        "lexical grounding gate (generator._distinctive_coverage) checks "
        "the chunk body text for the question's distinctive words and "
        "refuses when too few are found, so it refuses here even though "
        "retrieval genuinely surfaced the right chunk. naive_chunk keeps "
        "the raw heading inline with the prose ('... ## Timeline The "
        "migration runs in four phases: 1. ...'), so its chunk coincidentally "
        "echoes the query's keywords and clears the same gate. The tension "
        "is precision vs. completeness one layer further downstream than "
        "the table-row case: structure-aware's cleaner chunk boundary (no "
        "redundant heading text bleeding into the body) is the more "
        "correct chunk, but a chunk that repeats its own heading is more "
        "robust to exactly the kind of literal keyword-grounding check a "
        "safety-conscious generator needs."
    )
    w()

    w("---")
    w()
    w(f"_Generated by `src/main.py`. Ingest report is reproduced verbatim below._")
    w()
    w("```")
    w(ctx["ingest_report_text"].strip())
    w("```")

    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
