"""
Optional embeddings-based retrieval index for theology theme cards.

Design goals:
- Purely optional. Enabled only when ENABLE_EMBEDDINGS=1 and deps available
- Falls back to keyword/IDF retrieval when unavailable
- Avoid heavy downloads during tests/CI unless explicitly enabled
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


class EmbeddingIndex:
    def __init__(self, cards: List[Dict[str, Any]]) -> None:
        self.cards = cards or []
        self.enabled: bool = os.environ.get("ENABLE_EMBEDDINGS", "0") in ("1", "true", "True")
        self._model = None
        self._index = None
        self._card_texts: List[str] = []
        self._init_error: Optional[str] = None
        if not self.enabled:
            return
        try:
            # Lazy import to avoid hard dep when disabled
            from sentence_transformers import SentenceTransformer  # type: ignore

            try:
                import faiss  # type: ignore
            except Exception:  # pragma: no cover - optional
                faiss = None

            model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            self._model = SentenceTransformer(model_name)

            # Build card texts from theme, definition, and keywords
            self._card_texts = [
                f"{c.get('theme','')}. {c.get('definition','')} Keywords: {', '.join(c.get('keywords', []) or [])}"
                for c in self.cards
            ]
            embs = self._model.encode(
                self._card_texts, normalize_embeddings=True, convert_to_numpy=True
            )

            if faiss is not None:
                # Use FAISS index for efficient retrieval
                dim = embs.shape[1]
                index = faiss.IndexFlatIP(dim)
                index.add(embs)
                self._index = (index, "faiss")
            else:
                # Fallback: store embeddings in-memory for cosine search
                self._index = (embs, "numpy")
        except Exception as e:  # pragma: no cover - avoid failing tests when disabled
            self._init_error = str(e)
            self.enabled = False
            self._model = None
            self._index = None

    def is_available(self) -> bool:
        return self.enabled and self._index is not None and self._model is not None

    def search(self, query: str, top_k: int = 5) -> List[int]:
        if not self.is_available():
            return []
        try:
            import numpy as np  # type: ignore
        except Exception:
            return []

        query_emb = self._model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        index, idx_type = self._index
        if idx_type == "faiss":  # pragma: no cover
            D, I = index.search(query_emb, top_k)
            return [int(i) for i in I[0] if i >= 0]
        else:
            # Cosine via dot-product on normalized vectors
            embs = index
            scores = np.dot(embs, query_emb[0])
            order = np.argsort(-scores)[: max(1, top_k)]
            return [int(i) for i in order]
