#!/usr/bin/python
# -*- coding:utf-8 -*-

import unittest
import os
import sys
import logging
from unittest.mock import patch, MagicMock

# Force silent logging during test execution so our test results are clean
logging.disable(logging.CRITICAL)

# Ensure the current directory is in the path
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Import the modules we built
import config
import weather_api
import hal_sensors

class TestInkNodeCore(unittest.TestCase):

    def setUp(self):
        """Runs before every single test to ensure a clean slate."""
        self.test_env = os.path.join(BASE_DIR, ".env.test")
        # Point our config module to a temporary test environment file
        config.ENV_FILE = self.test_env
        if os.path.exists(self.test_env):
            os.remove(self.test_env)

    def tearDown(self):
        """Runs after every single test to clean up temporary test files."""
        if os.path.exists(self.test_env):
            os.remove(self.test_env)

    # -------------------------------------------------------------------------
    # 1. TEST CONFIGURATION ENGINE (config.py)
    # -------------------------------------------------------------------------
    def test_env_read_write(self):
        """Validates that saving settings cleanly writes to and reads from disk."""
        mock_data = {
            "UI_HEADER": "TEST_NODE",
            "LOCATION_LAT": "22.57",
            "LOCATION_LON": "88.36",
            "MQTT_ENABLED": "False"
        }
        # Save it
        config.save_env(mock_data)
        
        # Load it back and verify it matches perfectly
        loaded_data = config.load_env()
        self.assertEqual(loaded_data["UI_HEADER"], "TEST_NODE")
        self.assertEqual(loaded_data["LOCATION_LAT"], "22.57")
        self.assertEqual(loaded_data["MQTT_ENABLED"], "False")

    # -------------------------------------------------------------------------
    # 2. TEST WEATHER API INTEGRATION (weather_api.py)
    # -------------------------------------------------------------------------
    @patch('requests.get')
    def test_weather_api_success(self, mock_get):
        """Simulates a successful Open-Meteo API payload response."""
        # Create a fake successful JSON response mimicking Open-Meteo
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'current_weather': {
                'windspeed': 14.5,
                'weathercode': 3
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        wind, status, code = weather_api.fetch_weather_data()
        
        self.assertEqual(wind, "14.5")
        self.assertEqual(status, "Overcast") # Maps from code 3
        self.assertEqual(code, 3)

    @patch('requests.get')
    def test_weather_api_failure(self, mock_get):
        """Ensures the application handles network offline states gracefully without crashing."""
        # Force the HTTP request to throw a connection error
        mock_get.side_effect = Exception("Timeout connecting to server")
        
        wind, status, code = weather_api.fetch_weather_data()
        
        # Verify our code falls back to error indicators safely
        self.assertEqual(wind, "ERR")
        self.assertEqual(status, "Offline")
        self.assertEqual(code, -1)

    # -------------------------------------------------------------------------
    # 3. TEST SENSOR AGNOSTIC TELEMETRY LAYER (hal_sensors.py)
    # -------------------------------------------------------------------------
    @patch('sys.modules', new_callable=dict)
    def test_sensor_fallback_to_env(self, mock_modules):
        """Verifies that if physical I2C pins are empty, system reads remote ESP32 telemetry."""
        # Force physical hardware drivers to look missing or throw errors
        mock_modules['board'] = None
        mock_modules['adafruit_ahtx0'] = None
        
        # Populate our fake test environment with an active ESP32 payload
        config.save_env({"REMOTE_TEMP": "24.5", "REMOTE_HUM": "62.0"})
        
        # Run the sensor layer poll
        temp, hum = hal_sensors.get_sensor_telemetry()
        
        # Verify the framework automatically switched over to reading the network values
        self.assertEqual(temp, 24.5)
        self.assertEqual(hum, 62.0)

if __name__ == '__main__':
    print("🤖 Starting automated InkNode test suite pipeline...\n")
    unittest.main()