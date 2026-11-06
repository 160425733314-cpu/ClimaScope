import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta

st.set_page_config(page_title="CliMAScope", page_icon="🌍", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f0f5f7; color: #263840; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1600px; }
header[data-testid="stHeader"] { background: transparent; }
.brand {font-size: 2rem; letter-spacing:-1.2px; color:#31434a; font-weight:300; margin:0; line-height:1.1}
.brand strong {font-weight:800;color:#20343b}
.brand .dots {color:#24959b;letter-spacing:-5px;margin:0 10px 0 5px}
.subtle {color:#71838b;font-size:.85rem}
.panel {background:white;border:1px solid #dce6e9;border-radius:14px;padding:18px 20px;box-shadow:0 2px 10px rgba(30,55,65,.045);margin-bottom:12px}
.kpi {background:#fff;border:1px solid #dce6e9;border-radius:12px;padding:15px 16px;min-height:100px}
.kpi-label {font-size:.82rem;color:#70838a;margin-bottom:8px}
.kpi-value {font-size:1.65rem;font-weight:750;color:#253840;line-height:1.15}
.kpi-note {font-size:.75rem;color:#83949a;margin-top:5px}
.stTabs [data-baseweb="tab-list"] {gap:8px; border-bottom:1px solid #dce6e9;}
.stTabs [data-baseweb="tab"] {height:48px; padding:0 18px; background:#e7eff1; border-radius:10px 10px 0 0; font-weight:700;}
.stTabs [aria-selected="true"] {background:#168b92 !important; color:white !important;}
.section-title {font-size:1.04rem;font-weight:750;color:#293d45;margin:0 0 10px 0}
div[data-testid="stMetric"] {background:white;border:1px solid #dce6e9;border-radius:12px;padding:12px 14px}
.stButton>button {border-radius:9px;border:1px solid #d5e2e5;background:#168b92;color:white;font-weight:650}
.stButton>button:hover {background:#10777d;color:white;border-color:#10777d}
div[data-testid="stTextInput"] input {border-radius:9px}
footer {visibility:hidden}
</style>
""", unsafe_allow_html=True)

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"

@st.cache_data(ttl=3600, show_spinner=False)
def geocode_city(name):
    r = requests.get(GEOCODE, params={"name": name, "count": 8, "language": "en", "format": "json"}, timeout=15)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise ValueError(f"No location found for '{name}'. Try a nearby major city.")
    # Prefer exact-ish city name match, then population
    results.sort(key=lambda x: (x.get("name","").lower() != name.lower(), -(x.get("population") or 0)))
    return results[0]

@st.cache_data(ttl=3600, show_spinner=False)
def get_historical_weather(lat, lon, timezone, start_date, end_date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": timezone or "auto",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum",
    }
    r = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()
    if payload.get("error"):
        raise ValueError(payload.get("reason", "Historical weather data is unavailable."))
    return payload


@st.cache_data(ttl=900, show_spinner=False)
def get_weather(lat, lon, timezone):
    params = {
        "latitude": lat, "longitude": lon, "timezone": timezone or "auto",
        "forecast_days": 7,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunrise,sunset"
    }
    r = requests.get(FORECAST, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def weather_label(code):
    codes = {
        0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
        45:"Fog",48:"Depositing rime fog",51:"Light drizzle",53:"Drizzle",55:"Dense drizzle",
        56:"Freezing drizzle",57:"Heavy freezing drizzle",61:"Light rain",63:"Rain",65:"Heavy rain",
        66:"Freezing rain",67:"Heavy freezing rain",71:"Light snow",73:"Snow",75:"Heavy snow",
        77:"Snow grains",80:"Rain showers",81:"Rain showers",82:"Heavy rain showers",
        85:"Snow showers",86:"Heavy snow showers",95:"Thunderstorm",96:"Thunderstorm with hail",99:"Thunderstorm with hail"
    }
    return codes.get(int(code), "Conditions unavailable")

def weather_emoji(code, is_day=1):
    code = int(code)
    if code == 0: return "☀️" if is_day else "🌙"
    if code in (1,2): return "🌤️"
    if code in (3,45,48): return "☁️"
    if code in (51,53,55,56,57,61,63,65,66,67,80,81,82): return "🌧️"
    if code in (71,73,75,77,85,86): return "🌨️"
    if code >= 95: return "⛈️"
    return "🌡️"

st.markdown('<div class="brand">CliMA<span class="dots">●●<br>●●</span><strong>Scope</strong></div>', unsafe_allow_html=True)
st.caption("Weather intelligence dashboard · live conditions · air quality · risk monitoring")

with st.container():
    c1, c2, c3 = st.columns([5, 1.5, 1.1])
    with c1:
        city_input = st.text_input("Search location", value=st.session_state.get("city_text", "Hyderabad"), placeholder="City, region or country", label_visibility="collapsed")
    with c2:
        search_clicked = st.button("Search location", use_container_width=True)
    with c3:
        if st.button("Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

if "location" not in st.session_state or search_clicked:
    try:
        with st.spinner("Finding location…"):
            loc = geocode_city(city_input.strip() or "Hyderabad")
        st.session_state.location = loc
        st.session_state.city_text = city_input.strip() or "Hyderabad"
    except Exception as e:
        st.error(f"Could not find that location: {e}")
        if "location" not in st.session_state:
            st.stop()

loc = st.session_state.location
city = loc.get("name", "Selected location")
admin = loc.get("admin1", "")
country = loc.get("country", "")
lat, lon = float(loc["latitude"]), float(loc["longitude"])
try:
    with st.spinner(f"Loading forecast for {city}…"):
        weather = get_weather(lat, lon, loc.get("timezone", "auto"))
except Exception as e:
    st.error(f"Weather data could not be loaded. Check your internet connection and try Refresh data. Details: {e}")
    st.stop()

cur = weather.get("current", {})
hourly = weather.get("hourly", {})
daily = weather.get("daily", {})
unit = weather.get("current_units", {})
hour_df = pd.DataFrame({
    "time": pd.to_datetime(hourly.get("time", [])),
    "Temperature (°C)": hourly.get("temperature_2m", []),
    "Humidity (%)": hourly.get("relative_humidity_2m", []),
    "Rain chance (%)": hourly.get("precipitation_probability", []),
})
day_df = pd.DataFrame({
    "date": pd.to_datetime(daily.get("time", [])),
    "Maximum (°C)": daily.get("temperature_2m_max", []),
    "Minimum (°C)": daily.get("temperature_2m_min", []),
    "Rain chance (%)": daily.get("precipitation_probability_max", [0]*len(daily.get("time", []))),
    "Code": daily.get("weather_code", [0]*len(daily.get("time", []))),
})
today_min = float(day_df.iloc[0]["Minimum (°C)"]) if len(day_df) else float("nan")
today_max = float(day_df.iloc[0]["Maximum (°C)"]) if len(day_df) else float("nan")
location_name = ", ".join(x for x in [city, admin, country] if x)

overview_tab, history_tab, simulation_tab, air_tab, monitor_tab = st.tabs([
    "Overview", "Historical", "Simulation", "Air Quality & Risk", "Live Monitor"
])

with overview_tab:
    left, right = st.columns([1.55, 1], gap="medium")
    with left:
        st.markdown('<div class="panel"><div class="section-title">Location</div><div class="subtle">Geographic context · click the map controls to zoom</div></div>', unsafe_allow_html=True)
        map_df = pd.DataFrame({"City":[city], "Latitude":[lat], "Longitude":[lon], "Temperature (°C)":[float(cur.get("temperature_2m", 0))]})
        fig_map = go.Figure()
        fig_map.add_trace(go.Scattergeo(
            lon=[lon],
            lat=[lat],
            mode="markers+text",
            text=[city],
            textposition="top center",
            customdata=[[cur.get("temperature_2m", "—")]],
            marker=dict(size=14, color="#168b92", line=dict(width=2, color="white")),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Temperature: %{customdata[0]} °C<br>"
                "Latitude: %{lat:.2f}<br>"
                "Longitude: %{lon:.2f}<extra></extra>"
            )
        ))
        fig_map.update_geos(
            projection_type="natural earth", showland=True, landcolor="#e5edef",
            showocean=True, oceancolor="#f7fafb", showcountries=True, countrycolor="#cbd8dc",
            showcoastlines=True, coastlinecolor="#b7c8cd", showlakes=True, lakecolor="#f7fafb",
            lataxis_showgrid=True, lonaxis_showgrid=True,
            center=dict(lat=lat, lon=lon), projection_scale=3.5
        )
        fig_map.update_layout(height=390, margin=dict(l=0,r=0,t=4,b=0), paper_bgcolor="white",
                              geo=dict(bgcolor="white"), showlegend=False)
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": True, "scrollZoom": True})
        st.caption(f"Selected coordinates: {lat:.3f}°, {lon:.3f}° · Map shows location, not a global temperature raster.")

    with right:
        st.markdown(f'<div class="panel"><div style="display:flex;justify-content:space-between;gap:8px"><div class="section-title">Current conditions</div><span class="subtle">Open-Meteo forecast</span></div><h3 style="margin:4px 0 8px;color:#263a42">{location_name}</h3></div>', unsafe_allow_html=True)
        temp = cur.get("temperature_2m")
        code = cur.get("weather_code", 0)
        emoji = weather_emoji(code, cur.get("is_day", 1))
        st.markdown(f'<div class="kpi" style="margin-bottom:10px"><div style="font-size:2.6rem;line-height:1.2">{emoji} <span style="font-size:2.8rem;font-weight:800;color:#263a42">{temp if temp is not None else "—"}°C</span></div><div style="font-size:1rem;font-weight:600;margin-top:4px">{weather_label(code)}</div><div class="subtle">Feels like {cur.get("apparent_temperature","—")}°C</div></div>', unsafe_allow_html=True)
        k1,k2=st.columns(2)
        with k1:
            st.markdown(f'<div class="kpi"><div class="kpi-label">Humidity</div><div class="kpi-value">{cur.get("relative_humidity_2m","—")}%</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kpi" style="margin-top:10px"><div class="kpi-label">Wind speed</div><div class="kpi-value">{cur.get("wind_speed_10m","—")} <span style="font-size:1rem">km/h</span></div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="kpi"><div class="kpi-label">Today’s low / high</div><div class="kpi-value">{today_min:.0f}° / {today_max:.0f}°</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kpi" style="margin-top:10px"><div class="kpi-label">Rain chance today</div><div class="kpi-value">{day_df.iloc[0]["Rain chance (%)"]:.0f}%</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="subtle" style="margin-top:12px">Forecast-model values; not direct observations from a local weather station.</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel"><div class="section-title">7-day forecast</div><div class="subtle">Daily minimum and maximum temperature · local dates</div></div>', unsafe_allow_html=True)
    if not day_df.empty:
        fig_daily = go.Figure()
        xlabels = day_df["date"].dt.strftime("%a · %d %b")
        for i,row in day_df.iterrows():
            fig_daily.add_trace(go.Scatter(
                x=[xlabels.iloc[i], xlabels.iloc[i]], y=[row["Minimum (°C)"], row["Maximum (°C)"]],
                mode="lines+markers+text", line=dict(color="#279da0", width=7),
                marker=dict(size=8, color=["#6aa6d8", "#e8a14a"]), text=[f'{row["Minimum (°C)"]:.0f}°',f'{row["Maximum (°C)"]:.0f}°'],
                textposition=["bottom center","top center"], textfont=dict(size=11,color="#40555d"),
                hovertemplate=f'{xlabels.iloc[i]}<br>Low: {row["Minimum (°C)"]:.1f}°C<br>High: {row["Maximum (°C)"]:.1f}°C<extra></extra>', showlegend=False
            ))
        fig_daily.update_layout(height=230, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white",
                                xaxis=dict(showgrid=False, tickfont=dict(color="#667b82")), yaxis=dict(title="°C",gridcolor="#edf2f3",zeroline=False))
        st.plotly_chart(fig_daily, use_container_width=True)
        with st.expander("View forecast as a table"):
            show = day_df.copy()
            show["date"] = show["date"].dt.strftime("%A, %d %B")
            show["Conditions"] = show["Code"].map(weather_label)
            st.dataframe(show[["date","Conditions","Minimum (°C)","Maximum (°C)","Rain chance (%)"]].rename(columns={"date":"Date"}), use_container_width=True, hide_index=True)

    col_heat, col_dist = st.columns([1.5,1], gap="medium")
    with col_heat:
        st.markdown('<div class="panel"><div class="section-title">Hourly temperature heatmap</div><div class="subtle">Next 7 days · local time · hover for exact values</div></div>', unsafe_allow_html=True)
        if not hour_df.empty:
            heat = hour_df.copy()
            heat["Day"] = heat["time"].dt.strftime("%a %d %b")
            heat["Hour"] = heat["time"].dt.strftime("%H:%M")
            pivot = heat.pivot_table(index="Day", columns="Hour", values="Temperature (°C)", aggfunc="mean")
            # Keep hours in chronological order and make heatmap readable on desktop.
            fig_heat = px.imshow(pivot, aspect="auto", color_continuous_scale=["#2d4fa2","#368fd0","#41c5c4","#62bd79","#e7d64b","#f39b3d","#d84a3f"],
                                 labels=dict(x="Local hour", y="Day", color="°C"))
            fig_heat.update_layout(height=300, margin=dict(l=0,r=0,t=6,b=0), paper_bgcolor="white",
                                   xaxis=dict(tickfont=dict(size=9,color="#60757d"), tickangle=0, nticks=12),
                                   yaxis=dict(tickfont=dict(size=10,color="#60757d")))
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Hourly forecast is unavailable for this location.")

    with col_dist:
        st.markdown('<div class="panel"><div class="section-title">Temperature distribution</div><div class="subtle">Next 7 days · hourly forecast values</div></div>', unsafe_allow_html=True)
        vals = hour_df["Temperature (°C)"].dropna() if not hour_df.empty else pd.Series(dtype=float)
        if len(vals):
            fig_hist = px.histogram(x=vals, nbins=14, labels={"x":"Temperature (°C)","y":"Hours"},
                                    color_discrete_sequence=["#279da0"])
            fig_hist.update_layout(height=300, margin=dict(l=8,r=8,t=6,b=8), paper_bgcolor="white", plot_bgcolor="white",
                                   xaxis=dict(gridcolor="#edf2f3"),yaxis=dict(gridcolor="#edf2f3"))
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Temperature distribution is unavailable.")

    st.markdown('<div class="panel"><div class="section-title">Hourly temperature trend</div><div class="subtle">Explore daily warming and cooling across the forecast period.</div></div>', unsafe_allow_html=True)
    if not hour_df.empty:
        fig_line = px.line(hour_df, x="time", y="Temperature (°C)", markers=False, color_discrete_sequence=["#168b92"])
        fig_line.update_traces(line_width=2.5, hovertemplate="%{x|%a %d %b, %H:%M}<br>%{y:.1f}°C<extra></extra>")
        fig_line.update_layout(height=260, margin=dict(l=10,r=10,t=5,b=10), paper_bgcolor="white", plot_bgcolor="white",
                               xaxis_title="",yaxis_title="Temperature (°C)",xaxis=dict(gridcolor="#edf2f3"),
                               yaxis=dict(gridcolor="#edf2f3"))
        st.plotly_chart(fig_line, use_container_width=True)

with history_tab:
    st.markdown('<div class="panel"><div class="section-title">Historical weather</div><div class="subtle">Explore past temperature, humidity and precipitation. Historical values are reanalysis estimates, not guaranteed station observations.</div></div>', unsafe_allow_html=True)

    today_local = date.today()
    default_end = today_local - timedelta(days=5)
    default_start = default_end - timedelta(days=13)
    hist_col1, hist_col2, hist_col3 = st.columns([1, 1, 1.1])
    with hist_col1:
        history_start = st.date_input(
            "Start date",
            value=default_start,
            min_value=date(1940, 1, 1),
            max_value=default_end,
            key="history_start_date",
        )
    with hist_col2:
        history_end = st.date_input(
            "End date",
            value=default_end,
            min_value=date(1940, 1, 1),
            max_value=default_end,
            key="history_end_date",
        )
    with hist_col3:
        st.write("")
        st.write("")
        load_history = st.button("Load historical data", use_container_width=True)

    if load_history or "history_payload" not in st.session_state or st.session_state.get("history_location_key") != (lat, lon, str(history_start), str(history_end)):
        if history_start > history_end:
            st.error("Start date must be on or before end date.")
        else:
            try:
                with st.spinner("Loading historical weather…"):
                    st.session_state.history_payload = get_historical_weather(
                        lat, lon, loc.get("timezone", "auto"), str(history_start), str(history_end)
                    )
                    st.session_state.history_location_key = (lat, lon, str(history_start), str(history_end))
            except Exception as e:
                st.session_state.history_payload = None
                st.warning(f"Could not load historical weather for this date range: {e}")

    history_payload = st.session_state.get("history_payload")
    history_key = (lat, lon, str(history_start), str(history_end))
    if history_payload and st.session_state.get("history_location_key") == history_key:
        hist_hourly = history_payload.get("hourly", {})
        hist_daily = history_payload.get("daily", {})
        hist_df = pd.DataFrame({
            "time": pd.to_datetime(hist_hourly.get("time", [])),
            "Temperature (°C)": hist_hourly.get("temperature_2m", []),
            "Humidity (%)": hist_hourly.get("relative_humidity_2m", []),
            "Precipitation (mm)": hist_hourly.get("precipitation", []),
        })
        hist_day_df = pd.DataFrame({
            "date": pd.to_datetime(hist_daily.get("time", [])),
            "Maximum (°C)": hist_daily.get("temperature_2m_max", []),
            "Minimum (°C)": hist_daily.get("temperature_2m_min", []),
            "Mean (°C)": hist_daily.get("temperature_2m_mean", []),
            "Precipitation (mm)": hist_daily.get("precipitation_sum", []),
        })
        if not hist_df.empty:
            mean_temp = hist_df["Temperature (°C)"].mean()
            max_temp = hist_df["Temperature (°C)"].max()
            min_temp = hist_df["Temperature (°C)"].min()
            h1, h2, h3 = st.columns(3)
            h1.metric("Average temperature", f"{mean_temp:.1f} °C" if pd.notna(mean_temp) else "—")
            h2.metric("Highest hourly temperature", f"{max_temp:.1f} °C" if pd.notna(max_temp) else "—")
            h3.metric("Lowest hourly temperature", f"{min_temp:.1f} °C" if pd.notna(min_temp) else "—")
            hist_tab1, hist_tab2, hist_tab3 = st.tabs(["Temperature trend", "Daily summary", "Hourly data"])
            with hist_tab1:
                hist_fig = go.Figure()
                hist_fig.add_trace(go.Scatter(
                    x=hist_df["time"], y=hist_df["Temperature (°C)"],
                    mode="lines", name="Temperature",
                    line=dict(color="#168b92", width=2),
                    hovertemplate="%{x|%d %b %Y, %H:%M}<br>%{y:.1f} °C<extra></extra>"
                ))
                hist_fig.update_layout(
                    height=320, margin=dict(l=10, r=10, t=15, b=10),
                    paper_bgcolor="white", plot_bgcolor="white",
                    xaxis_title="", yaxis_title="Temperature (°C)",
                    xaxis=dict(gridcolor="#edf2f3"), yaxis=dict(gridcolor="#edf2f3")
                )
                st.plotly_chart(hist_fig, use_container_width=True)
                hist_humidity_fig = px.line(
                    hist_df, x="time", y="Humidity (%)",
                    color_discrete_sequence=["#6b83ce"]
                )
                hist_humidity_fig.update_layout(
                    height=240, margin=dict(l=10, r=10, t=15, b=10),
                    paper_bgcolor="white", plot_bgcolor="white",
                    xaxis_title="", yaxis_title="Humidity (%)",
                    xaxis=dict(gridcolor="#edf2f3"), yaxis=dict(gridcolor="#edf2f3")
                )
                st.plotly_chart(hist_humidity_fig, use_container_width=True)
            with hist_tab2:
                hist_day_show = hist_day_df.copy()
                hist_day_show["date"] = hist_day_show["date"].dt.strftime("%a, %d %b %Y")
                st.dataframe(
                    hist_day_show.rename(columns={"date": "Date"}),
                    use_container_width=True, hide_index=True
                )
            with hist_tab3:
                st.dataframe(hist_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download historical data (CSV)",
                data=hist_df.to_csv(index=False).encode("utf-8"),
                file_name=f"climascope_{city.lower().replace(' ', '_')}_history_{history_start}_{history_end}.csv",
                mime="text/csv",
                key="download_history_csv"
            )
        else:
            st.info("No historical hourly records were returned for this range.")

    st.markdown(
        '<div class="panel"><div class="section-title">Historical Temperature Patterns</div>'
        '<div class="subtle">Hourly temperature analysis for the selected location and historical date range.</div></div>',
        unsafe_allow_html=True,
    )

    # Reuse the historical dataset loaded in the Historical weather section above.
    history_payload = st.session_state.get("history_payload")
    history_key = (lat, lon, str(history_start), str(history_end))
    history_is_current = (
        history_payload is not None
        and st.session_state.get("history_location_key") == history_key
    )

    if history_is_current:
        historical_hourly = history_payload.get("hourly", {})
        analysis_df = pd.DataFrame({
            "time": pd.to_datetime(historical_hourly.get("time", [])),
            "Temperature (°C)": historical_hourly.get("temperature_2m", []),
        }).dropna(subset=["time", "Temperature (°C)"])

        if not analysis_df.empty:
            temperatures = analysis_df["Temperature (°C)"]
            peak_row = analysis_df.loc[temperatures.idxmax()]
            low_row = analysis_df.loc[temperatures.idxmin()]
            coldest_day = analysis_df.assign(
                date=analysis_df["time"].dt.date
            ).groupby("date")["Temperature (°C)"].mean().idxmin()
            daily_means = analysis_df.assign(
                date=analysis_df["time"].dt.date
            ).groupby("date")["Temperature (°C)"].mean()

            stat1, stat2, stat3, stat4 = st.columns(4)
            stat1.metric(
                "Highest recorded hourly value",
                f"{peak_row['Temperature (°C)']:.1f} °C",
                peak_row["time"].strftime("%a, %d %b · %H:%M"),
            )
            stat2.metric("Historical average", f"{temperatures.mean():.1f} °C")
            stat3.metric(
                "Lowest recorded hourly value",
                f"{low_row['Temperature (°C)']:.1f} °C",
                low_row["time"].strftime("%a, %d %b · %H:%M"),
            )
            stat4.metric(
                "Coldest daily average",
                f"{daily_means.loc[coldest_day]:.1f} °C",
                pd.Timestamp(coldest_day).strftime("%a, %d %b"),
            )

            pattern_df = analysis_df.copy()
            pattern_df["Day"] = pattern_df["time"].dt.day_name()
            pattern_df["Hour"] = pattern_df["time"].dt.hour
            weekday_order = [
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ]
            heatmap_matrix = pattern_df.pivot_table(
                index="Day", columns="Hour", values="Temperature (°C)", aggfunc="mean"
            ).reindex(index=weekday_order, columns=range(24))

            heat_col, distribution_col = st.columns([1.5, 1], gap="medium")
            with heat_col:
                st.markdown("#### Hour-of-day temperature heatmap")
                st.caption(
                    "Each cell is the average of historical readings for that weekday and hour "
                    "within the selected date range. Blank cells mean no matching readings."
                )
                heat_fig = px.imshow(
                    heatmap_matrix,
                    aspect="auto",
                    color_continuous_scale=["#2d4fa2", "#368fd0", "#41c5c4",
                                            "#62bd79", "#e7d64b", "#f39b3d", "#d84a3f"],
                    labels={"x": "Hour of day", "y": "Weekday", "color": "°C"},
                    x=[f"{h:02d}:00" for h in range(24)],
                    y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                )
                heat_fig.update_layout(
                    height=360, margin=dict(l=8, r=8, t=8, b=8),
                    paper_bgcolor="white", xaxis=dict(nticks=12),
                )
                st.plotly_chart(heat_fig, use_container_width=True)

            with distribution_col:
                st.markdown("#### Historical temperature distribution")
                st.caption("Distribution of all available hourly historical temperature readings.")
                hist_fig = px.histogram(
                    x=temperatures, nbins=16,
                    labels={"x": "Temperature (°C)", "y": "Number of hours"},
                    color_discrete_sequence=["#279da0"],
                )
                hist_fig.update_layout(
                    height=360, margin=dict(l=8, r=8, t=8, b=8),
                    paper_bgcolor="white", plot_bgcolor="white",
                    xaxis=dict(gridcolor="#edf2f3"),
                    yaxis=dict(gridcolor="#edf2f3"),
                )
                st.plotly_chart(hist_fig, use_container_width=True)

            with st.expander("View historical temperature data and summary"):
                st.write(
                    f"**Location:** {location_name}  \n"
                    f"**Date range:** {history_start:%d %b %Y} – {history_end:%d %b %Y}  \n"
                    f"**Hourly readings:** {len(analysis_df):,}  \n"
                    f"**Average temperature:** {temperatures.mean():.1f} °C  \n"
                    f"**Highest hourly value:** {peak_row['Temperature (°C)']:.1f} °C "
                    f"on {peak_row['time']:%d %b %Y at %H:%M}  \n"
                    f"**Lowest hourly value:** {low_row['Temperature (°C)']:.1f} °C "
                    f"on {low_row['time']:%d %b %Y at %H:%M}"
                )
                st.dataframe(
                    analysis_df.rename(columns={"time": "Date and time"}),
                    use_container_width=True, hide_index=True,
                )
                st.download_button(
                    "Download analyzed historical temperatures (CSV)",
                    data=analysis_df.to_csv(index=False).encode("utf-8"),
                    file_name=(
                        f"climascope_{city.lower().replace(' ', '_')}_"
                        f"historical_temperature_{history_start}_{history_end}.csv"
                    ),
                    mime="text/csv",
                    key="download_historical_temperature_analysis",
                )
        else:
            st.info("No hourly historical temperature readings are available for this date range.")
    else:
        st.info(
            "Load historical weather data above to see temperature patterns for the selected "
            "location and date range. This section does not generate simulated temperatures."
        )

with simulation_tab:
    # -----------------------------------------------------------------------------
    # Assignment-compliance module: simulated 7 x 24 weekly thermal analysis
    # Kept separate from historical observations so the two data types are not mixed.
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("## Weekly Thermal Simulation")
    st.caption(
        "Assignment requirement: a simulated 7 × 24 NumPy temperature matrix. "
        "This is intentionally separate from the historical Open-Meteo data above."
    )

    SIMULATION_SEED = 304
    rng = np.random.default_rng(SIMULATION_SEED)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = np.arange(24)
    # Peak at 14:00 and minimum at 04:00, following the assignment's specified peak/dip hours.
    daily_cycle = 25 + 8 * np.cos(np.pi * (hours - 14) / 10)
    # Broadcast the daily curve to 7 days and add realistic random weather noise.
    temp_matrix = np.tile(daily_cycle, (7, 1)) + rng.normal(0, 1.8, size=(7, 24))

    # Required NumPy matrix operations.
    hottest_flat_index = int(np.argmax(temp_matrix))
    hottest_day_idx, hottest_hour_idx = np.unravel_index(hottest_flat_index, temp_matrix.shape)
    weekly_average = float(np.mean(temp_matrix))
    daily_averages = np.mean(temp_matrix, axis=1)
    hottest_day_idx_avg = int(np.argmax(daily_averages))
    coldest_day_idx_avg = int(np.argmin(daily_averages))
    night_mask = np.arange(24) <= 5
    coldest_night_value = float(np.min(temp_matrix[:, night_mask]))
    coldest_night_day_idx, coldest_night_hour_idx = np.unravel_index(
        int(np.argmin(np.where(np.tile(night_mask, (7, 1)), temp_matrix, np.inf))),
        temp_matrix.shape,
    )
    comfortable_hours = int(np.count_nonzero((temp_matrix >= 22) & (temp_matrix <= 26)))

    report_a, report_b, report_c, report_d = st.columns(4)
    report_a.metric("Hottest peak", f"{temp_matrix[hottest_day_idx, hottest_hour_idx]:.1f} °C",
                    f"{days[hottest_day_idx]}, {hottest_hour_idx:02d}:00")
    report_b.metric("Weekly average", f"{weekly_average:.1f} °C")
    report_c.metric("Coldest night", f"{coldest_night_value:.1f} °C",
                    f"{days[coldest_night_day_idx]}, {coldest_night_hour_idx:02d}:00")
    report_d.metric("Coldest day average", f"{daily_averages[coldest_day_idx_avg]:.1f} °C",
                    days[coldest_day_idx_avg])
    st.caption(
        f"Hottest day by average: {days[hottest_day_idx_avg]} "
        f"({daily_averages[hottest_day_idx_avg]:.1f} °C). "
        f"Comfortable-zone hours (22–26 °C): {comfortable_hours} of 168. "
        "The simulation is reproducible (fixed random seed) and is not observed weather."
    )

    sim_heat_col, sim_dist_col = st.columns([1.4, 1], gap="large")
    with sim_heat_col:
        st.markdown("#### Simulated weekly heatmap")
        fig, ax = plt.subplots(figsize=(10, 4.3))
        image = ax.imshow(temp_matrix, cmap="magma", aspect="auto", interpolation="nearest")
        ax.set_yticks(np.arange(7), labels=days)
        tick_hours = [0, 6, 12, 18, 23]
        ax.set_xticks(tick_hours, labels=[f"{h:02d}:00" for h in tick_hours])
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("Day of week")
        ax.set_title("Hourly Temperature (Simulated Week)")
        colorbar = fig.colorbar(image, ax=ax, pad=0.02)
        colorbar.set_label("Temperature (°C)")
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    with sim_dist_col:
        st.markdown("#### Simulated temperature distribution")
        fig, ax = plt.subplots(figsize=(7, 4.3))
        ax.hist(temp_matrix.flatten(), bins=16, color="#279da0", edgecolor="white")
        ax.axvspan(22, 26, color="#79c7a5", alpha=0.25, label="Comfortable: 22–26 °C")
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("Number of hours")
        ax.set_title("Temperature Signature of the Week")
        ax.legend(frameon=False)
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with st.expander("View the required 7 × 24 NumPy matrix"):
        sim_matrix_df = pd.DataFrame(temp_matrix, index=days, columns=[f"{h:02d}:00" for h in hours])
        st.dataframe(sim_matrix_df.style.format("{:.1f}"), use_container_width=True)
        st.download_button(
            "Download simulated 7 × 24 matrix (CSV)",
            data=sim_matrix_df.to_csv().encode("utf-8"),
            file_name="climascope_simulated_weekly_temperature_matrix.csv",
            mime="text/csv",
            key="download_simulated_weekly_matrix",
        )

    csv = hour_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download hourly forecast (CSV)", data=csv, file_name=f"climascope_{city.lower().replace(' ','_')}_hourly.csv", mime="text/csv")
    st.caption("Data: Open-Meteo forecast API. Forecasts are model estimates and may differ from observed conditions. This dashboard does not claim to show climate normals or measured global climate fields.")


with air_tab:
    # =============================================================================
    # CliMAScope Advanced Intelligence Suite
    # Real API feeds, transparent heuristic risk indicators and optional ML forecast.
    # =============================================================================
    st.markdown("---")
    st.markdown("# CliMAScope Intelligence Centre")
    st.caption("Air quality · weather hazards · anomaly detection · heat stress · multi-city monitoring")

    AIR_API = "https://air-quality-api.open-meteo.com/v1/air-quality"

    @st.cache_data(ttl=1800, show_spinner=False)
    def get_air_quality(lat, lon, timezone="auto"):
        params = {
            "latitude": lat, "longitude": lon, "timezone": timezone or "auto",
            "forecast_days": 7,
            "current": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi",
            "hourly": "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi"
        }
        response = requests.get(AIR_API, params=params, timeout=25)
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise ValueError(payload.get("reason", "Air-quality data unavailable"))
        return payload

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_openaq_nearby(lat, lon, api_key):
        """Optional OpenAQ v3 station measurements. API key is never stored in source."""
        headers = {"X-API-Key": api_key}
        r = requests.get("https://api.openaq.org/v3/locations", params={
            "coordinates": f"{lat},{lon}", "radius": 25000, "limit": 10,
            "sort": "distance", "order_by": "distance"
        }, headers=headers, timeout=20)
        r.raise_for_status()
        locations = r.json().get("results", [])
        rows = []
        for location in locations[:6]:
            for sensor in location.get("sensors", []):
                parameter = sensor.get("parameter", {})
                pname = parameter.get("name", "unknown")
                if pname not in {"pm25", "pm10", "no2", "so2", "o3"}:
                    continue
                try:
                    mr = requests.get(f"https://api.openaq.org/v3/sensors/{sensor['id']}/measurements",
                                      params={"limit": 1}, headers=headers, timeout=15)
                    mr.raise_for_status()
                    measurements = mr.json().get("results", [])
                    if measurements:
                        m = measurements[0]
                        rows.append({"Station": location.get("name", "Unknown station"),
                                     "Pollutant": pname.upper(), "Value": m.get("value"),
                                     "Unit": m.get("unit", parameter.get("units", "")),
                                     "Last updated": m.get("period", {}).get("datetimeTo", {}).get("utc", "")})
                except Exception:
                    continue
        return pd.DataFrame(rows)

    def aqi_band(value):
        if pd.isna(value): return ("Unavailable", "#94a3b8")
        v=float(value)
        if v <= 50: return ("Good", "#2eaf68")
        if v <= 100: return ("Moderate", "#d6b52c")
        if v <= 150: return ("Unhealthy for sensitive groups", "#ed8b35")
        if v <= 200: return ("Unhealthy", "#df5148")
        if v <= 300: return ("Very unhealthy", "#8e5bb7")
        return ("Hazardous", "#7d263f")

    def risk_label(score):
        if score >= 75: return "Severe", "#9f2638"
        if score >= 50: return "High", "#df6546"
        if score >= 25: return "Moderate", "#d6a52e"
        return "Low", "#2eaf68"

    def heat_index_c(temp_c, humidity):
        """NOAA Rothfusz heat-index approximation; only meaningful in hot/humid conditions."""
        t = temp_c * 9/5 + 32
        rh = float(np.clip(humidity, 0, 100))
        hi = (-42.379 + 2.04901523*t + 10.14333127*rh - .22475541*t*rh
              - .00683783*t*t - .05481717*rh*rh + .00122874*t*t*rh
              + .00085282*t*rh*rh - .00000199*t*t*rh*rh)
        if t < 80 or rh < 40:
            hi = t
        return (hi - 32) * 5/9

    # Air quality from Open-Meteo (no key required); OpenAQ is an optional station cross-check.
    st.markdown("## 1 · Air quality monitoring")
    try:
        with st.spinner("Loading air-quality forecast…"):
            air = get_air_quality(lat, lon, loc.get("timezone", "auto"))
        air_cur = air.get("current", {})
        pollutants = [
            ("PM2.5", "pm2_5", "µg/m³"), ("PM10", "pm10", "µg/m³"),
            ("NO₂", "nitrogen_dioxide", "µg/m³"), ("SO₂", "sulphur_dioxide", "µg/m³"),
            ("O₃", "ozone", "µg/m³")]
        aqi_now = air_cur.get("us_aqi")
        band, band_color = aqi_band(aqi_now)
        aq_cols = st.columns(6)
        aq_cols[0].metric("US AQI", f"{aqi_now:.0f}" if aqi_now is not None else "—", band)
        for i,(label,key,unit_label) in enumerate(pollutants, start=1):
            value=air_cur.get(key)
            aq_cols[i].metric(label, f"{value:.1f} {unit_label}" if value is not None else "—")
        st.markdown(f"<div style='padding:12px 16px;border-radius:10px;background:{band_color}18;border-left:5px solid {band_color}'><b>Current modelled air-quality category: {band}</b><br><span style='color:#657780'>US AQI category based on Open-Meteo forecast model. Pollutant concentrations are model estimates, not local regulatory monitor readings.</span></div>", unsafe_allow_html=True)

        air_hour = air.get("hourly", {})
        air_df = pd.DataFrame({"time":pd.to_datetime(air_hour.get("time",[])),
            "PM2.5":air_hour.get("pm2_5",[]),"PM10":air_hour.get("pm10",[]),
            "NO₂":air_hour.get("nitrogen_dioxide",[]),"SO₂":air_hour.get("sulphur_dioxide",[]),
            "O₃":air_hour.get("ozone",[]),"US AQI":air_hour.get("us_aqi",[]),
            "European AQI":air_hour.get("european_aqi",[])})
        aq_tab1, aq_tab2, aq_tab3 = st.tabs(["AQI heatmap", "Pollutant trends", "Health guidance & correlation"])
        with aq_tab1:
            if not air_df.empty:
                aq_tmp=air_df.dropna(subset=["US AQI"]).copy()
                aq_tmp["Day"]=aq_tmp.time.dt.strftime("%a %d %b")
                aq_tmp["Hour"]=aq_tmp.time.dt.strftime("%H:%M")
                aq_pivot=aq_tmp.pivot_table(index="Day",columns="Hour",values="US AQI",aggfunc="mean")
                if not aq_pivot.empty:
                    f=px.imshow(aq_pivot,aspect="auto",color_continuous_scale=["#2eaf68","#d6b52c","#ed8b35","#df5148","#8e5bb7","#7d263f"],
                                labels={"x":"Local hour","y":"Day","color":"US AQI"})
                    f.update_layout(height=330,margin=dict(l=5,r=5,t=8,b=5),paper_bgcolor="white")
                    st.plotly_chart(f,use_container_width=True)
                else: st.info("AQI heatmap values are not available in this response.")
        with aq_tab2:
            if not air_df.empty:
                chosen=st.multiselect("Pollutants to display",["PM2.5","PM10","NO₂","SO₂","O₃"],default=["PM2.5","PM10"])
                if chosen:
                    f=px.line(air_df,x="time",y=chosen,labels={"time":"Local time","value":"Concentration (µg/m³)"})
                    f.update_layout(height=330,paper_bgcolor="white",xaxis_title="",yaxis_title="µg/m³")
                    st.plotly_chart(f,use_container_width=True)
                st.dataframe(air_df,use_container_width=True,hide_index=True)
        with aq_tab3:
            if aqi_now is None: advice="AQI is unavailable. Check local official air-quality guidance."
            elif aqi_now <= 50: advice="Air quality is good. Usual outdoor activities are generally appropriate."
            elif aqi_now <= 100: advice="Moderate air quality. Unusually sensitive people may consider reducing prolonged heavy outdoor exertion."
            elif aqi_now <= 150: advice="Sensitive groups should reduce prolonged outdoor exertion; monitor symptoms and local advisories."
            elif aqi_now <= 200: advice="Consider limiting prolonged outdoor exertion. Sensitive groups should avoid strenuous outdoor activity."
            else: advice="Avoid strenuous outdoor activity; consider staying indoors with cleaner air and follow local health authority advice."
            st.info("Health advisory (general guidance): " + advice)
            if not hour_df.empty and not air_df.empty:
                corr_df=hour_df[["time","Temperature (°C)"]].merge(air_df[["time","PM2.5","US AQI"]],on="time",how="inner").dropna()
                if len(corr_df)>=5:
                    corr=corr_df[["Temperature (°C)","PM2.5","US AQI"]].corr(method="pearson")
                    st.markdown("**Temperature–pollution Pearson correlation**")
                    st.dataframe(corr.style.format("{:.2f}"),use_container_width=True)
                    st.caption("Correlation indicates association, not causation; values are based on aligned forecast-model hours.")
                else: st.caption("Not enough aligned hourly values to calculate a reliable correlation.")
        with st.expander("Optional OpenAQ station measurements (API key required)"):
            openaq_key=st.text_input("OpenAQ API key",type="password",help="Paste your OpenAQ v3 key for this session. It is not written into the source file.")
            if openaq_key:
                try:
                    openaq_df=get_openaq_nearby(lat,lon,openaq_key)
                    if openaq_df.empty: st.warning("No nearby supported OpenAQ sensor measurements were returned.")
                    else: st.dataframe(openaq_df,use_container_width=True,hide_index=True)
                except Exception as e: st.warning(f"OpenAQ request failed: {e}")
    except Exception as e:
        air_df=pd.DataFrame()
        st.warning(f"Air-quality feed is currently unavailable: {e}")

    # Weather hazards, city risk score and unusual-condition detection.
    st.markdown("## 2 · Weather hazards, anomaly detection & city risk")
    precip = daily.get("precipitation_sum", [0]*len(daily.get("time",[])))
    precip_prob = daily.get("precipitation_probability_max", [0]*len(daily.get("time",[])))
    weather_risk_items=[]
    for i in range(min(len(day_df),len(precip),len(precip_prob))):
        d=day_df.iloc[i]
        rain=float(precip[i] or 0); prob=float(precip_prob[i] or 0)
        tmax=float(d["Maximum (°C)"]); tmin=float(d["Minimum (°C)"])
        if tmax>=40: weather_risk_items.append(("Heatwave threshold",str(d["date"].date()),f"Maximum {tmax:.1f}°C", "High" if tmax<45 else "Severe"))
        if tmin<=5: weather_risk_items.append(("Cold-wave threshold",str(d["date"].date()),f"Minimum {tmin:.1f}°C", "High" if tmin>0 else "Severe"))
        if rain>=64.5 or (rain>=35 and prob>=70): weather_risk_items.append(("Heavy-rain watch",str(d["date"].date()),f"Rain {rain:.1f} mm · probability {prob:.0f}%", "High" if rain<115 else "Severe"))
        if rain>=100 and prob>=70: weather_risk_items.append(("Potential flood-risk indicator",str(d["date"].date()),f"Rain {rain:.1f} mm · probability {prob:.0f}%", "Severe"))

    risk_score=0
    risk_reasons=[]
    if today_max>=40: risk_score+=35; risk_reasons.append("High forecast maximum temperature")
    if today_min<=5: risk_score+=25; risk_reasons.append("Low forecast minimum temperature")
    today_rain=float(precip[0] or 0) if len(precip) else 0
    today_prob=float(precip_prob[0] or 0) if len(precip_prob) else 0
    if today_rain>=64.5 or (today_rain>=35 and today_prob>=70): risk_score+=35; risk_reasons.append("Heavy-rain indicator")
    if 'aqi_now' in locals() and aqi_now is not None and aqi_now>100:
        risk_score+=min(30,(float(aqi_now)-100)*0.3); risk_reasons.append("Elevated AQI")
    risk_score=min(100,int(round(risk_score)))
    risk_name,risk_color=risk_label(risk_score)
    r1,r2=st.columns([1,2])
    with r1:
        st.markdown(f"<div style='background:{risk_color}18;border:1px solid {risk_color};border-radius:14px;padding:18px;text-align:center'><div style='font-size:13px;color:#60757d'>COMPOSITE CITY RISK</div><div style='font-size:38px;font-weight:800;color:{risk_color}'>{risk_name}</div><div style='font-size:22px;font-weight:700'>{risk_score}/100</div></div>",unsafe_allow_html=True)
    with r2:
        if risk_reasons: st.warning("Risk contributors: " + "; ".join(risk_reasons))
        else: st.success("No configured high-risk thresholds were triggered by the current forecast inputs.")
        st.caption("Prototype screening score based on transparent thresholds, not an official warning or calibrated probability.")
    if weather_risk_items:
        st.dataframe(pd.DataFrame(weather_risk_items,columns=["Alert","Forecast date","Signal","Prototype level"]),use_container_width=True,hide_index=True)
    else: st.success("No configured heatwave, cold-wave or heavy-rain thresholds were triggered in the seven-day forecast.")

    # Anomaly detection: robust z-score against the available 7-day hourly forecast distribution.
    if not hour_df.empty:
        anomaly_df=hour_df.dropna(subset=["Temperature (°C)"]).copy()
        med=anomaly_df["Temperature (°C)"].median()
        mad=(anomaly_df["Temperature (°C)"]-med).abs().median()
        anomaly_df["Robust z-score"] = 0.6745*(anomaly_df["Temperature (°C)"]-med)/(mad if mad else np.nan)
        anomalies=anomaly_df[anomaly_df["Robust z-score"].abs()>=3.5]
        st.markdown("**Temperature anomaly detection**")
        st.caption("Robust z-score method over the current seven-day forecast window; flags statistical outliers, not necessarily dangerous weather.")
        if anomalies.empty: st.success("No hourly temperature outliers detected using the configured robust z-score threshold (|z| ≥ 3.5).")
        else: st.dataframe(anomalies[["time","Temperature (°C)","Robust z-score"]],use_container_width=True,hide_index=True)

    # Feels-like/heat index and humidity matrix.
    st.markdown("## 3 · Heat stress & humidity")
    if not hour_df.empty:
        stress_df=hour_df.dropna(subset=["Temperature (°C)","Humidity (%)"]).copy()
        stress_df["Heat index (°C)"]=stress_df.apply(lambda row: heat_index_c(float(row["Temperature (°C)"]),float(row["Humidity (%)"])),axis=1)
        s1,s2,s3=st.columns(3)
        s1.metric("Current apparent temperature",f"{cur.get('apparent_temperature','—')} °C")
        s2.metric("Forecast max heat index",f"{stress_df['Heat index (°C)'].max():.1f} °C" if not stress_df.empty else "—")
        s3.metric("Peak forecast humidity",f"{stress_df['Humidity (%)'].max():.0f}%" if not stress_df.empty else "—")
        if not stress_df.empty:
            stress_df["Day"]=stress_df.time.dt.strftime("%a %d %b"); stress_df["Hour"]=stress_df.time.dt.strftime("%H:%M")
            stress_pivot=stress_df.pivot_table(index="Day",columns="Hour",values="Heat index (°C)",aggfunc="mean")
            hf=px.imshow(stress_pivot,aspect="auto",color_continuous_scale="YlOrRd",labels={"x":"Local hour","y":"Day","color":"Heat index °C"})
            hf.update_layout(height=320,margin=dict(l=5,r=5,t=5,b=5),paper_bgcolor="white")
            st.plotly_chart(hf,use_container_width=True)
            st.caption("Heat-index calculation is an approximation and is most meaningful in hot, humid conditions. Open-Meteo apparent temperature is also shown separately.")

with monitor_tab:
    # Multi-city dashboard: primary location plus user-selected comparison cities.
    st.markdown("## 4 · Multi-city live map & alerts panel")
    city_list_text=st.text_input("Cities to monitor (comma-separated)",value="Hyderabad, Delhi, Mumbai, Bengaluru, Chennai",key="multi_city_names")
    if st.button("Update multi-city dashboard",key="refresh_multi_city"):
        st.session_state.multi_city_payload=None
        st.cache_data.clear()
        st.rerun()

    @st.cache_data(ttl=1800,show_spinner=False)
    def fetch_city_snapshot(city_name):
        place=geocode_city(city_name)
        w=get_weather(float(place["latitude"]),float(place["longitude"]),place.get("timezone","auto"))
        a=get_air_quality(float(place["latitude"]),float(place["longitude"]),place.get("timezone","auto"))
        cc=w.get("current",{}); dd=w.get("daily",{}); ac=a.get("current",{})
        mx=float((dd.get("temperature_2m_max") or [0])[0] or 0)
        mn=float((dd.get("temperature_2m_min") or [0])[0] or 0)
        rain=float((dd.get("precipitation_sum") or [0])[0] or 0)
        aq=ac.get("us_aqi")
        score=0
        if mx>=40: score+=35
        if mn<=5: score+=25
        if rain>=64.5: score+=35
        if aq is not None and aq>100: score+=min(30,(float(aq)-100)*.3)
        score=min(100,int(round(score)))
        level,color=risk_label(score)
        return {"City":place.get("name",city_name),"Country":place.get("country",""),"Latitude":place["latitude"],"Longitude":place["longitude"],
                "Temperature (°C)":cc.get("temperature_2m"),"US AQI":aq,"Rain today (mm)":rain,"Risk score":score,"Risk level":level,"Risk colour":color}

    names=[]
    for n in [city.strip() for city in city_list_text.split(",") if city.strip()]:
        if n.lower() not in [x.lower() for x in names]: names.append(n)
    names=names[:10]
    city_rows=[]
    with st.spinner("Retrieving weather and air-quality snapshots for selected cities…"):
        for n in names:
            try: city_rows.append(fetch_city_snapshot(n))
            except Exception as e: st.warning(f"{n}: data unavailable ({e})")
    if city_rows:
        cities_df=pd.DataFrame(city_rows)
        m1,m2,m3=st.columns(3)
        m1.metric("Cities monitored",len(cities_df))
        m2.metric("Highest city risk",cities_df.loc[cities_df["Risk score"].idxmax(),"Risk level"])
        valid_aqi=cities_df["US AQI"].dropna()
        m3.metric("Highest US AQI",f"{valid_aqi.max():.0f}" if len(valid_aqi) else "—")
        map_fig=go.Figure()
        map_fig.add_trace(go.Scattergeo(lon=cities_df["Longitude"],lat=cities_df["Latitude"],mode="markers+text",
            text=cities_df["City"],textposition="top center",customdata=cities_df[["Temperature (°C)","US AQI","Risk level","Risk score"]].fillna("—").values,
            marker=dict(size=14,color=cities_df["Risk score"],colorscale=[[0,"#2eaf68"],[.25,"#d6a52e"],[.5,"#df6546"],[1,"#9f2638"]],cmin=0,cmax=100,
                        colorbar=dict(title="Risk /100"),line=dict(width=1,color="white")),
            hovertemplate="<b>%{text}</b><br>Temp: %{customdata[0]}°C<br>US AQI: %{customdata[1]}<br>Risk: %{customdata[2]} (%{customdata[3]}/100)<extra></extra>"))
        map_fig.update_geos(projection_type="natural earth",showland=True,landcolor="#e5edef",showocean=True,oceancolor="#f7fafb",showcountries=True,countrycolor="#cbd8dc")
        map_fig.update_layout(height=420,margin=dict(l=0,r=0,t=5,b=0),paper_bgcolor="white",geo=dict(bgcolor="white"))
        st.plotly_chart(map_fig,use_container_width=True)
        st.markdown("**City risk and alert panel**")
        st.dataframe(cities_df[["City","Country","Temperature (°C)","US AQI","Rain today (mm)","Risk score","Risk level"]],use_container_width=True,hide_index=True)
        alert_cities=cities_df[cities_df["Risk score"]>=25]
        if not alert_cities.empty:
            for _,rr in alert_cities.iterrows(): st.warning(f"{rr['City']}: {rr['Risk level']} prototype risk ({rr['Risk score']}/100). Review local official advisories.")
        else: st.success("No selected city crossed the prototype moderate-risk score threshold.")

    # Seven-day ML estimate. Train on historical Open-Meteo hourly archive values, evaluate a
    # chronological holdout, and clearly distinguish this estimate from the official API forecast.
    st.markdown("## 5 · Experimental 7-day machine-learning temperature estimate")
    st.caption("Random Forest regression trained on recent historical hourly temperatures. This is an experimental model, not an official forecast.")
    if st.button("Train model and generate 7-day estimate",key="train_temp_ml"):
        try:
            from sklearn.ensemble import RandomForestRegressor
            end_train=date.today()-timedelta(days=6)
            start_train=end_train-timedelta(days=179)
            with st.spinner("Downloading training history and fitting Random Forest…"):
                training=get_historical_weather(lat,lon,loc.get("timezone","auto"),str(start_train),str(end_train))
            train_hourly=training.get("hourly",{})
            train_df=pd.DataFrame({"time":pd.to_datetime(train_hourly.get("time",[])),"temp":train_hourly.get("temperature_2m",[]) }).dropna()
            if len(train_df)<300: raise ValueError("Not enough historical hourly data to train a meaningful model.")
            def features(dt_series):
                dt=pd.to_datetime(dt_series)
                return np.column_stack([dt.dt.hour,dt.dt.dayofyear,dt.dt.month,
                                        np.sin(2*np.pi*dt.dt.hour/24),np.cos(2*np.pi*dt.dt.hour/24),
                                        np.sin(2*np.pi*dt.dt.dayofyear/365.25),np.cos(2*np.pi*dt.dt.dayofyear/365.25)])
            split=int(len(train_df)*.8)
            X=features(train_df["time"]); y=train_df["temp"].to_numpy(dtype=float)
            model=RandomForestRegressor(n_estimators=180,max_depth=14,min_samples_leaf=2,random_state=42,n_jobs=-1)
            model.fit(X[:split],y[:split])
            holdout_pred=model.predict(X[split:])
            mae=float(np.mean(np.abs(holdout_pred-y[split:])))
            model.fit(X,y)
            future_times=pd.date_range(pd.Timestamp.now().floor("h"),periods=168,freq="h")
            predictions=model.predict(features(pd.Series(future_times)))
            ml_df=pd.DataFrame({"time":future_times,"ML estimate (°C)":predictions})
            st.session_state.ml_forecast_df=ml_df
            st.session_state.ml_mae=mae
        except Exception as e: st.error(f"Could not train the ML model: {e}")
    if "ml_forecast_df" in st.session_state:
        ml_df=st.session_state.ml_forecast_df
        st.metric("Chronological holdout MAE",f"{st.session_state.ml_mae:.2f} °C",help="Mean absolute error on the final 20% of historical hourly records before refitting on all available history.")
        mf=px.line(ml_df,x="time",y="ML estimate (°C)",labels={"time":"Time","ML estimate (°C)":"Temperature °C"})
        mf.update_traces(line_color="#8b63c7")
        mf.update_layout(height=300,paper_bgcolor="white",xaxis_title="",yaxis_title="°C")
        st.plotly_chart(mf,use_container_width=True)
        st.download_button("Download ML estimate (CSV)",ml_df.to_csv(index=False).encode(),"climascope_ml_7day_estimate.csv","text/csv")
        st.caption("The model uses calendar/time features only; it does not use future observations. Accuracy may be weak during rapidly changing weather. Compare with Open-Meteo forecast before drawing conclusions.")

    st.markdown("---")
    st.caption("CliMAScope is an educational prototype. Risk indicators and health guidance are informational and do not replace official meteorological, flood-management or public-health alerts.")
