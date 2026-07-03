from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
import socket
import threading


# PC's IP - change if needed
PC_IP = "10.79.118.174"
HEARTBEAT_PORT = 5556


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
        
        # PC IP Input (default to known PC IP)
        self.pc_ip_input = TextInput(
            text=PC_IP,
            hint_text="Enter PC IP address",
            multiline=False,
            halign='center',
            font_size='20sp'
        )
        
        # Status label
        self.status_label = Label(
            text=f"Target: {PC_IP}:{HEARTBEAT_PORT}",
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
        
        return layout

    def toggle_heartbeat(self, instance):
        if not self.sending:
            self.sending = True
            self.btn.text = "Stop Heartbeat 🥺"
            self.label.text = "Sending Love to PC... 💖✨"
            self.status_label.text = f"Target: {self.pc_ip_input.text}:{HEARTBEAT_PORT}"
            # Start the heartbeat loop in a separate thread
            threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        else:
            self.sending = False
            self.btn.text = "Start Heartbeat 💓"
            self.label.text = "Hello Henny! 💖"

    def heartbeat_loop(self):
        message = "HELLO_HENNY 🎀✨"
        target_ip = self.pc_ip_input.text
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
