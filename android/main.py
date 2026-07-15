from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
import socket
import threading
import time
import json
import os


CONFIG_FILE = "/sdcard/scrcpy_heartbeat_config.json"

def load_config():
    defaults = {
        "heartbeat_port": 5556,
        "discovery_port": 5557,
        "adb_port": 5555,
        "dark_theme": True
    }
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        for k, v in defaults.items():
            if k not in config:
                config[k] = v
        return config
    except:
        return defaults

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except:
        pass

config = load_config()

DISCOVERY_PORT = config["discovery_port"]
HEARTBEAT_PORT = config["heartbeat_port"]
ADB_PORT = config["adb_port"]
HEARTBEAT_INTERVAL = 5  # seconds


# Dark Green Theme Colors
DARK_BG = (0.1, 0.1, 0.18, 1)           # #1a1a2e
PANEL_BG = (0.086, 0.13, 0.243, 1)      # #16213e
BORDER = (0.059, 0.204, 0.376, 1)        # #0f3460
ACCENT = (0.0, 0.85, 0.647, 1)           # #00d9a5
TEXT = (0.878, 0.878, 0.878, 1)          # #e0e0e0
ACCENT_DIM = (0.0, 0.6, 0.45, 1)         # dimmer accent


class HeartbeatApp(App):
    def build(self):
        self.title = "Scrcpy Heartbeat"
        self.sending = False
        self.discovered_pc_ip = None
        self.heartbeat_thread = None
        self.last_phone_ip = None
        self.heartbeat_sock = None
        
        # Thread control flags
        self._discovery_running = False
        self._ip_monitor_running = False
        self._discovery_thread = None
        self._ip_monitor_thread = None
        
        # Root layout with dark background
        root = BoxLayout(orientation='vertical', padding=20, spacing=15)
        root.canvas.before.clear()
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*DARK_BG)
            self.rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_rect, pos=self._update_rect)
        
        # Header
        self.label = Label(
            text="Scrcpy Heartbeat", 
            font_size='24sp', 
            color=ACCENT,
            size_hint_y=None,
            height=50
        )
        
        # PC IP Input (auto-filled from discovery)
        self.pc_ip_input = TextInput(
            text="Discovering PC...",
            hint_text="PC IP (auto-discovered)",
            multiline=False,
            halign='center',
            font_size='20sp',
            readonly=True,
            background_color=PANEL_BG,
            foreground_color=TEXT,
            cursor_color=ACCENT,
            size_hint_y=None,
            height=50
        )
        
        # Phone IP display
        self.phone_ip_label = Label(
            text="Phone IP: Detecting...",
            font_size='16sp',
            color=(0.6, 0.6, 0.6, 1),
            size_hint_y=None,
            height=30
        )
        
        # Status label
        self.status_label = Label(
            text="Listening for PC broadcast...",
            font_size='16sp',
            color=(0.6, 0.6, 0.6, 1),
            size_hint_y=None,
            height=30
        )
        
        # Port Configuration Spinners
        port_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=80)
        
        # Heartbeat Port
        hb_layout = BoxLayout(orientation='vertical', spacing=5)
        hb_label = Label(text="Heartbeat Port", font_size='12sp', color=ACCENT, size_hint_y=None, height=20)
        self.heartbeat_port_spinner = Spinner(
            text=str(HEARTBEAT_PORT),
            values=[str(p) for p in range(5550, 5560)],
            background_color=PANEL_BG,
            color=TEXT,
            size_hint=(None, None),
            size=(100, 40)
        )
        self.heartbeat_port_spinner.bind(text=self.on_heartbeat_port_change)
        hb_layout.add_widget(hb_label)
        hb_layout.add_widget(self.heartbeat_port_spinner)
        port_layout.add_widget(hb_layout)
        
        # Discovery Port
        disc_layout = BoxLayout(orientation='vertical', spacing=5)
        disc_label = Label(text="Discovery Port", font_size='12sp', color=ACCENT, size_hint_y=None, height=20)
        self.discovery_port_spinner = Spinner(
            text=str(DISCOVERY_PORT),
            values=[str(p) for p in range(5550, 5560)],
            background_color=PANEL_BG,
            color=TEXT,
            size_hint=(None, None),
            size=(100, 40)
        )
        self.discovery_port_spinner.bind(text=self.on_discovery_port_change)
        disc_layout.add_widget(disc_label)
        disc_layout.add_widget(self.discovery_port_spinner)
        port_layout.add_widget(disc_layout)
        
        # ADB Port
        adb_layout = BoxLayout(orientation='vertical', spacing=5)
        adb_label = Label(text="ADB Port", font_size='12sp', color=ACCENT, size_hint_y=None, height=20)
        self.adb_port_spinner = Spinner(
            text=str(ADB_PORT),
            values=[str(p) for p in range(5550, 5560)],
            background_color=PANEL_BG,
            color=TEXT,
            size_hint=(None, None),
            size=(100, 40)
        )
        self.adb_port_spinner.bind(text=self.on_adb_port_change)
        adb_layout.add_widget(adb_label)
        adb_layout.add_widget(self.adb_port_spinner)
        port_layout.add_widget(adb_layout)
        
        # Restart Button
        restart_btn = Button(
            text="🔄 Restart Connection",
            background_color=(0.059, 0.204, 0.376, 1),  # #0f3460
            color=(0.0, 0.85, 0.647, 1),  # #00d9a5
            font_size='18sp',
            size_hint_y=None,
            height=60
        )
        restart_btn.bind(on_press=self.restart_connection)
        
        # Help/Guide Button
        help_btn = Button(
            text="📖 Complete Setup Guide",
            background_color=(0.2, 0.1, 0.4, 1),  # Dark purple
            color=(0.0, 0.85, 0.647, 1),  # #00d9a5
            font_size='16sp',
            size_hint_y=None,
            height=50
        )
        help_btn.bind(on_press=self.show_help_guide)
        
        # Add all widgets
        root = BoxLayout(orientation='vertical', padding=20, spacing=15)
        root.canvas.before.clear()
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*DARK_BG)
            self.rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_rect, pos=self._update_rect)
        
        root.add_widget(self.label)
        root.add_widget(self.pc_ip_input)
        root.add_widget(self.phone_ip_label)
        root.add_widget(self.status_label)
        root.add_widget(port_layout)
        root.add_widget(restart_btn)
        root.add_widget(help_btn)
        
        return root

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def on_start(self):
        print("App started")
        self._start_services()

    def _start_services(self):
        """Start all background services with proper thread management."""
        self._stop_services()  # Clean up any existing threads first
        
        self._discovery_running = True
        self._ip_monitor_running = True
        
        self._discovery_thread = threading.Thread(target=self.discovery_listener, daemon=True)
        self._discovery_thread.start()
        
        self._ip_monitor_thread = threading.Thread(target=self.phone_ip_monitor, daemon=True)
        self._ip_monitor_thread.start()
        
        print("Services started")

    def _stop_services(self):
        """Stop all background services gracefully."""
        self._discovery_running = False
        self._ip_monitor_running = False
        self.sending = False
        
        if self.heartbeat_sock:
            self.heartbeat_sock.close()
            self.heartbeat_sock = None
            
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2)
            self.heartbeat_thread = None
            
        # Wait for background threads to finish
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=2)
        if self._ip_monitor_thread and self._ip_monitor_thread.is_alive():
            self._ip_monitor_thread.join(timeout=2)
            
        self._discovery_thread = None
        self._ip_monitor_thread = None
        self.heartbeat_thread = None
        self.heartbeat_sock = None
        self.sending = False

    def on_start(self):
        print("App started")
        self._start_services()

    def on_pause(self):
        print("App paused - keeping heartbeat alive")
        return True

    def on_resume(self):
        print("App resumed")
        # Services should already be running, but ensure they are
        if not self._discovery_running:
            self._start_services()

    def on_stop(self):
        print("App stopping - cleaning up")
        self._stop_services()

    def restart_connection(self, instance):
        print("Restarting connection...")
        self._stop_services()
        self.discovered_pc_ip = None
        self.last_phone_ip = None
        self.pc_ip_input.text = "Discovering PC..."
        self.status_label.text = "Listening for PC broadcast..."
        self.label.text = "Scrcpy Heartbeat"
        self._start_services()
        print("Connection restart initiated")

    # ============================================================
    # DISCOVERY LISTENER - Listens for PC broadcast on DISCOVERY_PORT
    # ============================================================
    def discovery_listener(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)  # Allow checking _discovery_running flag
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
            
            print(f"Listening for PC discovery on port {DISCOVERY_PORT}...")
            
            while self._discovery_running:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = data.decode('utf-8').strip()
                    print(f"Discovery packet from {addr}: {message}")
                    
                    if message.startswith("SCRCPC_HERE"):
                        parts = message.split()
                        if len(parts) >= 3:
                            pc_ip = parts[1]
                            heartbeat_port = int(parts[2])
                            if self.discovered_pc_ip != pc_ip:
                                self.discovered_pc_ip = pc_ip
                                Clock.schedule_once(lambda dt: self.update_discovered_ip(pc_ip, heartbeat_port))
                                print(f"Discovered PC at {pc_ip}:{heartbeat_port}")
                except socket.timeout:
                    continue  # Check _discovery_running flag
                except Exception as e:
                    if self._discovery_running:
                        print(f"Discovery error: {e}")
                        time.sleep(1)
        except Exception as e:
            print(f"Discovery listener failed: {e}")
        finally:
            if sock:
                sock.close()
            print("Discovery listener stopped")

    def phone_ip_monitor(self):
        print("Phone IP monitor started")
        while self._ip_monitor_running:
            try:
                current_ip = self.get_phone_ip()
                if current_ip != self.last_phone_ip:
                    if self.last_phone_ip is not None:
                        print(f"Phone IP changed: {self.last_phone_ip} -> {current_ip}")
                        if self.sending:
                            Clock.schedule_once(lambda dt: self.restart_heartbeat())
                    self.last_phone_ip = current_ip
                    Clock.schedule_once(lambda dt: self.update_phone_ip_display(current_ip))
            except Exception as e:
                print(f"Phone IP monitor error: {e}")
            time.sleep(10)  # Check every 10 seconds

    def get_phone_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"

    def update_phone_ip_display(self, ip):
        self.phone_ip_label.text = f"Phone IP: {ip}"

    def update_discovered_ip(self, pc_ip, heartbeat_port):
        self.discovered_pc_ip = pc_ip
        self.pc_ip_input.text = pc_ip
        self.status_label.text = f"Discovered PC: {pc_ip}:{heartbeat_port}"
        if not self.sending:
            self.start_heartbeat()
        else:
            print(f"Heartbeat already running to {self.discovered_pc_ip}, skipping")

    def start_heartbeat(self):
        if not self.discovered_pc_ip:
            print("No PC IP discovered yet, waiting...")
            return
        if self.sending:
            print("Heartbeat already running!")
            return
        self.sending = True
        self.label.text = "Sending Heartbeat to PC..."
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def restart_heartbeat(self):
        print("Restarting heartbeat due to IP change...")
        self.sending = False
        time.sleep(0.5)
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2)
        self.start_heartbeat()

    def heartbeat_loop(self):
        target_ip = self.discovered_pc_ip
        port = HEARTBEAT_PORT
        
        print(f"Starting heartbeat to {target_ip}:{port}")
        
        self.heartbeat_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        retry_count = 0
        max_retries = 10
        
        while self.sending:
            try:
                phone_ip = self.get_phone_ip()
                # Get the ACTUAL ADB port (wireless debugging port)
                adb_port = self.get_adb_port()
                message = f"HELLO_HENNY|{phone_ip}|{adb_port}"
                
                self.heartbeat_sock.sendto(message.encode('utf-8'), (target_ip, port))
                print(f"Sent heartbeat to {target_ip}:{port} (phone IP: {phone_ip}, ADB port: {adb_port})")
                retry_count = 0
                
            except Exception as e:
                retry_count += 1
                print(f"Heartbeat error (attempt {retry_count}/{max_retries}): {e}")
                import traceback
                traceback.print_exc()
                
                if retry_count >= max_retries:
                    print(f"Max retries reached, stopping heartbeat")
                    self.sending = False
                    Clock.schedule_once(lambda dt: self.on_heartbeat_stopped())
                    break
                
                backoff = min(2 ** retry_count, 60)
                print(f"Retrying in {backoff}s...")
                time.sleep(backoff)
                continue
            
            time.sleep(HEARTBEAT_INTERVAL)
        
        if self.heartbeat_sock:
            self.heartbeat_sock.close()
        print("Heartbeat loop ended")
    
    def get_adb_port(self):
        """Get the actual ADB port (wireless debugging port)"""
        try:
            import subprocess
            # Try to get the ADB port from the system
            result = subprocess.run(["sh", "-c", "getprop service.adb.tcp.port"], capture_output=True, text=True)
            port = result.stdout.strip()
            if port and port.isdigit():
                return int(port)
        except:
            pass
        # Fallback to default
        return 5555

    def on_heartbeat_stopped(self):
        self.sending = False
        self.label.text = "Heartbeat Stopped (Error)"
        self.status_label.text = "Stopped - check logs"

    def on_heartbeat_port_change(self, spinner, text):
        try:
            new_port = int(text)
            config = load_config()
            config["heartbeat_port"] = new_port
            save_config(config)
            print(f"Heartbeat port changed to {new_port}")
        except:
            pass

    def on_discovery_port_change(self, spinner, text):
        try:
            new_port = int(text)
            config = load_config()
            config["discovery_port"] = new_port
            save_config(config)
            print(f"Discovery port changed to {new_port}")
        except:
            pass

    def on_adb_port_change(self, spinner, text):
        try:
            new_port = int(text)
            config = load_config()
            config["adb_port"] = new_port
            save_config(config)
            print(f"ADB port changed to {new_port}")
        except:
            pass

