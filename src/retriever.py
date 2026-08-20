"""
Builds the two chunk indexes (naive vs structure-aware) from the same 6
ingested articles, and exposes a single search(strategy, ...) entry point.

This is the ONLY thing that differs between the two experimental runs in
STEP 6 -- the chunker. Both indexes use the same Index class (same TF-IDF
vectorizer settings, same cosine-distance metric, backed by the same
persistent Chroma database), the same 6 source articles, and the same query
text. The only variable is naive_chunk vs structure_aware_chunk.
"""

import os

import chromadb
from chromadb.config import Settings

from bm25 import BM25Index
from chunkers import naive_chunk, structure_aware_chunk
from indexer import Index

RRF_K = 60  # standard Reciprocal Rank Fusion constant

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")

STRATEGIES = {
    "naive": naive_chunk,
    "structure_aware": structure_aware_chunk,
}


def build_chunks(records, strategy_name):
    chunk_fn = STRATEGIES[strategy_name]
    all_chunks = []
    for record in records:
        raw_chunks = chunk_fn(record["body"])
        for i, raw_chunk in enumerate(raw_chunks):
            chunk = {
                "chunk_id": f"{record['article_id']}::{strategy_name}::{i}",
                "text": raw_chunk["text"],
                "section": raw_chunk["section"],
                "source_file": record["source_file"],
                "article_id": record["article_id"],
                "product_area": record["product_area"],
                "last_updated": record["last_updated"],
                "strategy": strategy_name,
            }
            all_chunks.append(chunk)
    return all_chunks


class Retriever:
    def __init__(self, records, db_path=CHROMA_DB_PATH):
        # One persistent Chroma database on disk, shared by both
        # strategies' collections. anonymized_telemetry=False keeps this
        # fully offline -- no network calls, no external embedding API.
        self.client = chromadb.PersistentClient(
            path=db_path, settings=Settings(anonymized_telemetry=False)
        )
        self.indexes = {}
        self.bm25_indexes = {}
        self.chunk_counts = {}
        for strategy_name in STRATEGIES:
            chunks = build_chunks(records, strategy_name)
            collection_name = f"chunks_{strategy_name}"
            self.indexes[strategy_name] = Index(chunks, collection_name, self.client)
            # BM25 -- the "exact words" side of hybrid search, scored over
            # section-heading + body text (see bm25.BM25Index docstring for
            # why the heading has to be folded back in for this strategy).
            self.bm25_indexes[strategy_name] = BM25Index(chunks)
            self.chunk_counts[strategy_name] = len(chunks)

    def search(self, strategy_name, query, k=5, product_area_filter=None):
        return self.indexes[strategy_name].search(query, k=k, product_area_filter=product_area_filter)

    def search_hybrid(self, strategy_name, query, k=5, pool=10, product_area_filter=None):
        """
        Hybrid search: fuses the existing TF-IDF ("meaning") ranking with a
        BM25 ("exact words") ranking via Reciprocal Rank Fusion (RRF).

        Each side is queried independently for up to `pool` candidates (a
        wider net than the final k, so a chunk that is merely decent on one
        signal and strong on the other still has a chance to surface). A
        chunk's RRF score is 1/(RRF_K + rank) summed over every list it
        appears in (1-indexed rank); a chunk that only one side retrieved
        still gets a score from that side alone. Results are the top-k
        chunks by RRF score, descending.
        """
        tfidf_results = self.indexes[strategy_name].search(
            query, k=pool, product_area_filter=product_area_filter
        )
        bm25_results = self.bm25_indexes[strategy_name].search(query, k=pool)
        if product_area_filter:
            bm25_results = [
                r for r in bm25_results
                if r["chunk"]["product_area"] == product_area_filter
            ]

        # A component whose own top score is 0 has zero real signal -- every
        # candidate tied at an undefined/zero similarity. Chroma's HNSW index
        # still hands back *some* order for that tie, but it is an artifact
        # of internal graph traversal, not a ranking, and it is not even
        # stable run-to-run for an all-zero query vector. Feeding that into
        # RRF would let pure noise compete with the other side's real
        # ranking, and would make the fused result non-reproducible whenever
        # this happens. Drop a zero-signal component from fusion entirely
        # instead of trusting its order.
        if not tfidf_results or tfidf_results[0]["score"] <= 0:
            tfidf_results = []
        if not bm25_results or bm25_results[0]["score"] <= 0:
            bm25_results = []

        rrf_scores = {}
        chunk_by_id = {}
        component_scores = {}
        for rank_list in (tfidf_results, bm25_results):
            for rank, r in enumerate(rank_list, start=1):
                chunk_id = r["chunk"]["chunk_id"]
                chunk_by_id[chunk_id] = r["chunk"]
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
        for r in tfidf_results:
            component_scores.setdefault(r["chunk"]["chunk_id"], {})["tfidf"] = r["score"]
        for r in bm25_results:
            component_scores.setdefault(r["chunk"]["chunk_id"], {})["bm25"] = r["score"]

        ranked_ids = sorted(rrf_scores, key=lambda cid: -rrf_scores[cid])[:k]
        return [
            {
                "score": rrf_scores[cid],
                "chunk": chunk_by_id[cid],
                "component_scores": component_scores.get(cid, {}),
            }
            for cid in ranked_ids
        ]
