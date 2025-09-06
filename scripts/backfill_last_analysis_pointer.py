"""Backfill Song.last_analysis_result_id for existing data.

This script sets the pointer to the most recent completed analysis per song,
falling back to the most recent analysis of any status when no completed one exists.

Idempotent and safe to run multiple times.
"""
import os

from sqlalchemy import text


def main():
    # Ensure app context
    os.environ.setdefault("FLASK_ENV", os.environ.get("FLASK_ENV", "production"))
    from app import create_app
    from app.extensions import db

    app = create_app(
        os.environ.get("FLASK_ENV", "production"),
        skip_db_init=True,
    )

    with app.app_context():
        # 1) Prefer latest COMPLETED result per song
        sql_completed = text(
            """
            WITH latest_completed AS (
                SELECT DISTINCT ON (song_id) id, song_id
                FROM analysis_results
                WHERE status = 'completed'
                ORDER BY song_id, analyzed_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
            )
            UPDATE songs s
            SET last_analysis_result_id = lc.id
            FROM latest_completed lc
            WHERE s.id = lc.song_id
              AND (s.last_analysis_result_id IS DISTINCT FROM lc.id);
            """
        )

        # 2) For songs without pointer yet, set to latest ANY status
        sql_any = text(
            """
            WITH latest_any AS (
                SELECT DISTINCT ON (song_id) id, song_id
                FROM analysis_results
                ORDER BY song_id, analyzed_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
            )
            UPDATE songs s
            SET last_analysis_result_id = la.id
            FROM latest_any la
            WHERE s.id = la.song_id
              AND s.last_analysis_result_id IS NULL;
            """
        )

        # Execute updates
        res1 = db.session.execute(sql_completed)
        res2 = db.session.execute(sql_any)
        db.session.commit()

        # Report counts
        cnt_total = db.session.execute(text("SELECT COUNT(*) FROM songs")).scalar_one()
        cnt_with = db.session.execute(
            text("SELECT COUNT(*) FROM songs WHERE last_analysis_result_id IS NOT NULL")
        ).scalar_one()
        cnt_without = cnt_total - cnt_with

        print(
            f"Backfill completed. total_songs={cnt_total}, with_pointer={cnt_with}, without_pointer={cnt_without}"
        )


if __name__ == "__main__":
    main()


