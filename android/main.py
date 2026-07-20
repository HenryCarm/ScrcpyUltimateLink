import os, sys, time, socket, threading, json, subprocess, traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

# 1. Request Scoped Storage & Network Permissions to prevent 7-second Security Crash
try:
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.INTERNET, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
except Exception:
    pass

# 2. Dynamic Config & Logging Paths
CONFIG_FILE = "/sdcard/scrcpy_heartbeat_config.json"
LOG_DIR = "/sdcard/Logs"
LOG_FILE = os.path.join(LOG_DIR, "ScrcpyLink.log")

def load_config():
    defaults = {"heartbeat_port": 5556, "discovery_port": 5557, "adb_port": 5555, "logging_enabled": True}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            for k, v in defaults.items():
                if k not in config: config[k] = v
            return config
    except:
        pass
    return defaults

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except:
        pass

config = load_config()

# 3. Enterprise File Logger
def app_log(msg):
    if not config.get("logging_enabled", True):
        return
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_str = f"[{timestamp}] {msg}\n"
        with open(LOG_FILE, "a") as f:
            f.write(log_str)
        print(log_str.strip())
    except Exception as e:
        print(f"Logging failed: {e}")

# 4. Safe Threaded Shizuku Execution (Prevents ANR block)
def enable_shizuku_wireless_adb():
    app_log("Starting Shizuku/Root ADB background sequence...")
    adb_cmd = "setprop service.adb.tcp.port 5555; setprop persist.adb.tcp.port 5555; setprop service.adb.tcp.bind 0.0.0.0; stop adbd && start adbd"
    
    # Try JNI (Attach JVM thread safely)
    try:
        import jnius
        jnius.autoclass('java.lang.System') # Forces safe JVM attachment
        Runtime = jnius.autoclass('java.lang.Runtime')
        process = Runtime.getRuntime().exec(["su", "-c", adb_cmd])
        process.waitFor()
        app_log("Success: Pyjnius Runtime (su)")
        return
    except Exception as e:
        app_log(f"Pyjnius fallback triggered: {e}")

    # Try subprocess su
    try:
        subprocess.run(["su", "-c", adb_cmd], check=True, timeout=5)
        app_log("Success: subprocess su")
        return
    except Exception as e:
        app_log(f"Subprocess su fallback: {e}")
        
    # Try unrooted rish (Supports both standard and thedjchi forks)
    try:
        unrooted_cmd = "setprop service.adb.tcp.port 5555; setprop ctl.restart adbd; adb tcpip 5555; cmd appops set moe.shizuku.privileged.api RUN_IN_BACKGROUND allow 2>/dev/null; cmd appops set com.thedjchi.shizuku RUN_IN_BACKGROUND allow 2>/dev/null"
        subprocess.run(["rish", "-c", unrooted_cmd], check=False, timeout=5)
        app_log("Success: Shizuku rish (unrooted/thedjchi)")
    except Exception as e:
        app_log(f"Shizuku rish failed: {e}")

class HeartbeatApp(App):
    def build(self):
        self.title = "Scrcpy Heartbeat"
        self.sending = False
        self.discovered_pc_ip = None
        self._discovery_running = False
        
        # Dark Theme
        DARK_BG = (0.1, 0.1, 0.18, 1)
        ACCENT = (0.0, 0.85, 0.647, 1)
        TEXT = (0.878, 0.878, 0.878, 1)
        
        root = BoxLayout(orientation='vertical', padding=20, spacing=15)
        with root.canvas.before:
            Color(*DARK_BG)
            self.rect = Rectangle(size=(10000, 10000), pos=(0,0)) # Massive rect prevents layout crashes
            
        self.label = Label(text="Scrcpy Heartbeat", font_size='24sp', color=ACCENT, size_hint_y=None, height=50)
        self.pc_ip_input = TextInput(text="Discovering PC...", readonly=True, halign='center', font_size='20sp', size_hint_y=None, height=50)
        self.status_label = Label(text="Listening for PC broadcast...", font_size='16sp', color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=30)
        
        # Logging Toggle UI
        log_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        log_layout.add_widget(Label(text="Enable Logging (/sdcard/Logs)", color=TEXT))
        self.log_switch = Switch(active=config.get("logging_enabled", True))
        self.log_switch.bind(active=self.on_log_switch)
        log_layout.add_widget(self.log_switch)
        
        restart_btn = Button(text="🔄 Restart Connection", background_color=(0.059, 0.204, 0.376, 1), color=ACCENT, font_size='18sp', size_hint_y=None, height=60)
        restart_btn.bind(on_press=self.restart_connection)
        
        root.add_widget(self.label)
        root.add_widget(self.pc_ip_input)
        root.add_widget(self.status_label)
        root.add_widget(log_layout)
        root.add_widget(restart_btn)
        
        return root

    def on_log_switch(self, instance, value):
        config["logging_enabled"] = value
        save_config(config)
        app_log(f"Logging toggled to {value}")

    def on_start(self):
        app_log("App started - Launching background workers")
        threading.Thread(target=enable_shizuku_wireless_adb, daemon=True).start()
        self._start_services()

    def restart_connection(self, instance):
        app_log("Restarting connection manually...")
        self._stop_services()
        threading.Thread(target=enable_shizuku_wireless_adb, daemon=True).start()
        self.pc_ip_input.text = "Discovering PC..."
        self.status_label.text = "Listening for PC broadcast..."
        self._start_services()

    def _start_services(self):
        self._discovery_running = True
        threading.Thread(target=self.discovery_listener, daemon=True).start()

    def _stop_services(self):
        self._discovery_running = False
        self.sending = False

    def discovery_listener(self):
        app_log("Discovery listener active")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(2.0)
            sock.bind(("0.0.0.0", config["discovery_port"]))
            
            while self._discovery_running:
                try:
                    data, addr = sock.recvfrom(1024)
                    msg = data.decode('utf-8').strip()
                    if msg.startswith("SCRCPC_HERE"):
                        pc_ip = msg.split()[1]
                        if self.discovered_pc_ip != pc_ip:
                            self.discovered_pc_ip = pc_ip
                            app_log(f"Discovered PC: {pc_ip}")
                            Clock.schedule_once(lambda dt: self.start_heartbeat(pc_ip))
                except socket.timeout:
                    pass
                except Exception as e:
                    app_log(f"Discovery recv error: {e}")
                    time.sleep(1)
        except Exception as e:
            app_log(f"Discovery bind error: {e}")

    def start_heartbeat(self, pc_ip):
        self.pc_ip_input.text = pc_ip
        self.status_label.text = f"Found {pc_ip}! Sending heartbeat..."
        if not self.sending:
            self.sending = True
            threading.Thread(target=self.heartbeat_loop, args=(pc_ip,), daemon=True).start()

    def heartbeat_loop(self, target_ip):
        app_log(f"Starting heartbeat to {target_ip}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        port = config["heartbeat_port"]
        while self.sending:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                phone_ip = s.getsockname()[0]
                s.close()
                
                msg = f"HELLO_USER|{phone_ip}|{config['adb_port']}"
                sock.sendto(msg.encode('utf-8'), (target_ip, port))
                app_log(f"Beat sent: {msg}")
            except Exception as e:
                app_log(f"Heartbeat error: {e}")
            time.sleep(5)
        sock.close()

if __name__ == "__main__":
    try:
        HeartbeatApp().run()
    except Exception as e:
        # Fallback print if logger dies
        print(f"FATAL APP CRASH: {traceback.format_exc()}")