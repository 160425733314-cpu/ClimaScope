from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskResult:
    score: float
    level: str
    headline: str
    contributors: list[dict[str, Any]]
    uncertainty: str
    completeness: float
    methodology: str = "CliMAScope compound-risk heuristic v1"


def heat_index_celsius(temperature_c: float, humidity: float) -> float:
    """NOAA Rothfusz approximation, used only for hot/humid conditions."""
    temp_f = temperature_c * 9 / 5 + 32
    rh = max(0.0, min(100.0, humidity))
    if temp_f < 80 or rh < 40:
        return temperature_c
    hi = (
        -42.379
        + 2.04901523 * temp_f
        + 10.14333127 * rh
        - 0.22475541 * temp_f * rh
        - 0.00683783 * temp_f**2
        - 0.05481717 * rh**2
        + 0.00122874 * temp_f**2 * rh
        + 0.00085282 * temp_f * rh**2
        - 0.00000199 * temp_f**2 * rh**2
    )
    return (hi - 32) * 5 / 9


def _level(score: float) -> str:
    if score >= 75:
        return "Severe"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Moderate"
    return "Low"


def assess_compound_risk(observation: dict[str, Any]) -> RiskResult:
    """Transparent screening score; it is not a calibrated probability."""
    score = 0.0
    contributors: list[dict[str, Any]] = []

    def add(name: str, points: float, measurement: str, explanation: str) -> None:
        nonlocal score
        if points <= 0:
            return
        score += points
        contributors.append(
            {"factor": name, "points": round(points, 1), "measurement": measurement, "explanation": explanation}
        )

    temp = observation.get("temperature_c")
    humidity = observation.get("relative_humidity_pct")
    heat_index = observation.get("heat_index_c")
    if heat_index is None and temp is not None and humidity is not None:
        heat_index = heat_index_celsius(float(temp), float(humidity))
    if temp is not None:
        add("Daytime heat", max(0.0, min(30.0, (float(temp) - 32) * 3)), f"{float(temp):.1f} °C",
            "Temperature above 32 °C increases thermal stress.")
    if humidity is not None and float(humidity) >= 60:
        add("Humidity", min(12.0, (float(humidity) - 60) * 0.3), f"{float(humidity):.0f} %",
            "Elevated humidity reduces evaporative cooling.")
    if heat_index is not None and float(heat_index) >= 38:
        add("Heat index", min(25.0, (float(heat_index) - 38) * 2.5), f"{float(heat_index):.1f} °C",
            "Feels-like heat reaches a heat-stress range.")
    nighttime = observation.get("nighttime_temperature_c")
    if nighttime is not None and float(nighttime) >= 25:
        add("Persistent nighttime heat", min(15.0, (float(nighttime) - 25) * 2.5), f"{float(nighttime):.1f} °C",
            "Warm nights reduce overnight recovery.")
    hot_days = observation.get("consecutive_hot_days", 0)
    if hot_days and int(hot_days) >= 2:
        add("Persistence", min(15.0, (int(hot_days) - 1) * 3), f"{int(hot_days)} days",
            "Multi-day heat can compound exposure and recovery impacts.")
    pm25 = observation.get("pm25_ugm3")
    if pm25 is not None and float(pm25) >= 15:
        add("PM2.5", min(20.0, (float(pm25) - 15) * 0.45), f"{float(pm25):.1f} µg/m³",
            "Fine particulate exposure adds respiratory stress alongside heat.")
    aqi = observation.get("us_aqi")
    if aqi is not None and float(aqi) >= 101:
        add("Air quality", min(20.0, (float(aqi) - 100) * 0.2), f"US AQI {float(aqi):.0f}",
            "AQI above 100 indicates elevated pollution exposure.")
    rain = observation.get("precipitation_mm")
    if rain is not None and float(rain) >= 35:
        add("Rainfall screening signal", min(15.0, (float(rain) - 35) * 0.12), f"{float(rain):.1f} mm",
            "Heavy rainfall can create an exposure signal; this is not a flood forecast.")

    score = min(100.0, score)
    data_fields = [
        "temperature_c", "relative_humidity_pct", "nighttime_temperature_c",
        "pm25_ugm3", "us_aqi", "precipitation_mm",
    ]
    completeness = round(sum(observation.get(field) is not None for field in data_fields) / len(data_fields) * 100, 1)
    uncertainty = "Lower uncertainty" if completeness >= 80 else "Moderate uncertainty" if completeness >= 50 else "Higher uncertainty"
    level = _level(score)
    headline = "Elevated compound heat and pollution stress detected." if any(
        item["factor"] in {"Daytime heat", "Heat index", "PM2.5", "Air quality"} for item in contributors
    ) and level in {"High", "Severe"} else f"{level} compound climate risk screening signal."
    return RiskResult(score=round(score, 1), level=level, headline=headline,
                      contributors=contributors, uncertainty=uncertainty, completeness=completeness)
