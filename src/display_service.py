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
            self.font_u8g2_8  = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Regular.ttf"), 10)
            self.font_u8g2_10 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 12)
            self.font_u8g2_12 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 14)
            self.font_u8g2_14 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 16)
            self.font_u8g2_24 = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 28)
            self.font_main_temp = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 20)

            self.font_weather = os.path.join(font_dir, 'weathericons-regular-webfont.ttf')
            self.wi_font_small = ImageFont.truetype(self.font_weather, 10)
        except IOError:
            print("Warning: Fonts not found, using default.")
            self.font_u8g2_8  = ImageFont.load_default()
            self.font_u8g2_10 = ImageFont.load_default()
            self.font_u8g2_12 = ImageFont.load_default()
            self.font_u8g2_14 = ImageFont.load_default()
            self.font_u8g2_24 = ImageFont.load_default()
            self.font_main_temp = ImageFont.load_default()
            self.font_weather = None
            self.wi_font_small = ImageFont.load_default()

    # ------------------------------------------------------------------ helpers

    def _get_weather_description(self, code):
        descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Icy fog",
            51: "Light drizzle",
            53: "Drizzle",
            55: "Heavy drizzle",
            56: "Freezing drizzle",
            57: "Heavy freezing drizzle",
            61: "Light rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Freezing rain",
            67: "Heavy freezing rain",
            71: "Light snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Rain showers",
            81: "Heavy showers",
            82: "Violent showers",
            85: "Snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm w/ hail",
            99: "Thunderstorm w/ hail",
        }
        return descriptions.get(code, "Unknown")

    def _wind_dir_abbrev(self, degrees):
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = round(degrees / 22.5) % 16
        return dirs[idx]

    def _draw_arrow(self, draw, x, y, length, angle, arrow_head_size=3):
        # angle: meteorological (0=N, 90=E, 180=S, 270=W)
        # Convert to PIL math angle
        pil_angle = (angle - 90) * (math.pi / 180.0)

        end_x = x + length * math.cos(pil_angle)
        end_y = y + length * math.sin(pil_angle)

        draw.line((x, y, end_x, end_y), fill=0, width=2)
        draw.ellipse((end_x - 2, end_y - 2, end_x + 2, end_y + 2), fill=0)

    # ------------------------------------------------------------------ display

    def update_display(self, weather_data, location_name="Weather"):
        if not weather_data:
            return

        current = weather_data.get('current', {})
        daily   = weather_data.get('daily', {})
        hourly  = weather_data.get('hourly', {})

        # Landscape mode: 250×122
        width  = self.epd.height  # 250
        height = self.epd.width   # 122

        image = Image.new('1', (width, height), 255)
        draw  = ImageDraw.Draw(image)

        now = datetime.now()

        # ============================================================ HEADER ==
        # Left: location name   Right: weekday + date
        date_str = now.strftime("%a %d-%b-%y")   # e.g. "Thu 16-Apr-26"

        draw.text((2, 0), location_name, font=self.font_u8g2_8, fill=0)

        bbox = draw.textbbox((0, 0), date_str, font=self.font_u8g2_8)
        date_w = bbox[2] - bbox[0]
        draw.text((width - date_w - 2, 0), date_str, font=self.font_u8g2_8, fill=0)

        draw.line((0, 11, width, 11), fill=0)

        # =========================================================== MAIN ====
        temp      = current.get('temperature', 0)
        hum       = current.get('humidity', 0)
        feels     = current.get('apparent_temperature', temp)
        wcode     = current.get('weathercode', 0)
        is_day    = current.get('is_day', 1)

        # --- Left column (x=0–155) ---
        temp_hum_str = f"{temp:.1f}\u00b0 / {hum:.0f}%"
        draw.text((2, 14), temp_hum_str, font=self.font_main_temp, fill=0)

        # Weather icon — placed immediately right of the temp/hum text
        bbox = draw.textbbox((0, 0), temp_hum_str, font=self.font_main_temp)
        icon_x = min(bbox[2] - bbox[0] + 8, 124)
        icon_drawer = IconDrawer(draw, self.font_weather, 28)
        icon_drawer.draw_icon_for_code(wcode, icon_x, 12, 28, is_day)

        # Weather description
        description = self._get_weather_description(wcode)
        draw.text((2, 40), description, font=self.font_u8g2_12, fill=0)

        # --- Vertical separator between left and right columns ---
        draw.line((156, 12, 156, 71), fill=0)

        # --- Right column (x=158–250): astronomy + feels-like ---
        sunrise = daily.get('sunrise', [''])[0]
        sunset  = daily.get('sunset',  [''])[0]
        if sunrise and 'T' in sunrise:
            sunrise = sunrise.split('T')[1][:5]
        if sunset and 'T' in sunset:
            sunset = sunset.split('T')[1][:5]

        ast_x = 159

        def _wi(char_cp, x, y):
            """Draw one weather-icon glyph; return its rendered pixel width + gap."""
            ch = chr(char_cp)
            draw.text((x, y), ch, font=self.wi_font_small, fill=0)
            return draw.textbbox((0, 0), ch, font=self.wi_font_small)[2] + 3

        # Feels-like
        tx = ast_x + _wi(0xf055, ast_x, 14)
        draw.text((tx, 14), f"Feels: {feels:.1f}\u00b0", font=self.font_u8g2_8, fill=0)

        # Sunrise / Sunset — unchanged
        draw.text((ast_x, 26), f"\u2191 {sunrise} / \u2193 {sunset}", font=self.font_u8g2_8, fill=0)

        # UV index
        uv = daily.get('uv_index_max', [None])[0]
        if uv is not None:
            tx = ast_x + _wi(0xf00d, ast_x, 40)
            draw.text((tx, 40), f"UV: {int(round(uv))}", font=self.font_u8g2_8, fill=0)

        # Precipitation probability
        precip = daily.get('precipitation_probability_max', [None])[0]
        if precip is not None:
            tx = ast_x + _wi(0xf019, ast_x, 52)
            draw.text((tx, 52), f"Rain: {int(precip)}%", font=self.font_u8g2_8, fill=0)


        # ======================================================== SEPARATOR ==
        draw.line((0, 72, width, 72), fill=0)

        # ======================================================== FORECAST ===
        hourly_temp = hourly.get('temperature_2m', [])
        hourly_time = hourly.get('time', [])
        hourly_code = hourly.get('weather_code', hourly.get('weathercode', []))

        # Locate the slot closest to the current hour
        start_idx = 0
        current_hour_str = now.strftime("%Y-%m-%dT%H:00")
        for i, t in enumerate(hourly_time):
            if t >= current_hour_str:
                start_idx = i
                break

        col_width = 50   # 5 columns × 50px = 250px

        # Weather columns 0–3
        for col, offset in enumerate([3, 6, 9, 12]):
            idx = start_idx + offset
            if idx >= len(hourly_temp) or idx >= len(hourly_code):
                break

            x0 = col * col_width

            # Time label
            time_val = hourly_time[idx].split('T')[1][:5]
            draw.text((x0 + 5, 74), time_val, font=self.font_u8g2_8, fill=0)

            # Small weather icon
            code  = hourly_code[idx]
            h_int = int(time_val.split(':')[0])
            f_is_day = 1 if 6 <= h_int <= 18 else 0
            icon_small = IconDrawer(draw, self.font_weather, 18)
            icon_small.draw_icon_for_code(code, x0 + 14, 84, 18, f_is_day)

            # High / Low over the 3-hour window
            window = hourly_temp[idx:idx + 3]
            if window:
                t_high = max(window)
                t_low  = min(window)
                temp_str = f"{int(round(t_high))}\u00b0/{int(round(t_low))}\u00b0" \
                           if t_high != t_low else f"{int(round(t_high))}\u00b0"
            else:
                temp_str = f"{int(round(hourly_temp[idx]))}\u00b0"
            draw.text((x0 + 3, 108), temp_str, font=self.font_u8g2_10, fill=0)

            # Column separator
            draw.line((x0 + col_width, 72, x0 + col_width, 122), fill=0)

        # Wind column (x=200–250)
        wind_speed = current.get('windspeed', 0)
        wind_dir   = current.get('winddirection', 0)
        wind_abbr  = self._wind_dir_abbrev(wind_dir)
        wind_ms    = wind_speed / 3.6  # km/h → m/s

        wx = 200
        draw.text((wx + 5, 74), wind_abbr, font=self.font_u8g2_10, fill=0)
        self._draw_arrow(draw, wx + 25, 90, 10, wind_dir)
        draw.text((wx + 5, 100), f"{wind_ms:.1f}", font=self.font_u8g2_10, fill=0)
        draw.text((wx + 5, 111), "m/s", font=self.font_u8g2_8, fill=0)

        # ================================================ ROTATE & DISPLAY ===
        image = image.rotate(180)

        self.epd.display(self.epd.getbuffer(image))
        image.save("last_display.png")

    def clear(self):
        self.epd.Clear(0xFF)
        self.epd.sleep()


if __name__ == "__main__":
    ds = DisplayService()
    test_data = {
        'current': {
            'temperature': 22.5,
            'apparent_temperature': 20.1,
            'humidity': 60,
            'weathercode': 1,
            'is_day': 1,
            'windspeed': 18.4,
            'winddirection': 247,
        },
        'daily': {
            'sunrise': ['2023-10-27T06:30'],
            'sunset':  ['2023-10-27T18:45'],
            'uv_index_max': [7.2],
            'precipitation_probability_max': [30],
        },
        'hourly': {
            'time': [f"2023-10-27T{h:02d}:00" for h in range(24)] +
                    [f"2023-10-28T{h:02d}:00" for h in range(24)],
            'temperature_2m': [20 + (i % 5) for i in range(48)],
            'weathercode':    [1 for _ in range(48)],
        }
    }
    ds.update_display(test_data, "Birmingham, AL")
    print("Saved last_display.png")
