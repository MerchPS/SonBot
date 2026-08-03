#!/usr/bin/env python3
"""
🎵 BIMOLI SOUNDBOARD SERVER
Volume Control Fixed!
"""

import os
import sys
import json
import threading
import subprocess
import platform
import socket
import re

# Path dari launcher
SYSTEM_DIR = os.environ.get('BIMOLI_SYSTEM_DIR', '.bimoli_system')
BASE_DIR = os.environ.get('BIMOLI_BASE_DIR', os.getcwd())

sys.path.insert(0, SYSTEM_DIR)

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Inisialisasi
app = Flask(__name__, template_folder=os.path.join(SYSTEM_DIR, 'templates'))
app.config['SECRET_KEY'] = 'bimoli_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Konfigurasi
FOLDER_SUARA = os.path.join(BASE_DIR, "suara")
FILE_KONFIG = os.path.join(BASE_DIR, "config.json")
IS_WINDOWS = platform.system() == "Windows"
PORT = 5000
VOLUME_GLOBAL = 0.75  # Default 75%

# ============================================================

def muat_konfigurasi():
    if os.path.exists(FILE_KONFIG):
        try:
            with open(FILE_KONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"suara": [], "kategori": ["Bimoli", "Gaming", "Meme", "Efek", "Lainnya"]}

def simpan_konfigurasi(konfig):
    with open(FILE_KONFIG, 'w', encoding='utf-8') as f:
        json.dump(konfig, f, indent=2, ensure_ascii=False)

def update_play_count(nama_file):
    try:
        konfig = muat_konfigurasi()
        for s in konfig['suara']:
            if s['nama_file'] == nama_file:
                s['jumlah_main'] = s.get('jumlah_main', 0) + 1
        simpan_konfigurasi(konfig)
    except:
        pass

def play_with_vlc(file_path, volume=0.75):
    """
    Play audio dengan VLC + volume control
    Volume: 0.0 - 1.0 (0.25 = 25%, 0.5 = 50%, 1.0 = 100%)
    """
    try:
        if not IS_WINDOWS:
            return False
        
        # Cari VLC
        vlc_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
        ]
        vlc_exe = None
        for path in vlc_paths:
            if os.path.exists(path):
                vlc_exe = path
                break
        
        if not vlc_exe:
            return False
        
        # Konversi volume ke skala VLC
        # VLC: 0 = mute, 256 = 100%, 512 = 200%, 1024 = 400%
        # Kita pake 0-256 (0% - 100%)
        vlc_volume = int(volume * 256)
        
        # Bikin command VLC
        cmd = [
            vlc_exe,
            '--play-and-exit',           # Keluar setelah selesai
            '--intf', 'dummy',            # No interface
            '--no-video-title-show',      # Gak tampilin judul
            '--qt-start-minimized',       # Minimize window
            '--volume', str(vlc_volume),  # Volume! (0-256)
            '--gain', str(volume),        # Gain multiplier
            file_path
        ]
        
        # Jalankan VLC
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        return True
        
    except Exception as e:
        print(f"VLC error: {e}")
        return False

