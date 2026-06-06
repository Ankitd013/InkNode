import logging
import paho.mqtt.client as mqtt
from config import load_env

mqtt_client = None

def init_mqtt():
    """Initializes and connects your background MQTT communication engine client loop."""
    global mqtt_client
    config = load_env()
    
    # If MQTT is turned off or has no host target IP, terminate gracefully
    if config.get("MQTT_ENABLED") != "True" or not config.get("MQTT_BROKER"):
        return None
        
    try:
        # Initialize client with standard version 2 processing parameters
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        # If credentials exist, bind them before connecting
        if config.get("MQTT_USER"):
            mqtt_client.username_pw_set(config["MQTT_USER"], config["MQTT_PASS"])
            
        mqtt_client.connect(config["MQTT_BROKER"], int(config.get("MQTT_PORT", 1883)), 60)
        mqtt_client.loop_start()
        logging.info("MQTT transport layers linked successfully.")
        return mqtt_client
    except Exception as e:
        logging.error(f"MQTT Setup Failure: {e}")
        return None

def disconnect_mqtt():
    """Closes down any open data socket loops safely."""
    global mqtt_client
    if mqtt_client:
        try:
            mqtt_client.loop_stop()
        except Exception:
            pass
