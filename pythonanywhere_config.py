# PythonAnywhere configuration
import os

# Set the working directory
os.chdir('/home/YOUR_USERNAME/ytdownloadermp3')

# Create downloads directory if it doesn't exist
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# Set environment variables
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'production' 