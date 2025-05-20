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
LAT = 52.5200
LON = 13.4050
URL_CURRENT = f"{BASE}/get-current-outdoor-weather?lat={LAT}&lon={LON}"
URL_FORECAST = f"{BASE}/get-forecast-outdoor-weather?lat={LAT}&lon={LON}"

# --- Fetch current outdoor weather data ---
try:
    resp = requests.get(URL_CURRENT, timeout=5)
    if resp.status_code == 200:
        current_data = resp.json().get('data', {})
    else:
        current_data = {}
except Exception:
    current_data = {}

# --- Fetch forecast JSON ---
try:
    resp_f = requests.get(URL_FORECAST, timeout=5)
    forecast_json = resp_f.json().get('list', [])
except Exception:
    forecast_json = []

# --- Data generation for demonstration charts ---
date_rng = pd.date_range(start='2025-01-01', end=pd.Timestamp.now(), freq='h')
df = pd.DataFrame(date_rng, columns=['timestamp'])
np.random.seed(42)
df['temperature'] = np.random.uniform(15, 30, size=len(df)).round(1)
df['humidity'] = np.random.uniform(30, 90, size=len(df)).round(1)
df['co2'] = np.random.randint(400, 1000, size=len(df))
df['rain_probability'] = np.random.randint(0, 100, size=len(df))
# Placeholder indoor sensor columns
for col in [
    'indoor_temperature','indoor_humidity','indoor_pressure',
    'indoor_tvoc','indoor_co2eq','indoor_ethanol','indoor_h2','indoor_light_lux'
]:
    df[col] = None

# Use full dataset for charts
df_filtered = df.copy()

# --- Chart helpers ---
def make_line_chart(input_df, x_field, y_field, title=None, line_color=None):
    return (
        alt.Chart(input_df)
        .mark_line(point=True, color=line_color)
        .encode(
            x=alt.X(f'{x_field}:T', axis=alt.Axis(title="Timestamp")),
            y=alt.Y(f'{y_field}:Q', axis=alt.Axis(title=title)),
            tooltip=[x_field, y_field]
        )
        .properties(width=700, height=400, title=title)
    )

def make_donut(input_response, input_text, input_color):
    palettes = {'green':['#27AE60','#12783D'],'blue':['#29b5e8','#155F7A'],'red':['#E74C3C','#781F16']}
    colors = palettes.get(input_color,['#CCCCCC','#777777'])
    source = pd.DataFrame({'Category':['',input_text], '% value':[100-input_response, input_response]})
    chart = (
        alt.Chart(source)
        .mark_arc(innerRadius=45, cornerRadius=25)
        .encode(
            theta=alt.Theta('% value:Q'),
            color=alt.Color('Category:N', scale=alt.Scale(domain=[input_text,''], range=colors), legend=None)
        )
        .properties(width=150, height=150)
    )
    text = chart.mark_text(align='center', fontSize=32, fontWeight=700, color=colors[0]).encode(text=alt.value(f'{input_response} %'))
    return chart + text

# Initialize metric state
if 'metric' not in st.session_state:
    st.session_state.metric = 'temperature'

# --- Layout ---
col1, col2, col3 = st.columns((1.5, 4.5, 2), gap='medium')

def get_latest(df):
    return df.sort_values('timestamp').iloc[-1] if not df.empty else None
latest = get_latest(df_filtered)

# Column 1: Current Outdoor Conditions
with col1:
    st.markdown('#### Current Outdoor Conditions')
    left_c, right_c = st.columns(2)
    if current_data:
        # Left side fields
        left_c.metric('Latitude', current_data.get('latitude','N/A'))
        left_c.metric('Longitude', current_data.get('longitude','N/A'))
        left_c.metric('Temperature (°C)', current_data.get('outdoor_temperature','N/A'))
        # Outdoor Humidity gauge
        left_c.markdown('**Humidity (%)**')
        hum_val = current_data.get('outdoor_humidity', 0)
        left_c.altair_chart(make_donut(hum_val, 'Outdoor Humidity', 'blue'), use_container_width=True)
        # Timestamp
        ts = current_data.get('timestamp')
        if ts:
            dt = pd.to_datetime(ts, unit='s')
            left_c.write(dt.strftime('last updated %d.%m.%Y at %H:%Mpm'))
        # Rain Probability
        rain_p = current_data.get('outdoor_rain_1h', 0)
        left_c.markdown('**Rain (last 1h) (mm)**')
        left_c.metric('', rain_p)

        # Right side fields
        right_c.metric('Pressure (hPa)', current_data.get('outdoor_pressure','N/A'))
        right_c.metric('CO (ppm)', current_data.get('outdoor_air_co','N/A'))
        right_c.metric('AQI', current_data.get('outdoor_air_quality_index','N/A'))
        right_c.metric('Clouds (%)', current_data.get('outdoor_cloud_coverage','N/A'))
        right_c.metric('Wind Speed (m/s)', current_data.get('outdoor_wind_speed','N/A'))
        right_c.metric('Wind Direction (°)', current_data.get('outdoor_wind_deg','N/A'))
        # Weather description and icon
        icon = current_data.get('outdoor_weather_icon')
        right_c.metric('Weather', current_data.get('outdoor_weather_category','N/A'))
        right_c.write(current_data.get('outdoor_weather','N/A'))
        if icon:
            right_c.image(f"http://openweathermap.org/img/wn/{icon}@2x.png", width=80)
    else:
        left_c.write('Unable to fetch outdoor data.')

