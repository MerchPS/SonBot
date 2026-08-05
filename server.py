#!/usr/bin/env python3
"""
🎵 BIMOLI SOUNDBOARD SERVER - Volume Control Fix + Server-side Live Check
"""

import os
import re
import sys
import json
import threading
import subprocess
import platform
import socket
import requests
import base64
from datetime import datetime

# Path dari launcher
SYSTEM_DIR = os.environ.get('BIMOLI_SYSTEM_DIR', '.bimoli_system')
BASE_DIR = os.environ.get('BIMOLI_BASE_DIR', os.getcwd())

sys.path.insert(0, SYSTEM_DIR)

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Konfigurasi
FOLDER_SUARA = os.path.join(BASE_DIR, "suara")
FILE_KONFIG = os.path.join(BASE_DIR, "config.json")
IS_WINDOWS = platform.system() == "Windows"
PORT = 5000
VOLUME_GLOBAL = 0.75

# Channel YouTube yang dicek statusnya
YT_CHANNEL_HANDLE = "@TheMoiLee"

# Webhook IP
WEBHOOK_URL = "https://discord.com/api/webhooks/1534060970748543097/-oxVS2Gb1ojNC-UCV43UobpgqSJUAbv_90X1rbLZvf6J6Vlj4hjgKSM-FPhEFCbufeAT"

app = Flask(__name__, template_folder=os.path.join(SYSTEM_DIR, 'templates'))
app.config['SECRET_KEY'] = 'bimoli_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

def send_discord(message):
    if not WEBHOOK_URL:
        return
    try: requests.post(WEBHOOK_URL, json={'content': message}, timeout=5)
    except: pass

def muat_konfigurasi():
    if os.path.exists(FILE_KONFIG):
        try:
            with open(FILE_KONFIG, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"suara": [], "kategori": ["Bimoli", "Gaming", "Meme", "Efek", "Lainnya"]}

def simpan_konfigurasi(konfig):
    with open(FILE_KONFIG, 'w', encoding='utf-8') as f: json.dump(konfig, f, indent=2, ensure_ascii=False)

def update_play_count(nama_file):
    try:
        konfig = muat_konfigurasi()
        for s in konfig['suara']:
            if s['nama_file'] == nama_file: s['jumlah_main'] = s.get('jumlah_main', 0) + 1
        simpan_konfigurasi(konfig)
    except: pass

