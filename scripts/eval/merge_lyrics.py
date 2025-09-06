import argparse
import csv
import json
import os
from typing import Dict, List


def normalize(s: str) -> str:
    return (s or "").strip().lower()


def load_jsonl(path: str) -> List[dict]:
    items: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            items.append(json.loads(line))
    return items


def write_jsonl(path: str, items: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Merge full lyrics from CSV into eval JSONL")
    parser.add_argument("--csv", required=True, help="CSV with columns: id,title,artist,lyrics")
    parser.add_argument("--jsonl", default="scripts/eval/songs_eval.jsonl", help="Input JSONL to update")
    parser.add_argument("--out", default="scripts/eval/songs_eval.jsonl", help="Output JSONL (can overwrite input)")
    args = parser.parse_args()

    items = load_jsonl(args.jsonl)

    # Index items by id and by (title,artist)
    by_id: Dict[str, dict] = {}
    by_key: Dict[str, dict] = {}
    for it in items:
        if "id" in it and it["id"]:
            by_id[str(it["id"])]=it
        key = f"{normalize(it.get('title',''))}|{normalize(it.get('artist',''))}"
        by_key[key] = it

    updated = 0
    total = 0

    with open(args.csv, "r", encoding="utf-8") as cf:
        reader = csv.DictReader(cf)
        for row in reader:
            total += 1
            rid = str(row.get("id") or "").strip()
            title = row.get("title") or ""
            artist = row.get("artist") or ""
            lyrics = row.get("lyrics") or ""

            target = None
            if rid and rid in by_id:
                target = by_id[rid]
            else:
                key = f"{normalize(title)}|{normalize(artist)}"
                target = by_key.get(key)

            if target is None:
                continue

            if lyrics and (target.get("lyrics") != lyrics):
                target["lyrics"] = lyrics
                updated += 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_jsonl(args.out, items)
    print(json.dumps({"rows_in_csv": total, "updated_items": updated, "output": args.out}))


if __name__ == "__main__":
    main()


