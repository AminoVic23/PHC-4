"""
Startup script for Railway deployment
Handles database initialization and migrations
"""
import os
import sys
from app import create_app, db
from app.models import *  # Import all models
from flask_migrate import upgrade

def init_db():
    """Initialize database tables"""
    app = create_app()
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("Database tables created successfully")
            
            # Run migrations
            upgrade()
            print("Database migrations completed successfully")
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    init_db()
