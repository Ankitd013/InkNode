#!/usr/bin/python
# -*- coding:utf-8 -*-

import os
import time
import sys
from PIL import Image, ImageDraw, ImageFont

# Connect to our custom configurations and display drivers
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from config import BASE_DIR
from hal_display import render_to_physical_screen

# Redefine the icon rendering canvas matrix locally for isolated testing
def draw_weather_icon(draw, x, y, code):
    if code == -1: 
        draw.line((x, y, x+24, y+24), fill=0, width=3)
        draw.line((x+24, y, x, y+24), fill=0, width=3)
        return
    if code in [0, 1]:  
        draw.ellipse((x+3, y+3, x+21, y+21), outline=0, width=2)
        draw.line((x+12, y, x+12, y+24), fill=0, width=2)     
        draw.line((x, y+12, x+24, y+12), fill=0, width=2)     
        draw.line((x+4, y+4, x+20, y+20), fill=0, width=2)   
        draw.line((x+4, y+20, x+20, y+4), fill=0, width=2)   
    elif code in [2, 3, 45, 48]:  
        draw.ellipse((x, y+6, x+16, y+22), outline=0, width=2)
        draw.ellipse((x+6, y, x+24, y+18), outline=0, width=2)
        draw.ellipse((x+14, y+6, x+28, y+22), outline=0, width=2)
        draw.rectangle((x+5, y+8, x+20, y+21), fill=255) 
        draw.line((x+2, y+22, x+26, y+22), fill=0, width=2)
    else:  
        draw.ellipse((x, y+4, x+14, y+18), outline=0, width=2)
        draw.ellipse((x+5, y, x+20, y+15), outline=0, width=2)
        draw.ellipse((x+12, y+4, x+26, y+18), outline=0, width=2)
        draw.rectangle((x+4, y+6, x+18, y+17), fill=255)
        draw.line((x+2, y+18, x+24, y+18), fill=0, width=2)
        draw.line((x+6, y+22, x+3, y+28), fill=0, width=2)
        draw.line((x+13, y+22, x+10, y+28), fill=0, width=2)
        draw.line((x+20, y+22, x+17, y+28), fill=0, width=2)

def run_hardware_icon_test():
    print("📺 Initializing physical E-Paper layout debug sequence...")
    SCREEN_WIDTH, SCREEN_HEIGHT = 128, 296
    
    picdir = os.path.join(BASE_DIR, 'pic')
    font14 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 14)
    
    # Map out our 4 visual test conditions
    test_cases = [
        (-1, "OFFLINE MODE"),
        (0,  "SUNNY / CLEAR"),
        (2,  "CLOUDY / FOG"),
        (51, "RAIN / STORM")
    ]
    
    for code, label in test_cases:
        print(f" └─ Pushing layout state: [Code {code} - {label}] to screen registers...")
        
        # Instantiate fresh blank canvas frames
        LBlackimage = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), 255)  
        LRedimage = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), 255)    
        draw_black = ImageDraw.Draw(LBlackimage)
        draw_red = ImageDraw.Draw(LRedimage)
        
        # UI Top Framing Accent
        draw_red.rectangle((0, 0, SCREEN_WIDTH, 6), fill=0)
        
        # Render the specific text metadata centering it
        bbox = font14.getbbox(label)
        w = bbox[2] - bbox[0]
        draw_black.text(((SCREEN_WIDTH - w) // 2, 25), label, font=font14, fill=0)
        
        # Center and execute the vector shape generation formulas
        icon_x = (SCREEN_WIDTH - 28) // 2
        draw_weather_icon(draw_red, icon_x, 65, code)
        
        # Flash the current canvas matrix to the hardware display pins
        render_to_physical_screen(LBlackimage, LRedimage)
        
        print(" └─ Render complete. Holding layout for 5 seconds...")
        time.sleep(5)

    print("\n✅ Icon debug loop completed successfully. All channels verified.")

if __name__ == '__main__':
    run_hardware_icon_test()
