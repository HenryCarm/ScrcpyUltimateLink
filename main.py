import sys
import subprocess
import threading
import socket
import time
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QMainWindow, QSpinBox, QHBoxLayout, QScrollArea, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon
from heartbeat_listener import start_scrcpy, get_local_ip, LOG_FILE

APP_VERSION = "4.26.7"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    home_dir = os.path.expanduser("~")
    defaults = {
        "heartbeat_port": 5556,
        "discovery_port": 5557,
        "adb_port": 5555,
        "scrcpy_bin": "scrcpy",  # Let the system PATH find scrcpy natively on Win/Mac/Linux
        "last_ip_file": os.path.join(home_dir, "Desktop", "last_ip.txt"),
        "log_file": os.path.join(home_dir, "ScrcpyUltimateLink_debug.log")
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
SCRCPY_BIN = config["scrcpy_bin"]

def gui_log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] [GUI] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)
    return line

class DiscoveryBroadcaster:
    def __init__(self, local_ip, port=DISCOVERY_PORT):
        self.local_ip = local_ip
        self.port = port
        self.running = False
        
    def start(self):
        self.running = True
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
        
    def stop(self):
        self.running = False
        
    def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"SCRCPC_HERE {self.local_ip} {HEARTBEAT_PORT}".encode()
        
        gui_log(f"Starting discovery broadcast on port {self.port} (PC IP: {self.local_ip})")
        
        while self.running:
            try:
                sock.sendto(message, ('255.255.255.255', self.port))
                for ip in self._get_interface_ips():
                    parts = ip.split('.')
                    if len(parts) == 4:
                        bcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                        sock.sendto(message, (bcast, self.port))
                time.sleep(3)
            except Exception as e:
                gui_log(f"Broadcast error: {e}")
                time.sleep(1)
        sock.close()
        
    def _get_interface_ips(self):
        ips = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except:
            pass
        return ips

class HeartbeatWorker(QObject):
    heartbeat_received = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def run(self):
        gui_log("HeartbeatWorker thread starting...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", HEARTBEAT_PORT))
            gui_log(f"GUI listener bound to 0.0.0.0:{HEARTBEAT_PORT}")
            sock.settimeout(5.0)
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    ip = addr[0]
                    message = data.decode('utf-8').strip()
                    gui_log(f"GUI got packet from {ip}:{addr[1]} -> '{message}'")
                    if "HELLO_" in message:
                        gui_log(f"VALID heartbeat from {ip}")
                        self.heartbeat_received.emit(ip)
                    else:
                        gui_log(f"Ignoring non-HELLO: '{message}'")
                except socket.timeout:
                    gui_log(f"GUI heartbeat thread still alive (port {HEARTBEAT_PORT})...")
        except Exception as e:
            gui_log(f"GUI Listener Error: {e}")
            self.log_signal.emit(f"Listener Error: {e}")

    def gui_log(self, msg):
        self.log_signal.emit(msg)

