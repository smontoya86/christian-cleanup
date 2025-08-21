"""
Framework Loader

Reads and parses the canonical framework documents to produce a compact
rules registry consumed by the analyzers (LLM and HF pipelines).

Sources (canonical):
- docs/christian_framework.md
- docs/biblical_discernment_v2.md

Parsing is intentionally pragmatic: we extract the Positive/Negative theme
tables, multipliers, verdict gates, and a few guardrails. If parsing fails,
we return a minimal safe default to avoid blocking analysis.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List

from flask import current_app

_CACHE: Dict[str, Any] = {
    "hash": None,
    "rules": None,
}


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        current_app.logger.warning(f"Framework read failed for {path}: {e}")
        return ""


def _extract_table(md: str, header: str) -> List[Dict[str, Any]]:
    """Extracts a simple markdown table under a header. Returns list of rows.

    Expected table format with leading pipes, columns include Theme and Points or Penalty.
    """
    # Find section by header line
    idx = md.find(header)
    if idx == -1:
        return []
    section = md[idx:]
    # Capture up to next double newline header or end
    m = re.search(r"\n\n#", section)
    if m:
        section = section[: m.start()]
    rows: List[Dict[str, Any]] = []
    # Match lines like: | Theme | Description | Scripture Anchor | +10 |
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 4:
            continue
        theme = cols[0]
        if theme.lower() in ("theme", "-------"):
            continue
        points = cols[-1]
        try:
            # Support ranges like "+2 to +5" -> take max
            num = None
            nums = re.findall(r"-?\d+", points)
            if nums:
                num = int(nums[-1])
        except Exception:
            num = None
        rows.append(
            {
                "theme": theme,
                "description": cols[1] if len(cols) > 1 else "",
                "anchor": cols[2] if len(cols) > 2 else "",
                "value": num,
                "raw_value": points,
            }
        )
    return rows


def _extract_verdict_gates(md: str) -> Dict[str, Any]:
    gates = {}
    # Simple heuristics for thresholds from the v3.1 table
    if "Freely Listen" in md:
        gates["freely_listen"] = {"purity_min": 85, "risk_max": "low"}
    if "Context Required" in md:
        gates["context_required"] = {"purity_range": [60, 84], "risk": ["high"]}
    if "Caution — Limit Exposure" in md or "Caution - Limit Exposure" in md:
        gates["caution_limit"] = {"purity_range": [40, 59], "risk": ["high", "critical"]}
    if "Avoid for Formation" in md:
        gates["avoid_formation"] = {"purity_max": 39}
    return gates


def _compact_rules() -> Dict[str, Any]:
    base = os.path.join(os.getcwd(), "docs")
    path_fw = os.path.join(base, "christian_framework.md")
    path_bd = os.path.join(base, "biblical_discernment_v2.md")
    md_fw = _read(path_fw)
    md_bd = _read(path_bd)

    digest = hashlib.sha256((md_fw + "\n" + md_bd).encode("utf-8")).hexdigest()

    pos = _extract_table(md_fw, "## ✅ Positive Themes")
    neg = _extract_table(md_fw, "## ❌ Negative Themes")
    gates = _extract_verdict_gates(md_fw)

    rules = {
        "version_hash": digest,
        "positive_themes": pos,
        "negative_themes": neg,
        "verdict_gates": gates,
        "raw": {
            "fw_len": len(md_fw),
            "bd_len": len(md_bd),
        },
    }
    return digest, rules


def get_rules(force_refresh: bool = False) -> Dict[str, Any]:
    """Return cached rules, reloading if source files changed or forced."""
    try:
        digest, rules = _compact_rules()
        if force_refresh or _CACHE["hash"] != digest:
            _CACHE["hash"] = digest
            _CACHE["rules"] = rules
            current_app.logger.info(f"Framework rules loaded (hash={digest[:8]}…)")
        return _CACHE["rules"] or rules
    except Exception as e:
        current_app.logger.error(f"Framework rule load failed: {e}")
        # Fallback minimal rules
        return {
            "version_hash": "fallback",
            "positive_themes": [],
            "negative_themes": [],
            "verdict_gates": {
                "freely_listen": {"purity_min": 85, "risk_max": "low"},
                "context_required": {"purity_range": [60, 84]},
                "caution_limit": {"purity_range": [40, 59]},
                "avoid_formation": {"purity_max": 39},
            },
        }


def get_hash() -> str:
    return _CACHE.get("hash") or "unknown"
