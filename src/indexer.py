"""
TF-IDF vectors, persisted and queried through a Chroma vector database.

Chunks are stored in a persistent Chroma collection on disk (see
retriever.CHROMA_DB_PATH) rather than only held in memory. The embeddings
Chroma stores and searches over are still our own scikit-learn TF-IDF
vectors -- there is no external embedding API and no network call -- so the
similarity scores are the same TF-IDF cosine similarity as before, just
computed and stored via Chroma's collection.query() instead of a hand-rolled
sklearn cosine_similarity call. Both strategies' indexes use the exact same
vectorizer settings and the exact same distance metric; only the chunks fed
in (i.e. which chunker produced them) differ between the two collections.
"""

from sklearn.feature_extraction.text import TfidfVectorizer


class Index:
    def __init__(self, chunks, collection_name, client):
        """
        chunks: list of dicts, each carrying at least:
            chunk_id, text, source_file, article_id, product_area,
            last_updated, strategy, section
        collection_name: name of the Chroma collection to (re)create for
            this strategy's chunks.
        client: a chromadb PersistentClient shared across both strategies'
            indexes, backed by one on-disk database.
        """
        self.chunks_by_id = {c["chunk_id"]: c for c in chunks}

        # max_df downweights words shared by almost every chunk in this
        # corpus (every article says "billing", "migration", "cutover",
        # "account" repeatedly) so a query matching only on that shared
        # vocabulary does not score artificially high against an unrelated
        # chunk. sublinear_tf dampens raw term-frequency blowups in the
        # longer chunks. ngram_range=(1, 2) lets two-word phrases like
        # "sync error" or "error code" contribute as their own feature.
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_df=0.5,
            sublinear_tf=True,
            ngram_range=(1, 2),
        )
        texts = [c["text"] for c in chunks]
        matrix = self.vectorizer.fit_transform(texts)
        embeddings = matrix.toarray().tolist()

        # Reset the collection on every run -- this run indexes ONLY the
        # current 6 articles, so the collection must never accumulate
        # chunks left over from a previous run or a historical corpus.
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
        self.collection = client.create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        ids = [c["chunk_id"] for c in chunks]
        metadatas = [
            {
                "source_file": c["source_file"],
                "article_id": c["article_id"],
                "product_area": c["product_area"],
                "last_updated": c["last_updated"],
                "strategy": c["strategy"],
                "section": c["section"] or "",
            }
            for c in chunks
        ]
        self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts)

    def search(self, query, k=5, product_area_filter=None):
        """
        Returns a ranked list of up to k results:
            [{"score": float, "chunk": chunk_dict}, ...]
        sorted by score descending. If product_area_filter is given, Chroma
        restricts the search to chunks whose product_area matches via a
        `where` filter, applied before ranking -- not after truncating to k.
        """
        count = self.collection.count()
        if count == 0:
            return []

        where = {"product_area": product_area_filter} if product_area_filter else None
        query_vec = self.vectorizer.transform([query]).toarray().tolist()

        result = self.collection.query(
            query_embeddings=query_vec,
            n_results=min(k, count),
            where=where,
        )

        ids = result["ids"][0]
        distances = result["distances"][0]

        results = []
        for chunk_id, distance in zip(ids, distances):
            score = 1.0 - distance  # cosine distance -> cosine similarity
            results.append({"score": float(score), "chunk": self.chunks_by_id[chunk_id]})
        return results
