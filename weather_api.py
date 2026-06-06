import logging
import requests
from config import load_env

# Mapping table converting Open-Meteo structural integer codes to human-readable text strings
WEATHER_CODES = {
    0: "Clear Sky", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime Fog", 51: "Light Drizzle", 53: "Drizzle", 
    55: "Heavy Drizzle", 61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 80: "Rain Showers", 
    81: "Heavy Showers", 82: "Violent Showers", 95: "Thunderstorm", 
    96: "T-Storm / Hail", 99: "Heavy T-Storm"
}

def fetch_weather_data():
    """Queries the Open-Meteo API using your custom GPS coordinates."""
    config = load_env()
    lat = config.get("LOCATION_LAT", "0.0")
    lon = config.get("LOCATION_LON", "0.0")
    
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        wind = data['current_weather']['windspeed']
        code = data['current_weather']['weathercode']
        status = WEATHER_CODES.get(code, "Unknown")
        
        return f"{wind:.1f}", status, code
    except Exception as e:
        logging.error(f"Weather API Error: {e}")
        return "ERR", "Offline", -1
