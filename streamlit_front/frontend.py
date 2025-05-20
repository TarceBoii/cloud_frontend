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
PASSWORD = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"

URL_CURRENT = f"{BASE}/get-current-outdoor-weather?lat={LAT}&lon={LON}"
URL_FORECAST = f"{BASE}/get-forecast-outdoor-weather?lat={LAT}&lon={LON}"
URL_INDOOR = f"{BASE}/get_indoor_weather_json?lat={LAT}&lon={LON}&passwd={PASSWORD}"
URL_AQI_BATCH = f"{BASE}/get-indoor-air-quality-index"
URL_HISTORICAL_INDOOR = f"{BASE}/get-historical-indoor-weather"
URL_HISTORICAL_OUTDOOR = f"{BASE}/get-historical-outdoor-weather"

# --- Fetch data ---
# Current outdoor
try:
    resp = requests.get(URL_CURRENT, timeout=5)
    current_data = resp.json().get('data', {}) if resp.status_code == 200 else {}
except Exception:
    current_data = {}

# Forecast outdoor
try:
    resp_f = requests.get(URL_FORECAST, timeout=5)
    forecast_json = resp_f.json().get('list', []) if resp_f.status_code == 200 else []
except Exception:
    forecast_json = []

# Current indoor
try:
    resp_i = requests.get(URL_INDOOR, timeout=5)
    raw_i = resp_i.json()
    indoor_data = raw_i if resp_i.status_code == 200 and 'indoor_temperature' in raw_i else raw_i.get('data', {})
except Exception:
    indoor_data = {}

# Calculate Indoor AQI via batch endpoint
try:
    payload = [{
        'indoor_temperature': indoor_data.get('indoor_temperature'),
        'indoor_humidity': indoor_data.get('indoor_humidity'),
        'indoor_co2eq': indoor_data.get('indoor_co2eq'),
        'indoor_tvoc': indoor_data.get('indoor_tvoc')
    }]
    resp_aqi = requests.post(URL_AQI_BATCH, json=payload, timeout=5)
    aqi_result = resp_aqi.json()[0] if resp_aqi.status_code == 200 else {}
except Exception:
    aqi_result = {}

# Historical indoor
try:
    resp_hi = requests.get(URL_HISTORICAL_INDOOR, params={"lat": LAT, "lon": LON}, timeout=10)
    hist_indoor = resp_hi.json().get('data', []) if resp_hi.status_code == 200 else []
except Exception:
    hist_indoor = []
hist_indoor_df = pd.DataFrame(hist_indoor)
if not hist_indoor_df.empty:
    hist_indoor_df['timestamp'] = pd.to_datetime(hist_indoor_df['timestamp'], utc=True).dt.tz_convert(None)
    hist_indoor_df.sort_values('timestamp', inplace=True)
else:
    hist_indoor_df = pd.DataFrame(columns=['timestamp','indoor_temperature','indoor_humidity','indoor_pressure','indoor_tvoc','indoor_co2eq','indoor_ethanol','indoor_h2','indoor_motion_detected'])

# Historical outdoor
try:
    resp_ho = requests.get(URL_HISTORICAL_OUTDOOR, params={"lat": LAT, "lon": LON}, timeout=10)
    hist_outdoor = resp_ho.json().get('data', []) if resp_ho.status_code == 200 else []
except Exception:
    hist_outdoor = []
hist_outdoor_df = pd.DataFrame(hist_outdoor)
if not hist_outdoor_df.empty:
    hist_outdoor_df['timestamp'] = pd.to_datetime(hist_outdoor_df['timestamp'], utc=True).dt.tz_convert(None)
    hist_outdoor_df.sort_values('timestamp', inplace=True)
else:
    hist_outdoor_df = pd.DataFrame(columns=['timestamp','outdoor_temperature','outdoor_humidity','outdoor_pressure','outdoor_weather','latitude','longitude','outdoor_wind_speed','outdoor_cloud_coverage','outdoor_air_co','outdoor_air_quality_index','outdoor_wind_deg','outdoor_rain_1h'])

# --- Chart helpers ---
def make_line_chart(df, x, y, title=None):
    return (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X(f"{x}:T", title="Timestamp"),
            y=alt.Y(f"{y}:Q", title=title),
            tooltip=[x, y]
        )
        .properties(width=700, height=400, title=title)
    )


