import argparse
import json
import csv
from typing import Any, Dict, List

from app import create_app
from app.models.models import db, Song, AnalysisResult


def _extract_flags(concerns: Any) -> List[str]:
    if not concerns:
        return []
    out: List[str] = []
    if isinstance(concerns, list):
        for c in concerns:
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, dict):
                out.append(c.get("category") or c.get("type") or "")
    return [x for x in out if x]


def _extract_flags_with_fallback(latest: Any) -> List[str]:
    """Extract flags from the primary concerns field, falling back to purity_flags_details.

    Handles both list-of-strings and list-of-dicts forms.
    """
    # Primary source: concerns (already normalized to strings in many cases)
    flags = _extract_flags(getattr(latest, "concerns", []) if latest else [])
    if flags:
        return flags
    # Fallback: purity_flags_details (list of dicts with 'type' or 'category')
    pfd = getattr(latest, "purity_flags_details", []) if latest else []
    if isinstance(pfd, list):
        flags = []
        for item in pfd:
            if isinstance(item, dict):
                t = item.get("type") or item.get("category") or ""
                if t:
                    flags.append(t)
            elif isinstance(item, str):
                flags.append(item)
        return [x for x in flags if x]
    return []


def _extract_scripture_refs(supporting: Any) -> List[str]:
    if not supporting:
        return []
    out: List[str] = []
    if isinstance(supporting, list):
        for s in supporting:
            if isinstance(s, str):
                out.append(s)
            elif isinstance(s, dict):
                ref = s.get("reference") or s.get("ref")
                if ref:
                    out.append(ref)
    return out


def _map_score_to_verdict(score: float) -> str:
    """Map numeric score to framework verdict tiers.

    Aligns with eval runner thresholds to ensure consistency.
    """
    try:
        s = float(score)
    except Exception:
        return None  # type: ignore

    if s >= 85:
        return "freely_listen"
    if s >= 60:
        return "context_required"
    if s >= 40:
        return "caution_limit"
    return "avoid_formation"


def _map_score_to_concern_level(score: float) -> str:
    """Map numeric score to concern level bands (Low/Medium/High)."""
    try:
        s = float(score)
    except Exception:
        return None  # type: ignore

    if s >= 60:
        return "Low"
    if s >= 40:
        return "Medium"
    return "High"


def _derive_formation_risk(concern_level: Any) -> Any:
    """Derive formation_risk from concern level when missing.

    Mapping aligned with analyzer: Low->low, Medium->high, High->critical.
    """
    if not concern_level:
        return None
    cl = str(concern_level).strip().lower()
    if cl in ("very low", "very_low"):
        return "very_low"
    if cl == "low":
        return "low"
    if cl == "medium":
        return "high"
    if cl == "high" or cl == "critical":
        return "critical"
    return None


def _extract_scripture_refs_with_fallback(latest: Any) -> List[str]:
    """Extract scripture references with fallback to biblical_themes."""
    # Primary: supporting_scripture
    refs = _extract_scripture_refs(getattr(latest, "supporting_scripture", [])) if latest else []
    if refs:
        return refs
    # Fallback: biblical_themes may contain nested references
    bt = getattr(latest, "biblical_themes", []) if latest else []
    out: List[str] = []
    if isinstance(bt, list):
        for item in bt:
            if isinstance(item, dict):
                # common keys: reference/ref or a list under verses/scripture
                r = item.get("reference") or item.get("ref")
                if r:
                    out.append(r)
                verses = item.get("verses") or item.get("scripture")
                if isinstance(verses, list):
                    for v in verses:
                        if isinstance(v, dict):
                            rr = v.get("reference") or v.get("ref")
                            if rr:
                                out.append(rr)
                        elif isinstance(v, str):
                            out.append(v)
            elif isinstance(item, str):
                out.append(item)
    # de-dup
    seen = set()
    uniq = []
    for r in out:
        if r and r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq

