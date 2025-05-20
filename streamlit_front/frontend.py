import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests

st.set_page_config(
    page_title="Weather Monitoring Dashboard",
    page_icon="☁️",
    layout="wide"
)

alt.theme.enable("dark")

# --- Config ---
BASE = "https://plouf-backend-442302770654.europe-west6.run.app"
LAT = 46.5369
LON = 6.5848
# Replace with your actual password
PASSWORD = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"

URL_CURRENT = f"{BASE}/get-current-outdoor-weather?lat={LAT}&lon={LON}"
URL_FORECAST = f"{BASE}/get-forecast-outdoor-weather?lat={LAT}&lon={LON}"
URL_INDOOR = f"{BASE}/get_indoor_weather_json"

# --- Fetch outdoor weather ---
try:
    resp = requests.get(URL_CURRENT, timeout=5)
    current_data = resp.json().get('data', {}) if resp.status_code == 200 else {}
except Exception:
    current_data = {}

# --- Fetch forecast weather ---
try:
    resp_f = requests.get(URL_FORECAST, timeout=5)
    forecast_json = resp_f.json().get('list', [])
except Exception:
    forecast_json = []

# --- Fetch indoor weather ---
indoor_data = {}
try:
    resp_i = requests.get(
        URL_INDOOR,
        params={"lat": LAT, "lon": LON, "passwd": PASSWORD},
        timeout=5
    )
    # Debug response
    st.write(f"Indoor fetch - URL: {resp_i.url}")
    st.write(f"Indoor fetch - Status: {resp_i.status_code}")
    st.write(f"Indoor fetch - Raw text: {resp_i.text}")
    try:
        raw_i = resp_i.json()
        if resp_i.status_code == 200:
            # If the JSON is directly sensor data
            if 'indoor_temperature' in raw_i:
                indoor_data = raw_i
            # If wrapped in status/data
            elif raw_i.get('status') == 'success' and 'data' in raw_i:
                indoor_data = raw_i.get('data', {})
            else:
                st.write(f"Indoor fetch error: {raw_i.get('status')} - {raw_i.get('data')}")
        else:
            st.write(f"Indoor fetch failed with status {resp_i.status_code}")
    except ValueError:
        st.write("Failed to parse indoor JSON response")
except Exception as e:
    st.write(f"Exception fetching indoor data: {e}")

# --- Demo data for charts ---
date_rng = pd.date_range(start='2025-01-01', end=pd.Timestamp.now(), freq='h')
df = pd.DataFrame(date_rng, columns=['timestamp'])
np.random.seed(42)
df['temperature'] = np.random.uniform(15, 30, size=len(df)).round(1)
df['humidity'] = np.random.uniform(30, 90, size=len(df)).round(1)
df['co2'] = np.random.randint(400, 1000, size=len(df))
# Placeholder indoor columns
for col in [
    'indoor_temperature','indoor_humidity','indoor_pressure',
    'indoor_tvoc','indoor_co2eq','indoor_ethanol','indoor_h2','indoor_light_lux'
]:
    df[col] = None

df_filtered = df.copy()

# --- Chart helpers ---
def make_line_chart(df, x, y, title=None, color=None):
    return (
        alt.Chart(df)
        .mark_line(point=True, color=color)
        .encode(
            x=alt.X(f"{x}:T", title="Timestamp"),
            y=alt.Y(f"{y}:Q", title=title),
            tooltip=[x, y]
        )
        .properties(width=700, height=400, title=title)
    )

def make_donut(val, text, clr):
    pals = {'green':['#27AE60','#12783D'], 'blue':['#29b5e8','#155F7A'], 'red':['#E74C3C','#781F16']}
    cols = pals.get(clr, ['#CCCCCC', '#777777'])
    src = pd.DataFrame({'Category': ['', text], '% value': [100-val, val]})
    chart = (
        alt.Chart(src)
        .mark_arc(innerRadius=45, cornerRadius=25)
        .encode(
            theta=alt.Theta('% value:Q'),
            color=alt.Color('Category:N', scale=alt.Scale(domain=[text, ''], range=cols), legend=None)
        )
        .properties(width=150, height=150)
    )
    txt = chart.mark_text(align='center', fontSize=32, fontWeight=700, color=cols[0]).encode(text=alt.value(f"{val} %"))
    return chart + txt

# State and layout
if 'metric' not in st.session_state:
    st.session_state.metric = 'temperature'
col1, col2, col3 = st.columns((1.5, 4.5, 2), gap='medium')
now = pd.Timestamp.now()

def get_latest(df):
    return df.sort_values('timestamp').iloc[-1] if not df.empty else None
latest = get_latest(df_filtered)

