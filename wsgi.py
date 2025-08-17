"""
WSGI entry point for Railway deployment
"""
import os
import sys

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set environment variables if not already set
os.environ.setdefault('FLASK_APP', 'wsgi.py')
os.environ.setdefault('FLASK_ENV', 'production')

# Import and create the Flask application
from app import create_app
app = create_app()

if __name__ == "__main__":
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get("PORT", 8080))
    
    # Run the application
    app.run(host="0.0.0.0", port=port, debug=False)
