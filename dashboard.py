#!/usr/bin/python
# -*- coding:utf-8 -*-

import io
import os
import time
import logging
import socket
import threading
from flask import Flask, request, render_template, redirect, url_for, send_file
from PIL import Image, ImageDraw, ImageFont

# Import our custom modules
from config import BASE_DIR, load_env, save_env
from hal_sensors import get_sensor_telemetry
from hal_display import render_to_physical_screen, generate_web_preview
from weather_api import fetch_weather_data
import mqtt_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DASH - %(message)s')
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

LBlackimage = Image.new('1', (128, 296), 255)
LRedimage = Image.new('1', (128, 296), 255)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ==========================================
# WEB CONTROLLER ENDPOINTS
# ==========================================

@app.route('/')
def web_dashboard():
    """Serves the professional control center interface from templates folder."""
    return render_template('dashboard.html', config=load_env(), current_ip=get_local_ip(), saved=request.args.get('saved'))

@app.route('/save-config', methods=['POST'])
def save_config():
    """Catches post parameters from UI, rewrites environment configurations, recycles loops."""
    updated = {
        "MQTT_BROKER": request.form.get("MQTT_BROKER", ""),
        "MQTT_PORT": request.form.get("MQTT_PORT", "1883"),
        "MQTT_USER": request.form.get("MQTT_USER", ""),
        "MQTT_PASS": request.form.get("MQTT_PASS", ""),
        "MQTT_TOPIC_TEMP": request.form.get("MQTT_TOPIC_TEMP", "sensor/temperature"),
        "MQTT_TOPIC_HUM": request.form.get("MQTT_TOPIC_HUM", "sensor/humidity"),
        "LOCATION_LAT": request.form.get("LOCATION_LAT", "0.0"),
        "LOCATION_LON": request.form.get("LOCATION_LON", "0.0"),
        "UI_HEADER": request.form.get("UI_HEADER", "InkNode")
    }
    updated["MQTT_ENABLED"] = "True" if request.form.get("MQTT_ENABLED") else "False"
    updated["HIDE_IP"] = "True" if request.form.get("HIDE_IP") else "False"
            
    save_env(updated)
    
    # Safely recycle MQTT connections
    mqtt_engine.disconnect_mqtt()
    mqtt_engine.init_mqtt()
    
    return redirect(url_for('web_dashboard', saved=True))

@app.route('/api/update-sensor', methods=['POST'])
def receive_esp32_telemetry():
    """Allows remote network microcontrollers like the ESP32 to drop standard JSON telemetry arrays."""
    payload = request.get_json()
    if not payload: return {"status": "error", "message": "Invalid format"}, 400
        
    config = load_env()
    if "temperature" in payload: config["REMOTE_TEMP"] = str(payload["temperature"])
    if "humidity" in payload: config["REMOTE_HUM"] = str(payload["humidity"])
    save_env(config)
    return {"status": "success", "message": "Remote values mapped"}, 200

@app.route('/wipe-wifi', methods=['POST'])
def wipe_wifi():
    import subprocess
    subprocess.Popen(r"sleep 2; sudo nmcli connection delete id $(nmcli -t -f NAME connection show --active | grep -v 'Wired\|lo\|Hotspot'); sudo reboot", shell=True)
    return "<h3>Purging connectivity profiles... Rebooting device.</h3>"

@app.route('/api/screen/preview.png')
def screen_preview():
    """Generates and streams the live e-Paper frame in real-time."""
    try:
        # 1. Fetch your active canvas layouts from your main loop engine
        # 2. Blend them using the helper function
        preview_img = generate_web_preview(LBlackimage, LRedimage)
        
        # 3. Save to an in-memory byte array instead of writing to disk
        img_io = io.BytesIO()
        preview_img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png', download_name='inknode-screenshot.png')
    except Exception as e:
        return f"Failed to calculate display vector frame: {e}", 500
# ==========================================
# 🎨 DRAWING TOOLS & ICON RENDERING
# ==========================================
def draw_weather_icon(draw, x, y, code):
    """
    Draws minimalist geometric weather icons on the 128-pixel wide canvas.
    All shape bounds are carefully budgeted to prevent pixel clipping.
    """
    # 1. Error / Offline Icon (A bold X)
    if code == -1: 
        draw.line((x, y, x+24, y+24), fill=0, width=3)
        draw.line((x+24, y, x, y+24), fill=0, width=3)
        return

    # 2. Sunny / Clear Sky Icon (A crisp centered sun)
    if code in [0, 1]:  
        # Drawn smaller (24x24 box) so it stays centered inside the 128px frame
        draw.ellipse((x+3, y+3, x+21, y+21), outline=0, width=2)
        # Sun rays
        draw.line((x+12, y, x+12, y+24), fill=0, width=2)     # Vertical ray
        draw.line((x, y+12, x+24, y+12), fill=0, width=2)     # Horizontal ray
        draw.line((x+4, y+4, x+20, y+20), fill=0, width=2)   # Diagonal 1
        draw.line((x+4, y+20, x+20, y+4), fill=0, width=2)   # Diagonal 2

    # 3. Cloudy / Foggy Icon (Symmetrical overlapping cloud bubbles)
    elif code in [2, 3, 45, 48]:  
        # Shifted left and down slightly to keep the bubble cluster perfectly square
        draw.ellipse((x, y+6, x+16, y+22), outline=0, width=2)
        draw.ellipse((x+6, y, x+24, y+18), outline=0, width=2)
        draw.ellipse((x+14, y+6, x+28, y+22), outline=0, width=2)
        # Clear the overlapping internal lines cleanly
        draw.rectangle((x+5, y+8, x+20, y+21), fill=255) 
        draw.line((x+2, y+22, x+26, y+22), fill=0, width=2)

    # 4. Rainy / Thunderstorm Icon (Cloud bubble with raindrops)
    else:  
        # The main cloud frame
        draw.ellipse((x, y+4, x+14, y+18), outline=0, width=2)
        draw.ellipse((x+5, y, x+20, y+15), outline=0, width=2)
        draw.ellipse((x+12, y+4, x+26, y+18), outline=0, width=2)
        draw.rectangle((x+4, y+6, x+18, y+17), fill=255)
        draw.line((x+2, y+18, x+24, y+18), fill=0, width=2)
        # Symmetrical downward angled raindrops (Using your red channel indicator)
        draw.line((x+6, y+22, x+3, y+28), fill=0, width=2)
        draw.line((x+13, y+22, x+10, y+28), fill=0, width=2)
        draw.line((x+20, y+22, x+17, y+28), fill=0, width=2)
        
