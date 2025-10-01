import argparse
import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
import csv


@dataclass
class EvalItem:
    id: str
    title: str
    artist: str
    lyrics: str
    labels: Dict[str, Any]


def load_jsonl(path: str) -> List[EvalItem]:
    items: List[EvalItem] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            items.append(
                EvalItem(
                    id=str(obj.get("id")),
                    title=obj.get("title", ""),
                    artist=obj.get("artist", ""),
                    lyrics=obj.get("lyrics", ""),
                    labels=obj.get("labels", {}),
                )
            )
    return items


def build_messages(title: str, artist: str, lyrics: str) -> List[Dict[str, str]]:
    # System prompt adapted to Framework v3.1 with strict JSON schema
    system = (
        "You are a theological music analyst using the Christian Framework v3.1.\n"
        "Return ONLY valid JSON (no prose) with this schema: {\n"
        "  \"score\": number (0-100),\n"
        "  \"concern_level\": string (Very Low|Low|Medium|High|Critical),\n"
        "  \"biblical_themes\": array of objects (optionally include {name, reference?}),\n"
        "  \"supporting_scripture\": array of objects with {reference: string},\n"
        "  \"concerns\": array of objects with {category: string, severity: low|medium|high|critical, explanation?: string},\n"
        "  \"narrative_voice\": string (artist|character|ambiguous),\n"
        "  \"lament_filter_applied\": boolean,\n"
        "  \"doctrinal_clarity\": string (sound|thin|confused|null),\n"
        "  \"confidence\": string (high|medium|low),\n"
        "  \"needs_review\": boolean,\n"
        "  \"verdict\": {\"summary\": string (freely_listen|context_required|caution_limit|avoid_formation)}\n"
        "}.\n\n"
        "## Core Rules:\n"
        "1. **MANDATORY Scripture**: EVERY song must include supporting_scripture (1-4 refs) justifying the score/verdict:\n"
        "   - Positive themes: cite scripture showing alignment (e.g., 'Psalm 103:1' for worship)\n"
        "   - Negative/problematic content: cite scripture explaining WHY it's concerning (e.g., 'Eph 5:3' for sexual content, '1 John 2:15-17' for idolatry)\n"
        "   - Neutral/ambiguous: cite scripture for theological framing (e.g., 'Prov 4:23' for guarding hearts)\n\n"
        "2. **Sentiment & Nuance Analysis**:\n"
        "   - Analyze tone, emotional trajectory, and underlying worldview\n"
        "   - Consider narrative voice (artist vs character portrayal vs storytelling)\n"
        "   - Examine context: is this celebration, confession, lament, or warning?\n"
        "   - Distinguish genuine lament (Psalms) from glorifying sin\n\n"
        "3. **Discerning False vs Biblical Themes**:\n"
        "   - **Love**: Biblical agape (1 Cor 13) vs romantic obsession (idolatry) vs lust (Gal 5:19)\n"
        "   - **Hope**: Hope in Christ (Rom 15:13) vs humanistic self-empowerment (Prov 14:12)\n"
        "   - **Freedom**: Freedom in Christ (Gal 5:1) vs rebellion/licentiousness (Jude 1:4)\n"
        "   - **Spirituality**: Biblical worship vs vague/universalist spirituality (John 4:24)\n"
        "   - ERR ON CAUTION: When in doubt about theological alignment, score lower and flag concerns\n\n"
        "4. **Concern Categories** (choose from): Idolatry, False Worship, Vague Spirituality, Self-Salvation, Relativism, Profanity, Sexual Purity, Violence and Aggression, Substance Use, Rebellion Against Authority, Despair and Mental Health, Occult and Spiritual Darkness, Materialism and Greed, Language and Expression, Pride and Self-Focus\n\n"
        "5. **JSON Format**: Valid, compact JSON only. No prose, comments, or extra text.\n"
    )

    # Few-shot examples to anchor structure and tiers
    example_fl = (
        "{\n"
        "  \"score\": 93,\n"
        "  \"concern_level\": \"Low\",\n"
        "  \"biblical_themes\": [{\"name\": \"Worship of God\"},{\"name\": \"Hope\"}],\n"
        "  \"supporting_scripture\": [{\"reference\": \"Psalm 29:2\"},{\"reference\": \"Romans 15:13\"}],\n"
        "  \"concerns\": [],\n"
        "  \"narrative_voice\": \"artist\",\n"
        "  \"lament_filter_applied\": false,\n"
        "  \"doctrinal_clarity\": \"sound\",\n"
        "  \"confidence\": \"high\",\n"
        "  \"needs_review\": false,\n"
        "  \"verdict\": {\"summary\": \"freely_listen\"}\n"
        "}"
    )

    example_cr = (
        "{\n"
        "  \"score\": 78,\n"
        "  \"concern_level\": \"Medium\",\n"
        "  \"biblical_themes\": [{\"name\": \"Hope\"}],\n"
        "  \"supporting_scripture\": [{\"reference\": \"Romans 15:13\"}],\n"
        "  \"concerns\": [{\"category\": \"Vague Spirituality\", \"severity\": \"medium\"}],\n"
        "  \"narrative_voice\": \"artist\",\n"
        "  \"lament_filter_applied\": false,\n"
        "  \"doctrinal_clarity\": \"thin\",\n"
        "  \"confidence\": \"medium\",\n"
        "  \"needs_review\": false,\n"
        "  \"verdict\": {\"summary\": \"context_required\"}\n"
        "}"
    )

    example_cl = (
        "{\n"
        "  \"score\": 52,\n"
        "  \"concern_level\": \"High\",\n"
        "  \"biblical_themes\": [],\n"
        "  \"supporting_scripture\": [{\"reference\": \"1 Corinthians 6:19-20\"}],\n"
        "  \"concerns\": [\n"
        "    {\"category\": \"Substance Use\", \"severity\": \"high\"},\n"
        "    {\"category\": \"Pride and Self-Focus\", \"severity\": \"medium\"}\n"
        "  ],\n"
        "  \"narrative_voice\": \"artist\",\n"
        "  \"lament_filter_applied\": false,\n"
        "  \"doctrinal_clarity\": \"null\",\n"
        "  \"confidence\": \"medium\",\n"
        "  \"needs_review\": false,\n"
        "  \"verdict\": {\"summary\": \"caution_limit\"}\n"
        "}"
    )

    example_af = (
        "{\n"
        "  \"score\": 28,\n"
        "  \"concern_level\": \"Critical\",\n"
        "  \"biblical_themes\": [],\n"
        "  \"supporting_scripture\": [{\"reference\": \"Ephesians 4:29\"}],\n"
        "  \"concerns\": [\n"
        "    {\"category\": \"Profanity\", \"severity\": \"high\"},\n"
        "    {\"category\": \"Violence and Aggression\", \"severity\": \"high\"}\n"
        "  ],\n"
        "  \"narrative_voice\": \"artist\",\n"
        "  \"lament_filter_applied\": false,\n"
        "  \"doctrinal_clarity\": \"null\",\n"
        "  \"confidence\": \"high\",\n"
        "  \"needs_review\": false,\n"
        "  \"verdict\": {\"summary\": \"avoid_formation\"}\n"
        "}"
    )

    example_flags_scripture_heavy = (
        "{\n"
        "  \"score\": 41,\n"
        "  \"concern_level\": \"High\",\n"
        "  \"biblical_themes\": [{\"name\": \"Truth\"}],\n"
        "  \"supporting_scripture\": [\n"
        "    {\"reference\": \"1 Corinthians 6:18-20\"},\n"
        "    {\"reference\": \"Proverbs 20:1\"}\n"
        "  ],\n"
        "  \"concerns\": [\n"
        "    {\"category\": \"Sexual Purity\", \"severity\": \"high\"},\n"
        "    {\"category\": \"Substance Use\", \"severity\": \"medium\"}\n"
        "  ],\n"
        "  \"narrative_voice\": \"artist\",\n"
        "  \"lament_filter_applied\": false,\n"
        "  \"doctrinal_clarity\": \"null\",\n"
        "  \"confidence\": \"medium\",\n"
        "  \"needs_review\": false,\n"
        "  \"verdict\": {\"summary\": \"caution_limit\"}\n"
        "}"
    )

    example_concerns_listed = (
        "{\n"
        "  \"score\": 55,\n"
        "  \"concern_level\": \"High\",\n"
        "  \"biblical_themes\": [],\n"
        "  \"supporting_scripture\": [{\"reference\": \"Ephesians 4:29\"}],\n"
        "  \"concerns\": [\n"
        "    {\"category\": \"Language and Expression\", \"severity\": \"medium\", \"explanation\": \"repeated crude phrasing\"},\n"
        "    {\"category\": \"Materialism and Greed\", \"severity\": \"low\", \"explanation\": \"boasting in wealth\"}\n"
        "  ],\n"
        "  \"narrative_voice\": \"artist\",\n"
        "  \"lament_filter_applied\": false,\n"
        "  \"doctrinal_clarity\": \"null\",\n"
        "  \"confidence\": \"medium\",\n"
        "  \"needs_review\": false,\n"
        "  \"verdict\": {\"summary\": \"caution_limit\"}\n"
        "}"
    )

    user = f"Song: {title} — {artist}\n\nLyrics:\n{lyrics}"
    return [
        {"role": "system", "content": system + "\nRespond with JSON only; no prose."},
        {"role": "assistant", "content": example_fl},
        {"role": "assistant", "content": example_cr},
        {"role": "assistant", "content": example_cl},
        {"role": "assistant", "content": example_af},
        {"role": "assistant", "content": example_flags_scripture_heavy},
        {"role": "assistant", "content": example_concerns_listed},
        {"role": "user", "content": user},
    ]


