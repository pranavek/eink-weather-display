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
        draw.text((65, 40), f"W: {wind_kmh} km/h ({int(wind_mph)} mph) {wind_cardinal}", font=self.font_detail, fill=0)

        # Divider between top and bottom
        draw.line((0, 65, width, 65), fill=0, width=2)
        
        # --- Forecast (Bottom Half) ---
        # We have daily data: time, weathercode, temperature_2m_max, temperature_2m_min
        # We want to show today, tomorrow, day after (3 days)
        
        daily_time = daily.get('time', [])
        daily_code = daily.get('weathercode', [])
        daily_max = daily.get('temperature_2m_max', [])
        daily_min = daily.get('temperature_2m_min', [])
        
        # Column width = width / 3
        col_width = width // 3
        
        # Skip today (index 0), show next 3 days (indices 1, 2, 3)
        start_idx = 1
        end_idx = min(start_idx + 3, len(daily_time))
        
        for i in range(start_idx, end_idx):
            # Calculate display index (0, 1, 2) for positioning
            display_i = i - start_idx
            day_x = display_i * col_width
            
            # Date -> Day name
            date_str = daily_time[i]
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = date_obj.strftime('%a') # Mon, Tue...
            
            # Center text in column
            # Day Name
            bbox = draw.textbbox((0, 0), day_name, font=self.font_forecast)
            w = bbox[2] - bbox[0]
            draw.text((day_x + (col_width - w)//2, 70), day_name, font=self.font_forecast, fill=0)
            
            # Icon
            small_icon_size = 25
            # For forecast, assume daytime (is_day=1) since we don't have hourly data
            icon_drawer.draw_icon_for_code(daily_code[i], day_x + (col_width - small_icon_size)//2, 90, small_icon_size, is_day=1)
            
            # Temp Range (Max/Min)
            # e.g. 20/15
            t_max = daily_max[i]
            t_min = daily_min[i]
            temp_range = f"{int(t_max)}/{int(t_min)}"
            bbox = draw.textbbox((0, 0), temp_range, font=self.font_forecast)
            w = bbox[2] - bbox[0]
            draw.text((day_x + (col_width - w)//2, 125), temp_range, font=self.font_forecast, fill=0)


        # Rotate image 180 degrees
        image = image.rotate(180)
        
        self.epd.display(self.epd.getbuffer(image))

    def clear(self):
        self.epd.Clear(0xFF)
        self.epd.sleep()

if __name__ == "__main__":
    ds = DisplayService()
    # Test data
    ds.update_display({'temperature': 20, 'windspeed': 10, 'weathercode': 1})
