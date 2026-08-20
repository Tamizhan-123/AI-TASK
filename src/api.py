"""
API layer over the Week 3 / Week 4 pipeline: ask a question over HTTP, get
back the retrieved chunks (the inspection view -- question, what was
fetched, final answer, side by side) and the generated/cited answer.

Both weeks' retrieval strategies are exposed as a selectable `mode` on the
same endpoint, instead of picking one and hiding the other:
  - "tfidf"  -- Week 3's shipped strategy: structure_aware chunking +
                TF-IDF cosine similarity only.
  - "hybrid" -- Week 4's improvement: the same TF-IDF ranking fused with a
                BM25 ranking via Reciprocal Rank Fusion (retriever.
                Retriever.search_hybrid). Default, since it measured a
                higher hit-rate@3 (see results_week4.md).

The Retriever (and its two Chroma collections + BM25 indexes) is built
once at process startup, not per-request -- rebuilding it on every request
would re-fit the TF-IDF vectorizer and re-populate Chroma from scratch each
time, which is wasteful and unnecessary since the underlying 6 articles
don't change between requests.

Run with:  uvicorn api:app --reload --app-dir src
Then:      POST http://127.0.0.1:8000/ask  {"question": "...", "mode": "hybrid", "k": 3}
Docs at:   http://127.0.0.1:8000/docs
"""

from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from generator import CONFIDENCE_THRESHOLD, generate_answer
from ingest import ingest_articles
from retriever import Retriever

STRATEGY = "structure_aware"  # the chunking strategy shipped in Week 3

app = FastAPI(
    title="Billing Migration Help-Centre Q&A",
    description=(
        "Ask a question over the 6 billing-migration help-centre articles. "
        "Exposes both the Week 3 (TF-IDF-only) and Week 4 (hybrid "
        "TF-IDF + BM25) retrieval strategies via the `mode` field."
    ),
    version="4.0.0",
)

_retriever = None


def get_retriever():
    global _retriever
    if _retriever is None:
        records, failures = ingest_articles()
        if failures:
            raise RuntimeError(f"Ingest reported {len(failures)} failure(s)")
        _retriever = Retriever(records)
    return _retriever


@app.on_event("startup")
def _warm_up():
    get_retriever()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What does ERR-4032 mean and what's the fix?"])
    mode: Literal["tfidf", "hybrid"] = Field(
        "hybrid",
        description="'tfidf' = Week 3 shipped strategy. 'hybrid' = Week 4 improvement (TF-IDF + BM25 via RRF).",
    )
    k: int = Field(3, ge=1, le=20, description="Number of chunks to retrieve.")
    product_area_filter: Optional[str] = Field(
        None, description="Optional metadata filter, e.g. 'billing', 'payments', 'account'."
    )


class RetrievedChunk(BaseModel):
    rank: int
    score: float
    article_id: str
    chunk_id: str
    section: Optional[str]
    text: str
    component_scores: Optional[dict] = None


class AskResponse(BaseModel):
    question: str
    mode: str
    retrieved: list[RetrievedChunk]
    refused: bool
    answer: str
    citations: list
    reason: Optional[str] = None


@app.get("/health")
def health():
    retriever = get_retriever()
    return {
        "status": "ok",
        "strategy": STRATEGY,
        "chunk_counts": retriever.chunk_counts,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
    }


def _for_confidence_gate(results, mode):
    """
    generate_answer's CONFIDENCE_THRESHOLD (0.1) was calibrated against a
    raw TF-IDF cosine similarity, which has real magnitude proportional to
    how well a query matches a chunk. Reciprocal Rank Fusion's score does
    not: it is 1/(RRF_K + rank) summed per list, so it depends only on
    *rank position* in the candidate pool, not on how strong the match
    actually is -- a genuinely irrelevant query and a great match can both
    land a chunk at rank 1 and get nearly the same RRF score (verified:
    every in-corpus and out-of-corpus question scored ~0.032-0.033 here).
    Gating confidence on the raw RRF score would refuse strong hybrid hits
    and admit weak ones almost at random.

    So for the confidence floor only, hybrid mode substitutes each
    candidate's TF-IDF component score (falling back to 0.0 for a chunk
    BM25-only surfaced) -- a like-for-like, already-calibrated scale --
    while leaving hybrid's fused ORDER untouched. Hybrid fusion still
    decides which chunks make the top-k and in what order; the TF-IDF
    component score decides whether any of them are confident enough to
    answer from at all.
    """
    if mode != "hybrid":
        return results
    return [
        {**r, "score": r.get("component_scores", {}).get("tfidf", 0.0)}
        for r in results
    ]


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    retriever = get_retriever()

    if req.mode == "hybrid":
        results = retriever.search_hybrid(
            STRATEGY, req.question, k=req.k, product_area_filter=req.product_area_filter
        )
    else:
        results = retriever.search(
            STRATEGY, req.question, k=req.k, product_area_filter=req.product_area_filter
        )

    answer = generate_answer(req.question, _for_confidence_gate(results, req.mode))

    retrieved = [
        RetrievedChunk(
            rank=i + 1,
            score=r["score"],
            article_id=r["chunk"]["article_id"],
            chunk_id=r["chunk"]["chunk_id"],
            section=r["chunk"]["section"],
            text=r["chunk"]["text"],
            component_scores=r.get("component_scores"),
        )
        for i, r in enumerate(results)
    ]

    return AskResponse(
        question=req.question,
        mode=req.mode,
        retrieved=retrieved,
        refused=answer["refused"],
        answer=answer["answer"],
        citations=answer.get("citations", []),
        reason=answer.get("reason"),
    )


@app.get("/ask", response_model=AskResponse)
def ask_get(
    q: str,
    mode: Literal["tfidf", "hybrid"] = "hybrid",
    k: int = 3,
    product_area_filter: Optional[str] = None,
):
    """GET convenience form of /ask, e.g. /ask?q=...&mode=hybrid&k=3"""
    if not q.strip():
        raise HTTPException(status_code=422, detail="q must not be empty")
    return ask(AskRequest(question=q, mode=mode, k=k, product_area_filter=product_area_filter))
