#!/usr/bin/env python3
"""
Fix Spotify Token Issues
Refresh expired tokens and ensure proper token validation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User
from datetime import datetime

def fix_spotify_token_issues():
    """Fix Spotify token issues by refreshing expired tokens"""
    app = create_app()
    
    with app.app_context():
        print("🔧 FIXING SPOTIFY TOKEN ISSUES")
        print("=" * 50)
        
        # Get all users
        users = db.session.query(User).all()
        print(f"Found {len(users)} users")
        
        for user in users:
            print(f"\nProcessing user: {user.id} - {user.display_name}")
            print(f"Token expiry: {user.token_expiry}")
            print(f"Current time: {datetime.utcnow()}")
            print(f"Token expired: {user.is_token_expired}")
            
            if user.is_token_expired:
                print("🔄 Attempting to refresh expired token...")
                
                if user.ensure_token_valid():
                    print("✅ Token refreshed successfully!")
                    print(f"New token expiry: {user.token_expiry}")
                else:
                    print("❌ Failed to refresh token - user needs to re-authenticate")
                    print("   User should log out and log back in")
            else:
                print("✅ Token is still valid")
        
        print(f"\n📊 SUMMARY")
        print("-" * 30)
        
        # Check final status
        expired_users = [u for u in users if u.is_token_expired]
        valid_users = [u for u in users if not u.is_token_expired]
        
        print(f"Users with valid tokens: {len(valid_users)}")
        print(f"Users with expired tokens: {len(expired_users)}")
        
        if expired_users:
            print(f"\n⚠️  Users needing re-authentication:")
            for user in expired_users:
                print(f"  - {user.display_name} (ID: {user.id})")
        
        return len(expired_users) == 0

if __name__ == "__main__":
    success = fix_spotify_token_issues()
    if success:
        print("\n🎉 All token issues resolved!")
    else:
        print("\n⚠️  Some users still need to re-authenticate") 