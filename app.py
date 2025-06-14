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

def is_valid_youtube_url(url):
    return 'youtube.com/watch?v=' in url or 'youtu.be/' in url

def download_and_convert(url, format_type=None, format_id=None):
    """Function for downloading and converting to MP3"""
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': os.path.join('downloads', '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }

        # Download and convert
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'video')
            
            # Clean the title to make it safe for filenames
            safe_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
            safe_title = safe_title.replace(' ', '_')
            # Limit title length to avoid too long filenames
            safe_title = safe_title[:100]
            
            final_path = os.path.join('downloads', f"{safe_title}.mp3")

            return {
                'success': True,
                'filename': os.path.basename(final_path),
                'title': video_title
            }

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        logger.error(traceback.format_exc())
        return {'error': f'Error saat download: {str(e)}'}

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
        if request.is_json:
            data = request.json
        else:
            data = request.form

        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL tidak boleh kosong'}), 400

        if not is_valid_youtube_url(url):
            return jsonify({'error': 'URL YouTube tidak valid'}), 400

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