"""
The embedding step: turns chunk text into vectors.

This project is offline-only (see indexer.py, retriever.py) -- there is no
external embedding API and no network call, so "embedding" here means a
scikit-learn TF-IDF vector, not a dense/semantic embedding from a model like
OpenAI's or BERT's. TfidfEmbedder is the one place that vectorizer is
configured and fit, so indexer.py (which persists the resulting vectors into
Chroma) and anything else that needs to embed a query text share the exact
same vocabulary and settings.
"""

from sklearn.feature_extraction.text import TfidfVectorizer


class TfidfEmbedder:
    def __init__(self):
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
        self._fitted = False

    def fit_embed(self, texts):
        """Fits the vectorizer on `texts` and returns their embeddings (one per text)."""
        matrix = self.vectorizer.fit_transform(texts)
        self._fitted = True
        return matrix.toarray().tolist()

    def embed_query(self, text):
        """Embeds a single query text using the already-fitted vocabulary."""
        if not self._fitted:
            raise RuntimeError("embed_query called before fit_embed -- no vocabulary to embed against")
        return self.vectorizer.transform([text]).toarray().tolist()[0]
