from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
import socket
import threading
import time


DISCOVERY_PORT = 5557  # Listen for PC broadcast HERE
HEARTBEAT_PORT = 5556  # Send heartbeats HERE
HEARTBEAT_INTERVAL = 5  # seconds


class HeartbeatApp(App):
    def build(self):
        self.title = "Scrcpy Heartbeat 🎀✨"
        self.sending = False
        self.discovered_pc_ip = None
        self.heartbeat_thread = None
        self.last_phone_ip = None
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Header
        self.label = Label(
            text="Hello Henny! 💖", 
            font_size='24sp', 
            color=(1, 0.41, 0.71, 1)
        )
        
        # PC IP Input (auto-filled from discovery)
        self.pc_ip_input = TextInput(
            text="Discovering PC...",
            hint_text="PC IP (auto-discovered)",
            multiline=False,
            halign='center',
            font_size='20sp',
            readonly=True
        )
        
        # Phone IP display
        self.phone_ip_label = Label(
            text="Phone IP: Detecting...",
            font_size='16sp',
            color=(0.5, 0.5, 0.5, 1)
        )
        
        # Status label
        self.status_label = Label(
            text="Listening for PC broadcast...",
            font_size='16sp',
            color=(0.5, 0.5, 0.5, 1)
        )
        
        # Action Button
        self.btn = Button(
            text="Start Heartbeat 💓",
            background_color=(1, 0.41, 0.71, 1),
            font_size='20sp'
        )
        self.btn.bind(on_press=self.toggle_heartbeat)
        
        layout.add_widget(self.label)
        layout.add_widget(self.pc_ip_input)
        layout.add_widget(self.phone_ip_label)
        layout.add_widget(self.status_label)
        layout.add_widget(self.btn)
        
        # Start discovery listener
        threading.Thread(target=self.discovery_listener, daemon=True).start()
        
        # Start phone IP monitor
        threading.Thread(target=self.phone_ip_monitor, daemon=True).start()
        
        return layout

    def discovery_listener(self):
        """Listen for PC's discovery broadcast."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", DISCOVERY_PORT))
        
        print(f"📡 Listening for PC discovery on port {DISCOVERY_PORT}...")
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8').strip()
                print(f"📥 Discovery packet from {addr}: {message}")
                
                if message.startswith("SCRCPC_HERE"):
                    parts = message.split()
                    if len(parts) >= 3:
                        pc_ip = parts[1]
                        heartbeat_port = int(parts[2])
                        if self.discovered_pc_ip != pc_ip:
                            self.discovered_pc_ip = pc_ip
                            # Update UI on main thread
                            Clock.schedule_once(lambda dt: self.update_discovered_ip(pc_ip, heartbeat_port))
                            print(f"✅ Discovered PC at {pc_ip}:{heartbeat_port}")
            except Exception as e:
                print(f"Discovery error: {e}")
                time.sleep(1)

    def phone_ip_monitor(self):
        """Monitor phone's IP and restart heartbeat if it changes."""
        while True:
            try:
                current_ip = self.get_phone_ip()
                if current_ip != self.last_phone_ip:
                    if self.last_phone_ip is not None:
                        print(f"📱 Phone IP changed: {self.last_phone_ip} → {current_ip}")
                        if self.sending:
                            # Restart heartbeat with new IP
                            Clock.schedule_once(lambda dt: self.restart_heartbeat())
                    self.last_phone_ip = current_ip
                    Clock.schedule_once(lambda dt: self.update_phone_ip_display(current_ip))
            except Exception as e:
                print(f"Phone IP monitor error: {e}")
            time.sleep(10)  # Check every 10 seconds

    def get_phone_ip(self):
        """Get phone's local IP."""
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
        self.discovered_pc_ip = pc_ip  # Set this FIRST
        self.pc_ip_input.text = pc_ip
        self.status_label.text = f"Discovered PC: {pc_ip}:{heartbeat_port}"
        if not self.sending:
            # Auto-start heartbeat after discovery
            self.start_heartbeat()

    def start_heartbeat(self):
        if not self.discovered_pc_ip:
            print("No PC IP discovered yet, waiting...")
            return
        self.sending = True
        self.btn.text = "Stop Heartbeat 🥺"
        self.label.text = "Sending Love to PC... 💖✨"
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def restart_heartbeat(self):
        """Restart heartbeat with new IP."""
        print("🔄 Restarting heartbeat due to IP change...")
        self.sending = False
        time.sleep(0.5)
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2)
        self.start_heartbeat()

    def toggle_heartbeat(self, instance):
        if not self.sending:
            self.start_heartbeat()
        else:
            self.sending = False
            self.btn.text = "Start Heartbeat 💓"
            self.label.text = "Hello Henny! 💖"
            self.status_label.text = "Stopped"
            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=2)

    def heartbeat_loop(self):
        """Main heartbeat loop with retry logic."""
        target_ip = self.discovered_pc_ip
        port = HEARTBEAT_PORT
        
        print(f"💓 Starting heartbeat to {target_ip}:{port}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        retry_count = 0
        max_retries = 10
        
        while self.sending:
            try:
                # Refresh phone IP for each heartbeat
                phone_ip = self.get_phone_ip()
                message = f"HELLO_HENNY 🎀✨|{phone_ip}"
                
                sock.sendto(message.encode('utf-8'), (target_ip, port))
                print(f"✅ Sent heartbeat to {target_ip}:{port} (phone IP: {phone_ip})")
                retry_count = 0  # Reset on success
                
            except Exception as e:
                retry_count += 1
                print(f"❌ Heartbeat error (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count >= max_retries:
                    print(f"💀 Max retries reached, stopping heartbeat")
                    self.sending = False
                    Clock.schedule_once(lambda dt: self.on_heartbeat_stopped())
                    break
                
                # Exponential backoff: 2s, 4s, 8s, 16s...
                backoff = min(2 ** retry_count, 60)
                print(f"⏳ Retrying in {backoff}s...")
                time.sleep(backoff)
                continue
            
            time.sleep(HEARTBEAT_INTERVAL)
        
        sock.close()
        print("💓 Heartbeat loop ended")

    def on_heartbeat_stopped(self):
        self.sending = False
        self.btn.text = "Start Heartbeat 💓"
        self.label.text = "Hello Henny! 💖"
        self.status_label.text = "Stopped (error)"

if __name__ == "__main__":
    HeartbeatApp().run()