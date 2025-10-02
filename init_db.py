#!/usr/bin/env python3
"""
Database initialization script for Christian Music Curator
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db


def init_database():
    """Initialize the database with proper tables"""
    print("🔧 Initializing database...")
    
    # Create app
    app = create_app()
    
    with app.app_context():
        # Drop all tables and recreate (for clean slate)
        db.drop_all()
        print("📊 Dropped existing tables")
        
        # Create all tables
        db.create_all()
        print("✅ Created all tables")
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {', '.join(tables)}")
        
    print("🎉 Database initialization complete!")

if __name__ == "__main__":
    init_database()
