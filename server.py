#!/usr/bin/env python3
"""
🎵 BIMOLI SOUNDBOARD SERVER
Auto-Update | Hidden System | Volume Control
"""

import os
import sys
import json
import threading
import subprocess
import platform
import socket
import re

# ============================================================
# KONFIGURASI PATH (Support Hidden System Folder)
# ============================================================

SYSTEM_DIR = os.environ.get('BIMOLI_SYSTEM_DIR', '.bimoli_system')
BASE_DIR = os.environ.get('BIMOLI_BASE_DIR', os.path.dirname(os.path.abspath(__file__)))

# Tambah system dir ke path biar bisa import
sys.path.insert(0, SYSTEM_DIR)

# ============================================================
# IMPORT FLASK
# ============================================================

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# ============================================================
# INISIALISASI
# ============================================================

app = Flask(__name__, template_folder=os.path.join(SYSTEM_DIR, 'templates'))
app.config['SECRET_KEY'] = 'bimoli_soundboard_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=60)

# ============================================================
# KONFIGURASI
# ============================================================

FOLDER_SUARA = os.path.join(BASE_DIR, "suara")
FOLDER_SUARA_BARU = os.path.join(BASE_DIR, "suara_baru")
FOLDER_DOWNLOAD = os.path.join(BASE_DIR, "downloads")
FILE_KONFIG = os.path.join(BASE_DIR, "config.json")
IS_WINDOWS = platform.system() == "Windows"
PORT = 5000
VOLUME_GLOBAL = 1.0

# Tracking proses yang lagi jalan
proses_aktif = {}

# ============================================================
# FUNGSI UTILITY
# ============================================================

def get_local_ip():
    """Auto detect IP lokal"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith("192.168."):
            return ip
    except:
        pass
    
    try:
        hostname = socket.gethostname()
        ip_list = socket.gethostbyname_ex(hostname)[2]
        for ip in ip_list:
            if ip.startswith("192.168."):
                return ip
        for ip in ip_list:
            if not ip.startswith("127."):
                return ip
    except:
        pass
    
    if IS_WINDOWS:
        try:
            result = subprocess.run("ipconfig", shell=True, capture_output=True, text=True)
            pattern = r"IPv4 Address[.\s]*:\s*(\d+\.\d+\.\d+\.\d+)"
            matches = re.findall(pattern, result.stdout)
            for ip in matches:
                if ip.startswith("192.168."):
                    return ip
            for ip in matches:
                if not ip.startswith("127.") and ip != "0.0.0.0":
                    return ip
        except:
            pass
    
    return "127.0.0.1"

def muat_konfigurasi():
    """Muat konfigurasi soundboard"""
    if os.path.exists(FILE_KONFIG):
        try:
            with open(FILE_KONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "suara": [],
        "kategori": ["Bimoli", "Gaming", "Meme", "Efek", "Lainnya"],
        "pengaturan": {
            "volume": 1.0,
            "auto_deteksi": True,
            "port_server": 5000
        }
    }

def simpan_konfigurasi(konfig):
    """Simpan konfigurasi"""
    try:
        with open(FILE_KONFIG, 'w', encoding='utf-8') as f:
            json.dump(konfig, f, indent=2, ensure_ascii=False)
    except:
        pass

def update_play_count(nama_file):
    """Update jumlah main"""
    try:
        konfig = muat_konfigurasi()
        for s in konfig['suara']:
            if s['nama_file'] == nama_file:
                s['jumlah_main'] = s.get('jumlah_main', 0) + 1
        simpan_konfigurasi(konfig)
    except:
        pass

# ============================================================
# AUDIO PLAYER
# ============================================================

def play_with_vlc(file_path, volume=1.0):
    """Play audio dengan VLC + volume control"""
    try:
        if IS_WINDOWS:
            vlc_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
            ]
            
            vlc_exe = None
            for path in vlc_paths:
                if os.path.exists(path):
                    vlc_exe = path
                    break
            
            if vlc_exe:
                volume_persen = int(volume * 100)
                
                # Escape path
                safe_path = file_path.replace('"', '\\"')
                
                cmd = (
                    f'"{vlc_exe}" '
                    f'--play-and-exit '
                    f'--intf dummy '
                    f'--no-video-title-show '
                    f'--qt-start-minimized '
                    f'--volume {volume_persen} '
                    f'"{safe_path}"'
                )
                
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
                )
                
                proses_aktif[file_path] = process
                return True
    except Exception as e:
        print(f"VLC error: {e}")
    return False

def play_with_windows_media(file_path):
    """Fallback: Windows Media Player"""
    try:
        if IS_WINDOWS:
            cmd = f'wmplayer /play /close "{file_path}"'
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            proses_aktif[file_path] = process
            return True
    except:
        pass
    return False

def mainkan_audio(nama_file, volume=None):
    """Mainkan audio dengan volume control"""
    try:
        file_path = os.path.join(FOLDER_SUARA, nama_file)
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            print(f"File tidak ditemukan: {file_path}")
            return False
        
        if volume is None:
            volume = VOLUME_GLOBAL
        
        volume = max(0.0, min(1.0, volume))
        
        print(f"▶️ Memainkan: {nama_file} (volume: {volume*100:.0f}%)")
        
        # Update play count di background
        threading.Thread(target=update_play_count, args=(nama_file,), daemon=True).start()
        
        # Coba VLC dulu
        if play_with_vlc(file_path, volume):
            return True
        
        # Fallback Windows Media Player
        if play_with_windows_media(file_path):
            return True
        
        # Last resort
        if IS_WINDOWS:
            os.startfile(file_path)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error mainkan audio: {e}")
        return False

def hentikan_semua():
    """Stop semua audio"""
    try:
        if IS_WINDOWS:
            subprocess.run(
                'taskkill /F /IM vlc.exe',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.run(
                'taskkill /F /IM wmplayer.exe',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        
        proses_aktif.clear()
        print("⏹️ Semua suara dihentikan")
        return True
    except:
        return False

# ============================================================
# WEBSOCKET EVENTS
# ============================================================

@socketio.on('connect')
def handle_connect():
    """Client terhubung"""
    client_ip = None
    try:
        from flask import request
        client_ip = request.remote_addr
    except:
        pass
    
    print(f"📱 HP terhubung! {f'({client_ip})' if client_ip else ''}")
    
    emit('connected', {
        'status': 'ok',
        'message': 'Terhubung ke Bimoli Soundboard!',
        'volume': VOLUME_GLOBAL
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Client terputus"""
    print("📱 HP terputus!")

