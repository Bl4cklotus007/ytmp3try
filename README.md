# YouTube Audio Converter

Aplikasi web untuk mengunduh dan mengkonversi video YouTube ke format MP3 dengan kualitas tinggi.

## Fitur

- Download audio dari video YouTube
- Konversi otomatis ke format MP3
- Kualitas audio tinggi (320kbps)
- Nama file otomatis sesuai judul video
- Riwayat download
- Antarmuka web yang mudah digunakan

## Persyaratan Sistem

- Python 3.7 atau lebih baru
- FFmpeg
- yt-dlp
- Redis (untuk antrian)

## Instalasi

1. Clone repository:

```bash
git clone https://github.com/Bl4cklotus007/ytdownloadermp3.git
cd ytdownloadermp3
```

2. Buat virtual environment dan aktifkan:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Install FFmpeg:

- Windows: Download dari https://ffmpeg.org/download.html
- Linux: `sudo apt-get install ffmpeg`
- Mac: `brew install ffmpeg`

5. Install Redis:

- Windows: Download dari https://github.com/microsoftarchive/redis/releases
- Linux: `sudo apt-get install redis-server`
- Mac: `brew install redis`

## Penggunaan

1. Jalankan Redis server:

```bash
# Windows
redis-server
# Linux/Mac
sudo service redis-server start
```

2. Jalankan aplikasi:

```bash
python app.py
```

3. Buka browser dan akses `http://localhost:5000`

4. Masukkan URL video YouTube dan klik "Get Info"

5. Klik "Download MP3" untuk mengunduh audio

## Teknologi yang Digunakan

- Flask (Backend)
- Bootstrap (Frontend)
- yt-dlp (YouTube Downloader)
- FFmpeg (Audio Conversion)
- Redis (Queue Management)

## Lisensi

MIT License
