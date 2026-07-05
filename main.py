import sys
import subprocess
import threading
import socket
import time
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QMainWindow
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from heartbeat_listener import start_scrcpy, get_local_ip, LOG_FILE

APP_VERSION = "4.26.7"

DISCOVERY_PORT = 5557  # PC broadcasts HERE
HEARTBEAT_PORT = 5556  # Phone sends heartbeats HERE

def gui_log(msg):
    """Write to both the log file and return for display."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] [GUI] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)
    return line

class DiscoveryBroadcaster:
    """Broadcasts PC's presence so phone can discover it."""
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
        
        gui_log(f"📢 Starting discovery broadcast on port {self.port} (PC IP: {self.local_ip})")
        
        while self.running:
            try:
                # Broadcast to all interfaces
                sock.sendto(message, ('255.255.255.255', self.port))
                # Also send to each interface's broadcast
                for ip in self._get_interface_ips():
                    parts = ip.split('.')
                    if len(parts) == 4:
                        bcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                        sock.sendto(message, (bcast, self.port))
                time.sleep(3)
            except Exception as e:
                gui_log(f"⚠️  Broadcast error: {e}")
                time.sleep(1)
        sock.close()
        
    def _get_interface_ips(self):
        """Get all non-loopback IPs."""
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
            gui_log(f"✅ GUI listener bound to 0.0.0.0:{HEARTBEAT_PORT}")
            sock.settimeout(5.0)
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    ip = addr[0]
                    message = data.decode('utf-8').strip()
                    gui_log(f"💓 GUI got packet from {ip}:{addr[1]} → '{message}'")
                    if "HELLO_HENNY" in message:
                        gui_log(f"🎯 VALID heartbeat from {ip}")
                        self.heartbeat_received.emit(ip)
                    else:
                        gui_log(f"⚠️  Ignoring non-HELLO: '{message}'")
                except socket.timeout:
                    gui_log(f"⏳ GUI heartbeat thread still alive (port {HEARTBEAT_PORT})...")
        except Exception as e:
            gui_log(f"❌ GUI Listener Error: {e}")
            self.log_signal.emit(f"Listener Error: {e}")

    def gui_log(self, msg):
        """Emit log to GUI widget."""
        self.log_signal.emit(msg)

class ScrcpyUltimateLink(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scrcpy Ultimate Link 🎀✨")
        self.setFixedSize(450, 600)
        self.setStyleSheet("background-color: #FFF0F5;") # Lavender Blush 🌸

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        self.title = QLabel("Scrcpy Ultimate Link")
        self.title.setStyleSheet("font-size: 30px; font-weight: bold; color: #C71585;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.subtitle = QLabel("The '0 Seconds' Dream 🚀💖")
        self.subtitle.setStyleSheet("font-size: 16px; font-style: italic; color: #DB7093;")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status
        self.status_label = QLabel("Status: Waiting for heartbeat... 🥺")
        self.status_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FF69B4;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: white; border: 1px solid #FFB6C1; border-radius: 10px; padding: 10px; font-size: 12px;")
        self.log_area.setFixedHeight(200)
        
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_area)

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

    def add_log(self, message):
        self.log_area.append(message)
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_heartbeat(self, ip):
        self.status_label.setText(f"💓 Found {ip}! Connecting... ✨")
        self.status_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FF69B4;")
        threading.Thread(target=self.connect_and_launch, args=(ip,), daemon=True).start()

    def connect_and_launch(self, ip):
        if start_scrcpy(ip):
            self.status_label.setText("🚀 Launched! Enjoy, Henny! 💖")
            self.status_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #00FF00;")
            self.add_log(f"✨ Successfully connected to {ip}")
        else:
            self.status_label.setText("🥺 Connection failed... 🎀")
            self.status_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FF1493;")
            self.add_log(f"❌ Failed to connect to {ip}")

    def closeEvent(self, event):
        if hasattr(self, 'discovery'):
            self.discovery.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScrcpyUltimateLink()
    window.show()
    sys.exit(app.exec())
