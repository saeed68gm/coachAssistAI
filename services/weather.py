from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class WindForcast:
    location: str
    wind_speed_mps: float
    wind_gust_mps: float | None
    description: str
    temperature_celsius: float | None = None


class OpenMeteoWeatherService:
    """Weather client using the Open-Meteo API (no API key required).

    This service will first geocode the free-form `location` string using
    Open-Meteo's geocoding endpoint, then call the forecast API to retrieve
    the current weather (temperature and wind speed). Gusts are not always
    provided by the simple current weather response, so `wind_gust_mps` may
    be None.
    """

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def get_wind_forecast(self, location: str) -> WindForcast:
        # 1) Geocode the location
        # Try several sanitized forms of the location to improve geocoding
        candidates = [
            location,
            location.split("(")[0].strip(),
            location.split("-")[0].strip(),
            location.split(",")[0].strip(),
        ]
        place = None
        for candidate in candidates:
            params = {"name": candidate, "count": 1}
            r = self.session.get(self.GEOCODING_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            results = data.get("results") or []
            if results:
                place = results[0]
                break

        if not place:
            # fallback: return empty/default forecast
            return WindForcast(
                location=location,
                wind_speed_mps=0.0,
                wind_gust_mps=None,
                description="Unknown",
                temperature_celsius=None,
            )
        lat = place.get("latitude")
        lon = place.get("longitude")
        name = place.get("name") or location

        # 2) Query current weather
        fp = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "timezone": "auto",
        }
        fr = self.session.get(self.FORECAST_URL, params=fp, timeout=10)
        fr.raise_for_status()
        payload = fr.json()
        current = payload.get("current_weather") or {}

        temp = current.get("temperature")
        wind_speed = current.get("windspeed")
        # Open-Meteo current_weather doesn't always include gust; leave None
        wind_gust = None
        weathercode = current.get("weathercode")

        description = self._describe_weathercode(weathercode)

        return WindForcast(
            location=name,
            wind_speed_mps=wind_speed if wind_speed is not None else 0.0,
            wind_gust_mps=wind_gust,
            description=description,
            temperature_celsius=temp,
        )

    @staticmethod
    def _describe_weathercode(code: int | None) -> str:
        if code is None:
            return "No description available"
        # Simplified mapping of Open-Meteo weather codes
        if code == 0:
            return "Clear"
        if code in (1, 2, 3):
            return "Mainly clear / partly cloudy"
        if code in (45, 48):
            return "Fog"
        if 51 <= code <= 67:
            return "Drizzle / Rain"
        if 71 <= code <= 77:
            return "Snow / Ice"
        if 80 <= code <= 82:
            return "Rain showers"
        if 95 <= code <= 99:
            return "Thunderstorm"
        return f"Weather code {code}"
