import socket
import subprocess
import os

# Configuration
HEARTBEAT_PORT = 5556  # Port the phone will send "Hello" to
ADB_PATH = "/home/henry/Documents/Projects/Python/venv/bin/python" # Not needed for adb but keeping venv ref
SCRCPY_BIN = "/home/henry/Apps/scrcpy/scrcpy"
LAST_IP_FILE = "/home/henry/Desktop/last_ip.txt"

def start_scrcpy(ip):
    """Connects to the device and launches scrcpy."""
    print(f"🚀 Connecting to {ip}...")
    # Try connecting via ADB
    result = subprocess.run(["adb", "connect", f"{ip}:5555"], capture_output=True, text=True)
    
    if "connected to" in result.stdout.lower():
        print(f"💖 Connected! Launching scrcpy... (｡♥‿♥｡)")
        # Launch scrcpy in a separate process so it doesn't block the listener
        subprocess.Popen([SCRCPY_BIN, "--audio-source=playback", "-s", f"{ip}:5555"])
        return True
    else:
        print(f"🥺 Failed to connect to {ip}. Is ADB over TCP enabled? 🎀")
        return False

def listen_for_heartbeat():
    """Listens for UDP packets from the Android app."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", HEARTBEAT_PORT))
    
    print(f"📡 Heartbeat listener active on port {HEARTBEAT_PORT}...")
    print("Waiting for Henny's phone to say hello... 💖✨")
    
    while True:
        data, addr = sock.recvfrom(1024) # Buffer size 1024 bytes
        message = data.decode('utf-8').strip()
        ip = addr[0]
        
        if "HELLO_HENNY" in message:
            print(f"💓 Heartbeat received from {ip}! Message: {message}")
            if start_scrcpy(ip):
                print("✨ Success! Everything is mirrored! 🚀")
            else:
                print("🥺 Heartbeat was heard, but ADB connection failed. 🎀")

if __name__ == "__main__":
    try:
        listen_for_heartbeat()
    except KeyboardInterrupt:
        print("\nStopping listener... See you soon, Henny! 🎀💖")
