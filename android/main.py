from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
import socket
import threading


DISCOVERY_PORT = 5557  # Listen for PC broadcast HERE
HEARTBEAT_PORT = 5556  # Send heartbeats HERE


class HeartbeatApp(App):
    def build(self):
        self.title = "Scrcpy Heartbeat 🎀✨"
        self.sending = False
        self.discovered_pc_ip = None
        
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
        layout.add_widget(self.status_label)
        layout.add_widget(self.btn)
        
        # Start discovery listener
        threading.Thread(target=self.discovery_listener, daemon=True).start()
        
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
                break

    def update_discovered_ip(self, pc_ip, heartbeat_port):
        self.pc_ip_input.text = pc_ip
        self.status_label.text = f"Discovered PC: {pc_ip}:{heartbeat_port}"
        if not self.sending:
            # Auto-start heartbeat after discovery
            self.start_heartbeat()

    def start_heartbeat(self):
        self.sending = True
        self.btn.text = "Stop Heartbeat 🥺"
        self.label.text = "Sending Love to PC... 💖✨"
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

    def toggle_heartbeat(self, instance):
        if not self.sending:
            self.start_heartbeat()
        else:
            self.sending = False
            self.btn.text = "Start Heartbeat 💓"
            self.label.text = "Hello Henny! 💖"
            self.status_label.text = "Stopped"

    def heartbeat_loop(self):
        message = "HELLO_HENNY 🎀✨"
        target_ip = self.discovered_pc_ip or self.pc_ip_input.text
        port = HEARTBEAT_PORT
        
        print(f"Starting heartbeat to {target_ip}:{port}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        while self.sending:
            try:
                sock.sendto(message.encode('utf-8'), (target_ip, port))
                print(f"Sent heartbeat to {target_ip}:{port}")
                import time
                time.sleep(5) 
            except Exception as e:
                print(f"Error sending heartbeat: {e}")
                import traceback
                traceback.print_exc()
                break
        sock.close()

if __name__ == "__main__":
    HeartbeatApp().run()
