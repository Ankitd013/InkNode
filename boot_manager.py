import subprocess
import time
import logging
import qrcode
import sys
import os
import io
import re
import secrets
import string
import threading
from flask import Flask, request, render_template_string, send_file
from PIL import Image, ImageDraw, ImageFont
from config import BASE_DIR, load_env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - BOOT - %(message)s')
app = Flask(__name__)

SETUP_SSID = "Pi_Setup"
alphabet = string.ascii_letters + string.digits
SETUP_PASS = ''.join(secrets.choice(alphabet) for i in range(8))

# Initialize the global variable safely as None
SetupImage = None

def check_internet():
    """Verifies physical routing path out of the local network environment."""
    logging.info("Pinging 8.8.8.8 to verify internet...")
    try:
        subprocess.check_call(["ping", "-c", "1", "-W", "3", "8.8.8.8"], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def draw_qr_screen(ssid, password, ip_addr):
    """Draws an offline onboarding QR code layout to the display panel."""
    global SetupImage
    
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
        
        fallback_ip = ip_addr if ip_addr else "10.42.0.1"
        details_text = f"SSID: {ssid}\nPASS: {password}\nURL: {fallback_ip}"
        
        # Calculate Y position dynamically so it sits just below the QR code
        details_y = 55 + qr_h + 15 
        draw_black.multiline_text((10, details_y), details_text, font=font, fill=0, spacing=6)
        # Safely copy the canvas into global memory AFTER it is drawn
        SetupImage = LBlackimage.copy()
        
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
    return gateway_ip

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

def network_switch_worker(ssid, password):
    """Background execution loop managing physical hardware interface handover."""
    time.sleep(3)
    logging.info(f"Initiating network handoff to target SSID: {ssid}...")

    subprocess.run(["sudo", "nmcli", "connection", "down", SETUP_SSID])
    subprocess.run(["sudo", "nmcli", "device", "disconnect", "wlan0"], stderr=subprocess.DEVNULL)

    subprocess.run(["sudo", "nmcli", "connection", "delete", ssid], stderr=subprocess.DEVNULL)

    logging.info("Building raw WPA-PSK hidden profile...")
    subprocess.run(["sudo", "nmcli", "connection", "add", "type", "wifi", "con-name", ssid, "ifname", "wlan0", "ssid", ssid], capture_output=True)

    subprocess.run(["sudo", "nmcli", "connection", "modify", ssid, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password], capture_output=True)

    subprocess.run(["sudo", "nmcli", "connection", "modify", ssid, "wifi.hidden", "yes"], capture_output=True)

    logging.info("Executing blind handshake...")
    result = subprocess.run(["sudo", "nmcli", "connection", "up", ssid], capture_output=True, text=True)

    if result.returncode == 0:
        logging.info(f"Successfully connected to network: {ssid}. Recycling active service layers...")
        subprocess.run(["sudo", "systemctl", "restart", "epaper-dash.service"])
    else:
        logging.error(f"Handshake failed: {result.stderr}")
        subprocess.run(["sudo", "reboot"])

def generate_setup_preview(image_black):
    """Converts the 1-bit QR code canvas to an RGB web image."""
    if image_black is None: return Image.new("RGB", (128, 296), (255, 255, 255))
    width, height = image_black.size
    preview = Image.new("RGB", (width, height), (255, 255, 255))
    pixels_preview = preview.load()
    pixels_black = image_black.load()
    for y in range(height):
        for x in range(width):
            if pixels_black[x, y] == 0:
                pixels_preview[x, y] = (30, 30, 30)
    return preview

def session_skip_worker():
    """Tears down the hotspot and launches the dashboard for this session only."""
    time.sleep(2) # Give the browser time to load the status message
    logging.info("Skipping setup for current session. Tearing down hotspot...")
    
    try:
        with open('/tmp/skip_inknode_setup', 'w') as f:
            f.write('1')
    except Exception as e:
        logging.error(f"Failed to write session flag: {e}")
    # Drop the AP interface
    subprocess.run(["sudo", "nmcli", "connection", "down", SETUP_SSID])
    
    # Launch the main application in the background
    subprocess.run(["sudo", "systemctl", "restart", "epaper-dash.service"])

@app.route('/preview.png')
def screen_preview():
    global SetupImage
    preview_img = generate_setup_preview(SetupImage)
    img_io = io.BytesIO()
    preview_img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png', download_name='inknode_setup_qr.png')

@app.route('/skip')
def skip_session():
    threading.Thread(target=session_skip_worker).start()
    return render_template_string("""
    <div style="font-family:sans-serif; text-align:center; padding:40px; color:#f8fafc; background:#0f172a; height:100vh;">
        <h2>Skipping Setup...</h2>
        <p style="color:#94a3b8;">Hotspot shutting down. Launching offline dashboard.</p>
    </div>
    """)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def captive_portal(path):
    # Added the mirror-section HTML block to actually show the screenshot on the page
    return render_template_string("""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>InkNode Setup</title>
    <style>body{font-family:-apple-system,sans-serif;background-color:#0f172a;color:#f8fafc;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:20px;box-sizing:border-box;}
    .box{background-color:#1e293b;padding:32px 24px;border-radius:16px;max-width:400px;width:100%;box-shadow:0 10px 25px rgba(0,0,0,0.3);}
    input{width:100%;padding:12px;background-color:#0f172a;border:1px solid #334155;border-radius:8px;color:#fff;margin-bottom:16px;box-sizing:border-box;}
    button{width:100%;padding:14px;background-color:#3b82f6;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;}
    .mirror-section{margin-top:24px;text-align:center;border-top:1px solid #334155;padding-top:24px;}
    .btn-download{display:inline-block;padding:10px 16px;background-color:#475569;color:#fff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;margin-top:12px;}
    </style></head>
    <body>
        <div class="box">
            <h2>InkNode Setup</h2>
            <p style="color:#94a3b8; font-size: 14px; margin-bottom: 20px;">Connect device to home network</p>
            <form action="/connect" method="POST">
                <input type="text" name="ssid" placeholder="Wi-Fi SSID" required>
                <input type="password" name="password" placeholder="Password">
                <button type="submit">Connect Device</button>
            </form>
            <div style="margin-top: 16px; text-align: center;">
                <a href="/skip" style="color:#94a3b8; text-decoration:none; font-size:14px; font-weight: 500;">
                    Skip (This Session Only) &rarr;
                </a>
            </div>
            <div class="mirror-section">
                <h3 style="margin-bottom:16px; font-size:15px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;">E-Paper Mirror</h3>
                <img src="/preview.png" alt="Hardware Display" style="width:100%; max-width:128px; aspect-ratio:128/296; border:2px solid #334155; border-radius:4px; image-rendering:pixelated; background:white;">
                <br>
                <a href="/preview.png" download="inknode_setup_qr.png" class="btn-download">📥 Download Screenshot</a>
            </div>
        </div>
    </body></html>
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
    # Load environment variables to check the setup flag
    env_config = load_env()
    setup_status = env_config.get("INIT_SETUP", "enabled").strip().lower()
    session_skipped = os.path.exists('/tmp/skip_inknode_setup')

    if setup_status == "disabled" or session_skipped:
        logging.info("INIT_SETUP is disabled in .env. Bypassing Captive Portal...")
        dashboard_path = os.path.join(BASE_DIR, "dashboard.py")
        subprocess.run([sys.executable, dashboard_path])
    else:
        if check_internet():
            logging.info("Online. Handing over to Dashboard...")
            dashboard_path = os.path.join(BASE_DIR, "dashboard.py")
            subprocess.run([sys.executable, dashboard_path])
        else:
            gw_ip = start_hotspot()
            draw_qr_screen(SETUP_SSID, SETUP_PASS, gw_ip)
            app.run(host='0.0.0.0', port=80)