def play_with_powershell(file_path, volume=0.75):
    """
    Play audio dengan PowerShell (Windows built-in)
    Support volume control!
    """
    try:
        if not IS_WINDOWS:
            return False
        
        # Konversi volume (0.0 - 1.0)
        vol = max(0.0, min(1.0, volume))
        
        # PowerShell script dengan volume control
        ps_script = f'''
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
        
        # Encode ke base64 biar aman
        import base64
        encoded = base64.b64encode(ps_script.encode('utf-16le')).decode()
        
        subprocess.Popen(
            ['powershell', '-WindowStyle', 'Hidden', '-NoProfile', '-EncodedCommand', encoded],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        return True
        
    except Exception as e:
        print(f"PowerShell error: {e}")
        return False

def mainkan_audio(nama_file, volume=None):
    """Mainkan audio dengan volume"""
    try:
        file_path = os.path.join(FOLDER_SUARA, nama_file)
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            print(f"❌ File tidak ditemukan: {nama_file}")
            return False
        
        if volume is None:
            volume = VOLUME_GLOBAL
        
        volume = max(0.0, min(1.0, volume))
        
        print(f"▶️ {nama_file} | Volume: {volume*100:.0f}%")
        
        # Update play count
        threading.Thread(target=update_play_count, args=(nama_file,), daemon=True).start()
        
        # Coba VLC dulu (volume control lebih baik)
        if play_with_vlc(file_path, volume):
            return True
        
        # Coba PowerShell (Windows built-in)
        if play_with_powershell(file_path, volume):
            return True
        
        # Fallback: Windows Media Player (gak ada volume control)
        print("⚠️  Fallback ke default player (tanpa volume control)")
        os.startfile(file_path)
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def hentikan_semua():
    """Stop semua audio"""
    if IS_WINDOWS:
        subprocess.run(
            'taskkill /F /IM vlc.exe',
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        subprocess.run(
            'taskkill /F /IM wmplayer.exe',
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # Stop PowerShell audio players
        subprocess.run(
            'taskkill /F /FI "WINDOWTITLE eq powershell*"',
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    print("⏹️ Semua suara dihentikan")

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ============================================================
# WEBSOCKET
# ============================================================

@socketio.on('connect')
def handle_connect():
    print("📱 HP Connected!")
    emit('connected', {
        'status': 'ok',
        'volume': VOLUME_GLOBAL
    })

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
        new_vol = float(data.get('volume', 0.75))
        VOLUME_GLOBAL = max(0.0, min(1.0, new_vol))
        print(f"🔊 Volume diubah: {VOLUME_GLOBAL*100:.0f}%")
        
        # Broadcast ke semua client
        emit('volume_changed', {
            'status': 'ok',
            'volume': VOLUME_GLOBAL
        }, broadcast=True)
        
        # Update config
        try:
            konfig = muat_konfigurasi()
            if 'pengaturan' not in konfig:
                konfig['pengaturan'] = {}
            konfig['pengaturan']['volume'] = VOLUME_GLOBAL
            simpan_konfigurasi(konfig)
        except:
            pass
        
    except:
        pass

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

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    ip = get_ip()
    return f"""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>
        body{{background:#1a1a2e;color:white;font-family:sans-serif;text-align:center;padding:50px;}}
        .card{{background:rgba(255,255,255,0.1);border-radius:20px;padding:30px;max-width:400px;margin:0 auto;}}
        h1{{font-size:22px;}}.status{{font-size:50px;margin:20px 0;}}
        .btn{{background:#e94560;color:white;padding:15px 30px;border-radius:10px;text-decoration:none;display:inline-block;margin-top:15px;font-weight:bold;}}
        span{{color:#0f0;}}
    </style></head><body>
    <div class="card">
        <h1>✅ BIMOLI SOUNDBOARD</h1>
        <div class="status">🟢</div>
        <p>Server AKTIF!</p>
        <p>IP: <span>{ip}</span> | Port: <span>{PORT}</span></p>
        <p>URL: <span>http://{ip}:{PORT}</span></p>
        <a href="/" class="btn">🔊 BUKA SOUNDBOARD</a>
    </div></body></html>"""

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("\n🎵 BIMOLI SOUNDBOARD SERVER\n")
    
    # Load config
    konfig = muat_konfigurasi()
    if 'pengaturan' in konfig and 'volume' in konfig['pengaturan']:
        VOLUME_GLOBAL = konfig['pengaturan']['volume']
    
    ip = get_ip()
    print(f"📱 HP: http://{ip}:{PORT}")
    print(f"🔊 Volume default: {VOLUME_GLOBAL*100:.0f}%")
    print("🔴 Ctrl+C to stop\n")
    
    # Buka firewall
    if IS_WINDOWS:
        subprocess.run(
            f'netsh advfirewall firewall add rule name="Bimoli" dir=in action=allow protocol=TCP localport={PORT}',
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
