import pytest
from datetime import datetime, timezone
from app.models import AnalysisResult, Song, db
from app.utils.database import get_by_id  # Add SQLAlchemy 2.0 utility

class TestAnalysisResultModel:
    """Test suite for the AnalysisResult model."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        """Setup test environment for each test method."""
        # Create test data
        self.song = Song(
            spotify_id='test_song_123',
            title='Test Song',
            artist='Test Artist',
            album='Test Album',
            duration_ms=180000
        )
        db.session.add(self.song)
        db.session.commit()
        
        # Create a test analysis result
        self.analysis_result = AnalysisResult(
            song_id=self.song.id,
            status=AnalysisResult.STATUS_COMPLETED,
            themes={"faith": 0.9, "hope": 0.8},
            problematic_content={"explicit": False, "violence": False},
            concerns=["potential religious references"],
            score=85.5,
            concern_level="low",
            explanation="Song aligns well with Christian values",
            analyzed_at=datetime.now(timezone.utc)
        )
        db.session.add(self.analysis_result)
        db.session.commit()
        
        yield
        
        # Cleanup
        db.session.remove()
        db.drop_all()
    
    def test_analysis_result_creation(self, db_session):
        """Test creating a new analysis result."""
        # Create a new analysis result
        new_analysis = AnalysisResult(
            song_id=self.song.id,
            status=AnalysisResult.STATUS_PENDING,
            themes={},
            problematic_content={},
            concerns=[],
            score=None,
            concern_level=None,
            explanation=None
        )
        db.session.add(new_analysis)
        db.session.commit()
        
        assert new_analysis.id is not None
        assert new_analysis.status == AnalysisResult.STATUS_PENDING
        assert new_analysis.created_at is not None
        assert new_analysis.updated_at is not None
    
    def test_analysis_result_relationships(self, db_session):
        """Test the relationship between AnalysisResult and Song."""
        # Refresh the analysis result using SQLAlchemy 2.0 pattern
        analysis = get_by_id(AnalysisResult, self.analysis_result.id)
        
        assert analysis.song_rel is not None
        assert analysis.song_rel.id == self.song.id
    
    def test_analysis_result_status_constants(self):
        """Test the status constants are defined correctly."""
        assert hasattr(AnalysisResult, 'STATUS_PENDING')
        assert hasattr(AnalysisResult, 'STATUS_PROCESSING')
        assert hasattr(AnalysisResult, 'STATUS_COMPLETED')
        assert hasattr(AnalysisResult, 'STATUS_FAILED')
    
    def test_analysis_result_update(self, db_session):
        """Test updating an analysis result."""
        # Get the analysis result using SQLAlchemy 2.0 pattern
        analysis = get_by_id(AnalysisResult, self.analysis_result.id)
        
        # Update fields
        analysis.status = AnalysisResult.STATUS_FAILED
        analysis.error_message = "Analysis failed due to timeout"
        analysis.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Verify updates using SQLAlchemy 2.0 pattern
        updated = get_by_id(AnalysisResult, self.analysis_result.id)
        assert updated.status == AnalysisResult.STATUS_FAILED
        assert updated.error_message == "Analysis failed due to timeout"
    
    def test_analysis_result_json_serialization(self, db_session):
        """Test that the model can be serialized to JSON."""
        analysis = get_by_id(AnalysisResult, self.analysis_result.id)
        result = analysis.to_dict()
        
        assert 'id' in result
        assert 'song_id' in result
        assert 'status' in result
        assert 'themes' in result
        # Note: problematic_content is not included in the to_dict() output
        # so we don't check for it here
        assert 'concerns' in result
        assert 'score' in result
        assert 'concern_level' in result
        assert 'explanation' in result
        assert 'analyzed_at' in result
        assert 'created_at' in result
        assert 'updated_at' in result