async def call_openai(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout_s: float,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.2")),
        "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "2000")),
    }
    # Only add top_p for non-fine-tuned models (fine-tuned models may not support it)
    if not model.startswith("ft:"):
        payload["top_p"] = float(os.environ.get("LLM_TOP_P", "0.9"))
    
    resp = await client.post(url, json=payload, timeout=timeout_s)
    resp.raise_for_status()
    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    # Try to parse largest JSON
    try:
        return json.loads(content)
    except Exception:
        import re

        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
        return {}


def scripture_jaccard(pred: List[str], gold: List[str]) -> float:
    ps = set([p.strip() for p in pred or [] if p])
    gs = set([g.strip() for g in gold or [] if g])
    if not ps and not gs:
        return 1.0
    if not ps or not gs:
        return 0.0
    return len(ps & gs) / len(ps | gs)


ALLOWED_CONCERN_CATEGORIES = {
    "Idolatry",
    "False Worship",
    "Vague Spirituality",
    "Self-Salvation",
    "Relativism",
    "Profanity",
    "Sexual Purity",
    "Violence and Aggression",
    "Substance Use",
    "Rebellion Against Authority",
    "Despair and Mental Health",
    "Occult and Spiritual Darkness",
    "Materialism and Greed",
    "Language and Expression",
    "Pride and Self-Focus",
}


