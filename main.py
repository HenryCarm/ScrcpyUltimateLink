import sys
import subprocess
import threading
import socket
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QMainWindow
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from heartbeat_listener import start_scrcpy

class HeartbeatWorker(QObject):
    heartbeat_received = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def run(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", 5556))
            while True:
                data, addr = sock.recvfrom(1024)
                ip = addr[0]
                message = data.decode('utf-8').strip()
                if "HELLO_HENNY" in message:
                    self.heartbeat_received.emit(ip)
        except Exception as e:
            self.log_signal.emit(f"Listener Error: {e}")

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

        # Heartbeat Thread
        self.worker = HeartbeatWorker()
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker.heartbeat_received.connect(self.handle_heartbeat)
        self.worker.log_signal.connect(self.add_log)
        self.thread.start()

    def add_log(self, message):
        self.log_area.append(message)

    def handle_heartbeat(self, ip):
        self.status_label.setText(f"💓 Found {ip}! Connecting... ✨")
        self.status_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FF69B4;")
        
        # Run ADB in a separate thread to keep UI responsive
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScrcpyUltimateLink()
    window.show()
    sys.exit(app.exec())
