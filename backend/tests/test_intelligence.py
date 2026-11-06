from app.intelligence.risk import assess_compound_risk, heat_index_celsius


def test_heat_index_increases_in_hot_humid_conditions():
    assert heat_index_celsius(35, 75) > 35


def test_compound_risk_explains_heat_and_pollution():
    result = assess_compound_risk({
        "temperature_c": 40, "relative_humidity_pct": 75, "nighttime_temperature_c": 27,
        "consecutive_hot_days": 4, "pm25_ugm3": 45, "us_aqi": 160,
    })
    assert result.level in {"High", "Severe"}
    assert any(item["factor"] == "PM2.5" for item in result.contributors)
    assert result.completeness >= 80


def test_missing_data_is_reflected_in_completeness():
    result = assess_compound_risk({"temperature_c": 30})
    assert result.completeness < 50
    assert result.uncertainty == "Higher uncertainty"
