import csv
import json
from typing import List

from app import create_app
from app.models.models import Song, db


def export_songs(limit: int = 10, out_jsonl: str = "scripts/eval/songs_eval_db.jsonl", out_csv: str = "scripts/eval/songs_eval_db.csv") -> None:
    app = create_app()
    with app.app_context():
        q = (
            Song.query.filter(
                Song.lyrics.isnot(None),
                db.func.length(db.func.trim(Song.lyrics)) > 0,
            )
            .order_by(Song.updated_at.desc())
            .limit(limit)
        )
        songs: List[Song] = q.all()

        # Write JSONL (no labels yet; user/Claude will provide ground truth externally)
        with open(out_jsonl, "w", encoding="utf-8") as jf:
            for s in songs:
                rec = {
                    "id": f"db-{s.id}",
                    "title": s.title,
                    "artist": s.artist,
                    "lyrics": s.lyrics or "",
                }
                jf.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # CSV convenience
        with open(out_csv, "w", newline="", encoding="utf-8") as cf:
            w = csv.writer(cf)
            w.writerow(["id", "title", "artist", "lyrics"])  # headers
            for s in songs:
                w.writerow([f"db-{s.id}", s.title, s.artist, (s.lyrics or "").replace("\n", " ").strip()])

        print(json.dumps({"exported": len(songs), "jsonl": out_jsonl, "csv": out_csv}))


if __name__ == "__main__":
    export_songs()
