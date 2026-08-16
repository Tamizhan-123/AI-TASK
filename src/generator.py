"""
Extractive generation with a hard, code-level refusal gate.

Design choice: instead of calling an external LLM (not available/guaranteed
in this environment) generate_answer() is extractive -- it quotes directly
from the single retrieved chunk it cites. This is what lets us mechanically
guarantee "the cited chunk actually contains the claim": the claim IS a
verbatim substring of the cited chunk's text, checked in code
(_is_grounded), not asserted by prompt instruction.

The refusal behavior is enforced by TWO hard, code-level gates, not a soft
"use your best judgement" prompt instruction:

1. CONFIDENCE_THRESHOLD -- the top retrieval score must clear a fixed bar.
2. A grounding check specific to what is being asked:
   - If the question names an error code (ERR-####), the cited chunk must
     contain the COMPLETE table row for that code (code + cause + fix, all
     three pipe-delimited fields present together) -- not just the code
     label with the cause/fix cut off by a chunk boundary.
   - Otherwise, a DISTINCTIVE-keyword coverage check: this corpus is a
     single narrow topic (billing migration), so words like "billing",
     "migration", "cutover", "account" appear in nearly every chunk and
     make raw TF-IDF score alone an unreliable refusal signal (an
     out-of-corpus question like "what's the refund SLA?" still shares
     enough generic vocabulary with some chunk to score deceptively high).
     GENERIC_WORDS is the set of words that appear in at least 4 of the 6
     source articles; DISTINCTIVE_COVERAGE_THRESHOLD requires that at least
     half of the question's non-generic words actually appear in the cited
     chunk before a claim is allowed through.
"""

import re
from collections import Counter

from ingest import ingest_articles

CONFIDENCE_THRESHOLD = 0.10
DISTINCTIVE_COVERAGE_THRESHOLD = 0.5

REFUSAL_TEXT = (
    "I don't have grounded information in the indexed help-centre articles "
    "to answer this confidently, so I'm refusing rather than guessing."
)

ERROR_CODE_RE = re.compile(r"ERR-\d{3,4}")
WORD_RE = re.compile(r"[a-zA-Z']+")
STOPWORDS = frozenset(
    "what is the a an of for to and or how do i does after during my your "
    "before which who when where you should this that with are".split()
)


def _compute_generic_words():
    """
    Words appearing in at least 4 of the 6 source articles -- generic
    domain scaffolding ("billing", "migration", "cutover", "account", ...)
    that should not count as evidence a specific claim is grounded.
    """
    records, _ = ingest_articles()
    doc_freq = Counter()
    for record in records:
        words = set(w.lower() for w in WORD_RE.findall(record["body"]) if len(w) > 2)
        doc_freq.update(words)
    return frozenset(w for w, c in doc_freq.items() if c >= 4)


GENERIC_WORDS = _compute_generic_words()


def _distinctive_words(question):
    words = [w.lower() for w in WORD_RE.findall(question) if len(w) > 2]
    return [w for w in words if w not in STOPWORDS and w not in GENERIC_WORDS]


def _distinctive_coverage(question, text):
    """
    Fraction of the question's distinctive (non-generic, non-stopword)
    words that literally appear in the candidate chunk text, matched on
    whole-word boundaries (not raw substring containment -- otherwise a
    short word like "multi" would false-positive-match inside an unrelated
    word like "multiple"). Returns 1.0 (pass-through) if the question has
    no distinctive words at all, since there is nothing left to check
    beyond the score threshold.
    """
    words = _distinctive_words(question)
    if not words:
        return 1.0
    tl = text.lower()
    hits = sum(1 for w in words if re.search(r"\b" + re.escape(w) + r"\b", tl))
    return hits / len(words)


def _refusal(reason):
    return {
        "refused": True,
        "answer": REFUSAL_TEXT,
        "citations": [],
        "reason": reason,
    }


def _extract_complete_table_row(text, code):
    """
    Returns the COMPLETE pipe-delimited row "| CODE | cause | fix |" only if
    all three fields are present together in this chunk's text -- i.e. the
    cause and fix were not cut off by a chunk boundary. Works whether the
    chunk preserves real newlines (structure_aware) or has been flattened
    to a single line by naive_chunk's word-join, since the search is over
    the whole chunk text rather than per physical line.
    """
    row_re = re.compile(r"\|\s*" + re.escape(code) + r"\s*\|[^|]*\|[^|]*\|")
    match = row_re.search(text)
    if not match:
        return None
    return " ".join(match.group(0).split())


