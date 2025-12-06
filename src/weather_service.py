import requests

class WeatherService:
    def __init__(self, lat=40.7128, lon=-74.0060): # Default to New York
        self.lat = lat
        self.lon = lon
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def get_current_weather(self, lat=None, lon=None):
        params = {
            "latitude": lat if lat is not None else self.lat,
            "longitude": lon if lon is not None else self.lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,precipitation_probability_max",
            "timezone": "auto"
        }
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Transform to match expected format
            current_data = data.get("current", {})
            return {
                "current": {
                    "temperature": current_data.get("temperature_2m"),
                    "apparent_temperature": current_data.get("apparent_temperature"),
                    "windspeed": current_data.get("wind_speed_10m"),
                    "winddirection": current_data.get("wind_direction_10m"),
                    "weathercode": current_data.get("weather_code"),
                    "is_day": 1 if current_data.get("is_day") else 0,
                    "time": current_data.get("time")
                },
                "daily": data.get("daily")
            }
        except Exception as e:
            print(f"Error fetching weather: {e}")
            return None

if __name__ == "__main__":
    ws = WeatherService()
    print(ws.get_current_weather())
