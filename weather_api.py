import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from config import load_env

logger = logging.getLogger("DASH")

def translate_owm_to_openmeteo(owm_code):
    """Intercepts OWM codes and maps them back to your existing e-Paper icons."""
    if owm_code == 800: return 0, "Clear Sky"
    if owm_code in [801, 802]: return 2, "Partly Cloudy"
    if owm_code in [803, 804]: return 3, "Overcast"
    if 700 <= owm_code < 800: return 45, "Foggy"
    if 500 <= owm_code < 600: return 63, "Rain"
    if 300 <= owm_code < 400: return 51, "Drizzle"
    if 200 <= owm_code < 300: return 95, "Thunderstorm"
    if 600 <= owm_code < 700: return 71, "Snow"
    return -1, "Unknown"

def fetch_weather_data():
    """Queries the ultra-stable OpenWeatherMap API."""
    config = load_env()
    lat = config.get("LOCATION_LAT", "0.0")
    lon = config.get("LOCATION_LON", "0.0")
    api_key = config.get("OWM_API_KEY", "")
    
    if not api_key:
        logger.error("Weather API Error: Missing OWM_API_KEY in environment variables.")
        return "0.0", "No API Key", -1

    # Keep the robust retry engine just in case your local Wi-Fi drops
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        # units=metric requests standard Celsius temperatures and m/s wind
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        
        response = session.get(url, timeout=10) 
        response.raise_for_status()
        data = response.json()
        
        # 1. Parse Wind (OWM returns meters/sec, so multiply by 3.6 for km/h)
        raw_wind_ms = data.get('wind', {}).get('speed', 0.0)
        wind_kmh = float(raw_wind_ms) * 3.6
        wind_formatted = f"{wind_kmh:.1f}"
        
        # 2. Parse Weather Status
        weather_array = data.get('weather', [])
        if not weather_array:
            return wind_formatted, "Offline", -1
            
        owm_code = weather_array[0].get('id', 0)
        mapped_code, status_text = translate_owm_to_openmeteo(owm_code)
        
        return wind_formatted, status_text, mapped_code

    except requests.exceptions.RequestException as re:
        logger.error(f"OWM Connection Error: {re}")
        return "0.0", "Offline", -1
    except Exception as e:
        logger.error(f"OWM Parsing Error: {e}")
        return "0.0", "Offline", -1