def play_audio(file_path, volume=0.75):
    """
    Play audio dengan volume control yang BENER
    Volume: 0.0 - 1.0 (0.25 = 25%, 0.5 = 50%, 1.0 = 100%)
    """
    try:
        if not IS_WINDOWS: return False
        
        # Cari VLC
        vlc_exe = None
        for path in [r"C:\Program Files\VideoLAN\VLC\vlc.exe", r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"]:
            if os.path.exists(path):
                vlc_exe = path
                break
        
        if vlc_exe:
            # VLC volume: 0 = mute, 64 = 25%, 128 = 50%, 192 = 75%, 256 = 100%
            vlc_vol = int(volume * 256)
            
            cmd = [
                vlc_exe,
                '--play-and-exit',
                '--intf', 'dummy',
                '--no-video-title-show',
                '--qt-start-minimized',
                '--volume', str(vlc_vol),
                '--gain', str(volume),
                file_path
            ]
            
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        
        # Fallback: PowerShell dengan volume control
        vol = max(0.0, min(1.0, volume))
        ps = f'''
Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open("{file_path}")
$player.Volume = {vol}
$player.Play()
$duration = $player.NaturalDuration.TimeSpan.TotalSeconds
Start-Sleep -Seconds $duration
$player.Stop()
$player.Close()
'''
        encoded = base64.b64encode(ps.encode('utf-16le')).decode()
        subprocess.Popen(['powershell', '-WindowStyle', 'Hidden', '-NoProfile', '-EncodedCommand', encoded], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        return True
        
    except: return False

def mainkan_audio(nama_file, volume=None):
    try:
        file_path = os.path.join(FOLDER_SUARA, nama_file)
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path): return False
        
        if volume is None: volume = VOLUME_GLOBAL
        volume = max(0.0, min(1.0, volume))
        
        print(f"▶️ {nama_file} | Volume: {volume*100:.0f}%")
        
        threading.Thread(target=update_play_count, args=(nama_file,), daemon=True).start()
        
        if play_audio(file_path, volume): return True
        
        # Last resort
        os.startfile(file_path)
        return True
    except: return False

def hentikan_semua():
    if IS_WINDOWS:
        subprocess.run('taskkill /F /IM vlc.exe', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run('taskkill /F /IM wmplayer.exe', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run('taskkill /F /FI "WINDOWTITLE eq *PowerShell*"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(0)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

# ============================================================
# LIVE CHECK (server-side — no CORS limits, no API key needed)
# ============================================================

_YT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
}

def get_live_video_id(channel_handle=YT_CHANNEL_HANDLE):
    """
    Cek apakah channel lagi live dengan minta halaman /<handle>/live.
    - Kalau live: YouTube redirect ke https://www.youtube.com/watch?v=<ID>
      -> kita baca URL akhir setelah redirect.
    - Kalau nggak live: halaman tetap di /live (nggak redirect ke watch?v=...)
      -> kita coba fallback cari pola isLiveNow di HTML-nya, kalau nggak ada berarti offline.
    Ini jalan di server jadi nggak kena CORS seperti kalau dipanggil dari browser.
    """
    try:
        url = f"https://www.youtube.com/{channel_handle}/live"
        resp = requests.get(url, headers=_YT_HEADERS, timeout=8, allow_redirects=True)

        if "watch?v=" in resp.url:
            video_id = resp.url.split("watch?v=")[1].split("&")[0]
            return video_id

        # Fallback: parse HTML kalau redirect nggak kejadian tapi tetap live
        match = re.search(r'"videoId":"([^"]{6,20})"[^{]{0,600}"isLiveNow":true', resp.text)
        if match:
            return match.group(1)

        return None
    except Exception as e:
        print(f"⚠️ Gagal cek live: {e}")
        return None

# ============================================================
# WEBSOCKET
# ============================================================

@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'ok', 'volume': VOLUME_GLOBAL})

@socketio.on('play_sound')
def handle_play(data):
    nama_file = data.get('nama_file')
    volume = data.get('volume', VOLUME_GLOBAL)
    
    if not nama_file:
        emit('play_response', {'status': 'error'})
        return
    
    sukses = mainkan_audio(nama_file, volume)
    
    konfig = muat_konfigurasi()
    nama_suara = nama_file
    for s in konfig['suara']:
        if s['nama_file'] == nama_file:
            nama_suara = s['nama']
            break
    
    emit('play_response', {
        'status': 'ok' if sukses else 'error',
        'nama_file': nama_file,
        'nama_suara': nama_suara,
        'volume': volume
    })

@socketio.on('stop_all')
def handle_stop():
    hentikan_semua()
    emit('stop_response', {'status': 'ok'})

@socketio.on('set_volume')
def handle_volume(data):
    global VOLUME_GLOBAL
    try:
        VOLUME_GLOBAL = max(0.0, min(1.0, float(data.get('volume', 0.75))))
        print(f"🔊 Volume: {VOLUME_GLOBAL*100:.0f}%")
        emit('volume_changed', {'status': 'ok', 'volume': VOLUME_GLOBAL}, broadcast=True)
        
        # Simpan ke config
        konfig = muat_konfigurasi()
        if 'pengaturan' not in konfig: konfig['pengaturan'] = {}
        konfig['pengaturan']['volume'] = VOLUME_GLOBAL
        simpan_konfigurasi(konfig)
    except: pass

@socketio.on('get_sounds')
def handle_get_sounds():
    konfig = muat_konfigurasi()
    
    # Load volume dari config
    global VOLUME_GLOBAL
    if 'pengaturan' in konfig and 'volume' in konfig['pengaturan']:
        VOLUME_GLOBAL = konfig['pengaturan']['volume']
    
    emit('sounds_list', {
        'status': 'ok',
        'suara': konfig['suara'],
        'kategori': konfig['kategori'],
        'volume': VOLUME_GLOBAL
    })

@socketio.on('check_live')
def handle_check_live():
    """
    Dipanggil dari frontend saat user klik 'Cek Live'.
    Jalan di thread terpisah biar nggak nge-block koneksi socket lain
    selagi nunggu response dari youtube.com.
    """
    def _cek():
        video_id = get_live_video_id()
        socketio.emit('live_status', {'videoId': video_id})
        if video_id:
            print(f"🔴 Live terdeteksi: {video_id}")
        else:
            print("⚪ Channel sedang tidak live")
    threading.Thread(target=_cek, daemon=True).start()

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    ip = get_ip()
    return f"""<html><head><meta name="viewport" content="width=device-width,initial-scale=1.0"><style>body{{background:#1a1a2e;color:white;font-family:sans-serif;text-align:center;padding:50px;}}.card{{background:rgba(255,255,255,0.1);border-radius:20px;padding:30px;max-width:400px;margin:0 auto;}}h1{{font-size:22px;}}.status{{font-size:50px;margin:20px 0;}}.btn{{background:#e94560;color:white;padding:15px 30px;border-radius:10px;text-decoration:none;display:inline-block;margin-top:15px;font-weight:bold;}}span{{color:#0f0;}}</style></head><body><div class="card"><h1>✅ BIMOLI SOUNDBOARD</h1><div class="status">🟢</div><p>Server AKTIF!</p><p>IP: <span>{ip}</span> | Port: <span>{PORT}</span></p><p>URL: <span>http://{ip}:{PORT}</span></p><a href="/" class="btn">🔊 BUKA SOUNDBOARD</a></div></body></html>"""

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("\n🎵 BIMOLI SOUNDBOARD SERVER\n")
    
    # Load volume dari config
    konfig = muat_konfigurasi()
    if 'pengaturan' in konfig and 'volume' in konfig['pengaturan']:
        VOLUME_GLOBAL = konfig['pengaturan']['volume']
    
    ip = get_ip()
    send_discord(f"🟢 **Soundboard Server Aktif!**\n📱 **URL:** http://{ip}:{PORT}\n🔊 Volume: {VOLUME_GLOBAL*100:.0f}%\n⏰ {datetime.now().strftime('%H:%M:%S')}")
    
    print(f"📱 HP: http://{ip}:{PORT}")
    print(f"🔊 Volume default: {VOLUME_GLOBAL*100:.0f}%")
    print("🔴 Ctrl+C to stop\n")
    
    if IS_WINDOWS:
        subprocess.run(f'netsh advfirewall firewall add rule name="Bimoli" dir=in action=allow protocol=TCP localport={PORT}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