if __name__ == "__main__":
    HeartbeatApp().run()


# ============================================================
# COMPLETE SETUP GUIDE - Copy this to Termux for Shizuku Setup
# ============================================================
"""
===========================================================================
                    SCRCPY ULTIMATE LINK - COMPLETE SETUP GUIDE
===========================================================================

This guide provides everything needed to set up persistent wireless ADB
connection using Shizuku that survives phone reboots completely.

===========================================================================
1. PREREQUISITES
===========================================================================
• Samsung phone with Android 13/14
• Magisk installed and rooted
• Shizuku Magisk module installed (v13.5.2+)
• Termux + Termux:Boot from F-Droid/Play Store
• PC running Ubuntu/Linux with scrcpy 4.0+

===========================================================================
2. SHIZUKU SETUP (Run in Termux - ONE TIME)
===========================================================================
# Open Shizuku app → Start service (grant root when prompted)
# Then in Termux run this EXACT command:
su -c "setprop service.adb.tcp.port 5555; setprop persist.adb.tcp.port 5555; setprop service.adb.tcp.bind 0.0.0.0; stop adbd && start adbd"

# Verify it works:
su -c "netstat -tuln | grep 5555"
# Should show: 0.0.0.0:5555 or :::5555

===========================================================================
3. TERMUX:BOOT SCRIPT (Auto-start on boot)
===========================================================================
# Create the boot script:
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/99-adb-wifi.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash

# Keep Termux awake so One UI doesn't freeze it
termux-wake-lock

# Wait 10 seconds for system & Magisk/Shizuku to fully boot
sleep 10

# Force ADB to listen on 0.0.0.0:5555 (All Interfaces including Hotspot!)
su -c "setprop service.adb.tcp.port 5555"
su -c "setprop persist.adb.tcp.port 5555"
su -c "setprop service.adb.tcp.bind 0.0.0.0"
su -c "stop adbd && start adbd"

# Gentle keep-alive loop that won't spam your CPU or cycle IPs
while true; do
    PORT=$(su -c "getprop service.adb.tcp.port")
    if [ "$PORT" != "5555" ]; then
        su -c "setprop service.adb.tcp.port 5555; setprop persist.adb.tcp.port 5555; stop adbd && start adbd"
    fi
    sleep 60
done &

EOF

# Make it executable:
chmod +x ~/.termux/boot/99-adb-wifi.sh

===========================================================================
4. BATTERY OPTIMIZATION WHITELISTING (Critical!)
===========================================================================
su -c "cmd appops set com.termux RUN_IN_BACKGROUND allow"
su -c "cmd appops set com.termux RUN_ANY_IN_BACKGROUND allow"
su -c "cmd appops set moe.shizuku.privileged.api RUN_IN_BACKGROUND allow"
su -c "cmd appops set moe.shizuku.privileged.api RUN_ANY_IN_BACKGROUND allow"
su -c "dumpsys deviceidle whitelist +com.termux"
su -c "dumpsys deviceidle whitelist +moe.shizuku.privileged.api"
su -c "dumpsys deviceidle whitelist +com.genymobile.scrcpy"

===========================================================================
5. ANDROID 11+ WIRELESS DEBUGGING PAIRING (If needed)
===========================================================================
# On phone: Developer Options → Wireless Debugging → "Pair device with pairing code"
# In Termux:
su -c "adb pair <IP:PORT> <6-digit-code>"
# Then connect:
su -c "adb connect <IP:PORT>"
# Then from PC: adb connect <phone-ip>:5555

===========================================================================
5. VERIFICATION COMMANDS
===========================================================================
# Check ADB is listening on all interfaces:
su -c "netstat -tuln | grep 5555"
# Should show: 0.0.0.0:5555  or  :::5555

# From PC:
adb connect <phone-actual-ip>:5555
# e.g., adb connect 10.18.209.82:5555

# Then launch scrcpy:
scrcpy --audio-source=playback -s <phone-ip>:5555

===========================================================================
6. TROUBLESHOOTING
===========================================================================
• Phone not found? → Same network + WiFi hotspot enabled
• ADB connection refused? → Run Shizuku ADB command on phone
• IP cycling? → Tap 'Restart Connection' on phone app
• Black screen? → Tap 'Restart Connection' on phone app
• ADB over WiFi stops after reboot? → Check Termux:Boot script runs

===========================================================================
7. USEFUL LINKS
===========================================================================
• GitHub: https://github.com/HenryCarm/ScrcpyUltimateLink
• Shizuku: https://shizuku.rikka.app/
• Termux:Boot: https://f-droid.org/packages/com.termux.boot/
• Magisk: https://github.com/topjohnwu/Magisk
===========================================================================
"""