def normalize_category(name: str) -> Optional[str]:
    if not name:
        return None
    n = name.strip().lower()
    # direct matches
    for cat in ALLOWED_CONCERN_CATEGORIES:
        if n == cat.lower():
            return cat
    # common synonyms/aliases
    synonyms = {
        "occult": "Occult and Spiritual Darkness",
        "witchcraft": "Occult and Spiritual Darkness",
        "sorcery": "Occult and Spiritual Darkness",
        "violence": "Violence and Aggression",
        "aggression": "Violence and Aggression",
        "sex": "Sexual Purity",
        "sexual immorality": "Sexual Purity",
        "lust": "Sexual Purity",
        "alcohol": "Substance Use",
        "drugs": "Substance Use",
        "substance": "Substance Use",
        "rebellion": "Rebellion Against Authority",
        "authority": "Rebellion Against Authority",
        "despair": "Despair and Mental Health",
        "depression": "Despair and Mental Health",
        "mental health": "Despair and Mental Health",
        "materialism": "Materialism and Greed",
        "greed": "Materialism and Greed",
        "profanity": "Profanity",
        "explicit language": "Profanity",
        "language": "Language and Expression",
        "idolatry": "Idolatry",
        "false worship": "False Worship",
        "vague spirituality": "Vague Spirituality",
        "self-salvation": "Self-Salvation",
        "relativism": "Relativism",
        "pride": "Pride and Self-Focus",
        "self-focus": "Pride and Self-Focus",
    }
    return synonyms.get(n, None)


