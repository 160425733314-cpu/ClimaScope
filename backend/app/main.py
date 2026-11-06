from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .intelligence.risk import assess_compound_risk, heat_index_celsius
from .schemas import DashboardResponse, Observation, RiskResponse, ScenarioInput, ScenarioResponse
from .services.open_meteo import DataSourceError, OpenMeteoService

app = FastAPI(title="CliMAScope API", version="1.0.0", description="Explainable urban climate intelligence API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
service = OpenMeteoService()


def risk_response(observation: dict[str, Any]) -> RiskResponse:
    result = assess_compound_risk(observation)
    return RiskResponse(**result.__dict__)


def _alerts(daily: dict[str, Any], air_current: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    dates = daily.get("time", [])
    for index, date in enumerate(dates):
        max_temp = (daily.get("temperature_2m_max") or [None])[index]
        min_temp = (daily.get("temperature_2m_min") or [None])[index]
        rain = (daily.get("precipitation_sum") or [0])[index] or 0
        probability = (daily.get("precipitation_probability_max") or [0])[index] or 0
        if max_temp is not None and max_temp >= 40:
            alerts.append({"event_type": "Heatwave screening", "severity": "High", "date": date, "trigger": f"Maximum {max_temp:.1f} °C", "precaution": "Reduce strenuous outdoor exposure and hydrate."})
        if min_temp is not None and min_temp >= 25:
            alerts.append({"event_type": "Warm-night screening", "severity": "Moderate", "date": date, "trigger": f"Minimum {min_temp:.1f} °C", "precaution": "Plan for reduced overnight heat recovery."})
        if rain >= 64.5 or (rain >= 35 and probability >= 70):
            alerts.append({"event_type": "Heavy rainfall screening", "severity": "High", "date": date, "trigger": f"{rain:.1f} mm; {probability:.0f}% probability", "precaution": "Check local official rainfall and drainage advisories."})
    aqi = air_current.get("us_aqi")
    if aqi is not None and aqi >= 101:
        alerts.append({"event_type": "Air pollution screening", "severity": "High" if aqi >= 151 else "Moderate", "date": datetime.now(timezone.utc).date().isoformat(), "trigger": f"US AQI {aqi:.0f}", "precaution": "Sensitive groups should reduce prolonged outdoor exertion."})
    return alerts


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "climascope-api", "version": app.version}


@app.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard(city: str = Query("Hyderabad", min_length=1, max_length=80)) -> DashboardResponse:
    try:
        location = await service.geocode(city)
        weather, air = await service.forecast(location), await service.air_quality(location)
    except DataSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    current = weather.get("current", {})
    air_current = air.get("current", {})
    daily = weather.get("daily", {})
    hourly = weather.get("hourly", {})
    observation = {
        "temperature_c": current.get("temperature_2m"),
        "relative_humidity_pct": current.get("relative_humidity_2m"),
        "nighttime_temperature_c": (daily.get("temperature_2m_min") or [None])[0],
        "precipitation_mm": (daily.get("precipitation_sum") or [None])[0],
        "pm25_ugm3": air_current.get("pm2_5"),
        "pm10_ugm3": air_current.get("pm10"),
        "nitrogen_dioxide_ugm3": air_current.get("nitrogen_dioxide"),
        "sulphur_dioxide_ugm3": air_current.get("sulphur_dioxide"),
        "ozone_ugm3": air_current.get("ozone"),
        "us_aqi": air_current.get("us_aqi"),
    }
    if observation["temperature_c"] is not None and observation["relative_humidity_pct"] is not None:
        observation["heat_index_c"] = heat_index_celsius(observation["temperature_c"], observation["relative_humidity_pct"])
    days = [{"date": date, "max_c": daily.get("temperature_2m_max", [])[i], "min_c": daily.get("temperature_2m_min", [])[i],
             "rain_mm": daily.get("precipitation_sum", [])[i], "rain_probability_pct": daily.get("precipitation_probability_max", [])[i]}
            for i, date in enumerate(daily.get("time", []))]
    hours = [{"time": time, "temperature_c": value, "humidity_pct": (hourly.get("relative_humidity_2m") or [None] * len(hourly.get("time", [])))[i],
              "rain_probability_pct": (hourly.get("precipitation_probability") or [None] * len(hourly.get("time", [])))[i]}
             for i, (time, value) in enumerate(zip(hourly.get("time", []), hourly.get("temperature_2m", [])))]
    alerts = _alerts(daily, air_current)
    return DashboardResponse(location=location, current={**current, "heat_index_c": observation.get("heat_index_c")},
                             daily=days, hourly=hours, air_quality={**air_current, "hourly": air.get("hourly", {})},
                             risk=risk_response(observation), alerts=alerts,
                             meta={"sources": ["Open-Meteo forecast", "Open-Meteo air-quality"], "resolution": "city-point model grid", "updated_at": datetime.now(timezone.utc).isoformat(),
                                   "limitations": ["Screening heuristics are not official warnings or calibrated probabilities.", "Open-Meteo values are model estimates, not local station observations."]})


@app.post("/api/risk/assess", response_model=RiskResponse)
async def assess(observation: Observation) -> RiskResponse:
    return risk_response(observation.model_dump())


@app.post("/api/risk/scenario", response_model=ScenarioResponse)
async def scenario(observation: Observation, changes: ScenarioInput) -> ScenarioResponse:
    baseline = observation.model_dump()
    modified = {**baseline}
    for field in ("temperature_c", "nighttime_temperature_c"):
        if modified[field] is not None:
            modified[field] += changes.temperature_delta_c
    if modified["relative_humidity_pct"] is not None:
        modified["relative_humidity_pct"] += changes.humidity_delta_pct
    if modified["precipitation_mm"] is not None:
        modified["precipitation_mm"] *= changes.rainfall_multiplier
    if modified["pm25_ugm3"] is not None:
        modified["pm25_ugm3"] += changes.pm25_delta_ugm3
    modified["consecutive_hot_days"] += changes.hot_days_delta
    assumptions = ["Temperature, humidity, rainfall, duration and PM2.5 changes are sensitivity assumptions, not physical forecasts."]
    if changes.tree_cover_intervention:
        modified["temperature_c"] = (modified["temperature_c"] or 0) - 0.8
        assumptions.append("Tree-cover intervention represented as a hypothetical 0.8 °C local cooling sensitivity.")
    if changes.reflective_roof_intervention:
        modified["temperature_c"] = (modified["temperature_c"] or 0) - 0.5
        assumptions.append("Reflective-roof intervention represented as a hypothetical 0.5 °C local cooling sensitivity.")
    baseline_result, scenario_result = risk_response(baseline), risk_response(modified)
    return ScenarioResponse(baseline=baseline_result, scenario=scenario_result, delta=round(scenario_result.score - baseline_result.score, 1), assumptions=assumptions)
