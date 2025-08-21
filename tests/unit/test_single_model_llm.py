import json
import os


def test_single_model_llm_analyzes_song_and_persists(app, db, monkeypatch):
    # Force single-model LLM path
    os.environ["USE_LLM_ANALYZER"] = "1"
    os.environ.setdefault("SECRET_KEY", "test-secret-key-12345678901234567890abcd")

    from app.models.models import AnalysisResult, Song
    from app.services.unified_analysis_service import UnifiedAnalysisService
    from app.utils.analysis.llm_analyzer import LLMAnalyzer

    # Stub network call to the LLM endpoint with a strict JSON response
    def fake_chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "score": 88,
            "concern_level": "Low",
            "biblical_themes": [{"theme": "Gospel presentation", "confidence": 0.85}],
            "supporting_scripture": [{"reference": "John 3:16", "theme": "Gospel presentation"}],
            "concerns": [],
            "verdict": {"summary": "Gospel-centered content", "guidance": "Good for formation"},
        }
        return json.dumps(payload)

    monkeypatch.setattr(LLMAnalyzer, "_chat_completion", fake_chat_completion, raising=True)

    with app.app_context():
        # Create a song with required fields
        song = Song(
            spotify_id="test_song_llm_1",
            title="Test Song",
            artist="Test Artist",
            lyrics="Jesus saves by grace and truth.",
        )
        db.session.add(song)
        db.session.commit()

        # Run analysis through the unified service (should use LLMAnalyzer)
        svc = UnifiedAnalysisService()
        result = svc.analyze_song(song.id)

        # Validate result persisted and completed
        assert result is not None
        persisted = (
            AnalysisResult.query.filter_by(song_id=song.id)
            .order_by(AnalysisResult.created_at.desc())
            .first()
        )
        assert persisted is not None
        assert persisted.status == "completed"

        # Ensure we did not fall back to the heuristic with empty structures
        assert persisted.explanation is not None

        # Clean up happens via test runner fixtures; avoid explicit drop here to prevent interference
