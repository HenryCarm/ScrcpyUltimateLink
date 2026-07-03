import flet as ft
import subprocess
import threading
import socket
import os
import sys
from heartbeat_listener import listen_for_heartbeat, start_scrcpy

def main(page: ft.Page):
    try:
        page.title = "Scrcpy Ultimate Link 🎀✨"
        page.window_width = 450
        page.window_height = 600
        page.theme_mode = ft.ThemeMode.LIGHT
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.bgcolor = "#FFF0F5" # Lavender Blush for a cute vibe! 🌸

        # UI Components
        status_text = ft.Text(
            "Status: Waiting for Henny's phone... 🥺", 
            size=20, 
            weight=ft.FontWeight.BOLD, 
            color="#FF69B4" # Hot Pink! 💖
        )
        
        heart_icon = ft.Icon(icon="favorite", color="#FF1493", size=100)
        
        log_area = ft.Column(
            scroll=ft.ScrollMode.ALWAYS,
            expand=True,
            controls=[ft.Text("Logs: ", weight=ft.FontWeight.BOLD)]
        )

        def add_log(message):
            log_area.controls.append(ft.Text(message, size=12))
            page.update()

        def run_listener():
            # We'll wrap the listener to update the UI
            # Since the original listener was a blocking while loop, 
            # we'll implement a modified version for Flet here.
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", 5556))
            
            while True:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8').strip()
                ip = addr[0]
                
                if "HELLO_HENNY" in message:
                    status_text.value = f"💓 Heartbeat from {ip}! Connecting... ✨"
                    heart_icon.scale = 1.2 # Cute little pulse!
                    page.update()
                    
                    if start_scrcpy(ip):
                        status_text.value = "🚀 Scrcpy Launched! Enjoy, Henny! 💖"
                        heart_icon.color = "#00FF00" # Turns green on success!
                        add_log(f"✨ Successfully connected to {ip}")
                    else:
                        status_text.value = "🥺 Connection failed... 🎀"
                        add_log(f"❌ Failed to connect to {ip}")
                    
                    page.update()
                    heart_icon.scale = 1.0
                    page.update()

        # Start listener in a background thread
        threading.Thread(target=run_listener, daemon=True).start()

        # Layout
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("Scrcpy Ultimate Link", size=30, weight=ft.FontWeight.BOLD, color="#C71585", text_align=ft.TextAlign.CENTER),
                    ft.Text("The '0 Seconds' Dream 🚀💖", size=16, italic=True, text_align=ft.TextAlign.CENTER),
                    ft.Divider(height=20, color="transparent"),
                    heart_icon,
                    ft.Divider(height=20, color="transparent"),
                    status_text,
                    ft.Divider(height=20, color="transparent"),
                    ft.Container(
                        content=log_area,
                        border_radius=10,
                        padding=10,
                        height=200,
                        bgcolor="white"
                    ),
                    ft.Divider(height=20, color="transparent"),
                    ft.Text("Stay cute, stay connected! 🎀✨", size=12, color="#DB7093", text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                alignment=ft.Alignment.center
            )
        )
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        os._exit(1) # Kill the whole process instantly! 💥

if __name__ == "__main__":
    ft.app(target=main)