# --- Outdoor Panel ---
with col1:
    st.markdown('#### Current Outdoor Conditions')
    lc, rc = st.columns(2)
    if current_data:
        lc.metric('Lat', current_data.get('latitude', 'N/A'))
        lc.metric('Lon', current_data.get('longitude', 'N/A'))
        lc.metric('Temp (°C)', current_data.get('outdoor_temperature', 'N/A'))
        lc.markdown('**Humidity (%)**')
        hv = current_data.get('outdoor_humidity', 0)
        lc.altair_chart(make_donut(hv, 'Outdoor Humidity', 'blue'), use_container_width=True)
        ts = current_data.get('timestamp')
        if ts:
            lc.write(pd.to_datetime(ts, unit='s').strftime('last updated %d.%m.%Y at %H:%Mpm'))
        lp = current_data.get('outdoor_rain_1h', 0)
        lc.markdown('**Rain (1h mm)**')
        lc.metric('', lp)
        rc.metric('Press (hPa)', current_data.get('outdoor_pressure', 'N/A'))
        rc.metric('CO (ppm)', current_data.get('outdoor_air_co', 'N/A'))
        rc.metric('AQI', current_data.get('outdoor_air_quality_index', 'N/A'))
        rc.metric('Clouds (%)', current_data.get('outdoor_cloud_coverage', 'N/A'))
        rc.metric('Wind (m/s)', current_data.get('outdoor_wind_speed', 'N/A'))
        rc.metric('Dir (°)', current_data.get('outdoor_wind_deg', 'N/A'))
        icon = current_data.get('outdoor_weather_icon')
        rc.metric('Weather', current_data.get('outdoor_weather_category', 'N/A'))
        rc.write(current_data.get('outdoor_weather', 'N/A'))
        if icon:
            rc.image(f"http://openweathermap.org/img/wn/{icon}@2x.png", width=80)
    else:
        lc.write('Unable to fetch outdoor data.')

# --- Forecast & Trends Panel ---
with col2:
    st.markdown('#### Forecast')
    mode = st.selectbox('Forecast mode', ['Next 4 days @12:00', 'Next 4 entries (3h)'])
    entries = []
    if mode.startswith('Next 4 days'):
        base = now.normalize()
        for i in range(1, 5):
            dt = base + pd.Timedelta(days=i, hours=12)
            s = dt.strftime('%Y-%m-%d %H:%M:%S')
            m = next((x for x in forecast_json if x.get('dt_txt') == s), {})
            entries.append({
                'label': dt.strftime('%b %d'),
                'temp': m.get('main', {}).get('temp', '--'),
                'icon': m.get('weather', [{}])[0].get('icon')
            })
    else:
        fut = [x for x in forecast_json if pd.to_datetime(x.get('dt_txt')) > now]
        for x in fut[:4]:
            dt = pd.to_datetime(x.get('dt_txt'))
            entries.append({
                'label': dt.strftime('%b %d %H:%M'),
                'temp': x['main']['temp'],
                'icon': x['weather'][0]['icon']
            })
    fc_cols = st.columns(4)
    for c, e in zip(fc_cols, entries):
        if e['icon']:
            c.image(f"http://openweathermap.org/img/wn/{e['icon']}@2x.png", width=150)
        c.metric(e['label'], f"{e['temp']}°C")

    st.markdown('#### Metric Over Time')
    src = st.selectbox('Data source', ['Outdoor', 'Indoor'])
    tf = st.selectbox('Timeframe', ['Last 24 hours', 'Last 7 days', 'Last 30 days'])
    delta = pd.Timedelta(hours=24) if '24' in tf else pd.Timedelta(days=7) if '7' in tf else pd.Timedelta(days=30)
    df_time = df_filtered[df_filtered['timestamp'] >= now - delta]
    btns = st.columns(3)
    if btns[0].button('Temperature'):
        st.session_state.metric = 'temperature'
    if btns[1].button('Humidity'):
        st.session_state.metric = 'humidity'
    if btns[2].button('CO₂'):
        st.session_state.metric = 'co2'
    metric = st.session_state.metric
    field = metric if src == 'Outdoor' else f"indoor_{metric}"
    titles = {'temperature': 'Temperature (°C)', 'humidity': 'Humidity (%)', 'co2': 'CO₂ (ppm)'}
    colors = {'temperature': 'green', 'humidity': 'blue', 'co2': 'red'}
    st.altair_chart(make_line_chart(df_time, 'timestamp', field, f"{src} {titles[metric]}", colors[metric]), use_container_width=True)

# --- Indoor Panel ---
with col3:
    st.markdown('#### Indoor Sensor Readings')
    if indoor_data:
        st.json(indoor_data)
        a, b = st.columns(2)
        a.metric('Temp (°C)', indoor_data.get('indoor_temperature', 'N/A'))
        a.markdown('**Humidity (%)**')
        hv = indoor_data.get('indoor_humidity', 0)
        a.altair_chart(make_donut(hv, 'Indoor Humidity', 'blue'), use_container_width=True)
        a.metric('Pressure (hPa)', indoor_data.get('indoor_pressure', 'N/A'))
        b.metric('TVOC (ppb)', indoor_data.get('indoor_tvoc', 'N/A'))
        b.metric('CO₂eq (ppm)', indoor_data.get('indoor_co2eq', 'N/A'))
        b.metric('Ethanol (ppm)', indoor_data.get('indoor_ethanol', 'N/A'))
        b.metric('H₂ (ppb)', indoor_data.get('indoor_h2', 'N/A'))
        motion = "Yes" if indoor_data.get('indoor_motion_detected') else "No"
        b.metric('Motion Detected', motion)
        b.metric('Light (lux)', indoor_data.get('indoor_light_lux', 'N/A'))
        ts = indoor_data.get('timestamp')
        if ts:
            a.write(pd.to_datetime(ts).strftime('last updated %d.%m.%Y at %H:%M'))
    else:
        st.write('Unable to fetch indoor data.')
