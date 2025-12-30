import os
import sys
import logging
import math
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

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
        
        # Load Fonts
        font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts')
        try:
            self.font_u8g2_8 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Regular.ttf"), 10) # Roughly equivalent to u8g2_font_helvB08
            self.font_u8g2_10 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 12)
            self.font_u8g2_12 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 14)
            self.font_u8g2_14 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 16)
            self.font_u8g2_24 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 28)
            
            self.font_weather = os.path.join(font_dir, 'weathericons-regular-webfont.ttf')
        except IOError:
            print("Warning: Fonts not found, using default.")
            self.font_u8g2_8 = ImageFont.load_default()
            self.font_u8g2_10 = ImageFont.load_default()
            self.font_u8g2_12 = ImageFont.load_default()
            self.font_u8g2_14 = ImageFont.load_default()
            self.font_u8g2_24 = ImageFont.load_default()
            self.font_weather = None

    def _get_moon_phase(self, d, m, y):
        """
        Calculates moon phase (0-7).
        0: New, 4: Full.
        """
        if m < 3:
            y -= 1
            m += 12
        m += 1
        c = 365.25 * y
        e = 30.6 * m
        jd = c + e + d - 694039.09
        jd /= 29.53059
        b = int(jd)
        jd -= b
        b = int(jd * 8 + 0.5)
        b = b & 7
        return b

    def _draw_moon(self, draw, x, y, d, m, y_year, diameter=30):
        phase_idx = self._get_moon_phase(d, m, y_year)
        
        # Simple circle for moon base
        draw.ellipse((x, y, x + diameter, y + diameter), outline=0)
        
        # Ideally we draw the phase, but simpler is to just draw a circle and maybe text
        # Or fill it based on phase.
        # Implementation of full complex moon phase drawing with arcs in PIL is non-trivial.
        # I will simplify to: Empty Circle (New), Filled Circle (Full), Half Filled (Quarter).
        
        if phase_idx == 0: # New
            pass # Outline only
        elif phase_idx == 4: # Full
            draw.ellipse((x, y, x + diameter, y + diameter), fill=0)
        elif phase_idx in [1, 2, 3]: # Waxing
            draw.chord((x, y, x + diameter, y + diameter), 270, 90, fill=0) # Right Side filled
        elif phase_idx in [5, 6, 7]: # Waning
            draw.chord((x, y, x + diameter, y + diameter), 90, 270, fill=0) # Left Side filled

    def _draw_arrow(self, draw, x, y, length, angle, arrow_head_size=3):
        # Angle 0 is North (Up) in Meteorology? usually.
        # Convert to math angle (0 is East, counter-clockwise)
        # Met: 0=N, 90=E, 180=S, 270=W
        # PIL: 0=E, 90=S (Clockwise)
        
        # Convert Met angle to PIL angle
        # 0(N) -> 270(PIL)
        # 90(E) -> 0(PIL)
        # 180(S) -> 90(PIL)
        # 270(W) -> 180(PIL)
        pil_angle = (angle - 90) * (math.pi / 180.0) 
        
        end_x = x + length * math.cos(pil_angle)
        end_y = y + length * math.sin(pil_angle)
        
        draw.line((x, y, end_x, end_y), fill=0, width=2)
        
        # Draw Arrow head
        # Not implemented for brevity, line is sufficient for small icon
        draw.ellipse((end_x-2, end_y-2, end_x+2, end_y+2), fill=0)

    def update_display(self, weather_data, location_name="Weather"):
        if not weather_data:
            return
            
        current = weather_data.get('current', {})
        daily = weather_data.get('daily', {})
        hourly = weather_data.get('hourly', {})

        # Landscape mode: 250x122
        width = self.epd.height
        height = self.epd.width
        
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)
        
        # --- Header Section (0 - 11) ---
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        
        # Centered City Name
        text_bbox = draw.textbbox((0, 0), location_name, font=self.font_u8g2_8)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text(((width - text_width) / 2, 0), location_name, font=self.font_u8g2_8, fill=0)
        
        # Right aligned Date
        text_bbox = draw.textbbox((0, 0), date_str, font=self.font_u8g2_8)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text((width - text_width, 0), date_str, font=self.font_u8g2_8, fill=0)
        
        draw.line((0, 11, width, 11), fill=0)
        
        # --- Main Weather Section (12 - 72) ---
        
        # 1. Temp & Humidity (Left Column) -> x=5
        # Stacked vertically to save width
        temp = current.get('temperature', 0)
        hum = current.get('humidity', 0)
        
        temp_str = f"{temp:.1f}°"
        hum_str = f"{hum:.0f}%" 
        
        draw.text((5, 20), temp_str, font=self.font_u8g2_24, fill=0)
        draw.text((5, 50), hum_str, font=self.font_u8g2_14, fill=0)
        
        # 2. Weather Icon (Center-Left) -> x=90
        # Previously x=117 overlap with hum. Now we have space since hum is moved to x=5
        icon_drawer = IconDrawer(draw, self.font_weather, 40)
        icon_drawer.draw_icon_for_code(current.get('weathercode', 0), 90, 25, 40, current.get('is_day', 1))
        
        # 3. Astronomy (Center-Right) -> x=138 (Moved left slightly)
        sunrise = daily.get('sunrise', [''])[0]
        sunset = daily.get('sunset', [''])[0]
        
        if sunrise and 'T' in sunrise: sunrise = sunrise.split('T')[1][:5]
        if sunset and 'T' in sunset: sunset = sunset.split('T')[1][:5]
        
        # Shortened labels
        draw.text((138, 15), f"R {sunrise}", font=self.font_u8g2_8, fill=0)
        draw.text((138, 25), f"S {sunset}", font=self.font_u8g2_8, fill=0)
        
        # Moon Phase Text
        phase_idx = self._get_moon_phase(now.day, now.month, now.year)
        phases = ["New", "WaxCres", "1stQtr", "WaxGib", "Full", "WanGib", "3rdQtr", "WanCres"]
        moon_text = phases[phase_idx]
        draw.text((138, 35), moon_text, font=self.font_u8g2_8, fill=0)
        
        # Draw Moon Icon -> x=186 (Moved left), diameter=28
        self._draw_moon(draw, 186, 20, now.day, now.month, now.year, diameter=28)

        # 4. Wind (Moved to Bottom Right) -> x=220
        # Placeholder strictly to remove it from here
        pass

        # Separator Line for forecast
        draw.line((0, 72, 250, 72), fill=0)
        
        # --- Forecast Section (72 - 122) ---
        # 5 Columns, 44px wide each.
        # Forecast data from hourly
        hourly_temp = hourly.get('temperature_2m', [])
        hourly_time = hourly.get('time', [])
        hourly_code = hourly.get('weathercode', [])
        
        # Find next 5 intervals of 3 hours
        # Assume hourly data starts from 00:00 of today or includes current hour. 
        # We need to find the index closest to now, then +3, +6...
        start_idx = 0
        current_hour_str = now.strftime("%Y-%m-%dT%H:00")
        
        # Simple search for current hour
        for i, t in enumerate(hourly_time):
            if t >= current_hour_str:
                start_idx = i
                break
                
        forecast_indices = [start_idx + 3, start_idx + 6, start_idx + 9, start_idx + 12, start_idx + 15]
        
        for i, idx in enumerate(forecast_indices):
            if idx >= len(hourly_temp): break
            
            x_offset = i * 44
            
            # Time 
            time_val = hourly_time[idx].split('T')[1][:5]
            draw.text((x_offset + 5, 75), time_val, font=self.font_u8g2_8, fill=0)
            
            # Icon
            code = hourly_code[idx]
            # Small icon for forecast
            icon_drawer_small = IconDrawer(draw, self.font_weather, 20)
            # Determine is_day for forecast? Simple logic: 6-18 is day
            h_int = int(time_val.split(':')[0])
            f_is_day = 1 if 6 <= h_int <= 18 else 0
            icon_drawer_small.draw_icon_for_code(code, x_offset + 12, 85, 20, f_is_day)
            
            # Temp
            t_val = hourly_temp[idx]
            draw.text((x_offset + 5, 108), f"{int(t_val)}°", font=self.font_u8g2_10, fill=0)
            
            # Vertical Separator
            draw.line((x_offset + 44, 72, x_offset + 44, 122), fill=0)

        # --- Wind Section (Bottom Right) ---
        # Moves to x=220 (after 5th forecast column)
        wind_speed = current.get('windspeed', 0)
        wind_dir = current.get('winddirection', 0)
        
        wx = 220
        wy = 75
        
        # Adjusted coordinates for small box
        self._draw_arrow(draw, wx + 15, wy + 10, 10, wind_dir)
        draw.text((wx + 5, wy + 20), f"{int(wind_speed)}", font=self.font_u8g2_10, fill=0)
        draw.text((wx + 5, wy + 32), "kmh", font=self.font_u8g2_8, fill=0)


        # Rotate 180
        image = image.rotate(180)
        
        # Display
        self.epd.display(self.epd.getbuffer(image))
        
        # DEBUG: Save image for verification
        image.save("last_display.png")

    def clear(self):
        self.epd.Clear(0xFF)
        self.epd.sleep()

if __name__ == "__main__":
    ds = DisplayService()
    # Mock Data
    test_data = {
        'current': {
            'temperature': 22.5,
            'humidity': 60,
            'weathercode': 1,
            'is_day': 1,
            'windspeed': 15,
            'winddirection': 180
        },
        'daily': {
            'sunrise': ['2023-10-27T06:30'],
            'sunset': ['2023-10-27T18:45'],
        },
        'hourly': {
            'time': [f"2023-10-27T{h:02d}:00" for h in range(24)] + [f"2023-10-28T{h:02d}:00" for h in range(24)],
            'temperature_2m': [20 + (i%5) for i in range(48)],
            'weathercode': [1 for _ in range(48)]
        }
    }
    # Update current time in mock to match "now" for test
    now_h = datetime.now().hour
    # Just run it
    ds.update_display(test_data, "New York")
