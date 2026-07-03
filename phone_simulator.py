import socket
import time

# Configuration
TARGET_IP = "127.0.0.1" # Testing locally
TARGET_PORT = 5556
MESSAGE = "HELLO_HENNY 🎀✨"

def send_heartbeat():
    print(f"📱 Simulating phone... Sending heartbeat to {TARGET_IP}:{TARGET_PORT} 💖")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(MESSAGE.encode('utf-8'), (TARGET_IP, TARGET_PORT))
        print("✨ Heartbeat sent! Hope the PC app is listening... (｡♥‿♥｡)")
    except Exception as e:
        print(f"❌ Error sending heartbeat: {e} 🥺")
    finally:
        sock.close()

if __name__ == "__main__":
    send_heartbeat()
