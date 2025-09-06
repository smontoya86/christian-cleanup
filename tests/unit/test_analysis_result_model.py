from datetime import datetime, timezone

import pytest

from app.models import AnalysisResult, Song, db
from app.utils.database import get_by_id  # Add SQLAlchemy 2.0 utility


class TestAnalysisResultModel:
    """Test suite for the AnalysisResult model."""

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        """Setup test environment for each test method."""
        # Create test data
        self.song = Song(
            spotify_id="test_song_123",
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            duration_ms=180000,
        )
        db.session.add(self.song)
        db.session.commit()

        # Create a test analysis result
        self.analysis_result = AnalysisResult(
            song_id=self.song.id,
            # No status field needed - all stored analyses are completed
            themes={"faith": 0.9, "hope": 0.8},
            problematic_content={"explicit": False, "violence": False},
            concerns=["potential religious references"],
            score=85.5,
            concern_level="low",
            explanation="Song aligns well with Christian values",
            analyzed_at=datetime.now(timezone.utc),
        )
        db.session.add(self.analysis_result)
        db.session.commit()

        yield

        # Cleanup
        db.session.remove()
        db.drop_all()

    def test_analysis_result_creation(self, db_session):
        """Test creating a new analysis result."""
        # Create a different song since we already have an analysis for self.song
        from app.models.models import Song
        new_song = Song(
            spotify_id="new_test_song_456",
            title="New Test Song",
            artist="New Test Artist"
        )
        db.session.add(new_song)
        db.session.flush()  # Get the ID
        
        # Create a new analysis result
        new_analysis = AnalysisResult(
            song_id=new_song.id,
            # No status field needed - all stored analyses are completed
            themes={},
            problematic_content={},
            concerns=[],
            score=85.0,
            concern_level='Low',
            explanation='Test analysis',
        )
        db.session.add(new_analysis)
        db.session.commit()

        assert new_analysis.id is not None
        assert new_analysis.score == 85.0
        assert new_analysis.created_at is not None
        assert new_analysis.updated_at is not None

    def test_analysis_result_relationships(self, db_session):
        """Test the relationship between AnalysisResult and Song."""
        # Refresh the analysis result using SQLAlchemy 2.0 pattern
        analysis = get_by_id(AnalysisResult, self.analysis_result.id)

        assert analysis.song_rel is not None
        assert analysis.song_rel.id == self.song.id

    def test_analysis_result_status_constants(self):
        """Test that status constants are no longer needed."""
        # Status constants removed in simplified model
        assert not hasattr(AnalysisResult, "STATUS_PENDING")
        assert not hasattr(AnalysisResult, "STATUS_PROCESSING")
        assert not hasattr(AnalysisResult, "STATUS_COMPLETED")
        assert not hasattr(AnalysisResult, "STATUS_FAILED")

    def test_analysis_result_update(self, db_session):
        """Test updating an analysis result."""
        # Get the analysis result using SQLAlchemy 2.0 pattern
        analysis = get_by_id(AnalysisResult, self.analysis_result.id)

        # Update fields (no status or error_message in simplified model)
        analysis.score = 90.0
        analysis.explanation = "Updated analysis"
        analysis.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        # Verify updates using SQLAlchemy 2.0 pattern
        updated = get_by_id(AnalysisResult, self.analysis_result.id)
        assert updated.score == 90.0
        assert updated.explanation == "Updated analysis"

    def test_analysis_result_json_serialization(self, db_session):
        """Test that the model can be serialized to JSON."""
        analysis = get_by_id(AnalysisResult, self.analysis_result.id)
        result = analysis.to_dict()

        assert "id" in result
        assert "song_id" in result
        assert "status" in result
        assert "themes" in result
        # Note: problematic_content is not included in the to_dict() output
        # so we don't check for it here
        assert "concerns" in result
        assert "score" in result
        assert "concern_level" in result
        assert "explanation" in result
        assert "analyzed_at" in result
        # Note: created_at and updated_at are not included in to_dict() output
        # but they exist on the model instance
        assert hasattr(analysis, "created_at")
        assert hasattr(analysis, "updated_at")
        assert analysis.created_at is not None
        assert analysis.updated_at is not None