def _extract_lead_sentences(text, max_sentences=2):
    flat = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", flat)
    return " ".join(sentences[:max_sentences]).strip()


def _is_grounded(claim_text, chunk_text):
    """
    Hard check: the claim must literally appear inside the cited chunk's
    text. This is what makes "the cited chunk actually contains the claim"
    a code-level guarantee instead of a hope.
    """
    if not claim_text:
        return False
    normalize = lambda s: " ".join(s.split())
    return normalize(claim_text) in normalize(chunk_text)


def generate_answer(question, retrieved_chunks, threshold=CONFIDENCE_THRESHOLD):
    """
    question: str
    retrieved_chunks: ranked list from Index.search(), i.e.
        [{"score": float, "chunk": {...}}, ...] sorted best-first.
    threshold: fixed confidence cutoff (hard-coded default). Refusal is a
        forced code path below this line, not a suggestion to the model.

    Returns a dict:
        {"refused": bool, "answer": str, "citations": [...], ...}
    """
    if not retrieved_chunks:
        return _refusal("no chunks retrieved for this query")

    # Hard floor: no candidate below this score is considered at all,
    # regardless of rank.
    candidates = [rc for rc in retrieved_chunks if rc["score"] >= threshold]
    if not candidates:
        return _refusal(
            f"top retrieval score {retrieved_chunks[0]['score']:.4f} is "
            f"below the confidence threshold {threshold:.4f}"
        )

    codes_in_question = ERROR_CODE_RE.findall(question)

    if codes_in_question:
        code = codes_in_question[0]
        # Search rank-by-rank (among candidates clearing the score floor)
        # for the first chunk that contains the COMPLETE cause+fix row.
        # Never settle for a chunk where the row was severed by a chunk
        # boundary, even if it ranked higher.
        found = None
        for rc in candidates:
            claim = _extract_complete_table_row(rc["chunk"]["text"], code)
            if claim is not None:
                found = (rc, claim)
                break
        if found is None:
            return _refusal(
                f"question asks about {code} but no retrieved chunk above "
                f"the confidence threshold contains the complete cause+fix "
                f"row for it -- refusing rather than inventing or guessing "
                f"from a partial row"
            )
        top, claim = found
        chunk = top["chunk"]
    else:
        # Search rank-by-rank for the first chunk whose distinctive
        # (non-generic) query terms are actually grounded in it, instead of
        # blindly trusting whichever chunk happened to rank #1 by raw
        # cosine score.
        found = None
        for rc in candidates:
            coverage = _distinctive_coverage(question, rc["chunk"]["text"])
            if coverage >= DISTINCTIVE_COVERAGE_THRESHOLD:
                found = rc
                break
        if found is None:
            best_coverage = max(
                _distinctive_coverage(question, rc["chunk"]["text"]) for rc in candidates
            )
            return _refusal(
                f"the question's distinctive terms are not sufficiently "
                f"grounded in any retrieved chunk above the confidence "
                f"threshold (best coverage={best_coverage:.2f} < "
                f"{DISTINCTIVE_COVERAGE_THRESHOLD}) -- refusing rather than "
                f"answering from generic topical overlap alone"
            )
        top = found
        chunk = top["chunk"]
        claim = _extract_lead_sentences(chunk["text"], max_sentences=2)

    if not _is_grounded(claim, chunk["text"]):
        return _refusal(
            "extracted claim failed the grounding check against its own "
            "cited chunk -- refusing rather than asserting an ungrounded claim"
        )

    citation = f"[source: article_id={chunk['article_id']}, chunk_id={chunk['chunk_id']}]"
    answer_text = f"{claim} {citation}"

    return {
        "refused": False,
        "answer": answer_text,
        "citations": [
            {
                "article_id": chunk["article_id"],
                "chunk_id": chunk["chunk_id"],
                "source_file": chunk["source_file"],
            }
        ],
        "top_score": top["score"],
    }
