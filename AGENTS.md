# E-Ink Weather Display - Developer/Agent Guide

## Project Overview
A Python-based weather display application for Waveshare 2.13" e-Paper Display V4. Designed for Raspberry Pi.

## Tech Stack
- **Language**: Python 3.7+
- **Hardware Interaction**: `waveshare-epd` (Library), `RPi.GPIO`
- **Graphics**: `Pillow` (PIL) for image generation
- **Data**: `requests` for Open-Meteo API
- **Deployment**: Systemd service (`weather-display.service`)

## Project Structure
- `src/main.py`: Entry point. Handles scheduling and multi-location looping.
- `src/display_service.py`: Core logic for drawing to the e-ink screen. Contains `DisplayService` class.
- `src/weather_service.py`: Fetches data from Open-Meteo API. Returns structured dict.
- `src/icons.py`: Helper to draw weather icons using `weathericons-regular-webfont.ttf`.
- `lib/waveshare_epd/`: Drivers for the specific e-ink hardware.
- `fonts/`: Contains `.ttf` files for UI text and icons.

## Key Configuration
- **Locations**: Configured in `src/main.py` (List of dicts with `lat`/`lon`).
- **Update Interval**: Configured in `src/main.py` (Default 60 mins).
- **Fonts/Icons**: Paths defined in `src/display_service.py` relative to project root.

## Development Notes
- **Mock Mode**: `display_service.py` includes a mock EPD class if drivers fail (for local testing on non-Pi devices).
- **Service Management**:
    - Service file: `weather-display.service`
    - Logs: `sudo journalctl -u weather-display.service -f`
    - Restart: `sudo systemctl restart weather-display.service`

## Display rendering
- The display is rendered in a 250x122 pixel image.
- Use the correct font sizes and positions.
- Make best use of the display space.
- The image is then sent to the e-ink display.

## API Data Structure
`WeatherService.get_current_weather` returns:
```python
{
    "current": {
        "temperature": float,
        "apparent_temperature": float,
        "windspeed": float,
        "weathercode": int,
        "is_day": int (0/1),
        ...
    },
    "daily": {
        "uv_index_max": [float],
        "precipitation_probability_max": [int],
        "sunset": [str], # ISO format
        ...
    }
}
```
