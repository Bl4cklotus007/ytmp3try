import sys
import os

# Add the project directory to the Python path
path = '/home/blacklotus/ytmp3try'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'production'

# Import the Flask app from app.py
from app import app as application 