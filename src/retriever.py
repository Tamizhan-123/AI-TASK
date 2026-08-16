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

from chunkers import naive_chunk, structure_aware_chunk
from indexer import Index

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
        self.chunk_counts = {}
        for strategy_name in STRATEGIES:
            chunks = build_chunks(records, strategy_name)
            collection_name = f"chunks_{strategy_name}"
            self.indexes[strategy_name] = Index(chunks, collection_name, self.client)
            self.chunk_counts[strategy_name] = len(chunks)

    def search(self, strategy_name, query, k=5, product_area_filter=None):
        return self.indexes[strategy_name].search(query, k=k, product_area_filter=product_area_filter)
