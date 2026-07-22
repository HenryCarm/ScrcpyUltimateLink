import os, sys, time, socket, threading, json, subprocess, traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

# 1. Request Scoped Storage & Network Permissions
try:
    from android.permissions import request_permissions, Permission
    from android import api_version
    from jnius import autoclass

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Environment = autoclass('android.os.Environment')

    perms = [Permission.INTERNET, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
    request_permissions(perms)

    if api_version >= 30 and not Environment.isExternalStorageManager():
        try:
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            Uri = autoclass('android.net.Uri')
            intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
            intent.setData(Uri.parse("package:" + PythonActivity.mActivity.getPackageName()))
            PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            print(f"MANAGE_EXTERNAL_STORAGE request failed: {e}")
except Exception as e:
    print(f"Permission request failed: {e}")

# 2. Dynamic Config & Logging Paths - fallback to internal storage if external not available
def get_storage_dirs():
    """Get available storage directories, preferring external but falling back to internal"""
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        internal_dir = PythonActivity.mActivity.getFilesDir().getAbsolutePath()
    except:
        # Fallback for testing outside Android
        internal_dir = os.path.join(os.path.expanduser("~"), "scrcpy_link")
    external_config = "/sdcard/scrcpy_heartbeat_config.json"
    external_log_dir = "/sdcard/log"
    
    # Check if we can write to external storage
    can_write_external = False
    try:
        if os.path.exists("/sdcard"):
            test_file = "/sdcard/.scrcpy_test"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            can_write_external = True
    except:
        pass
    
    if can_write_external:
        config_file = external_config
        log_dir = external_log_dir
    else:
        # Use internal storage
        os.makedirs(internal_dir, exist_ok=True)
        config_file = os.path.join(internal_dir, "scrcpy_heartbeat_config.json")
        log_dir = os.path.join(internal_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
    
    return config_file, log_dir, can_write_external

CONFIG_FILE, LOG_DIR, CAN_WRITE_EXTERNAL = get_storage_dirs()
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
        pkg_name = "org.henry.scrcpy.scrcpyheartbeat"
        env = os.environ.copy()
        env["RISH_APPLICATION_ID"] = pkg_name
        unrooted_cmd = "setprop service.adb.tcp.port 5555; setprop ctl.restart adbd; adb tcpip 5555; cmd appops set moe.shizuku.privileged.api RUN_IN_BACKGROUND allow 2>/dev/null; cmd appops set com.thedjchi.shizuku RUN_IN_BACKGROUND allow 2>/dev/null"
        subprocess.run(["rish", "-c", unrooted_cmd], check=False, timeout=5, env=env)
        app_log("Success: Shizuku rish (unrooted/thedjchi)")
    except Exception as e:
        app_log(f"Shizuku rish failed: {e}")

# --- SCREENS ---

DARK_BG = (0.1, 0.1, 0.18, 1)
PANEL_BG = (0.086, 0.13, 0.243, 1)
ACCENT = (0.0, 0.85, 0.647, 1)
TEXT = (0.878, 0.878, 0.878, 1)

class ColoredBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*DARK_BG)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.label = Label(text="Scrcpy Heartbeat", font_size='28sp', bold=True, color=ACCENT, size_hint_y=None, height=60)
        self.pc_ip_input = TextInput(text="Discovering PC...", readonly=True, halign='center', font_size='20sp', background_color=PANEL_BG, foreground_color=TEXT, size_hint_y=None, height=60)
        self.status_label = Label(text="Listening for PC broadcast...", font_size='16sp', color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=40)
        
        # Removed the spacer widget here so the buttons float higher up!
        btn_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=200)
        
        restart_btn = Button(text="🔄 Restart Connection", background_color=(0.059, 0.204, 0.376, 1), color=ACCENT, font_size='18sp')
        restart_btn.bind(on_press=self.restart_connection)
        
        settings_btn = Button(text="⚙️ Settings", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size='18sp')
        settings_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'settings'))

        help_btn = Button(text="📖 Help Guide", background_color=(0.1, 0.4, 0.2, 1), color=ACCENT, font_size='18sp')
        help_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'help'))
        
        btn_layout.add_widget(restart_btn)
        btn_layout.add_widget(settings_btn)
        btn_layout.add_widget(help_btn)
        
        layout.add_widget(self.label)
        layout.add_widget(self.pc_ip_input)
        layout.add_widget(self.status_label)
        layout.add_widget(btn_layout)
        layout.add_widget(Widget()) # Pushed the spacer below the buttons!
        
        self.add_widget(layout)
        
        self.sending = False
        self.discovered_pc_ip = None
        self._discovery_running = False

    def on_enter(self):
        if not self._discovery_running:
            app_log("Main screen entered - Launching background workers")
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

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=20, spacing=15)
        
        title = Label(text="⚙️ Settings", font_size='24sp', bold=True, color=ACCENT, size_hint_y=None, height=50)
        layout.add_widget(title)
        
        # Log Info
        log_info = Label(text=f"Logs saved to:\n{LOG_DIR}", font_size='14sp', color=TEXT, halign='center', size_hint_y=None, height=50)
        layout.add_widget(log_info)
        
        # Logging Toggle
        log_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        log_layout.add_widget(Label(text="Enable Logging", color=TEXT, font_size='16sp'))
        self.log_switch = Switch(active=config.get("logging_enabled", True))
        self.log_switch.bind(active=self.on_log_switch)
        log_layout.add_widget(self.log_switch)
        layout.add_widget(log_layout)
        
        # Ports
        self.add_port_spinner(layout, "ADB Port", "adb_port")
        self.add_port_spinner(layout, "Heartbeat Port", "heartbeat_port")
        self.add_port_spinner(layout, "Discovery Port", "discovery_port")
        
        layout.add_widget(Widget()) # Spacer
        
        back_btn = Button(text="🔙 Back", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size='18sp', size_hint_y=None, height=60)
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'main'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def add_port_spinner(self, layout, label_text, config_key):
        box = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        box.add_widget(Label(text=label_text, color=TEXT, font_size='16sp'))
        spinner = Spinner(text=str(config.get(config_key)), values=[str(p) for p in range(5550, 5560)], background_color=PANEL_BG, color=TEXT)
        spinner.bind(text=lambda instance, text: self.on_port_change(config_key, text))
        box.add_widget(spinner)
        layout.add_widget(box)

    def on_log_switch(self, instance, value):
        config["logging_enabled"] = value
        save_config(config)
        app_log(f"Logging toggled to {value}")

    def on_port_change(self, key, value):
        try:
            config[key] = int(value)
            save_config(config)
            app_log(f"{key} changed to {value}")
        except:
            pass

class HelpScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = ColoredBoxLayout(orientation='vertical', padding=20, spacing=15)
        
        title = Label(text="📖 Help Guide", font_size='24sp', bold=True, color=ACCENT, size_hint_y=None, height=50)
        layout.add_widget(title)
        
        # Guide content in a scroll view
        from kivy.uix.scrollview import ScrollView
        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        
        guide_text = (
            "<b>🚀 Quick Start:</b><br/>"
            "1. Make sure your phone and PC are on the same network (or phone hotspot)<br/>"
            "2. Open this app on PC, then open 'Scrcpy Heartbeat' on your phone<br/>"
            "3. Tap '🔄 Restart Connection' on phone if needed<br/>"
            "4. scrcpy will launch automatically!<br/><br/>"
            
            "<b>📱 Android App Install:</b><br/>"
            "• Download APK from GitHub Actions artifacts<br/>"
            "• Install on phone (allow unknown sources)<br/>"
            "• Grant all permissions when prompted<br/><br/>"
            
            "<b>⚡ Shizuku Setup (Persistent ADB over WiFi):</b><br/>"
            "1. Install <b>Magisk</b> → Install <b>Shizuku</b> module in Magisk app → Reboot<br/>"
            "2. Open <b>Shizuku</b> app → Start service (grant root when prompted)<br/>"
            "3. Install <b>Termux</b> + <b>Termux:Boot</b> from F-Droid/Play Store<br/>"
            "4. In Termux, run these exact commands:<br/>"
            "<code style='color:#00d9a5;'>su -c \"setprop service.adb.tcp.port 5555; setprop persist.adb.tcp.port 5555; "
            "setprop service.adb.tcp.bind 0.0.0.0; stop adbd && start adbd\"</code><br/>"
            "5. Create Termux:Boot script: <code style='color:#00d9a5;'>~/.termux/boot/99-adb-wifi.sh</code><br/>"
            "   (See GitHub wiki for full script - makes ADB persistent across reboots)<br/>"
            "6. Whitelist from battery optimization:<br/>"
            "<code style='color:#00d9a5;'>su -c \"cmd appops set com.termux RUN_IN_BACKGROUND allow\"</code><br/>"
            "<code style='color:#00d9a5;'>su -c \"dumpsys deviceidle whitelist +com.termux\"</code><br/><br/>"
            
            "<b>🔧 Port Configuration:</b><br/>"
            "• Heartbeat Port (default 5556): Phone→PC discovery<br/>"
            "• Discovery Port (default 5557): PC broadcast<br/>"
            "• ADB Port (default 5555): scrcpy connection<br/>"
            "Change if ports conflict, then click '🔄 Restart Server'<br/><br/>"
            
            "<b>🔁 Restart Buttons:</b><br/>"
            "• PC: '🔄 Restart Server' - restarts discovery & heartbeat listeners<br/>"
            "• Phone: '🔄 Restart Connection' - full reconnection reset<br/><br/>"
            
            "<b>🔍 Troubleshooting:</b><br/>"
            "• Phone not found? Check both devices on same network<br/>"
            "• ADB connection refused? Run Shizuku ADB command on phone<br/>"
            "• IP cycling? Restart both apps using restart buttons<br/>"
            "• Black screen on phone? Tap 'Restart Connection' on phone app<br/><br/>"
            
            "<b>📱 Shizuku Persistent Setup (Auto on Boot):</b><br/>"
            "1. Install Termux + Termux:Boot from F-Droid<br/>"
            "2. Create <code>~/.termux/boot/99-adb-wifi.sh</code> with the script from GitHub wiki<br/>"
            "3. <code>chmod +x ~/.termux/boot/99-adb-wifi.sh</code><br/>"
            "4. Run whitelist commands (see GitHub wiki)<br/>"
            "5. Reboot phone - ADB over WiFi starts automatically!<br/><br/>"
            
            "<b>🔗 Links:</b><br/>"
            "• GitHub: <a href='https://github.com/HenryCarm/ScrcpyUltimateLink' style='color:#00d9a5;'>github.com/HenryCarm/ScrcpyUltimateLink</a><br/>"
            "• Shizuku: <a href='https://shizuku.rikka.app/' style='color:#00d9a5;'>shizuku.rikka.app</a><br/>"
            "• Termux:Boot: <a href='https://f-droid.org/packages/com.termux.boot/' style='color:#00d9a5;'>F-Droid</a>"
        )
        
        guide_label = Label(
            text=guide_text,
            markup=True,
            color=TEXT,
            font_size='13sp',
            halign='left',
            valign='top',
            size_hint_y=None
        )
        guide_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))
        guide_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        
        content.add_widget(guide_label)
        scroll.add_widget(content)
        layout.add_widget(scroll)
        
        back_btn = Button(text="🔙 Back", background_color=(0.2, 0.1, 0.4, 1), color=ACCENT, font_size='18sp', size_hint_y=None, height=60)
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'main'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

class HeartbeatApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.add_widget(HelpScreen(name='help'))
        return sm

if __name__ == "__main__":
    try:
        HeartbeatApp().run()
    except Exception as e:
        print(f"FATAL APP CRASH: {traceback.format_exc()}")