class ScrcpyUltimateLink(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Scrcpy Ultimate Link v{APP_VERSION}")
        self.setFixedSize(500, 650)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "android", "icon.png")
        self.setWindowIcon(QIcon(icon_path))
        
        # Dark green theme (match scrcpy)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QTextEdit {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 8px;
                padding: 10px;
                color: #e0e0e0;
                font-family: monospace;
                font-size: 12px;
            }
            QSpinBox {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 4px;
                padding: 5px;
                color: #e0e0e0;
                font-size: 14px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #0f3460;
                border: none;
                width: 20px;
            }
            QSpinBox::up-arrow { image: none; }
            QSpinBox::down-arrow { image: none; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Port Configuration
        port_layout = QHBoxLayout()
        port_layout.setSpacing(15)
        
        # Heartbeat Port
        hb_layout = QVBoxLayout()
        hb_label = QLabel("Heartbeat Port")
        hb_label.setStyleSheet("color: #00d9a5; font-size: 12px;")
        self.heartbeat_port_spin = QSpinBox()
        self.heartbeat_port_spin.setRange(1024, 65535)
        self.heartbeat_port_spin.setValue(HEARTBEAT_PORT)
        self.heartbeat_port_spin.valueChanged.connect(self.on_port_changed)
        hb_layout.addWidget(hb_label)
        hb_layout.addWidget(self.heartbeat_port_spin)
        port_layout.addLayout(hb_layout)
        
        # Discovery Port
        disc_layout = QVBoxLayout()
        disc_label = QLabel("Discovery Port")
        disc_label.setStyleSheet("color: #00d9a5; font-size: 12px;")
        self.discovery_port_spin = QSpinBox()
        self.discovery_port_spin.setRange(1024, 65535)
        self.discovery_port_spin.setValue(DISCOVERY_PORT)
        self.discovery_port_spin.valueChanged.connect(self.on_port_changed)
        disc_layout.addWidget(disc_label)
        disc_layout.addWidget(self.discovery_port_spin)
        port_layout.addLayout(disc_layout)
        
        # ADB Port
        adb_layout = QVBoxLayout()
        adb_label = QLabel("ADB Port")
        adb_label.setStyleSheet("color: #00d9a5; font-size: 12px;")
        self.adb_port_spin = QSpinBox()
        self.adb_port_spin.setRange(1024, 65535)
        self.adb_port_spin.setValue(ADB_PORT)
        self.adb_port_spin.valueChanged.connect(self.on_port_changed)
        adb_layout.addWidget(adb_label)
        adb_layout.addWidget(self.adb_port_spin)
        port_layout.addLayout(adb_layout)
        
        layout.addLayout(port_layout)

        # Title
        self.title = QLabel("Scrcpy Ultimate Link")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00d9a5;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.subtitle = QLabel(f"Version {APP_VERSION} - Dark Green Edition")
        self.subtitle.setStyleSheet("font-size: 14px; font-style: italic; color: #00d9a5;")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status
        self.status_label = QLabel("Status: Waiting for heartbeat...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d9a5;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #16213e; border: 1px solid #0f3460; border-radius: 8px; padding: 10px; color: #e0e0e0; font-family: monospace; font-size: 12px;")
        self.log_area.setFixedHeight(250)
        
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_area)

        # Help/Guide Section
        self.help_area = QScrollArea()
        self.help_area.setWidgetResizable(True)
        self.help_area.setFixedHeight(300)
        self.help_area.setStyleSheet("""
            QScrollArea {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 8px;
            }
            QScrollBar:vertical {
                background-color: #1a1a2e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #00d9a5;
                border-radius: 4px;
                min-height: 30px;
            }
        """)
        
        help_widget = QWidget()
        help_layout = QVBoxLayout(help_widget)
        help_layout.setSpacing(15)
        help_layout.setContentsMargins(20, 20, 20, 20)
        
        # Help Title
        help_title = QLabel("📖 Complete Setup Guide")
        help_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00d9a5;")
        help_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_layout.addWidget(help_title)
        
        # Guide Content
        guide_text = QLabel()
        guide_text.setWordWrap(True)
        guide_text.setStyleSheet("color: #e0e0e0; font-size: 13px; line-height: 1.6;")
        guide_text.setText(
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
        help_layout.addWidget(help_title)
        help_layout.addWidget(guide_text)
        
        self.help_area.setWidget(help_widget)
        layout.addWidget(self.help_area)
        
        # Restart Server Button
        self.restart_btn = QPushButton("🔄 Restart Server")
        self.restart_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                color: #00d9a5;
                border: 2px solid #00d9a5;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d9a5;
                color: #1a1a2e;
            }
            QPushButton:pressed {
                background-color: #00b890;
            }
        """)
        self.restart_btn.clicked.connect(self.restart_services)
        layout.addWidget(self.restart_btn)

        # Initialize threads
        self.discovery = None
        self.worker = None
        self.thread = None
        
        # Start services
        self.restart_services()

    def restart_services(self):
        global HEARTBEAT_PORT, DISCOVERY_PORT, ADB_PORT
        # Stop existing services
        if self.discovery:
            self.discovery.stop()
        
        # Start discovery broadcaster
        local_ip = get_local_ip()
        self.discovery = DiscoveryBroadcaster(local_ip)
        self.discovery.start()
        
        # Heartbeat Thread
        self.worker = HeartbeatWorker()
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker.heartbeat_received.connect(self.handle_heartbeat)
        self.worker.log_signal.connect(self.add_log)
        self.thread.start()

    def on_port_changed(self):
        global HEARTBEAT_PORT, DISCOVERY_PORT, ADB_PORT
        HEARTBEAT_PORT = self.heartbeat_port_spin.value()
        DISCOVERY_PORT = self.discovery_port_spin.value()
        ADB_PORT = self.adb_port_spin.value()
        config = load_config()
        config["heartbeat_port"] = HEARTBEAT_PORT
        config["discovery_port"] = DISCOVERY_PORT
        config["adb_port"] = ADB_PORT
        save_config(config)
        gui_log(f"Ports updated: Heartbeat={HEARTBEAT_PORT}, Discovery={DISCOVERY_PORT}, ADB={ADB_PORT}")
        # Restart services with new ports
        self.restart_services()

    def add_log(self, message):
        self.log_area.append(message)
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_heartbeat(self, ip):
        self.status_label.setText(f"Found {ip}! Connecting...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d9a5;")
        threading.Thread(target=self.connect_and_launch, args=(ip,), daemon=True).start()

    def connect_and_launch(self, ip):
        if start_scrcpy(ip):
            self.status_label.setText("Launched! Enjoy!")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d9a5;")
            self.add_log(f"Successfully connected to {ip}")
        else:
            self.status_label.setText("Connection failed...")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff6b6b;")
            self.add_log(f"Failed to connect to {ip}")

    def closeEvent(self, event):
        if hasattr(self, 'discovery'):
            self.discovery.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "android", "icon.png")
    app.setWindowIcon(QIcon(icon_path))
    window = ScrcpyUltimateLink()
    window.show()
    sys.exit(app.exec())