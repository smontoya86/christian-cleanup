#!/usr/bin/env python3
"""Quick test to verify core functionality."""

from app import create_app
from app.models.models import User, Song, AnalysisResult
from app.services.unified_analysis_service import UnifiedAnalysisService

def main():
    app = create_app()
    with app.app_context():
        print('✅ Database connectivity test:')
        user_count = User.query.count()
        song_count = Song.query.count()
        analysis_count = AnalysisResult.query.count()
        print(f'   Users: {user_count}, Songs: {song_count}, Analyses: {analysis_count}')
        
        print('✅ UnifiedAnalysisService test:')
        service = UnifiedAnalysisService()
        print('   Service initialized successfully')
        
        if user_count > 0:
            user = User.query.first()
            print(f'   First user: {user.display_name} (ID: {user.id})')
        
        print('✅ All core systems functional!')

if __name__ == "__main__":
    main() 