def export(limit: int, out_prefix: str) -> Dict[str, Any]:
    app = create_app()
    results: List[Dict[str, Any]] = []
    with app.app_context():
        songs: List[Song] = (
            Song.query.filter(
                Song.lyrics.isnot(None), db.func.length(db.func.trim(Song.lyrics)) > 0
            )
            .order_by(Song.updated_at.desc())
            .limit(limit)
            .all()
        )
        for s in songs:
            latest: AnalysisResult = (
                AnalysisResult.query.filter_by(song_id=s.id)  # All stored analyses are completed
                .order_by(AnalysisResult.analyzed_at.desc())
                .first()
            )
            expected_verdict = latest.verdict if latest and getattr(latest, "verdict", None) else None
            expected_score = latest.score if latest else None
            expected_flags = _extract_flags_with_fallback(latest)
            expected_scripture_refs = _extract_scripture_refs_with_fallback(latest)

            # Backfill verdict from score if missing
            if expected_verdict in (None, "", "null") and expected_score is not None:
                expected_verdict = _map_score_to_verdict(expected_score)

            # Concern level with fallback from score
            expected_concern_level = getattr(latest, "concern_level", None) if latest else None
            if (not expected_concern_level) and expected_score is not None:
                expected_concern_level = _map_score_to_concern_level(expected_score)

            # Detailed objects (leave None if DB lacks them)
            expected_biblical_themes = getattr(latest, "biblical_themes", None) if latest else None
            expected_supporting_scripture_detailed = (
                getattr(latest, "supporting_scripture", None) if latest else None
            )
            expected_positive_themes = (
                getattr(latest, "positive_themes_identified", None) if latest else None
            )
            expected_purity_flags_details = (
                getattr(latest, "purity_flags_details", None) if latest else None
            )
            expected_narrative_voice = getattr(latest, "narrative_voice", None) if latest else None
            expected_lament_filter_applied = (
                getattr(latest, "lament_filter_applied", None) if latest else None
            )
            expected_doctrinal_clarity = (
                getattr(latest, "doctrinal_clarity", None) if latest else None
            )
            expected_confidence = getattr(latest, "confidence", None) if latest else None
            expected_needs_review = getattr(latest, "needs_review", None) if latest else None
            expected_formation_risk = getattr(latest, "formation_risk", None) if latest else None
            if not expected_formation_risk and expected_concern_level:
                expected_formation_risk = _derive_formation_risk(expected_concern_level)
            entry = {
                "id": f"db-{s.id}",
                "title": s.title,
                "artist": s.artist,
                "lyrics": s.lyrics or "",
                "expected_verdict": expected_verdict,
                "expected_score": expected_score,
                "expected_flags": expected_flags,
                "expected_scripture_refs": expected_scripture_refs,
                # Extended expected fields
                "expected_concern_level": expected_concern_level,
                "expected_biblical_themes": expected_biblical_themes,
                "expected_supporting_scripture_detailed": expected_supporting_scripture_detailed,
                "expected_positive_themes": expected_positive_themes,
                "expected_purity_flags_details": expected_purity_flags_details,
                "expected_narrative_voice": expected_narrative_voice,
                "expected_lament_filter_applied": expected_lament_filter_applied,
                "expected_doctrinal_clarity": expected_doctrinal_clarity,
                "expected_confidence": expected_confidence,
                "expected_needs_review": expected_needs_review,
                "expected_formation_risk": expected_formation_risk,
                # No model_json here; this export is ground truth from DB
            }
            results.append(entry)

    # Write files
    jsonl_path = f"{out_prefix}.jsonl"
    json_path = f"{out_prefix}.json"
    csv_path = f"{out_prefix}.csv"

    with open(jsonl_path, "w", encoding="utf-8") as jf:
        for e in results:
            jf.write(json.dumps(e, ensure_ascii=False) + "\n")

    with open(json_path, "w", encoding="utf-8") as jpf:
        json.dump(results, jpf, indent=2, ensure_ascii=False)

    headers = [
        "id",
        "title",
        "artist",
        "lyrics",
        "expected_verdict",
        "expected_score",
        "expected_flags",
        "expected_scripture_refs",
        # Extended expected fields
        "expected_concern_level",
        "expected_biblical_themes",
        "expected_supporting_scripture_detailed",
        "expected_positive_themes",
        "expected_purity_flags_details",
        "expected_narrative_voice",
        "expected_lament_filter_applied",
        "expected_doctrinal_clarity",
        "expected_confidence",
        "expected_needs_review",
        "expected_formation_risk",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        w = csv.writer(cf)
        w.writerow(headers)
        for e in results:
            w.writerow(
                [
                    e.get("id"),
                    e.get("title"),
                    e.get("artist"),
                    (e.get("lyrics") or "").replace("\n", " ").strip(),
                    e.get("expected_verdict"),
                    e.get("expected_score"),
                    json.dumps(e.get("expected_flags") or []),
                    json.dumps(e.get("expected_scripture_refs") or []),
                    # Extended
                    e.get("expected_concern_level"),
                    json.dumps(e.get("expected_biblical_themes") or []),
                    json.dumps(e.get("expected_supporting_scripture_detailed") or []),
                    json.dumps(e.get("expected_positive_themes") or []),
                    json.dumps(e.get("expected_purity_flags_details") or []),
                    e.get("expected_narrative_voice"),
                    json.dumps(e.get("expected_lament_filter_applied") if e.get("expected_lament_filter_applied") is not None else None),
                    e.get("expected_doctrinal_clarity"),
                    e.get("expected_confidence"),
                    json.dumps(e.get("expected_needs_review") if e.get("expected_needs_review") is not None else None),
                    e.get("expected_formation_risk"),
                ]
            )

    return {"count": len(results), "jsonl": jsonl_path, "json": json_path, "csv": csv_path}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=10)
    p.add_argument(
        "--out",
        default="scripts/eval/reports/db_gpt_review_inputs",
        help="Output file prefix (without extension)",
    )
    args = p.parse_args()
    stats = export(args.limit, args.out)
    print(json.dumps(stats))
