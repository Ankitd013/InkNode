import subprocess
import time
import logging
import qrcode
import sys
import os
import re
import threading
from flask import Flask, request, render_template_string
from PIL import Image, ImageDraw, ImageFont
from config import BASE_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - BOOT - %(message)s')
app = Flask(__name__)

SETUP_SSID = "Pi_Setup"
SETUP_PASS = "Setup12345"

def check_internet():
    """Verifies physical routing path out of the local network environment."""
    logging.info("Pinging 8.8.8.8 to verify internet...")
    try:
        subprocess.check_call(["ping", "-c", "1", "-W", "3", "8.8.8.8"], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def draw_qr_screen(ssid, password):
    """Draws an offline onboarding QR code layout to the display panel."""
    try:
        from hal_display import render_to_physical_screen
        logging.info("Offline. Drawing Captive Portal QR to E-Paper...")
        
        wifi_string = f"WIFI:S:{ssid};T:WPA;P:{password};;"
        qr = qrcode.QRCode(box_size=3, border=1)
        qr.add_data(wifi_string)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('1')
        
        # 128x296 resolution template mapping profiles
        SCREEN_WIDTH, SCREEN_HEIGHT = 128, 296
        LBlackimage = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), 255)
        draw_black = ImageDraw.Draw(LBlackimage)
        
        try:
            font = ImageFont.truetype(os.path.join(BASE_DIR, 'pic', 'Font.ttc'), 14)
        except Exception:
            font = ImageFont.load_default()
            
        display_text = "SYSTEM OFFLINE\nScan QR to Setup"
        bbox = draw_black.multiline_textbbox((0, 0), display_text, font=font, align="center")
        text_w = bbox[2] - bbox[0]
        text_x = (SCREEN_WIDTH - text_w) // 2
        
        draw_black.multiline_text((text_x, 8), display_text, font=font, fill=0, align="center", spacing=4)
        
        qr_w, qr_h = qr_img.size
        qr_x = (SCREEN_WIDTH - qr_w) // 2
        LBlackimage.paste(qr_img, (qr_x, 55))
        
        render_to_physical_screen(LBlackimage)
    except Exception as e:
        logging.warning(f"[HAL] Core boot drawing routine bypassed (Simulation Mode): {e}")

def start_hotspot():
    """Configures localized network access point profile using nmcli."""
    logging.info("Clearing network states and forcing Legacy WPA1/TKIP Hotspot...")
    subprocess.run("sudo rfkill unblock wifi", shell=True)
    subprocess.run("sudo nmcli radio wifi on", shell=True)
    subprocess.run("sudo nmcli device disconnect wlan0", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f'sudo nmcli connection delete "{SETUP_SSID}"', shell=True, stderr=subprocess.DEVNULL)
    
    subprocess.run(f'sudo nmcli connection add type wifi ifname wlan0 con-name "{SETUP_SSID}" autoconnect no ssid "{SETUP_SSID}"', shell=True)
    
    setup_cmd = (
        f'sudo nmcli connection modify "{SETUP_SSID}" '
        f'802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 6 '
        f'ipv4.method shared ipv6.method disabled '
        f'wifi-sec.key-mgmt wpa-psk wifi-sec.proto wpa '
        f'wifi-sec.pairwise tkip wifi-sec.group tkip '
        f'wifi-sec.psk "{SETUP_PASS}" wifi-sec.pmf disable'
    )
    subprocess.run(setup_cmd, shell=True)
    subprocess.run(f'sudo nmcli connection up "{SETUP_SSID}"', shell=True)
    
    time.sleep(1.5)
    gateway_ip = None
    try:
        ip_output = subprocess.run("ip -4 addr show wlan0", shell=True, capture_output=True, text=True)
        match = re.search(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ip_output.stdout)
        if match: gateway_ip = match.group(1)
    except Exception: pass

    if gateway_ip:
        config_dir = "/etc/NetworkManager/dnsmasq-shared.d"
        config_file = f"{config_dir}/inknode-captive.conf"
        pid_file = "/run/nm-dnsmasq-wlan0.pid"
        try:
            if not os.path.exists(config_dir): subprocess.run(f"sudo mkdir -p {config_dir}", shell=True)
            subprocess.run(f'echo "address=/#/{gateway_ip}" | sudo tee {config_file}', shell=True)
            if os.path.exists(pid_file): subprocess.run(f"sudo kill -HUP $(cat {pid_file})", shell=True)
            else: subprocess.run("sudo killall -HUP dnsmasq", shell=True, stderr=subprocess.DEVNULL)
        except Exception: pass

def network_switch_worker(ssid, password):
    """Background loop managing physical hardware interface connection handover."""
    time.sleep(3)
    subprocess.run(f'sudo nmcli connection down "{SETUP_SSID}"', shell=True)
    subprocess.run("sudo nmcli device disconnect wlan0", shell=True, stderr=subprocess.DEVNULL)
    
    connect_cmd = f'sudo nmcli device wifi connect "{ssid}" password "{password}" name "{ssid}"'
    result = subprocess.run(connect_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        subprocess.run("sudo systemctl restart epaper-dash.service", shell=True)
    else:
        subprocess.run("sudo reboot", shell=True)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def captive_portal(path):
    return render_template_string("""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>InkNode Setup</title>
    <style>body{font-family:-apple-system,sans-serif;background-color:#0f172a;color:#f8fafc;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}
    .box{background-color:#1e293b;padding:32px 24px;border-radius:16px;max-width:400px;width:100%;box-shadow:0 10px 25px rgba(0,0,0,0.3);}
    input{width:100%;padding:12px;background-color:#0f172a;border:1px solid #334155;border-radius:8px;color:#fff;margin-bottom:16px;box-sizing:border-box;}
    button{width:100%;padding:14px;background-color:#3b82f6;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;}</style></head>
    <body><div class="box"><h2>InkNode Setup</h2><p>Connect device to home network</p>
    <form action="/connect" method="POST"><input type="text" name="ssid" placeholder="Wi-Fi SSID" required><input type="password" name="password" placeholder="Password"><button type="submit">Connect Device</button></form></div></body></html>
    """)

@app.route('/connect', methods=['POST'])
def connect_wifi():
    ssid = request.form.get('ssid')
    password = request.form.get('password')
    if not ssid: return "SSID missing.", 400
    threading.Thread(target=network_switch_worker, args=(ssid, password)).start()
    return render_template_string("<h3>Applying Credentials... Disconnecting from hotspot.</h3>")

if __name__ == '__main__':
    time.sleep(10)
    if check_internet():
        logging.info("Online. Handing over to Dashboard...")
        dashboard_path = os.path.join(BASE_DIR, "dashboard.py")
        subprocess.run([sys.executable, dashboard_path])
    else:
        start_hotspot()
        draw_qr_screen(SETUP_SSID, SETUP_PASS)
        app.run(host='0.0.0.0', port=80)
