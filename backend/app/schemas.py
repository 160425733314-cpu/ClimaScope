from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Location(BaseModel):
    name: str
    country: str = ""
    admin1: str = ""
    latitude: float
    longitude: float
    timezone: str = "auto"


class ScenarioInput(BaseModel):
    temperature_delta_c: float = Field(0, ge=-10, le=10)
    humidity_delta_pct: float = Field(0, ge=-40, le=40)
    rainfall_multiplier: float = Field(1, ge=0, le=5)
    hot_days_delta: int = Field(0, ge=-7, le=14)
    pm25_delta_ugm3: float = Field(0, ge=-100, le=200)
    tree_cover_intervention: bool = False
    reflective_roof_intervention: bool = False


class Observation(BaseModel):
    temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    heat_index_c: float | None = None
    nighttime_temperature_c: float | None = None
    consecutive_hot_days: int = 0
    precipitation_mm: float | None = None
    pm25_ugm3: float | None = None
    pm10_ugm3: float | None = None
    nitrogen_dioxide_ugm3: float | None = None
    sulphur_dioxide_ugm3: float | None = None
    ozone_ugm3: float | None = None
    us_aqi: float | None = None


class RiskResponse(BaseModel):
    score: float
    level: str
    headline: str
    contributors: list[dict[str, Any]]
    uncertainty: str
    completeness: float
    methodology: str


class ScenarioResponse(BaseModel):
    baseline: RiskResponse
    scenario: RiskResponse
    delta: float
    assumptions: list[str]


class DashboardResponse(BaseModel):
    location: Location
    current: dict[str, Any]
    daily: list[dict[str, Any]]
    hourly: list[dict[str, Any]]
    air_quality: dict[str, Any]
    risk: RiskResponse
    alerts: list[dict[str, Any]]
    meta: dict[str, Any]


class CitySnapshot(BaseModel):
    location: Location
    temperature_c: float | None
    us_aqi: float | None
    risk: RiskResponse
    active_alerts: int
    freshness: datetime | None = None
