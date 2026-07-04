import socket
import subprocess
import os
import time
from datetime import datetime

# Configuration
HEARTBEAT_PORT = 5556  # Port the phone will send "Hello" to
SCRCPY_BIN = "/home/henry/Apps/scrcpy/scrcpy"
LAST_IP_FILE = "/home/henry/Desktop/last_ip.txt"

# Phone's ADB TCP IP (connect via USB, then enable ADB over TCP)
PHONE_ADB_IP = "10.121.2.114"
PHONE_ADB_PORT = 5555

LOG_FILE = "/home/henry/Documents/Projects/Python/ScrcpyUltimateLink/heartbeat_debug.log"

def log(msg, also_print=True):
    """Write to both log file and stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    if also_print:
        print(line, flush=True)

def get_local_ip():
    """Get the actual local IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"unknown ({e})"

def start_scrcpy(phone_ip=None):
    """Connects to the device and launches scrcpy."""
    # Always use the known phone IP for ADB
    ip = PHONE_ADB_IP
    log(f"🚀 Connecting to phone at {ip}:{PHONE_ADB_PORT}...")
    # Try connecting via ADB
    result = subprocess.run(["adb", "connect", f"{ip}:{PHONE_ADB_PORT}"], capture_output=True, text=True)
    log(f"ADB connect stdout: {result.stdout.strip()}")
    log(f"ADB connect stderr: {result.stderr.strip()}")
    
    if "connected to" in result.stdout.lower():
        log(f"💖 Connected! Launching scrcpy... (｡♥‿♥｡)")
        # Launch scrcpy in a separate process so it doesn't block the listener
        subprocess.Popen([SCRCPY_BIN, "--audio-source=playback", "-s", f"{ip}:{PHONE_ADB_PORT}"])
        return True
    else:
        log(f"🥺 Failed to connect to {ip}. Is ADB over TCP enabled? 🎀")
        return False

def listen_for_heartbeat():
    """Listens for UDP packets from the Android app."""
    local_ip = get_local_ip()
    log("=" * 60)
    log("Scrcpy Ultimate Link - Heartbeat Listener Starting...")
    log(f"Local PC IP: {local_ip}")
    log(f"Heartbeat port: {HEARTBEAT_PORT}")
    log(f"Phone ADB IP: {PHONE_ADB_IP}:{PHONE_ADB_PORT}")
    log(f"SCRCPY_BIN: {SCRCPY_BIN}")
    log(f"ADB available: {subprocess.run(['which', 'adb'], capture_output=True).stdout.decode().strip()}")
    log("=" * 60)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", HEARTBEAT_PORT))
        log(f"✅ Bound to 0.0.0.0:{HEARTBEAT_PORT}")
    except Exception as e:
        log(f"❌ FAILED to bind port {HEARTBEAT_PORT}: {e}")
        log(f"   Check if another process is using it: lsof -i :{HEARTBEAT_PORT}")
        return
    
    sock.settimeout(5.0)  # 5 second timeout so we can log periodic status
    log(f"📡 Heartbeat listener ACTIVE on port {HEARTBEAT_PORT}...")
    log("Waiting for Henny's phone to say hello... 💖✨")
    
    beat_count = 0
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            beat_count += 1
            message = data.decode('utf-8').strip()
            ip = addr[0]
            
            log(f"💓 [Beat #{beat_count}] From {addr[0]}:{addr[1]} → Message: '{message}'")
            
            if "HELLO_HENNY" in message:
                log(f"🎯 VALID heartbeat from {ip}!")
                if start_scrcpy(ip):
                    log("✨ Success! Everything is mirrored! 🚀")
                else:
                    log("🥺 Heartbeat was heard, but ADB connection failed. 🎀")
            else:
                log(f"⚠️  Ignoring non-HELLO packet: '{message}' from {ip}")
                
        except socket.timeout:
            log(f"⏳ Still listening... (received {beat_count} total packets so far)")
        except Exception as e:
            log(f"❌ Socket error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    # Clear old log
    with open(LOG_FILE, "w") as f:
        f.write("")
    log("Logger initialized.")
    try:
        listen_for_heartbeat()
    except KeyboardInterrupt:
        log("\nStopping listener... See you soon, Henny! 🎀💖")
