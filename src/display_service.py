import os
import sys
import logging
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Ensure lib is in path if running directly (for testing)
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

try:
    from waveshare_epd import epd2in13_V4
except (ImportError, RuntimeError, Exception) as e:
    # Mock for testing on non-Pi systems or if driver fails to init
    print(f"Warning: waveshare_epd driver could not be loaded ({e}). Using mock.")
    class MockEPD:
        width = 122
        height = 250
        def init(self): pass
        def Clear(self, color): pass
        def display(self, image): pass
        def getbuffer(self, image): return []
        def sleep(self): pass
    
    class MockModule:
        EPD = MockEPD
    
    epd2in13_V4 = MockModule()

try:
    from src.icons import IconDrawer
except ImportError:
    from icons import IconDrawer

class DisplayService:
    def __init__(self):
        self.epd = epd2in13_V4.EPD()
        self.epd.init()
        self.epd.Clear(0xFF)
        # Use default font for simplicity
        self.font = ImageFont.load_default()
        # Try to load Montserrat fonts
        font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts')
        try:
            self.font_location = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 24)
            self.font_temp = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 36)
            self.font_detail = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Regular.ttf"), 18)
            self.font_forecast = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 22)
        except IOError:
            self.font_location = ImageFont.load_default()
            self.font_temp = ImageFont.load_default()
            self.font_detail = ImageFont.load_default()
            self.font_forecast = ImageFont.load_default()

    def update_display(self, weather_data, location_name="Weather"):
        if not weather_data:
            return
        
        current = weather_data.get('current', {})
        daily = weather_data.get('daily', {})
        
        if not current:
            return

        # EPD_WIDTH = 122, EPD_HEIGHT = 250
        # Landscape mode: 250x122
        width = self.epd.height
        height = self.epd.width
        
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)
        
        # --- Current Weather (Top Half) ---
        # Icon
        icon_size = 40
        icon_x = 5
        icon_y = 5
        
        # Initialize icon drawer with weather icons font
        font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts', 'weathericons-regular-webfont.ttf')
        icon_drawer = IconDrawer(draw, font_path, icon_size)
        
        code = current.get('weathercode')
        is_day = current.get('is_day', 1)
        icon_drawer.draw_icon_for_code(code, icon_x, icon_y, icon_size, is_day)
        
        # Temp
        temp_c = current.get('temperature')
        temp_f = (temp_c * 9/5) + 32
        temp_text = f"{temp_c}°C / {int(temp_f)}°F"
        
        # Use a slightly smaller font for temp to fit nicely
        draw.text((65, 10), temp_text, font=self.font_location, fill=0)
        
        # Wind
        wind_kmh = current.get('windspeed')
        wind_mph = wind_kmh * 0.621371  # Convert km/h to mph
        wind_dir = current.get('winddirection', 0)
        def get_cardinal(d):
            dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            ix = round(d / (360. / len(dirs)))
            return dirs[ix % len(dirs)]
        wind_cardinal = get_cardinal(wind_dir)
        draw.text((65, 40), f"W: {int(wind_mph)} mph {wind_cardinal}", font=self.font_detail, fill=0)

        # Divider between top and bottom
        draw.line((0, 65, width, 65), fill=0, width=2)
        
        # --- Details & Recommendations (Bottom Half) ---
        # Available Y: 67 to 122 (55px height)
        # 3 lines of ~18px
        
        # Data preparation
        feels_like = current.get('apparent_temperature')
        uv_index = daily.get('uv_index_max', [0])[0]
        sunset_str = daily.get('sunset', [''])[0]
        sunset_time = ""
        if sunset_str:
            try:
                # Format: 2023-10-27T18:00
                dt_sunset = datetime.strptime(sunset_str, '%Y-%m-%dT%H:%M')
                sunset_time = dt_sunset.strftime('%H:%M')
            except ValueError:
                sunset_time = sunset_str
                
        precip_prob = daily.get('precipitation_probability_max', [0])[0]
        weather_code = current.get('weathercode', 0)
        
        # Recommendations Logic
        # Umbrella
        umbrella_rec = "No Umb"
        # Codes 51-67 (drizzle/rain), 80-82 (showers), 95-99 (thunderstorm)
        is_raining = (51 <= weather_code <= 67) or (80 <= weather_code <= 82) or (95 <= weather_code <= 99)
        if precip_prob > 30 or is_raining:
            umbrella_rec = "Take Umb"
            
        # Clothing
        clothing_rec = "T-Shirt"
        if feels_like < 10:
            clothing_rec = "Coat"
        elif feels_like < 20:
            clothing_rec = "Jacket"
            
        # Outdoors
        outdoor_score = "Good"
        # Simple logic: Bad if raining, very high wind, or extreme temps
        if is_raining or feels_like > 35 or feels_like < -5 or wind_kmh > 30:
            outdoor_score = "Poor"
        elif 61 <= weather_code <= 67: # Rain
             outdoor_score = "Poor"
             
        # Draw Lines
        line_height = 18
        y_start = 67
        
        # Line 1: Feels Like | UV | Sunset
        line1_text = f"Feel: {int(feels_like)}°C  UV: {uv_index}  Sun: {sunset_time}"
        draw.text((5, y_start), line1_text, font=self.font_detail, fill=0)
        
        # Line 2: Umbrella | Clothing
        line2_text = f"Rec: {umbrella_rec}, {clothing_rec}"
        draw.text((5, y_start + line_height), line2_text, font=self.font_detail, fill=0)
        
        # Line 3: Outdoor Status
        line3_text = f"Outdoors: {outdoor_score}"
        draw.text((5, y_start + line_height * 2), line3_text, font=self.font_detail, fill=0)


        # Rotate image 180 degrees
        image = image.rotate(180)
        
        self.epd.display(self.epd.getbuffer(image))

    def clear(self):
        self.epd.Clear(0xFF)
        self.epd.sleep()

if __name__ == "__main__":
    ds = DisplayService()
    # Test data
    test_data = {
        'current': {
            'temperature': 20,
            'apparent_temperature': 18,
            'windspeed': 10,
            'weathercode': 1,
            'is_day': 1
        },
        'daily': {
            'uv_index_max': [5],
            'sunset': ['2023-10-27T18:30'],
            'precipitation_probability_max': [10]
        }
    }
    ds.update_display(test_data)
