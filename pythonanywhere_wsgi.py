import sys
import os

# Add your project directory to the sys.path
path = '/home/YOUR_USERNAME/ytdownloadermp3'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'production'

# Import your Flask app
from app import app as application 