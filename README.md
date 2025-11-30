# E-Ink Weather Display

A Python-based weather display application for Waveshare e-ink displays (2.13" V4). Features professional weather icons, modern typography, and automatic updates.

![Weather Display](assets/weather_eink.jpg)

## Features

- 📊 **Current Weather** - Temperature (°C/°F), wind speed (km/h & mph), and conditions
- 📅 **3-Day Forecast** - Daily high/low temperatures with weather icons
- 🎨 **Professional Design** - Weather-icons font for icons, Montserrat font for text
- 🌓 **Day/Night Icons** - Appropriate weather icons based on time of day
- 🔄 **Auto-Updates** - Refreshes every 60 minutes
- 🌍 **Multi-Location** - Support for multiple locations (configurable)

## Hardware Requirements

- Raspberry Pi (any model with GPIO)
- Waveshare 2.13" e-Paper Display V4
- Internet connection for weather API access

## Software Requirements

- Python 3.7+
- Pillow (PIL)
- requests
- RPi.GPIO (for Raspberry Pi)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd weather
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Download Fonts

The required fonts should already be in the `fonts/` directory:
- `weathericons-regular-webfont.ttf` - Weather icons
- `Montserrat-Bold.ttf` - Bold text
- `Montserrat-Regular.ttf` - Regular text

If missing, download them:
- Weather Icons: [erikflowers/weather-icons](https://github.com/erikflowers/weather-icons)
- Montserrat: [Google Fonts](https://fonts.google.com/specimen/Montserrat)

### 4. Configure Location

Edit `src/main.py` to set your location(s):

```python
locations = [
    {"name": "Your City", "lat": YOUR_LATITUDE, "lon": YOUR_LONGITUDE},
]
```

### 5. Test Run

```bash
python3 -m src.main
```

## Running as a System Service

To run the weather display automatically on boot:

### 1. Update Service File

Edit `weather-display.service` to match your setup:
- Change `User=root` to your username if needed
- Update `WorkingDirectory=/root/weather` to your installation path

### 2. Install Service

```bash
# Copy service file
sudo cp weather-display.service /etc/systemd/system/

# Set permissions
sudo chmod 644 /etc/systemd/system/weather-display.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable weather-display.service

# Start service
sudo systemctl start weather-display.service
```

### 3. Manage Service

```bash
# Check status
sudo systemctl status weather-display.service

# View logs
sudo journalctl -u weather-display.service -f

# Restart service
sudo systemctl restart weather-display.service

# Stop service
sudo systemctl stop weather-display.service

# Disable auto-start
sudo systemctl disable weather-display.service
```

## Project Structure

```
weather_display/
├── fonts/                          # Font files
│   ├── weathericons-regular-webfont.ttf
│   ├── Montserrat-Bold.ttf
│   └── Montserrat-Regular.ttf
├── lib/                            # Waveshare e-ink driver
│   └── waveshare_epd/
├── src/                            # Source code
│   ├── __init__.py
│   ├── main.py                     # Main application
│   ├── weather_service.py          # Weather API client
│   ├── display_service.py          # E-ink display manager
│   └── icons.py                    # Weather icon renderer
├── requirements.txt                # Python dependencies
├── weather-display.service         # Systemd service file
├── INSTALL_SERVICE.md             # Service installation guide
└── README.md                       # This file
```

## Configuration

### Weather API

This project uses the [Open-Meteo API](https://open-meteo.com/) which is free and doesn't require an API key.

### Display Layout

The display is divided into two sections:
- **Top Half**: Current weather with large icon, temperature, and wind information
- **Bottom Half**: 3-day forecast with day names, icons, and high/low temperatures

### Update Frequency

By default, the display updates every 60 minutes. To change this, edit `src/main.py`:

```python
# Sleep for 60 minutes
time.sleep(60 * 60)  # Change this value
```

## Customization

### Font Sizes

Edit `src/display_service.py` to adjust font sizes:

```python
self.font_temp = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 36)  # Temperature
self.font_detail = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Regular.ttf"), 18)  # Details
self.font_forecast = ImageFont.truetype(os.path.join(font_dir, "Montserrat-Bold.ttf"), 22)  # Forecast
```

### Icon Sizes

```python
icon_size = 40  # Current weather icon
small_icon_size = 25  # Forecast icons
```

## Troubleshooting

### Service Won't Start

1. Check logs: `sudo journalctl -u weather-display.service -n 100`
2. Verify working directory exists and contains the code
3. Ensure Python dependencies are installed
4. Check file permissions

### Permission Issues

If you get SPI/GPIO permission errors:

```bash
sudo usermod -a -G spi,gpio $USER
# Log out and back in for changes to take effect
```

### Display Not Updating

1. Check internet connectivity: `ping -c 4 8.8.8.8`
2. Verify API access: Check logs for API errors
3. Ensure e-ink display is properly connected

### Font Not Found Errors

Ensure all font files are in the `fonts/` directory with correct names.

## Weather Icon Mappings

The application uses the weather-icons font with WMO weather codes:

| Condition | Day Icon | Night Icon |
|-----------|----------|------------|
| Clear sky | ☀️ | 🌙 |
| Partly cloudy | ⛅ | ☁️ |
| Overcast | ☁️ | ☁️ |
| Rain | 🌧️ | 🌧️ |
| Snow | ❄️ | ❄️ |
| Thunderstorm | ⛈️ | ⛈️ |
| Fog | 🌫️ | 🌫️ |

## Credits

- **Weather Data**: [Open-Meteo API](https://open-meteo.com/)
- **Weather Icons**: [erikflowers/weather-icons](https://github.com/erikflowers/weather-icons)
- **Font**: [Montserrat by Google Fonts](https://fonts.google.com/specimen/Montserrat)
- **E-ink Driver**: [Waveshare](https://www.waveshare.com/)

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
