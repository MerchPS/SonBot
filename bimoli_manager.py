#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║     🎵 BIMOLI SOUNDBOARD MANAGER 🎵        ║
║     YouTube Downloader (yt-dlp)             ║
╚══════════════════════════════════════════════╝
"""

import os
import sys
import json
import shutil
import time
import re
import traceback
from datetime import datetime
import subprocess

# Path dari launcher
SYSTEM_DIR = os.environ.get('BIMOLI_SYSTEM_DIR', '.bimoli_system')
BASE_DIR = os.environ.get('BIMOLI_BASE_DIR', os.getcwd())

# Konfigurasi
FOLDER_SUARA = os.path.join(BASE_DIR, "suara")
FOLDER_SUARA_BARU = os.path.join(BASE_DIR, "suara_baru")
FOLDER_DOWNLOAD = os.path.join(BASE_DIR, "downloads")
FILE_KONFIG = os.path.join(BASE_DIR, "config.json")
ERROR_LOG = os.path.join(BASE_DIR, "error.log")
FORMAT_DIDUKUNG = ['.mp3', '.wav', '.ogg', '.m4a', '.mp4', '.webm']

# Warna
class Warna:
    UNGU = '\033[95m'
    BIRU = '\033[94m'
    CYAN = '\033[96m'
    HIJAU = '\033[92m'
    KUNING = '\033[93m'
    MERAH = '\033[91m'
    PUTIH = '\033[97m'
    TEBAL = '\033[1m'
    RESET = '\033[0m'

# ============================================================
# ERROR LOGGING
# ============================================================

def tulis_log(pesan, tipe="INFO"):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{tipe}] {pesan}\n")
    except:
        pass

def tulis_error(error, lokasi=""):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{timestamp}] [ERROR] Lokasi: {lokasi}\n")
            f.write(f"Error: {str(error)}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")
            f.write(f"{'='*60}\n\n")
    except:
        pass

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
║         YouTube Downloader (yt-dlp)             ║
╚══════════════════════════════════════════════════╝
{Warna.RESET}
    """)

