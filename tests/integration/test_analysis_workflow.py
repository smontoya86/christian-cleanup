"""
Integration tests for complete analysis workflow
"""

import pytest

from app.models.models import AnalysisResult, LyricsCache, Song


class TestAnalysisWorkflow:
    """Test complete analysis workflow from lyrics to results"""
    
    def test_full_analysis_pipeline(self, db_session, mock_analysis_service):
        """Test complete analysis pipeline"""
        from app.services.simplified_christian_analysis_service import (
            SimplifiedChristianAnalysisService,
        )
        
        # 1. Create a song
        song = Song(
            spotify_id='workflow_test_123',
            title='Test Hymn',
            artist='Test Artist',
            album='Test Album',
            duration_ms=240000
        )
        db_session.add(song)
        db_session.commit()
        
        # 2. Cache lyrics
        lyrics = "Praise the Lord, O my soul; all my inmost being, praise his holy name."
        LyricsCache.cache_lyrics('Test Artist', 'Test Hymn', lyrics, 'test')
        
        # 3. Analyze the song
        service = SimplifiedChristianAnalysisService()
        result = service.analyze_song_content('Test Hymn', 'Test Artist', lyrics)
        
        # 4. Verify analysis structure
        assert 'overall_score' in result or 'score' in result
        assert 'verdict' in result
        
        # 5. Save analysis result
        score = result.get('overall_score') or result.get('score')
        analysis = AnalysisResult(
            song_id=song.id,
            score=score,
            verdict=result.get('verdict'),
            biblical_themes=result.get('biblical_analysis', {}).get('themes', []),
            concerns=[],
            explanation=result.get('detailed_explanation', '')
        )
        db_session.add(analysis)
        db_session.commit()
        
        # 6. Verify analysis was saved
        saved_analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
        assert saved_analysis is not None
        assert saved_analysis.score == score
        assert saved_analysis.verdict == result.get('verdict')
    
    def test_analysis_with_cached_lyrics(self, sample_lyrics_cache, mock_analysis_service):
        """Test analysis uses cached lyrics"""
        from app.services.simplified_christian_analysis_service import (
            SimplifiedChristianAnalysisService,
        )
        from app.utils.lyrics.lyrics_fetcher import LyricsFetcher
        
        # Fetch from cache
        fetcher = LyricsFetcher()
        lyrics = fetcher.fetch_lyrics('Amazing Grace', 'John Newton')
        
        assert lyrics is not None
        assert 'Amazing grace' in lyrics
        
        # Analyze
        service = SimplifiedChristianAnalysisService()
        result = service.analyze_song_content('Amazing Grace', 'John Newton', lyrics)
        
        assert result is not None
        assert 'verdict' in result
    
    def test_reanalysis_updates_existing(self, db_session, sample_song, sample_analysis, mock_analysis_service):
        """Test re-analysis updates existing analysis"""
        from app.services.simplified_christian_analysis_service import (
            SimplifiedChristianAnalysisService,
        )
        
        original_score = sample_analysis.score
        
        # Re-analyze
        service = SimplifiedChristianAnalysisService()
        new_result = service.analyze_song_content(
            sample_song.title,
            sample_song.artist,
            'New lyrics content'
        )
        
        # Update analysis
        sample_analysis.score = new_result.get('overall_score') or new_result.get('score')
        sample_analysis.verdict = new_result.get('verdict')
        db_session.commit()
        
        # Verify update
        updated = AnalysisResult.query.get(sample_analysis.id)
        assert updated.score == (new_result.get('overall_score') or new_result.get('score'))


class TestBatchAnalysis:
    """Test batch analysis functionality"""
    
    def test_multiple_songs_analysis(self, db_session, mock_analysis_service):
        """Test analyzing multiple songs"""
        from app.services.simplified_christian_analysis_service import (
            SimplifiedChristianAnalysisService,
        )
        
        songs = [
            ('Song 1', 'Artist 1', 'Lyrics 1'),
            ('Song 2', 'Artist 2', 'Lyrics 2'),
            ('Song 3', 'Artist 3', 'Lyrics 3'),
        ]
        
        service = SimplifiedChristianAnalysisService()
        results = []
        
        for title, artist, lyrics in songs:
            result = service.analyze_song_content(title, artist, lyrics)
            results.append(result)
        
        assert len(results) == 3
        for result in results:
            assert 'verdict' in result
            assert 'overall_score' in result or 'score' in result

