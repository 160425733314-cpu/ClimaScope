# CliMAScope

CliMAScope is an explainable urban climate intelligence and decision-support platform. It combines live Open-Meteo weather and air-quality model feeds with transparent compound-risk screening and interactive what-if sensitivity analysis.

## Architecture

```
frontend/  React + Vite + TypeScript + Recharts + Leaflet
backend/   FastAPI + Pydantic + httpx + SQLite-ready event layer
legacy/    Original Streamlit application preserved unchanged
```

The compound-risk engine is intentionally a screening heuristic rather than a calibrated probability or official warning. It reports each contributing measurement, points, data completeness and uncertainty. Rainfall indicators are screening signals and do not establish flood probability.

## Run locally

Requirements: Python 3.10+, Node.js 18+.

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
./run_backend.sh
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The API health check is http://localhost:8000/api/health and interactive API documentation is available at http://localhost:8000/docs.

## Validation

```bash
cd backend && pytest
cd frontend && npm run build
```

## Data and limitations

- Weather and air quality come from Open-Meteo forecast/model-grid APIs.
- The map displays the selected city-point model grid, not invented street-level measurements.
- US AQI is shown as supplied by Open-Meteo; it is not Indian National AQI.
- The current release exposes live dashboard, risk explainability, what-if simulator and transparency views. Navigation items without a dedicated analysis page return to the command-centre data context rather than presenting fake results.
- Historical and ML workflows from the original application remain available in `legacy/CliMAScope_Advanced.py` while their modular successors are developed.
