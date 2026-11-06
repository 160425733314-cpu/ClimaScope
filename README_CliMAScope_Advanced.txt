CliMAScope — Advanced Weather Risk & Air Quality Intelligence

FILES
- CliMAScope_Advanced.py: complete Streamlit application
- requirements_CliMAScope_Advanced.txt: Python dependencies

RUN
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:
   pip install -r requirements_CliMAScope_Advanced.txt
4. Start the app:
   python -m streamlit run CliMAScope_Advanced.py

DATA SOURCES
- Open-Meteo Forecast API: weather forecast, current conditions and hourly/daily variables.
- Open-Meteo Historical Archive API: historical hourly weather used for training the experimental Random Forest.
- Open-Meteo Air Quality API: modelled PM2.5, PM10, NO2, SO2, O3 and AQI forecast.
- OpenAQ API v3: optional station-level measurement cross-check; requires a personal API key entered in the app's OpenAQ expander. The key is not hard-coded.

FEATURES
- Existing location weather dashboard, 7-day forecast, historical weather and required 7x24 thermal simulation.
- Five pollutant cards, US AQI, AQI heatmap, pollutant trends, general health guidance and temperature/pollution correlation.
- Threshold-based heatwave, cold-wave, heavy-rain and potential flood-risk indicators.
- Composite city risk score and robust-z-score temperature anomaly detection.
- Heat-index approximation and humidity/heat-index heatmap.
- Multi-city map and risk/alerts table (up to 10 cities).
- Experimental Random Forest 7-day hourly temperature estimate with chronological holdout MAE.

IMPORTANT LIMITATIONS
- This is an educational prototype, not an official warning system or medical device.
- Weather and air-quality API values are model estimates; OpenAQ values are station measurements and can vary in age/coverage.
- Heatwave/cold-wave/rain/flood thresholds are transparent prototype screening rules, not official regional warning criteria. Flood risk cannot be reliably inferred from rainfall alone; local drainage, river levels, soil saturation and terrain are not modelled.
- City risk score is a heuristic index, not a calibrated probability.
- Health guidance is general and not a substitute for local public-health advice.
- The ML forecast is an experimental Random Forest using calendar/time features and recent historical temperature. It is not a production-grade weather model. Compare it against the Open-Meteo forecast.
- API fallback and CSV export should be tested in the target environment before presenting them as passed.
- OpenAQ access requires an API key. Open-Meteo features work without one.

API DOCUMENTATION
- https://open-meteo.com/en/docs
- https://open-meteo.com/en/docs/air-quality-api
- https://docs.openaq.org/