# Column 2: Forecast and Metric Over Time
with col2:
    # Forecast mode selector
    mode = st.selectbox('Forecast mode', ['Next 4 days @12:00', 'Next 4 entries (3h)'], index=0)
    now = pd.Timestamp.now()
    entries = []
    if mode == 'Next 4 days @12:00':
        today = now.normalize()
        for i in range(1, 5):
            dt = today + pd.Timedelta(days=i) + pd.Timedelta(hours=12)
            s = dt.strftime('%Y-%m-%d %H:%M:%S')
            m = next((item for item in forecast_json if item.get('dt_txt') == s), None)
            temp = m['main']['temp'] if m else '--'
            icon = m['weather'][0]['icon'] if m else None
            entries.append({'label': dt.strftime('%b %d'), 'temp': temp, 'icon': icon})
    else:
        future = [it for it in forecast_json if pd.to_datetime(it.get('dt_txt')) > now]
        for it in future[:4]:
            dt = pd.to_datetime(it.get('dt_txt'))
            entries.append({'label': dt.strftime('%b %d %H:%M'), 'temp': it['main']['temp'], 'icon': it['weather'][0]['icon']})
    st.markdown('#### Forecast')
    fc_cols = st.columns(4)
    for c, e in zip(fc_cols, entries):
        if e['icon']:
            c.image(f"http://openweathermap.org/img/wn/{e['icon']}@2x.png", width=150)
        c.metric(e['label'], f"{e['temp']}°C")

    # Data source selector
    data_src = st.selectbox('Data source', ['Outdoor', 'Indoor'], index=0)
    st.markdown('#### Metric Over Time')
    # Timeframe selector
    tf = st.selectbox('Timeframe', ['Last 24 hours', 'Last 7 days', 'Last 30 days'], index=0)
    cutoff = now - pd.Timedelta(hours=24) if tf == 'Last 24 hours' else now - pd.Timedelta(days=7) if tf == 'Last 7 days' else now - pd.Timedelta(days=30)
    df_time = df_filtered[df_filtered['timestamp'] >= cutoff]

    # Metric buttons
    btn_temp, btn_hum, btn_co2 = st.columns(3)
    if btn_temp.button('Temperature'):
        st.session_state.metric = 'temperature'
    if btn_hum.button('Humidity'):
        st.session_state.metric = 'humidity'
    if btn_co2.button('CO₂'):
        st.session_state.metric = 'co2'

    # Determine field and color based on metrics and source
    if data_src == 'Outdoor':
        field_map = {'temperature': 'temperature', 'humidity': 'humidity', 'co2': 'co2'}
    else:
        field_map = {'temperature': 'indoor_temperature', 'humidity': 'indoor_humidity', 'co2': 'indoor_co2'}
    metric = st.session_state.metric
    y_field = field_map.get(metric, 'temperature')
    title_map = {'temperature': 'Temperature (°C)', 'humidity': 'Humidity (%)', 'co2': 'CO₂ (ppm)'}
    color_map = {'temperature': 'green', 'humidity': 'blue', 'co2': 'red'}

    # Chart
    st.altair_chart(
        make_line_chart(
            df_time,
            'timestamp',
            y_field,
            f"{data_src} {title_map[metric]}",
            line_color=color_map[metric]
        ),
        use_container_width=True
    )

# Column 3: Indoor Sensor Readings
with col3:
    st.markdown('#### Indoor Sensor Readings')
    l,r = st.columns(2)
    if latest is not None:
        l.write(latest['timestamp'].strftime('last updated %d.%m.%Y at %H:%Mpm'))
        l.metric('Indoor Temp (°C)',latest['indoor_temperature'] or 'N/A')
        l.markdown('**Indoor Humidity (%)**')
        hv = latest['indoor_humidity'] or 0
        l.altair_chart(make_donut(hv,'Indoor Humidity','blue'),use_container_width=True)
        l.metric('Pressure (hPa)',latest['indoor_pressure'] or 'N/A')
        r.metric('TVOC (ppb)',latest['indoor_tvoc'] or 'N/A')
        r.metric('CO₂eq (ppm)',latest['indoor_co2eq'] or 'N/A')
        r.metric('Ethanol (ppm)',latest['indoor_ethanol'] or 'N/A')
        r.metric('H₂ (ppb)',latest['indoor_h2'] or 'N/A')
        r.metric('Light (lux)',latest['indoor_light_lux'] or 'N/A')
    else:
        l.write('No indoor data available.')