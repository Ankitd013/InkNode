import os
import logging
from PIL import Image

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

def render_to_physical_screen(black_buffer, red_buffer=None):
    """
    Sends the compiled image layouts straight to the physical display panel.
    Defaults to Waveshare 2.9" tri-color b_V4 layout via SPI.
    """
    try:
        from waveshare_epd import epd2in9b_V4
        
        epd = epd2in9b_V4.EPD()
        epd.init_Fast()
        
        # If running a monochromatic display layout with no red canvas, create a blank default canvas
        if red_buffer is None:
            red_buffer = Image.new('1', (epd.width, epd.height), 255)
            
        epd.display_Fast(epd.getbuffer(black_buffer), epd.getbuffer(red_buffer))
        epd.sleep()
    except Exception as e:
        # If running code on a PC or Mac without a screen plugged into GPIO pins, catch the skip
        logging.debug(f"[HAL] Hardware panel driver write skipped (Simulation Mode active): {e}")
