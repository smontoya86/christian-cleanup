"""
Rules RAG index for framework markdown documents.

Production-ready, dependency-light design:
- Uses sentence-transformers + FAISS if available (falls back to numpy cosine)
- Persists index and metadata on disk with content-hash versioning
- Thread-safe lazy load with in-process cache
- Hot-rebuild when docs change or on admin request

Env:
- ENABLE_RULES_RAG=1 to enable retrieval (otherwise no-op)
- EMBEDDING_MODEL (default sentence-transformers/all-MiniLM-L6-v2)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

INDEX_DIR = os.path.join(os.getcwd(), "data", "rag")
os.makedirs(INDEX_DIR, exist_ok=True)

DOC_PATHS = [
    os.path.join(os.getcwd(), "docs", "christian_framework.md"),
    os.path.join(os.getcwd(), "docs", "biblical_discernment_v2.md"),
]


_CACHE: Dict[str, Any] = {
    "loaded_hash": None,
    "meta": None,
    "embeddings_type": None,  # "faiss" | "numpy" | None
    "index": None,
    "model": None,
}
_LOCK = threading.RLock()


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        current_app.logger.warning(f"RAG: failed to read {path}: {e}")
        return ""


def _content_hash() -> str:
    md = "\n\n".join([_read(p) for p in DOC_PATHS])
    return hashlib.sha256(md.encode("utf-8")).hexdigest()


def _chunk_markdown(md_text: str, source: str, target_tokens: int = 400) -> List[Dict[str, Any]]:
    """Very simple chunker: split by H2/H3 headers; further split large blocks by paragraph windows."""
    chunks: List[Dict[str, Any]] = []
    if not md_text:
        return chunks
    # Normalize newlines
    text = md_text.replace("\r\n", "\n")
    # Split by headers
    import re

    parts = re.split(r"(^##\s.*$|^###\s.*$)", text, flags=re.MULTILINE)

    # parts like [pre, header1, block1, header2, block2, ...]
    def _emit(block_header: str, block_text: str) -> None:
        # secondary split by blank lines windows
        paras = [p.strip() for p in block_text.split("\n\n") if p.strip()]
        window: List[str] = []
        size = 0
        for p in paras:
            size += len(p)
            window.append(p)
            if size >= target_tokens * 4:  # rough char≈token heuristic
                chunks.append(
                    {"source": source, "header": (block_header or ""), "text": "\n\n".join(window)}
                )
                window, size = [], 0
        if window:
            chunks.append(
                {"source": source, "header": (block_header or ""), "text": "\n\n".join(window)}
            )

    header = ""
    if parts:
        # handle possible leading block
        if not parts[0].startswith("## ") and not parts[0].startswith("### "):
            _emit(header, parts[0])
        # iterate pairs
        for i in range(1, len(parts), 2):
            header = parts[i].strip()
            block = parts[i + 1] if i + 1 < len(parts) else ""
            _emit(header, block)
    else:
        chunks.append({"source": source, "header": "", "text": text})
    return chunks


def _load_embed_stack():
    from sentence_transformers import SentenceTransformer  # type: ignore

    try:
        import faiss  # type: ignore
    except Exception:
        faiss = None
    model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    return model, faiss


def _persist_paths(chash: str) -> Tuple[str, str, str]:
    meta_path = os.path.join(INDEX_DIR, f"rules-{chash}.meta.json")
    faiss_path = os.path.join(INDEX_DIR, f"rules-{chash}.faiss")
    npy_path = os.path.join(INDEX_DIR, f"rules-{chash}.npy")
    return meta_path, faiss_path, npy_path


def build_index(force: bool = False) -> Dict[str, Any]:
    if os.environ.get("ENABLE_RULES_RAG", "0") not in ("1", "true", "True"):
        return {"enabled": False, "message": "RAG disabled via env"}
    chash = _content_hash()
    meta_path, faiss_path, npy_path = _persist_paths(chash)

    with _LOCK:
        if (
            not force
            and os.path.exists(meta_path)
            and (os.path.exists(faiss_path) or os.path.exists(npy_path))
        ):
            _CACHE["loaded_hash"] = chash
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    _CACHE["meta"] = json.load(f)
            except Exception:
                _CACHE["meta"] = {"chunks": []}
            return {
                "enabled": True,
                "built": False,
                "hash": chash,
                "chunks": len((_CACHE["meta"] or {}).get("chunks", [])),
            }

        # Build new index
        try:
            current_app.logger.info("[RAG] building rules index…")
            model, faiss = _load_embed_stack()
            all_chunks: List[Dict[str, Any]] = []
            for p in DOC_PATHS:
                all_chunks.extend(_chunk_markdown(_read(p), os.path.basename(p)))
            texts = [f"{c['header']}\n{c['text']}".strip() for c in all_chunks]
            embs = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

            embeddings_type: Optional[str] = None
            index = None
            if faiss is not None:
                dim = embs.shape[1]
                index = faiss.IndexFlatIP(dim)
                index.add(embs)
                embeddings_type = "faiss"
                import faiss as _fa  # type: ignore

                _fa.write_index(index, faiss_path)
            else:
                import numpy as np  # type: ignore

                np.save(npy_path, embs)
                embeddings_type = "numpy"

            meta = {
                "hash": chash,
                "chunks": all_chunks,
                "model": os.environ.get(
                    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
                ),
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f)

            _CACHE.update(
                {
                    "loaded_hash": chash,
                    "meta": meta,
                    "embeddings_type": embeddings_type,
                    "index": index,
                    "model": model,
                }
            )
            current_app.logger.info(
                f"[RAG] built index hash={chash[:8]}… chunks={len(all_chunks)} type={embeddings_type}"
            )
            return {
                "enabled": True,
                "built": True,
                "hash": chash,
                "chunks": len(all_chunks),
                "embeddings_type": embeddings_type,
            }
        except Exception as e:
            current_app.logger.error(f"RAG build failed: {e}")
            return {"enabled": False, "error": str(e)}


def _ensure_loaded() -> bool:
    if os.environ.get("ENABLE_RULES_RAG", "0") not in ("1", "true", "True"):
        return False
    chash = _content_hash()
    meta_path, faiss_path, npy_path = _persist_paths(chash)
    with _LOCK:
        if _CACHE.get("loaded_hash") == chash and _CACHE.get("meta") is not None:
            return True
        # Load
        if not os.path.exists(meta_path) or (
            not os.path.exists(faiss_path) and not os.path.exists(npy_path)
        ):
            build_index(force=True)
        try:
            model, faiss = _load_embed_stack()
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            index = None
            embeddings_type = None
            if os.path.exists(faiss_path) and faiss is not None:
                import faiss as _fa  # type: ignore

                index = _fa.read_index(faiss_path)
                embeddings_type = "faiss"
            elif os.path.exists(npy_path):
                import numpy as np  # type: ignore

                index = np.load(npy_path)
                embeddings_type = "numpy"
            else:
                return False
            _CACHE.update(
                {
                    "loaded_hash": chash,
                    "meta": meta,
                    "embeddings_type": embeddings_type,
                    "index": index,
                    "model": model,
                }
            )
            current_app.logger.info(
                f"[RAG] loaded index hash={chash[:8]}… chunks={len((meta or {}).get('chunks', []))} type={embeddings_type}"
            )
            return True
        except Exception as e:
            current_app.logger.error(f"RAG load failed: {e}")
            return False


def retrieve_rules(query_text: str, top_k: int = 6) -> List[Dict[str, Any]]:
    if not _ensure_loaded():
        return []
    try:
        import numpy as np  # type: ignore
    except Exception:
        return []
    with _LOCK:
        model = _CACHE.get("model")
        index = _CACHE.get("index")
        meta = _CACHE.get("meta") or {}
        etype = _CACHE.get("embeddings_type")
        if not model or index is None:
            return []
        emb = model.encode([query_text], normalize_embeddings=True, convert_to_numpy=True)
        if etype == "faiss":  # pragma: no cover
            D, I = index.search(emb, top_k)
            idxs = [int(i) for i in I[0] if i >= 0]
        else:
            scores = np.dot(index, emb[0])
            order = np.argsort(-scores)[: max(1, top_k)]
            idxs = [int(i) for i in order]
        chunks: List[Dict[str, Any]] = meta.get("chunks") or []
        out: List[Dict[str, Any]] = []
        for i in idxs:
            if 0 <= i < len(chunks):
                out.append(chunks[i])
        return out


def status() -> Dict[str, Any]:
    chash = _content_hash()
    with _LOCK:
        return {
            "enabled": os.environ.get("ENABLE_RULES_RAG", "0") in ("1", "true", "True"),
            "current_hash": chash,
            "loaded_hash": _CACHE.get("loaded_hash"),
            "embeddings_type": _CACHE.get("embeddings_type"),
            "chunks": len(((_CACHE.get("meta") or {}).get("chunks", [])))
            if _CACHE.get("meta")
            else 0,
        }
