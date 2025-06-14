import os
import sys
import logging

# Configure logging
logging.basicConfig(stream=sys.stderr)

# Add the project directory to the Python path
path = '/home/blacklotus/ytmp3try'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'
os.environ['PYTHONUNBUFFERED'] = '1'

# Import the Flask app from app.py
from app import app as application 