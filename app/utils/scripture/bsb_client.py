"""
BSB Bible API client with simple caching.

Environment:
  - BSB_API_BASE (e.g., https://api.bereanbible.com)
  - BSB_API_KEY

Public API:
  fetch(reference: str) -> { reference, text } | None
"""

from __future__ import annotations

import os
import time
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter, Retry


class _LRUCache:
    def __init__(self, maxsize: int = 512, ttl_seconds: int = 30 * 24 * 3600) -> None:
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._store: Dict[str, tuple[float, Dict]] = {}

    def get(self, key: str) -> Optional[Dict]:
        item = self._store.get(key)
        if not item:
            return None
        ts, val = item
        if time.time() - ts > self._ttl:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, val: Dict) -> None:
        if len(self._store) >= self._maxsize:
            # drop an arbitrary item (simple LRU-ish behavior)
            self._store.pop(next(iter(self._store)))
        self._store[key] = (time.time(), val)


class BsbClient:
    def __init__(self) -> None:
        self.base = os.environ.get("BSB_API_BASE", "")
        self.key = os.environ.get("BSB_API_KEY", "")
        self.cache = _LRUCache()
        # Simple circuit breaker
        self._cb_failures = 0
        self._cb_open_until = 0.0
        self._cb_threshold = int(os.environ.get("BSB_CB_THRESHOLD", "3"))
        self._cb_cooldown = float(os.environ.get("BSB_CB_COOLDOWN_SECONDS", "30"))
        # Session with retry/backoff
        self._session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self._session.mount("http://", HTTPAdapter(max_retries=retries))
        self._session.mount("https://", HTTPAdapter(max_retries=retries))

    def fetch(self, reference: str) -> Optional[Dict[str, str]]:
        ref = reference.strip()
        if not ref:
            return None
        # Circuit breaker: if open, skip external call
        now = time.time()
        if self._cb_open_until > now:
            cached = self.cache.get(ref)
            return cached  # return cached or None when open
        cached = self.cache.get(ref)
        if cached:
            return cached
        if not self.base or not self.key:
            return None
        try:
            # Example path; adapt to your BSB provider’s API format as needed
            url = f"{self.base}/v1/passage"
            params = {"q": ref, "translation": "BSB"}
            headers = {"Authorization": f"Bearer {self.key}"}
            r = self._session.get(url, params=params, headers=headers, timeout=15)
            if r.status_code != 200:
                self._cb_failures += 1
                if self._cb_failures >= self._cb_threshold:
                    self._cb_open_until = now + self._cb_cooldown
                return None
            data = r.json()
            text = data.get("text") or data.get("passage") or ""
            if not text:
                self._cb_failures += 1
                if self._cb_failures >= self._cb_threshold:
                    self._cb_open_until = now + self._cb_cooldown
                return None
            payload = {"reference": ref, "text": text}
            self.cache.set(ref, payload)
            # Reset circuit on success
            self._cb_failures = 0
            self._cb_open_until = 0.0
            return payload
        except Exception:
            self._cb_failures += 1
            if self._cb_failures >= self._cb_threshold:
                self._cb_open_until = now + self._cb_cooldown
            return None
