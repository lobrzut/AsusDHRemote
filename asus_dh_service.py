import hid
import time
import sys
import os
import json
import subprocess
import ctypes
from ctypes import wintypes
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser
import urllib.request
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# Windows Virtual Key Codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_STOP = 0xB2

# Constants for SendInput API
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
INPUT_KEYBOARD = 1

# Ctypes structures for SendInput
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION)
    ]

def send_key(vk_code):
    """Sends a single key press and release event with mapped scan code using keybd_event."""
    scan_code = ctypes.windll.user32.MapVirtualKeyW(vk_code, 0)
    # Media and volume keys are extended keys, requiring KEYEVENTF_EXTENDEDKEY (0x0001)
    flags_down = KEYEVENTF_EXTENDEDKEY
    flags_up = KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP
    
    ctypes.windll.user32.keybd_event(vk_code, scan_code, flags_down, 0)
    time.sleep(0.01)
    ctypes.windll.user32.keybd_event(vk_code, scan_code, flags_up, 0)

def show_desktop():
    """Simulates Win+D key combination to show/hide the desktop."""
    extra = ctypes.c_ulong(0)
    VK_LWIN = 0x5B
    KEY_D = 0x44
    
    # Win down
    ii1 = INPUT_UNION()
    ii1.ki = KEYBDINPUT(VK_LWIN, 0, KEYEVENTF_EXTENDEDKEY, 0, ctypes.pointer(extra))
    # D down
    ii2 = INPUT_UNION()
    ii2.ki = KEYBDINPUT(KEY_D, 0, 0, 0, ctypes.pointer(extra))
    # D up
    ii3 = INPUT_UNION()
    ii3.ki = KEYBDINPUT(KEY_D, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    # Win up
    ii4 = INPUT_UNION()
    ii4.ki = KEYBDINPUT(VK_LWIN, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    
    inputs = (INPUT * 4)(
        INPUT(INPUT_KEYBOARD, ii1),
        INPUT(INPUT_KEYBOARD, ii2),
        INPUT(INPUT_KEYBOARD, ii3),
        INPUT(INPUT_KEYBOARD, ii4)
    )
    ctypes.windll.user32.SendInput(4, ctypes.pointer(inputs), ctypes.sizeof(INPUT))

def lock_pc():
    """Locks the Windows workstation immediately."""
    try:
        ctypes.windll.user32.LockWorkStation()
    except Exception as e:
        print(f"Error locking PC: {e}", flush=True)

def toggle_maximize():
    """Toggles maximizing the active (foreground) window."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            # Check if active window is maximized
            is_max = ctypes.windll.user32.IsZoomed(hwnd)
            # SW_RESTORE = 9, SW_MAXIMIZE = 3
            n_cmd_show = 9 if is_max else 3
            ctypes.windll.user32.ShowWindow(hwnd, n_cmd_show)
    except Exception as e:
        print(f"Error toggling maximize: {e}", flush=True)

def execute_action(action_name, action_data):
    """Executes the mapped action for a button press."""
    action = action_data.get("action")
    print(f"Executing: {action_name} -> Action: {action}", flush=True)
    
    if action == "volume_up":
        send_key(VK_VOLUME_UP)
    elif action == "volume_down":
        send_key(VK_VOLUME_DOWN)
    elif action == "mute":
        send_key(VK_VOLUME_MUTE)
    elif action == "play_pause":
        send_key(VK_MEDIA_PLAY_PAUSE)
    elif action == "next_track":
        send_key(VK_MEDIA_NEXT_TRACK)
    elif action == "prev_track":
        send_key(VK_MEDIA_PREV_TRACK)
    elif action == "show_desktop":
        show_desktop()
    elif action == "lock_pc":
        lock_pc()
    elif action == "toggle_maximize":
        toggle_maximize()
    elif action == "run_command":
        cmd = action_data.get("command")
        if cmd:
            try:
                # Launch asynchronously so we don't freeze the main loop
                subprocess.Popen(cmd, shell=True)
            except Exception as e:
                print(f"Error running command '{cmd}': {e}", flush=True)
    else:
        print(f"Unknown action configured: {action}", flush=True)

# Thread control and service state globals
running = True
httpd_server = None

class ServiceState:
    def __init__(self):
        self.last_pressed_key = None
        self.last_pressed_time = 0
        self.config = {}
        self.config_lock = threading.Lock()
        self.receiver_connected = False

state = ServiceState()

DEFAULT_CONFIG = {
    "0x01": {"action": "show_desktop"},
    "0x02": {"action": "lock_pc"},
    "0x03": {"action": "mute"},
    "0x04": {"action": "run_command", "command": "cmd.exe /c start https://www.google.com"},
    "0x05": {"action": "run_command", "command": "calc.exe"},
    "0x06": {"action": "toggle_maximize"},
    "0x07": {"action": "volume_up"},
    "0x08": {"action": "prev_track"},
    "0x09": {"action": "play_pause"},
    "0x0A": {"action": "next_track"},
    "0x0B": {"action": "volume_down"}
}

def _base_dir():
    return os.path.dirname(os.path.abspath(__file__))

def _load_default_config():
    """Prefer config.example.json when present; otherwise built-in defaults."""
    example_path = os.path.join(_base_dir(), "config.example.json")
    if os.path.exists(example_path):
        try:
            with open(example_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading config.example.json: {e}", flush=True)
    return dict(DEFAULT_CONFIG)

def load_config():
    """Loads button mapping configuration from config.json into the shared state."""
    config_path = os.path.join(_base_dir(), "config.json")
    default_config = _load_default_config()

    if not os.path.exists(config_path):
        print("config.json not found. Seeding from defaults.", flush=True)
        with state.config_lock:
            state.config = default_config
        # Persist a local copy so the GUI and user edits have a starting point
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Could not create config.json: {e}", flush=True)
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            with state.config_lock:
                state.config = data
    except Exception as e:
        print(f"Error loading config.json: {e}. Using built-in defaults.", flush=True)
        with state.config_lock:
            state.config = default_config

def save_config(new_config):
    """Saves mapping configuration to config.json and reloads it in the shared state."""
    config_path = os.path.join(_base_dir(), "config.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
        with state.config_lock:
            state.config = new_config
        print("Configuration saved and hot-reloaded successfully.", flush=True)
        return True
    except Exception as e:
        print(f"Error saving config.json: {e}", flush=True)
        return False

# Tray Icon Helper functions
def create_tray_icon(width, height):
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    # Draw a glowing purple circle
    dc.ellipse((2, 2, width-3, height-3), fill=(146, 84, 222, 255), outline=(19, 194, 194, 255), width=2)
    # Draw a mini wireless wave indicator in center
    center_x = width // 2
    center_y = height // 2
    dc.ellipse((center_x-2, center_y-2, center_x+2, center_y+2), fill=(255, 255, 255, 255))
    dc.arc((center_x-6, center_y-6, center_x+6, center_y+6), start=210, end=330, fill=(255, 255, 255, 255), width=2)
    dc.arc((center_x-11, center_y-11, center_x+11, center_y+11), start=210, end=330, fill=(255, 255, 255, 255), width=2)
    return image

def on_open_settings(icon, item):
    webbrowser.open("http://127.0.0.1:5555")

def on_view_log(icon, item):
    log_path = os.path.join(_base_dir(), "asus_dh_remote.log")
    if os.path.exists(log_path):
        os.startfile(log_path)

def on_reload_config(icon, item):
    load_config()
    print("Configuration reloaded via tray menu.", flush=True)

def on_exit(icon, item):
    global running
    print("Shutting down ASUS DH Remote service...", flush=True)
    running = False
    icon.stop()
    if httpd_server:
        try:
            httpd_server.shutdown()
        except Exception:
            pass

class RemoteHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence standard HTTP logs to prevent bloating asus_dh_remote.log
        pass

    def do_GET(self):
        if self.path == '/':
            index_path = os.path.join(_base_dir(), "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(index_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"index.html not found.")

        elif self.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            with state.config_lock:
                config_copy = dict(state.config)
            self.wfile.write(json.dumps(config_copy).encode('utf-8'))

        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "running",
                "receiver_connected": state.receiver_connected
            }).encode('utf-8'))

        elif self.path == '/api/last_press':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            # If the last press is older than 2 seconds, clear the highlight in UI
            if time.time() - state.last_pressed_time < 2.0:
                resp = {"key": state.last_pressed_key, "timestamp": state.last_pressed_time}
            else:
                resp = {"key": None, "timestamp": 0}
            self.wfile.write(json.dumps(resp).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                new_config = json.loads(post_data.decode('utf-8'))
                if save_config(new_config):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.end_headers()
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server():
    global httpd_server
    server_address = ('127.0.0.1', 5555)
    try:
        httpd_server = HTTPServer(server_address, RemoteHTTPHandler)
        print("Debug: HTTP server running on http://127.0.0.1:5555", flush=True)
        httpd_server.serve_forever()
    except Exception as e:
        print(f"Error starting HTTP server: {e}", flush=True)

def run_hid_listener():
    global running
    last_trigger_times = {}  # button_code -> timestamp
    VID = 0x1130
    PID = 0xCC00

    print("Debug: Entering HID listener loop...", flush=True)
    while running:
        h = None
        reconnect_delay = 0
        try:
            enumerated = hid.enumerate(VID, PID)
            if not enumerated:
                state.receiver_connected = False
                reconnect_delay = 3
            else:
                path = enumerated[0]["path"]
                h = hid.device()
                h.open_path(path)
                state.receiver_connected = True
                print(f"Connected to ASUS DH IR Receiver at {path.decode('ascii', 'ignore')}", flush=True)

                while running:
                    data = h.read(64, timeout_ms=100)
                    if data:
                        if len(data) >= 2 and data[0] == 0x02:
                            button_code = data[1]
                            current_time = time.time()

                            if button_code != 0:
                                button_hex = f"0x{button_code:02X}"

                                state.last_pressed_key = button_hex
                                state.last_pressed_time = current_time

                                with state.config_lock:
                                    action_data = state.config.get(button_hex)

                                if action_data:
                                    is_volume_key = button_code in (0x07, 0x0B)
                                    time_since_last_trigger = current_time - last_trigger_times.get(button_code, 0)
                                    cooldown = 0.15 if is_volume_key else 0.25

                                    if time_since_last_trigger > cooldown:
                                        execute_action(button_hex, action_data)
                                        last_trigger_times[button_code] = current_time
                    time.sleep(0.01)

        except Exception as e:
            state.receiver_connected = False
            reconnect_delay = 2
            if running:
                print(f"Connection lost or error occurred: {e}", flush=True)
                print("Attempting to reconnect in 2 seconds...", flush=True)
        finally:
            state.receiver_connected = False
            if h is not None:
                try:
                    h.close()
                except Exception:
                    pass

        if reconnect_delay and running:
            time.sleep(reconnect_delay)

class UnbufferedWriter:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

def main():
    # 1. Singleton Check: If service is already running, open GUI (if requested) and exit
    service_already_running = False
    try:
        with urllib.request.urlopen("http://127.0.0.1:5555/api/status", timeout=0.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if data.get("status") == "running":
                    service_already_running = True
    except Exception:
        pass

    if service_already_running:
        print("ASUS DH Remote service is already running.", flush=True)
        if "--gui" in sys.argv:
            print("Opening Web GUI settings...", flush=True)
            webbrowser.open("http://127.0.0.1:5555")
        sys.exit(0)

    # 2. Allocate and immediately hide console if running in background
    if "--console" not in sys.argv:
        try:
            ctypes.windll.kernel32.AllocConsole()
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                # SW_HIDE = 0
                ctypes.windll.user32.ShowWindow(hwnd, 0)
            
            conout = open("CONOUT$", "w")
            os.dup2(conout.fileno(), 1)
            os.dup2(conout.fileno(), 2)
        except Exception:
            pass

    # 3. Redirect standard outputs to log file if background
    if "--console" not in sys.argv:
        log_path = os.path.join(_base_dir(), "asus_dh_remote.log")
        try:
            f = open(log_path, "a", encoding="utf-8")
            sys.stdout = UnbufferedWriter(f)
            sys.stderr = sys.stdout
        except Exception as e:
            pass

    print(f"\n--- Service started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---", flush=True)
    print("ASUS DH Remote background service started.", flush=True)
    
    # 4. Load configuration into state
    print("Debug: Loading config...", flush=True)
    load_config()
    print("Debug: Config loaded successfully.", flush=True)
    
    # 5. Start background HTTP server thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # 6. Start background HID listener thread
    hid_thread = threading.Thread(target=run_hid_listener, daemon=True)
    hid_thread.start()
    
    # 7. Auto-open Web GUI in browser if --gui argument is present
    if "--gui" in sys.argv:
        try:
            webbrowser.open("http://127.0.0.1:5555")
        except Exception as e:
            print(f"Error opening browser: {e}", flush=True)

    # 8. Start system tray icon loop on the main thread (blocking)
    try:
        icon_image = create_tray_icon(64, 64)
        tray_menu = pystray.Menu(
            item('Open Settings', on_open_settings, default=True),
            item('View Log', on_view_log),
            item('Reload Config', on_reload_config),
            item('Exit', on_exit)
        )
        icon = pystray.Icon("AsusDHRemote", icon_image, "ASUS DH Remote Manager", menu=tray_menu)
        icon.run()
    except Exception as e:
        print(f"Error running tray icon: {e}", flush=True)
        # Fallback: if tray icon fails to initialize, just sleep to keep threads running
        global running
        while running:
            time.sleep(1)

if __name__ == "__main__":
    main()