def make_donut(val, text, clr):
    pals = {'green':['#27AE60','#12783D'], 'blue':['#29b5e8','#155F7A'], 'red':['#E74C3C','#781F16']}
    cols = pals.get(clr, ['#CCCCCC','#777777'])
    src = pd.DataFrame({'Category': ['', text], '% value': [100-val, val]})
    chart = (
        alt.Chart(src)
        .mark_arc(innerRadius=45, cornerRadius=25)
        .encode(
            theta=alt.Theta('% value:Q'),
            color=alt.Color('Category:N', scale=alt.Scale(domain=[text,''], range=cols), legend=None)
        )
        .properties(width=150, height=150)
    )
    txt = chart.mark_text(align='center', fontSize=32, fontWeight=700, color=cols[0])
    return chart + txt.encode(text=alt.value(f"{val} %"))


def make_aqi_donut(aqi: int):
    palette = {
        1: ['#27AE60', '#12783D'],
        2: ['#7ED957', '#4C8C2B'],
        3: ['#F1C232', '#A2882D'],
        4: ['#F39C12', '#A35400'],
        5: ['#D35400', '#803200'],
        6: ['#E74C3C', '#781F16'],
    }
    cols = palette.get(aqi, ['#CCCCCC', '#777777'])
    src = pd.DataFrame({'Category': ['', 'AQI Level'], '% value': [6-aqi, aqi]})
    chart = (
        alt.Chart(src)
        .mark_arc(innerRadius=45, cornerRadius=25)
        .encode(
            theta=alt.Theta('% value:Q'),
            color=alt.Color('Category:N', scale=alt.Scale(domain=['AQI Level',''], range=cols), legend=None)
        )
        .properties(width=150, height=150, title='AQI Level')
    )
    txt = chart.mark_text(align='center', fontSize=24, fontWeight=700, color=cols[0])
    return chart + txt.encode(text=alt.value(str(aqi)))

# --- Layout & State ---
if 'metric' not in st.session_state:
    st.session_state.metric = 'temperature'
