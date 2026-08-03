#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║     🎵 BIMOLI SOUNDBOARD MANAGER 🎵        ║
║     YouTube Downloader + Error Logging      ║
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
    """Tulis log ke file error.log"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{tipe}] {pesan}\n")
    except:
        pass

def tulis_error(error, lokasi=""):
    """Tulis error lengkap dengan traceback"""
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

def log_download_yt(url, status, detail=""):
    """Log khusus download YouTube"""
    tulis_log(f"YT Download | URL: {url} | Status: {status} | {detail}", "DOWNLOAD")

# ============================================================
# FUNGSI UTILITY
# ============================================================

def bersihkan_layar():
    os.system('cls' if os.name == 'nt' else 'clear')

def tampilkan_banner():
    bersihkan_layar()
    print(f"""
{Warna.CYAN}{Warna.TEBAL}
╔══════════════════════════════════════════════════╗
║        🎵 BIMOLI SOUNDBOARD MANAGER 🎵         ║
║         YouTube Downloader + Manager            ║
╚══════════════════════════════════════════════════╝
{Warna.RESET}
    """)

def muat_konfigurasi():
    try:
        if os.path.exists(FILE_KONFIG):
            with open(FILE_KONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        tulis_error(e, "muat_konfigurasi")
    
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
    except Exception as e:
        tulis_error(e, "simpan_konfigurasi")
        print(f"{Warna.MERAH}❌ Gagal simpan config! Cek error.log{Warna.RESET}")
        return False

# ============================================================
# DOWNLOAD YOUTUBE
# ============================================================

def cek_pytube():
    """Cek apakah pytube terinstall"""
    try:
        import pytube
        return True
    except:
        return False

def cek_ytdlp():
    """Cek apakah yt-dlp terinstall"""
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def install_package(nama_package):
    """Install Python package"""
    print(f"{Warna.CYAN}⏳ Install {nama_package}...{Warna.RESET}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", nama_package, "--quiet"],
                      shell=True, check=True)
        print(f"{Warna.HIJAU}✅ {nama_package} terinstall!{Warna.RESET}")
        return True
    except Exception as e:
        tulis_error(e, f"install_package({nama_package})")
        print(f"{Warna.MERAH}❌ Gagal install {nama_package}{Warna.RESET}")
        print(f"{Warna.KUNING}💡 Coba manual: pip install {nama_package}{Warna.RESET}")
        return False

def download_youtube_pytube(url, nama_kustom=None):
    """
    Download YouTube pakai pytube (TANPA ffmpeg)
    """
    lokasi = "download_youtube_pytube"
    
    try:
        print(f"\n{Warna.CYAN}⏳ Download pakai pytube...{Warna.RESET}")
        tulis_log(f"Mulai download: {url}", "DOWNLOAD")
        
        # Import pytube
        try:
            from pytube import YouTube
            from pytube.exceptions import PytubeError, VideoUnavailable
        except ImportError:
            print(f"{Warna.MERAH}❌ pytube belum terinstall!{Warna.RESET}")
            tulis_log("pytube tidak terinstall", "ERROR")
            return None
        
        # Bikin object YouTube
        try:
            print(f"{Warna.PUTIH}📡 Menghubungi YouTube...{Warna.RESET}")
            yt = YouTube(url)
        except VideoUnavailable:
            print(f"{Warna.MERAH}❌ Video tidak tersedia!{Warna.RESET}")
            log_download_yt(url, "GAGAL", "Video tidak tersedia")
            return None
        except PytubeError as e:
            print(f"{Warna.MERAH}❌ Error YouTube: {e}{Warna.RESET}")
            tulis_error(e, f"{lokasi} - YouTube Error")
            log_download_yt(url, "GAGAL", str(e))
            return None
        except Exception as e:
            print(f"{Warna.MERAH}❌ Gagal akses video: {e}{Warna.RESET}")
            tulis_error(e, f"{lokasi} - Akses video")
            log_download_yt(url, "GAGAL", f"Akses: {e}")
            return None
        
        # Info video
        try:
            judul = yt.title
            durasi = yt.length
            print(f"{Warna.PUTIH}📹 Judul : {judul}{Warna.RESET}")
            print(f"{Warna.PUTIH}⏱️  Durasi: {durasi} detik{Warna.RESET}")
            tulis_log(f"Info video: {judul} ({durasi}s)", "INFO")
        except Exception as e:
            tulis_error(e, f"{lokasi} - Info video")
        
        # Cari audio stream
        print(f"{Warna.CYAN}🔍 Mencari audio stream...{Warna.RESET}")
        
        try:
            audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
            
            if not audio_streams or len(audio_streams) == 0:
                print(f"{Warna.MERAH}❌ Tidak ada audio stream!{Warna.RESET}")
                tulis_log("Tidak ada audio stream tersedia", "ERROR")
                return None
            
            # Pilih kualitas terbaik
            audio = audio_streams.first()
            print(f"{Warna.PUTIH}🎵 Kualitas: {audio.abr}{Warna.RESET}")
            tulis_log(f"Audio stream: {audio.abr}", "INFO")
            
        except Exception as e:
            print(f"{Warna.MERAH}❌ Gagal dapat stream: {e}{Warna.RESET}")
            tulis_error(e, f"{lokasi} - Stream")
            return None
        
        # Download
        print(f"{Warna.CYAN}📥 Downloading...{Warna.RESET}")
        
        try:
            os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
            
            # Nama file
            if nama_kustom:
                nama_file = re.sub(r'[<>:"/\\|?*]', '', nama_kustom)[:50]
            else:
                nama_file = re.sub(r'[<>:"/\\|?*]', '', yt.title)[:50]
            
            # Download
            downloaded = audio.download(
                output_path=FOLDER_DOWNLOAD,
                filename=nama_file + ".mp4"
            )
            
            print(f"{Warna.HIJAU}✅ Downloaded: {os.path.basename(downloaded)}{Warna.RESET}")
            tulis_log(f"Download selesai: {downloaded}", "SUKSES")
            
        except Exception as e:
            print(f"{Warna.MERAH}❌ Gagal download: {e}{Warna.RESET}")
            tulis_error(e, f"{lokasi} - Download")
            log_download_yt(url, "GAGAL", f"Download error: {e}")
            return None
        
        # Convert ke MP3 (rename aja)
        try:
            mp3_path = downloaded.replace('.mp4', '.mp3').replace('.webm', '.mp3')
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
            os.rename(downloaded, mp3_path)
            
            ukuran = os.path.getsize(mp3_path) / 1024
            print(f"{Warna.HIJAU}✅ MP3: {os.path.basename(mp3_path)} ({ukuran:.0f} KB){Warna.RESET}")
            tulis_log(f"Convert ke MP3: {mp3_path} ({ukuran:.0f} KB)", "SUKSES")
            log_download_yt(url, "SUKSES", f"{os.path.basename(mp3_path)} ({ukuran:.0f} KB)")
            
            return mp3_path
            
        except Exception as e:
            print(f"{Warna.MERAH}❌ Gagal convert: {e}{Warna.RESET}")
            tulis_error(e, f"{lokasi} - Convert")
            # Tetap return file asli
            log_download_yt(url, "SUKSES (TANPA CONVERT)", os.path.basename(downloaded))
            return downloaded
        
    except Exception as e:
        print(f"{Warna.MERAH}❌ Error tidak dikenal: {e}{Warna.RESET}")
        tulis_error(e, f"{lokasi} - Unknown")
        log_download_yt(url, "GAGAL", f"Unknown: {e}")
        print(f"{Warna.KUNING}💡 Cek error.log untuk detail lengkap{Warna.RESET}")
        return None

def download_youtube_ytdlp(url, nama_kustom=None):
    """
    Download YouTube pakai yt-dlp (butuh ffmpeg, kualitas lebih baik)
    """
    lokasi = "download_youtube_ytdlp"
    
    try:
        print(f"\n{Warna.CYAN}⏳ Download pakai yt-dlp...{Warna.RESET}")
        tulis_log(f"Mulai download (yt-dlp): {url}", "DOWNLOAD")
        
        os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
        
        # Template output
        if nama_kustom:
            output = os.path.join(FOLDER_DOWNLOAD, f"{nama_kustom}.%(ext)s")
        else:
            output = os.path.join(FOLDER_DOWNLOAD, "%(title)s.%(ext)s")
        
        # Command yt-dlp
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "192K",
            "-o", output,
            "--no-playlist",
            "--no-warnings",
            url
        ]
        
        print(f"{Warna.PUTIH}📥 Downloading...{Warna.RESET}")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        
        # Cari file yang didownload
        downloaded = []
        for f in os.listdir(FOLDER_DOWNLOAD):
            if f.endswith('.mp3'):
                fp = os.path.join(FOLDER_DOWNLOAD, f)
                downloaded.append((fp, os.path.getmtime(fp)))
        
        if downloaded:
            downloaded.sort(key=lambda x: x[1], reverse=True)
            file_path = downloaded[0][0]
            ukuran = os.path.getsize(file_path) / 1024
            
            print(f"{Warna.HIJAU}✅ Downloaded: {os.path.basename(file_path)} ({ukuran:.0f} KB){Warna.RESET}")
            tulis_log(f"Download selesai: {file_path} ({ukuran:.0f} KB)", "SUKSES")
            log_download_yt(url, "SUKSES", f"{os.path.basename(file_path)} ({ukuran:.0f} KB)")
            
            return file_path
        
        print(f"{Warna.MERAH}❌ File tidak ditemukan setelah download{Warna.RESET}")
        tulis_log("File MP3 tidak ditemukan setelah download", "ERROR")
        return None
        
    except subprocess.TimeoutExpired:
        print(f"{Warna.MERAH}❌ Download timeout (terlalu lama){Warna.RESET}")
        tulis_error("Timeout", lokasi)
        log_download_yt(url, "GAGAL", "Timeout")
        return None
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        print(f"{Warna.MERAH}❌ yt-dlp error!{Warna.RESET}")
        
        # Cek apakah karena ffmpeg
        if "ffmpeg" in error_msg.lower() or "ffprobe" in error_msg.lower():
            print(f"{Warna.KUNING}💡 ffmpeg tidak terinstall!{Warna.RESET}")
            print(f"{Warna.PUTIH}   Download ffmpeg: https://www.gyan.dev/ffmpeg/builds/{Warna.RESET}")
            print(f"{Warna.PUTIH}   Atau pakai pytube (tanpa ffmpeg){Warna.RESET}")
            tulis_log("ffmpeg tidak ditemukan", "ERROR")
        
        tulis_error(error_msg, f"{lokasi} - yt-dlp error")
        log_download_yt(url, "GAGAL", f"yt-dlp: {error_msg[:100]}")
        
        print(f"{Warna.KUNING}💡 Cek error.log untuk detail{Warna.RESET}")
        return None
    except Exception as e:
        print(f"{Warna.MERAH}❌ Error: {e}{Warna.RESET}")
        tulis_error(e, lokasi)
        log_download_yt(url, "GAGAL", str(e))
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
        
        # Copy file
        shutil.copy2(filepath, tujuan)
        tulis_log(f"File dicopy: {filepath} -> {tujuan}", "INFO")
        
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
        
        # Simpan info
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
        
        # Hapus file asli kalo dari folder download/suara_baru
        if os.path.exists(filepath) and (FOLDER_DOWNLOAD in filepath or FOLDER_SUARA_BARU in filepath):
            os.remove(filepath)
            tulis_log(f"File asli dihapus: {filepath}", "INFO")
        
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
        print(f"{Warna.MERAH}❌ Gagal tambah suara: {e}{Warna.RESET}")
        print(f"{Warna.KUNING}💡 Cek error.log{Warna.RESET}")
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
    
    # Cek tools yang tersedia
    pytube_ada = cek_pytube()
    ytdlp_ada = cek_ytdlp()
    
    print(f"\n{Warna.CYAN}🔍 Tools tersedia:{Warna.RESET}")
    print(f"  pytube : {'✅' if pytube_ada else '❌'} (tanpa ffmpeg)")
    print(f"  yt-dlp : {'✅' if ytdlp_ada else '❌'} (butuh ffmpeg)")
    
    if not pytube_ada and not ytdlp_ada:
        print(f"\n{Warna.KUNING}📦 Tidak ada downloader!{Warna.RESET}")
        print(f"Install salah satu:")
        print(f"  1. pip install pytube (paling gampang)")
        print(f"  2. pip install yt-dlp (butuh ffmpeg)")
        
        pilihan = input(f"\n{Warna.TEBAL}Pilih (1-2): {Warna.RESET}").strip()
        
        if pilihan == '1':
            install_package("pytube")
        elif pilihan == '2':
            install_package("yt-dlp")
        else:
            return
    
    while True:
        print(f"\n{Warna.TEBAL}Masukkan URL YouTube:{Warna.RESET}")
        print(f"{Warna.KUNING}(atau ketik 'batal' untuk kembali){Warna.RESET}")
        url = input(f"{Warna.PUTIH}▶️  URL: {Warna.RESET}").strip()
        
        if url.lower() == 'batal':
            return
        
        if not url:
            print(f"{Warna.MERAH}❌ URL kosong!{Warna.RESET}")
            continue
        
        if not ('youtube.com' in url or 'youtu.be' in url):
            print(f"{Warna.KUNING}⚠️  Bukan URL YouTube?{Warna.RESET}")
            lanjut = input("Tetap download? (y/n): ").strip().lower()
            if lanjut != 'y':
                continue
        
        # Nama kustom
        print(f"\n{Warna.CYAN}Nama untuk sound ini (opsional):{Warna.RESET}")
        nama_kustom = input(f"{Warna.PUTIH}Nama: {Warna.RESET}").strip()
        
        # Pilih metode download
        if pytube_ada:
            print(f"\n{Warna.CYAN}Pakai pytube (rekomendasi)...{Warna.RESET}")
            file_path = download_youtube_pytube(url, nama_kustom if nama_kustom else None)
        elif ytdlp_ada:
            print(f"\n{Warna.CYAN}Pakai yt-dlp...{Warna.RESET}")
            file_path = download_youtube_ytdlp(url, nama_kustom if nama_kustom else None)
        else:
            print(f"{Warna.MERAH}❌ Tidak ada downloader!{Warna.RESET}")
            return
        
        if not file_path:
            print(f"\n{Warna.MERAH}❌ Download gagal!{Warna.RESET}")
            print(f"{Warna.KUNING}💡 Cek error.log untuk detail error{Warna.RESET}")
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
        
        # Cek suara baru
        file_baru = []
        if os.path.exists(FOLDER_SUARA_BARU):
            for f in os.listdir(FOLDER_SUARA_BARU):
                fp = os.path.join(FOLDER_SUARA_BARU, f)
                if os.path.isfile(fp) and any(f.lower().endswith(ext) for ext in FORMAT_DIDUKUNG):
                    file_baru.append(fp)
        
        if file_baru:
            print(f"\n{Warna.KUNING}{Warna.TEBAL}📁 {len(file_baru)} FILE BARU TERDETEKSI!{Warna.RESET}")
            print(f"{Warna.CYAN}📍 Folder: suara_baru{Warna.RESET}\n")
            
            for fp in file_baru:
                nama_file = os.path.basename(fp)
                ukuran = os.path.getsize(fp) / 1024
                nama_saran = os.path.splitext(nama_file)[0].replace('_', ' ').title()
                
                print(f"{Warna.PUTIH}📁 {nama_file} ({ukuran:.0f} KB){Warna.RESET}")
                print(f"   💡 Saran nama: {nama_saran}")
                
                pilihan = input(f"   Tambah? (y/n/skip): ").strip().lower()
                
                if pilihan == 'y' or pilihan == '':
                    nama_baru = input(f"   Nama (Enter=saran): ").strip()
                    if not nama_baru:
                        nama_baru = nama_saran
                    tambahkan_suara(fp, nama_baru, konfig)
                elif pilihan == 'skip':
                    print(f"   {Warna.KUNING}⏭️  Skip{Warna.RESET}")
                print()
        
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
                print(f"\n{Warna.KUNING}📭 Belum ada suara!{Warna.RESET}")
            else:
                print(f"\n{Warna.CYAN}{Warna.TEBAL}📋 DAFTAR SUARA:{Warna.RESET}")
                for kat in konfig['kategori']:
                    suara_kat = [s for s in konfig['suara'] if s['kategori'] == kat]
                    if suara_kat:
                        print(f"\n{Warna.KUNING}📂 {kat}:{Warna.RESET}")
                        for i, s in enumerate(suara_kat, 1):
                            icon = "🎬" if s.get('sumber') == 'youtube' else "💾"
                            print(f"  {icon} {s['nama']} - {s['jumlah_main']}x")
            input(f"\n{Warna.CYAN}Tekan Enter...{Warna.RESET}")
        
        elif p == '2':
            menu_youtube(konfig)
        
        elif p == '3':
            if not konfig['suara']:
                print(f"\n{Warna.KUNING}📭 Tidak ada suara!{Warna.RESET}")
            else:
                print(f"\n{Warna.CYAN}Pilih suara yang dihapus:{Warna.RESET}")
                for i, s in enumerate(konfig['suara'], 1):
                    print(f"  {i}. {s['nama']} [{s['kategori']}]")
                print(f"  0. Batal")
                
                try:
                    idx = int(input(f"\n{Warna.TEBAL}Pilih: {Warna.RESET}"))
                    if 1 <= idx <= len(konfig['suara']):
                        s = konfig['suara'][idx-1]
                        konfirm = input(f"{Warna.MERAH}Hapus '{s['nama']}'? (y/n): {Warna.RESET}").strip().lower()
                        if konfirm == 'y':
                            fp = os.path.join(FOLDER_SUARA, s['nama_file'])
                            if os.path.exists(fp):
                                os.remove(fp)
                            konfig['suara'].pop(idx-1)
                            simpan_konfigurasi(konfig)
                            print(f"{Warna.HIJAU}✅ Dihapus!{Warna.RESET}")
                except:
                    print(f"{Warna.MERAH}❌ Input error{Warna.RESET}")
            input(f"\n{Warna.CYAN}Tekan Enter...{Warna.RESET}")
        
        elif p == '4':
            if os.name == 'nt' and os.path.exists(FOLDER_SUARA):
                os.startfile(FOLDER_SUARA)
            time.sleep(0.3)
        
        elif p == '5':
            # Lihat error log
            if os.path.exists(ERROR_LOG):
                print(f"\n{Warna.CYAN}{'='*60}{Warna.RESET}")
                print(f"{Warna.PUTIH}📝 ERROR LOG:{Warna.RESET}")
                print(f"{Warna.CYAN}{'='*60}{Warna.RESET}")
                
                with open(ERROR_LOG, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Tampilkan 30 baris terakhir
                    for line in lines[-30:]:
                        print(line.rstrip())
                
                print(f"\n{Warna.CYAN}{'='*60}{Warna.RESET}")
                
                hapus = input(f"\n{Warna.KUNING}Hapus error log? (y/n): {Warna.RESET}").strip().lower()
                if hapus == 'y':
                    os.remove(ERROR_LOG)
                    print(f"{Warna.HIJAU}✅ Error log dihapus{Warna.RESET}")
            else:
                print(f"\n{Warna.HIJAU}✅ Tidak ada error log. Semua berjalan normal!{Warna.RESET}")
            input(f"\n{Warna.CYAN}Tekan Enter...{Warna.RESET}")
        
        elif p == '0':
            break

# ============================================================

if __name__ == "__main__":
    # Pastikan folder ada
    os.makedirs(FOLDER_SUARA, exist_ok=True)
    os.makedirs(FOLDER_SUARA_BARU, exist_ok=True)
    os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
    
    # Mulai menu
    menu_utama()
