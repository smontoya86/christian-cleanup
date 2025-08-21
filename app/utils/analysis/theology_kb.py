"""
Tiny theology knowledge base (KB) for grounding.

Provides theme cards (name, brief definition, exemplar verses) and a trivial
retrieval method based on keyword overlap. This is intentionally lightweight
for MVP and runs fully local.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from .embedding_index import EmbeddingIndex

THEME_CARDS: List[Dict[str, Any]] = [
    {
        "theme": "Gospel Presentation",
        "definition": "Proclaims Christ's atoning work, cross, resurrection, grace by faith.",
        "keywords": ["cross", "resurrection", "gospel", "grace", "salvation", "jesus"],
        "scripture": [
            {"reference": "1 Corinthians 15:3-4", "theme": "Gospel Presentation"},
            {"reference": "John 3:16", "theme": "Gospel Presentation"},
        ],
    },
    {
        "theme": "Christ-Centered",
        "definition": "Exalts Jesus as Lord, Savior, King; worship directed to Christ.",
        "keywords": ["jesus", "christ", "lord", "king", "savior", "messiah"],
        "scripture": [
            {"reference": "John 14:6", "theme": "Christ-Centered"},
            {"reference": "Colossians 1:15-20", "theme": "Christ-Centered"},
        ],
    },
    {
        "theme": "Redemption",
        "definition": "Deliverance by grace; ransom from sin and death.",
        "keywords": ["redeem", "redeemed", "redemption", "ransom", "blood"],
        "scripture": [
            {"reference": "Ephesians 1:7", "theme": "Redemption"},
            {"reference": "1 Peter 1:18-19", "theme": "Redemption"},
        ],
    },
    {
        "theme": "Worship of God",
        "definition": "Praise, adoration, reverence directed to God.",
        "keywords": ["praise", "worship", "glory", "exalt", "hallelujah"],
        "scripture": [
            {"reference": "Psalm 29:2", "theme": "Worship of God"},
            {"reference": "Hebrews 13:15", "theme": "Worship of God"},
        ],
    },
    {
        "theme": "Profanity",
        "definition": "Obscene or degrading language contrary to Christian virtue.",
        "keywords": ["f***", "s***", "b****", "curse", "obscene"],
        "scripture": [
            {"reference": "Ephesians 4:29", "theme": "Profanity"},
        ],
    },
    {
        "theme": "Sexual Immorality",
        "definition": "Celebration or normalization of lust, adultery, fornication.",
        "keywords": ["lust", "adultery", "fornication", "hookup", "porn"],
        "scripture": [
            {"reference": "1 Corinthians 6:18", "theme": "Sexual Immorality"},
        ],
    },
]


class TheologyKB:
    def __init__(self) -> None:
        # Load external catalog if present, else fallback to built-ins
        catalog_path = os.environ.get(
            "THEME_CATALOG_PATH",
            os.path.join(os.path.dirname(__file__), "themes_catalog.json"),
        )
        cards = THEME_CARDS
        try:
            if os.path.exists(catalog_path):
                with open(catalog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    cards = data
        except Exception:
            # Fallback to built-ins on any error
            pass
        self.cards = cards
        # Versioning for persistence/telemetry
        self.version = os.environ.get("KB_VERSION", "builtin-v1")
        # Optional embedding index (FAISS or numpy) when enabled
        self._emb_index = EmbeddingIndex(self.cards)
        # Build lightweight IDF map for keywords (no heavy deps)
        self._keyword_idf: Dict[str, float] = {}
        total_docs = len(self.cards) if self.cards else 1
        keyword_doc_counts: Dict[str, int] = {}
        for card in self.cards:
            seen = set()
            for kw in card.get("keywords", []) or []:
                kw_low = (kw or "").lower().strip()
                if not kw_low:
                    continue
                if kw_low in seen:
                    continue
                seen.add(kw_low)
                keyword_doc_counts[kw_low] = keyword_doc_counts.get(kw_low, 0) + 1
        for kw, df in keyword_doc_counts.items():
            # Add-one smoothing in denominator to avoid div-by-zero
            self._keyword_idf[kw] = max(
                0.0, __import__("math").log((total_docs + 1) / (df + 1)) + 1.0
            )

    def retrieve_theme_cards(self, text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return up to top_k cards ranked by IDF-weighted keyword overlap (fallback: naive)."""
        text_low = (text or "").lower()
        # Try embedding index first if available
        if hasattr(self, "_emb_index") and self._emb_index.is_available():
            idxs = self._emb_index.search(text_low, top_k=top_k)
            if idxs:
                return [self.cards[i] for i in idxs if 0 <= i < len(self.cards)]
        scored: List[Dict[str, Any]] = []
        for card in self.cards:
            score = 0.0
            kws = card.get("keywords", []) or []
            for kw in kws:
                kw_low = (kw or "").lower()
                if kw_low and kw_low in text_low:
                    score += self._keyword_idf.get(kw_low, 1.0)
            # Small bonus if theme name occurs
            theme_name = (card.get("theme") or "").lower()
            if theme_name and theme_name in text_low:
                score += 0.5
            scored.append({"score": score, **card})
        scored.sort(key=lambda x: x["score"], reverse=True)
        top = [card for card in scored if card["score"] > 0][: max(1, top_k)]
        if not top:
            top = scored[: max(1, top_k)]  # fallback if nothing matched
        return [{k: v for k, v in card.items() if k != "score"} for card in top]
