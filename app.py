from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
import os
import json
from datetime import datetime
import uuid
import re
import logging
import traceback
import subprocess
import tempfile
from dotenv import load_dotenv
from rq import Worker, Queue
from redis import Redis

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

if not os.path.exists('downloads'):
    os.makedirs('downloads')

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(redis_url)

def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    youtube_regex_match = re.match(youtube_regex, url)
    return bool(youtube_regex_match)

def download_and_convert(url, format_type=None, format_id=None):
    """Function for downloading and converting to MP3"""
    try:
        # Get video info first to get the title
        info_result = subprocess.run([
            'yt-dlp',
            '--dump-json',
            url
        ], capture_output=True, text=True, timeout=30)
        
        if info_result.returncode != 0:
            logger.error(f"yt-dlp info error: {info_result.stderr}")
            return {'error': 'Gagal mengambil info video.'}
            
        video_info = json.loads(info_result.stdout)
        video_title = video_info.get('title', 'video')
        
        # Clean the title to make it safe for filenames
        safe_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
        safe_title = safe_title.replace(' ', '_')
        # Limit title length to avoid too long filenames
        safe_title = safe_title[:100]
        
        # First download as m4a
        temp_m4a = f"downloads/{safe_title}.m4a"
        ytdlp_cmd = [
            'yt-dlp',
            '-f', 'bestaudio[ext=m4a]/bestaudio/best',
            '--extract-audio',
            '--audio-format', 'm4a',
            '--audio-quality', '0',
            '--prefer-ffmpeg',
            '--ffmpeg-location', 'ffmpeg',
            '--postprocessor-args', '-vn',
            '-o', temp_m4a,
            '--verbose',
            url
        ]

        logger.debug(f"Running yt-dlp command: {' '.join(ytdlp_cmd)}")
        result = subprocess.run(ytdlp_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"yt-dlp error output: {result.stderr}")
            logger.error(f"yt-dlp stdout: {result.stdout}")
            return {'error': 'Gagal mengunduh audio.'}

        # Then convert to mp3 using ffmpeg
        final_mp3 = f"downloads/{safe_title}.mp3"
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', temp_m4a,
            '-vn',
            '-ar', '44100',
            '-ac', '2',
            '-b:a', '320k',
            '-y',  # Overwrite output file if it exists
            final_mp3
        ]

        logger.debug(f"Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg error output: {result.stderr}")
            logger.error(f"ffmpeg stdout: {result.stdout}")
            return {'error': 'Gagal mengkonversi ke MP3.'}

        # Remove temporary m4a file
        try:
            os.remove(temp_m4a)
        except Exception as e:
            logger.warning(f"Failed to remove temporary file: {str(e)}")

        # Check if the final mp3 file exists
        if os.path.exists(final_mp3):
            return {
                'success': True,
                'filename': os.path.basename(final_mp3),
                'title': video_title
            }
        else:
            return {'error': 'File tidak ditemukan setelah konversi.'}

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        logger.error(traceback.format_exc())
        return {'error': f'Error saat download: {str(e)}'}

@app.route('/')
def index():
    if 'download_history' not in session:
        session['download_history'] = []
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
            result = subprocess.run([
                'yt-dlp',
                '--dump-json',
                '--verbose',
                url
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"yt-dlp error output: {result.stderr}")
                logger.error(f"yt-dlp stdout: {result.stdout}")
                return jsonify({'error': 'Gagal mengambil info video.'}), 400

            info = json.loads(result.stdout)
            formats = []
            for f in info.get('formats', []):
                if f.get('ext') in ['mp4', 'm4a', 'webm']:
                    formats.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'format_note': f.get('format_note'),
                        'filesize': f.get('filesize') or f.get('filesize_approx'),
                        'resolution': f.get('resolution') or f.get('height'),
                        'abr': f.get('abr'),
                        'vcodec': f.get('vcodec'),
                        'acodec': f.get('acodec'),
                        'fps': f.get('fps'),
                        'format': f.get('format')
                    })

            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'formats': formats
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

        # Process download directly
        result = download_and_convert(url)
        
        if 'error' in result:
            return jsonify(result), 400

        # Add to download history
        download_info = {
            'title': result['title'],
            'format': 'mp3',
            'filename': result['filename'],
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
        }
        history = session.get('download_history', [])
        history.append(download_info)
        session['download_history'] = history

        return jsonify(result)

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Error server: {str(e)}'}), 500

@app.route('/download_file/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join('downloads', filename)
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return jsonify({'error': 'File tidak ditemukan'}), 404
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        logger.error(f"Error sending file: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 400

@app.route('/get_history')
def get_history():
    return jsonify(session.get('download_history', []))

if __name__ == '__main__':
    app.run(debug=True, port=5000)

    worker = Worker([Queue(connection=redis_conn)], connection=redis_conn)
    worker.work() 