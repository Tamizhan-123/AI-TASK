"""
A small, dependency-free BM25 (Okapi) implementation -- the "exact words"
half of this week's hybrid search. No external package (rank_bm25 is not
installed in this environment and this task is offline-only, same
constraint as the rest of this codebase), so BM25Index below reimplements
the standard formula directly.

Deliberately scored over `(section heading + body text)`, not body text
alone. structure_aware_chunk (see chunkers.py) strips every markdown
heading out of the chunk body and carries it only as the `section`
metadata field -- so a query built from heading vocabulary ("escalation
path", "testing webhooks", "timeline") has zero lexical overlap with any
indexed chunk body at all under the existing TF-IDF index. Folding the
heading back in for the keyword side of hybrid search is what buys that
vocabulary back without touching the chunk bodies TF-IDF and the generator
already depend on.
"""

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")

K1 = 1.5
B = 0.75


def tokenize(text):
    return TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, chunks):
        """
        chunks: list of chunk dicts (chunk_id, text, section, ...). The
        keyword document for each chunk is its section heading (if any)
        followed by its body text.
        """
        self.chunks = chunks
        self.doc_tokens = [
            tokenize(f"{c['section'] or ''} {c['text']}") for c in chunks
        ]
        self.doc_len = [len(toks) for toks in self.doc_tokens]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_tokens else 0.0

        n_docs = len(self.doc_tokens)
        doc_freq = Counter()
        for toks in self.doc_tokens:
            doc_freq.update(set(toks))
        self.idf = {
            term: math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            for term, df in doc_freq.items()
        }
        self.term_freqs = [Counter(toks) for toks in self.doc_tokens]

    def search(self, query, k=5):
        """
        Returns a ranked list of up to k results:
            [{"score": float, "chunk": chunk_dict}, ...]
        sorted by BM25 score descending. Scores are >= 0; a score of 0.0
        means none of the query's tokens matched this chunk at all.
        """
        if not self.doc_tokens:
            return []

        q_tokens = tokenize(query)
        scored = []
        for i, tf in enumerate(self.term_freqs):
            dl = self.doc_len[i]
            score = 0.0
            for term in q_tokens:
                if term not in tf:
                    continue
                f = tf[term]
                idf = self.idf.get(term, 0.0)
                denom = f + K1 * (1 - B + B * dl / self.avgdl) if self.avgdl else f
                score += idf * (f * (K1 + 1)) / denom
            scored.append((score, i))

        scored.sort(key=lambda x: -x[0])
        results = []
        for score, i in scored[:k]:
            results.append({"score": float(score), "chunk": self.chunks[i]})
        return results