def muat_konfigurasi():
    try:
        if os.path.exists(FILE_KONFIG):
            with open(FILE_KONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {
        "suara": [],
        "kategori": ["Bimoli", "Gaming", "Meme", "Efek", "Lainnya"],
        "pengaturan": {"volume": 1.0}
    }

def simpan_konfigurasi(konfig):
    try:
        with open(FILE_KONFIG, 'w', encoding='utf-8') as f:
            json.dump(konfig, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

# ============================================================
# CEK & INSTALL yt-dlp
# ============================================================

def cek_ytdlp():
    """Cek yt-dlp terinstall"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"{Warna.HIJAU}✅ yt-dlp v{version} terdeteksi{Warna.RESET}")
            return True
    except:
        pass
    return False

def cek_ffmpeg():
    """Cek ffmpeg terinstall"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print(f"{Warna.HIJAU}✅ ffmpeg terdeteksi (kualitas MP3 terbaik){Warna.RESET}")
            return True
    except:
        pass
    
    # Cek di folder system
    ffmpeg_path = os.path.join(SYSTEM_DIR, "ffmpeg.exe")
    if os.path.exists(ffmpeg_path):
        print(f"{Warna.HIJAU}✅ ffmpeg terdeteksi (local){Warna.RESET}")
        return True
    
    return False

def install_ytdlp():
    """Install/Update yt-dlp"""
    print(f"\n{Warna.KUNING}📦 Install yt-dlp...{Warna.RESET}")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            check=True, shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"{Warna.HIJAU}✅ yt-dlp terinstall!{Warna.RESET}")
        return True
    except:
        print(f"{Warna.MERAH}❌ Gagal install yt-dlp{Warna.RESET}")
        print(f"{Warna.KUNING}💡 Coba manual: pip install yt-dlp{Warna.RESET}")
        return False

# ============================================================
# DOWNLOAD YOUTUBE (yt-dlp)
# ============================================================

def download_youtube(url, nama_kustom=None):
    """
    Download YouTube pakai yt-dlp
    - Otomatis convert ke MP3
    - Support ffmpeg (kualitas lebih bagus)
    """
    try:
        print(f"\n{Warna.CYAN}⏳ Download dari YouTube...{Warna.RESET}")
        tulis_log(f"Mulai download: {url}", "DOWNLOAD")
        
        os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
        
        # Template output
        if nama_kustom:
            nama_bersih = re.sub(r'[<>:"/\\|?*]', '', nama_kustom)[:50]
            output_template = os.path.join(FOLDER_DOWNLOAD, f"{nama_bersih}.%(ext)s")
        else:
            output_template = os.path.join(FOLDER_DOWNLOAD, "%(title).50s.%(ext)s")
        
        # Command yt-dlp
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-x",                      # Extract audio
            "--audio-format", "mp3",   # Format MP3
            "--audio-quality", "0",    # Best quality
            "-o", output_template,     # Output
            "--no-playlist",           # Jangan download playlist
            "--no-warnings",
            "--no-check-certificate",
            url
        ]
        
        # Kalo ada ffmpeg, tambahin opsi
        ffmpeg_path = os.path.join(SYSTEM_DIR, "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            cmd.extend(["--ffmpeg-location", ffmpeg_path])
        
        print(f"{Warna.PUTIH}📥 Downloading...{Warna.RESET}")
        print(f"{Warna.KUNING}(Tunggu ya, tergantung ukuran video){Warna.RESET}\n")
        
        # Jalankan download
        result = subprocess.run(
            cmd,
            check=True,
            timeout=300,  # 5 menit max
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        
        # Cari file yang didownload
        downloaded = []
        for f in os.listdir(FOLDER_DOWNLOAD):
            if f.endswith('.mp3'):
                fp = os.path.join(FOLDER_DOWNLOAD, f)
                downloaded.append((fp, os.path.getmtime(fp)))
        
        if downloaded:
            # Ambil file terbaru
            downloaded.sort(key=lambda x: x[1], reverse=True)
            file_path = downloaded[0][0]
            ukuran = os.path.getsize(file_path) / 1024
            
            print(f"\n{Warna.HIJAU}✅ Download berhasil!{Warna.RESET}")
            print(f"{Warna.PUTIH}📁 {os.path.basename(file_path)} ({ukuran:.0f} KB){Warna.RESET}")
            
            tulis_log(f"Download sukses: {file_path} ({ukuran:.0f} KB)", "SUKSES")
            return file_path
        
        print(f"\n{Warna.MERAH}❌ File tidak ditemukan!{Warna.RESET}")
        tulis_log("File MP3 tidak ditemukan setelah download", "ERROR")
        return None
        
    except subprocess.TimeoutExpired:
        print(f"\n{Warna.MERAH}❌ Download timeout (terlalu lama){Warna.RESET}")
        tulis_error("Timeout", "download_youtube")
        return None
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stdout.decode() if e.stdout else str(e)
        
        print(f"\n{Warna.MERAH}❌ Download gagal!{Warna.RESET}")
        
        # Cek error spesifik
        if "HTTP Error 400" in error_msg:
            print(f"{Warna.KUNING}💡 Video mungkin tidak tersedia atau private{Warna.RESET}")
        elif "ffprobe" in error_msg or "ffmpeg" in error_msg:
            print(f"{Warna.KUNING}💡 ffmpeg tidak terinstall{Warna.RESET}")
            print(f"{Warna.PUTIH}   Download: https://www.gyan.dev/ffmpeg/builds/{Warna.RESET}")
            print(f"{Warna.PUTIH}   Atau coba download tanpa convert{Warna.RESET}")
        elif "HTTP Error 403" in error_msg:
            print(f"{Warna.KUNING}💡 Video dibatasi usia/region{Warna.RESET}")
        else:
            print(f"{Warna.KUNING}💡 Error: {error_msg[:200]}{Warna.RESET}")
        
        tulis_error(error_msg[:500], "download_youtube - yt-dlp")
        return None
        
    except Exception as e:
        print(f"\n{Warna.MERAH}❌ Error: {e}{Warna.RESET}")
        tulis_error(e, "download_youtube")
        return None

# ============================================================
# TAMBAH SUARA
# ============================================================

def tambahkan_suara(filepath, nama, konfig, sumber="local"):
    """Tambah suara ke soundboard"""
    try:
        ext = os.path.splitext(filepath)[1]
        nama_bersih = re.sub(r'[<>:"/\\|?*]', '', nama.lower().replace(' ', '_'))[:30]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nama_file_baru = f"bimoli_{nama_bersih}_{timestamp}{ext}"
        tujuan = os.path.join(FOLDER_SUARA, nama_file_baru)
        
        shutil.copy2(filepath, tujuan)
        
        # Pilih kategori
        print(f"\n{Warna.CYAN}📂 Pilih kategori:{Warna.RESET}")
        for i, kat in enumerate(konfig['kategori'], 1):
            print(f"  {i}. {kat}")
        
        try:
            pilihan = input(f"\n{Warna.TEBAL}Pilih [Enter=Bimoli]: {Warna.RESET}").strip()
            if pilihan == '':
                kategori = "Bimoli"
            elif pilihan.isdigit() and 1 <= int(pilihan) <= len(konfig['kategori']):
                kategori = konfig['kategori'][int(pilihan)-1]
            else:
                kategori = "Bimoli"
        except:
            kategori = "Bimoli"
        
        info = {
            "id": len(konfig['suara']) + 1,
            "nama": nama,
            "nama_file": nama_file_baru,
            "kategori": kategori,
            "ditambahkan": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "jumlah_main": 0,
            "ukuran_kb": os.path.getsize(tujuan) / 1024,
            "sumber": sumber
        }
        
        konfig['suara'].append(info)
        simpan_konfigurasi(konfig)
        
        # Hapus file asli
        if os.path.exists(filepath) and (FOLDER_DOWNLOAD in filepath or FOLDER_SUARA_BARU in filepath):
            os.remove(filepath)
        
        print(f"\n{Warna.HIJAU}{Warna.TEBAL}")
        print(f"╔══════════════════════════════════════════════════╗")
        print(f"║  ✅ SUKSES!                                     ║")
        print(f"║  🎵 {nama:<40} ║")
        print(f"║  📂 {kategori:<40} ║")
        print(f"║  🏷️  {sumber:<40} ║")
        print(f"╚══════════════════════════════════════════════════╝")
        print(f"{Warna.RESET}")
        
        return True
        
    except Exception as e:
        tulis_error(e, "tambahkan_suara")
        print(f"{Warna.MERAH}❌ Gagal: {e}{Warna.RESET}")
        return False

# ============================================================
# MENU YOUTUBE
# ============================================================

def menu_youtube(konfig):
    """Menu download YouTube"""
    print(f"\n{Warna.CYAN}{Warna.TEBAL}")
    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║        🎬 YOUTUBE → MP3 DOWNLOADER             ║")
    print(f"╚══════════════════════════════════════════════════╝")
    print(f"{Warna.RESET}")
    
    # Cek & install yt-dlp
    if not cek_ytdlp():
        print(f"\n{Warna.KUNING}📦 yt-dlp belum terinstall{Warna.RESET}")
        p = input("Install sekarang? (y/n): ").strip().lower()
        if p == 'y':
            if not install_ytdlp():
                return
        else:
            print(f"{Warna.KUNING}💡 Install manual: pip install yt-dlp{Warna.RESET}")
            return
    
    # Cek ffmpeg
    ffmpeg_ada = cek_ffmpeg()
    if not ffmpeg_ada:
        print(f"{Warna.KUNING}⚠️  ffmpeg tidak terdeteksi{Warna.RESET}")
        print(f"{Warna.PUTIH}   Download MP3 tetap bisa, tapi kualitas lebih baik dengan ffmpeg{Warna.RESET}")
        print(f"{Warna.PUTIH}   Download ffmpeg: https://www.gyan.dev/ffmpeg/builds/{Warna.RESET}\n")
    
    while True:
        print(f"\n{Warna.TEBAL}Masukkan URL YouTube:{Warna.RESET}")
        print(f"{Warna.KUNING}(atau ketik 'batal' untuk kembali){Warna.RESET}")
        url = input(f"{Warna.PUTIH}▶️  URL: {Warna.RESET}").strip()
        
        if url.lower() == 'batal':
            return
        
        if not url:
            print(f"{Warna.MERAH}❌ URL kosong!{Warna.RESET}")
            continue
        
        # Support berbagai format URL
        if not ('youtube.com' in url or 'youtu.be' in url):
            print(f"{Warna.KUNING}⚠️  Bukan URL YouTube?{Warna.RESET}")
            lanjut = input("Tetap download? (y/n): ").strip().lower()
            if lanjut != 'y':
                continue
        
        # Nama kustom
        print(f"\n{Warna.CYAN}Nama untuk sound ini (opsional):{Warna.RESET}")
        nama_kustom = input(f"{Warna.PUTIH}Nama: {Warna.RESET}").strip()
        
        # Download!
        file_path = download_youtube(url, nama_kustom if nama_kustom else None)
        
        if not file_path:
            print(f"\n{Warna.MERAH}❌ Download gagal!{Warna.RESET}")
            print(f"{Warna.KUNING}💡 Cek error.log untuk detail{Warna.RESET}")
            coba_lagi = input("\nCoba lagi? (y/n): ").strip().lower()
            if coba_lagi != 'y':
                return
            continue
        
        # Tambah ke soundboard
        nama_file = os.path.basename(file_path)
        nama_saran = os.path.splitext(nama_file)[0].replace('_', ' ').replace('-', ' ').title()
        
        if len(nama_saran) > 50:
            nama_saran = nama_saran[:47] + "..."
        
        print(f"\n{Warna.KUNING}💡 Nama saran: {nama_saran}{Warna.RESET}")
        ganti = input("Ganti nama? (y/n): ").strip().lower()
        if ganti == 'y':
            nama_final = input(f"{Warna.PUTIH}Nama baru: {Warna.RESET}").strip()
            if not nama_final:
                nama_final = nama_saran
        else:
            nama_final = nama_saran
        
        tambahkan_suara(file_path, nama_final, konfig, "youtube")
        
        lagi = input(f"\n{Warna.CYAN}Download video lain? (y/n): {Warna.RESET}").strip().lower()
        if lagi != 'y':
            break

# ============================================================
# MENU UTAMA
# ============================================================

def menu_utama():
    konfig = muat_konfigurasi()
    
    while True:
        tampilkan_banner()
        
        # Cek suara baru di folder
        file_baru = []
        if os.path.exists(FOLDER_SUARA_BARU):
            for f in os.listdir(FOLDER_SUARA_BARU):
                fp = os.path.join(FOLDER_SUARA_BARU, f)
                if os.path.isfile(fp) and any(f.lower().endswith(ext) for ext in FORMAT_DIDUKUNG):
                    file_baru.append(fp)
        
        if file_baru:
            print(f"\n{Warna.KUNING}{Warna.TEBAL}📁 {len(file_baru)} FILE BARU TERDETEKSI!{Warna.RESET}")
            for fp in file_baru:
                nama_file = os.path.basename(fp)
                ukuran = os.path.getsize(fp) / 1024
                nama_saran = os.path.splitext(nama_file)[0].replace('_', ' ').title()
                
                print(f"\n{Warna.PUTIH}📁 {nama_file} ({ukuran:.0f} KB){Warna.RESET}")
                print(f"   💡 Saran: {nama_saran}")
                
                p = input(f"   Tambah? (y/n/skip): ").strip().lower()
                if p == 'y' or p == '':
                    nama_baru = input(f"   Nama: ").strip() or nama_saran
                    tambahkan_suara(fp, nama_baru, konfig)
                elif p == 'skip':
                    print(f"   {Warna.KUNING}⏭️  Skip{Warna.RESET}")
        
        # Menu
        jumlah = len(konfig['suara'])
        print(f"\n{Warna.TEBAL}📋 MENU (Total: {jumlah} suara):{Warna.RESET}")
        print(f"  {Warna.HIJAU}1.{Warna.RESET} 📋 Lihat daftar suara")
        print(f"  {Warna.HIJAU}2.{Warna.RESET} 🎬 Download YouTube → MP3")
        print(f"  {Warna.HIJAU}3.{Warna.RESET} 🗑️  Hapus suara")
        print(f"  {Warna.HIJAU}4.{Warna.RESET} 📁 Buka folder suara")
        print(f"  {Warna.HIJAU}5.{Warna.RESET} 📝 Lihat error log")
        print(f"  {Warna.HIJAU}0.{Warna.RESET} ❌ Kembali")
        
        p = input(f"\n{Warna.TEBAL}Pilih (0-5): {Warna.RESET}").strip()
        
        if p == '1':
            if not konfig['suara']:
                print(f"\n{Warna.KUNING}📭 Kosong{Warna.RESET}")
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
        
        elif p == '2':
            menu_youtube(konfig)
        
        elif p == '3':
            if not konfig['suara']:
                print(f"\n{Warna.KUNING}📭 Kosong{Warna.RESET}")
            else:
                for i, s in enumerate(konfig['suara'], 1):
                    print(f"  {i}. {s['nama']} [{s['kategori']}]")
                try:
                    idx = int(input(f"\n{Warna.TEBAL}Hapus nomor (0=batal): {Warna.RESET}"))
                    if 1 <= idx <= len(konfig['suara']):
                        s = konfig['suara'][idx-1]
                        if input(f"{Warna.MERAH}Hapus '{s['nama']}'? (y/n): {Warna.RESET}").strip().lower() == 'y':
                            fp = os.path.join(FOLDER_SUARA, s['nama_file'])
                            if os.path.exists(fp):
                                os.remove(fp)
                            konfig['suara'].pop(idx-1)
                            simpan_konfigurasi(konfig)
                            print(f"{Warna.HIJAU}✅ Dihapus!{Warna.RESET}")
                except:
                    pass
            input(f"\n{Warna.CYAN}Tekan Enter...{Warna.RESET}")
        
        elif p == '4':
            if os.name == 'nt':
                os.startfile(FOLDER_SUARA)
            time.sleep(0.3)
        
        elif p == '5':
            if os.path.exists(ERROR_LOG):
                print(f"\n{Warna.CYAN}{'='*60}{Warna.RESET}")
                with open(ERROR_LOG, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-25:]:
                        print(line.rstrip())
                print(f"{Warna.CYAN}{'='*60}{Warna.RESET}")
                if input(f"\nHapus log? (y/n): ").strip().lower() == 'y':
                    os.remove(ERROR_LOG)
                    print(f"{Warna.HIJAU}✅ Dihapus{Warna.RESET}")
            else:
                print(f"\n{Warna.HIJAU}✅ Tidak ada error!{Warna.RESET}")
            input(f"\n{Warna.CYAN}Tekan Enter...{Warna.RESET}")
        
        elif p == '0':
            break

if __name__ == "__main__":
    os.makedirs(FOLDER_SUARA, exist_ok=True)
    os.makedirs(FOLDER_SUARA_BARU, exist_ok=True)
    os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
    menu_utama()
