#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║     🎵 BIMOLI SOUNDBOARD MANAGER 🎵        ║
║     Auto-Detect | YouTube Downloader        ║
╚══════════════════════════════════════════════╝
"""

import os
import sys
import json
import shutil
import time
import re
from datetime import datetime
import threading
import subprocess

# Path
SYSTEM_DIR = os.environ.get('BIMOLI_SYSTEM_DIR', '.bimoli_system')
BASE_DIR = os.environ.get('BIMOLI_BASE_DIR', os.path.dirname(os.path.abspath(__file__)))

# Konfigurasi
FOLDER_SUARA = os.path.join(BASE_DIR, "suara")
FOLDER_SUARA_BARU = os.path.join(BASE_DIR, "suara_baru")
FOLDER_DOWNLOAD = os.path.join(BASE_DIR, "downloads")
FILE_KONFIG = os.path.join(BASE_DIR, "config.json")
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
    if os.path.exists(FILE_KONFIG):
        with open(FILE_KONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "suara": [],
        "kategori": ["Bimoli", "Gaming", "Meme", "Efek", "Lainnya"],
        "pengaturan": {"volume": 1.0}
    }

def simpan_konfigurasi(konfig):
    with open(FILE_KONFIG, 'w', encoding='utf-8') as f:
        json.dump(konfig, f, indent=2, ensure_ascii=False)

def tambahkan_suara(filepath, nama, konfig, sumber="local"):
    """Tambah suara ke sistem"""
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
    if os.path.exists(filepath) and (FOLDER_SUARA_BARU in filepath or FOLDER_DOWNLOAD in filepath):
        os.remove(filepath)
    
    print(f"\n{Warna.HIJAU}✅ '{nama}' ditambahkan! [{kategori}]{Warna.RESET}")

def download_youtube_pytube(url, nama=None):
    """Download YouTube dengan pytube"""
    try:
        from pytube import YouTube
        
        print(f"\n{Warna.CYAN}⏳ Download dari YouTube...{Warna.RESET}")
        yt = YouTube(url)
        print(f"Judul: {yt.title}")
        
        audio = yt.streams.filter(only_audio=True).first()
        if not audio:
            print(f"{Warna.MERAH}❌ Tidak ada audio{Warna.RESET}")
            return None
        
        os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
        output = nama if nama else re.sub(r'[<>:"/\\|?*]', '', yt.title)[:50]
        
        downloaded = audio.download(output_path=FOLDER_DOWNLOAD, filename=output + ".mp4")
        mp3_path = downloaded.replace('.mp4', '.mp3')
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        os.rename(downloaded, mp3_path)
        
        print(f"{Warna.HIJAU}✅ Download selesai!{Warna.RESET}")
        return mp3_path
    except Exception as e:
        print(f"{Warna.MERAH}❌ Error: {e}{Warna.RESET}")
        return None

def menu_youtube(konfig):
    """Menu download YouTube"""
    print(f"\n{Warna.CYAN}🎬 YOUTUBE DOWNLOADER{Warna.RESET}")
    
    # Cek pytube
    try:
        import pytube
    except:
        print(f"{Warna.KUNING}Install pytube dulu: pip install pytube{Warna.RESET}")
        return
    
    url = input(f"\n{Warna.PUTIH}URL YouTube: {Warna.RESET}").strip()
    if not url:
        return
    
    nama = input(f"{Warna.PUTIH}Nama (opsional): {Warna.RESET}").strip()
    
    file_path = download_youtube_pytube(url, nama if nama else None)
    if file_path:
        nama_file = os.path.basename(file_path)
        nama_saran = os.path.splitext(nama_file)[0].replace('_', ' ').title()
        
        print(f"\n{Warna.KUNING}Nama: {nama_saran}{Warna.RESET}")
        ganti = input("Ganti nama? (y/n): ").strip().lower()
        if ganti == 'y':
            nama_saran = input("Nama baru: ").strip() or nama_saran
        
        tambahkan_suara(file_path, nama_saran, konfig, "youtube")

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
            print(f"\n{Warna.KUNING}📁 {len(file_baru)} file baru terdeteksi!{Warna.RESET}")
            for fp in file_baru:
                nama = os.path.splitext(os.path.basename(fp))[0].replace('_', ' ').title()
                print(f"\n{Warna.PUTIH}File: {os.path.basename(fp)}{Warna.RESET}")
                print(f"Saran nama: {nama}")
                
                pilihan = input("Tambah? (y/n/skip): ").strip().lower()
                if pilihan == 'y' or pilihan == '':
                    nama_baru = input("Nama (Enter=saran): ").strip() or nama
                    tambahkan_suara(fp, nama_baru, konfig)
                elif pilihan == 'skip':
                    print(f"{Warna.KUNING}⏭️ Skip{Warna.RESET}")
        
        print(f"\n{Warna.TEBAL}MENU:{Warna.RESET}")
        print(f"  1. 📋 Lihat suara ({len(konfig['suara'])})")
        print(f"  2. 🎬 Download YouTube")
        print(f"  3. 🗑️  Hapus suara")
        print(f"  4. 📁 Buka folder suara")
        print(f"  0. Kembali")
        
        p = input(f"\n{Warna.TEBAL}Pilih: {Warna.RESET}").strip()
        
        if p == '1':
            if not konfig['suara']:
                print(f"\n{Warna.KUNING}📭 Kosong{Warna.RESET}")
            else:
                for i, s in enumerate(konfig['suara'], 1):
                    print(f"  {i}. {s['nama']} [{s['kategori']}] - {s['jumlah_main']}x")
            input(f"\n{Warna.CYAN}Enter...{Warna.RESET}")
        
        elif p == '2':
            menu_youtube(konfig)
        
        elif p == '3':
            if konfig['suara']:
                for i, s in enumerate(konfig['suara'], 1):
                    print(f"  {i}. {s['nama']}")
                try:
                    idx = int(input("Hapus nomor (0=batal): "))
                    if 1 <= idx <= len(konfig['suara']):
                        s = konfig['suara'][idx-1]
                        fp = os.path.join(FOLDER_SUARA, s['nama_file'])
                        if os.path.exists(fp):
                            os.remove(fp)
                        konfig['suara'].pop(idx-1)
                        simpan_konfigurasi(konfig)
                        print(f"{Warna.HIJAU}✅ Dihapus{Warna.RESET}")
                except:
                    pass
        
        elif p == '4':
            if os.name == 'nt':
                os.startfile(FOLDER_SUARA)
        
        elif p == '0':
            break

if __name__ == "__main__":
    os.makedirs(FOLDER_SUARA, exist_ok=True)
    os.makedirs(FOLDER_SUARA_BARU, exist_ok=True)
    os.makedirs(FOLDER_DOWNLOAD, exist_ok=True)
    menu_utama()