# ==========================================
# BACKGROUND REFRESH RUNNER LOOP
# ==========================================

def display_loop():
    global LBlackimage, LRedimage
    logging.info("Starting background E-Paper refresh loop...")
    picdir = os.path.join(BASE_DIR, 'pic')

    # Fixed physical scaling specifications
    SCREEN_WIDTH, SCREEN_HEIGHT = 128, 296
    
    font12 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)
    font14 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 14)
    font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
    font32 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 32)

    def draw_centered_text(draw_obj, text, y_pos, font_obj, color=0):
        bbox = font_obj.getbbox(text)
        text_width = bbox[2] - bbox[0]
        x_pos = (SCREEN_WIDTH - text_width) // 2
        draw_obj.text((x_pos, y_pos), text, font=font_obj, fill=color)

    mqtt_engine.init_mqtt()

    last_screen_update = 0
    last_mqtt_publish = 0
    last_api_update = 0

    wind_val, weather_status, weather_code = "Load", "Init", -1
    temp_str, hum_str = "--.-°C", "--%"
    raw_temp, raw_hum = None, None

    while True:
        current_time = time.time()
        config = load_env()

        # 1. Weather Update Timer (Every 10 minutes)
        if current_time - last_api_update >= 600:
            wind_val, weather_status, weather_code = fetch_weather_data()
            last_api_update = current_time

        # 2. Sensor Poll & Automation Broadcast (Every 10 seconds)
        if current_time - last_mqtt_publish >= 10:
            t, h = get_sensor_telemetry()
            if t is not None:
                raw_temp, raw_hum = t, h
                temp_str, hum_str = f"{t:.1f}°C", f"{h:.0f}%"
                
                # Broadcasters
                if config.get("MQTT_ENABLED") == "True" and mqtt_engine.mqtt_client:
                    try:
                        mqtt_engine.mqtt_client.publish(config.get("MQTT_TOPIC_TEMP", "sensor/temperature"), round(raw_temp, 2))
                        mqtt_engine.mqtt_client.publish(config.get("MQTT_TOPIC_HUM", "sensor/humidity"), round(raw_hum, 2))
                    except Exception: pass
            last_mqtt_publish = current_time

        # 3. Screen Update Timer (Every 60 seconds)
        if current_time - last_screen_update >= 60:
            time_str = time.strftime('%I:%M %p')
            
            LBlackimage = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), 255)  
            LRedimage = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), 255)    
            draw_black = ImageDraw.Draw(LBlackimage)
            draw_red = ImageDraw.Draw(LRedimage)

            # Draw Premium Swiss Layout UI
            draw_red.rectangle((0, 0, SCREEN_WIDTH, 6), fill=0) # Accent Top Frame Line
            draw_centered_text(draw_black, config.get("UI_HEADER", "InkNode").upper(), 20, font18)
            draw_centered_text(draw_black, time_str, 42, font12)

            # Weather status icon centering
            icon_x = (SCREEN_WIDTH - 40) // 2 if weather_code not in [-1, 0, 1] else (SCREEN_WIDTH - 30) // 2
            draw_weather_icon(draw_red, icon_x, 65, weather_code)
            draw_centered_text(draw_black, weather_status.upper(), 112, font12)
            draw_centered_text(draw_black, temp_str, 135, font32)

            # Lower Grid Dividers & Matrix Layout
            grid_y = 190
            draw_black.line((20, grid_y, SCREEN_WIDTH-20, grid_y), fill=0, width=1)
            
            # Left block: Humidity column
            draw_red.text((20, grid_y + 12), "HUM", font=font12, fill=0)
            draw_black.text((20, grid_y + 28), hum_str, font=font18, fill=0)

            # Right block: Wind column
            draw_red.text((75, grid_y + 12), "WIND", font=font12, fill=0)
            draw_black.text((75, grid_y + 28), wind_val, font=font18, fill=0)
            draw_black.text((75, grid_y + 48), "km/h", font=font12, fill=0)

            # IP Footer block check
            if config.get("HIDE_IP") != "True":
                draw_black.line((20, grid_y + 68, SCREEN_WIDTH-20, grid_y + 68), fill=0, width=1)
                draw_centered_text(draw_black, get_local_ip(), grid_y + 76, font12)

            # Hand images off to abstraction loop wrapper to flash physical hardware
            render_to_physical_screen(LBlackimage, LRedimage)
            last_screen_update = current_time

        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=display_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)
