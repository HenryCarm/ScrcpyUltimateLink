from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
import socket
import threading


def get_local_ip():
    """Get the phone's local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_broadcast_ip():
    """Calculate subnet broadcast address from local IP (assumes /24)."""
    local_ip = get_local_ip()
    parts = local_ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.255"
    return "255.255.255.255"


class HeartbeatApp(App):
    def build(self):
        self.title = "Scrcpy Heartbeat 🎀✨"
        self.sending = False
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Header
        self.label = Label(
            text="Hello Henny! 💖", 
            font_size='24sp', 
            color=(1, 0.41, 0.71, 1) # Hot Pink!
        )
        
        # Show local IP for debugging
        local_ip = get_local_ip()
        broadcast_ip = get_broadcast_ip()
        self.ip_label = Label(
            text=f"Phone IP: {local_ip}\nBroadcast: {broadcast_ip}",
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
        layout.add_widget(self.ip_label)
        layout.add_widget(self.btn)
        
        return layout

    def toggle_heartbeat(self, instance):
        if not self.sending:
            self.sending = True
            self.btn.text = "Stop Heartbeat 🥺"
            self.label.text = "Sending Love to PC... 💖✨"
            # Start the heartbeat loop in a separate thread
            threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        else:
            self.sending = False
            self.btn.text = "Start Heartbeat 💓"
            self.label.text = "Hello Henny! 💖"

    def heartbeat_loop(self):
        port = 5556
        message = "HELLO_HENNY 🎀✨"
        broadcast_ip = get_broadcast_ip()
        
        print(f"Starting heartbeat to {broadcast_ip}:{port}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Enable broadcasting
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.sending:
            try:
                sock.sendto(message.encode('utf-8'), (broadcast_ip, port))
                print(f"Sent heartbeat to {broadcast_ip}:{port}")
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
