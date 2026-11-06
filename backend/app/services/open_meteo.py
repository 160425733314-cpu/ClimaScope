from __future__ import annotations

import time
from typing import Any

import httpx

from ..schemas import Location


class DataSourceError(RuntimeError):
    pass


class OpenMeteoService:
    forecast_url = "https://api.open-meteo.com/v1/forecast"
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}

    async def _get(self, url: str, params: dict[str, Any], ttl: int = 900) -> dict[str, Any]:
        key = url + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
        cached = self._cache.get(key)
        if cached and time.time() - cached[0] < ttl:
            return cached[1]
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DataSourceError(f"Open-Meteo request failed: {exc}") from exc
        if payload.get("error"):
            raise DataSourceError(payload.get("reason", "Open-Meteo returned an error"))
        self._cache[key] = (time.time(), payload)
        return payload

    async def geocode(self, name: str) -> Location:
        payload = await self._get(self.geocode_url, {"name": name, "count": 1, "language": "en", "format": "json"}, 3600)
        results = payload.get("results", [])
        if not results:
            raise DataSourceError(f"No location found for '{name}'")
        result = results[0]
        return Location(name=result["name"], country=result.get("country", ""), admin1=result.get("admin1", ""),
                        latitude=result["latitude"], longitude=result["longitude"], timezone=result.get("timezone", "auto"))

    async def forecast(self, location: Location) -> dict[str, Any]:
        return await self._get(self.forecast_url, {
            "latitude": location.latitude, "longitude": location.longitude, "timezone": location.timezone,
            "forecast_days": 7,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
        })

    async def air_quality(self, location: Location) -> dict[str, Any]:
        return await self._get(self.air_url, {
            "latitude": location.latitude, "longitude": location.longitude, "timezone": location.timezone,
            "forecast_days": 7,
            "current": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi",
            "hourly": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi",
        }, 1800)
