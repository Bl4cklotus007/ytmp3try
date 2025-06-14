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
        
        # Use temporary directory for downloads
        temp_dir = tempfile.mkdtemp()
        temp_m4a = os.path.join(temp_dir, f"{safe_title}.m4a")
        final_mp3 = os.path.join(temp_dir, f"{safe_title}.mp3")
        
        # First download as m4a
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
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', temp_m4a,
            '-vn',
            '-ar', '44100',
            '-ac', '2',
            '-b:a', '320k',
            '-y',
            final_mp3
        ]

        logger.debug(f"Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg error output: {result.stderr}")
            logger.error(f"ffmpeg stdout: {result.stdout}")
            return {'error': 'Gagal mengkonversi ke MP3.'}

        # Move the final file to downloads directory
        final_path = os.path.join('downloads', f"{safe_title}.mp3")
        os.rename(final_mp3, final_path)

        # Clean up temporary files
        try:
            os.remove(temp_m4a)
            os.rmdir(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {str(e)}")

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
        return send_file(
            os.path.join('downloads', filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Download file error: {str(e)}")
        return jsonify({'error': 'File tidak ditemukan'}), 404

@app.route('/get_history')
def get_history():
    return jsonify(session.get('download_history', []))

# For Vercel deployment
if __name__ == '__main__':
    app.run(debug=True) 