col1, col2, col3 = st.columns((1.5, 4.5, 2), gap='medium')
now = pd.Timestamp.now()

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
            lc.write(pd.to_datetime(ts, unit='s').strftime('last updated %d.%m.%Y at %H:%M'))
        lp = current_data.get('outdoor_rain_1h', 0)
        lc.markdown('**Rain (1h mm)**')
        lc.metric('', lp)

        # Clouds with % formatting
        clouds = current_data.get('outdoor_cloud_coverage', None)
        rc.metric('Clouds (%)', f"{round(clouds)}%" if isinstance(clouds, (int, float)) else 'N/A')

        # AQI Donut
        aqi = current_data.get('outdoor_air_quality_index', None)
        if isinstance(aqi, int) and 1 <= aqi <= 6:
            rc.markdown('**Air Quality Index**')
            rc.altair_chart(make_aqi_donut(aqi), use_container_width=True)
        else:
            rc.metric('AQI', aqi if aqi is not None else 'N/A')

        rc.metric('Press (hPa)', current_data.get('outdoor_pressure', 'N/A'))
        rc.metric('CO (ppm)', current_data.get('outdoor_air_co', 'N/A'))
        rc.metric('Wind (m/s)', current_data.get('outdoor_wind_speed', 'N/A'))
        rc.metric('Dir (°)', current_data.get('outdoor_wind_deg', 'N/A'))
        rc.metric('Weather', current_data.get('outdoor_weather', 'N/A'))
        icon = current_data.get('outdoor_weather_icon')
        if icon:
            rc.image(f"http://openweathermap.org/img/wn/{icon}@2x.png", width=150)
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
            dt = base + pd.Timedelta(days=i)
            same = [x for x in forecast_json if x.get('dt_txt','').startswith(dt.strftime('%Y-%m-%d'))]
            m = min(same, key=lambda x: abs((pd.to_datetime(x['dt_txt']).hour + pd.to_datetime(x['dt_txt']).minute/60) - 12)) if same else {}
            entries.append({'label': dt.strftime('%b %d'), 'temp': m.get('main', {}).get('temp','--'), 'icon': m.get('weather',[{}])[0].get('icon')})
    else:
        fut = [x for x in forecast_json if pd.to_datetime(x.get('dt_txt')) > now]
        for x in fut[:4]:
            dt = pd.to_datetime(x.get('dt_txt'))
            entries.append({'label': dt.strftime('%b %d %H:%M'), 'temp': x['main']['temp'], 'icon': x['weather'][0]['icon']})
    fc_cols = st.columns(4)
    for c, e in zip(fc_cols, entries):
        if e['icon']:
            c.image(f"http://openweathermap.org/img/wn/{e['icon']}@2x.png", width=150)
        c.metric(e['label'], f"{e['temp']}°C")

    st.markdown('#### Metric Over Time')
    src = st.selectbox('Data source', ['Outdoor', 'Indoor'])
    tf = st.selectbox('Timeframe', ['Last 24 hours', 'Last 7 days', 'Last 30 days'])
    delta = pd.Timedelta(hours=24) if '24' in tf else pd.Timedelta(days=7) if '7' in tf else pd.Timedelta(days=30)
    btns = st.columns(4)
    if btns[0].button('Temperature'):
        st.session_state.metric = 'temperature'
    if btns[1].button('Humidity'):
        st.session_state.metric = 'humidity'
    if btns[2].button('CO₂'):
        st.session_state.metric = 'co2'
    if btns[3].button('Pressure'):
        st.session_state.metric = 'pressure'

    metric = st.session_state.metric
    field_map = {
        'temperature': 'outdoor_temperature',
        'humidity': 'outdoor_humidity',
        'co2': 'outdoor_air_co',
        'pressure': 'outdoor_pressure'
    }
    outdoor_field = field_map[metric]
    indoor_field = f"indoor_{metric}" if metric != 'co2' else 'indoor_co2eq'

    if src == 'Outdoor':
        df_time = hist_outdoor_df.loc[hist_outdoor_df['timestamp'] >= now - delta, ['timestamp', outdoor_field]]
    else:
        df_time = hist_indoor_df.loc[hist_indoor_df['timestamp'] >= now - delta, ['timestamp', indoor_field]]

    if df_time.empty:
        st.info(f'No {src.lower()} data available for the chosen timeframe.')
    else:
        titles = {
            'temperature': 'Temperature (°C)',
            'humidity': 'Humidity (%)',
            'co2': 'CO₂ (ppm)',
            'pressure': 'Pressure (hPa)'
        }
        st.altair_chart(
            make_line_chart(
                df_time, 'timestamp', outdoor_field if src == 'Outdoor' else indoor_field,
                f"{src} {titles[metric]}"
            ),
            use_container_width=True
        )

# --- Indoor Panel ---
with col3:
    st.markdown('#### Indoor Sensor Readings')
    if indoor_data:
        a, b = st.columns(2)
        a.metric('Temp (°C)', indoor_data.get('indoor_temperature', 'N/A'))
        a.markdown('**Humidity (%)**')
        hv_i = round(indoor_data.get('indoor_humidity', 0))
        a.altair_chart(make_donut(hv_i, 'Indoor Humidity', 'blue'), use_container_width=True)
        a.metric('Pressure (hPa)', indoor_data.get('indoor_pressure', 'N/A'))
        # Indoor AQI via batch endpoint
        if aqi_result:
            idx = aqi_result.get('index')
            lbl = aqi_result.get('label')
            desc = aqi_result.get('description')
            a.markdown('**Indoor Air Quality Index**')
            a.altair_chart(make_aqi_donut(idx), use_container_width=True)
            a.write(f"**{lbl}**: {desc}")
        else:
            a.write('Unable to calculate indoor air quality index.')
        b.metric('TVOC (ppb)', indoor_data.get('indoor_tvoc', 'N/A'))
        b.metric('CO₂eq (ppm)', indoor_data.get('indoor_co2eq', 'N/A'))
        b.metric('Ethanol (ppm)', indoor_data.get('indoor_ethanol', 'N/A'))
        b.metric('H₂ (ppb)', indoor_data.get('indoor_h2', 'N/A'))
        ts_i = indoor_data.get('timestamp')
        if ts_i:
            a.write(pd.to_datetime(ts_i).strftime('last updated %d.%m.%Y at %H:%M'))
    else:
        st.write('Unable to fetch indoor data.')
