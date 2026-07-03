from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
import socket
import threading

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
        
        # IP Input
        self.ip_input = TextInput(
            text="192.168.1.100", # Default placeholder
            hint_text="Enter your PC IP address",
            multiline=False,
            halign='center',
            font_size='20sp'
        )
        
        # Action Button
        self.btn = Button(
            text="Start Heartbeat 💓",
            background_color=(1, 0.41, 0.71, 1),
            font_size='20sp'
        )
        self.btn.bind(on_press=self.toggle_heartbeat)
        
        layout.add_widget(self.label)
        layout.add_widget(self.ip_input)
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
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Enable broadcasting
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_ip = "255.255.255.255"
        
        while self.sending:
            try:
                sock.sendto(message.encode('utf-8'), (broadcast_ip, port))
                import time
                time.sleep(5) 
            except Exception as e:
                print(f"Error: {e}")
                break
        sock.close()

if __name__ == "__main__":
    HeartbeatApp().run()
