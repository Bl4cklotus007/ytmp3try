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

def download_and_convert(url, format_type=None, format_id=None):
    """Function for downloading and converting to MP3"""
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')

        # Configure yt-dlp options with proxy settings
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            # Disable proxy to avoid connection issues
            'noproxy': '*',
            # Add retries for better reliability
            'retries': 3,
            # Add socket timeout
            'socket_timeout': 30,
            # Add user agent
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }

        try:
            # Download and convert using yt-dlp Python API
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Attempting to download video from URL: {url}")
                info = ydl.extract_info(url, download=True)
                video_title = info.get('title', 'video')
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
def download():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400

        url = data['url']
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        result = download_and_convert(url)
        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Error server: {str(e)}'}), 500

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