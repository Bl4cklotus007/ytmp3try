from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
import os
import json
from datetime import datetime
import uuid
import re
import logging
import traceback
import yt_dlp
import tempfile
from dotenv import load_dotenv
import shutil
import socket

# Load environment variables
load_dotenv()

# Konfigurasi logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)

# Create downloads directory if it doesn't exist
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# Regex pattern for validating YouTube URLs
YOUTUBE_REGEX = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'

def is_valid_youtube_url(url):
    return bool(re.match(YOUTUBE_REGEX, url))

def get_yt_dlp_opts(output_path):
    """Get yt-dlp options with robust configuration"""
    return {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        # Network settings
        'noproxy': '*',
        'retries': 10,
        'socket_timeout': 60,
        'extractor_retries': 10,
        'ignoreerrors': True,
        'no_check_certificate': True,
        # Custom headers
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        # Additional options
        'geo_bypass': True,
        'geo_verification_proxy': None,
        'source_address': '0.0.0.0',
        # Cookie handling
        'cookiesfrombrowser': ('chrome',),
        # Extractors
        'extract_flat': False,
        'force_generic_extractor': False,
        # Debug options
        'verbose': True,
        'dump_single_json': True,
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST', 'GET'])
def get_video_info():
    try:
        url = None
        if request.method == 'POST':
            if request.is_json:
                url = request.json.get('url')
            else:
                url = request.form.get('url')
        else:
            url = request.args.get('url')

        if not url:
            return jsonify({'error': 'URL tidak boleh kosong'}), 400

        if not is_valid_youtube_url(url):
            return jsonify({'error': 'URL YouTube tidak valid'}), 400

        try:
            logger.debug(f"Getting video info for URL: {url}")
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return jsonify({
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail')
                })

        except Exception as e:
            logger.error(f"yt-dlp info error: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Gagal mengambil info video: {str(e)}'}), 400

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Error server: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download_and_convert():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400

        url = data['url']
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')

        try:
            # First try to get video info without downloading
            with yt_dlp.YoutubeDL(get_yt_dlp_opts(output_path)) as ydl:
                logger.info(f"Attempting to get video info from URL: {url}")
                try:
                    # Try to get video info first
                    info = ydl.extract_info(url, download=False)
                    if info is None:
                        raise Exception("Failed to extract video information")
                    
                    video_title = info.get('title', 'video')
                    logger.info(f"Successfully got video info: {video_title}")
                    
                    # Now try to download
                    logger.info("Starting download...")
                    info = ydl.extract_info(url, download=True)
                    
                    # Get the actual output file path
                    output_file = os.path.join(temp_dir, f"{video_title}.mp3")

                    if not os.path.exists(output_file):
                        logger.error("Output file not found after download")
                        return jsonify({'error': 'Failed to download video'}), 500

                    logger.info(f"Successfully downloaded and converted video: {video_title}")
                    # Send the file
                    return send_file(
                        output_file,
                        as_attachment=True,
                        download_name=f"{video_title}.mp3",
                        mimetype='audio/mpeg'
                    )
                except yt_dlp.utils.DownloadError as e:
                    logger.error(f"Download error: {str(e)}")
                    # Try to get more detailed error information
                    error_details = {
                        'error': str(e),
                        'url': url,
                        'timestamp': str(datetime.now())
                    }
                    logger.error(f"Error details: {json.dumps(error_details)}")
                    return jsonify({'error': f'Error downloading video: {str(e)}'}), 500

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Request processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary directory
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/download_file/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join('downloads', filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Download file error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Error saat download file: {str(e)}'}), 500

@app.route('/get_history')
def get_history():
    try:
        history = []
        for filename in os.listdir('downloads'):
            if filename.endswith('.mp3'):
                file_path = os.path.join('downloads', filename)
                history.append({
                    'filename': filename,
                    'title': os.path.splitext(filename)[0].replace('_', ' '),
                    'size': os.path.getsize(file_path),
                    'date': datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                })
        return jsonify(history)
    except Exception as e:
        logger.error(f"Get history error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Error saat mengambil history: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True) 