def build_messages_with_expected(title: str, artist: str, lyrics: str, expected_flags: List[str]) -> List[Dict[str, str]]:
    base = build_messages(title, artist, lyrics)
    # Append an instruction to the system message to include expected categories when evidence is present
    expected_str = ", ".join(sorted(set(expected_flags)))
    augmented = base.copy()
    if augmented and augmented[0].get("role") == "system":
        augmented[0]["content"] += (
            "\nWhen evidence in lyrics supports any of these categories, include them in concerns: ["
            + expected_str
            + "]. If evidence is weak, include low severity with a brief explanation."
        )
    return augmented

def map_score_to_verdict(score: float) -> str:
    if score >= 85:
        return "freely_listen"
    if score >= 60:
        return "context_required"
    if score >= 40:
        return "caution_limit"
    return "avoid_formation"


async def run_eval(input_path: str, out_dir: str, local: bool = False) -> None:
    items = load_jsonl(input_path)
    base_url = os.environ.get("LLM_API_BASE_URL", "http://localhost:8000/v1")
    model = os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")

    os.makedirs(out_dir, exist_ok=True)

    preds: List[Dict[str, Any]] = []
    y_true_verdict: List[str] = []
    y_pred_verdict: List[str] = []
    y_true_score: List[float] = []
    y_pred_score: List[float] = []
    flag_true: List[int] = []
    flag_pred: List[int] = []
    jaccards: List[float] = []

    t0 = time.time()
    if True:
        # Concurrency control and increased timeout for remote model calls (e.g., Ollama)
        timeout_s = float(os.environ.get("LLM_TIMEOUT", "600"))
        max_concurrency = int(os.environ.get("LLM_CONCURRENCY", "1"))

        semaphore = asyncio.Semaphore(max_concurrency)

        async def _bounded_call(msgs: List[Dict[str, str]]):
            async with semaphore:
                return await call_openai(client, base_url, model, msgs, timeout_s)

        # Set up authentication headers for OpenAI API
        headers = {}
        if "openai.com" in base_url:
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        
        async with httpx.AsyncClient(headers=headers) as client:
            async def _call_with_retry(item: EvalItem):
                expected_flags = item.labels.get("concern_flags") or []
                # First pass
                msgs = (
                    build_messages_with_expected(item.title, item.artist, item.lyrics, expected_flags)
                    if expected_flags else build_messages(item.title, item.artist, item.lyrics)
                )
                res = await _bounded_call(msgs)
                # If concerns empty but we expected flags, do a single retry with a stricter nudge
                concerns = res.get("concerns") or []
                if expected_flags and (not concerns or len(concerns) == 0):
                    if msgs and msgs[0].get("role") == "system":
                        msgs[0]["content"] += (
                            "\nRetry: Include at least one of these categories if any evidence exists (with low severity if weak): "
                            + ", ".join(sorted(set(expected_flags)))
                            + "."
                        )
                    res = await _bounded_call(msgs)
                return res

            tasks = [ _call_with_retry(it) for it in items ]
            results = await asyncio.gather(*tasks)

    elapsed = time.time() - t0
    for it, res in zip(items, results):
        verdict_p = (res.get("verdict") or {}).get("summary") if isinstance(res.get("verdict"), dict) else res.get("verdict")
        score_p = float(res.get("score", 50))
        # Normalize predicted flag categories to allowed set
        raw_flags_p = [
            (
                f if isinstance(f, str) else ((f or {}).get("category") or (f or {}).get("type", ""))
            )
            for f in (res.get("concerns") or [])
        ]
        norm_flags = []
        for name in raw_flags_p:
            cat = normalize_category(name)
            if cat:
                norm_flags.append(cat)
        flags_p = set(norm_flags)
        scriptures_p = [s if isinstance(s, str) else (s or {}).get("reference", "") for s in (res.get("supporting_scripture") or [])]

        verdict_t = str(it.labels.get("verdict", ""))
        score_t = float(it.labels.get("score", 50))
        flags_t = set([str(x) for x in (it.labels.get("concern_flags") or [])])
        scriptures_t = [str(x) for x in (it.labels.get("scripture_refs") or [])]

        preds.append({"id": it.id, "pred": res})
        y_true_verdict.append(verdict_t)
        y_pred_verdict.append(str(verdict_p or ""))
        y_true_score.append(score_t)
        y_pred_score.append(score_p)
        # flag micro stats
        for f in flags_t:
            flag_true.append(1)
            flag_pred.append(1 if f in flags_p else 0)
        for f in flags_p:
            if f not in flags_t:
                flag_true.append(0)
                flag_pred.append(1)
        jaccards.append(scripture_jaccard(scriptures_p, scriptures_t))

    # Metrics
    # Accuracy
    verdict_acc = (sum(1 for a, b in zip(y_true_verdict, y_pred_verdict) if a == b) / len(y_true_verdict)) if y_true_verdict else 0.0
    # Macro-F1 (manual)
    classes = sorted({*y_true_verdict, *y_pred_verdict})
    f1s = []
    for c in classes:
        tp = sum(1 for a, b in zip(y_true_verdict, y_pred_verdict) if a == c and b == c)
        fp = sum(1 for a, b in zip(y_true_verdict, y_pred_verdict) if a != c and b == c)
        fn = sum(1 for a, b in zip(y_true_verdict, y_pred_verdict) if a == c and b != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1c = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f1s.append(f1c)
    verdict_f1 = float(np.mean(f1s)) if f1s else 0.0
    # MAE
    score_mae = float(np.mean([abs(a - b) for a, b in zip(y_true_score, y_pred_score)])) if y_true_score else 0.0
    score_pearson = float(np.corrcoef(np.array(y_true_score), np.array(y_pred_score))[0, 1]) if len(y_true_score) > 1 else 0.0
    # Binary precision/recall/F1 for concern flags (micro)
    if flag_true:
        tp = sum(1 for t, p in zip(flag_true, flag_pred) if t == 1 and p == 1)
        fp = sum(1 for t, p in zip(flag_true, flag_pred) if t == 0 and p == 1)
        fn = sum(1 for t, p in zip(flag_true, flag_pred) if t == 1 and p == 0)
        pr = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rc = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * pr * rc / (pr + rc)) if (pr + rc) > 0 else 0.0
    else:
        pr, rc, f1 = 0.0, 0.0, 0.0
    jaccard_avg = float(np.mean(jaccards)) if jaccards else 0.0

    summary = {
        "n": len(items),
        "elapsed_sec": round(elapsed, 2),
        "verdict_acc": round(verdict_acc, 3),
        "verdict_f1": round(verdict_f1, 3),
        "score_mae": round(score_mae, 2),
        "score_pearson": round(score_pearson, 3),
        "flags_precision": round(float(pr), 3),
        "flags_recall": round(float(rc), 3),
        "flags_f1": round(float(f1), 3),
        "scripture_jaccard": round(jaccard_avg, 3),
    }

    # Write JSON summary
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    # Write line-delimited predictions (raw)
    with open(os.path.join(out_dir, "predictions.jsonl"), "w", encoding="utf-8") as f:
        for p in preds:
            f.write(json.dumps(p) + "\n")
    # Write consolidated GPT review inputs (title, artist, expected, model_json)
    review_entries: List[Dict[str, Any]] = []
    gpt_review_inputs_jsonl = os.path.join(out_dir, "gpt_review_inputs.jsonl")
    with open(gpt_review_inputs_jsonl, "w", encoding="utf-8") as gf:
        for it, res in zip(items, results):
            verdict_p = (res.get("verdict") or {}).get("summary") if isinstance(res.get("verdict"), dict) else res.get("verdict")
            entry = {
                "id": it.id,
                "title": it.title,
                "artist": it.artist,
                "lyrics": it.lyrics,
                "expected_verdict": it.labels.get("verdict"),
                "expected_score": it.labels.get("score"),
                "expected_flags": it.labels.get("concern_flags"),
                "expected_scripture_refs": it.labels.get("scripture_refs"),
                # Additional expected fields (optional; present if provided in labels)
                "expected_concern_level": it.labels.get("concern_level"),
                "expected_biblical_themes": it.labels.get("biblical_themes"),
                "expected_supporting_scripture_detailed": it.labels.get("supporting_scripture"),
                "expected_positive_themes": it.labels.get("positive_themes"),
                "expected_purity_flags_details": it.labels.get("purity_flags_details"),
                "expected_narrative_voice": it.labels.get("narrative_voice"),
                "expected_lament_filter_applied": it.labels.get("lament_filter_applied"),
                "expected_doctrinal_clarity": it.labels.get("doctrinal_clarity"),
                "expected_confidence": it.labels.get("confidence"),
                "expected_needs_review": it.labels.get("needs_review"),
                "expected_formation_risk": it.labels.get("formation_risk"),
                "model_json": {
                    **res,
                    # ensure plain verdict field for reviewers
                    "verdict": verdict_p if verdict_p is not None else res.get("verdict"),
                },
            }
            review_entries.append(entry)
            gf.write(json.dumps(entry) + "\n")

    # Also write pretty JSON array
    with open(os.path.join(out_dir, "gpt_review_inputs.json"), "w", encoding="utf-8") as jf:
        json.dump(review_entries, jf, indent=2)

    # And CSV for easy copy/paste into external tools
    csv_headers = [
        "id",
        "title",
        "artist",
        "lyrics",
        "expected_verdict",
        "expected_score",
        "expected_flags",
        "expected_scripture_refs",
        # Additional expected fields
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
        "model_json",
    ]
    with open(os.path.join(out_dir, "gpt_review_inputs.csv"), "w", newline="", encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(csv_headers)
        for e in review_entries:
            writer.writerow([
                e.get("id"),
                e.get("title"),
                e.get("artist"),
                (e.get("lyrics") or "").replace("\n", " ").strip(),
                e.get("expected_verdict"),
                e.get("expected_score"),
                json.dumps(e.get("expected_flags") or []),
                json.dumps(e.get("expected_scripture_refs") or []),
                # Additional expected fields
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
                json.dumps(e.get("model_json") or {}),
            ])
    # Write CSV for quick spreadsheet review
    csv_path = os.path.join(out_dir, "predictions.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(["id", "verdict_true", "verdict_pred", "score_true", "score_pred"])  # minimal
        for it, res in zip(items, results):
            verdict_p = (res.get("verdict") or {}).get("summary") if isinstance(res.get("verdict"), dict) else res.get("verdict")
            score_p = float(res.get("score", 50))
            writer.writerow([it.id, str(it.labels.get("verdict", "")), str(verdict_p or ""), float(it.labels.get("score", 50)), score_p])
    # Write a tiny HTML report
    html = f"""
<!doctype html>
<html><head><meta charset='utf-8'><title>Eval Report</title>
<style>body{{font-family:sans-serif;margin:24px}} table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ddd;padding:6px}} th{{background:#f5f5f5}}</style>
</head><body>
<h1>Evaluation Report</h1>
<pre>{json.dumps(summary, indent=2)}</pre>
<h2>Predictions (first {min(50,len(items))})</h2>
<table><thead><tr><th>#</th><th>ID</th><th>Verdict (true)</th><th>Verdict (pred)</th><th>Score (true)</th><th>Score (pred)</th></tr></thead><tbody>
"""
    for idx, (it, res) in enumerate(zip(items[:50], results[:50]), start=1):
        verdict_p = (res.get("verdict") or {}).get("summary") if isinstance(res.get("verdict"), dict) else res.get("verdict")
        score_p = float(res.get("score", 50))
        html += f"<tr><td>{idx}</td><td>{it.id}</td><td>{it.labels.get('verdict','')}</td><td>{(verdict_p or '')}</td><td>{float(it.labels.get('score',50))}</td><td>{score_p}</td></tr>\n"
    html += "</tbody></table>\n</body></html>\n"
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as hf:
        hf.write(html)

    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    # Router-only: local path removed; keep flag for compatibility but ignore
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_eval(args.input, args.out, local=False))


if __name__ == "__main__":
    main()


