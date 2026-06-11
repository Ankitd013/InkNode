import logging
from config import load_env

def get_sensor_telemetry():
    """
    Tries to read from a physical AHT25/AHT20 sensor via I2C bus lines.
    If the sensor isn't physically plugged in, it falls back to data sent by an ESP32.
    """
    try:
        import board
        import adafruit_ahtx0
        
        i2c = board.I2C()
        sensor_device = adafruit_ahtx0.AHTx0(i2c)
        return sensor_device.temperature, sensor_device.relative_humidity
    except Exception as e:
        logging.debug(f"[HAL] Local physical I2C sensor driver unavailable: {e}")
        
        # Hardware fallback: Check if a remote ESP32 has updated our configuration vars
        config = load_env()
        try:
            raw_temp = float(config.get("REMOTE_TEMP"))
            raw_hum = float(config.get("REMOTE_HUM"))
            return raw_temp, raw_hum
        except (TypeError, ValueError):
            # If there's no physical sensor and no ESP32 data, return None
            return None, None
from PIL import Image