@socketio.on('play_sound')
def handle_play_sound(data):
    """Mainkan suara"""
    try:
        nama_file = data.get('nama_file')
        volume = data.get('volume', VOLUME_GLOBAL)
        
        if not nama_file:
            emit('play_response', {
                'status': 'error',
                'message': 'Nama file tidak valid'
            })
            return
        
        # Mainkan audio
        sukses = mainkan_audio(nama_file, volume)
        
        # Cari nama suara
        konfig = muat_konfigurasi()
        nama_suara = nama_file.replace('.mp3', '').replace('.wav', '').replace('.ogg', '')
        for s in konfig['suara']:
            if s['nama_file'] == nama_file:
                nama_suara = s['nama']
                break
        
        if sukses:
            emit('play_response', {
                'status': 'ok',
                'message': f'Memainkan: {nama_suara}',
                'nama_file': nama_file,
                'nama_suara': nama_suara,
                'volume': volume
            })
        else:
            emit('play_response', {
                'status': 'error',
                'message': 'Gagal memainkan suara'
            })
            
    except Exception as e:
        print(f"Error play_sound: {e}")
        emit('play_response', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('stop_all')
def handle_stop_all():
    """Stop semua suara"""
    try:
        hentikan_semua()
        emit('stop_response', {
            'status': 'ok',
            'message': 'Semua suara dihentikan'
        })
    except Exception as e:
        emit('stop_response', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('set_volume')
def handle_set_volume(data):
    """Set volume global"""
    global VOLUME_GLOBAL
    
    try:
        volume = float(data.get('volume', 1.0))
        volume = max(0.0, min(1.0, volume))
        
        VOLUME_GLOBAL = volume
        
        print(f"🔊 Volume diubah ke: {volume*100:.0f}%")
        
        emit('volume_changed', {
            'status': 'ok',
            'volume': volume,
            'message': f'Volume: {volume*100:.0f}%'
        }, broadcast=True)
        
    except Exception as e:
        emit('volume_changed', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('get_sounds')
def handle_get_sounds():
    """Kirim daftar suara"""
    try:
        konfig = muat_konfigurasi()
        
        # Update info file (ukuran, dll)
        for s in konfig['suara']:
            file_path = os.path.join(FOLDER_SUARA, s['nama_file'])
            if os.path.exists(file_path):
                s['ukuran_kb'] = os.path.getsize(file_path) / 1024
            else:
                s['file_hilang'] = True
        
        emit('sounds_list', {
            'status': 'ok',
            'suara': konfig['suara'],
            'kategori': konfig['kategori'],
            'volume': VOLUME_GLOBAL
        })
        
    except Exception as e:
        print(f"Error get_sounds: {e}")
        emit('sounds_list', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('ping_server')
def handle_ping():
    """Ping buat cek koneksi"""
    emit('pong', {'status': 'ok', 'timestamp': __import__('time').time()})

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    """Halaman utama soundboard"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Halaman test koneksi"""
    ip = get_local_ip()
    return f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test - Bimoli Soundboard</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .card {{
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                padding: 40px 30px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
                text-align: center;
                max-width: 400px;
                width: 100%;
            }}
            h1 {{ font-size: 24px; margin-bottom: 15px; }}
            .status {{ font-size: 60px; margin: 20px 0; }}
            .info {{
                background: rgba(0,0,0,0.3);
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                font-size: 14px;
                text-align: left;
                line-height: 1.6;
            }}
            .info span {{ color: #00ff00; font-weight: bold; }}
            .btn {{
                display: inline-block;
                background: #e94560;
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                font-size: 18px;
                font-weight: bold;
                margin-top: 15px;
                transition: all 0.3s;
            }}
            .btn:hover {{ background: #c73e54; }}
            .hint {{
                font-size: 12px;
                color: #a8b2d1;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>✅ BIMOLI SOUNDBOARD</h1>
            <div class="status">🟢</div>
            <p style="font-size: 18px; margin-bottom: 10px;">Server AKTIF!</p>
            <div class="info">
                <p>🔗 IP PC: <span>{ip}</span></p>
                <p>🔌 Port: <span>{PORT}</span></p>
                <p>📱 URL: <span>http://{ip}:{PORT}</span></p>
            </div>
            <a href="/" class="btn">🔊 BUKA SOUNDBOARD</a>
            <div class="hint">
                💡 Tips: Buka URL di atas dari HP kamu<br>
                HP & PC harus terhubung ke WiFi yang sama
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/api/suara')
def api_suara():
    """API daftar suara (fallback)"""
    konfig = muat_konfigurasi()
    return json.dumps(konfig, ensure_ascii=False)

@app.route('/api/status')
def api_status():
    """API status server"""
    konfig = muat_konfigurasi()
    return json.dumps({
        'status': 'ok',
        'jumlah_suara': len(konfig['suara']),
        'volume': VOLUME_GLOBAL,
        'vlc_tersedia': any(os.path.exists(p) for p in [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
        ]),
        'ip': get_local_ip(),
        'port': PORT
    }, ensure_ascii=False)

# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return """
    <html>
    <body style="background:#1a1a2e;color:white;font-family:sans-serif;text-align:center;padding:50px;">
        <h1>404 - Halaman tidak ditemukan</h1>
        <p>Kembali ke <a href="/" style="color:#e94560;">Soundboard</a></p>
    </body>
    </html>
    """, 404

@app.errorhandler(500)
def server_error(e):
    return """
    <html>
    <body style="background:#1a1a2e;color:white;font-family:sans-serif;text-align:center;padding:50px;">
        <h1>500 - Server Error</h1>
        <p>Coba restart server</p>
    </body>
    </html>
    """, 500

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════╗
║                                                  ║
║     🎵 BIMOLI SOUNDBOARD SERVER 🎵              ║
║              v1.0.0                              ║
║                                                  ║
╚══════════════════════════════════════════════════╝
    """)
    
    # Pastikan folder suara ada
    for folder in [FOLDER_SUARA, FOLDER_SUARA_BARU, FOLDER_DOWNLOAD]:
        os.makedirs(folder, exist_ok=True)
    
    # Dapetin IP
    ip_lokal = get_local_ip()
    
    print(f"""
╔══════════════════════════════════════════════════╗
║           📱 INFORMASI KONEKSI                  ║
╠══════════════════════════════════════════════════╣
║  IP PC      : {ip_lokal:<32} ║
║  Port       : {PORT:<32} ║
║  URL HP     : http://{ip_lokal}:{PORT:<26} ║
║  Test URL   : http://{ip_lokal}:{PORT}/test{'':<23} ║
╚══════════════════════════════════════════════════╝
    """)
    
    # Cek VLC
    vlc_paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
    ]
    vlc_ada = any(os.path.exists(p) for p in vlc_paths)
    
    if vlc_ada:
        print("✅ VLC Terdeteksi! Volume control AKTIF!\n")
    else:
        print("⚠️  VLC tidak terdeteksi")
        print("💡 Install VLC untuk volume control & suara lebih responsif")
        print("   Download: https://www.videolan.org/vlc/\n")
    
    # Buka firewall
    print("🔧 Konfigurasi firewall...")
    try:
        subprocess.run(
            f'netsh advfirewall firewall add rule name="Bimoli Soundboard" dir=in action=allow protocol=TCP localport={PORT}',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("✅ Firewall OK!\n")
    except:
        pass
    
    print("📋 CARA AKSES:")
    print(f"   1. HP & PC harus 1 WiFi")
    print(f"   2. Buka browser di HP")
    print(f"   3. Ketik: http://{ip_lokal}:{PORT}")
    print(f"   4. Atau test dulu: http://{ip_lokal}:{PORT}/test")
    print()
    print("🔴 Tekan Ctrl+C untuk berhenti")
    print("="*50 + "\n")
    
    # Jalankan server
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=PORT,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except OSError as e:
        if "Address already in use" in str(e) or "10048" in str(e):
            print(f"\n❌ ERROR: Port {PORT} sudah digunakan!")
            print("   Tutup program lain yang pakai port 5000")
            print("   Atau restart komputer")
        else:
            print(f"\n❌ ERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Server dihentikan")
        sys.exit(0)